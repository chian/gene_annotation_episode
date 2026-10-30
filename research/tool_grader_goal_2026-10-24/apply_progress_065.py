"""Record reviewed VDB components without claiming a complete native tool."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_065.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(relative):
    return {"path": relative, "sha256": sha(ROOT / relative)}


if UPDATE.exists():
    raise RuntimeError("Immutable update already exists")
previous = json.loads((HERE / "PROGRESS_UPDATE_064.json").read_text())
before_sha = sha(STATUS)
assert before_sha == previous["new_status_sha256"]
scope_sha = sha(HERE / "SCOPE.json")
assert scope_sha == previous["scope_sha256_unchanged"]
status = json.loads(STATUS.read_text())
rows_before = deepcopy(status["rows"])
row_ids = [r["id"] for r in status["rows"]]
binding_ids = [r["id"] for r in status["resource_bindings"]]
bindings_before = deepcopy(status["resource_bindings"])
assert len(row_ids) == 308 and len(binding_ids) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 99
assert status["verified_bound_local_tool_mode_rows"] == 40
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
packet = "verification/tool_graders_blast_vdb_2026-10-26_312/"
receipt = json.loads((ROOT / packet / "check_007/receipt.json").read_text())
assert receipt["returncode"] == 0
assert receipt["metadata"]["policy"] == {
    "memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
assert receipt["source_sha256_before"] == receipt["source_sha256_after"]
for path, expected in receipt["source_sha256_after"].items():
    assert sha(ROOT / path) == expected, path
suites = list(ET.parse(ROOT / packet / "check_007/pytest.xml").getroot().iter("testsuite"))
assert len(suites) == 1
assert {k: int(suites[0].get(k)) for k in ("tests", "failures", "errors", "skipped")} == {
    "tests": 66, "failures": 0, "errors": 0, "skipped": 0}
assert json.loads((ROOT / packet / "example_export_002/receipt.json").read_text())["returncode"] == 0
examples = ROOT / packet / "example_export_002/examples"
manifest = json.loads((examples / "MANIFEST.json").read_text())
assert len(manifest["files"]) == 43
for item in manifest["files"]:
    path = examples / item["file"]
    assert sha(path) == item["sha256"] and path.stat().st_size == item["size_bytes"]
assert len(json.loads((examples / "SUMMARY.json").read_text())) == 17

evidence = {
    "id": "BLAST-VDB-FIELDS-FUNCTIONS-065",
    "kind": "pure_component_implementation_and_verification",
    "reports": [descriptor(packet + p) for p in (
        "CONTRACT_001.md", "CONTRACT_ADDENDUM_002.md", "CONTRACT_ADDENDUM_003.md",
        "ROOT_REVIEW_001.md", "check_007/receipt.json", "check_007/pytest.xml",
        "example_export_002/receipt.json", "example_export_002/examples/MANIFEST.json",
        "example_export_002/examples/SUMMARY.json")],
    "summary": "VDB fields, three deterministic metadata parsers, explicit binder, population function and component calculator implemented;66 tests and17 synthetic numerical examples checked by root.",
    "qualification": "No authentic native VDB search, configured resource binding, new dataset acquisition or complete episode return is verified. VDB function-weight model and missing native metadata adapters remain unfinished.",
}
assert not any(e["id"] == evidence["id"] for e in status["verification_evidence"])
status["verification_evidence"].append(evidence)
changes = []
for mode in ("blastn_vdb", "tblastn_vdb"):
    row = next(r for r in status["rows"] if r["id"] == "A-L070-" + mode + "-database")
    before = deepcopy(row)
    assert row["numerical_sheet"] == "vdb_hsp_member_feature_population_fields_defined_implementation_in_progress"
    row.update(
        overall="partial_fields_and_functions_verified_execution_and_episode_integration_pending",
        source_presence="new_vdb_population_parser_binder_calculator_files_inspected",
        numerical_sheet="vdb_hsp_member_sequence_sample_feature_population_fields_implemented_and_verified",
        native_parser="runinfo_exact_vdb_member_table_and_gbseq_parsers_synthetic_format_verified_authentic_vdb_output_pending",
        metadata_extractor="explicit_parent_member_feature_binding_and_saved_source_recheck_verified_other_native_adapters_pending",
        deterministic_calculator="geometry_codons_membership_taxonomy_quality_population_components_verified_vdb_function_model_pending",
        numerical_verification="66_passing_cases_17_synthetic_examples_and_shared_native_geometry_checked",
        production_result_binding="not_implemented_for_these_new_mode_components",
        integration_verification="new_mode_selected_execution_to_requested_episode_return_not_verified",
        live_resource_verification="no_new_mode_database_execution_no_authentic_mode_fixture_claim",
    )
    row["evidence_ids"].append(evidence["id"])
    row["note"] += " Update065: fields and population/parser/binder/calculator functions reviewed with66 passing tests. Unavailable-report zeros and repeated-feature aggregation corrected. Synthetic examples verify implementation, not native execution. Function model, authentic modes, source acquisition and complete episode returns remain pending; no tally increment."
    changes.append({"group": "rows", "id": row["id"], "before": before, "after": deepcopy(row)})

changed_ids = {c["id"] for c in changes}
assert all(before == after for before, after in zip(rows_before, status["rows"]) if before["id"] not in changed_ids)
assert [r["id"] for r in status["rows"]] == row_ids
assert [r["id"] for r in status["resource_bindings"]] == binding_ids
assert status["resource_bindings"] == bindings_before
assert sha(HERE / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(),
    "scope_sha256_unchanged": scope_sha, "scope_changes": [],
    "changes": changes, "added_evidence": [evidence],
    "verification": [{"packet": packet, "test_receipt": packet + "check_007/receipt.json",
        "tests_passed": 66, "synthetic_sheet_component_examples": 17,
        "native_mode_search_executed": False, "episode_path_verified": False}],
    "numerical_grader_progress_tally": {"before": 99, "after": 99, "added_row_ids": [],
        "meaning": "Verified VDB components do not complete the remaining native extraction/function-model and tool execution/return work."},
    "verified_bound_local_tool_mode_rows": {"before": 40, "after": 40},
    "remaining_fixed_rows_outside_tally": 209,
    "completed_work": [
        "VDB field definitions and six pure population/parser/binder/calculator exports implemented and reviewed.",
        "66 tests, source identity checks and43 generated example files verified; no new native VDB execution claimed.",
        "Population availability/completeness, repeated-feature unions and assignment-scope regression fixes verified."
    ],
    "unfinished_work": [
        "Native database producer313 remains in implementation/testing; no deployment or selected HPC job verified.",
        "Result/metadata/projection contract314 remains in preparation before integration coding.",
        "Authentic mode outputs, native membership/convergence extractors, remaining metadata adapters and VDB function model remain unfinished.",
        "Selected child execution, complete capture and authenticated typed episode returns remain unfinished for the new modes.",
        "All other fixed308-row work remains as previously recorded."
    ],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"],
}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.065.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"changed_progress_rows": 2, "scope_rows": 308, "resource_bindings": 288,
    "numerical_grader_progress_tally": 99, "new_status_sha256": sha(STATUS)}))
