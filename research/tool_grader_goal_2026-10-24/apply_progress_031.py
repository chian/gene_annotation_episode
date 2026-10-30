"""Record verified proteome provider, requested facts and native text decoding."""
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
assert before == "df1813c3e7dd1d1d19c6e09875337a3465f09eb780ebee415ea9263fbeda95b5"
assert not (HERE / "PROGRESS_UPDATE_031.json").exists()
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
provider = "verification/tool_graders_bvbrc_proteome_bundle_2026-10-25_173/"
reader = "verification/tool_graders_bvbrc_proteome_directional_2026-10-25_172/"
projection = "verification/tool_graders_bvbrc_proteome_projection_2026-10-25/"
packaging = "verification/tool_graders_bvbrc_proteome_packaging_2026-10-25/"
assert junit(provider + "pytest_006.xml") == dict(tests=143, failures=0, errors=0, skipped=0)
assert junit(reader + "TEST_RUN_004.xml") == dict(tests=79, failures=0, errors=0, skipped=0)
assert junit(projection + "projection_pytest_003.xml") == dict(tests=120, failures=0, errors=0, skipped=0)
delivery = read(provider + "FINAL_RECEIPT_001.json")
for path, digest in delivery["owned_file_sha256"].items():
    assert hashed(path)["sha256"] == digest, path
example = read(provider + "example_001/RECEIPT.json")
for name, digest in example["dependency_sha256"].items():
    assert hashed("gene_annotation_episode/" + name)["sha256"] == digest, name
for name, digest in example["files"].items():
    assert hashed(provider + "example_001/" + name)["sha256"] == digest, name
for row in read(reader + "ARTIFACT_HASHES_001.json"):
    path = ROOT / row["file"]
    assert path.stat().st_size == row["byte_count"] and hashed(row["file"])["sha256"] == row["sha256"], row["file"]
for path, digest in read(base + "COMBINED_VERIFICATION_001.json")["source_after"].items():
    assert hashed(path)["sha256"] == digest, path
assert (example["identity_mean"], example["subject_endpoint_difference_mean"], example["selected_before"], example["selected_after"]) == (.4375, .625, 1, 0)
assert example["saved_sheet_unchanged"] and example["executed_reference_count"] is None
wheel = read(packaging + "WHEEL_VERIFICATION_003.json")
assert wheel["all_modules_from_wheel"] and len(wheel["module_origins"]) == 15
assert wheel["complete_provider_result_matches_saved_example"]
assert wheel["matching_saved_reprojection_and_changed_parameter_calculation"]
assert wheel["matching_retained_native_reports"] == 3
assert wheel["native_query_subject_hsp_counts"] == [[1, 0, 0], [2, 23, 25], [3, 3, 4]]
assert wheel["io_network_execution_blocked_during_pure_calls"] and not wheel["live_or_episode_execution_claimed"]
assert read(packaging + "CONFIG_CHANGE_002.json")["pytest_configuration_unchanged"]

provider_id = "BVBRC-PROTEOME-PROVIDER-PROJECTION-031"
reader_id = "BVBRC-PROTEOME-DIRECTIONAL-NATIVE-031"
provider_evidence = {
    "id": provider_id,
    "kind": "pure_provider_actual_constructors_requested_projection_and_wheel_verified",
    "summary": "New pure provider composes actual native parsing, five input extractors, explicit joins, numerical sheet, calculators and finite requested-fact projection. Closed saved validation preserves original supplied values and constructor outputs. Current final143focused tests pass:21provider contracts/facade,39resolution,66fact contracts,17projection. No scientific result constructors are stubbed.",
    "qualification": "Provider is not registered in production yet. Its full B1 example uses explicitly synthetic effective-parameter evidence; current host sets effective_parameters null. Submitted request_ref route, actual AppService publication/custody and episode delivery remain unfinished. Raw legacy data do not establish exact executed denominators or full scientific GenomeComparison capability.",
    "example": {"identity_mean": .4375, "legacy_subject_endpoint_difference_mean": .625,
                "selected_before": 1, "selected_after": 0, "executed_reference_count": None,
                "original_sheet_unchanged": True},
    "root_corrections": "CellFact now enforces state=value iff numerical value is present; request-specific failures retain actual saved scope and attach only to their requested field. A nonexisting target does not gain an invented saved identity. Earlier failed detached-schema test receipt remains.",
    "packaging": "Two additional explicit schema assets packaged. Isolated Python-I loads15modules from the built wheel and reproduces complete provider result, saved requested facts, changed-parameter components and all3native report projections with IO/network/execution blocked after packaged schema initialization. First cold-start attempt caught lazy packaged-schema load; failed receipt/script retained.",
    "implementation_sha256": delivery["implementation_sha256"],
    "reports": [hashed(path) for path in (
        provider + "HANDOFF_001.md", provider + "FINAL_RECEIPT_001.json", provider + "pytest_006.xml",
        provider + "example_001/RECEIPT.json", projection + "projection_pytest_002.xml", projection + "projection_pytest_003.xml",
        base + "PROJECTION_REVIEW_CORRECTIONS_011.md", base + "SUBMITTED_PARAMETER_BINDING_GAP_012.md",
        base + "RETURN_BINDER_HANDOFF_013.md", base + "SUBMITTED_PARAMETER_REPAIR_HANDOFF_014.md",
        base + "SUBMISSION_REPAIR_CLARIFICATION_015.md", packaging + "CONFIG_CHANGE_002.json",
        packaging + "wheel_check_002.log", packaging + "WHEEL_VERIFICATION_003.json",
        "gene_annotation_episode/bvbrc_proteome_fact_contracts.py", "gene_annotation_episode/bvbrc_proteome_bundle_projection.py")],
}
reader_evidence = {
    "id": reader_id,
    "kind": "retained_native_legacy_BLASTP_directional_reader_and_saved_validation",
    "summary": "Independent text reader retains every displayed query, description, subject, HSP and traceback for reviewed BLASTP2.0.11/2.2.2/2.2.21. Decimal strings preserve nonzero underflowing E-values; missing native gaps remain missing. Contradictory native observations stay present with required consistency issues.79focused tests passed;275prefix-cut probe retained separately.",
    "qualification": "Public Biopython native report bytes are real format examples, not a BV-BRC service task or deployed-version observation. B2/B3 attachment, actual executed-input and occurrence witnesses, complete-hit scientific calculators and live/episode paths remain unfinished. Example HSP arithmetic is inspection, not a newly bound general calculator.",
    "example": {"release_2221_descriptions": 30, "release_2221_aligned_subjects": 3, "release_2221_hsps": 4,
                "second_query_hsp_identities": [[353, 414], [115, 115]],
                "second_query_union_span": [529, 600], "second_query_disjoint_identity_counts": [468, 529]},
    "reports": [hashed(path) for path in (reader + "VERIFICATION_001.md", reader + "ARTIFACT_HASHES_001.json",
        reader + "TEST_RUN_004.xml", reader + "NUMERICAL_CHECKS_001.json", reader + "SAVED_REPLAY_001.json",
        reader + "TRUNCATION_PROBE_001.json", reader + "SOURCE_INPUTS_001.json",
        "gene_annotation_episode/bvbrc_proteome_directional.py", "gene_annotation_episode/bvbrc_proteome_directional_contracts.py",
        "gene_annotation_episode/bvbrc_proteome_directional_schemas.json")],
}
added = [provider_evidence, reader_evidence]
assert not {e["id"] for e in added} & {e["id"] for e in work["verification_evidence"]}
work["verification_evidence"].extend(added)
for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row.update(overall="pure_provider_and_native_directional_reader_verified_full_execution_and_episode_path_unfinished",
            source_presence="all24native_definitions_and15proteome_modules_five_schema_assets_packaged",
            native_parser="legacy_custom_JSON_TSV94synthetic_checks_and_directional_text79checks_with_retained_public_native_reports_no_BV_BRC_task",
            numerical_verification="prior637pure_checks_sources_unchanged_plus143provider_projection_and79directional_checks_no_full_tool_claim",
            integration_verification="pure_provider_saved_requested_projection_and_isolated_wheel_verified_actual_API_and_episode_path_unfinished")
        row["evidence_ids"].extend([provider_id, reader_id])
        row["note"] += " Update031:actual pure provider and finite requested facts now implemented;143focused checks pass. Standalone full directional text reader has79checks against three retained public native reports. Installed wheel reproduces both and saved recalculation without input acquisition. Current submitted request binding remains unavailable; fresh175repairs it only in an isolated candidate. Fresh174owns typed returns. Production dispatch/library/episode/prompt verification, authentic producer/input/occurrence witnesses, full directional attachment/calculators and live execution remain unfinished. All original scope rows retained;0complete scientific tools claimed."
for row in work["resource_bindings"]:
    if row["id"] == "C-L206-GenomeComparison::api":
        row["evidence_ids"].extend([provider_id, reader_id])
        row["integration_verification"] = "pure_provider_saved_requested_projection_and_isolated_wheel_verified_actual_API_and_episode_path_unfinished"
        row["native_format_observed"] = "retained_public_legacy_BLASTP_reports_observed_BV_BRC_task_output_and_deployment_still_unverified"

assert len(work["rows"]) == len(original["rows"]) == len(scope["rows"]) == 308
assert len(work["resource_bindings"]) == len(original["resource_bindings"]) == len(scope["resource_bindings"]) == 288
assert work["complete_scientific_tools_claimed"] == original["complete_scientific_tools_claimed"] == 0
changes = []
for group in ("rows", "resource_bindings"):
    prior = {r["id"]: r for r in original[group]}
    assert set(prior) == {r["id"] for r in work[group]}
    changes.extend(dict(group=group, id=r["id"], before=prior[r["id"]], after=deepcopy(r))
                   for r in work[group] if r != prior[r["id"]])
assert len(changes) == 2
assert hashlib.sha256((HERE / work["scope_file"]).read_bytes()).hexdigest() == scope_sha
updated = (json.dumps(work, indent=2) + "\n").encode()
record = dict(schema="tool_grader_progress_update_v1", date="2026-10-25",
    recorded_at=datetime.now(timezone.utc).isoformat(), author="root", previous_status_sha256=before,
    new_status_sha256=hashlib.sha256(updated).hexdigest(), scope_sha256_unchanged=scope_sha,
    previous_goal_turn_classification="progress",
    previous_goal_turn_evidence="Prior implementation wrote fact/projection modules with56and16passed focused checks and dispatched scoped provider/native-reader coding. Intervening inventory-wording clarification made no implementation progress and is not counted as implementation work.",
    this_goal_turn_classification="progress",
    current_progress="Completed pure provider and requested facts, corrected cell/failure semantics, accepted retained-native directional reader, packaged two schema assets and reproduced both paths from isolated wheel. Fresh typed-return and submitted-source repair work continues; scientific goal remains active.",
    changes=changes, added_evidence=added, scope_changes=False,
    specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
with (HERE / "PROGRESS_UPDATE_031.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
status_path.write_bytes(updated)
print(json.dumps(dict(checkpoint=31, changed_rows_and_bindings=len(changes), scope_rows=308,
                     resource_bindings=288, status_sha256=record["new_status_sha256"])))
