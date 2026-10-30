"""Record verified chromatin boundaries; preserve scope and completion counts."""
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
UPDATE = HERE / "PROGRESS_UPDATE_107.json"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_106.json")
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
    ("tool_graders_chromatin_return_views_2026-10-27_445/check005", 23, 0, "junit.xml"),
    ("tool_graders_chromatin_received_returns_2026-10-27_449/check001", 78, 6, "pytest.xml"),
    ("tool_graders_chromatin_received_returns_2026-10-27_449/check002", 6, 0, "pytest.xml"),
    ("tool_graders_chromatin_selected_inputs_2026-10-27_450/check003", 129, 0, "junit.xml"),
    ("tool_graders_chromatin_result_receipts_2026-10-27_448/check003", 24, 0, "junit.xml"),
]
checks, reports, received_outcomes = [], [], {}
for relative, passed, failed, xml_name in cases:
    directory = ROOT / "verification" / relative
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == (1 if failed else 0)
    assert receipt.get("executed_source_pins_unchanged", receipt.get("source_pins_unchanged")) is True
    assert receipt["metadata"]["policy"] == {
        "memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    group = receipt["metadata"]["verified_cgroup"]
    assert group["memory_max"] == 21474836480 and group["memory_swap_max"] == 0
    assert group["runtime_max"] == "infinity"
    suite = ET.parse(directory / xml_name).getroot().find("testsuite")
    assert suite is not None
    assert int(suite.attrib["tests"]) == passed + failed
    assert int(suite.attrib["failures"]) == failed
    assert suite.attrib["errors"] == suite.attrib["skipped"] == "0"
    if "_449/" in relative:
        for case in suite.findall("testcase"):
            key = (case.attrib["classname"], case.attrib["name"])
            received_outcomes[key] = case.find("failure") is None
    files = [directory / name for name in (
        "receipt.json", "source_pins_before.json", "source_pins_after.json", xml_name, "stdout.txt")]
    reports.extend({"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for path in files)
    checks.append({"attempt": relative, "tests_passed": passed, "tests_failed": failed,
        "scope": "component_or_shared_boundary_not_complete_workflow",
        "checkout_changes_during_check": receipt.get("checkout_drift", [])})
assert len(received_outcomes) == 84 and all(received_outcomes.values())
for name, expected in {
    "chromatin_interaction_returns.py": "982bcd4765d81d30c35f017120d663ef1b4b48576184c6c295be3919f5a8f1c9",
    "chromatin_interaction_operands.py": "6d8b0c8b90d9f7674923f5446cb422387d8a74eb0630bd3a784556800d4547b0",
}.items():
    assert sha(ROOT / "gene_annotation_episode" / name) == expected

summary = (
    "Chromatin selected-input validation passed129 final focused tests; exact received-return "
    "validation passed84 distinct cases across two retained attempts (78pass6fixture failures, "
    "then6pass after fixture-only corrections). Shared resource/result-selection registration "
    "passed23 tests, including repeated byte identities with different input roles and RNA/chromatin "
    "schema coexistence. Results receipts passed24 core tests at their recorded snapshot; final "
    "refinement checks remain in progress and are not claimed here. Root reviewed the complete "
    "selected-input and received-return production helpers. The fresh451 full Workflow verifier "
    "is implementing original acquisition, requested-only parent return, saved recalculation, "
    "partial results, credit, practical completion and closed replay under the existing011 "
    "contract. No complete chromatin Workflow pass is claimed. HIC, model-facing text, further "
    "native coverage and live HPC remain unfinished. Protein and genomic-overlap messages/operands, "
    "historical failures and all other fixed-scope work remain open. Counts remain112/308,42local,196outside.")
evidence = {"id": "CHROMATIN-INPUTS-RETURNS-SHARED-107",
    "kind": "separately_pinned_component_and_shared_boundary_checks",
    "summary": summary, "checks": checks, "reports": reports}
assert evidence["id"] not in {item["id"] for item in status["verification_evidence"]}
status["verification_evidence"].append(evidence)
tool_id = "B-L124-analyze_chromatin_interactions"
row = next(item for item in status["rows"] if item["id"] == tool_id)
before = deepcopy(row)
row.update(
    invocation_contract="shared_registration_and_selected_input_checks_passed_full_workflow_unfinished",
    production_result_binding="native_worker_and_receipt_components_verified_final_join_and_workflow_unfinished",
    integration_verification="input_return_and_resource_selection_boundaries_passed_full_workflow_unfinished")
row["evidence_ids"].append(evidence["id"])
row["note"] += " Update107: " + summary
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != tool_id)
assert original["resource_bindings"] == status["resource_bindings"]
checklist = deepcopy(previous["work_item_states"])
for item in checklist:
    if item["id"] == "U05":
        item["current_evidence"] += " Update107: " + summary
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
findings = deepcopy(previous["findings_requiring_repair"])
stale = "410 complete Workflow remains in progress; no final full-path pass claimed."
assert stale in findings
findings[findings.index(stale)] = (
    "Correction to the stale410 status repeated in106: update100 already recorded4 complete "
    "scripted Workflow passes at their earlier source snapshot. Current protein receiver text, "
    "decision operands and final shared integration review remain unfinished.")
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
    "completed_work": [
        "Chromatin selected-input validation:129 final focused tests passed.",
        "Chromatin received-return validation:84 distinct cases passed across two retained attempts.",
        "Shared resource/result selection:23 focused tests passed.",
        "Results receipt core:24 tests passed at recorded snapshot; later refinements still under verification."],
    "findings_requiring_repair": findings, "work_item_states": checklist,
    "unfinished_work": [x["current_evidence"] for x in checklist if x["status"] != "complete"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.107.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 0,
    "grader_tally": 112, "verified_local_bindings": 42, "remaining_rows": 196,
    "new_status_sha256": sha(STATUS)}))
