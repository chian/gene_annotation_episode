"""Record verified overlap components without claiming an integrated tool."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_103.json'
POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_102.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 112
assert status['verified_bound_local_tool_mode_rows'] == 42
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']

# Overlapping checks and historical source pins remain separate observations.
# Only explicitly named final-owner files must still match the current checkout.
specifications = [
    ('result_worker_2026-10-27_432', 'check004', 1, 0, 'HANDOFF.md', []),
    ('result_worker_2026-10-27_432', 'check005', 70, 0, 'HANDOFF.md', []),
    ('result_worker_2026-10-27_432', 'check006', 23, 0, 'HANDOFF.md',
     ['genomic_overlap_result_worker.py']),
    ('native_capture_2026-10-27_433', 'check002', 71, 0, 'HANDOFF.md',
     ['native_genomic_overlap_capture.py']),
    ('worker_preparation_2026-10-27_434', 'check003', 22, 0, 'HANDOFF.md',
     ['native_genomic_overlap_preparation.py']),
    ('worker_preparation_2026-10-27_434', 'check005', 1, 0, 'HANDOFF.md', []),
    ('return_authority_2026-10-27_435', 'check002', 57, 0, 'HANDOFF.md',
     ['genomic_overlap_returns.py']),
    ('execution_information_2026-10-27_438', 'check002', 53, 0, 'REPORT.md',
     ['genomic_overlap_execution_information.py']),
    ('shared_2026-10-27_429', 'check006', 159, 1, None, []),
    ('shared_2026-10-27_429', 'check007', 1, 0, None, []),
    ('shared_2026-10-27_429', 'check008', 147, 0, None,
     ['execution_episodes.py', 'execution_progress.py', 'genomic_overlap_return_views.py',
      'communication.py']),
]
checks, reports = [], []
for packet, attempt_name, count, failures, report, current_names in specifications:
    base = ROOT / 'verification' / ('tool_graders_genomic_overlap_' + packet)
    attempt = base / attempt_name
    receipt = read(attempt / 'receipt.json')
    assert receipt['returncode'] == (1 if failures else 0)
    assert receipt['metadata']['policy'] == POLICY
    cgroup = receipt['metadata']['verified_cgroup']
    assert cgroup['memory_max'] == POLICY['memory_bytes'] and cgroup['memory_swap_max'] == 0
    assert cgroup['runtime_max'] == 'infinity'
    assert receipt['executed_source_pins_unchanged']
    pins = read(attempt / 'source_pins_before.json')
    assert pins == read(attempt / 'source_pins_after.json')
    indexed = {pin['path']: pin for pin in pins}
    for name in current_names:
        relative = 'gene_annotation_episode/' + name
        assert sha(ROOT / relative) == indexed[relative]['sha256'], relative
    if 'binary_pins_unchanged' in receipt:
        assert receipt['binary_pins_unchanged']
    suite = ET.parse(attempt / 'pytest.xml').getroot().find('testsuite')
    assert suite is not None
    assert {key: suite.attrib[key] for key in ('tests', 'errors', 'failures', 'skipped')} == {
        'tests': str(count), 'errors': '0', 'failures': str(failures), 'skipped': '0'}
    if report is not None:
        reports.append(base / report)
    reports.extend(attempt / name for name in ('receipt.json', 'pytest.xml', 'stdout.txt',
        'source_pins_before.json', 'source_pins_after.json'))
    checks.append({'packet': packet, 'attempt': attempt_name, 'tests_passed': count - failures,
        'tests_failed': failures, 'elapsed_seconds': receipt['metadata']['elapsed_seconds'],
        'current_owner_files_verified': current_names,
        'checkout_changes_during_check': receipt.get('checkout_drift',
            receipt.get('checkout_source_drift', []))})

summary = (
    'Native result capture passed 71 tests. The retained worker passed 70 small cases before its '
    'final diagnostic-role change, then 23 focused cases at the final pin; the retained large '
    'interrupted-output case passed at its recorded earlier pin. Worker preparation passed 22 '
    'tests, with a separate strengthened saved-input-loss check passing at the same production '
    'pin. Typed-return authority passed 57 tests using actual runtime records and an explicitly '
    'labeled results-host double. Pure launch/results information passed 53 tests. Shared '
    'communication checks first passed 158 with one missing-fixture failure; that check passed '
    'separately after including its existing fixture. Current shared wiring passed 147 tests. '
    'These groups overlap and are not a single combined final-source suite. Original AB/AC/BC '
    'unions yield Jaccard 1/3, 1/4, 2/13; saved minimum overlap4 selects counts1,1,0 without '
    'native reacquisition. The production results host and full Workflow are being verified '
    'separately; model-facing results/receiver rendering remains unfinished. No new tool or '
    'resource binding enters the tally.')
evidence = {
    'id': 'GENOMIC-OVERLAP-CAPTURE-WORKER-RETURN-COMPONENTS-103',
    'kind': 'retained_capture_worker_authority_information_and_shared_component_verification',
    'summary': summary,
    'qualification': 'Component evidence, including actual bounded workers and retained native bytes; '
        'return-authority fixtures use a strict labeled host double. Whole production Workflow '
        'and model presentation are not established by these checks.',
    'checks': checks,
    'reports': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in dict.fromkeys(reports)],
}
assert evidence['id'] not in {item['id'] for item in status['verification_evidence']}
status['verification_evidence'].append(evidence)
tool_id = 'B-L123-analyze_genomic_region_overlap'
row = next(row for row in status['rows'] if row['id'] == tool_id)
before = deepcopy(row)
row.update(overall='capture_worker_return_components_verified_host_and_workflow_unfinished',
    tool_information='local_launch_and_results_information_verified_model_rendering_unfinished',
    production_result_binding='capture_worker_and_return_authority_components_verified_actual_host_under_verification',
    integration_verification='shared_wiring_regressions_passed_full_workflow_and_presentation_unfinished')
row['evidence_ids'].append(evidence['id'])
row['note'] += ' Update103: ' + summary
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] != tool_id)
assert original['resource_bindings'] == status['resource_bindings']
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] += ' Update103: ' + summary + ' Count112/308,42local bindings,196remaining unchanged.'
assert [(x['id'], x['original_item'], x['status']) for x in checklist] == [
    (x['id'], x['original_item'], x['status']) for x in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-27', 'author': 'root',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'previous_status_sha256': before_sha,
    'new_status_sha256': hashlib.sha256(raw).hexdigest(), 'scope_sha256_unchanged': scope_sha,
    'scope_changes': [], 'changes': [{'id': tool_id, 'before': before, 'after': deepcopy(row)}],
    'resource_binding_changes': [], 'added_evidence': [evidence],
    'numerical_grader_progress_tally': {'before': 112, 'after': 112, 'added_row_ids': [],
        'meaning': previous['numerical_grader_progress_tally']['meaning']},
    'verified_bound_local_tool_mode_rows': {'before': 42, 'after': 42},
    'remaining_fixed_rows_outside_tally': 196, 'completed_work': [summary],
    'findings_requiring_repair': deepcopy(previous['findings_requiring_repair']),
    'work_item_states': checklist,
    'unfinished_work': [x['current_evidence'] for x in checklist if x['status'] != 'complete'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': status['complete_scientific_tools_claimed'],
}
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.103.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({'updated_tool_rows': 1, 'updated_resource_bindings': 0,
    'grader_tally': 112, 'verified_local_bindings': 42, 'remaining_rows': 196,
    'new_status_sha256': sha(STATUS)}))
