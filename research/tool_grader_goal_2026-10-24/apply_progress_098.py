"""Record retained-target verification and measured schema reuse; no tool acceptance."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_098.json"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_097.json")
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
for suffix, check, expected in [
    ("retained_target_2026-10-27_412", "check002", "19 passed in 1374.06s"),
    ("schema_reuse_2026-10-27_416", "check001", "85 passed in 55.20s"),
]:
    packet = ROOT / ("verification/tool_graders_protein_structure_" + suffix)
    directory = packet / check
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0 and receipt["executed_source_pins_unchanged"]
    assert receipt["metadata"]["policy"] == {
        "memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    assert expected in (directory / "stdout.txt").read_text()
    reports.extend([directory / "receipt.json", directory / "stdout.txt"])
    reports.extend(p for p in packet.iterdir() if p.is_file() and p.suffix in (".md", ".json", ".diff"))

profile = ROOT / "verification/tool_graders_protein_structure_validation_profile_2026-10-27_415"
comparison = read(profile / "check002/comparison.json")
assert comparison["diagnostic_outcomes_identical"]
assert comparison["retained_input_identity_all_four_manifests_equal"]
assert comparison["baseline_check001_files_unchanged"]
assert all(row["identical"] for row in comparison["exact_record_comparison"].values())
for check in ("check001", "check002"):
    directory = profile / check
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == 0 and receipt["executed_source_pins_unchanged"]
    assert receipt["retained_input_pins_unchanged"]
    assert read(directory / "diagnostic.json")[-1] == {
        "step": "actual_typed_report_admission", "outcome": "accepted"}
    reports.extend(directory / name for name in ("receipt.json", "diagnostic.json", "profile_summary.json"))
reports.append(profile / "check002/comparison.json")
reports.extend(p for p in profile.iterdir() if p.is_file() and p.suffix in (".md", ".json"))

summary = ("412 authenticated retained-target shared-consumer checks passed19 cases.416 private schema "
    "validator reuse passed85 cases, including33 new cases and52 existing native contract/tool-information/"
    "execution cases.415 repeated actual retained report admission with unchanged form/facts/inputs: "
    "profiled wall48.274595→32.511627s, schema constructions295→9, all293 payload checks retained. "
    "Full410 Workflow and receiver integration remain unfinished;112/308 unchanged.")
item = {"id": "PROTEIN-RETAINED-TARGET-SCHEMA-REUSE-098",
    "kind": "component_and_actual_retained_admission_verification_full_workflow_open",
    "summary": summary,
    "qualification": "412 uses real Store/Journal/397/406/407 and actual native original/saved work on "
        "synthetic structures, through ExecutionEpisodes but without outer Workflow/controller. Its immutable "
        "snapshot predates416; the single checkout drift is recorded.416 includes actual local worker/lifecycle "
        "tests on synthetic inputs.415 uses actual original recorded authority and real typed admission; it "
        "does not rerun native science, serialize the returned ParentReport object, or time a full Workflow. "
        "Profile overhead is included. Full410 completion and receiver text/operand integration remain open.",
    "reports": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in sorted(set(reports))]}
assert item["id"] not in {r["id"] for r in status["verification_evidence"]}
status["verification_evidence"].append(item)
protein_id = "B-L107-compare_protein_structures"
changes, binding_changes = [], []
for row in status["rows"]:
    if row["id"] == protein_id:
        before = deepcopy(row)
        row.update(production_result_binding="actual_result_host_and_retained_target_verified_full_workflow_open",
            integration_verification="shared_retained_target_and_actual_admission_verified_full_workflow_and_prompt_open")
        row["evidence_ids"].append(item["id"])
        row["note"] += (" Update098:412 final19-case shared retained-target suite passed, including new saved "
            "use after original handoff loss, exact replay and current saved-byte failures.416 schema reuse "
            "passed85 checks;415 actual same-record admission stayed accepted,295→9 schema constructions and "
            "48.27→32.51 profiled seconds with293 current payload validations unchanged.410 full Workflow "
            "continues; receiver text and decision operand selection remain unfinished. No complete tool or binding added.")
        changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
for row in status["resource_bindings"]:
    if row["id"] == protein_id + "::local":
        before = deepcopy(row)
        row.update(production_result_binding="actual_result_host_information_and_retained_target_verified_full_workflow_open",
            integration_verification="shared_retained_target_and_admission_verified_full_workflow_and_receiver_open")
        row["evidence_ids"].append(item["id"])
        binding_changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
assert len(changes) == len(binding_changes) == 1
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != protein_id)
assert all(a == b for a, b in zip(original["resource_bindings"], status["resource_bindings"]) if a["id"] != protein_id + "::local")
checklist = deepcopy(previous["work_item_states"])
for row in checklist:
    if row["id"] == "U05":
        row["current_evidence"] += (" Update098 completes412 retained-target component verification and "
            "416 pure schema reuse, with415 real-admission before/after evidence.410 full Workflow and "
            "receiver text/decision operand integration remain open.112/308,42 local bindings,196 remaining "
            "rows and prior historical failures remain.")
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
        "410 complete Workflow remains in progress; no final full-path pass claimed.",
        "Receiver text rendering and decision operand selection remain unfinished; printed proposed template awaits user feedback.",
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
temporary = STATUS.with_name(".WORK_STATUS.098.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 1, "grader_tally": 112,
    "verified_local_bindings": 42, "remaining_rows": 196, "new_status_sha256": sha(STATUS)}))
