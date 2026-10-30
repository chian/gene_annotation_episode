"""Record verified pure proteome construction/calculation and installed assets."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / "WORK_STATUS.json"
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == "f6e9dcf4ad1a1d2cf27e4020bfcc4a48fe425b7b73c4224e4fecc437b7a7ef76"
assert not (HERE / "PROGRESS_UPDATE_030.json").exists()
authority = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
assert hashlib.sha256(authority.read_bytes()).hexdigest() == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
work = json.loads(raw)
old = deepcopy(work)


def hashed(name):
    return {"path": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}


def read(name):
    return json.loads((ROOT / name).read_text())


def junit(name):
    return {key: sum(int(s.get(key, "0")) for s in ET.parse(ROOT / name).getroot().iter("testsuite"))
            for key in ("tests", "failures", "errors", "skipped")}


construction = "verification/tool_graders_bvbrc_proteome_data_contracts_2026-10-25/"
packaging = "verification/tool_graders_bvbrc_proteome_packaging_2026-10-25/"
presentation = "verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/"
combined = read(construction + "COMBINED_VERIFICATION_001.json")
assert combined["returncode"] == 0 and combined["changed_sources"] == []
assert combined["counts"] == junit(construction + "combined_pytest_001.xml") == dict(tests=637, failures=0, errors=0, skipped=0)
assert junit(construction + "b2_pytest_001.xml") == dict(tests=42, failures=1, errors=0, skipped=0)
assert junit(construction + "b2_pytest_002.xml") == dict(tests=50, failures=0, errors=0, skipped=0)
assert junit(construction + "construction_pytest_001.xml") == dict(tests=6, failures=0, errors=0, skipped=0)
for name, digest in combined["source_after"].items():
    assert hashed(name)["sha256"] == digest
example = read(construction + "construction_example_001/RECEIPT.json")
assert (example["identity_mean"], example["subject_endpoint_difference_mean"], example["selected_before"], example["selected_after"]) == (.4375, .625, 1, 0)
assert example["sheet_unchanged"] and example["supplied_inputs_unchanged"] and example["executed_reference_count"] is None
wheel = read(packaging + "WHEEL_VERIFICATION_001.json")
assert wheel["all_modules_from_wheel"] and wheel["matching_constructed_joins_sheet_components_and_changed_parameters"]
assert not wheel["live_or_episode_execution_claimed"]
assert read(packaging + "CONFIG_CHANGE_001.json")["pytest_configuration_unchanged"]

evidence_id = "BVBRC-PROTEOME-NATIVE-SHEET-030"
evidence = {
    "id": evidence_id,
    "kind": "implemented_pure_native_joins_sheet_calculators_and_packaged_assets",
    "summary": "Actual A/B1/B2/B3/B4 composition implemented and verified. B2 preserves explicit original input mapping, duplicate occurrence ambiguity, exact ID/sequence/metadata relationships and local rejected requests. B3 constructs numerical sheets with exact native cells and explicit alternate representations. B4 calculates inspectable native descriptive components and repeats with changed parameters from saved data. Final combined637tests passed with unchanged recorded sources; includes6actual pure composition checks.",
    "qualification": "Synthetic supplied bytes and saved examples only. No live native GenomeComparison job, qualified executed-input denominator/full directional reports or selected API/episode result integration is claimed. Supplied counts remain distinct from executed membership. This is useful legacy-native data processing, not the complete scientific capability required by the goal.",
    "counts": {"native_parser": 94, "input_validation": 52, "input_extractors": 185, "sheet_validation": 124,
               "joins": 50, "sheet_builder": 72, "calculators": 54, "pure_composition": 6, "combined": 637},
    "example": {"native_identity_percentages": [87.5, 0], "native_identity_mean": .4375,
                "native_subject_endpoint_difference_mean": .625, "bound_references": 2, "bound_subjects": 2,
                "selected_before": 1, "selected_after": 0, "executed_denominator": None, "sheet_unchanged": True},
    "retained_failures": "B2first:41passed/1testfailed because expected ordering omitted B1's documented reference-first order; corrected expectation. B3first:61passed/1failed because malformed envelope was classified at final rather than initial validation; added explicit input-envelope check. Packaging build001 lacked executable build module; pip isolated wheel build002 succeeded. Original receipts retained.",
    "packaging": "Added only three explicit proteome schema assets to package data. Original run161 recorded closure excludes pyproject.toml; pytest startup configuration unchanged. Python-I verified all8pure modules loaded from extracted wheel and reproduced constructed joins/sheet/calculations exactly.",
    "reports": [hashed(name) for name in (
        construction + "COMBINED_VERIFICATION_001.json", construction + "combined_pytest_001.xml",
        construction + "b2_pytest_001.xml", construction + "b2_pytest_002.xml", construction + "construction_pytest_001.xml",
        construction + "B2_B3_VERIFICATION_001.md", construction + "construction_example_001/RECEIPT.json",
        construction + "B2_B3_CONSTRUCTION_005.md", construction + "B2_B3_OWNERSHIP_006.md",
        construction + "NEXT_INTEGRATION_BOUNDARIES_007.md",
        packaging + "CONFIG_CHANGE_001.json", packaging + "WHEEL_VERIFICATION_001.json",
        "verification/tool_graders_bvbrc_proteome_sheet_2026-10-25_169/VERIFICATION_001.md",
        "verification/tool_graders_bvbrc_proteome_sheet_validation_2026-10-25_168/RECEIPT_003.json",
        "verification/tool_graders_bvbrc_proteome_calculators_2026-10-25_167/VERIFICATION_001.md",
        "gene_annotation_episode/bvbrc_proteome_joins.py", "gene_annotation_episode/bvbrc_proteome_sheet.py",
        "gene_annotation_episode/bvbrc_proteome_calculators.py", "gene_annotation_episode/bvbrc_proteome_sheet_contracts.py",
        "gene_annotation_episode/bvbrc_proteome_sheet_schemas.json", "pyproject.toml")],
}
presentation_id = "CONTROLLED-PRESENTATION-LIMIT-030"
presentation_evidence = {
    "id": presentation_id, "kind": "read_only_limits_of_existing_controlled_Workflow_tests",
    "summary": "Candidate006 numerical/custody/accounting assertions remain passed, but all9captured scientific contexts lack action_yields; conditional yield-table assertions therefore never ran. Six separately rendered post-result STEERING blocks contain326lines/20053bytes, tracking IDs, repeated qualifications and no own-action rows despite completed controller turns.",
    "qualification": "Choices.complete bypasses ModelConnection/providers._presentation. Separately rendering captured legacy contexts does not prove how the configured provider state-frame path behaves. Role-specific TASK/STEERING decision traces, user-reviewed templates and real-provider verification remain unfinished. No prompt/runtime/source edit made by this inspection.",
    "reports": [hashed(presentation + name) for name in ("PRESENTATION_LIMIT_002.md", "CANDIDATE_PRESENTATION_INSPECTION_001.json")],
}
added = [evidence, presentation_evidence]
assert not {r["id"] for r in added} & {r["id"] for r in work["verification_evidence"]}
work["verification_evidence"].extend(added)

for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row.update(overall="native_inputs_joins_sheet_calculators_verified_full_reports_and_application_path_unfinished",
            source_presence="all24native_definitions_and_pure_proteome_modules_three_schema_assets_packaged",
            numerical_sheet="legacy_native_numeric_sheet_constructed_with_actual_A_B1_B2_outputs_verified",
            metadata_extractor="five_input_extractors_and_explicit_occurrence_metadata_joins_implemented_verified",
            deterministic_calculator="native_descriptive_components_and_saved_parameter_recalculation_implemented_verified",
            numerical_verification="637combined_current_source_checks_passed_including6actual_pure_composition_tests_synthetic_only",
            integration_verification="pure_A_B1_B2_B3_B4_and_wheel_path_verified_selected_API_and_episode_path_unfinished")
        row["evidence_ids"].append(evidence_id)
        row["note"] += " Update030:rootB2 and freshB3/B4/shared validation now compose through actual functions;637combined tests passed with unchanged sources. Full synthetic raw-input/measurement-sheet examples and changed-parameter results are retained. Installed-wheel imports reproduce them. Exact execution/occurrence witnesses, full directional reports, service/library/provider/typed-return wiring, live-resource and episode verification remain unfinished; separate170/171contract proposals underway. No tool completion claimed."
    elif row["id"] == "C-L202-GenomeAlignment":
        row["evidence_ids"].append(presentation_id)
        row["note"] += " Update030:read-only presentation inspection exposes absent action_yields in all9scripted scientific contexts and therefore vacuous conditional yield-table assertions. Numerical/custody/accounting tests remain6passed; separate20KBsteering render is not configured-provider verification. Prompt work remains open. Original baseline still pending and validation candidate unapplied."
for binding in work["resource_bindings"]:
    if binding["id"] == "C-L206-GenomeComparison::api":
        binding["evidence_ids"].append(evidence_id)
        binding["integration_verification"] = "pure_A_B1_B2_B3_B4_and_wheel_path_verified_selected_API_and_episode_path_unfinished"
    elif binding["id"] == "C-L202-GenomeAlignment::api":
        binding["evidence_ids"].append(presentation_id)

assert len(work["rows"]) == len(old["rows"]) == 308
assert len(work["resource_bindings"]) == len(old["resource_bindings"]) == 288
assert work["complete_scientific_tools_claimed"] == old["complete_scientific_tools_claimed"] == 0
changes = []
for group in ("rows", "resource_bindings"):
    original = {r["id"]: r for r in old[group]}
    assert set(original) == {r["id"] for r in work[group]}
    changes.extend({"group": group, "id": r["id"], "before": original[r["id"]], "after": deepcopy(r)}
                   for r in work[group] if r != original[r["id"]])
updated = (json.dumps(work, indent=2) + "\n").encode()
record = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-25", "recorded_at": datetime.now(timezone.utc).isoformat(),
          "author": "root", "previous_status_sha256": before, "new_status_sha256": hashlib.sha256(updated).hexdigest(),
          "current_progress": "Pure proteome joins, numerical sheet, deterministic calculators, shared validation and installed schema assets implemented;637combined tests and isolated-wheel composition pass. Producer retention and API-wiring contracts being defined independently; full tool/episode/live-resource work remains.",
          "previous_goal_turn_classification": "verified_wait",
          "previous_goal_turn_evidence": "Progress-summary turn polled original live pytestPID1056858 at2h10m32s; did not change goal/status or claim terminal.",
          "this_goal_turn_classification": "progress", "changes": changes, "added_evidence": added,
          "scope_changes": False, "specific_pending_NCBI_job_verification_included": False, "complete_scientific_tools_claimed": 0}
with (HERE / "PROGRESS_UPDATE_030.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
path.write_bytes(updated)
print(json.dumps({"checkpoint": 30, "changed_rows_and_bindings": len(changes), "scope_rows": 308,
                  "resource_bindings": 288, "status_sha256": record["new_status_sha256"]}))
