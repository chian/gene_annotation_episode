"""Record the tested U04 correction without counting another tool grader."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_080.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if UPDATE.exists():
    raise RuntimeError('Immutable update already exists')
previous = read(HERE / 'PROGRESS_UPDATE_079.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 108
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']

packet = ROOT / 'verification/tool_graders_known_regression_fixtures_2026-10-26_356'
for run, expected_exit, expected_summary in (
        ('before001', 1, '9 failed, 17 passed'), ('after001', 0, '40 passed')):
    receipt = read(packet / run / 'receipt.json')
    assert receipt['returncode'] == expected_exit
    assert receipt['metadata']['native_returncode'] == expected_exit
    assert receipt['metadata']['policy'] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert expected_summary in (packet / run / 'stdout.txt').read_text()
    assert read(packet / run / 'source-before.json') == read(packet / run / 'source-after.json')
before = {r['path']: r['sha256'] for r in read(packet / 'before001/source-before.json')}
after = {r['path']: r['sha256'] for r in read(packet / 'after001/source-after.json')}
assert set(before) == set(after)
assert {p for p in before if before[p] != after[p]} == {
    'tests/test_numeric_bounds.py', 'tests/test_execution_tool_contract_declarations.py'}
assert all(sha(ROOT / p) == digest for p, digest in after.items())

names = ['SCOPE_001.md', 'REVIEW_001.md', 'run_checks.py']
for run in ('before001', 'after001'):
    names.extend(run + '/' + name for name in (
        'request.json', 'receipt.json', 'stdout.txt', 'stderr.txt', 'source-before.json', 'source-after.json'))
evidence = dict(id='KNOWN-REGRESSION-FIXTURES-080', kind='reviewed_test_correction',
    summary='Nine known regression failures reproduced and corrected in two test modules. Forty targeted tests pass; production code and annotation scoring are unchanged. Censored-value geometry, independent finding progress, full versus request-specific BV-BRC catalogs, and wrong-version rejection remain explicitly verified.',
    reports=[dict(path=str((packet / name).relative_to(ROOT)), sha256=sha(packet / name)) for name in names],
    qualification='Test-only repair. No native/API/HPC scientific execution, no full-repository pass claim, and no tool tally increase.')
assert not any(e['id'] == evidence['id'] for e in status['verification_evidence'])
status['verification_evidence'].append(evidence)
assert status['rows'] == original['rows'] and status['resource_bindings'] == original['resource_bindings']

checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U02':
        item['current_evidence'] = ('350 census and352 requested-artifact repairs remain accepted. '
            '347 HSP publication-association union passes five targeted integration cases in run011, '
            'including both delivery orders and closed ancestor replay. Final combined regressions '
            'and root review remain pending. Both VDB rows remain outside108.')
    elif item['id'] == 'U04':
        item['status'] = 'complete'
        item['current_evidence'] = ('356 reproduced nine failures, corrected only two test modules, '
            'and passed40 targeted tests with stable source snapshots. Retired scoring stays unavailable; '
            'both BV-BRC request versions select their exact operation. No production or scoring change. '
            'The old broad failed receipt remains unchanged; no full-repository pass is claimed.')
    elif item['id'] == 'U05':
        item['current_evidence'] = ('All remaining fixed308 rows and resource bindings stay in scope. '
            '354 has written the four RNA scientific modules and reports110 passing dedicated tests; '
            'root review and production integration are unfinished.355 is defining exact execution, '
            'publication and requested-return contracts. Neither RNA tool is counted. W05 and literature '
            'grading remain separate.')
assert [(i['id'], i['original_item']) for i in checklist] == [
    (i['id'], i['original_item']) for i in previous['work_item_states']]
assert [i['id'] for i, p in zip(checklist, previous['work_item_states']) if i['status'] != p['status']] == ['U04']
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=[], added_evidence=[evidence],
    numerical_grader_progress_tally=dict(before=108, after=108, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=[evidence['summary']], findings_requiring_repair=[],
    work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as f:
    json.dump(update, f, indent=2, ensure_ascii=False)
    f.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.080.writing')
with temporary.open('xb') as f:
    f.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=0, updated_resource_bindings=0, scope_rows=308,
    numerical_grader_progress_tally=108, remaining_fixed_rows_outside_tally=200,
    completed_checklist_item='U04', new_status_sha256=sha(STATUS))))
