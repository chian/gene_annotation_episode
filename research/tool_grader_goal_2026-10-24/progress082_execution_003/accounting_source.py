"""Record reviewed RNA execution components and the user's return requirements."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_082.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_081.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 108
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']

specs = [
    ('RNA-EXECUTION-COMPONENT-082', 'tool_graders_rna_structure_producer_2026-10-26_357', 'check003', 268,
     ['ROOT_REVIEW_001.md', 'HANDOFF.md', 'INTERFACES_001.md', 'NATIVE_PATHS.txt'],
     'Single-input execution, exact native output retention and isolated ViennaRNA 2.7.0 runs reviewed. 268 tests passed, including167 overlapping pure-component tests. Complete episode integration and comparison/scan calculations remain unfinished.'),
    ('RNA-REGISTERED-RETURN-SCHEMAS-082', 'tool_graders_rna_structure_report_boundary_2026-10-26_359', 'check001', 172,
     ['ROOT_REVIEW_001.md', 'SCOPE_001.md'],
     'Exact registered RNA typed-return schemas accepted by the shared validator;172 boundary and compatibility tests passed. No complete results path or display is claimed.'),
]
evidence = []
for ident, directory, run_name, passed, names, summary in specs:
    packet = ROOT / 'verification' / directory
    run = packet / run_name
    receipt = read(run / 'receipt.json')
    assert receipt['returncode'] == receipt['metadata']['native_returncode'] == 0
    assert receipt['sources_unchanged'] is True
    assert receipt['metadata']['policy'] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert str(passed) + ' passed' in (run / 'stdout.txt').read_text()
    paths = [packet / name for name in names]
    request_name = 'selected_request.json' if ident == 'RNA-EXECUTION-COMPONENT-082' else 'request.json'
    paths += [run / name for name in (request_name, 'receipt.json', 'stdout.txt', 'stderr.txt')]
    item = dict(id=ident, kind='reviewed_execution_or_communication_component', summary=summary,
        reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths],
        qualification='Component verification only. Neither RNA row enters the implemented-grader tally. Later concurrent integration changes are not covered by these historical receipts.')
    assert not any(old['id'] == ident for old in status['verification_evidence'])
    status['verification_evidence'].append(item)
    evidence.append(item)

direction = ROOT / 'verification/tool_graders_rna_structure_plan_2026-10-26_349/USER_DIRECTION_009.md'
direction_record = dict(id='RNA-QUESTION-DEPENDENT-RETURNS-082', kind='verbatim_user_direction_unfinished_work',
    summary='The parent defines energy, whole-structure, selected-position or perturbation-scan questions and requested returns. No universal aggregate display or blanket structure dump. Comparison and scan calculations are not implemented.',
    reports=[dict(path=str(direction.relative_to(ROOT)), sha256=sha(direction))])
status['verification_evidence'].append(direction_record)
evidence.append(direction_record)

ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row.update(overall='numerical_and_native_execution_components_verified_episode_and_comparison_work_unfinished',
        source_presence='four_pure_and_five_execution_production_modules_inspected',
        tool_information='four_fields_and_explicit_local_commissioning_contract_reviewed',
        invocation_contract='shared_durable_local_execution_component_verified_registered_full_episode_path_in_progress',
        live_resource_verification='actual_viennarna_2_7_0_single_input_runs_in_isolated_local_test_installation_full_episode_path_pending')
    row['evidence_ids'] += [item['id'] for item in evidence]
    row['note'] += (' Update082:357 execution component and359 exact schema recognition reviewed;268 '
        'execution/core tests and172 communication tests passed as separately recorded overlapping scopes. '
        '358 results and360 complete episode-path verification continue. The user rejected a universal '
        'aggregate display and clarified parent-question-dependent energy/structure/position/scan returns. '
        'Comparison and scan calculations remain additional unfinished work; no RNA tally increment.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {r['id'] for r in changes} == ids
assert status['resource_bindings'] == original['resource_bindings']
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)

checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U02':
        item['current_evidence'] = ('347 targeted repair run013 passed29 tests, includingall18 failures '
            'from run012. Root inspected final deltas, receipts,35 evidence-file digests and numerical '
            'examples. Final contract/review acceptance remains unfinished; bothVDB rows stay outside108. '
            'Earlier failed broad receipts remain intact; no live native/HPC execution is claimed.')
    elif item['id'] == 'U05':
        item['current_evidence'] = ('354 RNA numerical and357 execution components plus359 exact return '
            'schemas accepted.358 results and360 registered complete-path verification remain in progress. '
            'New user direction requires parent-question-dependent returns; comparison/position/scan '
            'calculation and projection planning remains unfinished. NeitherRNA tool is counted. '
            'All remaining fixed308 rows/resource bindings remain in scope; W05/literature grading remain separate.')
    elif item['id'] == 'U06':
        item['current_evidence'] = ('361 is planning an explicit original native-path to scientific '
            'database/census association for shared sequence calculations. Existing VDB exact '
            'population/snapshot checks remain separate. No association implementation is complete.')
assert [(i['id'], i['original_item'], i['status']) for i in checklist] == [
    (i['id'], i['original_item'], i['status']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=108, after=108, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=[item['summary'] for item in evidence[:2]],
    findings_requiring_repair=[direction_record['summary']], work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.082.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, numerical_grader_progress_tally=108,
    remaining_fixed_rows_outside_tally=200, new_status_sha256=sha(STATUS))))
