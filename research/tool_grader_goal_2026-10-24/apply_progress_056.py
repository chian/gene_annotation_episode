"""Append inspected HMMER component evidence without claiming episode completion."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).parent
STATUS = DIRECTORY / "WORK_STATUS.json"
UPDATE = DIRECTORY / "PROGRESS_UPDATE_056.json"
AUTHORITY = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def descriptor(relative):
    path = ROOT / relative
    return {"path": relative, "sha256": sha(path)}

if UPDATE.exists():
    raise RuntimeError("immutable progress update already exists")
if sha(AUTHORITY) != "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7":
    raise RuntimeError("authority identity changed")
before_sha = sha(STATUS)
if before_sha != "8ebd22759e53d64e550c3e6de8f1f3b6669545025fc48851fc8e8cc3031a20f1":
    raise RuntimeError("status changed; inspect before making another update")
status = json.loads(STATUS.read_text())
scope_sha = sha(DIRECTORY / "SCOPE.json")
before_ids = [row["id"] for row in status["rows"]]
before_binding_ids = deepcopy(status["resource_bindings"])

components = [
    ("HMMER-FM-056", "tool_graders_hmmer_fm_data_2026-10-26_264", "check006", 66, "README.md",
     "Complete supplied-ABI FM extraction and separate source/index/match numerical components."),
    ("HMMER-PRODUCER-056", "tool_graders_hmmer_preparation_producer_2026-10-26_267", "check005", 225, "REPORT.md",
     "77 actual native executions across26 modes at the original producer checkpoint; later simulation-setting correction has separate270 evidence."),
    ("HMMER-ARTIFACT-056", "tool_graders_hmmer_artifact_data_2026-10-26_268", "check003", 105, "README.md",
     "Model conversion/retrieval/index/pressed-artifact numerical sheets, joins and saved recalculation."),
    ("HMMER-ALIGNMENT-PREPARATION-056", "tool_graders_hmmer_alignment_data_2026-10-26_269", "check005", 48, "REPORT_ADDENDUM_001.md",
     "Build/mask native measurements and model/alignment geometry with actual denominators."),
    ("HMMER-CAPTURE-056", "tool_graders_hmmer_preparation_capture_2026-10-26_270", "check005", 149, "README.md",
     "Original26-mode byte custody and corrected request settings, including four newly executed simulation algorithms."),
    ("HMMER-GRADING-056", "tool_graders_hmmer_preparation_grading_2026-10-26_271", "check004", 135, "README.md",
     "Pure mode-specific grading dispatch and saved recalculation across77 retained producer cases plus corrected simulations."),
    ("HMMER-PROJECTION-056", "tool_graders_hmmer_preparation_views_2026-10-26_272", "check005", 173, "VERIFICATION.md",
     "Requested-only exact scalar/check/file selection with actual native row and occurrence relationships."),
    ("HMMER-PUBLICATION-056", "tool_graders_hmmer_preparation_results_2026-10-26_273", "check003", 32, "README.md",
     "Real bounded saved-data grading/publication for26 modes; selected dependencies and artifact-only recovery from injected grade-worker failure."),
    ("HMMER-TOOL-INFORMATION-056", "tool_graders_hmmer_preparation_tool_info_2026-10-26_274", "check001", 254, "REPORT.md",
     "All26 actual tool-information entries and exact local software-pinned callable contracts."),
]
added, verification = [], []
for identity, directory, check, passed, report, meaning in components:
    relative = "verification/" + directory
    receipt_path = ROOT / relative / check / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if receipt["returncode"] != 0:
        raise RuntimeError("unsuccessful receipt: " + str(receipt_path))
    stdout = (ROOT / relative / check / "stdout.log").read_text()
    if not re.search(r"\b" + str(passed) + r" passed\b", stdout):
        raise RuntimeError("verification count mismatch: " + relative)
    evidence = {"id": identity, "kind": "verified_component_with_shared_episode_integration_pending",
        "summary": meaning + " " + str(passed) + " tests passed.",
        "qualification": "Component-specific scope and native/retained/synthetic distinctions are in the exact report; no full-tool or full-resource completion claim.",
        "reports": [descriptor(relative + "/" + report), descriptor(relative + "/" + check + "/receipt.json")]}
    added.append(evidence)
    verification.append({"directory": relative + "/" + check, "passed": passed, "failed": 0,
        "receipt": descriptor(relative + "/" + check + "/receipt.json")})
known_ids = {row["id"] for row in status["verification_evidence"]}
if known_ids.intersection(row["id"] for row in added):
    raise RuntimeError("evidence identity already exists")
status["verification_evidence"].extend(added)

programs = ("alimask", "hmmbuild", "hmmconvert", "hmmemit", "hmmfetch", "hmmpress", "hmmsim", "hmmstat", "makehmmerdb", "hmmerfm-exactmatch")
common_evidence = [row["id"] for row in added if row["id"] not in {
    "HMMER-FM-056", "HMMER-ARTIFACT-056", "HMMER-ALIGNMENT-PREPARATION-056"}]
changes = []
for program in programs:
    row = next(r for r in status["rows"] if r["id"] == "A-L076-" + program)
    before = deepcopy(row)
    row.update(overall="numerical_and_saved_result_components_verified_shared_episode_verification_pending",
        tool_information="actual_26_mode_entries_and_software_pinned_local_contracts_verified",
        invocation_contract="real_native_producer_verified_shared_practical_hooks_under_verification",
        numerical_sheet="implemented_native_numerical_sheet_with_explicit_format_limits",
        native_parser="retained_native_formats_partial_and_missing_states_verified",
        metadata_extractor="exact_original_occurrence_model_key_source_and_abi_joins_verified",
        deterministic_calculator="separate_numerical_components_and_saved_recalculation_verified",
        production_result_binding="capture_bounded_grading_and_selected_publication_verified_shared_hooks_written",
        numerical_verification="independent_native_values_and_adversarial_component_cases_passed",
        integration_verification="saved_result_path_verified_full_shared_Workflow_checks_in_progress",
        live_resource_verification="tiny_native_local_producer_cases_verified_full_episode_native_runs_in_progress")
    specific = ("HMMER-ALIGNMENT-PREPARATION-056" if program in {"alimask", "hmmbuild"} else
                "HMMER-ARTIFACT-056" if program in {"hmmconvert", "hmmfetch", "hmmpress"} else
                "HMMER-FM-056" if program in {"makehmmerdb", "hmmerfm-exactmatch"} else None)
    row["evidence_ids"] = list(dict.fromkeys([*row["evidence_ids"], *common_evidence, *([specific] if specific else [])]))
    row["note"] += (" Update056: numerical, capture, saved-data grading, requested projection, publication and tool-information components are implemented and verified. Shared execution/receipt hooks are written; L1/R1/W1 complete episode verification is still in progress. Binary/HMMER2 decoding and unestablished native alignment-map subcases remain explicit. No independent annotation-confidence score is assigned to preparation.")
    changes.append({"group": "rows", "id": row["id"], "before": before, "after": deepcopy(row)})

assert len(status["rows"]) == 308 and [r["id"] for r in status["rows"]] == before_ids
assert status["resource_bindings"] == before_binding_ids
assert sha(DIRECTORY / "SCOPE.json") == scope_sha
raw = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode()
update = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-26",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before_sha, "new_status_sha256": hashlib.sha256(raw).hexdigest(),
    "scope_sha256_unchanged": scope_sha, "scope_changes": [], "changes": changes,
    "added_evidence": added, "verification": verification, "count_change": {},
    "numerical_grader_progress_tally": {"before": 79, "after": 79, "added_row_ids": [],
        "meaning": "Component evidence advanced; the ten-tool batch is not added before its shared episode paths are verified."},
    "remaining_fixed_rows_outside_tally": 229,
    "completed_work": ["All ten HMMER preparation numerical component families, actual local producer and complete retained-result path.",
        "All26 precise tool-information contracts and selected typed projection catalogues.",
        "Shared execution, receipt and practical hooks written with independent typed-return and Workflow verification in progress."],
    "unfinished_work": ["Complete shared Workflow and both immediate-parent typed boundaries for every supported HMMER preparation mode.",
        "Explicit native mode/format gaps including binary/HMMER2 body/index decoders and unestablished alignment-map cases.",
        "Remaining fixed308-row goal, generic TASK/STEERING/resource instructions and previously recorded integration/resource gaps.",
        "Eight previously recorded obsolete shared receipt expectations remain unresolved; no retired root tools or scoring policy restored."],
    "excluded_claims": ["Full HMMER preparation episode-path completion", "API/HPC deployment", "W05 or final annotation scoring", "Literature graders", "Whole-checkout frozen verification", "Full308-goal completion"],
    "previous_goal_turn": {"classification": "no_progress", "reason": "Status-only response; this continuation revalidated receipts and then changed implementation and executed tests."},
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": status["complete_scientific_tools_claimed"]}
with UPDATE.open("x") as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
temporary = STATUS.with_name(".WORK_STATUS.056.writing")
with temporary.open("xb") as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({"updated_rows": len(changes), "added_evidence": len(added),
    "numerical_grader_progress_tally": 79, "scope_rows": len(status["rows"]),
    "new_status_sha256": sha(STATUS)}))
