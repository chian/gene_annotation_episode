"""Record candidate implementations and exact unfinished integration boundaries.

This updates completion evidence only. The original inventory, scope, goal and
previous status receipts remain unchanged. Candidate tests are not live-service
or whole-tool completion.
"""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATH = HERE / "WORK_STATUS.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def report(path):
    return {"path": path, "sha256": sha(ROOT / path)}


raw = PATH.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == "91520f26eb13a744c31b926c0955760ca120b45f4779577dd210e643141948ef"
assert not (HERE / "PROGRESS_UPDATE_038.json").exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work["scope_file"]
scope_sha = sha(scope_path)
scope = json.loads(scope_path.read_text())
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == work["authority_sha256"]

p = "verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182/"
r = "verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/"
for name, value in read(p + "BASELINE_001.json").items():
    assert sha(ROOT / name) == value, name
assert not (ROOT / (p + "APPLICATION_RECEIPT_001.json")).exists()
final_freeze = read(p + "FREEZE_001.json")
assert len(final_freeze["sources"]) == 952
assert all(sha(ROOT / (p + "candidate/" + name)) == value
           for name, value in final_freeze["sources"].items())
assert (ROOT / (p + "final_host_001/command.json")).is_file()
assert (ROOT / (p + "final_workflow_001/command.json")).is_file()
assert not (ROOT / (p + "final_host_001/receipt.json")).exists()
assert not (ROOT / (p + "final_workflow_001/receipt.json")).exists()

checked = read(r + "evidence_n_review/N_C_AFTER_001.json")
assert checked["exit_code"] == 0 and checked["source_stable"]
assert all(sha(ROOT / (r + "candidate/" + name)) == value
           for name, value in checked["source_after"].items())
xml = ET.parse(ROOT / (r + "evidence_n_review/N_C_AFTER_001.xml")).getroot()
cases = xml.findall(".//testcase")
assert len(cases) == len({(c.attrib["classname"], c.attrib["name"]) for c in cases}) == 176
assert not any(xml.findall(".//" + name) for name in ("failure", "error", "skipped"))
d_commands = read(r + "evidence_d/COMMANDS_AND_RESULTS_001.json")
assert d_commands["commands"][-1]["exit_code"] == 0
assert d_commands["commands"][-1]["result"] == "54 passed in 5.48s"
assert "111 passed" in (ROOT / (r + "evidence_p/pytest_007.log")).read_text()

proteome = {
    "id": "PROTEOME-DIRECTIONAL-FINAL-WORKFLOW-STARTED-038",
    "kind": "frozen_candidate_actual_Workflow_verification_running",
    "summary": "The reviewed root-admission assertion is in the final 952-path freeze. Root-owned final host and actual Workflow verification are running with durable command/log/receipt harnesses. Previously passed 737-case unit and installed-package results remain unchanged. No candidate delta is applied to production.",
    "qualification": "The earlier worker development Workflow process disappeared without a terminal exit result; its log was empty and the reason is unknown. It is not counted as passing. Final host and Workflow results are still pending. Controlled service/decision inputs and retained public native bytes do not establish live BV-BRC execution, original deployed producer identity, executed input roster or a row-to-HSP association.",
    "reports": [report(p + name) for name in (
        "FREEZE_001.json", "evidence_f/F_HANDOFF_001.json",
        "evidence_f/DEV_005_TERMINAL_OBSERVATION_001.json",
        "final_host_001/command.json", "final_workflow_001/command.json")],
}
comparative = {
    "id": "COMPARATIVE-SYSTEMS-NATIVE-DATA-CALCULATOR-VERIFICATION-038",
    "kind": "candidate_native_Data_calculators_provider_and_episode_integration_in_progress",
    "summary": "N parser/sheet, D qualified Data extraction and C deterministic calculations are implemented in isolated186. Root N94+C82 verification passes 176 unique tests in29.60s with unchanged source during the run. D54 tests pass. P111 tests pass in128.41s after source/nullable/reference/canonical-form fixes; its actual N/D/C example retains native75%, later44.444%, reference2/4 versus3/4 and a measured active count0. I is implementing authenticated publication and actual typed episode delivery.",
    "numerical_example": "Actual parser/builder/calculator paths preserve native 3/(2*2)*100=75% separately from supplied later 4/(3*3)*100=44.44444444444444%. Family reported mean200aa, population SD81.64965809277261 and per-genome2/1/0 survive a malformed neighboring row. Native hex10001 remains ambiguous rather than a fabricated per-genome count.",
    "corrections": "C now permits feature-side metadata variation when the native subsystem formula's actual join/role/context operands agree, while contradictory identities still fail. Unrelated malformed summary rows no longer suppress valid row-specific formula checks. Root reproduced six malformed-family parser/builder failures, then preserved exact present lexemes and null for absent columns without weakening validators. Eight new regression cases pass; the other45 frozen N files remain unchanged.",
    "qualification": "All new inputs are retained source-executed synthetic outputs or explicit synthetic Data/service fixtures. No live ComparativeSystems or Data result is claimed. Twenty-five already frozen proteome paths were composed into186 candidate only before I started; root production is unchanged. Original-parameter custody, Data/source possession, lossless partial/failure publication, complete Workflow return verification and final installed package verification remain required before application. This is not whole-tool completion.",
    "reports": [report(r + name) for name in (
        "DATA_EXTRACTOR_HANDOFF_002.md", "INTEGRATION_BOUNDARY_CLOSURE_003.md",
        "REFERENCE_BINDING_CLOSURE_004.md", "PROTEOME_COMPOSITION_RECEIPT_001.json",
        "evidence_n_review/ROOT_REVIEW_001.json", "evidence_n_review/REGRESSION_BEFORE_001.json",
        "evidence_n_review/N_C_AFTER_001.json", "evidence_n_review/N_C_AFTER_001.xml",
        "evidence_c_review/C_REVIEW_HANDOFF_001.md",
        "evidence_c_review/C_REVIEW_OWNED_FILE_MANIFEST_001.json",
        "evidence_c_review/CURRENT_N_TO_C_CHECK_001.json",
        "evidence_d/HANDOFF_D_001.md", "evidence_d/SOURCE_HASHES_001.json",
        "evidence_d/COMMANDS_AND_RESULTS_001.json", "evidence_d/NUMERICAL_RESULT_001.json",
        "evidence_p/pytest_007.log", "evidence_p/P_VERIFICATION_INPUTS_001.json",
        "evidence_p/FILLED_PROVIDER_RECEIPT_001.json")],
}
added = [proteome, comparative]
assert not {e["id"] for e in added}.intersection(e["id"] for e in work["verification_evidence"])
work["verification_evidence"].extend(added)
for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row["integration_verification"] = "737frozen_unit_and_installed_facade_pass_root_final_host_and_Workflow_running"
        row["evidence_ids"].append(proteome["id"])
        row["note"] += " Update038: final full952-path freeze contains the reviewed actual-root receipt assertion. Root-owned host and Workflow tests are running;737unit and installed-package passes are preserved. Earlier worker development process disappeared without terminal evidence and is not a pass; cause unknown. No182production application. Live execution, producer/executed-input and row/HSP association limitations remain."
    elif row["id"] == "C-L207-ComparativeSystems":
        row["overall"] = "candidate_native_Data_calculators_implemented_provider_and_episode_verification_in_progress"
        row["tool_information"] = "candidate_resource_specific_tool_info_and_registration_being_integrated"
        row["numerical_sheet"] = "candidate_native_builder_implemented_and_numerically_tested"
        row["native_parser"] = "six_profiles_implemented_partial_malformed_family_rows_preserved"
        row["metadata_extractor"] = "candidate_qualified_Data_extractor_54tests_pass_host_possession_integration_pending"
        row["deterministic_calculator"] = "candidate_quantities_implemented_dependency_precision_corrected_82tests_pass"
        row["production_result_binding"] = "candidate_provider_implemented_actual_publication_and_episode_returns_in_progress_not_applied"
        row["numerical_verification"] = "176root_N_C_unique_cases_pass_D54pass_actual_native75_and_later44point444_separate"
        row["integration_verification"] = "provider111pass_actual_N_D_C_example_pass_host_and_episode_path_unfinished"
        row["evidence_ids"].append(comparative["id"])
        row["note"] += " Update038: N/D/C delivered; root repaired exact malformed-family lexeme bug after six reproduced failures. Native51+sheet43+calculator82=176unique tests pass, source stable; D54pass. C11dependency counterexamples repaired,27saved native answers unchanged,22old histories validated without recalculation. P111pass after reference/nullable/canonical-form fixes; actual provider example yields native75%, later44.444%, reference2/4 versus3/4 and measured active0. Fresh I owns actual authenticated publication, configured tool binding and own/received typed returns. Proteome delta composed into186candidate only. No ComparativeSystems production application or live service result. Historical tests overlap and are not summed as cumulative unique coverage."
for row in work["resource_bindings"]:
    if row["id"] == "C-L206-GenomeComparison::api":
        row["integration_verification"] = "737candidate_unit_and_installed_facade_pass_root_final_host_and_Workflow_running"
        row["evidence_ids"].append(proteome["id"])
    elif row["id"] == "C-L207-ComparativeSystems::api":
        row["production_result_binding"] = "candidate_provider_and_existing_AppService_episode_binding_in_progress_not_applied"
        row["integration_verification"] = "actual_N_D_C_provider111_and_filled_example_pass_host_Workflow_pending"
        row["evidence_ids"].append(comparative["id"])

changes = []
for group, count in (("rows", 308), ("resource_bindings", 288)):
    assert len(work[group]) == count
    assert [row["id"] for row in work[group]] == [row["id"] for row in original[group]] == [row["id"] for row in scope[group]]
    prior = {row["id"]: row for row in original[group]}
    changes.extend({"group": group, "id": row["id"], "before": prior[row["id"]], "after": deepcopy(row)}
                   for row in work[group] if row != prior[row["id"]])
assert len(changes) == 4 and work["complete_scientific_tools_claimed"] == 0
assert sha(scope_path) == scope_sha
updated = (json.dumps(work, indent=2) + "\n").encode()
record = {
    "schema": "tool_grader_progress_update_v1", "date": "2026-10-25",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before, "new_status_sha256": hashlib.sha256(updated).hexdigest(),
    "scope_sha256_unchanged": scope_sha,
    "this_goal_turn_classification": "progress",
    "current_progress": "Reproduced and repaired native parser partial-row loss;176 actual N/C tests pass. Received and verified D/C deliveries. P and I continue isolated provider and episode integration. Final182 host/Workflow runs are observed live; no final result or production application claimed.",
    "changes": changes, "added_evidence": added, "scope_changes": False,
    "inventory_maintenance_counted_as_implementation_progress": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": 0,
}
with (HERE / "PROGRESS_UPDATE_038.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
PATH.write_bytes(updated)
print(json.dumps({"checkpoint": 38, "changed_rows_and_bindings": len(changes),
                  "scope_rows": 308, "resource_bindings": 288,
                  "status_sha256": record["new_status_sha256"]}))
