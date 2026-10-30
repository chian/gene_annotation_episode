"""Append verified library/return work and the isolated submitted-input repair."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
status_path = HERE / "WORK_STATUS.json"
raw = status_path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == "632efb1808990689a0cf292239795b9571780593fbd44de075d9884826fe554c"
assert not (HERE / "PROGRESS_UPDATE_032.json").exists()
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert hashlib.sha256(authority.read_bytes()).hexdigest() == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
work = json.loads(raw)
original = deepcopy(work)
scope_raw = (HERE / work["scope_file"]).read_bytes()
scope_sha = hashlib.sha256(scope_raw).hexdigest()
scope = json.loads(scope_raw)


def read(path):
    return json.loads((ROOT / path).read_text())


def hashed(path):
    return {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def junit(path):
    return {key: sum(int(s.get(key, "0")) for s in ET.parse(ROOT / path).getroot().iter("testsuite"))
            for key in ("tests", "failures", "errors", "skipped")}


base = "verification/tool_graders_bvbrc_proteome_data_contracts_2026-10-25/"
library = "verification/tool_graders_bvbrc_proteome_tool_info_2026-10-25/"
returns = "verification/tool_graders_bvbrc_proteome_returns_2026-10-25_174/"
submitted = "verification/tool_graders_bvbrc_proteome_submission_binding_2026-10-25_175/"
integration = "verification/tool_graders_bvbrc_proteome_api_integration_2026-10-25_176/"
assert junit(library + "pytest_001.xml") == dict(tests=22, failures=0, errors=0, skipped=0)
library_record = read(library + "VERIFICATION_001.json")
for row in library_record["files"]:
    assert hashed(row["path"])["sha256"] == row["sha256"], row["path"]
assert library_record["actual_library_freeze_and_resolution"] and not library_record["production_provider_registered"]
returns_record = read(returns + "FINAL_VERIFICATION_001.json")
assert returns_record["current_tests"]["distinct_current_cases_verified"] == 113
for path, expected in returns_record["source_sha256"].items():
    assert hashed(path)["sha256"] == expected, path
assert returns_record["example_values"]["mean_identity_fraction"] == .4375
assert returns_record["example_values"]["observed_zero_identity_percent"] == 0
assert returns_record["example_values"]["executed_reference_denominator"] is None
assert junit(submitted + "pytest_009.xml") == dict(tests=954, failures=17, errors=0, skipped=0)
assert junit(submitted + "pytest_projection_correction_011.xml") == dict(tests=17, failures=0, errors=0, skipped=0)
assert junit(submitted + "pytest_preparation_review_010.xml") == dict(tests=6, failures=0, errors=0, skipped=0)
failed = {(t.attrib["classname"], t.attrib["name"]) for t in ET.parse(ROOT / (submitted + "pytest_009.xml")).getroot().iter("testcase") if t.find("failure") is not None}
fixed = {(t.attrib["classname"], t.attrib["name"]) for t in ET.parse(ROOT / (submitted + "pytest_projection_correction_011.xml")).getroot().iter("testcase")}
assert failed == fixed and len(fixed) == 17
manifest = read(submitted + "DELTA_MANIFEST_002.json")
assert hashed(submitted + "DELTA_002.patch")["sha256"] == manifest["patch_sha256"]
assert len(manifest["files"]) == 14
for row in manifest["files"]:
    assert hashed(submitted + "candidate/" + row["path"])["sha256"] == row["candidate_sha256"], row["path"]
    if row["kind"] == "new":
        assert not (ROOT / row["path"]).exists(), row["path"]
    else:
        assert hashed(row["path"])["sha256"] == row["before_sha256"], row["path"]
assert junit(integration + "TEST_001.xml") == dict(tests=11, failures=1, errors=0, skipped=0)
assert junit(integration + "TEST_002.xml") == dict(tests=6, failures=0, errors=0, skipped=0)

added = [
    {
        "id": "BVBRC-PROTEOME-TOOL-INFORMATION-032",
        "kind": "actual_tool_information_and_invocation_schema_component",
        "summary": "One resource-specific GenomeComparison tool entry supplies name, description, resources and instructions with actual API assignment and launch/results commission contracts. 22 focused tests pass, including real ScientificToolLibrary freeze/selection and API assignment validation.",
        "qualification": "Production catalog registration remains unfinished. Schema acceptance does not prove runtime usability: subsequent actual host integration exposed the future-artifact identity defect in the original native document selector. Additive handoff019 defines the correction; this receipt does not claim that correction is implemented.",
        "reports": [hashed(path) for path in (library + "VERIFICATION_001.json", library + "pytest_001.xml", base + "TOOL_INFORMATION_HANDOFF_016.md", "gene_annotation_episode/bvbrc_proteome_tool_info.py", "tests/test_bvbrc_proteome_tool_info.py")],
    },
    {
        "id": "BVBRC-PROTEOME-TYPED-RETURNS-032",
        "kind": "isolated_actual_custody_and_typed_return_binder",
        "summary": "Eight finite fact families bind to original requested fields, saved numerical values, actual source custody and immediate-child relationships. Runs003 and005 verify113 distinct current cases with five overlapping cases; production binder/dependencies unchanged between successful runs.",
        "qualification": "The example uses actual provider, Store, Journal, custody and TypedReportContract with a controlled publication envelope. It is not the full AppService publication path, a complete Workflow, live-service verification or controller-credit proof. Production dispatch remains unfinished.",
        "example": deepcopy(returns_record["example_values"]),
        "reports": [hashed(path) for path in (returns + "FINAL_VERIFICATION_001.json", returns + "FINAL_VERIFICATION_001.md", returns + "RUN_003.json", returns + "RUN_005.json", returns + "TEST_ONLY_FOLLOWUP_005.patch", returns + "example_001/RECEIPT.json", returns + "INTEGRATION_HANDOFF_001.md", "gene_annotation_episode/bvbrc_proteome_returns.py")],
    },
    {
        "id": "BVBRC-PROTEOME-SUBMITTED-INPUT-CANDIDATE-032",
        "kind": "isolated_submitted_request_binding_candidate_not_applied",
        "summary": "Real retained request_ref bytes and exact /prepared/native_operands/call/rpc_request/params/1 feed the original-input constructor. Nine content-binding enums across six assets gain request_ref. Candidate contains14 exact changed paths.937 passing cases plus17 corrected projection-fixture cases cover954 current cases across separate receipts; six additional preparation-corruption checks pass.",
        "qualification": "Not one954-pass run;17 original failures and their later correction remain recorded. Original production is unchanged. This supports real controlled submission/custody and pure-provider construction, not complete artifact publication, a live GenomeComparison task or full episode integration.",
        "candidate_patch_sha256": manifest["patch_sha256"],
        "reports": [hashed(path) for path in (submitted + "HANDOFF_001.md", submitted + "FINAL_RECEIPT_001.json", submitted + "DELTA_MANIFEST_002.json", submitted + "PATCH_APPLICATION_RECEIPT_002.json", submitted + "pytest_009.xml", submitted + "pytest_projection_correction_011.xml", submitted + "pytest_preparation_review_010.xml", submitted + "SOURCE_GUARD_AFTER_001.json", submitted + "SCHEMA_AND_ASSERTION_GUARD_001.json", submitted + "example_001/RECEIPT.json")],
    },
    {
        "id": "BVBRC-PROTEOME-INTEGRATION-CONTRACT-GAP-032",
        "kind": "concrete_host_defect_and_bounded_candidate_work_in_progress",
        "summary": "Actual frozen assignment requires a native source/artifact identity that does not exist until acquisition; source creation itself includes the assignment digest. Handoff019 supplies a second selector by existing requested-output requirement, retained actual acquisition membership, unique resolution and saved-bundle validation. Worker176 owns that candidate correction and host integration; worker177 independently defines full directional-report calculations before coding.",
        "qualification": "The correction is specified and assigned, not verified complete. Candidate frame/catalog tests passed11 distinct cases before this extension (10passes/1fixture failure, then6catalog passes). Those tests do not establish native artifact publication. Missing native joins, execution witnesses and full directional calculations remain unfinished.",
        "reports": [hashed(path) for path in (base + "API_INTEGRATION_HANDOFF_017.md", base + "DIRECTIONAL_CALCULATION_BOUNDARY_018.md", base + "PREACQUISITION_SELECTION_HANDOFF_019.md", integration + "TEST_001.xml", integration + "TEST_002.xml")],
    },
]
new_ids = [e["id"] for e in added]
assert not set(new_ids) & {e["id"] for e in work["verification_evidence"]}
work["verification_evidence"].extend(added)
for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row.update(overall="library_and_return_components_verified_host_integration_candidate_in_progress",
            source_presence="all24native_definitions_and17proteome_modules_five_schema_assets_present",
            tool_information="real_name_description_resources_instructions_and_invocation_component22checks_catalog_registration_unfinished",
            invocation_contract="actual_API_assignment_schema_tested_submitted_request_repair_verified_only_in_isolated_candidate",
            production_result_binding="typed_return_binder_verified_in_isolation_actual_native_host_publication_blocked_by_future_identity_contract",
            integration_verification="library22_and_typed_return113distinct_checks_submitted_candidate954cases_across_receipts_full_path_unfinished")
        row["evidence_ids"].extend(new_ids)
        row["note"] += " Update032: new tool-information component has22checks and actual library selection. Typed return binder has113distinct current cases; synthetic numerical example preserves0.4375, observed0 and missing executed denominators. Submitted-source repair has954current candidate cases across retained receipts, not one green run, and remains unapplied. Fresh176 candidate adds registry/host/return ports; actual acquisition revealed a circular frozen selector requiring future source/artifact identities.019 defines an explicit requirement-based selection and retained acquisition membership; implementation/testing continue.177 defines full directional numerical contracts independently. Full artifact publication, episode/presentation/live verification, producer witnesses and complete directional scientific calculations remain unfinished. Same308tool/mode and288resource rows;0complete scientific tools claimed."
for row in work["resource_bindings"]:
    if row["id"] == "C-L206-GenomeComparison::api":
        row["evidence_ids"].extend(new_ids)
        row["invocation_contract"] = "API_assignment_and_library_component_tested_submitted_source_repair_verified_only_in_isolated_candidate"
        row["production_result_binding"] = "typed_return_component_verified_full_native_publication_selector_correction_in_candidate"
        row["integration_verification"] = "library_return_and_submitted_source_component_receipts_full_host_episode_path_unfinished"

assert [r["id"] for r in work["rows"]] == [r["id"] for r in original["rows"]] == [r["id"] for r in scope["rows"]]
assert [r["id"] for r in work["resource_bindings"]] == [r["id"] for r in original["resource_bindings"]] == [r["id"] for r in scope["resource_bindings"]]
assert len(work["rows"]) == 308 and len(work["resource_bindings"]) == 288
assert work["complete_scientific_tools_claimed"] == original["complete_scientific_tools_claimed"] == 0
changes = []
for group in ("rows", "resource_bindings"):
    prior = {r["id"]: r for r in original[group]}
    changes.extend(dict(group=group, id=r["id"], before=prior[r["id"]], after=deepcopy(r)) for r in work[group] if r != prior[r["id"]])
assert len(changes) == 2
assert hashlib.sha256((HERE / work["scope_file"]).read_bytes()).hexdigest() == scope_sha
updated = (json.dumps(work, indent=2) + "\n").encode()
record = dict(schema="tool_grader_progress_update_v1", date="2026-10-25", recorded_at=datetime.now(timezone.utc).isoformat(),
    author="root", previous_status_sha256=before, new_status_sha256=hashlib.sha256(updated).hexdigest(), scope_sha256_unchanged=scope_sha,
    previous_goal_turn_classification="progress", previous_goal_turn_evidence="Checkpoint031 retained pure provider, numerical projection and native directional parsing. Inventory-wording clarification is not new implementation work.",
    this_goal_turn_classification="progress", current_progress="Verified library and return components, accepted isolated submitted-input repair and assigned actual host integration with a concrete correction to a newly observed circular selection contract. Original verification161 remains live with all814original hashes unchanged at16:50:50Z. No full-tool completion.",
    changes=changes, added_evidence=added, scope_changes=False, specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
with (HERE / "PROGRESS_UPDATE_032.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
status_path.write_bytes(updated)
print(json.dumps(dict(checkpoint=32, changed_rows_and_bindings=len(changes), scope_rows=308, resource_bindings=288, status_sha256=record["new_status_sha256"])))
