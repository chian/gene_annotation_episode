"""Record verified local translation/extraction paths without changing scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_059.json'
BASE = ROOT / 'verification/tool_graders_sequence_derivation_2026-10-26_279'
AUTHORITY = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptor(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


if UPDATE.exists():
    raise RuntimeError('Immutable update already exists')
assert sha(AUTHORITY) == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
previous = json.loads((HERE / 'PROGRESS_UPDATE_058.json').read_text())
before_sha = sha(STATUS)
assert before_sha == previous['new_status_sha256']
status = json.loads(STATUS.read_text())
ids = [row['id'] for row in status['rows']]
bindings = deepcopy(status['resource_bindings'])
scope_sha = sha(HERE / 'SCOPE.json')
manifest = json.loads((BASE / 'FINAL_MANIFEST.json').read_text())
assert manifest['focused_grader_tests_passed'] == 121
assert manifest['new_integration_tests_passed'] == 16
assert manifest['actual_publication_examples'] == 10
for item in [manifest['report'], manifest['filled_examples'],
             *manifest['current_relevant_source_snapshots']]:
    assert sha(ROOT / item['path']) == item['sha256'], item['path']
for result in manifest['run_results']:
    for key in ('receipt', 'junit'):
        item = result[key]
        assert sha(ROOT / item['path']) == item['sha256'], item['path']
evidence = {
    'id': 'SEQUENCE-DERIVATION-NUMERICAL-WORKFLOW-059',
    'kind': 'native_local_and_scripted_shared_workflow_evidence',
    'summary': '121 focused grader tests and 16 new integration tests passed; '
               '10 filled actual transformation operations with source custody.',
    'reports': [descriptor(BASE / name) for name in
                ('REPORT_001.md', 'FINAL_MANIFEST.json', 'FILLED_INTEGRATION_EXAMPLES_001.json')],
    'qualification': manifest['qualification'],
}
assert not any(item['id'] == evidence['id'] for item in status['verification_evidence'])
status['verification_evidence'].append(evidence)
changes = []
for row_id in manifest['scope_rows']:
    row = next(item for item in status['rows'] if item['id'] == row_id)
    before = deepcopy(row)
    assert row['overall'] == 'not_assessed'
    row.update(
        overall='local_numerical_transformation_and_selected_child_return_verified',
        source_presence='actual_producer_and_complete_retention_path_inspected',
        tool_information='registered_name_description_local_resource_and_substantive_instructions',
        invocation_contract='selected_effective_request_actual_input_and_original_mapping_bound',
        numerical_sheet='separate_complete_native_measurement_sheet_retained',
        native_parser='pure_native_input_and_coordinate_extraction_verified',
        metadata_extractor='actual_parent_identity_ordered_source_path_and_native_settings_verified',
        deterministic_calculator='saved_json_recalculation_without_io_or_native_execution_verified',
        production_result_binding='actual_child_operation_native_artifact_sheet_and_numeric_observation_verified',
        numerical_verification='native_examples_and_missing_malformed_repeated_coordinate_cases_passed',
        integration_verification='slotted_scientific_child_requested_parent_return_replay_and_partial_failure_verified',
        live_resource_verification='tiny_actual_local_transformations_no_api_or_hpc_claim',
    )
    row['evidence_ids'] = [*row['evidence_ids'], evidence['id']]
    row['note'] += (' Update059: complete numerical transformation sheet and deterministic '
        'calculations integrated with the existing direct scientific-child operation. '
        '121 focused grader tests and all16 new publication/Workflow tests passed. '
        'Split codons, repeated physical source positions and nt/aa units remain distinct. '
        'The original broad regression failures are retained; repaired test groups passed '
        'separately. No annotation-confidence score, API/HPC deployment, configured-model '
        'scientific investigation, W05 or literature grading is claimed.')
    changes.append({'group': 'rows', 'id': row_id, 'before': before, 'after': deepcopy(row)})
assert len(status['rows']) == 308 and [row['id'] for row in status['rows']] == ids
assert status['resource_bindings'] == bindings
assert sha(HERE / 'SCOPE.json') == scope_sha
before_count = previous['numerical_grader_progress_tally']['after']
assert before_count == 89
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-26',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before_sha, 'new_status_sha256': hashlib.sha256(raw).hexdigest(),
    'scope_sha256_unchanged': scope_sha, 'scope_changes': [], 'changes': changes,
    'added_evidence': [evidence], 'verification': manifest['run_results'],
    'numerical_grader_progress_tally': {
        'before': 89, 'after': 91, 'added_row_ids': manifest['scope_rows'],
        'meaning': 'Implemented numerical graders/validation with verified declared local '
                   'episode paths; not every-resource or whole-goal completion.',
    },
    'remaining_fixed_rows_outside_tally': 217,
    'completed_work': ['Translation and extraction numerical sheets/calculators integrated '
                       'and verified through selected child operations and typed parent returns.',
                       'Obsolete sequence-view, knowledge and v2 root commission fixtures '
                       'corrected without restoring retired scoring or root tools.'],
    'unfinished_work': [
        'Alignment-site reference-position and BLAST-column contracts are being finalized; '
        'their grading implementations and selected-row return path remain pending.',
        'Previously recorded HMMER opaque-format/expert-mode and resource gaps remain.',
        'Remaining fixed308-row tool/mode work, actual resource deployments and '
        'generic TASK/STEERING/integration gaps remain.',
    ],
    'excluded_claims': ['Whole-goal completion', 'API/HPC deployment',
                        'Configured-model scientific investigation', 'Whole-checkout frozen verification',
                        'W05 or annotation scoring', 'Literature graders'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': status['complete_scientific_tools_claimed'],
}
with UPDATE.open('x') as stream:
    json.dump(update, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.059.writing')
with temporary.open('xb') as stream:
    stream.write(raw)
temporary.replace(STATUS)
print(json.dumps({'updated_rows': 2, 'numerical_grader_progress_tally': 91,
                  'scope_rows': 308, 'new_status_sha256': sha(STATUS)}))
