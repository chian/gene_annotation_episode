"""Record RNA result-component acceptance and accepted U06 coding boundaries."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_084.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_083.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256'] and scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 110
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']
packet = ROOT / 'verification/tool_graders_rna_structure_results_2026-10-26_358'
run_names = ['check_20261027T021057670712Z', 'check_20261027T021819991815Z']
for run_name, passed in zip(run_names, [79, 6]):
    receipt = read(packet / run_name / 'receipt.json')
    assert receipt['returncode'] == receipt['metadata']['native_returncode'] == 0 and receipt['source_unchanged']
    assert receipt['metadata']['policy'] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert str(passed) + ' passed' in (packet / run_name / 'stdout.txt').read_text()
pins = read(packet / run_names[-1] / 'command.json')['source_sha256']
assert len(pins) == 13
for name, value in pins.items():
    if name.endswith('/run_checks.py'):
        continue  # Explicit later metadata-only correction, preserved additively.
    assert sha(ROOT / name) == value
paths = [packet / name for name in ['ROOT_REVIEW_001.md', 'HANDOFF.md', 'INTERFACES_001.md',
    'INTERFACES_002.md', 'RETAINED_DATA_AND_TYPED_RETURNS_001.md', 'CHECK_RECORD_CORRECTION_001.md']]
paths += [packet / run / name for run in run_names for name in ['command.json', 'receipt.json', 'stdout.txt']]
evidence = [dict(id='RNA-RESULTS-COMPONENT-084', kind='root_reviewed_result_component',
    summary='Six RNA result modules accepted after full root source, five-test-file, fixture, contract and retained-example review.79 component tests passed;6 focused tests passed after strict execution-entry authority correction. Full shared integration review and question-specific comparison/scan/presentation remain unfinished.',
    reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths],
    qualification='Synthetic scientific fixtures with real bounded worker, Store, receipts and typed forms. No additional scientific run, whole-tree pass or tool-tally increment.')]
plan = ROOT / 'verification/tool_graders_blast_database_census_association_plan_2026-10-26_361'
evidence.append(dict(id='BLAST-POPULATION-ASSOCIATION-CONTRACT-084', kind='accepted_implementation_contract',
    summary='U06 exact native operand, semantic population, manifest and supplied census association contract accepted. Fresh363 owns pure sheets/qualification; fresh364 owns supplied metadata; iteration/worker workloadC remains separately scoped for assignment. No association implementation is accepted yet; VDB is unchanged.',
    reports=[dict(path=str((plan / name).relative_to(ROOT)), sha256=sha(plan / name))
        for name in ['PLAN_001.md', 'SOURCE_AND_CONSUMER_FINDINGS_001.md', 'ACCEPTANCE_001.md']]))
assert not {item['id'] for item in evidence} & {item['id'] for item in status['verification_evidence']}
status['verification_evidence'].extend(evidence)
ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row['source_presence'] = 'pure_execution_and_result_components_reviewed_full_shared_path_review_pending'
    row['production_result_binding'] = 'six_result_modules_accepted_actual_workflow_tests_delivered_root_shared_path_review_pending'
    row['evidence_ids'].append(evidence[0]['id'])
    row['note'] += (' Update084:358 result component accepted;79-test original suite and6 focused final-authority tests inspected. '
        '360 delivered10 passing RNA Workflow checks, alongside a60pass8fail6deselected broader run; all8 failures reproduced with '
        'the five pre360 modules. Root shared integration review is unfinished, not a full regression pass. '
        '362 plans parent-defined comparison/position/scan calculations and selected returns; none is implemented or counted.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {item['id'] for item in changes} == ids
assert status['resource_bindings'] == original['resource_bindings']
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] = ('354 numerical,357 execution,359 registered schemas and358 result components accepted. '
            '360 delivered10 passing actual RNA Workflow checks; root integration review remains unfinished. '
            'The broader60pass8fail6deselected run remains failed; all8 failures reproduce against original modules. '
            '362 comparison/position/scan contract planning continues; no question-specific comparison or presentation is complete. '
            'Neither RNA row is counted. All other fixed308 rows/bindings remain in scope; W05/literature remain separate.')
    elif item['id'] == 'U06':
        item['status'] = 'in_progress'
        item['current_evidence'] = ('361 exact supplied population-association contract accepted. Fresh363 implements pure '
            'qualification and numerical-sheet ports; fresh364 implements supplied metadata. WorkloadC iteration/worker '
            'integration has defined nonoverlapping ports and awaits assignment. No completed association capability claimed. '
            'Existing VDB exact population/snapshot checks are unchanged.')
assert [(i['id'], i['original_item']) for i in checklist] == [(i['id'], i['original_item']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=110, after=110, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[evidence[0]['summary']], findings_requiring_repair=[], work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.084.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, numerical_grader_progress_tally=110,
    remaining_fixed_rows_outside_tally=198, new_status_sha256=sha(STATUS))))
