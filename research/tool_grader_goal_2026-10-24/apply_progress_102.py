"""Record overlap execution components; preserve unfinished whole-tool accounting."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_102.json"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_101.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

# Each selected historical snapshot remains its own verification. Only the
# named current owners are required to match current source; later contract
# extensions do not retroactively change older native receipts.
specifications = [
    ("execution_contracts_2026-10-27_426", "check002", 104, 0, "REPORT.md",
     ["native_genomic_overlap_tool_info.py"]),
    ("native_driver_2026-10-27_427", "check005", 65, 0, "REPORT.md",
     ["native_genomic_overlap_driver.py", "native_genomic_overlap_local.py"]),
    ("input_authority_2026-10-27_430", "check002", 57, 0, "HANDOFF.md",
     ["genomic_overlap_operands.py"]),
    ("analytic_availability_2026-10-27_431", "check001", 192, 0, "HANDOFF.md",
     ["genomic_overlap_inputs.py", "genomic_overlap_calculations.py", "genomic_overlap_result_views.py"]),
    ("shared_2026-10-27_429", "check004", 188, 1, "REPORT.md", []),
    ("shared_2026-10-27_429", "check005", 1, 0, "REPORT.md",
     ["execution_episodes.py", "execution_progress.py", "practical_execution_records.py",
      "practical_execution_operations.py", "native_genomic_overlap_observations.py",
      "native_genomic_overlap_contracts.py"]),
]
reports, checks = [], []
for packet, attempt_name, total, failures, report, current_names in specifications:
    base = ROOT / "verification" / ("tool_graders_genomic_overlap_" + packet)
    attempt = base / attempt_name
    receipt = read(attempt / "receipt.json")
    assert receipt["returncode"] == (1 if failures else 0)
    assert receipt["metadata"]["policy"] == POLICY
    group = receipt["metadata"]["verified_cgroup"]
    assert group["memory_max"] == POLICY["memory_bytes"] and group["memory_swap_max"] == 0
    assert group["runtime_max"] == "infinity"
    assert receipt["executed_source_pins_unchanged"] and not receipt["checkout_source_drift"]
    pins = read(attempt / "source_pins_before.json")
    assert pins == read(attempt / "source_pins_after.json") == read(attempt / "checkout_source_pins_after.json")
    indexed = {pin["path"]: pin for pin in pins}
    for name in current_names:
        relative = "gene_annotation_episode/" + name
        assert sha(ROOT / relative) == indexed[relative]["sha256"]
    if "binary_pins_unchanged" in receipt:
        assert receipt["binary_pins_unchanged"]
        assert read(attempt / "binary_pins_before.json") == read(attempt / "binary_pins_after.json")
    suite = ET.parse(attempt / "pytest.xml").getroot().find("testsuite")
    assert suite is not None
    assert {k: suite.attrib[k] for k in ("tests", "errors", "failures", "skipped")} == {
        "tests": str(total), "errors": "0", "failures": str(failures), "skipped": "0"}
    reports.extend([base / report] + [attempt / name for name in (
        "receipt.json", "pytest.xml", "stdout.txt", "source_pins_before.json", "source_pins_after.json")])
    checks.append({"packet": packet, "attempt": attempt_name,
        "tests_passed": total - failures, "tests_failed": failures,
        "elapsed_seconds": receipt["metadata"]["elapsed_seconds"]})

summary = (
    "Fixed execution records and tool information passed104 tests; native local driver passed65 "
    "tests with actual bedtools bytes, interruption and mixed-empty publication cases; actual "
    "Store/receipt input authority passed57 tests. Shared registration, native hooks and original "
    "pair-seal validation passed187 checks with one test-only frozen-value assertion failure; "
    "its corrected commissioning check passed separately (1 targeted test). Current input-loss "
    "semantics passed192 pure/projection tests: intact AB retains I5/U15/J1/3; AC/BC requiring "
    "lost C maps return unavailable, without rewriting original analytic-empty facts. Saved "
    "threshold4 still selects1 AB pair/5bp. All reported executions retain their own unchanged "
    "source pins. Results-worker custody, host result admission and full Workflow verification "
    "remain unfinished. No new complete tool or accepted resource binding is counted.")
evidence = {
    "id": "GENOMIC-OVERLAP-NATIVE-AUTHORITY-SHARED-102",
    "kind": "native_execution_and_shared_boundary_component_verification",
    "summary": summary,
    "qualification": "Separate retained snapshots and tests, including one failed assertion corrected by a targeted rerun; not one combined passing suite or a full Workflow result.",
    "checks": checks,
    "reports": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in dict.fromkeys(reports)],
}
assert evidence["id"] not in {item["id"] for item in status["verification_evidence"]}
status["verification_evidence"].append(evidence)
tool_id = "B-L123-analyze_genomic_region_overlap"
row = next(r for r in status["rows"] if r["id"] == tool_id)
before = deepcopy(row)
row.update(overall="native_and_shared_components_verified_results_and_workflow_unfinished",
    tool_information="implemented_exact_four_field_local_operation_information",
    invocation_contract="implemented_native_local_preparation_and_shared_commissioning_verified",
    numerical_sheet="implemented_supplied_data_and_current_input_loss_verified",
    native_parser="implemented_native_format_partial_and_input_loss_cases_verified",
    metadata_extractor="implemented_exact_reference_joins_and_received_input_authority_verified",
    deterministic_calculator="implemented_numerical_cases_and_saved_recalculation_verified",
    production_result_binding="worker_and_host_result_custody_and_typed_delivery_unfinished",
    numerical_verification="192_pure_projection_and_input_loss_tests_passed",
    integration_verification="native_and_shared_commissioning_boundaries_verified_full_workflow_unfinished",
    live_resource_verification="local_canonical_token_bedtools_execution_and_interruption_verified")
row["evidence_ids"].append(evidence["id"])
row["note"] += " Update102: " + summary
changes = [{"id": tool_id, "before": before, "after": deepcopy(row)}]
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != tool_id)
assert original["resource_bindings"] == status["resource_bindings"]
checklist = deepcopy(previous["work_item_states"])
for item in checklist:
    if item["id"] == "U05":
        item["current_evidence"] += " Update102: " + summary + " Count112/308,42local bindings,196remaining unchanged."
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": changes, "resource_binding_changes": [], "added_evidence": [evidence],
    "numerical_grader_progress_tally": {"before": 112, "after": 112, "added_row_ids": [],
        "meaning": previous["numerical_grader_progress_tally"]["meaning"]},
    "verified_bound_local_tool_mode_rows": {"before": 42, "after": 42},
    "remaining_fixed_rows_outside_tally": 196, "completed_work": [summary],
    "findings_requiring_repair": deepcopy(previous["findings_requiring_repair"]),
    "work_item_states": checklist,
    "unfinished_work": [x["current_evidence"] for x in checklist if x["status"] != "complete"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"],
}
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.102.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 0,
    "grader_tally": 112, "verified_local_bindings": 42, "remaining_rows": 196,
    "new_status_sha256": sha(STATUS)}))
