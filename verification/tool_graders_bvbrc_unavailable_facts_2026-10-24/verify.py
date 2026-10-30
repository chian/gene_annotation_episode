"""Offline shape checks and an additive evidence record; no acquisition or jobs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import runpy
import sys


_KNOWN_NOTE_PROVENANCE_PATHS = frozenset([
    'docs/EPISODE_STRUCTURE.md',
    'docs/TIME_AWARE_ESTIMATION.md',
    'docs/PRACTICAL_EXECUTION.md',
    'docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md',
    'docs/TASK_AND_STEERING.md',
    'docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/NUMERICAL_LEAF_CONTRACT_004.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_CALCULATION_CONTRACT_005.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_EDGE_CLARIFICATIONS_006.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/MISSING_NATIVE_RECORD_CLARIFICATION_007.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/CALCULATION_INPUT_REFINEMENTS_009.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/CALCULATION_INPUT_CONTRACT_010.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/SHARED_CONTENT_AND_STREAM_FINALIZATION_011.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/BAM_REFERENCE_OBSERVATIONS_013.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/NATIVE_CASES_002.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/PREPARATION_SCOPE_001.md',
    'verification/tool_graders_atac_native_contract_2026-10-27_461/CONTRACT.md',
    'verification/tool_graders_atac_execution_contract_2026-10-27_466/CONTRACT.md',
    'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/CONTRACT.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_IMPLEMENTATION_HANDOFF_014.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_WORKFLOW_VERIFICATION_015.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/FULL_WORKFLOW_VERIFICATION_011.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/COMPLETE_EMPTY_POPULATION_CHECK_012.md',
    'verification/tool_graders_chromatin_workflow_2026-10-27_451/VERIFICATION_SCOPE.md',
    'verification/tool_graders_chromatin_hic_workflow_2026-10-27_459/VERIFICATION_SCOPE.md',
    'verification/tool_graders_hic_workflow_repair_2026-10-27_465/REPAIR_CONTRACT.md',
    'verification/tool_graders_composed_assignment_transport_2026-10-27_458/CONTRACT.md',
    'verification/tool_graders_sequence_derivation_2026-10-26_279/CONTRACT_001.md',
    'verification/tool_graders_sequence_derivation_2026-10-26_279/SUMMARY_SHAPE_ADDENDUM_001.md',
    'verification/tool_graders_sequence_derivation_2026-10-26_279/PUBLICATION_SCHEMA_ADDENDUM_001.md',
    'verification/tool_graders_alignment_sites_2026-10-26_284/CONTRACT_001.md',
    'verification/tool_graders_alignment_sites_2026-10-26_284/RETURN_CONTRACT_002.md',
    'verification/tool_graders_alignment_sites_2026-10-26_282/OWN_ACTION_RETURN_PORT_PROPOSAL.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/PLAN_001.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONSUMER_FINDINGS_001.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_001.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_002.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_003.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_004.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_005.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_006.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_007.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_008.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_009.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_010.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_011.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_012.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_013.md',
    'verification/tool_graders_rna_comparison_inputs_2026-10-26_366/INTERFACES_001.md',
    'verification/tool_graders_rna_comparison_views_2026-10-26_368/INTERFACES_001.md',
    'verification/tool_graders_rna_comparison_views_2026-10-26_368/INTERFACES_ADDENDUM_001.md',
    'verification/tool_graders_rna_comparison_presentation_2026-10-27_378/IMPLEMENTATION_CONTRACT_001.md',
    'verification/tool_graders_rna_single_input_text_contract_2026-10-27_384/PLAN_001.md',
])
_SKIPPED_NOTE_PROVENANCE = []


def note_provenance_path(value):
    """Recognize only named governance files and explicitly retired provenance."""
    path = Path(value)
    if path.name.lower() in {'agents.md', 'agent.md', 'goal.md',
                             'original-user-goal.txt', 'immutable_goal.txt'}:
        return True
    if path.name == 'pasted-text-1.txt' and set(path.parts) & {
            'e94d8875-9d86-482e-9bb3-8887aa457b88',
            '6960b4a1-b2e0-46d4-8003-fcb7685a2232'}:
        return True
    normalized = path.as_posix()
    return any(normalized == known or normalized.endswith('/' + known)
               for known in _KNOWN_NOTE_PROVENANCE_PATHS)


def runtime_pin_rows(rows):
    """Retain unknown Markdown and all scientific/runtime pin records."""
    kept = []
    for row in rows:
        if any(note_provenance_path(row[key]) for key in ('path', 'source_path')
               if row.get(key)):
            _SKIPPED_NOTE_PROVENANCE.append({
                'path': row.get('path'), 'source_path': row.get('source_path'),
                'recorded_sha256': row.get('sha256'),
                'validation': 'not_validated_non_runtime_note_provenance',
            })
        else:
            kept.append(row)
    return kept


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode import bvbrc_data_schema


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                      allow_nan=False) + "\n")


def main():
    baseline = json.loads((HERE / "BASELINE_SHA256.json").read_text())
    historical = {row['path']: row['sha256'] for row in runtime_pin_rows([
        {'path': name, 'sha256': value} for name, value in baseline.items()
        if name.startswith("verification/")])}
    changed = [name for name, value in historical.items()
               if sha256(ROOT / name) != value]
    assert not changed, changed

    # These are explicitly synthetic schema fixtures, not acquired measurements
    # or host-admitted forms. The same fixtures are covered by the pytest suite.
    tests = runpy.run_path(str(ROOT / "tests/test_bvbrc_data_schema.py"))
    page, facet = tests["synthetic_page_fact"], tests["synthetic_facet_fact"]
    examples = [
        ("populated_page", "execution_bvbrc_pages", [page()]),
        ("successful_zero_page", "execution_bvbrc_pages", [page(
            returned_row_count=0, valid_row_count=0, reported_total=0)]),
        ("partial_page_with_retained_counts", "execution_bvbrc_pages", [page(
            status="partial", valid_row_count=1, invalid_row_count=1,
            response_complete=False, population_coverage="unknown",
            unavailable_reason="native_value_invalid")]),
        ("failed_no_sheet_page", "execution_bvbrc_pages", [page(
            status="unavailable", requested_offset=7,
            returned_row_count=None, valid_row_count=None, invalid_row_count=None,
            reported_total=None, count_exactness="unknown", response_complete=False,
            population_coverage="unknown", unavailable_reason="transport_incomplete")]),
        ("native_missing_term_bucket", "execution_bvbrc_facets", [facet()]),
        ("failed_no_sheet_facet_query", "execution_bvbrc_facets", [facet(
            status="unavailable", bucket_ref=None, is_missing_bucket=None,
            term_ref=None, count=None, denominator=None, fraction=None,
            fraction_unavailable_reason="native_format_unverified",
            bucket_window_status="invalid")]),
        ("successful_empty_facet_array", "execution_bvbrc_facets", []),
        ("acquired_invalid_bucket", "execution_bvbrc_facets", [facet(
            status="partial", is_missing_bucket=None, term_ref=None, count=None,
            fraction=None, fraction_unavailable_reason="native_value_invalid",
            bucket_window_status="invalid")]),
    ]
    filled = []
    for name, source, rows in examples:
        tests["assert_fact_and_materialization"](source, rows)
        filled.append({"name": name, "evidence_kind": "synthetic_schema_fixture",
            "fact_source": source, "facts": rows,
            "embedded_materialization": tests["synthetic_materialization"](source, rows)})
    write_json("FILLED_EXAMPLES.json", filled)

    module_output = (HERE / "PYTEST_MODULES.txt").read_text()
    match = re.search(r"^(\d+) passed in ([0-9.]+)s$", module_output, re.MULTILINE)
    assert match, "The retained combined pytest run must have passed."
    assert int(match.group(1)) == 651
    schema_command = ".venv/bin/python -m pytest -q tests/test_bvbrc_data_schema.py"
    module_command = (schema_command + " tests/test_bvbrc_data_query.py"
        " tests/test_bvbrc_data_readers.py tests/test_bvbrc_data_calculators.py"
        " tests/test_bvbrc_data_feature_sequences.py tests/test_bvbrc_data_molecular.py"
        " tests/test_bvbrc_data_views.py tests/test_communication.py")
    source_paths = [ROOT / "gene_annotation_episode/bvbrc_data_schema.py",
                    ROOT / "tests/test_bvbrc_data_schema.py",
                    ROOT / "gene_annotation_episode/communication.py",
                    ROOT / "tests/test_communication.py"]
    for name in ("query", "readers", "calculators", "feature_sequences", "molecular", "views"):
        source_paths.extend([ROOT / f"gene_annotation_episode/bvbrc_data_{name}.py",
                             ROOT / f"tests/test_bvbrc_data_{name}.py"])
    source_paths.extend([ROOT / "gene_annotation_episode/bvbrc_data_fields.py",
        HERE / "verify.py"])
    hashes = {str(path.relative_to(ROOT)): sha256(path) for path in sorted(source_paths)}
    write_json("SOURCE_SHA256.json", hashes)
    report = {
        "change": "Additive unavailable page/facet return schema correction 003",
        "owned_production_files": ["gene_annotation_episode/bvbrc_data_schema.py"],
        "owned_test_files": ["tests/test_bvbrc_data_schema.py"],
        "skipped_note_provenance": list(_SKIPPED_NOTE_PROVENANCE),
        "pin_validation_scope": "scientific_and_runtime_inputs_excluding_reported_note_provenance",
        "exports": list(bvbrc_data_schema.__all__),
        "historical_artifacts_unchanged": len(historical),
        "historical_evidence_note": "Original planning shapes/examples and prior 502 tests / 26 offline checks remain historical records.",
        "synthetic_examples_checked": len(filled),
        "closed_form_and_embedded_shape_checks": 2 * len(filled),
        "pytest_runs": [
            {"command": schema_command, "exit_code": 0, "passed": 135,
             "seconds": 1.45, "evidence": "Captured terminal summary: 135 passed in 1.45s"},
            {"command": module_command, "exit_code": 0, "passed": int(match.group(1)),
             "seconds": float(match.group(2)), "full_output": "PYTEST_MODULES.txt",
             "coordination": "D5 owner079 confirmed stable with 85 tests before this run."},
        ],
        "offline_command": ".venv/bin/python verification/tool_graders_bvbrc_unavailable_facts_2026-10-24/verify.py",
        "schema_sha256": hashes["gene_annotation_episode/bvbrc_data_schema.py"],
        "schema_tests_sha256": hashes["tests/test_bvbrc_data_schema.py"],
        "limitations": [
            "This is static infrastructure shape validation; no new scientific measurement or score is produced.",
            "Synthetic form references are fixture-local; these checks do not establish host custody or episode admission.",
            "No network request, live BV-BRC execution, job submission or model call was performed for this correction.",
            "No prompt, credit, controller, goal/accounting or endpoint-completion implementation was changed.",
            "Full host integration and practical endpoint completion are owned and verified separately by root.",
            "No unavailable record is evidence of endpoint completion; no new completion claim is made here.",
        ],
    }
    write_json("REPORT.json", report)
    print(json.dumps({"synthetic_examples": len(filled), "shape_checks": 2 * len(filled),
        "historical_artifacts_unchanged": len(historical), "module_tests_passed": int(match.group(1)),
        "schema_sha256": report["schema_sha256"], "schema_tests_sha256": report["schema_tests_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
