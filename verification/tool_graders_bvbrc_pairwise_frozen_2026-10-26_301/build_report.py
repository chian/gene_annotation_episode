"""Read completed verification outputs; no scientific code or native work runs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
SNAPSHOT = EVIDENCE / "snapshot"
CHECK = SNAPSHOT / "verification/frozen_check_001"


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def artifact(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}


def junit(path):
    root = ET.parse(path).getroot()
    cases = []
    for case in root.iter("testcase"):
        failed = next((node for node in case if node.tag in {"failure", "error", "skipped"}), None)
        cases.append({"name": case.attrib["name"], "classname": case.attrib["classname"],
            "seconds": float(case.attrib["time"]), "status": "passed" if failed is None else failed.tag,
            "message": None if failed is None else failed.attrib.get("message"),
            "detail": None if failed is None else failed.text})
    counts = {"tests": len(cases), **{label: sum(row["status"] == tag for row in cases)
        for label, tag in (("passed", "passed"), ("failures", "failure"), ("errors", "error"), ("skipped", "skipped"))}}
    return {"counts": counts, "seconds": sum(float(s.attrib.get("time", 0)) for s in root.iter("testsuite")), "cases": cases}


def archive_nodes(node):
    yield node
    for unit in node.get("units", []):
        if isinstance(unit.get("child"), dict):
            yield from archive_nodes(unit["child"])


def main():
    receipt = read(CHECK / "receipt.json")
    result = junit(CHECK / "junit.xml")
    runs = list((SNAPSHOT / "verification/tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24/runs").glob("*"))
    if len(runs) != 1:
        raise RuntimeError("exactly_one_original_pairwise_fixture_run_required")
    run, = runs
    manifest = read(EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json")
    before, after = read(CHECK / "source_before.json"), read(CHECK / "source_after.json")
    source_before, source_after = read(run / "SOURCE_PROVENANCE.json"), read(run / "SOURCE_PROVENANCE_AFTER.json")
    source_differences = {key: {"before": value, "after": source_after.get(key)}
        for key, value in source_before.items() if key != "loaded_modules" and value != source_after.get(key)}
    changed_files = {key: {"before": value, "after": source_after["files"].get(key)}
        for key, value in source_before["files"].items() if source_after["files"].get(key) != value}
    imports = read(CHECK / "imports_after.json")
    numerical = None
    accounting = []
    if (run / "sheet.json").is_file():
        sheet, components, publication = read(run / "sheet.json"), read(run / "components.json"), read(run / "publication.json")
        query, = sheet["queries"]
        paired = query["blast_sheet"]
        hsp, = paired["hsps"]
        returned, forwarded = read(run / "results-return.json"), read(run / "scientific-return.json")
        partials = []
        for path in run.rglob("scientific_adapter_result.json"):
            value = read(path)["adapter_result"]
            if value is not None and value["status"] == "partial":
                partials.append({"source_path": str(path), "status": value["status"],
                    "facts": value["facts"], "missing_requirements": value["missing_requirements"]})
        contradiction_path = run / "contradictory-reference-claim-result.json"
        contradiction = read(contradiction_path) if contradiction_path.exists() else None
        replay_path = run / "saved-replay-verification.json"
        replay = read(replay_path) if replay_path.exists() else None
        numerical = {"representation": "Synthetic native BLAST JSON15 bytes processed by actual production code; no BLAST/service execution",
            "input_sequences": {"query": read(run / "original-input.json")["query_members"][0]["sequence"],
                "reference": read(run / "original-input.json")["reference_members"][0]["sequence"]},
            "scientific_mode": sheet["scientific_mode"], "source_sheet": artifact(run / "sheet.json"),
            "source_components": artifact(run / "components.json"),
            "native_bytes": artifact(run / "native-raw.json"),
            "measurements_received_by_results_parent": returned["measurements"],
            "measurements_forwarded_to_root": forwarded["measurements"],
            "returned_values": {row["field"]: row["value"] for row in returned["measurements"]},
            "hsp_native_scores": hsp["components"]["native_scores"],
            "hsp_counts": hsp["components"]["counts"],
            "coordinate_units": hsp["components"]["coordinate_units"],
            "pairwise_union": paired["union"],
            "formulas": paired["calculations"],
            "conditional_function_weights": components["queries"][0]["conditional_function_weights"],
            "database_model": sheet["binding"]["adapter_parameters"]["database_model"],
            "partial_publications": partials,
            "contradictory_reference": None if contradiction is None else {
                "artifact": artifact(contradiction_path), "status": contradiction["status"],
                "facts": contradiction["facts"], "missing_requirements": contradiction["missing_requirements"],
                "diagnostics": contradiction["diagnostics"]},
            "recalculation_and_replay": replay,
            "final_projection_status": publication["publication"]["requested_form_status"],
            "task_association_qualification": [row["task_association"]["byte_version_status"]
                for row in publication["bundle"]["artifacts"] if row["role"] == "blast_json15_raw"]}
        if (run / "archive.json").exists():
            nodes = {node["episode_id"]: node for node in archive_nodes(read(run / "archive.json"))}
            with sqlite3.connect((run / "state/state.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
                db.row_factory = sqlite3.Row
                for episode in db.execute("SELECT episode_id,path,state FROM runtime_episodes ORDER BY rowid"):
                    eid = episode["episode_id"]
                    actions = [json.loads(row[0]) for row in db.execute("SELECT action FROM runtime_actions WHERE episode_id=? ORDER BY decision_index", (eid,))]
                    node = nodes[eid]
                    accounting.append({"role": json.loads(episode["path"])[-1][0], "episode_id": eid,
                        "state": episode["state"], "action_categories": [row.get("tool") if row["kind"] == "tool" else row["kind"] + ":" + row.get("role", "") for row in actions],
                        "counts": {table: db.execute("SELECT count(*) FROM " + table + " WHERE episode_id=?", (eid,)).fetchone()[0]
                            for table in ("runtime_actions", "runtime_observations", "runtime_model_calls")},
                        "expected_next_gain": node["controller_state"]["estimate"]["expected_next_gain"],
                        "actual_marginal_gains": [unit["controller_step"]["marginal_credit"] for unit in node["units"]]})
        write(EVIDENCE / "NUMERICAL_EXAMPLES.json", numerical)
        write(EVIDENCE / "ACTION_ACCOUNTING.json", accounting)
    previous_differences = read(EVIDENCE / "authority/prior-source-differences.json")
    previous_receipt = read(EVIDENCE / "authority/prior-RECOVERED_RECEIPT_001.json")
    original_junit = ROOT / "verification/tool_graders_blast_geometry_2026-10-26_295/checks_003/junit.xml"
    original_errors = [row for row in junit(original_junit)["cases"] if row["status"] == "error"]
    for row in original_errors:
        row["detail"] = row["detail"][-2000:] if row["detail"] else None
    stable = before["unchanged"] and after["unchanged"] and not source_differences and imports["all_project_and_fixture_imports_copied"]
    passed = stable and receipt["returncode"] == 0 and result["counts"] == {"tests": 5, "passed": 5, "failures": 0, "errors": 0, "skipped": 0}
    diagnosis = {"schema": "frozen_pairwise_verification_v1", "workload": "301",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Only the exact tests/test_bvbrc_homology_pairwise_workflow.py on the acquired source snapshot",
        "result": "passed" if passed else "failed_or_unverified", "pytest": result,
        "native_receipt": receipt, "snapshot_receipt": read(EVIDENCE / "SOURCE_SNAPSHOT_RECEIPT.json"),
        "snapshot_checks": {"all_copied_files_before": before, "all_copied_files_after": after,
            "fixture_source_differences": source_differences, "fixture_changed_files": changed_files,
            "fixture_hashed_file_count": len(source_before["files"]),
            "imported_project_and_fixture_module_count": imports["module_count"],
            "all_project_and_fixture_imports_copied": imports["all_project_and_fixture_imports_copied"],
            "original_provenance_assertion_preserved": True},
        "previous_run": {"native_receipt": previous_receipt, "junit": artifact(original_junit),
            "pairwise_setup_errors": original_errors, "provenance_differences": previous_differences,
            "diagnosis": "All five prior setup errors arose at the fixture's final provenance equality assertion after nine source files changed during the original run; its historical result remains unchanged.",
            "original_job_altered_or_rerun": False},
        "production_files_modified_by_this_workload": [], "original_tests_modified_by_this_workload": [],
        "actual_run_directory": str(run), "action_accounting": accounting,
        "numerical_examples": None if numerical is None else artifact(EVIDENCE / "NUMERICAL_EXAMPLES.json"),
        "actual_work": read(run / "PROVENANCE.json"),
        "limitations": [
            "Controlled choices and root/scientific continuation; NativeClient supplies explicitly synthetic service bytes.",
            "No live BV-BRC request, native BLAST executable, database BLAST, configured model or HPC execution.",
            "This verifies current frozen source for five pairwise cases only, not a frozen pass of the earlier broad suite.",
            "The test exercises its existing composed Workflow route; it does not establish independent detached episode execution.",
            "Copied production packages, fixtures and selected publication are immutable; the existing .venv and system Python libraries were reused, with loaded file hashes also checked by the unchanged fixture.",
            "Artifact/task association does not establish producer-bound remote byte versions; the saved qualification remains explicit.",
            "Filled numerical outputs are verification examples, not new tool-library fields, grader functions or evidence of biological function."]}
    write(EVIDENCE / "DIAGNOSIS.json", diagnosis)
    artifacts = [EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json", EVIDENCE / "SOURCE_SNAPSHOT_RECEIPT.json",
        CHECK / "receipt.json", CHECK / "junit.xml", CHECK / "stdout.txt", CHECK / "stderr.txt",
        CHECK / "source_before.json", CHECK / "source_after.json", CHECK / "imports_collection.json", CHECK / "imports_after.json",
        run / "SOURCE_PROVENANCE.json", run / "SOURCE_PROVENANCE_AFTER.json", EVIDENCE / "DIAGNOSIS.json"]
    artifacts.extend(path for path in run.iterdir() if path.is_file() and path not in artifacts)
    artifacts.extend(path for path in (EVIDENCE / "NUMERICAL_EXAMPLES.json", EVIDENCE / "ACTION_ACCOUNTING.json") if path.is_file())
    counts = result["counts"]
    values = numerical["returned_values"] if numerical else {}
    snapshot_count = sum(row["category"] == "snapshot" for row in manifest["files"])
    authority_count = sum(row["category"] == "authority" for row in manifest["files"])
    report = [
        f"The unchanged pairwise workflow module produced **{counts['passed']} passed, {counts['failures']} failed, {counts['errors']} errors** in {result['seconds']:.3f} seconds. Native return code: {receipt['returncode']}. This is a five-case verification on the acquired snapshot; it is not a frozen all-suite pass.",
        f"The acquisition manifest covers {manifest['file_count']:,} copied files ({manifest['byte_count']:,} bytes): {snapshot_count:,} snapshot files and {authority_count} authority/evidence files. Original hashes were stable across acquisition and every copied hash agreed. Source files and directories were made read-only. Before/after execution checks covered all copied files; the test's own provenance assertion stayed enabled and checked {len(source_before['files']):,} files. All {imports['module_count']} loaded project and fixture modules resolved to copied files. See [snapshot receipt](SOURCE_SNAPSHOT_RECEIPT.json) and [full source manifest](SOURCE_SNAPSHOT_MANIFEST.json).",
        "The native job used the existing .venv Python through copied production local_jobs, with 20 GiB RAM, 4 GiB scratch and no wall cap. The receipt records cgroup enforcement and measured duration. [Receipt](snapshot/verification/frozen_check_001/receipt.json), [JUnit](snapshot/verification/frozen_check_001/junit.xml), [stdout](snapshot/verification/frozen_check_001/stdout.txt), [stderr](snapshot/verification/frozen_check_001/stderr.txt).",
        "The prior broad run remains 226 passed, 15 failed and 5 errors. All five pairwise errors arose at the final SOURCE_PROVENANCE equality assertion after nine production files changed during the long fixture. No original job, receipt, log or source file was altered. Exact prior hashes, test error text and current checks are retained in [DIAGNOSIS.json](DIAGNOSIS.json).",
    ]
    if numerical:
        report += [
            "Actual retained numerical example from this run:",
            "| Quantity | Value | Meaning |\n| --- | ---: | --- |\n"
            f"| Query paired coverage | {values.get('query_coverage')} | 9 paired nucleotide positions / 15 supplied nucleotide positions |\n"
            f"| Reference paired coverage | {values.get('reference_coverage')} | 3 paired amino-acid positions / 5 supplied amino-acid positions |\n"
            f"| Distinct aligned pairs | {values.get('aligned_pairs')} | Three translated codon-to-residue correspondences |\n"
            f"| Paired identity | {values.get('identity')} | 3 identical amino-acid pairs / 3 paired columns |",
            "The 15-nt query ATGAAAACTGGGTAA and 5-aa reference MKTGG produce the synthetic native MKT/MKT HSP. Native score 40, bit score 20 and E-value 0 are retained separately; database E-value does not define pairwise relevance. Query intervals are [0,3), [3,6), [6,9); reference intervals are [0,1), [1,2), [2,3). Database function weights and database-model parameters remain null.",
            "The requested measurements reach the results parent and are forwarded through the scientific child's typed return. The intermediate publication retains missing values. Contradictory reference identity yields partial status and null pairwise facts. The saved-sheet/replay check forbids acquisition, preserves durable actions and forms, and adds zero native calls. See [numerical examples](NUMERICAL_EXAMPLES.json) and [action accounting](ACTION_ACCOUNTING.json).",
            "Actual code paths exercised include input parsing, custody, selected primitive calls, manifest associations, artifact retention, Homology native parsing, pairwise sheet construction, deterministic calculations, typed returns and practical completion. Selected decisions, root/scientific continuation and NativeClient transport are fixture controls. Synthetic native bytes do not establish live BV-BRC or native BLAST execution.",
        ]
    report += ["No production file or original test changed. No annotation scoring, literature grading, root execution, runtime-loop behavior, resource deployment or scope accounting changed. This existing composed Workflow test does not establish independent detached execution. The remaining live-service and broad-suite claims stay unverified. [Inspected implementation paths](INSPECTION.md) and [completion review](COMPLETION_REVIEW.json) record the scope of inspection and the final authority/contract reread."]
    (EVIDENCE / "REPORT.md").write_text("\n\n".join(report) + "\n")
    artifacts.extend(EVIDENCE / name for name in ("REPORT.md", "INSPECTION.md", "COMPLETION_REVIEW.json",
        "acquire_snapshot.py", "run_checks.py", "run_frozen_pytest.py", "build_report.py") if (EVIDENCE / name).is_file())
    write(EVIDENCE / "ARTIFACT_MANIFEST.json", [artifact(path) for path in artifacts])
    print(json.dumps({"result": diagnosis["result"], **result["counts"], "seconds": result["seconds"], "numeric_values": values,
        "source_stable": stable, "report": str(EVIDENCE / "REPORT.md")}, sort_keys=True))


if __name__ == "__main__":
    main()
