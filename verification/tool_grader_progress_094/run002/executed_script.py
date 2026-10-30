"""Record verified protein components without claiming whole-tool integration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / "WORK_STATUS.json"
UPDATE = HERE / "PROGRESS_UPDATE_094.json"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / "PROGRESS_UPDATE_093.json")
before_sha, scope_sha = sha(STATUS), sha(HERE / "SCOPE.json")
assert before_sha == previous["new_status_sha256"]
assert scope_sha == previous["scope_sha256_unchanged"]
status = read(STATUS)
original = deepcopy(status)
assert len(status["rows"]) == 308 and len(status["resource_bindings"]) == 288
assert previous["numerical_grader_progress_tally"]["after"] == 112
assert status["verified_bound_local_tool_mode_rows"] == 42
assert sha(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")) == status["authority_sha256"]
policy = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
reports = []
for suffix, check, expected_code, expected_summary in (
    ("preparation_2026-10-27_396", "check003", 0, "81 passed"),
    ("operands_2026-10-27_398", "check005", 0, "89 passed"),
    ("publication_2026-10-27_399", "check003", 0, "44 passed"),
    ("publication_2026-10-27_399", "check006", 1, "2 failed, 416 passed"),
    ("publication_2026-10-27_399", "check007", 0, "2 passed"),
    ("publication_2026-10-27_399", "check008", 0, "1 passed"),
):
    packet = ROOT / ("verification/tool_graders_protein_structure_" + suffix)
    directory = packet / check
    receipt = read(directory / "receipt.json")
    assert receipt["returncode"] == expected_code
    assert receipt["metadata"]["policy"] == policy
    pin_key = ("executed_snapshot_pins_unchanged" if suffix == "operands_2026-10-27_398"
        else "executed_source_pins_unchanged")
    assert receipt[pin_key] is True
    assert expected_summary in (directory / "stdout.txt").read_text()
    reports += [directory / "receipt.json", directory / "stdout.txt"]
    reports += [path for path in packet.iterdir() if path.is_file() and path.suffix in (".md", ".json")]

packet399 = ROOT / "verification/tool_graders_protein_structure_publication_2026-10-27_399"
verification = read(packet399 / "VERIFICATION_001.json")
assert verification["selector_and_source_payload_checks"] == 44
assert verification["form_and_regression_checks"] == 418
def checked_pin(check, path):
    return next(row["sha256"] for row in read(packet399 / check / "source_pins_before.json") if row["path"] == path)
assert checked_pin("check006", "gene_annotation_episode/communication.py") == checked_pin(
    "check007", "gene_annotation_episode/communication.py") == sha(ROOT / "gene_annotation_episode/communication.py")
contracts = ROOT / "verification/tool_graders_protein_structure_shared_contract_2026-10-27_380"
reports += [contracts / name for name in (
    "RESULT_PREPARATION_CONTRACT_010.md", "AUTHORITY_MODULE_SEAMS_011.md",
    "RESULT_SELECTOR_CONTRACT_012.md", "FORM_BOUNDARY_CONTRACT_013.md",
    "RECORD_PUBLICATION_CONTRACT_014.md", "ALIGNMENT_PREFLIGHT_CONTRACT_015.md",
    "RECEIVED_WITNESS_ORDER_016.md")]

summary = ("Protein retained-worker preparation396 passed 81 tests; operand consistency398 passed 89. "
    "Root399 passed 44 pure selector/error/source-payload checks and all 418 distinct form/regression "
    "cases across check006 (416 passed, two missing fixture-data failures) and check007 (those two passed). "
    "No production change separated those last two snapshots. check008 repeats one successful form "
    "to retain its admitted example, adding no distinct coverage. These suites overlap dependencies "
    "and are component evidence, not a complete protein episode path. Tally stays 112/308.")
item = {"id": "PROTEIN-PREPARATION-OPERANDS-FORMS-094",
    "kind": "component_verification_with_full_episode_path_unfinished", "summary": summary,
    "reports": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for path in sorted(set(reports))],
    "qualification": "398 uses injected received-authority ports.399's form examples use synthetic custody. "
        "396 executes actual result workers and recovery but does not publish or authenticate episode returns. "
        "397 received authority,400 Store publication,401 alignment/estimate preflight and root host integration remain unaccepted here.",
    "source_pins": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)} for path in (
        ROOT / "gene_annotation_episode/native_protein_structure_preparation.py",
        ROOT / "gene_annotation_episode/protein_structure_operands.py",
        ROOT / "gene_annotation_episode/protein_structure_authority.py",
        ROOT / "gene_annotation_episode/protein_structure_selection.py",
        ROOT / "gene_annotation_episode/communication.py")],
    "snapshot_note": "All executed snapshots remained unchanged. Exact live-checkout drift is retained "
        "per receipt.399 pins the earlier pure source helper separately from400's later publication extensions."}
assert item["id"] not in {entry["id"] for entry in status["verification_evidence"]}
status["verification_evidence"].append(item)
protein_id = "B-L107-compare_protein_structures"
changes, binding_changes = [], []
for row in status["rows"]:
    if row["id"] != protein_id:
        continue
    before = deepcopy(row)
    row.update(overall="preparation_operand_and_form_components_tested_full_path_unfinished",
        source_presence="native_components_preparation_operands_selector_and_forms_present_host_integration_unfinished",
        production_result_binding="preparation_operand_and_form_components_tested_host_and_receipt_wiring_unfinished",
        integration_verification="component_and_shared_form_only_no_complete_receiving_episode_proof")
    row["evidence_ids"].append(item["id"])
    row["note"] += (" Update094:396 preparation passed81,398 operands passed89,399 selector/source payload "
        "passed44 and shared forms/regressions passed all418 distinct cases across two runs. "
        "The same four registered sources preserve exact original schemas, integer counts, selected "
        "fields and recorded facts.397/400/401 and the root host, resource, full receipt and message "
        "integration remain unfinished. No protein tool or local-binding count is added.")
    changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
for row in status["resource_bindings"]:
    if row["id"] != protein_id + "::local":
        continue
    before = deepcopy(row)
    row.update(production_result_binding="capture_worker_preparation_and_operand_components_tested_host_path_unfinished",
        integration_verification="component_and_form_only_no_actual_resource_registry_and_receiving_episode_path")
    row["evidence_ids"].append(item["id"])
    binding_changes.append({"id": row["id"], "before": before, "after": deepcopy(row)})
assert len(changes) == len(binding_changes) == 1
assert all(a == b for a, b in zip(original["rows"], status["rows"]) if a["id"] != protein_id)
assert all(a == b for a, b in zip(original["resource_bindings"], status["resource_bindings"]) if a["id"] != protein_id + "::local")
checklist = deepcopy(previous["work_item_states"])
for entry in checklist:
    if entry["id"] == "U05":
        entry["current_evidence"] += (" Update094:396 retained-worker preparation81,398 operands89 and399 "
            "selector/payload44 plus shared-form/regression418 checks are recorded as components. "
            "397 received proof,400 publication,401 preflight and root result host/resource/full "
            "communication integration remain open.112/308,42 local bindings,196 remaining fixed "
            "rows and eight historical receipt failures are unchanged. W05/literature stay separate.")
assert [(x["id"], x["original_item"], x["status"]) for x in checklist] == [
    (x["id"], x["original_item"], x["status"]) for x in previous["work_item_states"]]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-27", "author": "root",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "previous_status_sha256": before_sha,
    "new_status_sha256": hashlib.sha256(raw).hexdigest(), "scope_sha256_unchanged": scope_sha,
    "scope_changes": [], "changes": changes, "resource_binding_changes": binding_changes,
    "added_evidence": [item], "numerical_grader_progress_tally": {"before": 112, "after": 112,
        "added_row_ids": [], "meaning": previous["numerical_grader_progress_tally"]["meaning"]},
    "verified_bound_local_tool_mode_rows": {"before": 42, "after": 42},
    "remaining_fixed_rows_outside_tally": 196, "completed_work": [summary],
    "findings_requiring_repair": [
        "Protein result host, resource registration, full original received authority, typed result return and prompt integration remain unfinished.",
        "397 received proof,400 Store publication and401 preflight are ongoing and not accepted by this update.",
        "Eight historical receipt failures remain under U05; U03 native/HPC work and all other fixed rows remain."],
    "work_item_states": checklist,
    "unfinished_work": [entry["current_evidence"] for entry in checklist if entry["status"] != "complete"],
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
assert sha(STATUS) == before_sha and sha(HERE / "SCOPE.json") == scope_sha
with UPDATE.open("x") as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.094.writing")
with temporary.open("xb") as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_tool_rows": 1, "updated_resource_bindings": 1,
    "numerical_grader_progress_tally": 112, "verified_bound_local_tool_mode_rows": 42,
    "remaining_fixed_rows_outside_tally": 196, "new_status_sha256": sha(STATUS)}))
