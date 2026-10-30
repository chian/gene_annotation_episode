"""Record inspected evidence without changing the fixed scope or original goal."""

raise SystemExit('Historical progress replay is retired; this script does not update current accounting.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'research/tool_grader_goal_2026-10-24'
STATUS = BASE / 'WORK_STATUS.json'
UPDATE = BASE / 'PROGRESS_UPDATE_113.json'
EXPECTED = 'a2ed1f2f83b83e8a4ae3c7f6a96c80d995a41f86eda03b846c2611196c37fe8e'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def pin(path):
    path = ROOT / path
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(raw), size_bytes=len(raw))


def attempt(relative, expected_passes, expected_failures=0):
    directory = ROOT / 'verification' / relative
    receipt = json.loads((directory / 'receipt.json').read_text())
    assert receipt['terminal'] and receipt['quiescent']
    checks = {k: v for k, v in receipt.items() if k.endswith('_unchanged')}
    assert checks and all(value is True for value in checks.values())
    junit = directory / 'junit.xml'
    if junit.is_file():
        cases = ET.parse(junit).findall('.//testcase')
        failed = sum(case.find('failure') is not None for case in cases)
        errors = sum(case.find('error') is not None for case in cases)
        skipped = sum(case.find('skipped') is not None for case in cases)
        passed = len(cases) - failed - errors - skipped
        report_files = [pin(junit.relative_to(ROOT))]
        report_format = 'junit'
    else:
        # Packet489 deliberately retained stdout plus its actual pytest exit
        # record. Do not invent a JUnit file or claim named-case detail from it.
        assert relative == 'tool_graders_expression_nmf_results_integration_2026-10-27_489/check003'
        result = json.loads((directory / 'test-result.json').read_text())
        assert result == {'returncode': 0}
        lines = (directory / 'stdout.txt').read_text().splitlines()
        summaries = [line for line in lines if re.fullmatch(r'[0-9]+ passed in [0-9.]+s(?: \([^\n]+\))?', line)]
        assert len(summaries) == 1
        passed = int(summaries[0].split()[0])
        failed = errors = skipped = 0
        report_files = [pin(directory.relative_to(ROOT) / name) for name in ('stdout.txt', 'test-result.json')]
        report_format = 'pytest_stdout_and_exit_record'
    assert (passed, failed, errors, skipped) == (expected_passes, expected_failures, 0, 0)
    assert receipt['returncode'] == (1 if expected_failures else 0)
    return dict(attempt=relative, returncode=receipt['returncode'], terminal=True,
        quiescent=True, unit=receipt['unit'], pin_checks=checks, tests=passed + failed + errors + skipped,
        passed=passed, failures=failed, errors=errors, skipped=skipped,
        test_report_format=report_format), [pin(directory.relative_to(ROOT) / 'receipt.json'), *report_files]


def evidence(key, summary, specs, reports):
    checks, files = [], []
    for spec in specs:
        checked, checked_files = attempt(*spec)
        checks.append(checked)
        files.extend(checked_files)
    files.extend(pin(path) for path in reports)
    return dict(id=key, kind='verified_scoped_implementation_evidence', summary=summary,
        checks=checks, reports=files)


raw = STATUS.read_bytes()
assert digest(raw) == EXPECTED and not UPDATE.exists()
old = json.loads(raw)
new = deepcopy(old)
previous = json.loads((BASE / 'PROGRESS_UPDATE_112.json').read_text())
scope_sha = digest((BASE / 'SCOPE.json').read_bytes())
assert scope_sha == previous['scope_sha256_unchanged']
assert len(new['rows']) == 308 and len(new['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 112
assert new['verified_bound_local_tool_mode_rows'] == 42

atac_summary = ('Root accepted the declared single-end BAM numerical grader and selected local result path. '
    '478/check005 has 3 passing original full-path checks and the preserved failed replay; '
    '487/replay003 passes the corrected original closed replay using authenticated original sources plus only the ATAC helper. '
    '487/current_root001 newly passes all19 focused checks on the current helper after NMF integration. '
    'These are complementary frozen checks, not one all-current full Workflow pass. '
    'Actual condition2 peak spans[2909,3190), summit3020, pileup100, fold23.3077, minus-log10 p108.597/q104.594; '
    'three representations remain one peak, display1045 survives, native bdgdiff coordinate defects stay qualified. '
    'Saved cutoff1000000 gives zero derived regions. Original8 actions/8 observations and gains7/3/2/0 remain unchanged; '
    '43 deleted files remain absent. Message presentation, further modes/formats and HPC remain open. '
    'One numerical grader and one declared local binding enter the tally; this is not complete scientific-tool/goal completion.')
nmf_summary = ('Final489/check003 passes28 scoped native-result-worker and return-custody checks with unchanged pins. '
    'Root read all8 final modules and their public consumers; the10 checked production/test files still match the checked snapshot. '
    'Exact retained values include SSE1.9138191182688943e-08, RMSE4.611361715334678e-05 over9 cells and17 iterations. '
    'The complete490 selected scientific-parent Workflow is still running; no full-path success or tally increment is claimed. '
    'Earlier484/488 checks and missing-Bio failure remain as recorded; no old test passes are added again.')
chromatin_summary = ('Original481/cooler002 andhic001 each pass7 full scripted Workflow cases, collected terminal/quiescent exit0. '
    'Both retain unchanged source/dependency/interpreter/stdlib and279 native-library pins with no outside modules/mappings. '
    'Cooler E-P raw6/mean4/fold1.5; divisive HIC raw6/normalized6/mean3.25/fold24/13. '
    'Saved threshold2to1 changes only the flag, after removal of original scientific files. '
    'Complete cases preserve8 actions/8 observations, original gains7/3/2/0 and exact terminal-zero practical expectations. '
    'Partial Cooler preserves p0 and null p1 rows; partial HIC preserves p0, records p1 unavailable and emits no p1 pair rows. '
    'Genuine complete-zero populations retain denominators and undefined folds. '
    'Root reread the full439 contract and441 additions011/012/015 and reviewed the481 handoff/cases. '
    'Root final numerical-sheet/metadata/calculator review remains separate and unfinished. '
    'Later NMF/literature shared additions were not executed by these snapshots. '
    'Full episode insulation/weighted-Cooler coverage, messages, further native coverage and HPC remain open; no count increment.')

added = [
    evidence('ATAC-DECLARED-EPISODE-PATH-113', atac_summary, [
        ('tool_graders_atac_episode_path_2026-10-27_478/check005', 3, 1),
        ('tool_graders_atac_input_identity_replay_2026-10-27_487/replay003', 1),
        ('tool_graders_atac_input_identity_replay_2026-10-27_487/current_root001', 19)], [
        'verification/tool_graders_atac_input_identity_replay_2026-10-27_487/ROOT_CURRENT_VERIFICATION_001.md',
        'verification/tool_graders_atac_input_identity_replay_2026-10-27_487/replay003/REPLAY.json',
        'verification/tool_graders_atac_input_identity_replay_2026-10-27_487/replay003/OVERLAY_SCOPE_AUDIT.json']),
    evidence('NMF-FINAL-RESULT-COMPONENTS-113', nmf_summary, [
        ('tool_graders_expression_nmf_results_integration_2026-10-27_489/check003', 28)], [
        'verification/tool_graders_expression_nmf_results_integration_2026-10-27_489/checked-source.json',
        'verification/tool_graders_expression_nmf_results_integration_2026-10-27_489/HANDOFF.md',
        'verification/tool_graders_expression_nmf_integration_2026-10-27_488/ROOT_REVIEW_001.md']),
    evidence('CHROMATIN-PINNED-FULL-WORKFLOWS-113', chromatin_summary, [
        ('tool_graders_chromatin_current_path_2026-10-27_481/cooler002', 7),
        ('tool_graders_chromatin_current_path_2026-10-27_481/hic001', 7)], [
        'verification/tool_graders_chromatin_current_path_2026-10-27_481/HANDOFF.md',
        'verification/tool_graders_chromatin_current_path_2026-10-27_481/HANDOFF.json',
        'verification/tool_graders_chromatin_current_path_2026-10-27_481/CHECKED_CASES.json',
        'verification/tool_graders_chromatin_current_path_2026-10-27_481/SHARED_CONSUMER_COMPARISON_LATER.json']),
]
checked_nmf = json.loads((ROOT / 'verification/tool_graders_expression_nmf_results_integration_2026-10-27_489/checked-source.json').read_text())
assert len(checked_nmf) == 10
for row in checked_nmf:
    assert row['matches_checked_source'] and all(pin(row['path'])[key] == row[key] for key in ('sha256', 'size_bytes'))

rows = {row['id']: row for row in new['rows']}
bindings = {row['id']: row for row in new['resource_bindings']}
atac = rows['B-L125-analyze_atac_seq_differential_accessibility']
atac.update(overall='numerical_grader_and_declared_local_episode_path_verified',
    invocation_contract='selected_local_MACS2_original_request_and_child_path_verified',
    production_result_binding='actual_native_sheet_calculation_requested_returns_saved_recalculation_and_replay_verified',
    integration_verification='3_original_full_path_checks_corrected_frozen_replay_and19_current_helper_checks_verified',
    live_resource_verification='actual_local_MACS2_synthetic_BAM_full_path_verified_further_modes_and_HPC_open')
atac['evidence_ids'].append(added[0]['id'])
atac['note'] += ' Update113: ' + atac_summary
nmf = rows['B-L128-perform_gene_expression_nmf_analysis']
nmf['integration_verification'] = '4_resource_5_shared_28_result_custody_checks_passed_full_Workflow_running'
nmf['evidence_ids'].append(added[1]['id'])
nmf['note'] += ' Update113: ' + nmf_summary
chromatin = rows['B-L124-analyze_chromatin_interactions']
chromatin.update(invocation_contract='actual_selected_local_Cooler_and_HIC_full_Workflows_verified',
    production_result_binding='pinned_full_native_sheet_calculation_and_requested_returns_verified_final_component_review_pending',
    integration_verification='7_Cooler_and7_HIC_current_verification_snapshots_pass_later_shared_additions_separate',
    live_resource_verification='actual_local_Cooler_and_HIC_full_paths_verified_remaining_modes_and_HPC_open')
chromatin['evidence_ids'].append(added[2]['id'])
chromatin['note'] += ' Update113: ' + chromatin_summary
for row_id, source, evidence_id in ((atac['id'], atac, added[0]['id']), (chromatin['id'], chromatin, added[2]['id'])):
    binding = bindings[row_id + '::local']
    for field in ('invocation_contract', 'production_result_binding', 'integration_verification', 'live_resource_verification'):
        binding[field] = source[field]
    binding['evidence_ids'].append(evidence_id)
new['verified_bound_local_tool_mode_rows'] = 43
new['verification_evidence'].extend(added)
assert [r['id'] for r in new['rows']] == [r['id'] for r in old['rows']]
assert [r['id'] for r in new['resource_bindings']] == [r['id'] for r in old['resource_bindings']]
assert new['complete_scientific_tools_claimed'] == 0

body = encode(new)
update = deepcopy(previous)
update.update(recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=EXPECTED,
    new_status_sha256=digest(body), changes=[dict(id=after['id'], before=before, after=after)
        for before, after in zip(old['rows'], new['rows']) if before != after],
    resource_binding_changes=[dict(id=after['id'], before=before, after=after)
        for before, after in zip(old['resource_bindings'], new['resource_bindings']) if before != after],
    added_evidence=added, numerical_grader_progress_tally=dict(before=112, after=113,
        added_row_ids=[atac['id']], meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=42, after=43), remaining_fixed_rows_outside_tally=195,
    completed_work=[atac_summary, nmf_summary, chromatin_summary],
    findings_requiring_repair=[
        'NMF full selected scientific-parent delivery/recalculation/replay is running on its original490 handle.',
        'Chromatin final numerical-sheet/metadata/calculator review and full episode insulation/weighted-Cooler coverage remain.',
        'ATAC message presentation, further native modes/formats and HPC remain.',
        'Barcode491 numerical and492 native implementation proceed against frozen interfaces; result custody/shared integration remain.',
        'All other fixed308 rows/resource bindings and existing native-format/message obligations remain.'],
    previous_goal_turn_classification='no_progress_status_report_only',
    this_goal_turn_progress='verified19_current_ATAC_checks_and_accepted_declared_grader_path_recorded_final_NMF_chromatin_checks_started_parallel_barcode_code')
for item in update['work_item_states']:
    if item['id'] == 'U05':
        item['current_evidence'] += ' Update113: ' + atac_summary + ' ' + nmf_summary + ' ' + chromatin_summary
assert [(r['id'], r['status']) for r in update['work_item_states']] == [(r['id'], r['status']) for r in previous['work_item_states']]
update['unfinished_work'].append('Update113 supersedes earlier current-status phrases without erasing their histories: ATAC declared numerical/local result path accepted; its messages and further modes/resources remain. NMF full Workflow and chromatin final component review remain. Barcode491/492 code is in progress with full integration still required. Fixed scope remains308 rows/288 bindings; count113/308,43 verified local rows,195 outside tally.')
assert digest(STATUS.read_bytes()) == EXPECTED and digest((BASE / 'SCOPE.json').read_bytes()) == scope_sha
with UPDATE.open('xb') as stream:
    stream.write(encode(update))
temporary = BASE / '.WORK_STATUS.progress113.tmp'
with temporary.open('xb') as stream:
    stream.write(body)
temporary.replace(STATUS)
assert digest(STATUS.read_bytes()) == update['new_status_sha256']
print(json.dumps(dict(progress_update=113, numerical_graders=113, total_fixed_rows=308,
    verified_local_rows=43, remaining_outside_tally=195, scope_unchanged=True,
    status_sha256=update['new_status_sha256'])))
