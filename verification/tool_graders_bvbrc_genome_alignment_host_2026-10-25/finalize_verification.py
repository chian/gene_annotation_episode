"""Index original pytest receipts and compare the recorded scientific pins."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as adapter


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


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


attempts, latest = [], {}
for path in sorted(BASE.glob('pytest_*.xml')):
    for node in ET.parse(path).getroot().iter('testcase'):
        failure, error, skipped = node.find('failure'), node.find('error'), node.find('skipped')
        outcome = 'failed' if failure is not None or error is not None else 'skipped' if skipped is not None else 'passed'
        attempt = {'case': node.attrib['name'], 'receipt': path.name,
            'outcome': outcome, 'seconds': float(node.attrib['time'])}
        if failure is not None:
            attempt['failure_message'] = failure.attrib.get('message')
        attempts.append(attempt)
        latest[attempt['case']] = attempt
collected = [line.split('::', 1)[1] for line in (BASE / 'collect_004.txt').read_text().splitlines()
    if line.startswith('tests/test_bvbrc_genome_alignment_host.py::')]
assert len(collected) == 12 and set(collected) == set(latest)
assert all(latest[name]['outcome'] == 'passed' for name in collected)
pin = adapter.implementation_sha256()
stores, observed_pins = [], set()
for path in sorted(BASE.glob('SAVED_TRACE_00[345].json')):
    for case in json.loads(path.read_text())['cases']:
        assert case['all_saved_artifact_bytes_verified']
        assert case['counts']['runtime_observations'] == 0
        stores.append({'case_directory': case['case_directory'], 'trace': path.name,
            'database_sha256': case['database_sha256'], 'counts': case['counts']})
        observed_pins.update(publication['configured_adapter_sha256'] for publication in case['publications'])
assert observed_pins == {pin}, (observed_pins, pin)
previous = json.loads((BASE / 'SOURCE_COMPARISON_004.json').read_text())
previous_hashes = {row['path']: row['sha256'] for row in runtime_pin_rows([
    {'path': name, 'sha256': value} for name, value in previous['source_hashes'].items()])}
current = {name: sha(ROOT / name) for name in previous_hashes}
changed = {name: {'previous': old, 'current': current[name]}
    for name, old in previous_hashes.items() if current[name] != old}
sources = {'current_adapter_sha256': pin, 'recorded_pins_from_runs_003_004_005': sorted(observed_pins),
    'same_E_dependency_closure': True, 'E_dependency_count': len(adapter._DEPENDENCIES),
    'source_hashes': current, 'changes_since_source_comparison_004': changed,
    'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
    'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
(BASE / 'SOURCE_HASHES_FINAL.json').write_text(json.dumps(sources, indent=2, sort_keys=True) + '\n')
index = {'kind': 'disjoint_rerun_verification_index', 'current_collected_case_count': len(collected),
    'latest_cases': [latest[name] for name in collected], 'all_original_attempts': attempts,
    'retained_stores': stores, 'current_adapter_sha256': pin,
    'scope': {'controlled_service_replies': True, 'scripted_original_selections': True,
        'runtime_model_call_rows_are_scripted_decision_records': True,
        'live_model_service_invocation': False, 'live_BVBRC_execution': False,
        'configured_model_Workflow_verification': False,
        'production_publication_records_custody_E_F': True}}
(BASE / 'RESULT_INDEX_001.json').write_text(json.dumps(index, indent=2, sort_keys=True) + '\n')
print(json.dumps({'passed_current_cases': len(collected), 'original_attempts': len(attempts),
    'recorded_E_pin_matches_current': pin, 'retained_store_count': len(stores),
    'changed_sources_since_comparison004': list(changed)}, indent=2))
