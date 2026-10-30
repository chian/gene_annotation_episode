"""Record actual overlap Workflow evidence without declaring the tool finished."""
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
UPDATE = HERE / "PROGRESS_UPDATE_104.json"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_103.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

specifications = [
    ("result_host_2026-10-27_436", "attempt04", 19, [],
     "Earlier acquisition-evidence source: actual native/saved results, interruption, partial output, genuine zero and failed acquisition. Later completion/failure-scope changes have separate checks."),
    ("workflow_2026-10-27_437", "check003", 7,
     ["execution_episodes.py", "native_genomic_overlap_results.py"],
     "Complete scripted Workflow with real bedtools and production receipts; receipt module precedes the later narrow global-failure fallback."),
    ("result_host_2026-10-27_436", "attempt06", 2,
     ["native_genomic_overlap_results.py", "genomic_overlap_result_receipts.py"],
     "Current-source targeted global worker failure and requested-field failure scoping; not a repeat of the entire Workflow suite."),
]
checks, files = [], []
for packet, attempt_name, count, current_names, qualification in specifications:
    directory = ROOT / "verification" / ("tool_graders_genomic_overlap_" + packet) / attempt_name
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0
    assert receipt["metadata"]["policy"] == POLICY
    cgroup = receipt["metadata"]["verified_cgroup"]
    assert cgroup["memory_max"] == POLICY["memory_bytes"] and cgroup["memory_swap_max"] == 0
    assert cgroup["runtime_max"] == "infinity"
    assert receipt["executed_source_pins_unchanged"] and receipt["binary_pins_unchanged"]
    pins = read(directory / "source_pins_before.json")
    assert pins == read(directory / "source_pins_after.json")
    indexed = {pin["path"]: pin for pin in pins}
    for name in current_names:
        relative = "gene_annotation_episode/" + name
        assert sha(ROOT / relative) == indexed[relative]["sha256"], relative
    suite = ET.parse(directory / "junit.xml").getroot().find("testsuite")
    assert suite is not None
    assert {key: suite.attrib[key] for key in ("tests", "errors", "failures", "skipped")} == {
        "tests": str(count), "errors": "0", "failures": "0", "skipped": "0"}
    files.extend(directory / name for name in (
        "receipt.json", "junit.xml", "stdout.txt", "source_pins_before.json", "source_pins_after.json"))
    checks.append({"packet": packet, "attempt": attempt_name, "tests_passed": count,
        "tests_failed": 0, "qualification": qualification,
        "current_owner_files_verified": current_names,
        "elapsed_seconds": receipt["metadata"]["elapsed_seconds"],
        "checkout_changes_during_check": receipt.get("checkout_drift", [])})

workflow = ROOT / "verification/tool_graders_genomic_overlap_workflow_2026-10-27_437"
files.extend(workflow / name for name in ("REPORT.md", "EVIDENCE.json", "CONTRACT_AND_FIXTURES.md"))
summary = (
    "Actual scripted Workflow check003 passed all seven distinct checks with real bedtools, "
    "production capture/calculation, typed parent returns, saved-sheet recalculation after "
    "31 native/source files were removed, exact practical endpoints and closed replay. "
    "The invalid-C and missing-AC-output cases preserved independent comparisons and actual "
    "acquisition gain while leaving practical completion false. Earlier host attempt04 passed "
    "19 checks; current-source attempt06 passed two focused global-failure/requested-field "
    "checks. These receipts have separately recorded source versions and are not one combined "
    "final-source suite. Completion-only, saved-origin repair and frozen-credit-baseline "
    "verification are still running. Model-facing results and receiving-episode text remain "
    "unfinished. No new tool or resource binding enters the tally.")
evidence = {"id": "GENOMIC-OVERLAP-SCRIPTED-WORKFLOW-104",
    "kind": "actual_scripted_workflow_and_separately_pinned_host_checks",
    "summary": summary,
    "qualification": "Synthetic supplied inputs and scripted episode decisions; real bounded native execution and ordinary shared Workflow. No configured-model annotation, final prompt rendering, API or HPC claim.",
    "checks": checks,
    "reports": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for path in files]}
assert evidence["id"] not in {item["id"] for item in status["verification_evidence"]}
status["verification_evidence"].append(evidence)
tool_id = "B-L123-analyze_genomic_region_overlap"
row = next(item for item in status["rows"] if item["id"] == tool_id)
before = deepcopy(row)
row.update(overall="scripted_workflow_verified_final_host_and_presentation_unfinished",
    production_result_binding="actual_native_and_saved_result_paths_verified_final_host_cases_running",
    integration_verification="seven_actual_scripted_workflow_checks_passed_model_presentation_unfinished")
row["evidence_ids"].append(evidence["id"])
row["note"] += " Update104: " + summary
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != tool_id)
assert original["resource_bindings"] == status["resource_bindings"]
checklist = deepcopy(previous["work_item_states"])
for item in checklist:
    if item["id"] == "U05":
        item["current_evidence"] += " Update104: " + summary + " Counts remain112/308,42local,196outside."
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
    "remaining_fixed_rows_outside_tally": 196, "completed_work": [summary],
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
temporary = STATUS.with_name(".WORK_STATUS.104.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 0,
    "grader_tally": 112, "verified_local_bindings": 42, "remaining_rows": 196,
    "new_status_sha256": sha(STATUS)}))
