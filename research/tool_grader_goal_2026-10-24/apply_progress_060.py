"""Record five implemented paired-BLAST graders; preserve every fixed scope row."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_060.json'
BASE = ROOT / 'verification/tool_graders_blast_programs_2026-10-26_292'
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


if UPDATE.exists():
    raise RuntimeError('Immutable update already exists')
assert sha(GOAL) == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
previous = json.loads((HERE / 'PROGRESS_UPDATE_059.json').read_text())
before_sha = sha(STATUS)
assert before_sha == previous['new_status_sha256']
status = json.loads(STATUS.read_text())
row_ids = [r['id'] for r in status['rows']]
binding_ids = [r['id'] for r in status['resource_bindings']]
scope_sha = sha(HERE / 'SCOPE.json')
manifest = json.loads((BASE / 'VERIFICATION_MANIFEST_001.json').read_text())
assert manifest['full_workflow_passing_checks'] == 97
assert manifest['actual_retained_native_example_count'] == 20
assert manifest['full_workflow_native_program'] == 'blastx'
for item in [manifest['report'], manifest['source_after_manifest'],
             manifest['library_retrieval_receipt'], *manifest['contracts'],
             *manifest['filled_verification_examples'],
             *manifest['verified_relevant_source_snapshots']]:
    assert sha(ROOT / item['path']) == item['sha256'], item['path']
for run in manifest['run_results']:
    for key in ('receipt', 'test_outcome'):
        item = run[key]
        assert sha(ROOT / item['path']) == item['sha256'], item['path']

evidence = {
    'id': 'NATIVE-PAIRWISE-BLAST-FIELDS-FUNCTIONS-060',
    'kind': 'actual_local_native_and_scripted_shared_workflow_evidence',
    'summary': 'Five paired-program numerical sheets, population functions and '
               'calculators implemented with native local capture and requested '
               'typed returns; 20 retained actual native examples; 97 final '
               'integration checks. Full scripted Workflow example is BLASTX.',
    'reports': [descriptor(BASE / name) for name in
                ('REPORT_001.md', 'VERIFICATION_MANIFEST_001.json')],
    'qualification': manifest['qualification'],
}
assert not any(item['id'] == evidence['id'] for item in status['verification_evidence'])
status['verification_evidence'].append(evidence)
changes = []
for row_id in manifest['scope_rows']:
    row = next(item for item in status['rows'] if item['id'] == row_id)
    before = deepcopy(row)
    assert row['overall'] == 'not_assessed'
    full_example = row_id == 'A-L069-blastx-pairwise'
    integration = ('actual_reverse_translated_full_workflow_numeric_return_forwarding_and_replay_verified'
        if full_example else 'actual_native_capture_and_calculation_verified_shared_return_binding_tested_full_workflow_example_is_blastx')
    row.update(
        overall='local_pairwise_numerical_and_shared_episode_path_verified',
        source_presence='native_producer_collector_calculator_and_receiving_consumers_inspected',
        tool_information='registered_name_description_local_resource_and_substantive_instructions',
        invocation_contract='actual_program_specific_supplied_pair_and_original_selected_job_bound',
        numerical_sheet='complete_native_search_and_explicit_full_and_selected_operand_fields_defined',
        native_parser='actual_json_and_declared_tabular_formats_original_ordinals_and_partial_siblings_verified',
        metadata_extractor='actual_sequence_byte_identity_original_source_units_frames_and_selected_intervals_bound',
        deterministic_calculator='separate_saved_sheet_calculations_without_io_or_execution_verified',
        production_result_binding='selected_local_child_capture_sheet_calculation_and_requested_typed_return_connected',
        numerical_verification='actual_native_five_program_examples_and_missing_partial_zero_conflict_cases_passed',
        integration_verification=integration,
        live_resource_verification='tiny_actual_local_two_sequence_jobs_no_database_api_or_hpc_claim',
    )
    row['evidence_ids'] = [*row['evidence_ids'], evidence['id']]
    row['note'] += (' Update060: numerical fields, population functions and separate '
        'calculators implemented, with actual local paired execution/capture and '
        'shared requested-return binding. All five programs have native numerical '
        'examples; the complete scientific-parent Workflow example is reverse '
        'BLASTX. Test groups overlap. No database identification, API/HPC deployment, '
        'configured-model annotation, selected-column inspection, W05 or literature '
        'grader completion is claimed.')
    changes.append({'group': 'rows', 'id': row_id, 'before': before, 'after': deepcopy(row)})
    binding = next(item for item in status['resource_bindings'] if item['id'] == row_id + '::local')
    before_binding = deepcopy(binding)
    assert binding['production_result_binding'] == 'not_assessed'
    binding.update(
        invocation_contract='explicit_program_pairwise_supplied_sequences_actual_software_and_caller_allocation',
        production_result_binding='native_capture_numerical_sheet_functions_and_requested_return_verified',
        integration_verification=integration,
        live_resource_verification='actual_small_local_supplied_pair_executed',
        prerequisites_present='actual_existing_executable_hash_version_and_supplied_fasta_operands_verified',
        native_format_observed='actual_json15_and_declared_tabular7_each_program',
        evidence_ids=[*binding['evidence_ids'], evidence['id']],
    )
    changes.append({'group': 'resource_bindings', 'id': binding['id'],
                    'before': before_binding, 'after': deepcopy(binding)})

assert status['verified_bound_local_tool_mode_rows'] == 32
status['verified_bound_local_tool_mode_rows'] = 37
assert status['verified_bound_local_tool_mode_rows'] == sum(
    r['production_result_binding'] != 'not_assessed'
    for r in status['resource_bindings'] if r['id'].endswith('::local'))
assert len(status['rows']) == 308 and [r['id'] for r in status['rows']] == row_ids
assert len(status['resource_bindings']) == 288
assert [r['id'] for r in status['resource_bindings']] == binding_ids
assert sha(HERE / 'SCOPE.json') == scope_sha
assert previous['numerical_grader_progress_tally']['after'] == 91
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-26',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before_sha, 'new_status_sha256': hashlib.sha256(raw).hexdigest(),
    'scope_sha256_unchanged': scope_sha, 'scope_changes': [], 'changes': changes,
    'added_evidence': [evidence], 'verification': manifest['run_results'],
    'numerical_grader_progress_tally': {
        'before': 91, 'after': 96, 'added_row_ids': manifest['scope_rows'],
        'meaning': 'Implemented numerical graders/validation with verified declared '
                   'episode paths; not every-resource or whole-goal completion. '
                   'For these five rows, all native/capture/numerical paths are '
                   'tested and the full shared Workflow example is BLASTX.',
    },
    'verified_bound_local_tool_mode_rows': {'before': 32, 'after': 37},
    'remaining_fixed_rows_outside_tally': 212,
    'completed_work': [
        'Five local paired-BLAST numerical sheets, population functions, calculators and requested-return binding.',
        'Actual source/sequence/coordinate custody, full native retention, frozen replay and practical terminal credit behavior verified.',
        'Existing BLAST test expectations repaired without restoring retired scorer or root tools.',
    ],
    'unfinished_work': [
        'Alignment-site fields/functions and existing paths verified; new native paired-HSP connection is underway. These three rows remain outside the tally.',
        'Five earlier BV-BRC setup errors caused by concurrent source changes are being rechecked in an isolated source snapshot; no all-suite pass is claimed.',
        'BLAST database metadata/identification, additional PSI/DELTA/RPS/VDB semantics and actual required resource bindings remain.',
        'Previously recorded HMMER mode/resource gaps and other fixed308-row tool/mode, communication and deployment work remain.',
    ],
    'excluded_claims': ['Whole-goal completion', 'API/HPC deployment',
        'Configured-model scientific investigation', 'Whole-checkout frozen verification',
        'Every program separately executed through the full Workflow',
        'W05 or annotation scoring', 'Literature graders'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': status['complete_scientific_tools_claimed'],
}
with UPDATE.open('x') as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.060.writing')
with temporary.open('xb') as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({'updated_rows': 5, 'updated_resource_bindings': 5,
                  'numerical_grader_progress_tally': 96, 'scope_rows': 308,
                  'new_status_sha256': sha(STATUS)}))
