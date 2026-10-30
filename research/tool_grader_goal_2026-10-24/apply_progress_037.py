"""Record frozen candidate verification and the next explicit coding workloads.

No production integration, live service execution or whole-tool completion is
inferred from these candidate/contract results. Preserve all fixed scope rows.
"""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATH = HERE / "WORK_STATUS.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative):
    return json.loads((ROOT / relative).read_text())


def report(relative):
    return {"path": relative, "sha256": sha(ROOT / relative)}


raw = PATH.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == "bfefe9418bc3b5964e8c0152683e88cb7836b1c8d39f27fb495094984cc30895"
assert not (HERE / "PROGRESS_UPDATE_037.json").exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work["scope_file"]
scope_sha = sha(scope_path)
scope = json.loads(scope_path.read_text())
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert sha(authority) == work["authority_sha256"]

p = "verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182/"
q = "verification/tool_graders_bvbrc_comparative_systems_contract_2026-10-25_185/"
r = "verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/"
unit = read(p + "final_unit_001/receipt.json")
package = read(p + "package_verification_001/receipt.json")
assert unit["passed"] and unit["case_counts"] == {"passed": 737, "failed": 0, "error": 0, "skipped": 0}
assert unit["source_count"] == 951 and not unit["changed_sources"]
cases = read(p + "final_unit_001/cases.json")
assert len({(case["classname"], case["name"]) for case in cases}) == 737
assert package["passed"] and not package["changed_sources"] and package["source_count"] == 951
freeze1 = read(p + "FREEZE_INDEPENDENT_001.json")
freeze2 = read(p + "FREEZE_INDEPENDENT_002.json")
assert set(freeze1["sources"]) == set(freeze2["sources"])
assert [name for name in freeze1["sources"] if freeze1["sources"][name] != freeze2["sources"][name]] == [
    "tests/test_bvbrc_proteome_directional_returns.py"]
assert (ROOT / (p + "final_host_001/command.json")).is_file()
for name, value in read(p + "BASELINE_001.json").items():
    assert sha(ROOT / name) == value, name

manifest = read(q + "DELIVERY_MANIFEST_001.json")
for entry in manifest["files"]:
    assert sha(ROOT / (q + entry["path"])) == entry["sha256"], entry["path"]
contract = read(q + "CONTRACT_VALIDATION_001.json")
assert contract["all_passed"] and contract["passed_checks"] == 123
assert contract["schema_definitions"] == 115 and contract["conforming_examples"] == 27
accepted = read(r + "CONTRACT_ACCEPTANCE_001.json")
assert [entry["workload"] for entry in accepted["assigned"]] == ["N", "C"]

candidate_evidence = {
    "id": "PROTEOME-DIRECTIONAL-CANDIDATE-VERIFICATION-037",
    "kind": "frozen_candidate_unit_and_installed_package_verification",
    "summary": "Directional v2 provider, numerical publication, fourteen finite fact families and return binding are implemented in isolated182.737 unique case identities pass the final unit group in588.275s, with951 tracked files unchanged. Installed wheel/facade check passes with951 unchanged files. Final nine-module host verification is running; the full Workflow test and explicit root admission assertion remain unfinished. No182 production delta has been applied.",
    "numerical_example": "Installed facade returns529/600 coverage,468/529 symbol identity,468/468 resolved identity,61 unresolved pairs and native expectation2e-66 from retained public BLASTP bytes. Task/artifact custody in this example is controlled synthetic provenance, not a live GenomeComparison result.",
    "qualification": "Developer host run retained7passes/1failure: changed provider version was correctly rejected earlier at authenticated publication read, whereas the test expected a later exception. Reviewed one-line test correction follows final unit completion; production is unchanged. The new host freeze differs only in that test. Existing legacy provider pin remains unchanged. Executed input roster, native row-to-HSP binding, producer retention/deployment and live service evidence remain unresolved.",
    "reports": [report(p + name) for name in (
        "FREEZE_INDEPENDENT_001.json", "FREEZE_INDEPENDENT_002.json",
        "final_unit_001/receipt.json", "final_unit_001/pytest.xml",
        "package_verification_001/receipt.json", "package_verification_001/installed_result.json",
        "evidence_d/OWNED_SOURCE_MANIFEST_001.json", "evidence_d/DEVELOPMENT_HANDOFF_001.json",
        "evidence_f/OWNED_SOURCE_MANIFEST_001.json", "evidence_f/RETURN_EXPECTATION_PATCH_RECEIPT_001.json",
        "PRODUCTION_REVIEW_001.json", "HOST_VERIFICATION_SCOPE_001.json",
        "final_host_001/command.json")],
}
comparative_evidence = {
    "id": "COMPARATIVE-SYSTEMS-CONTRACT-AND-ASSIGNMENTS-037",
    "kind": "source_executed_synthetic_evidence_closed_interfaces_and_fresh_coding",
    "summary": "Reviewed actual ComparativeSystems source and eight offline source-executed synthetic cases.115 closed definitions and27 filled cross-worker examples pass123 contract/arithmetic checks. Closed explicit analysis/population inputs, document-to-producer mapping, native/calculated-scalar/ratio selectors and acyclic shared shape helpers before assigning fresh N187 native/sheet and C188 calculator workers.935 unchanged source files were copied into isolated186.",
    "numerical_example": "Native retained pathway population gives3/(2*2)*100=75%; the separately supplied synthetic later population gives4/(3*3)*100=44.444...%. Family lengths100,200,300 give mean200, population SD81.64965809277261 and CV0.4082482904638631. Native hex10001 for two genomes remains ambiguous. These are source/contract examples, not production parser results.",
    "qualification": "No ComparativeSystems production parser/calculator, selected tool binding or actual parent-return path is claimed. Two public probes returned403. D supplied Data extraction, P provider/projection and I host/tool-info/returns have exact planned boundaries and remain unassigned. No scope row, evidence-axis or annotation-credit formula changed.",
    "reports": [report(q + name) for name in (
        "DELIVERY_MANIFEST_001.json", "SOURCE_WITNESS_RESULTS_001.json",
        "HANDOFF_SCHEMAS_001.json", "FILLED_EXAMPLES_001.json",
        "CONTRACT_VALIDATION_001.json", "HANDOFF_CLOSURE_002.md",
        "FINAL_MAPPING_AND_PARENT_BOUNDARY_003.md", "VERIFICATION_CASES_001.md")]
        + [report(r + name) for name in (
            "PREPARATION_RECEIPT_001.json", "IMPLEMENTATION_HANDOFF_001.md",
            "CONTRACT_ACCEPTANCE_001.json")],
}
new_evidence = [candidate_evidence, comparative_evidence]
assert not {entry["id"] for entry in new_evidence}.intersection(entry["id"] for entry in work["verification_evidence"])
work["verification_evidence"].extend(new_evidence)
for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row["overall"] = "legacy_API_and_directional_numerics_applied_directional_v2_candidate_under_host_verification"
        row["production_result_binding"] = "legacy_path_applied_directional_v2_candidate_implemented_not_applied"
        row["integration_verification"] = "737frozen_candidate_unit_cases_and_installed_facade_pass_final_host_and_Workflow_pending"
        row["evidence_ids"].append(candidate_evidence["id"])
        row["note"] += " Update037:182v2 candidate implemented;737final unit cases pass in588.275s with951sources unchanged; installed package reproduces529/600,468/529,468/468,61unresolved and2e-66. These overlap earlier component coverage and are not added to previous test totals. Fifteen production/package paths are prepared but not applied. A developer host test expected the wrong rejection layer; its one-line expectation was corrected after final unit completion, without production edits. Nine final host modules are running; full Workflow/root admission is unfinished. Live service and executed input/producer linkage remain unverified."
    elif row["id"] == "C-L207-ComparativeSystems":
        row["overall"] = "native_source_and_closed_contract_reviewed_native_sheet_and_calculators_assigned"
        row["source_presence"] = "native_application_and_exact_producer_helper_sources_retained_with_eight_source_executed_synthetic_cases"
        row["tool_information"] = "resource_specific_name_description_instructions_drafted_not_registered"
        row["numerical_sheet"] = "closed_numerical_sheet_contract_defined_native_builder_assigned_unfinished"
        row["native_parser"] = "six_source_profiles_defined_native_parser_assigned_unfinished"
        row["metadata_extractor"] = "qualified_Data_population_handoff_defined_extractor_unassigned"
        row["deterministic_calculator"] = "all_quantity_interfaces_defined_fresh_calculator_work_assigned_unfinished"
        row["numerical_verification"] = "123contract_checks_27examples_eight_source_executed_synthetic_cases_no_production_grader_test"
        row["evidence_ids"].append(comparative_evidence["id"])
        row["note"] += " Update037: reviewed source-defined TSV-in-JSON views, first-object loss, real population denominators, ambiguous hex overflow and malformed variant matrix. Eight unchanged-source synthetic cases and123contract checks over115definitions/27examples pass. Root closed analysis/population IDs, producing-evidence mapping, calculated-scalar selection and acyclic data-only helpers before fresh N187/C188 coding in isolated186. D/P/I exact boundaries remain planned and unassigned. No production grader, actual episode path or successful live native response is established."
for row in work["resource_bindings"]:
    if row["id"] == "C-L206-GenomeComparison::api":
        row["production_result_binding"] = "legacy_applied_directional_v2_candidate_final_host_verification_running"
        row["integration_verification"] = "737candidate_unit_checks_and_installed_facade_pass_full_host_and_Workflow_pending"
        row["evidence_ids"].append(candidate_evidence["id"])
    elif row["id"] == "C-L207-ComparativeSystems::api":
        row["evidence_ids"].append(comparative_evidence["id"])

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
    "previous_goal_turn_classification": "no_progress",
    "previous_goal_turn_evidence": "Previous user-question turn clarified inventory wording; it did not advance implementation.",
    "this_goal_turn_classification": "progress",
    "current_progress": "737 frozen candidate unit cases and installed package verification passed. Final host verification started after a reviewed test-only correction. Closed and accepted ComparativeSystems interfaces and assigned fresh independent N/C coding workers.",
    "changes": changes, "added_evidence": new_evidence, "scope_changes": False,
    "specific_pending_NCBI_job_verification_included": False,
    "complete_scientific_tools_claimed": 0,
}
with (HERE / "PROGRESS_UPDATE_037.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
PATH.write_bytes(updated)
print(json.dumps({"checkpoint": 37, "changed_rows_and_bindings": len(changes),
                  "scope_rows": 308, "resource_bindings": 288,
                  "status_sha256": record["new_status_sha256"]}))
