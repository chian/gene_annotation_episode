"""Copy existing verification records and their measured fields; no science runs."""
from pathlib import Path
from collections import Counter
import hashlib
import json

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
run = PACKET / "check003"
tree = run / "temporary/pytest"


def save(name, value):
    (PACKET / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def artifact(store, reference):
    checksum = reference.removeprefix("artifact_")
    path = store / "artifacts" / checksum[:2] / checksum
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == checksum
    return raw


pins = json.loads((run / "source_pins_before.json").read_bytes())
required = {
    "gene_annotation_episode/native_protein_structure_preparation.py",
    "tests/test_native_protein_structure_preparation.py",
    "gene_annotation_episode/protein_structure_result_worker.py",
    "gene_annotation_episode/native_protein_structure_acquisition.py",
    "gene_annotation_episode/native_lifecycle.py", "gene_annotation_episode/local_jobs.py",
    "gene_annotation_episode/_local_job_worker.py", "gene_annotation_episode/materials.py",
    "gene_annotation_episode/state.py", "gene_annotation_episode/execution_contracts.py",
    "gene_annotation_episode/protein_structure_contracts.py",
    "gene_annotation_episode/native_protein_structure_contracts.py",
    "gene_annotation_episode/protein_structure_sheet.py",
    "gene_annotation_episode/protein_structure_calculations.py",
}
selected = [row for row in pins if row["path"] in required or row["path"].startswith(
    "verification/tool_graders_protein_structure_shared_contract_2026-10-27_380/")]
assert required <= {row["path"] for row in selected}
save("SOURCE_PINS_001.json", {"executed_run": "check003", "files": selected,
    "all_executed_pins": "check003/source_pins_before.json",
    "after_run_pins": "check003/source_pins_after.json",
    "actual_imports": "check003/executed_imports.json"})

sample = tree / "test_original_and_changed_save0/filled-example.json"
raw = sample.read_bytes()
(PACKET / "FILLED_OUTPUT_MANIFEST_001.json").write_bytes(raw)
views = json.loads(raw)
store = sample.parent / "store"
examples = {}
for label, view in views.items():
    result = view["result"]
    components = json.loads(artifact(store, result["components_file"]["file_identity"]["artifact_ref"]))
    handle = json.loads(artifact(store, view["execution"]["handle_artifact_ref"]))
    examples[label] = {"unit": handle["unit"], "command": handle["command"],
        "worker_result_artifact_ref": view["prepared"]["worker_result_artifact_ref"],
        "sheet_file": result["sheet_file"], "components_file": result["components_file"],
        "fit_used_count": components["counts"]["fit_used_count"],
        "evaluation_used_count": components["counts"]["evaluation_used_count"],
        "evaluation_sse": components["evaluation"]["evaluation_sse"],
        "evaluation_rmsd": components["evaluation"]["evaluation_rmsd"],
        "evaluation_mean_distance": components["evaluation"]["evaluation_mean_distance"],
        "site_measurements": components["site_measurements"],
        "execution_metadata": view["execution"]["metadata"]}
assert examples["original"]["sheet_file"]["file_identity"] == examples["saved"]["sheet_file"]["file_identity"]
save("FILLED_EXAMPLES_001.json", {"qualification": "synthetic_native_format_engineering_fixture",
    "source_record": str(sample.relative_to(REPO)), "store": str(store.relative_to(REPO)),
    "expected_original": "four fit pairs, one held-out evaluation; distance/RMSD2 angstrom, SSE4 angstrom_squared",
    "expected_saved": "same four fit pairs, five evaluations; RMSD sqrt(4/5) angstrom; original sheet/baseline unchanged",
    "examples": examples})

records = []
for path in sorted(tree.rglob("prepared.json")):
    if path.is_symlink():
        continue  # Deliberate preflight fault, not a prepared record.
    relative = path.relative_to(tree)
    original_store = tree / relative.parts[0] / "store"
    prepared = json.loads(path.read_bytes())
    execution = json.loads(artifact(original_store, prepared["execution_receipt_artifact_ref"]))
    retained_fault = None
    try:
        result = (json.loads(artifact(original_store, prepared["worker_result_artifact_ref"]))
                  if prepared["worker_result_artifact_ref"] is not None else None)
    except (FileNotFoundError, AssertionError, json.JSONDecodeError) as error:
        result, retained_fault = None, type(error).__name__
    records.append({"prepared_path": str(path.relative_to(REPO)), "execution": execution,
        "worker_result_artifact_ref": prepared["worker_result_artifact_ref"],
        "scientific_state": result["state"] if result is not None else None,
        "intentional_retained_fault": retained_fault,
        "host_issues": prepared["issues"], "diagnostic_files": prepared["diagnostic_files"]})
save("RETAINED_EXECUTIONS_001.json", {"records": records,
    "note": "Terminal resource/execution AcquisitionError cases are explicitly injected fixtures on actual completed worker handles. The nonzero CLI exit is actual. Lost retained-byte cases intentionally damage their own test Store artifacts."})

runs = []
for name, count, seconds in (("check001", 9, 42.11), ("check002", 73, 193.96), ("check003", 81, 242.56)):
    receipt = json.loads((PACKET / name / "receipt.json").read_bytes())
    assert receipt["returncode"] == 0 and receipt["executed_source_pins_unchanged"]
    runs.append({"run": name, "passed": count, "failed": 0, "pytest_seconds": seconds, "receipt": receipt})
save("VERIFICATION_001.json", {"runs": runs, "final_unique_test_count": 81,
    "overlapping_counts_must_not_be_added": True, "failed_pytest_attempts": 0,
    "claim_limit": "bounded result-preparation and retained-only custody; no source publication, receipt authority, selected projection or complete episode-path proof",
    "immutable_goal_sha256": "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"})
print(json.dumps({"final_tests": 81, "retained_final_execution_records": len(records),
    "outcomes": dict(Counter(row["execution"]["outcome"] for row in records)),
    "original_rmsd": examples["original"]["evaluation_rmsd"]["value"],
    "original_sse": examples["original"]["evaluation_sse"]["value"],
    "saved_rmsd": examples["saved"]["evaluation_rmsd"]["value"]}))
