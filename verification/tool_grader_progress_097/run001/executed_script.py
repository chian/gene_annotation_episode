"""Record receipt/host/information components without accepting the full tool."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_097.json"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_096.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]
reports = []
for suffix, check, summary in [
    ("result_receipts_2026-10-27_406", "check002", "61 passed"),
    ("result_receipts_2026-10-27_406", "check003", "3 passed"),
    ("result_receipts_2026-10-27_406", "check004", "9 passed"),
    ("result_host_2026-10-27_407", "check004", "19 passed"),
    ("result_host_2026-10-27_407", "check005", "2 passed"),
    ("execution_information_2026-10-27_411", "check001", "48 passed"),
    ("audit_boundary_2026-10-27_414", "check001", "58 passed"),
]:
    packet = ROOT / ("verification/tool_graders_protein_structure_" + suffix)
    directory = packet / check
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0 and receipt["executed_source_pins_unchanged"]
    assert receipt["metadata"]["policy"] == {
        "memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    assert summary in (directory / "stdout.txt").read_text()
    reports.extend([directory / "receipt.json", directory / "stdout.txt"])
    reports.extend(path for path in packet.iterdir() if path.is_file() and path.suffix in (".md", ".json"))

diagnostic = ROOT / "verification/tool_graders_protein_structure_workflow_2026-10-27_410/check010"
actual_receipt = read(diagnostic / "receipt.json")
assert actual_receipt["returncode"] == 0 and actual_receipt["executed_source_pins_unchanged"]
assert read(diagnostic / "diagnostic.json")[-1] == {"step": "actual_typed_report_admission", "outcome": "accepted"}
reports.extend([diagnostic / "receipt.json", diagnostic / "diagnostic.json"])

summary = ("406 receipt baseline61, classifier3 and shared-manifest9 checks passed on separately recorded "
    "source revisions.407 actual host19 plus recovery2 checks passed.411 actual result-information/selector48 "
    "checks passed.410 complete Workflow exposed shared assignment newline and typed-custody audit incompatibilities;406 "
    "and414 fixed them.414 passed58 checks and410's retained real-authority admission diagnostic passed. "
    "The full rerun,412 retained-target verification and receiver text remain "
    "unfinished. No tool-count increment;112/308 remains.")
item = {"id": "PROTEIN-RECEIPTS-HOST-INFORMATION-097",
    "kind": "component_verification_with_full_episode_path_unfinished", "summary": summary,
    "qualification": "406 uses actual Store/Journal/commission proof with deliberately injected scientific "
        "qualification; its full61-case run predates the separately tested classifier and shared-manifest "
        "corrections.407 uses actual native/capture/worker/source/return machinery in a direct-host fixture, "
        "not the complete Workflow; its final21 cases predate those406 corrections.411 describes actual "
        "bound functions but does not run native analysis or implement model-facing text.414 preserves exact "
        "internal typed custody after semantic validation while keeping the model-input audit strict; its "
        "unit facts are synthetic and410's separate diagnostic uses actual retained authority. Full410 delivery, "
        "412 saved/replay recovery and prompt integration are open. Old failing attempts remain retained.",
    "reports": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in sorted(set(reports))],
    "snapshot_note": "Executed snapshots remain immutable; checkout drift and source revisions are recorded "
        "separately. Counts overlap across suites and are not a single total of tests on the final checkout."}
assert item["id"] not in {row["id"] for row in status["verification_evidence"]}
status["verification_evidence"].append(item)
protein_id = "B-L107-compare_protein_structures"
changes, binding_changes = [], []
for row in status["rows"]:
    if row["id"] != protein_id:
        continue
    before = deepcopy(row)
    row.update(overall="local_host_and_information_components_verified_full_workflow_and_text_open",
        source_presence="local_resource_shared_hooks_receipts_host_and_result_information_present",
        tool_information="local_launch_monitor_result_information_verified_receiver_text_open",
        invocation_contract="local_registration_and_saved_factory_verified_complete_workflow_open",
        production_result_binding="actual_result_host_verified_full_workflow_and_retained_target_repair_open",
        integration_verification="receipt_host_information_components_verified_complete_workflow_and_prompt_open")
    row["evidence_ids"].append(item["id"])
    row["note"] += (" Update097:406 receipt61 plus classifier3 and shared-assignment9 checks,407 host19 plus "
        "recovery2 checks, and411 result-information48 checks passed with their recorded source limits. "
        "410 found the shared assignment.json LF incompatibility that406 corrected and the typed custody audit "
        "rejection that414 corrected (58 checks plus actual410 retained-form diagnostic). Its full rerun is ongoing. "
        "412 handles authenticated saved/replay targets after original handoff byte loss. Parent-specific text "
        "is proposed for user feedback and remains uncoded. No complete tool or binding added.")
    changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
for row in status["resource_bindings"]:
    if row["id"] != protein_id + "::local":
        continue
    before = deepcopy(row)
    row.update(production_result_binding="actual_result_host_and_information_verified_full_workflow_open",
        integration_verification="actual_host_receipts_and_selected_information_verified_shared_recovery_and_workflow_open")
    row["evidence_ids"].append(item["id"])
    binding_changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
assert len(changes) == len(binding_changes) == 1
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != protein_id)
assert all(a == b for a, b in zip(original["resource_bindings"], status["resource_bindings"]) if a["id"] != protein_id + "::local")
checklist = deepcopy(previous["work_item_states"])
for row in checklist:
    if row["id"] == "U05":
        row["current_evidence"] += (" Update097 adds verified406 receipt/classifier/shared-writer,407 direct "
            "host/recovery,411 result-information and414 typed-custody admission components.410 complete Workflow rerun,412 authenticated "
            "retained-target consumers and413 receiver-text design are open. Printed prompt awaits user "
            "feedback.112/308,42 local bindings,196 remaining rows and prior historical failures remain.")
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": changes, "resource_binding_changes": binding_changes, "added_evidence": [item],
    "numerical_grader_progress_tally": {"before": 112, "after": 112, "added_row_ids": [],
        "meaning": previous["numerical_grader_progress_tally"]["meaning"]},
    "verified_bound_local_tool_mode_rows": {"before": 42, "after": 42}, "remaining_fixed_rows_outside_tally": 196,
    "completed_work": [summary], "findings_requiring_repair": [
        "410 complete receiving-episode Workflow remains in progress after shared-manifest repair.",
        "412 authenticated retained-target recovery is in progress; existing shared dispatch reopens original handoff bytes.",
        "Receiver text rendering remains unfinished and the printed proposed template awaits user feedback.",
        "Prior401 commission/policy/timing fixture failures and eight historical U05 failures remain.",
        "U03 native/HPC and all other fixed unfinished rows remain."],
    "work_item_states": checklist, "unfinished_work": [x["current_evidence"] for x in checklist if x["status"] != "complete"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.097.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 1, "grader_tally": 112,
    "verified_local_bindings": 42, "remaining_rows": 196, "new_status_sha256": sha(STATUS)}))
