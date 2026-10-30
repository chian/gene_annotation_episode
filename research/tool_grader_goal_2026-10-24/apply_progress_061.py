"""Account for three verified alignment-selection implementations additively."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_061.json'
BASE = ROOT / 'verification/tool_graders_alignment_sites_2026-10-26_284'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


if UPDATE.exists():
    raise RuntimeError('Immutable update already exists')
previous = json.loads((HERE / 'PROGRESS_UPDATE_060.json').read_text())
before_sha = sha(STATUS)
assert before_sha == previous['new_status_sha256']
status = json.loads(STATUS.read_text())
row_ids = [r['id'] for r in status['rows']]
binding_ids = [r['id'] for r in status['resource_bindings']]
scope_sha = sha(HERE / 'SCOPE.json')
assert scope_sha == previous['scope_sha256_unchanged']
manifest = json.loads((BASE / 'COMPLETION_VERIFICATION_002.json').read_text())
assert manifest['native_extension_distinct_passing_cases'] == 297
assert manifest['pending_native_pairwise_hsp_connection'] is False
for item in [manifest['report'], manifest['baseline'], *manifest['contracts'],
             *manifest['native_verification'], *manifest['library_retrieval'],
             *manifest['current_relevant_source_snapshots']]:
    assert sha(ROOT / item['path']) == item['sha256'], item['path']
for run in manifest['run_results']:
    for key in ('receipt', 'test_outcome'):
        item = run[key]
        assert sha(ROOT / item['path']) == item['sha256'], item['path']

evidence = {
    'id': 'ALIGNMENT-SELECTION-FIELDS-FUNCTIONS-061',
    'kind': 'retained_alignment_and_scripted_scientific_child_return_verification',
    'summary': 'Three alignment-selection field/function implementations and '
        'requested returns verified; original source identity, distinct '
        'counting populations and frozen closure preserved. Native paired '
        'BLAST connection adds 297 distinct passing checks and one actual '
        'reverse-BLASTX Workflow.',
    'reports': [descriptor(BASE / name) for name in
        ('REPORT_001.md', 'BASELINE_VERIFICATION_001.json',
         'REPORT_ADDENDUM_002.md', 'COMPLETION_VERIFICATION_002.json')],
    'qualification': manifest['qualification'],
}
assert not any(item['id'] == evidence['id'] for item in status['verification_evidence'])
status['verification_evidence'].append(evidence)
specific = {
    'A-L064-native-pairwise': {
        'parser': 'retained_biopython_and_phmmer_alignment_fields_and_source_ancestry',
        'integration': 'scientific_child_selected_reference_positions_requested_return_and_replay_verified',
        'live': 'actual_small_biopython_and_phmmer_examples_phmmer_uses_documented_older_flat_launch',
        'format': 'actual_biopython_pairwise_and_native_phmmer_alignment_json',
    },
    'A-L064-blast-hsp': {
        'parser': 'received_ncbi_json_and_native_paired_json_declared_table_hsps_original_ordinals_preserved',
        'integration': 'actual_reverse_blastx_workflow_parent_receipt_selected_child_columns_return_and_frozen_replay',
        'live': 'one_actual_reverse_blastx_full_workflow_twenty_retained_reports_no_live_api_hpc_claim',
        'format': 'retained_ncbi_json_and_actual_five_program_paired_json15_declared_tables',
    },
    'A-L064-mapping-correspondence': {
        'parser': 'retained_six_preset_minimap2_paf_correspondence_read_quality_and_original_ancestry',
        'integration': 'scientific_child_selected_mapping_positions_requested_return_and_replay_verified',
        'live': 'existing_actual_retained_mapping_outputs_no_new_mapping_execution_claimed',
        'format': 'actual_retained_minimap2_paf_and_original_fasta_operands',
    },
}
changes = []
for row_id in manifest['scope_rows']:
    detail = specific[row_id]
    row = next(item for item in status['rows'] if item['id'] == row_id)
    before = deepcopy(row)
    assert row['overall'] == 'not_assessed'
    row.update(
        overall='alignment_selection_fields_functions_and_scientific_child_returns_verified',
        source_presence='complete_population_calculation_custody_and_return_consumers_inspected',
        tool_information='actual_registered_operation_with_complete_retrievable_instructions_verified',
        invocation_contract='explicit_received_alignment_and_selected_positions_or_columns',
        numerical_sheet='native_rows_original_units_selected_population_and_count_ratio_fields_defined',
        native_parser=detail['parser'],
        metadata_extractor='original_source_operand_identity_units_and_available_ancestry_bound',
        deterministic_calculator='separate_saved_sheet_counts_and_ratios_without_acquisition_or_execution',
        production_result_binding='existing_scientific_child_own_action_stored_fields_and_requested_return_connected',
        numerical_verification='actual_retained_zero_partial_duplicate_gap_boundary_and_conflict_cases_verified',
        integration_verification=detail['integration'],
        live_resource_verification=detail['live'],
        evidence_ids=[*row['evidence_ids'], evidence['id']],
    )
    row['note'] += (' Update061: reusable fields, population functions, separate '
        'calculators and requested scientific-child returns verified. Filled '
        'sheets are test examples. BLAST viewing creates no new scientific '
        'observation; closure uses stored facts. Native/retained/scripted '
        'resource claims differ by row and are recorded explicitly. No '
        'every-resource, all-suite, W05, literature or annotation-score claim.')
    changes.append({'group': 'rows', 'id': row_id, 'before': before, 'after': deepcopy(row)})
    binding = next(item for item in status['resource_bindings']
                   if item['id'] == row_id + '::local')
    old_binding = deepcopy(binding)
    assert binding['production_result_binding'] == 'not_assessed'
    binding.update(
        invocation_contract='local_read_calculation_of_explicit_retained_alignment_no_aligner_reexecution',
        production_result_binding='selected_scientific_child_operation_to_requested_numerical_return_verified',
        integration_verification=detail['integration'],
        live_resource_verification=detail['live'],
        prerequisites_present='actual_retained_source_bytes_original_operands_and_existing_python_operations',
        native_format_observed=detail['format'],
        evidence_ids=[*binding['evidence_ids'], evidence['id']],
    )
    changes.append({'group': 'resource_bindings', 'id': binding['id'],
                    'before': old_binding, 'after': deepcopy(binding)})

assert status['verified_bound_local_tool_mode_rows'] == 37
status['verified_bound_local_tool_mode_rows'] = 40
assert sum(r['production_result_binding'] != 'not_assessed'
           for r in status['resource_bindings'] if r['id'].endswith('::local')) == 40
assert len(row_ids) == 308 and [r['id'] for r in status['rows']] == row_ids
assert len(binding_ids) == 288 and [r['id'] for r in status['resource_bindings']] == binding_ids
assert sha(HERE / 'SCOPE.json') == scope_sha
assert previous['numerical_grader_progress_tally']['after'] == 96
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-26',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before_sha, 'new_status_sha256': hashlib.sha256(raw).hexdigest(),
    'scope_sha256_unchanged': scope_sha, 'scope_changes': [], 'changes': changes,
    'added_evidence': [evidence], 'verification': manifest['run_results'],
    'numerical_grader_progress_tally': {
        'before': 96, 'after': 99, 'added_row_ids': manifest['scope_rows'],
        'meaning': 'Implemented numerical fields/functions/validation with verified '
            'declared episode paths; not every-resource or whole-goal completion.'},
    'verified_bound_local_tool_mode_rows': {'before': 37, 'after': 40},
    'remaining_fixed_rows_outside_tally': 209,
    'completed_work': [
        'Three alignment-selection field definitions, population functions, calculators and requested scientific-child returns.',
        'Actual native paired-HSP source connection and reverse-BLASTX selected-column Workflow.',
        'Five unchanged BV-BRC regression cases passed in an isolated source snapshot; original broad failure remains recorded.'
    ],
    'unfinished_work': [
        'Additional BLAST sequence/profile/iteration/VDB fields, functions and resource bindings; first exact coding workload now assigned.',
        'Required BLAST database metadata acquisition and identification paths beyond the verified modes.',
        'Previously recorded HMMER mode/resource gaps and remaining fixed308-row implementations, communication and deployment work.'
    ],
    'excluded_claims': ['Whole-goal completion', 'Every-resource deployment',
        'Configured-model scientific investigation', 'Whole-checkout frozen all-suite verification',
        'W05 or annotation scoring', 'Literature graders'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': status['complete_scientific_tools_claimed'],
}
with UPDATE.open('x') as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.061.writing')
with temporary.open('xb') as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({'updated_rows': 3, 'updated_resource_bindings': 3,
                  'numerical_grader_progress_tally': 99, 'scope_rows': 308,
                  'new_status_sha256': sha(STATUS)}))
