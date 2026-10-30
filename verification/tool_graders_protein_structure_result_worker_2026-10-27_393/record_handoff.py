"""Metadata-only manifest of already completed checks; no scientific execution."""
from pathlib import Path
import hashlib
import json

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
RUN = PACKET / "check004"


def checksum(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(PACKET)), "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}


def write(name, value):
    target = PACKET / name
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    with target.open("xb") as stream:
        stream.write(raw)


results = []
for path in sorted((RUN / "temporary/pytest").rglob("worker-result.json")):
    result = json.loads(path.read_bytes())
    files = []
    for field in ("native_result_file", "sheet_file", "components_file"):
        declared = result[field]
        if declared is None:
            continue
        output = path.parent / declared["relative_path"]
        observed = checksum(output)
        assert observed["sha256"] == declared["file_identity"]["sha256"]
        assert observed["byte_length"] == declared["file_identity"]["byte_length"]
        assert declared["file_identity"]["artifact_ref"] == "artifact_" + observed["sha256"]
        files.append({"field": field, **observed, "file_identity": declared["file_identity"]})
    results.append({"worker_result_file": checksum(path), "result": result, "outputs": files})
write("FILLED_OUTPUT_MANIFEST_001.json", {"version": "protein_result_worker_verification_manifest_v1",
    "run": "check004", "qualification": "synthetic_native_format_engineering_checks_not_biological_measurements",
    "authorization": "no_Store_registration_or_received_prefix_authority_claimed",
    "record_count": len(results), "records": results})

examples = []
for label, test in (("native_held_out_cli", "test_real_cli_and_output_bytes0"),
                    ("saved_all_pairs_cli", "test_real_cli_and_output_bytes1"),
                    ("missing_native_cli", "test_real_cli_and_output_bytes2"),
                    ("saved_changed_fit", "test_saved_explicit_new_fit_se0"),
                    ("saved_changed_mode", "test_saved_explicit_mode_chang0"),
                    ("diagnostic_native_arithmetic_rejected", "test_c_valid_native_with_bad_a0")):
    root = RUN / "temporary/pytest" / test
    path = root / "output/worker-result.json"
    assert path.exists(), path
    result = json.loads(path.read_bytes())
    entry = {"label": label, "worker_result_file": checksum(path), "result": result}
    if result["components_file"] is not None:
        components_path = path.parent / "components.json"
        components = json.loads(components_path.read_bytes())
        entry.update(components_file=checksum(components_path), calculation_id=components["calculation_id"],
            parameters=components["parameters"], counts=components["counts"], evaluation=components["evaluation"],
            transform=components["transform"], fit_rmsd=components["fit"]["fit_rmsd"])
    if (root / "plan.json").exists():
        entry["plan_file"] = checksum(root / "plan.json")
        entry["command_file"] = checksum(root / "cli-command.json")
    examples.append(entry)
write("FILLED_EXAMPLES_001.json", {"qualification": "values_copied_from_actual_completed_worker_files_without_recalculation",
    "examples": examples})

snapshot = RUN / "source_snapshot"
before = json.loads((RUN / "source_pins_before.json").read_bytes())
imports = json.loads((RUN / "executed_imports_after.json").read_bytes())
imported = {str(Path(path).relative_to(snapshot)) for path in imports.values() if path}
required = imported | {"tests/test_protein_structure_result_worker.py",
    "gene_annotation_episode/local_jobs.py", "gene_annotation_episode/native_lifecycle.py",
    "gene_annotation_episode/_local_job_worker.py"}
pins = [row for row in before if row["path"] in required]
for row in pins:
    raw = (REPO / row["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["sha256"]
write("SOURCE_PINS_001.json", {"run": "check004", "source": "actual_executed_snapshot",
    "pinned_files": pins, "all_snapshot_pins": "check004/source_pins_before.json",
    "after_pins": "check004/source_pins_after.json"})

runs = []
outcomes = {"check001": {"passed": 68, "failed": 7, "pytest_seconds": 20.79},
    "check002": {"passed": 76, "failed": 0, "pytest_seconds": 24.08},
    "check003": {"passed": 0, "failed": 3, "pytest_seconds": 0.62},
    "check004": {"passed": 79, "failed": 0, "pytest_seconds": 26.13}}
for name, outcome in outcomes.items():
    receipt = json.loads((PACKET / name / "receipt.json").read_bytes())
    runs.append({"run": name, **outcome, "receipt": receipt})
write("VERIFICATION_001.json", {"version": "protein_result_worker_verification_v1", "runs": runs,
    "counts_are_overlapping_runs_not_unique_tests_added_together": True,
    "final_suite": {"run": "check004", "passed": 79, "failed": 0},
    "inspected": ["immutable_goal_complete", "AGENTS.md", "380_001_relevant_A_B_C_records",
        "380_addenda_002_003_004_006_007_008_009", "B389_and_C390_complete_handoffs",
        "A_B_C_complete_scientific_and_execution_modules", "local_jobs_and_native_lifecycle"],
    "retained_native": "C390_bounded_synthetic_native_operations_and_B389_filled_examples",
    "live_resources": {"local_bounded_result_worker_and_cli": "verified", "new_native_structure_analysis": "not_run_by_D2b",
        "API": "not_run", "HPC": "not_run", "model": "not_run"},
    "not_established": ["Store_authority", "capture_custody", "received_prefix_authorization", "normal_sequence_publication",
        "parent_forms_and_returns", "complete_selected_tool_episode_path", "scientific_annotation_credit", "tool_tally_change"]})
print(json.dumps({"final_passed": 79, "filled_result_records": len(results), "filled_examples": len(examples),
    "worker_pin": next(row for row in pins if row["path"].endswith("/protein_structure_result_worker.py")),
    "test_pin": next(row for row in pins if row["path"].endswith("/test_protein_structure_result_worker.py"))}))
