"""Seal existing Q007 scripted reconstruction evidence; execute no application."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import xml.etree.ElementTree as ET


EXPECTED_PIN = "d39a6756507bacd8e9ba90f75912cc01822a316f766cc72764154b7205ba81e3"
CHECKOUT = Path("/tmp/gene-annotation-configured-caller-20261022-007")
BUNDLE = Path("/tmp/gene-annotation-Q007-reconstruction-evidence-20261022-001")
ROOTS = {
    Path("/tmp/gene-annotation-local-frame-reconstruction-20261022-001"): Path("invocations/001"),
    Path("/tmp/gene-annotation-local-frame-reconstruction-20261022-002"): Path("invocations/002"),
    Path("/tmp/gene-annotation-frame-reconstruction-authoring-20261022-001"): Path("authoring-drafts"),
}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def details(path):
    value = path.lstat()
    if stat.S_ISREG(value.st_mode):
        return {"kind": "regular", "sha256": sha(path), "bytes": value.st_size,
                "mode": format(stat.S_IMODE(value.st_mode), "04o")}
    if stat.S_ISDIR(value.st_mode):
        return {"kind": "directory", "mode": format(stat.S_IMODE(value.st_mode), "04o")}
    if stat.S_ISLNK(value.st_mode):
        return {"kind": "alias", "target": os.readlink(path),
                "mode": format(stat.S_IMODE(value.st_mode), "04o")}
    raise RuntimeError(f"unexpected special member; not traversed: {path}")


def inventory(root):
    result = {".": details(root)}
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories+files):
            path = Path(directory)/name
            result[str(path.relative_to(root))] = details(path)
    return result


def pin(members):
    digest = hashlib.sha256()
    for item in members:
        digest.update(item["path"].encode()+b"\0")
        digest.update(bytes.fromhex(item["sha256"]))
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def copied_sqlite(path, callback):
    connection = sqlite3.connect(path.as_uri()+"?mode=ro&immutable=1", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        return callback(connection)
    finally:
        connection.close()


def route_summary(fixture):
    manifest = json.loads((fixture/"run/run.json").read_text())
    audits = [json.loads(line) for line in (fixture/"capture-audit.jsonl").read_text().splitlines()]
    turns = [json.loads(line) for line in (fixture/"turns.jsonl").read_text().splitlines()]
    def read(db):
        spec, = [json.loads(row[0]) for row in db.execute("SELECT spec FROM runtime_commission_intents")]
        parent, child = (spec[side]["episode_id"] for side in ("parent", "child"))
        observations = {episode: [json.loads(row[0]) for row in db.execute(
            "SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index", (episode,))]
            for episode in (parent, child)}
        requests = {row[0]: json.loads(row[1]) for row in db.execute(
            "SELECT call_index,request FROM runtime_model_calls WHERE episode_id=?", (parent,))}
        contexts = {row[0]: json.loads(row[1]) for row in db.execute(
            "SELECT decision_index,data FROM runtime_estimation_contexts WHERE episode_id=?", (parent,))}
        after_wait, = contexts[1]["local_commission_frame_after_action"]["commissions"]
        after_admission, = contexts[0]["local_commission_frame_after_action"]["commissions"]
        current = after_admission["admission_evidence"]["sample"]
        result = {
            "run_id": manifest["run_id"], "handle": spec["handle"],
            "parent_episode_id": parent, "child_episode_id": child,
            "source_pin": spec["runtime_binding"]["implementation_sha256"],
            "parent_capture_pids": sorted({row["pid"] for row in audits if row["episode_id"] == parent}),
            "worker_capture_pids": sorted({row["pid"] for row in audits if row["episode_id"] == child}),
            "worker_capture_handles": sorted({row["execution_handle"] for row in audits if row["episode_id"] == child}),
            "capture_counts": {episode: sum(row["episode_id"] == episode for row in audits)
                               for episode in (parent, child)},
            "protocol_turn_count": sum(row["kind"] == "turn/start" for row in turns),
            "observation_decision_order": {episode: [row["decision_index"] for row in values]
                                            for episode, values in observations.items()},
            "raw_controller_deltas": {episode: [row["step"]["marginal_credit"] for row in values]
                                      for episode, values in observations.items()},
            "original_admission_count": db.execute("SELECT count(*) FROM runtime_return_admissions").fetchone()[0],
            "model_request_versions": sorted({json.loads(row[0])["version"] for row in db.execute("SELECT request FROM runtime_model_calls")}),
            "completed_context_versions": sorted({json.loads(row[0])["version"] for row in db.execute("SELECT data FROM runtime_estimation_contexts")}),
            "wait_completion_cut": {"accounting_status": after_wait["accounting_status"],
                "return_presence": after_wait["return_presence"],
                "admission_evidence": after_wait["admission_evidence"]},
            "original_admission_before_observation_cut": {key: current[key] for key in
                ("admission_state", "observation_state", "raw_controller_delta", "unit_ref", "completion_sequence")},
            "original_selection_population_count": requests[0]["local_commission_frame"]["population_count"],
        }
        assert result["source_pin"] == EXPECTED_PIN
        assert result["observation_decision_order"][parent] == [1, 0, 2]
        assert result["observation_decision_order"][child] == [0, 1, 2]
        assert result["original_admission_count"] == 1
        assert result["parent_capture_pids"] != result["worker_capture_pids"]
        assert result["worker_capture_handles"] == [spec["handle"]]
        assert current["observation_state"] == "unobserved" and current["raw_controller_delta"] is None
        assert after_wait["admission_evidence"] is None and after_wait["return_presence"] == "observed"
        return result
    return copied_sqlite(fixture/"case/workspace/state.sqlite3", read)


def main():
    started = datetime.now(timezone.utc).isoformat()
    before = {str(root): inventory(root) for root in ROOTS}
    source_members = [{"path": str(path.relative_to(CHECKOUT)), "sha256": sha(path)}
        for path in sorted(path for package in ("gene_annotation_episode", "method_loop")
                           for path in (CHECKOUT/package).rglob("*.py"))]
    assert len(source_members) == 137 and pin(source_members) == EXPECTED_PIN
    explicit = {CHECKOUT/item["path"]: Path("runtime-source")/item["path"] for item in source_members}
    explicit.update({
        CHECKOUT/"tests/test_local_commission_frame_reconstruction.py": Path("selected-inputs/test_local_commission_frame_reconstruction.py"),
        CHECKOUT/"scripts/prove_local_commission_frame_reconstruction.py": Path("selected-inputs/prove_local_commission_frame_reconstruction.py"),
        Path("/home/chia/repos/gene_annotation_episode/docs/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_001.md"):
            Path("scope/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_001.md"),
        Path(__file__).resolve(): Path("SEAL_OPERATOR.py"),
    })
    explicit_before = {str(path): details(path) for path in explicit}
    BUNDLE.mkdir(exist_ok=False)
    aliases = []
    for root, target in ROOTS.items():
        for relative, item in before[str(root)].items():
            source = root if relative == "." else root/relative
            destination = BUNDLE/target if relative == "." else BUNDLE/target/relative
            if item["kind"] == "directory":
                destination.mkdir(parents=True, exist_ok=True)
            elif item["kind"] == "regular":
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination, follow_symlinks=False)
                assert sha(destination) == item["sha256"]
            else:
                # Resolve only lexically against the finite known source roots.
                original = Path(os.path.normpath(os.path.join(source.parent, item["target"])))
                translated = None
                for known, copied in ROOTS.items():
                    if original.is_relative_to(known):
                        translated = BUNDLE/copied/original.relative_to(known)
                        break
                target_text = item["target"] if translated is None else os.path.relpath(translated, destination.parent)
                destination.symlink_to(target_text)
                aliases.append({"path": str(destination.relative_to(BUNDLE)), "original_target": item["target"],
                    "target": target_text, "status": "unknown_external_not_traversed" if translated is None else "known_internal_rebased"})
    for source, relative in explicit.items():
        destination = BUNDLE/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)
        assert sha(destination) == explicit_before[str(source)]["sha256"]
    # Compare originals after every read/copy; no mode or byte change is permitted.
    after = {str(root): inventory(root) for root in ROOTS}
    explicit_after = {str(path): details(path) for path in explicit}
    assert before == after and explicit_before == explicit_after
    controls = {"version": "q007_reconstruction_copy_controls_v1", "started_at": started,
        "copied_at": datetime.now(timezone.utc).isoformat(),
        "original_trees": {root: {"before": before[root], "after": after[root],
            "destination": str(ROOTS[Path(root)]), "unchanged": True} for root in before},
        "explicit_inputs": [{"source": str(path), "destination": str(relative),
            "before": explicit_before[str(path)], "after": explicit_after[str(path)], "unchanged": True}
            for path, relative in explicit.items()],
        "all_original_bytes_sizes_modes_unchanged": True,
        "aliases": aliases, "unknown_aliases_traversed": False}
    write_json(BUNDLE/"COPY_CONTROLS.json", controls)
    invocations = {}
    for label, expected in (("001", (2, 2)), ("002", (4, 0))):
        folder = BUNDLE/"invocations"/label
        recorded = json.loads((folder/"results.json").read_text())
        suite, = ET.parse(folder/"pytest.xml").getroot()
        actual = (int(suite.attrib["tests"])-int(suite.attrib["failures"])-int(suite.attrib["errors"]), int(suite.attrib["failures"]))
        assert actual == expected
        assert recorded["implementation_sha256"] == recorded["final_implementation_sha256"] == EXPECTED_PIN
        assert recorded["source_unchanged"] and recorded["selected_members_unchanged"]
        assert recorded["source_members"] == source_members
        invocations[label] = {"passed": actual[0], "failed": actual[1], "errors": int(suite.attrib["errors"]),
            "elapsed_seconds": float(suite.attrib["time"]), "exit_code": recorded["exit_code"],
            "command": recorded["command"], "additional_environment_assignments": recorded["additional_environment_assignments"],
            "implementation_sha256": EXPECTED_PIN, "test_sha256": recorded["test_sha256"],
            "operator_sha256": recorded["operator_sha256"], "source_unchanged": True,
            "selected_members_unchanged": True, "results_sha256": sha(folder/"results.json"),
            "log_sha256": sha(folder/"pytest.log"), "xml_sha256": sha(folder/"pytest.xml")}
    actual_routes = []
    for fixture in sorted((BUNDLE/"invocations/002/raw-fixtures").iterdir()):
        if "root_worker" in json.loads((fixture/"fixture.json").read_text())["test"]:
            actual_routes.append({"fixture": str(fixture.relative_to(BUNDLE)), **route_summary(fixture)})
    assert len(actual_routes) == 2
    final = {"version": "Q007_local_commission_frame_reconstruction_results_v1",
        "source_file_count": 137, "implementation_sha256": EXPECTED_PIN,
        "historical_invocation_001": invocations["001"], "final_invocation_002": invocations["002"],
        "final_distinct_passing_cases": 4, "historical_passes_overlap_final": True,
        "pass_counts_must_not_be_added": True,
        "first_failure": {"classification": "scripted_transport_fixture_only", "count": 2,
            "exception": "KeyError: role", "stage": "first root provider response, before C1 child commission",
            "correction": "use original goal.parent_goal_id in scripted transport and protocol-log grouping",
            "patch": "invocations/002/fixture-correction.patch",
            "production_changes": []},
        "actual_scripted_routes": actual_routes,
        "verified_by_passing_tests": ["same actual Store/Journal/backend in root and detached worker frame capture",
            "v3 selection frames kept outside provider context and presentation",
            "v6 pair and current CE aligned before existing on_unit observation",
            "returned but unadmitted wait cut has no payoff; current admission remains unobserved in frame",
            "one parent observation per actual completion in order wait, original child report, query",
            "saved root and worker slot/context replay forbids frame, pending, CE, provider and tool recapture",
            "interrupted v3 retries preserve exact request TEXT, serialized context, generated schema order and instructions in both modes"],
        "numerical_scope": {"controller": "production YieldController available upper <= caller cost",
            "scripted_estimator": "existing test_case_execution fixture callback exact1 until stop_after3 (route) or1 (retry), then exact0, cost0",
            "fixture_credit": "constant zero; raw deltas preserved", "pending_aware_model_adopted": False,
            "new_payoff_or_observation": False},
        "limits": ["scripted local RPC transports, fixture gates and synthetic separate stores only",
            "no live model, public network, native scientific computation or configured scientific proof",
            "source capture facts do not fit an arrival/payoff or censoring model",
            "saved JSON contains original absolute provenance paths unchanged; it is evidence, not a relocated deployment",
            "root12 original-module checks are separate and may remain active; no source release or complete-goal claim"],
        "copy_controls": "COPY_CONTROLS.json", "all_original_bytes_sizes_modes_unchanged": True,
        "filesystem_alias_count": len(aliases), "unknown_external_aliases": [item for item in aliases if item["status"] == "unknown_external_not_traversed"]}
    write_json(BUNDLE/"RESULTS_FINAL.json", final)
    (BUNDLE/"README.md").write_text("# Q007 factual commission-frame reconstruction evidence\n\n"
        "Final invocation002 passed four distinct scripted engineering cases. Historical invocation001 had two overlapping passes and two fixture failures before child commission. Do not add invocation pass counts.\n\n"
        "RESULTS_FINAL.json binds both invocations, exact held 137-file source, input revisions, actual process/observation facts and limits. COPY_CONTROLS.json records each original member's before/after bytes, size and mode. Original trees were copied without modification. MANIFEST.json inventories every other regular member and all filesystem aliases; its own hash is supplied separately. Files are 0444 and directories 0555. No aliases were found, so no external data were traversed. Saved absolute JSON paths remain original provenance, not relocated execution claims.\n\n"
        "No tests were run while sealing. This bundle neither releases the source freeze nor establishes scientific completion.\n")
    # Final original controls also cover the metadata-building phase.
    assert all(inventory(root) == before[str(root)] for root in ROOTS)
    assert all(details(path) == explicit_before[str(path)] for path in explicit)
    directories = []
    regular = []
    for directory, subdirs, files in os.walk(BUNDLE, followlinks=False):
        directories.append(Path(directory))
        for name in files:
            path = Path(directory)/name
            if path.is_symlink():
                continue
            path.chmod(0o444)
            regular.append({"path": str(path.relative_to(BUNDLE)), **details(path)})
    manifest = {"version": "Q007_evidence_manifest_v1", "regular_members": sorted(regular, key=lambda row: row["path"]),
        "aliases": aliases, "listed_regular_member_count": len(regular),
        "listed_regular_bytes": sum(row["bytes"] for row in regular),
        "directory_count_including_root": len(directories), "directory_mode": "0555",
        "regular_mode": "0444", "alias_count": len(aliases),
        "self_exclusion": "MANIFEST.json is excluded from regular_members; its SHA256 is returned separately",
        "physical_regular_member_count_including_manifest": len(regular)+1}
    write_json(BUNDLE/"MANIFEST.json", manifest)
    (BUNDLE/"MANIFEST.json").chmod(0o444)
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        directory.chmod(0o555)
    # Reopen and verify every sealed member, then close each read handle.
    for item in regular:
        assert details(BUNDLE/item["path"]) == {key: value for key, value in item.items() if key != "path"}
    assert all(stat.S_IMODE(directory.stat().st_mode) == 0o555 for directory in directories)
    print(json.dumps({"bundle": str(BUNDLE), "manifest_sha256": sha(BUNDLE/"MANIFEST.json"),
        "results_final_sha256": sha(BUNDLE/"RESULTS_FINAL.json"),
        "copy_controls_sha256": sha(BUNDLE/"COPY_CONTROLS.json"),
        "listed_regular_member_count": len(regular), "physical_regular_member_count_including_manifest": len(regular)+1,
        "listed_regular_bytes": manifest["listed_regular_bytes"],
        "physical_regular_bytes_including_manifest": manifest["listed_regular_bytes"]+(BUNDLE/"MANIFEST.json").stat().st_size,
        "directory_count_including_root": len(directories), "alias_count": len(aliases),
        "all_original_bytes_sizes_modes_unchanged": True, "readonly": True}, indent=2))


if __name__ == "__main__":
    main()
