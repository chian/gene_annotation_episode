"""Record full alignment verification and the completed proteome input modules."""
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
assert before == "f84d0129b1104cb9e684b2a25d026e8fa26caca439bd53fefd57152e0f7343bd"
assert not (HERE / "PROGRESS_UPDATE_029.json").exists()
work = json.loads(raw)
old = deepcopy(work)


def hashed(name):
    return {"path": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}


def read(name):
    return json.loads((ROOT / name).read_text())


def junit(name):
    return {key: sum(int(s.get(key, "0")) for s in ET.parse(ROOT / name).getroot().iter("testsuite"))
            for key in ("tests", "failures", "errors", "skipped")}


alignment = "verification/tool_graders_bvbrc_alignment_workflow_2026-10-25_162/"
candidate = "verification/tool_graders_form_reference_validation_2026-10-25/"
inputs = "verification/tool_graders_bvbrc_proteome_inputs_2026-10-25_166/"
contracts = "verification/tool_graders_bvbrc_proteome_data_contracts_2026-10-25/"
proposal = "verification/tool_graders_bvbrc_proteome_sheet_contract_2026-10-25_165/"
assert junit(alignment + "pytest.junit.xml") == dict(tests=12, failures=0, errors=0, skipped=0)
assert junit(candidate + "candidate-workflow-006.xml") == dict(tests=6, failures=0, errors=0, skipped=0)
assert junit(inputs + "TEST_RUN_003.xml") == dict(tests=237, failures=0, errors=0, skipped=0)
assessment = read(alignment + "assessment.json")
assert assessment["terminal"]["returncode"] == 0 and assessment["process_launch_count"] == 1
assert assessment["broad_source_changes"] == []
candidate_pass = read(candidate + "CANDIDATE_WORKFLOW_PASS_003.json")
assert not candidate_pass["production_applied"]
assert candidate_pass["replay"]["counts_before"] == candidate_pass["replay"]["counts_after"]
assert candidate_pass["replay"]["new_http_calls"] == 0
assert len(candidate_pass["replay"]["blocked_scientific_implementations_and_aliases"]) == 173
assert hashed("gene_annotation_episode/bvbrc_proteome_inputs.py")["sha256"] == "66fc298dda9e250f86a0ffa9dc27636f9ae1ee33c4c640fd4a25c1ff28cc1df4"
assert hashed("gene_annotation_episode/bvbrc_proteome_data_contracts.py")["sha256"] == "12a8aaa5cdc0006e3fab6d8e083139a8ab04a91bf1aa65b202a0ca1d5ac46381"

alignment_id = "BVBRC-ALIGNMENT-FULL-WORKFLOW-029"
alignment_evidence = {
    "id": alignment_id, "kind": "completed_controlled_full_Workflow_suite",
    "summary": "Original single12test process completed exit0 after5871.78seconds. OrdinaryMSA, MetaCATS and XMFA each passed all4checks, both typed parent boundaries, practical exact-zero endpoints, one own action/observation and strict saved replay. Every AFTER_TESTS used-source guard passed; only unrelated unimported additions occurred.",
    "qualification": "Actual production Workflow/custody/HTTP/parser/calculator/return paths with controlled loopback service responses and scripted choices over retained native byte examples. No live BV-BRC, new native program, configured-model annotation or generic prompt completion claim.",
    "examples": {"MSA": {"members": 4, "cells": 28, "gaps": 6, "entropy_bits": .9182958340544896, "native_score": 92},
        "MetaCATS": {"chi_square": 8.330556481172943, "calculated_p": .0038983714243371837, "native_p": .00389837142433717, "counts": [6, 0, 0, 6]},
        "XMFA": {"blocks": 6, "identical": 39, "substitutions": 7, "comparable": 46, "identity_fraction": 39 / 46}},
    "reports": [hashed(alignment + name) for name in ("assessment.json", "REPORT.md", "pytest.junit.xml",
        "case-msa_dna.json", "case-metacats_files.json", "case-xmfa_blocks.json")],
}
candidate_id = "FORM-VALIDATION-FULL-CANDIDATE-029"
candidate_evidence = {
    "id": candidate_id, "kind": "isolated_complete_Workflow_verified_not_applied",
    "summary": "Candidate006 passed all6GenomeAlignment Workflow tests in971.274seconds. Both300used-path guards unchanged; saved replay blocked173 scientific/parser implementations and aliases, preserved26actions/27calls/26observations/215receipts/5reports and made zero HTTP calls. Exact numerical parents, future-zero practical endpoints, original partial action ordering and explicit saved recalculation verified.",
    "qualification": "Still isolated; production validation source is unchanged while original run161 continues. No method_loop/controller change. Controlled HTTP/scripted choices with retained Mauve native bytes, not live service or native execution.",
    "retained_failures": "004: test compared REASONING model role to episode role.005:5passed/1failed because test expected request-selector manifest_member in saved task association, whose valid kind is task_result_manifest.006 corrects those test selectors and restores parser owners before strict alias-discovery. Earlier receipts preserved.",
    "reports": [hashed(candidate + name) for name in ("candidate-workflow-004.xml", "candidate-workflow-005.xml",
        "candidate-workflow-006.xml", "CANDIDATE_WORKFLOW_FAILURE_REVIEW_001.json", "CANDIDATE_WORKFLOW_REVIEW_002.md",
        "CANDIDATE_WORKFLOW_PASS_003.json", "CANDIDATE_TEST_SOURCE_005.py", "CANDIDATE_TEST_SOURCE_006.py")],
}
input_id = "BVBRC-PROTEOME-SUPPLIED-INPUTS-029"
input_evidence = {
    "id": input_id, "kind": "implemented_supplied_input_extraction_and_saved_data_validation",
    "summary": "Five B1 functions implemented: proteinFASTA inventory, feature/genome/feature-sequence JSON snapshots and original parameter-input indexing. Separate B0 validates closed saved data, exact source/ordinal/count/digest relationships, meaningful missing states and recorded input order.237tests passed:185B1+52B0. Eight saved synthetic supplied-input examples replayed exactly under final source.",
    "qualification": "Supporting extraction only, no fabricated scientific confidence. Inputs are explicitly synthetic supplied bytes, not native GenomeComparison output. Inventories do not prove executed membership. Joins, aggregate sheets/calculators, qualified execution/occurrence witness, full directional reports, actual service data, application binding and complete episode integration remain unfinished.",
    "example": {"supplied_bytes": 59, "observed_records": 3, "complete_records": 3, "valid_records": 1,
        "normalized_sequences": ["ACDE", "AA-?1", ""], "symbol_counts": [4, 5, 0],
        "invalid_empty_sequences_keep_actual_hashes": True, "incomplete_record_sequence_count_hashes": None},
    "contract_repairs": ["Proposal001 lacked decoded execution witnesses: correction002 keeps locator-only claims unqualified and leaves the real witness interface unfinished.",
        "OriginalTask lacks submitted digest/pointer when effective parameters are selected: optional additional_parameter_sources now supplies actual source locations; absent submitted provenance remains partial, never fabricated.",
        "B0 public boundary now translates excessive JSON nesting to a fixed typed failure; original failing probe remains saved."],
    "reports": [hashed(name) for name in (inputs + "TEST_RUN_003.xml", inputs + "VERIFICATION_RECEIPT_001.json",
        inputs + "EXAMPLE_REPLAY_002.json", inputs + "FILLED_SUPPLIED_INPUT_EXAMPLES_001.json", inputs + "FAILURE_PROBE_001.json",
        contracts + "B1_FREEZE_001.md", contracts + "B1_PARAMETER_SOURCES_002.md", contracts + "FREEZE_RECEIPT_001.json",
        proposal + "REVIEW_CORRECTION_002.md", proposal + "VERIFICATION_001.json", proposal + "VERIFICATION_002.json",
        "gene_annotation_episode/bvbrc_proteome_data_contracts.py", "gene_annotation_episode/bvbrc_proteome_data_schemas.json",
        "gene_annotation_episode/bvbrc_proteome_inputs.py", "tests/test_bvbrc_proteome_data_contracts.py", "tests/test_bvbrc_proteome_inputs.py")],
}
added = [alignment_evidence, candidate_evidence, input_evidence]
assert not {r["id"] for r in added} & {r["id"] for r in work["verification_evidence"]}
work["verification_evidence"].extend(added)

for row in work["rows"]:
    if row["id"] == "C-L206-GenomeComparison":
        row.update(overall="native_projection_and_supplied_input_components_verified_application_path_unfinished",
            metadata_extractor="five_supplied_input_extractors185tests_plus52saved_data_validation_tests_passed_joins_unfinished",
            numerical_sheet="native_numeric_sheet_contract_reviewed_builder_unfinished",
            deterministic_calculator="native_summary_formula_contract_frozen_fresh_parallel_implementation_in_progress",
            numerical_verification="native_parser94tests_and_supplied_input_B0_B1_237tests_verified_no_full_scientific_sheet_or_application_path")
        row["evidence_ids"].append(input_id)
        row["note"] += (" Update029:five pure supplied-input extractors and separate saved-data validator implemented and tested; exact source relationships, duplicate occurrences, invalid/empty versus incomplete sequence meanings retained. Native aggregate calculations and shared sheet validation are now separate fresh coding workloads. B2/B3 construction, actual execution witnesses/full reports and application/episode integration remain unfinished; no scope reduction or full-tool claim.")
    elif row["id"] in ("C-L202-GenomeAlignment", "C-L204-MSA", "C-L205-MetaCATS"):
        row["evidence_ids"].append(candidate_id)
        row["note"] += " Update029:isolated form-validation candidate now passes all6GenomeAlignment Workflow checks, still not applied to production while originalrun161 finishes. Original failure receipts and correct source pins preserved."
        if row["id"] != "C-L202-GenomeAlignment":
            row["evidence_ids"].append(alignment_id)
            row["integration_verification"] = ("ordinary_MSA_and_XMFA_all8checks_passed_in_original12test_Workflow_suite" if row["id"] == "C-L204-MSA" else "MetaCATS_all4checks_passed_in_original12test_Workflow_suite")
            row["note"] += " Original full12test MSA/MetaCATS/XMFA suite completed with all source guards and saved replay unchanged; live-service and configured-model/prompt limitations remain."
        else:
            row["integration_verification"] = "isolated_candidate_all6_Workflow_checks_passed_original_run_pending_candidate_not_applied"
for binding in work["resource_bindings"]:
    target = binding["id"].removesuffix("::api")
    if binding["id"].endswith("::api") and target in ("C-L202-GenomeAlignment", "C-L204-MSA", "C-L205-MetaCATS", "C-L206-GenomeComparison"):
        if target == "C-L206-GenomeComparison":
            binding["evidence_ids"].append(input_id)
        else:
            binding["evidence_ids"].append(candidate_id)
            binding["integration_verification"] = next(r["integration_verification"] for r in work["rows"] if r["id"] == target)
            if target != "C-L202-GenomeAlignment":
                binding["evidence_ids"].append(alignment_id)

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
record = {"schema": "tool_grader_progress_update_v1", "date": "2026-10-25",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "author": "root",
    "previous_status_sha256": before, "new_status_sha256": hashlib.sha256(updated).hexdigest(),
    "current_progress": "Full12test alignment suite and isolated6test GenomeAlignment candidate passed; five supplied-input extractors/B0 validation implemented237tests. Fresh independent calculator and saved-sheet validation coding underway. Original run161 still active; no production candidate application or full proteome capability claimed.",
    "previous_goal_turn_classification": "progress",
    "changes": changes, "added_evidence": added, "scope_changes": False,
    "specific_pending_NCBI_job_verification_included": False, "complete_scientific_tools_claimed": 0}
with (HERE / "PROGRESS_UPDATE_029.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
path.write_bytes(updated)
print(json.dumps({"checkpoint": 29, "changed_rows_and_bindings": len(changes),
    "scope_rows": 308, "resource_bindings": 288, "status_sha256": record["new_status_sha256"]}))
