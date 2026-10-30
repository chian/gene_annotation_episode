"""Record chromatin component evidence without counting a complete tool."""
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
UPDATE = HERE / "PROGRESS_UPDATE_106.json"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_105.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

cases = [
    ("tool_graders_chromatin_inputs_sheet_2026-10-27_442/tests_attempt6", 27, "unittest"),
    ("tool_graders_chromatin_calculations_projection_2026-10-27_443/check004", 54, "pytest"),
    ("tool_graders_chromatin_calculations_projection_2026-10-27_443/check005", 12, "pytest"),
    ("tool_graders_chromatin_calculations_projection_2026-10-27_443/check006", 10, "pytest"),
    ("tool_graders_chromatin_native_execution_2026-10-27_444/check005", 10, "pytest_stdout"),
    ("tool_graders_chromatin_return_views_2026-10-27_445/check003", 58, "pytest"),
]
checks, reports = [], []
for relative, expected, kind in cases:
    directory = ROOT / "verification" / relative
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0
    assert receipt.get("executed_source_pins_unchanged", receipt.get("source_pins_unchanged")) is True
    assert receipt["metadata"]["policy"] == {
        "memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    group = receipt["metadata"]["verified_cgroup"]
    assert group["memory_max"] == 21474836480 and group["memory_swap_max"] == 0
    assert group["runtime_max"] == "infinity"
    files = [directory / "receipt.json", directory / "source_pins_before.json",
        directory / "source_pins_after.json"]
    if kind == "unittest":
        result = read(directory / "TEST_RESULT.json")
        assert result == {"tests_run": expected, "failures": 0, "errors": 0, "successful": True}
        files.append(directory / "TEST_RESULT.json")
    elif kind == "pytest":
        suite = ET.parse(directory / "junit.xml").getroot().find("testsuite")
        assert suite is not None
        assert suite.attrib["tests"] == str(expected)
        assert all(suite.attrib[key] == "0" for key in ("failures", "errors", "skipped"))
        files.extend([directory / "junit.xml", directory / "stdout.txt"])
    else:
        assert f"{expected} passed in " in (directory / "stdout.txt").read_text()
        files.append(directory / "stdout.txt")
    reports.extend({"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for path in files)
    checks.append({"attempt": relative, "tests_passed": expected,
        "checkout_changes_during_check": receipt.get("checkout_drift", []),
        "scope": "component_or_shared_state_check_not_complete_workflow"})

summary = (
    "Chromatin component work is implemented and recorded without adding a tool: C1 input/sheet "
    "checks passed27 against actual synthetic Cooler HDF5; C2 full focused suite passed54, followed "
    "by separately pinned12 and10 targeted checks for final changes. These are overlapping groups, "
    "not76 unique final-source tests. C3 native producer/retained worker checks passed10, including "
    "raw6/mean4/fold1.5, weighted mean7/fold6/7, insulation, saved recalculation, partial interruption "
    "and real PracticalState reservation recovery. Its shared LocalPracticalOperations path and "
    "later capture-loss fixes are still being verified. Root return/communication/practical-state "
    "check003 passed58 with unchanged executed pins. Shared local start/status/collect, bounded "
    "observation and target-authentication branches are written; complete results custody, received "
    "operands, full Workflow and model-facing text remain unfinished. Final C1/C2 code review remains "
    "open. HIC and large-scale/biological native coverage remain unfinished. No new tool or resource "
    "binding enters the tally. Earlier genomic-overlap presentation, protein messages/operands, "
    "historical failures and all remaining fixed-scope work stay open.")
evidence = {"id": "CHROMATIN-COMPONENTS-SHARED-RETURN-106",
    "kind": "separately_pinned_component_and_shared_boundary_checks",
    "summary": summary, "checks": checks, "reports": reports}
assert evidence["id"] not in {item["id"] for item in status["verification_evidence"]}
status["verification_evidence"].append(evidence)
tool_id = "B-L124-analyze_chromatin_interactions"
row = next(item for item in status["rows"] if item["id"] == tool_id)
before = deepcopy(row)
row.update(overall="component_checks_passed_shared_integration_unfinished",
    source_presence="upstream_source_inspected_replacement_modules_written",
    tool_information="local_information_written_final_review_pending",
    invocation_contract="shared_practical_registration_written_verification_in_progress",
    numerical_sheet="implemented_native_component_checks_passed_root_review_pending",
    native_parser="cooler_schema3_component_checks_passed_hic_unfinished",
    metadata_extractor="implemented_component_joins_verified_root_review_pending",
    deterministic_calculator="implemented_component_checks_passed_root_review_pending",
    production_result_binding="native_worker_verified_shared_result_and_parent_paths_unfinished",
    numerical_verification="separately_pinned_native_component_and_saved_recalculation_checks_passed",
    integration_verification="typed_return_and_practical_state_checks_passed_full_workflow_unfinished",
    live_resource_verification="local_native_component_checks_passed_complete_route_unfinished")
row["evidence_ids"].append(evidence["id"])
row["note"] += " Update106: " + summary
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != tool_id)
assert original["resource_bindings"] == status["resource_bindings"]
checklist = deepcopy(previous["work_item_states"])
for item in checklist:
    if item["id"] == "U05":
        item["current_evidence"] += " Update106: " + summary + " Counts remain112/308,42local,196outside."
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": [{"id": tool_id, "before": before, "after": deepcopy(row)}],
    "resource_binding_changes": [], "added_evidence": [evidence],
    "numerical_grader_progress_tally": {"before": 112, "after": 112, "added_row_ids": [],
        "meaning": previous["numerical_grader_progress_tally"]["meaning"]},
    "verified_bound_local_tool_mode_rows": {"before": 42, "after": 42},
    "remaining_fixed_rows_outside_tally": 196,
    "completed_work": ["Shared chromatin fact schemas and reference/relationship validation registered; 58 selected shared checks passed."],
    "findings_requiring_repair": deepcopy(previous["findings_requiring_repair"]),
    "work_item_states": checklist,
    "unfinished_work": [x["current_evidence"] for x in checklist if x["status"] != "complete"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.106.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 0,
    "grader_tally": 112, "verified_local_bindings": 42, "remaining_rows": 196,
    "new_status_sha256": sha(STATUS)}))
