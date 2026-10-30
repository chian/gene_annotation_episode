"""Record applied proteome API integration and separately assigned D/F work."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / "WORK_STATUS.json"
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == "74f55d714c4350a033c7ab4b2c7c64748cabddcbd750069c077869dd9595ffe9"
assert not (HERE / "PROGRESS_UPDATE_036.json").exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work["scope_file"]
scope_hash = hashlib.sha256(scope_path.read_bytes()).hexdigest()
scope = json.loads(scope_path.read_text())
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert hashlib.sha256(authority.read_bytes()).hexdigest() == work["authority_sha256"]
base = "verification/tool_graders_bvbrc_proteome_api_integration_2026-10-25_176/"


def read(name):
    return json.loads((ROOT / (base + name)).read_text())


def hashed(name):
    return {"path":name,"sha256":hashlib.sha256((ROOT/name).read_bytes()).hexdigest()}


application = read("APPLICATION_RECEIPT_001.json")
assert application["production_applied"] and len(application["files"]) == 20
assert application["distinct_passing_cases_across013_and014"] == 466
for item in application["files"]:
    assert hashlib.sha256((ROOT/item["path"]).read_bytes()).hexdigest() == item["candidate_sha256"]
applied = read("applied_verification_001/receipt.json")
assert applied["exit_code"] == 0 and not applied["changed_sources"]
assert applied["source_count"] == 867
assert [(int(s["tests"]),int(s["failures"]),int(s["errors"]),int(s["skipped"]))
        for s in applied["testsuites"]] == [(86,0,0,0)]
final = read("TEST_INDEX_FINAL_001.json")
assert final["distinct_case_identities"] == 466

evidence = {
    "id":"PROTEOME-API-INTEGRATION-APPLIED-036",
    "kind":"reviewed_native_host_publication_and_typed_returns_applied",
    "summary":"Applied176's20-file delta:13 implementation/schema/tool-information files and7 tests/fixtures. Actual configured API registry, library selection, retained acquisition/publication and all eight legacy fact families reach typed results-to-scientific-parent communication.466 distinct cases have passing stable-source receipts across013/014;013 retains one descriptor-fixture failure and014 passes the complete corrected10-case group.86 focused cases pass again in the applied checkout, with867 tracked paths unchanged; those86 are repeated checks, not extra distinct cases.",
    "numerical_example":"Controlled native fractions0.875 and0 yield mean0.4375; native endpoint-difference fractions0.750 and0.500 yield mean0.625. Changing the saved-sheet identity threshold0.6 to0.9 changes the selected-association count1 to0 without acquisition/native parsing. Endpoint difference is not full alignment coverage. Executed input denominators stay missing.",
    "qualification":"Host integration uses actual selected API operations, immutable publication and typed custody with controlled transport/native fixtures. It does not establish live BV-BRC access, full Workflow/model presentation, producer retention, executed input occurrence rosters or row-to-HSP linkage. Complete directional numerical modules remain separately applied; their v2 provider and parent-return integration is newly assigned to two fresh coding workers and unfinished. The descriptor fixture now supplies the actual launch BindingContext; production initial-context behavior was not changed.",
    "reports":[hashed(base+name) for name in (
        "APPLICATION_RECEIPT_001.json","PREFLIGHT_001.json","DELTA_MANIFEST_002.json",
        "INTEGRATION_HANDOFF_002.md","TEST_INDEX_FINAL_001.json",
        "TEST_013_core.xml","TEST_013_host.xml","TEST_014.xml",
        "NUMERICAL_ARTIFACTS_001.json","NUMERICAL_EXAMPLE_001.md",
        "applied_verification_001/receipt.json","applied_verification_001/pytest.xml")],
}
planning = {
    "id":"PROTEOME-DIRECTIONAL-PROVIDER-RETURN-ASSIGNED-036",
    "kind":"reviewed_modular_contracts_and_fresh_parallel_coding_assignments",
    "summary":"Reviewed exact provider/saved-sheet/finite-return contracts, the acyclic module import graph, fourteen receiving source families, shared selectors and nonoverlapping file ownership before assigning fresh D183 and F184. Prepared900 copied candidate files from applied179 plus verified176; no dependency candidate was mutated.",
    "qualification":"This records planning and active coding, not completed provider/return integration. D owns construction, saved validation and host publication. F owns finite facts, typed return and real tool information. Root owns packaging, combined verification and application. Known native numerical values and symbolic custody examples are design fixtures, not a live service run.",
    "reports":[hashed("verification/tool_graders_bvbrc_proteome_directional_provider_contract_2026-10-25_181/"+name)
               for name in ("PROVIDER_CONTRACT_001.md","RETURN_CONTRACT_002.md",
                            "IMPLEMENTATION_HANDOFF_003.md","REVIEW_CLOSURE_004.md",
                            "VERIFICATION_CASES_005.md","WORKED_RETAINED_EXAMPLE_006.md")]
              + [hashed("verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182/COMPOSITION_RECEIPT_001.json")],
}
assert not {evidence["id"],planning["id"]}.intersection(r["id"] for r in work["verification_evidence"])
work["verification_evidence"].extend([evidence,planning])
for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row["overall"] = "legacy_API_host_integration_and_directional_numerics_applied_directional_v2_return_integration_unfinished"
        row["tool_information"] = "actual_configured_resource_library_name_description_instructions_contracts_applied_and_verified_for_legacy_provider"
        row["invocation_contract"] = "explicit_provider_pin_and_requirement_based_preacquisition_selection_applied_verified"
        row["production_result_binding"] = "legacy_actual_native_host_publication_and_typed_parent_returns_applied_directional_v2_under_implementation"
        row["integration_verification"] = "466distinct_stable_candidate_cases_including11controlled_host_cases_86focused_applied_checks_full_Workflow_and_live_unverified"
        row["evidence_ids"].extend([evidence["id"],planning["id"]])
        row["note"] += " Update036:176's20-file delta applied:13 production/schema/tool-info files and7 test/fixture files. Parent requirement selection can be frozen before acquisition without inventing future source IDs. Actual acquisition membership, custody, original task, saved sheet and requested facts are checked.466distinct cases have passing stable-source receipts across013/014;013's descriptor-fixture failure remains recorded, and only that fixture changed before014's10 passes.86focused applied-checkout tests pass with867tracked paths unchanged; these repeat existing cases. Eleven controlled host cases cover actual publication and typed custody, not full Workflow or live BV-BRC. Identity/endpoint means remain0.4375/0.625, saved threshold recalculation1->0; missing executed denominators stay missing. Applied179 numerical modules are unchanged. Exact181 D/F contracts and182's900-file isolated base were prepared before fresh D183/F184 coding; directional provider and typed return remain unfinished. Inventory identities/scope are unchanged, not repaired and not counted as implementation progress."
for row in work["resource_bindings"]:
    if row["id"] == "C-L206-GenomeComparison::api":
        row["invocation_contract"] = "explicit_configured_provider_and_parent_requirement_selection_applied_verified"
        row["production_result_binding"] = "legacy_actual_native_publication_and_typed_return_path_applied_directional_v2_pending"
        row["integration_verification"] = "11controlled_native_host_cases_and86focused_applied_checks_full_Workflow_and_live_unverified"
        row["evidence_ids"].extend([evidence["id"],planning["id"]])
changes = []
for group,count in (("rows",308),("resource_bindings",288)):
    assert len(work[group]) == count
    assert [r["id"] for r in work[group]] == [r["id"] for r in original[group]] == [r["id"] for r in scope[group]]
    prior = {r["id"]:r for r in original[group]}
    changes.extend({"group":group,"id":r["id"],"before":prior[r["id"]],"after":deepcopy(r)}
                   for r in work[group] if r != prior[r["id"]])
assert len(changes) == 2 and work["complete_scientific_tools_claimed"] == 0
assert hashlib.sha256(scope_path.read_bytes()).hexdigest() == scope_hash
updated = (json.dumps(work,indent=2)+"\n").encode()
record = {
    "schema":"tool_grader_progress_update_v1","date":"2026-10-25",
    "recorded_at":datetime.now(timezone.utc).isoformat(),"author":"root",
    "previous_status_sha256":before,"new_status_sha256":hashlib.sha256(updated).hexdigest(),
    "scope_sha256_unchanged":scope_hash,
    "previous_goal_turn_classification":"progress",
    "previous_goal_turn_evidence":"Checkpoint035 applied numerical179 and verified319distinct cases in candidate and production.",
    "this_goal_turn_classification":"progress",
    "current_progress":"Applied verified176 native host/typed-return integration;86focused applied checks passed. Defined exact181 interfaces and composed182 before launching fresh parallel coding D183/F184. No whole-tool completion claim.",
    "changes":changes,"added_evidence":[evidence,planning],"scope_changes":False,
    "specific_pending_NCBI_job_verification_included":False,"complete_scientific_tools_claimed":0,
}
with (HERE/"PROGRESS_UPDATE_036.json").open("x") as stream:
    json.dump(record,stream,indent=2)
    stream.write("\n")
path.write_bytes(updated)
print(json.dumps({"checkpoint":36,"changed_rows_and_bindings":len(changes),
                  "scope_rows":308,"resource_bindings":288,"status_sha256":record["new_status_sha256"]}))
