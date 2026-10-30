"""Record verified schema resource preparation without accepting another tool."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_099.json"
PACKET = ROOT / "verification/tool_graders_protein_structure_schema_resources_2026-10-27_417"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_098.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]
assert sha(ROOT / "gene_annotation_episode/native_protein_structure_contracts.py") == "44e7308e77e0e6fdcc25cdf4bfa1448037150875c40284ae13ecfe668fc81774"

reports = []
for attempt in ("check001", "profile001", "analysis001"):
    directory = PACKET / attempt
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0 and receipt["executed_source_pins_unchanged"]
    if attempt != "analysis001":
        assert not receipt["checkout_source_drift"]
        assert receipt["metadata"]["policy"] == {
            "memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
        assert receipt["metadata"]["verified_cgroup"]["memory_swap_max"] == 0
    reports.append(directory / "receipt.json")
assert "133 passed in 54.30s" in (PACKET / "check001/stdout.txt").read_text()
assert read(PACKET / "profile001/receipt.json")["retained_input_pins_unchanged"]
comparison = read(PACKET / "analysis001/comparison.json")
assert comparison["diagnostic_outcomes_identical"] and comparison["stdout_identical"]
assert comparison["retained_input_identity_all_four_manifests_equal"]
assert comparison["retained_input_root_identical"]
assert comparison["baseline_and_existing_test_files_unchanged"]
assert comparison["baseline_and_existing_test_file_count"] == 3104
assert all(record["identical"] for record in comparison["exact_record_comparison"].values())
assert comparison["returned_parent_report_serialized"] is False
functions = {row["function"]: row for row in comparison["function_comparison"]}
for function, count in {
    "native_protein_structure_contracts.py:_checked": 293,
    "native_protein_structure_contracts.py:validate_protein_structure_request": 125,
    "native_protein_structure_contracts.py:validate_protein_structure_job": 58,
    "native_protein_structure_returns.py:_commission": 37,
    "native_protein_structure_returns.py:authenticate": 17,
    "episode_return_records.py:authenticate": 54,
    "protein_structure_result_receipts.py:completed_receipts": 3,
    "native_protein_structure_results.py:_verify_artifacts": 1,
    "native_protein_structure_results.py:_bytes": 4,
}.items():
    assert functions[function]["before"]["total_calls"] == count
    assert functions[function]["after"]["total_calls"] == count
assert functions["_core.py:crawl"]["before"]["total_calls"] == 294
assert functions["_core.py:crawl"]["after"]["total_calls"] == 8
reports.extend(PACKET / name for name in (
    "REPORT_001.md", "VERIFICATION_001.json", "SOURCE_PINS_001.json",
    "PRODUCTION_DIFF_001.patch", "HARNESS_EQUALITY_001.json", "COMMANDS.md",
    "check001/stdout.txt", "profile001/diagnostic.json", "analysis001/comparison.json",
    "analysis001/baseline_preservation.json"))
reports.append(ROOT / "verification/tool_graders_protein_structure_shared_contract_2026-10-27_380/SCHEMA_RESOURCE_PREPARATION_CONTRACT_027.md")

summary = ("417 prepares the private fixed schema resources once through public Registry/Resource APIs. "
    "All 133 checks passed: 48 new cases and 85 existing cases. The unchanged actual retained-admission "
    "diagnostic stayed accepted; registry crawls fell from 294 to 8 and profiled wall time from "
    "32.511627 to 23.840324 seconds. All 293 payload checks and original authority/current-byte checks "
    "remain. Full 410 Workflow and receiver integration are unfinished; 112/308 is unchanged.")
item = {
    "id": "PROTEIN-SCHEMA-RESOURCE-PREPARATION-099",
    "kind": "component_and_actual_retained_admission_verification_full_workflow_open",
    "summary": summary,
    "qualification": ("133 tests include real local workers/lifecycle on synthetic structures, not "
        "configured-model science. The profile reuses exact original retained authority and actual "
        "resolver/semantic callbacks; no native science is rerun. The admitted form, facts and retained "
        "inputs match exactly, but the returned ParentReport object is not separately serialized. "
        "Profile overhead is included; this does not establish full Workflow speedup or completion. "
        "The running 410 proof retains its older frozen sources. Receiver text and decision operand "
        "integration, prior failures and all unfinished tool rows remain open."),
    "reports": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                for path in sorted(set(reports))],
}
assert item["id"] not in {entry["id"] for entry in status["verification_evidence"]}
status["verification_evidence"].append(item)
protein_id = "B-L107-compare_protein_structures"
changes, binding_changes = [], []
for row in status["rows"]:
    if row["id"] == protein_id:
        before = deepcopy(row)
        row["evidence_ids"].append(item["id"])
        row["note"] += (" Update099: 417 fixed-schema resource preparation passed 133 checks, including "
            "all 85 prior cases. The same retained admission stayed accepted with registry crawls "
            "294→8 and profiled wall time 32.51→23.84s; payload, authority and current-byte checks "
            "remain. Full 410 completion and receiver text/operand integration stay open. No tool "
            "or resource-binding count is added.")
        changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
for row in status["resource_bindings"]:
    if row["id"] == protein_id + "::local":
        before = deepcopy(row)
        row["evidence_ids"].append(item["id"])
        binding_changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
assert len(changes) == len(binding_changes) == 1
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != protein_id)
assert all(a == b for a, b in zip(original["resource_bindings"], status["resource_bindings"])
           if a["id"] != protein_id + "::local")
checklist = deepcopy(previous["work_item_states"])
for row in checklist:
    if row["id"] == "U05":
        row["current_evidence"] += (" Update099 accepts 417 pure schema resource preparation with "
            "133 passing checks and an unchanged real retained admission. Full 410 Workflow, receiver "
            "text/operand integration and historical failures remain open. Counts remain 112/308, "
            "42 local bindings and 196 remaining tool rows.")
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": changes, "resource_binding_changes": binding_changes,
    "added_evidence": [item],
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
temporary = STATUS.with_name(".WORK_STATUS.099.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 1, "grader_tally": 112,
    "verified_local_bindings": 42, "remaining_rows": 196, "new_status_sha256": sha(STATUS)}))
