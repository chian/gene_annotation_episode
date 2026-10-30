"""Record verified overlap numerical components without counting a bound tool."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_101.json"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_100.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]

reports, checks = [], []
for packet, count, report in (
    ("tool_graders_genomic_overlap_pure_2026-10-27_423", 96, "REPORT.md"),
    ("tool_graders_genomic_overlap_projection_2026-10-27_424", 41, "REPORT_002.md"),
):
    base = ROOT / "verification" / packet
    attempt = base / "check003"
    receipt = read(attempt / "receipt.json")
    assert receipt["returncode"] == 0
    assert receipt["metadata"]["policy"] == POLICY
    group = receipt["metadata"]["verified_cgroup"]
    assert group["memory_max"] == POLICY["memory_bytes"] and group["memory_swap_max"] == 0
    assert group["runtime_max"] == "infinity"
    assert receipt["executed_source_pins_unchanged"] and not receipt["checkout_source_drift"]
    pins = read(attempt / "source_pins_before.json")
    assert pins == read(attempt / "source_pins_after.json") == read(attempt / "checkout_source_pins_after.json")
    for pin in pins:
        if pin["path"].startswith(("gene_annotation_episode/genomic_overlap_", "tests/test_genomic_overlap_")):
            assert sha(ROOT / pin["path"]) == pin["sha256"]
    suite = ET.parse(attempt / "pytest.xml").getroot().find("testsuite")
    assert suite is not None
    assert {key: suite.attrib[key] for key in ("tests", "errors", "failures", "skipped")} == {
        "tests": str(count), "errors": "0", "failures": "0", "skipped": "0"}
    reports.extend([base / report] + [attempt / name for name in (
        "receipt.json", "pytest.xml", "stdout.txt", "source_pins_before.json", "source_pins_after.json")])
    checks.append({"packet": packet, "attempt": "check003", "tests_passed": count,
                   "elapsed_seconds": receipt["metadata"]["elapsed_seconds"]})

summary = (
    "423 check003 passed96 tests for supplied-input/native-table parsing, numerical sheets, "
    "reference extraction and deterministic calculation. 424 check003 passed41 projection tests "
    "including the actual joined reader/calculator path on the same final source pins. Exact "
    "example: pairwise width sum8bp, shared union5bp, combined union15bp, Jaccard5/15. "
    "Saved threshold4 selects1pair/5bp without acquisition, rerunning intersection or altering "
    "prior components. All executed sources remained unchanged. Native421 token-remapped "
    "fixtures are explicitly derived, not new canonical-token native execution. Native binding, "
    "artifact custody, results worker and full episode delivery remain unfinished.")
evidence = {
    "id": "GENOMIC-OVERLAP-PURE-NUMERICS-PROJECTION-101",
    "kind": "supplied_data_numerical_and_selected_projection_verification",
    "summary": summary,
    "qualification": "Pure components only. No new whole-tool, live canonical-token execution, resource binding, custody or complete Workflow claim. Existing source declarations of completeness remain supplied assertions.",
    "checks": checks,
    "reports": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in reports],
}
assert evidence["id"] not in {item["id"] for item in status["verification_evidence"]}
status["verification_evidence"].append(evidence)
tool_id = "B-L123-analyze_genomic_region_overlap"
row = next(r for r in status["rows"] if r["id"] == tool_id)
before = deepcopy(row)
row.update(overall="pure_numerical_components_and_projection_verified_native_binding_unfinished",
           numerical_sheet="implemented_supplied_data_verified",
           native_parser="implemented_native_format_and_partial_cases_verified",
           metadata_extractor="implemented_exact_source_and_reference_joins_verified",
           deterministic_calculator="implemented_numerical_cases_and_saved_recalculation_verified",
           numerical_verification="96_pure_tests_and_41_projection_tests_passed",
           integration_verification="pure_reader_calculator_projection_join_verified_episode_path_unfinished")
row["evidence_ids"].append(evidence["id"])
row["note"] += " Update101: " + summary + " Complete-tool count unchanged."
changes = [{"id": tool_id, "before": before, "after": deepcopy(row)}]
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != tool_id)
assert original["resource_bindings"] == status["resource_bindings"]
checklist = deepcopy(previous["work_item_states"])
for item in checklist:
    if item["id"] == "U05":
        item["current_evidence"] += " Update101: " + summary + " Count112/308,42local bindings,196remaining unchanged."
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": changes, "resource_binding_changes": [],
    "added_evidence": [evidence],
    "numerical_grader_progress_tally": {"before": 112, "after": 112, "added_row_ids": [],
        "meaning": previous["numerical_grader_progress_tally"]["meaning"]},
    "verified_bound_local_tool_mode_rows": {"before": 42, "after": 42},
    "remaining_fixed_rows_outside_tally": 196,
    "completed_work": [summary],
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
temporary = STATUS.with_name(".WORK_STATUS.101.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 0,
    "grader_tally": 112, "verified_local_bindings": 42, "remaining_rows": 196,
    "new_status_sha256": sha(STATUS)}))
