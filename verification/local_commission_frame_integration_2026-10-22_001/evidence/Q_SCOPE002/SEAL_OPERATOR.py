"""Seal only the root-confirmed Q003 evidence; never execute app/tests or open DBs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import xml.etree.ElementTree as ET


PIN = "3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842"
TEST_SHA = "cc9e3da34e59811e32a161bc91b7a8d021e6078fc21c8f7088b49bc858c560c5"
OPERATOR_SHA = "c140c1f1171aa6eaad360f30a94f5bedfc7b1c5472ff230de090d6e995bb374f"
SCOPE_SHA = "324aca20c4f8448951ad9b657e045c04f4f2abe4fde88df5e46e22d1f28989df"
CHECKOUT = Path("/tmp/gene-annotation-configured-caller-20261022-007")
RAW = Path("/tmp/gene-annotation-local-frame-reconstruction-20261022-003")
OUTPUT = Path("/tmp/gene-annotation-Q007-scope002-reconstruction-evidence-20261022-001")
SCOPE = Path("/home/chia/repos/gene_annotation_episode/docs/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_002.md")


def sha(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        assert stat.S_ISREG(os.fstat(stream.fileno()).st_mode)
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata(value):
    return {"mode": format(stat.S_IMODE(value.st_mode), "04o"), "mtime_ns": value.st_mtime_ns,
            "inode": value.st_ino, "device": value.st_dev}


def witness(path):
    value = path.lstat()
    if stat.S_ISREG(value.st_mode):
        return {"kind": "regular", "bytes": value.st_size, "sha256": sha(path), **metadata(value)}
    if stat.S_ISDIR(value.st_mode):
        return {"kind": "directory", **metadata(value)}
    if stat.S_ISLNK(value.st_mode):
        return {"kind": "alias", "target": os.readlink(path), **metadata(value)}
    raise ValueError("special member not traversed: "+str(path))


def tree(root):
    # Known ancestors must be actual directories, never external aliases.
    for path in reversed((root, *root.parents)):
        assert stat.S_ISDIR(path.lstat().st_mode), "alias/non-directory ancestor: "+str(path)
    result = {".": witness(root)}
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories+files):
            path = Path(directory)/name
            result[str(path.relative_to(root))] = witness(path)
    return result


def source_identity():
    members = []
    digest = hashlib.sha256()
    for path in sorted(path for package in ("gene_annotation_episode", "method_loop")
                       for path in (CHECKOUT/package).rglob("*.py")):
        name = str(path.relative_to(CHECKOUT))
        item = {"path": name, **witness(path)}
        assert item["kind"] == "regular"
        digest.update(name.encode()+b"\0")
        digest.update(bytes.fromhex(item["sha256"]))
        members.append(item)
    assert len(members) == 137 and digest.hexdigest() == PIN
    return members


def json_read(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "r") as stream:
        return json.load(stream)


def json_write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-confirmed-final", action="store_true", required=True)
    args = parser.parse_args()
    assert args.root_confirmed_final
    started = datetime.now(timezone.utc).isoformat()
    before = tree(RAW)
    sources_before = source_identity()
    invocation = json_read(RAW/"results.json")
    assert invocation["implementation_sha256"] == invocation["final_implementation_sha256"] == PIN
    assert invocation["test_sha256"] == TEST_SHA and invocation["operator_sha256"] == OPERATOR_SHA
    assert invocation["exit_code"] == 0 and invocation["source_unchanged"] and invocation["selected_members_unchanged"]
    assert invocation["source_members"] == [{"path": row["path"], "sha256": row["sha256"]} for row in sources_before]
    xml = (RAW/"pytest.xml").read_bytes()
    assert b"<!DOCTYPE" not in xml.upper()
    suite, = ET.fromstring(xml)
    cases = list(suite.iter("testcase"))
    counts = {"cases": len(cases), "failed": sum(bool(list(case.iter("failure"))) for case in cases),
              "errors": sum(bool(list(case.iter("error"))) for case in cases),
              "skipped": sum(bool(list(case.iter("skipped"))) for case in cases)}
    assert counts == {"cases": 4, "failed": 0, "errors": 0, "skipped": 0}
    explicit = {
        CHECKOUT/"tests/test_local_commission_frame_reconstruction.py": Path("selected-inputs/test_local_commission_frame_reconstruction.py"),
        CHECKOUT/"scripts/prove_local_commission_frame_reconstruction.py": Path("selected-inputs/prove_local_commission_frame_reconstruction.py"),
        SCOPE: Path("scope/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_002.md"),
        Path(__file__).resolve(): Path("SEAL_OPERATOR.py"),
    }
    explicit_before = {str(path): witness(path) for path in explicit}
    assert explicit_before[str(CHECKOUT/"tests/test_local_commission_frame_reconstruction.py")]["sha256"] == TEST_SHA
    assert explicit_before[str(CHECKOUT/"scripts/prove_local_commission_frame_reconstruction.py")]["sha256"] == OPERATOR_SHA
    assert explicit_before[str(SCOPE)]["sha256"] == SCOPE_SHA
    OUTPUT.mkdir(exist_ok=False)
    prefix = Path("invocation-003")
    aliases = []
    for name, row in before.items():
        source = RAW if name == "." else RAW/name
        destination = OUTPUT/prefix if name == "." else OUTPUT/prefix/name
        if row["kind"] == "directory":
            destination.mkdir(parents=True, exist_ok=True)
        elif row["kind"] == "regular":
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=False)
            assert sha(destination) == row["sha256"]
        else:
            target = Path(os.path.normpath(os.path.join(source.parent, row["target"])))
            assert target.is_relative_to(RAW), "unknown external alias not traversed: "+str(source)
            target_member = prefix/target.relative_to(RAW)
            rebased = os.path.relpath(OUTPUT/target_member, destination.parent)
            destination.symlink_to(rebased)
            aliases.append({"path": str(destination.relative_to(OUTPUT)), "original_path": str(source),
                "original_target": row["target"], "published_target": rebased,
                "target_member": str(target_member), "mapping_kind": "known_internal_rebased", "authority": None})
    for source, member in explicit.items():
        destination = OUTPUT/member
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)
        assert sha(destination) == explicit_before[str(source)]["sha256"]
    process_facts = []
    for fixture in sorted((OUTPUT/prefix/"raw-fixtures").iterdir()):
        fixture_record = json_read(fixture/"fixture.json")
        if "root_worker" not in fixture_record["test"]:
            continue
        with (fixture/"capture-audit.jsonl").open() as stream:
            audits = [json.loads(line) for line in stream]
        with (fixture/"turns.jsonl").open() as stream:
            turns = [json.loads(line) for line in stream]
        parent_pids = sorted({row["pid"] for row in audits if row["execution_handle"] is None})
        worker_pids = sorted({row["pid"] for row in audits if row["execution_handle"] is not None})
        assert len(parent_pids) == len(worker_pids) == 1 and parent_pids != worker_pids
        assert {row["implementation_sha256"] for row in audits} == {PIN}
        assert len(audits) == 12 and sum(row["kind"] == "turn/start" for row in turns) == 6
        process_facts.append({"fixture": str(fixture.relative_to(OUTPUT)), "parent_pids": parent_pids,
            "worker_pids": worker_pids, "worker_handles": sorted({row["execution_handle"] for row in audits if row["execution_handle"]}),
            "capture_count": len(audits), "protocol_turn_count": 6})
    assert len(process_facts) == 2
    after = tree(RAW)
    sources_after = source_identity()
    explicit_after = {str(path): witness(path) for path in explicit}
    assert before == after and sources_before == sources_after and explicit_before == explicit_after
    json_write(OUTPUT/"SOURCE_IDENTITIES.json", {"version": "Q007_scope002_source_readset_v1",
        "runtime_pin": PIN, "runtime_files": 137, "before": sources_before, "after": sources_after,
        "unchanged": True, "runtime_source_bytes_repeated": False})
    json_write(OUTPUT/"COPY_CONTROLS.json", {"version": "Q007_scope002_copy_controls_v1",
        "original_tree": {"source_root": str(RAW), "prefix": str(prefix), "before": before, "after": after},
        "explicit_inputs": [{"source": str(path), "member": str(member), "before": explicit_before[str(path)],
            "after": explicit_after[str(path)]} for path, member in explicit.items()],
        "aliases": aliases, "all_original_bytes_sizes_modes_mtime_inode_device_unchanged": True,
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat()})
    json_write(OUTPUT/"RESULTS_FINAL.json", {"version": "Q007_scope002_reconstruction_results_v1",
        "runtime_pin": PIN, "runtime_files": 137, "test_sha256": TEST_SHA, "operator_sha256": OPERATOR_SHA,
        "invocation": "003", "counts": counts, "suite_seconds": float(suite.attrib["time"]),
        "nodeids": [case.attrib.get("classname", "")+"."+case.attrib["name"] for case in cases],
        "command": invocation["command"], "additional_environment_assignments": invocation["additional_environment_assignments"],
        "source_unchanged": True, "selected_members_unchanged": True, "process_facts": process_facts,
        "verified_by_retained_passing_test_assertions": ["same Store/Journal/backend capture ownership",
            "parent observation order [1,0,2], child [0,1,2], raw zero deltas",
            "v3/v6 and current CE alignment; returned-unadmitted cut has no early payoff",
            "pure saved root/worker replay without recapture or extra observation",
            "original pending retry context/schema order and instructions in both presentation modes"],
        "historical_Q_bundle": "external historical authority; not recopied here",
        "no_cross_invocation_pass_total": True,
        "limits": ["scripted local transports and synthetic separate stores only",
            "actual production controller comparison with fixture exact1/0 estimator and cost0; no numerical wait-model adoption",
            "no live model, network, native science, application/test call or DB open while sealing",
            "no scientific completion, source release, or full-goal claim"],
        "all_original_controls_unchanged": True})
    (OUTPUT/"README.md").write_text("# Q007 scope002 reconstruction evidence\n\n"
        "This new bundle retains raw invocation003 once, after root independently confirmed four passes at the corrected pin. Earlier invocations001/002 remain only in the separate historical Q007 bundle. Do not sum overlapping invocation counts.\n\n"
        "RESULTS_FINAL.json records the exact pin, selected input hashes, XML cases and scripted limits. SOURCE_IDENTITIES.json retains the before/after held137-file readset without duplicating runtime source bytes. COPY_CONTROLS.json records original raw/selected-input witnesses. Files are0444, directories0555. MANIFEST.json excludes its own digest, returned separately. No DB, test, app, model, network or native operation runs while sealing.\n")
    assert tree(RAW) == before and source_identity() == sources_before
    assert {str(path): witness(path) for path in explicit} == explicit_before
    regular = []
    directories = []
    for directory, subdirs, files in os.walk(OUTPUT, followlinks=False):
        directories.append(Path(directory))
        for name in files:
            path = Path(directory)/name
            if path.is_symlink():
                continue
            path.chmod(0o444)
            regular.append({"path": str(path.relative_to(OUTPUT)), "kind": "regular", "sha256": sha(path),
                "bytes": path.stat().st_size, "mode": "0444"})
    manifest = {"version": "Q007_scope002_evidence_manifest_v1", "runtime_pin": PIN,
        "regular_members": sorted(regular, key=lambda row: row["path"]), "aliases": aliases,
        "listed_regular_member_count": len(regular), "listed_regular_bytes": sum(row["bytes"] for row in regular),
        "directory_count_including_root": len(directories), "regular_mode": "0444", "directory_mode": "0555",
        "manifest_self_excluded": True, "physical_regular_member_count_including_manifest": len(regular)+1}
    json_write(OUTPUT/"MANIFEST.json", manifest)
    (OUTPUT/"MANIFEST.json").chmod(0o444)
    for path in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        path.chmod(0o555)
    for row in regular:
        path = OUTPUT/row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["bytes"]
        assert stat.S_IMODE(path.lstat().st_mode) == 0o444
    print(json.dumps({"bundle": str(OUTPUT), "manifest_sha256": sha(OUTPUT/"MANIFEST.json"),
        "results_final_sha256": sha(OUTPUT/"RESULTS_FINAL.json"), "copy_controls_sha256": sha(OUTPUT/"COPY_CONTROLS.json"),
        "listed_regular_member_count": len(regular), "listed_regular_bytes": manifest["listed_regular_bytes"],
        "physical_regular_member_count_including_manifest": len(regular)+1,
        "physical_bytes_including_manifest": manifest["listed_regular_bytes"]+(OUTPUT/"MANIFEST.json").stat().st_size,
        "directories": len(directories), "aliases": len(aliases), "readonly": True,
        "originals_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
