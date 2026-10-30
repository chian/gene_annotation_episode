"""Add verified component/path evidence without changing the original goal.

Standard-library accounting only. No scientific work or application imports.
Existing rows, aliases, requirements, prior updates and failed runs are retained.
"""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/tool_graders_accounting_2026-10-27_482'
AUTHORITY = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
AUTHORITY_SHA = '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def retained(path):
    path = Path(path)
    relative = path.relative_to(ROOT)
    target = PACKET / 'retained_inputs' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(path, target)
        target.chmod(0o444)
    assert sha(target) == sha(path)
    return {'path': str(relative), 'sha256': sha(path), 'size_bytes': path.stat().st_size,
            'retained_copy': str(target.relative_to(ROOT))}


def evidence(identifier, summary, attempts, extra=()):
    checks, reports = [], []
    for directory in attempts:
        path = ROOT / 'verification' / directory
        receipt = json.loads((path / 'receipt.json').read_text())
        assert receipt['terminal'] is True and receipt['quiescent'] is True
        check = {'attempt': directory, 'returncode': receipt['returncode'],
            'terminal': True, 'quiescent': True, 'unit': receipt['unit'],
            'pin_checks': {k: v for k, v in receipt.items() if k.endswith('_pins_unchanged')}}
        assert check['pin_checks'] and all(v is True for v in check['pin_checks'].values())
        junit = path / 'junit.xml'
        if junit.exists():
            suites = list(ET.parse(junit).getroot().iter('testsuite'))
            totals = {key: sum(int(s.get(key, 0)) for s in suites)
                      for key in ('tests', 'failures', 'errors', 'skipped')}
            check.update(totals, passed=totals['tests'] - totals['failures'] - totals['errors'] - totals['skipped'])
        checks.append(check)
        for filename in ('receipt.json', 'junit.xml', 'selected_request.json', 'stdout.txt'):
            if (path / filename).is_file():
                reports.append(retained(path / filename))
        for control in sorted(path.glob('*_pins_*.json')):
            reports.append(retained(control))
    reports.extend(retained(ROOT / item) for item in extra)
    return {'id': identifier, 'kind': 'verified_scoped_implementation_evidence',
        'summary': summary, 'checks': checks, 'reports': reports,
        'complete_tool_acceptance': False}


assert sha(AUTHORITY) == AUTHORITY_SHA
status_path = HERE / 'WORK_STATUS.json'
previous_path = HERE / 'PROGRESS_UPDATE_110.json'
previous = json.loads(previous_path.read_text())
assert sha(status_path) == previous['new_status_sha256']
assert sha(HERE / 'SCOPE.json') == previous['scope_sha256_unchanged']
assert not (HERE / 'PROGRESS_UPDATE_111.json').exists()
before_bytes, previous_sha = status_path.read_bytes(), sha(status_path)
before = json.loads(before_bytes)
updated = deepcopy(before)
PACKET.mkdir(exist_ok=False)
retained(status_path)
retained(previous_path)

atac_summary = (
    'Selected local ATAC execution, tool information, finite result worker and typed-return bindings are implemented. '
    '474/check004 passed35; actual474/native002 succeeded with31/31 captured native output occurrences and actual100/200 '
    'postfilter tags. 475/check008 passed49 worker/parser/calculation/preparation cases, including saved recalculation and '
    'valid prefixes surviving missing/corrupt tables. C476 records166 distinct latest passing tests across incremental '
    'snapshots, not one final combined run. Root477/check002 passed11 shared cases; after an actual full-path failure '
    'exposed duplicate command log roles,477/check004 passed14. Root478/shared001 passed15 after a second actual failure '
    'identified inconsistent single-file dependency roots; setup now uses the existing shared dependency-root function. '
    'Native analysis and numerical worker execution have occurred inside the full selected Workflow, but no complete '
    'ATAC Workflow pass is claimed. 478/check001 failed an authored source-count assertion; check002 exposed duplicate '
    'log identities; check003 exposed worker environment mismatch; diagnostic001 had a harness reconstruction failure; '
    'diagnostic002 located the actual environment mismatch using retained outputs without rerunning native work. '
    'Earlier snapshots remain historical evidence after these root repairs. Full current path, completed-worker tamper '
    'checks and message review remain unfinished. Counts stay112/308 and42 verified local bindings.')
atac_attempts = [
    'tool_graders_atac_native_producer_finish_2026-10-27_474/check004',
    'tool_graders_atac_native_producer_finish_2026-10-27_474/native002',
    'tool_graders_atac_result_worker_finish_2026-10-27_475/check008',
    *['tool_graders_atac_result_authority_finish_2026-10-27_476/' + name
      for name in ('check005', 'check006', 'check007', 'check008')],
    *['tool_graders_atac_shared_integration_2026-10-27_477/' + name
      for name in ('check001', 'check002', 'check004')],
    *['tool_graders_atac_episode_path_2026-10-27_478/' + name
      for name in ('check001', 'check002', 'check003', 'diagnostic001', 'diagnostic002', 'shared001')],
]
atac = evidence('ATAC-NATIVE-WORKER-AND-EPISODE-111', atac_summary, atac_attempts, (
    'verification/tool_graders_atac_native_producer_finish_2026-10-27_474/native002/native-acceptance.json',
    'verification/tool_graders_atac_result_worker_finish_2026-10-27_475/RESULTS.json',
    'verification/tool_graders_atac_result_authority_finish_2026-10-27_476/RESULTS.md',
    'verification/tool_graders_atac_result_authority_finish_2026-10-27_476/LATEST_TEST_OBSERVATIONS.json'))
chromatin_summary = (
    'Original451/check004 and465/check001 completed on their original handles with7 passing full scripted Workflow '
    'checks each, unchanged recorded source/binary pins. They exercise selected local execution, native Cooler/HIC '
    'results, requested typed returns, saved recalculation without original data, partial/zero populations, original '
    'action credit, terminal zero expectations and closed replay. These snapshots predate final shared transport '
    'changes; their runners did not separately pin the complete dependency/standard-library closure. They do not '
    'prove the entire current checkout. Fresh481/cooler002 andhic001 are separate current-source verification work, '
    'not counted as passing here. Message presentation, further native coverage and HPC remain open.')
chromatin = evidence('CHROMATIN-CLOSED-FROZEN-WORKFLOWS-111', chromatin_summary, (
    'tool_graders_chromatin_workflow_2026-10-27_451/check004',
    'tool_graders_hic_workflow_repair_2026-10-27_465/check001'))
added = [atac, chromatin]
assert not {e['id'] for e in added} & {e['id'] for e in before['verification_evidence']}
updated['verification_evidence'].extend(added)
rows = {row['id']: row for row in updated['rows']}
atac_id = 'B-L125-analyze_atac_seq_differential_accessibility'
chromatin_id = 'B-L124-analyze_chromatin_interactions'
rows[atac_id].update(
    tool_information='configured_local_name_description_resources_instructions_and_invocation_verified',
    invocation_contract='actual_selected_local_start_verified_full_result_delivery_in_verification',
    production_result_binding='implemented_actual_native_and_worker_execution_observed_full_delivery_unverified',
    numerical_verification='prior_numerical_suites_and49_worker_cases_verified_at_recorded_pins',
    integration_verification='15_current_shared_checks_pass_full_Workflow_repairs_under_verification',
    live_resource_verification='actual_MACS2_and_finite_worker_executed_in_selected_path_delivery_unverified')
rows[atac_id]['evidence_ids'].append(atac['id'])
rows[atac_id]['note'] += ' Update111: ' + atac_summary
rows[chromatin_id].update(
    integration_verification='two_recorded_seven_case_full_Workflow_suites_pass_current_snapshot_verification_open',
    live_resource_verification='actual_Cooler_and_HIC_full_paths_verified_at_recorded_snapshots_current_verification_open')
rows[chromatin_id]['evidence_ids'].append(chromatin['id'])
rows[chromatin_id]['note'] += ' Update111: ' + chromatin_summary
for binding in updated['resource_bindings']:
    if binding['id'] == atac_id + '::local':
        binding.update(invocation_contract=rows[atac_id]['invocation_contract'],
            production_result_binding=rows[atac_id]['production_result_binding'],
            integration_verification=rows[atac_id]['integration_verification'],
            live_resource_verification=rows[atac_id]['live_resource_verification'],
            prerequisites_present='actual_MACS2_2_2_9_1_and_bounded_worker_executed',
            native_format_observed='31_native_outputs_and_actual_header_depth_track_peak_records',
            evidence_ids=[*binding['evidence_ids'], atac['id']])
    elif binding['id'] == chromatin_id + '::local':
        binding.update(invocation_contract='selected_Cooler_and_HIC_v9_local_paths_verified_at_recorded_snapshots',
            production_result_binding='native_sheet_calculation_and_typed_returns_verified_at_recorded_snapshots',
            integration_verification=rows[chromatin_id]['integration_verification'],
            live_resource_verification=rows[chromatin_id]['live_resource_verification'],
            prerequisites_present='actual_local_Cooler_and_HIC_v9_runs_recorded',
            native_format_observed='synthetic_Cooler_HDF5_and_retained_HIC_v9_native_bytes',
            evidence_ids=[*binding['evidence_ids'], chromatin['id']])

assert [r['id'] for r in updated['rows']] == [r['id'] for r in before['rows']]
assert [r['id'] for r in updated['resource_bindings']] == [r['id'] for r in before['resource_bindings']]
assert len(updated['rows']) == 308 and len(updated['resource_bindings']) == 288
assert updated['verified_bound_local_tool_mode_rows'] == 42
assert updated['complete_scientific_tools_claimed'] == 0
work_items = deepcopy(previous['work_item_states'])
for row in work_items:
    if row['id'] == 'U05':
        row['current_evidence'] += ' Update111: ' + atac_summary + ' ' + chromatin_summary
changes = [{'id': r['id'], 'before': old, 'after': r}
           for old, r in zip(before['rows'], updated['rows']) if old != r]
resource_changes = [{'id': r['id'], 'before': old, 'after': r}
                    for old, r in zip(before['resource_bindings'], updated['resource_bindings']) if old != r]
raw = (json.dumps(updated, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
assert sha(status_path) == previous_sha and sha(previous_path) == retained(previous_path)['sha256']
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-27', 'author': 'root',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'previous_status_sha256': previous_sha,
    'new_status_sha256': hashlib.sha256(raw).hexdigest(),
    'scope_sha256_unchanged': sha(HERE / 'SCOPE.json'), 'scope_changes': [],
    'changes': changes, 'resource_binding_changes': resource_changes, 'added_evidence': added,
    'numerical_grader_progress_tally': {'before': 112, 'after': 112, 'added_row_ids': [],
        'meaning': previous['numerical_grader_progress_tally']['meaning']},
    'verified_bound_local_tool_mode_rows': {'before': 42, 'after': 42},
    'remaining_fixed_rows_outside_tally': 196, 'completed_work': [atac_summary, chromatin_summary],
    'findings_requiring_repair': [
        'ATAC complete Workflow and genuine completed-worker receipt tamper checks remain unverified.',
        'Current chromatin/HIC full suites remain in progress; prior snapshots are recorded separately.',
        'BV-BRC original compact contract and seven consumer repairs are being verified separately; broader failures remain open.'],
    'work_item_states': work_items,
    'unfinished_work': [r['current_evidence'] for r in work_items if r['status'] != 'complete'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': 0,
    'previous_goal_turn_classification': 'progress_verified_job_completion_evidence_changed_next_action'}
write_new(PACKET / 'VERIFIED_ACCOUNTING.json', {
    'original_goal_sha256': AUTHORITY_SHA, 'row_ids_preserved': True, 'resource_ids_preserved': True,
    'scope_sha256': sha(HERE / 'SCOPE.json'), 'numerical_grader_count': 112,
    'verified_local_count': 42, 'rows_outside_tally': 196,
    'unchanged_work_item_statuses': {r['id']: r['status'] for r in work_items},
    'closed_attempt_count': sum(len(e['checks']) for e in added),
    'scientific_work_performed_by_accounting': False})
write_new(HERE / 'PROGRESS_UPDATE_111.json', update)
status_path.write_bytes(raw)
assert sha(status_path) == update['new_status_sha256']
print(json.dumps({'updated': [r['id'] for r in changes], 'resources_updated': len(resource_changes),
    'numerical_graders': 112, 'verified_local_bindings': 42, 'scope_unchanged': True,
    'status_sha256': update['new_status_sha256']}))
