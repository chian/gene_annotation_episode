"""Append verified chromatin/ATAC evidence without increasing any progress count."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(sys.argv[1]).resolve()
ATTEMPT = Path(sys.argv[2]).resolve()
HERE = ROOT / 'research/tool_grader_goal_2026-10-24'
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_110.json'
STATUS_SHA = 'b63b1ca6ba3b481aa71d29cbfac2c96f8d5499806453d7fe9c81585ee142ec10'
SCOPE_SHA = '2f2d6670e3f89ecb980f87857b44d129751bad26471213b8bada9115960c1719'
POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}
CHROMATIN = 'B-L124-analyze_chromatin_interactions'
ATAC = 'B-L125-analyze_atac_seq_differential_accessibility'
captured = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    with Path(path).open('x') as output:
        json.dump(value, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write('\n')


def capture(path):
    path = Path(path)
    relative = str(path.relative_to(ROOT))
    if relative not in captured:
        raw = path.read_bytes()
        target = ATTEMPT / 'retained_inputs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write(raw)
        target.chmod(0o444)
        captured[relative] = {'path': relative, 'sha256': digest(raw),
            'size_bytes': len(raw), 'retained_copy': str(target.relative_to(ROOT))}
    return (ROOT / captured[relative]['retained_copy']).read_bytes()


def read(path):
    return json.loads(capture(path))


def reports_for(paths):
    return [deepcopy(captured[str(Path(path).relative_to(ROOT))]) for path in paths]


assert not UPDATE.exists()
assert sha(STATUS) == STATUS_SHA
assert sha(HERE / 'SCOPE.json') == SCOPE_SHA
previous = read(HERE / 'PROGRESS_UPDATE_109.json')
scope = read(HERE / 'SCOPE.json')
status = read(STATUS)
original = deepcopy(status)
assert previous['new_status_sha256'] == STATUS_SHA
assert previous['scope_sha256_unchanged'] == SCOPE_SHA
assert len(status['rows']) == len(scope['rows']) == 308
assert len(status['resource_bindings']) == len(scope['resource_bindings']) == 288
assert [r['id'] for r in status['rows']] == [r['id'] for r in scope['rows']]
assert [r['id'] for r in status['resource_bindings']] == [r['id'] for r in scope['resource_bindings']]
assert len({r['id'] for r in status['rows']}) == 308
assert len({r['id'] for r in status['resource_bindings']}) == 288
assert previous['numerical_grader_progress_tally']['after'] == 112
assert previous['remaining_fixed_rows_outside_tally'] == 196
assert status['verified_bound_local_tool_mode_rows'] == 42
assert status['complete_scientific_tools_claimed'] == 0

checks = []
receipt_paths = []


def receipt_check(relative, code, *, tests=None, repeated=False):
    directory = ROOT / 'verification' / relative
    path = directory / 'receipt.json'
    receipt = read(path)
    assert receipt['returncode'] == code
    assert receipt['terminal'] and receipt['quiescent']
    assert receipt['metadata']['policy'] == POLICY
    group = receipt['metadata']['verified_cgroup']
    assert group['memory_max'] == 21474836480 and group['memory_swap_max'] == 0
    assert group['runtime_max'] == 'infinity'
    pin_groups = []
    frozen_verified = 0
    for label in ('source', 'binary', 'input', ''):
        prefix = label + '_' if label else ''
        before_path = directory / (prefix + 'pins_before.json')
        if not before_path.exists():
            continue
        after_path = directory / (prefix + 'pins_after.json')
        before, after = read(before_path), read(after_path)
        assert before == after, str(directory)
        assert receipt[prefix + 'pins_unchanged']
        pin_groups.append({'group': label or 'combined', 'count': len(before),
                           'before_after_equal': True})
        for pin in before:
            candidate = Path(pin['path'])
            # Original mutable launcher paths may later change. The run's before/
            # after pair is retained; immutable executed snapshots are checked now.
            if '/source_snapshot/' in str(candidate):
                assert sha(candidate) == pin['sha256'], str(candidate)
                frozen_verified += 1
    assert pin_groups
    row = {'attempt': relative, 'returncode': code, 'terminal': True,
        'quiescent': True, 'pin_groups': pin_groups,
        'retained_frozen_files_verified_now': frozen_verified,
        'previously_recorded_in_update109': repeated,
        'receipt_sha256': digest(capture(path)), 'unit': receipt['unit']}
    if tests is not None:
        passed, failed, errors = tests
        junit = directory / 'junit.xml'
        suite = ET.fromstring(capture(junit)).find('testsuite')
        assert suite is not None
        assert int(suite.attrib['tests']) == passed + failed + errors
        assert int(suite.attrib['failures']) == failed
        assert int(suite.attrib['errors']) == errors
        assert int(suite.attrib['skipped']) == 0
        row.update(passed=passed, failed=failed, errors=errors)
        row['test_names'] = [item.attrib['classname'] + '::' + item.attrib['name']
                             for item in suite.findall('testcase')]
    elif code == -11:
        assert not (directory / 'junit.xml').exists()
        row['junit_report'] = 'absent_after_native_SIGSEGV'
        capture(directory / 'stack-samples.txt')
    checks.append(row)
    receipt_paths.append(path)
    return directory, row



for relative, count in [
 ('tool_graders_atac_differential_plan_2026-10-27_460/components001', 132),
 ('tool_graders_atac_native_implementation_2026-10-27_464/check007', 87),
 ('tool_graders_atac_bam_references_2026-10-27_468/check002', 143),
 ('tool_graders_atac_calculation_bridge_2026-10-27_467/check003', 106),
 ('tool_graders_composed_assignment_transport_2026-10-27_458/check013', 63),
 ('tool_graders_composed_assignment_transport_2026-10-27_458/check014', 83)]:
    receipt_check(relative, 0, tests=(count, 0, 0))
receipt_check('tool_graders_composed_assignment_transport_2026-10-27_458/baseline002', 1, tests=(0, 38, 0))
receipt_check('tool_graders_chromatin_hic_workflow_2026-10-27_459/check003', 1, tests=(2, 0, 5))
headers, _ = receipt_check('tool_graders_atac_bam_references_2026-10-27_468/native001', 0)
observations = read(headers / 'BAM_HEADER_OBSERVATIONS.json')['observations']
assert len(observations) == 2
for observation in observations:
    assert observation['input_before'] == observation['input_after']
    assert observation['raw_bam_text_equals_reader_text'] is True
    assert observation['native_dictionary'] == [{'chromosome': 'chrToy', 'length_bp': 12000}]
    header = observation['header']
    raw = capture(Path(header['path']))
    assert raw == b'@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrToy\tLN:12000\n'.decode('unicode_escape').encode()
    assert digest(raw) == header['sha256'] and len(raw) == header['size_bytes'] == 48
comparison = read(ROOT / 'verification/tool_graders_composed_assignment_transport_2026-10-27_458/baseline002/COMPARISON.json')
assert len(comparison) == 38 and all(row['baseline_status'] == 'failed' and row['failure_first_line_equal'] for row in comparison)
for relative in [
 'tool_graders_atac_differential_plan_2026-10-27_460/NUMERICAL_COMPONENT_REVIEW_012.json']:
    capture(ROOT / 'verification' / relative)
live = []
for relative in ['tool_graders_chromatin_workflow_2026-10-27_451/check004',
                 'tool_graders_hic_workflow_repair_2026-10-27_465/check001']:
    directory = ROOT / 'verification' / relative
    handle = read(directory / 'handle.json')
    result = subprocess.run(['systemctl', '--user', 'show', handle['unit'],
        '--property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,MemoryMax,MemorySwapMax,RuntimeMaxUSec'],
        capture_output=True, text=True, check=True)
    live.append({'attempt': relative, 'unit': handle['unit'],
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'systemd_properties': dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line),
        'receipt_present': (directory / 'receipt.json').exists(),
        'junit_present': (directory / 'junit.xml').exists(),
        'scope': 'original_handle_observation_only_no_final_pass_claim'})
save(ATTEMPT / 'LIVE_OBSERVATIONS.json', live)
atac_summary = (
 '460/components001 passed 132 numerical leaf/interval checks including validation for empty input streams. '
 '464/check007 passed 87 native parser/sheet checks, including preserving unsupported formats and retaining '
 'equal-content outputs under distinct legitimate roles. 468/check002 passed 143 checks, which INCLUDE those '
 '87 rather than adding 143 independent tests, for actual SAM-header parsing and additive sheet associations. '
 '468/native001 read both original BAMs without changing their identities: each retained 48 actual SAM-header '
 'bytes with chrToy length 12000 and no M5; raw BAM text equals the reader text. 467/check003 passed 106 '
 'calculation-input bridge checks against actual retained headers, native 100/200 postfilter depth operands, '
 'explicit supplied tracks, selected references, partial/missing data, shared content and saved-only '
 'recalculation. Native header comparison belongs to the bridge; no synthetic header or copied summary flag '
 'substitutes for actual records. These are separately pinned component checks. Native producer, retained '
 'worker, original-result authority, library instructions and full selected episode delivery remain unfinished. '
 'Neither this accounting nor those component suites establish a complete production ATAC tool.')
chromatin_summary = (
 'Final composed-assignment transport repair passed 63 focused checks and 83 unchanged custody checks at their '
 'own immutable source pins. All 38 broader failures reproduce with the same first failure line against the '
 'pre-repair baseline; they remain failures and no full-suite pass is claimed. The separate BV-BRC '
 'commission-message declaration mismatch remains uncorrected. Original 459/check003 ended with 2 passes '
 'and 5 setup errors from a fixture trying to delete an absent dense-output artifact. 465 corrects that '
 'fixture without changing its seven test bodies or production sources; its original replacement handle '
 'is observed separately and not called passed here. 451/check004 also retains its original handle and '
 'has no final acceptance in this update. Both workflow snapshots precede the final transport refinement. '
 'Earlier SIGSEGV failures remain recorded with their cause unproven. Pending message work, broader '
 'native formats, current full integration and HPC verification remain unfinished.')
shared = 'Counts remain 112/308 graders, 42 verified local bindings, 196 outside the tally. U03/U05 remain open. W05 and literature work remain separate.'
evidence = []
for identifier, summary, is_atac in [('ATAC-NUMERICAL-INPUT-COMPONENTS-110', atac_summary, True),
                                      ('CHROMATIN-TRANSPORT-AND-WORKFLOW-110', chromatin_summary, False)]:
    evidence.append({'id': identifier, 'kind': 'verified_component_evidence_not_full_tool_acceptance',
        'summary': summary, 'checks': [deepcopy(c) for c in checks if ('atac_' in c['attempt']) == is_atac],
        'reports': [deepcopy(v) for k,v in captured.items() if k.startswith('verification/') and ('atac_' in k) == is_atac],
        'original_handle_observations': [] if is_atac else live, 'complete_tool_acceptance': False})
assert not ({e['id'] for e in evidence} & {e['id'] for e in status['verification_evidence']})
status['verification_evidence'].extend(evidence)
changes = []
for tool_id, summary, item in [(ATAC, atac_summary, evidence[0]), (CHROMATIN, chromatin_summary, evidence[1])]:
    row = next(r for r in status['rows'] if r['id'] == tool_id)
    before = deepcopy(row)
    row['evidence_ids'].append(item['id'])
    row['note'] += ' Update110: ' + summary + ' ' + shared
    if tool_id == ATAC:
        row.update(overall='numerical_parser_sheet_calculation_components_verified_production_path_unfinished',
            numerical_sheet='native_measurement_sheet_and_additive_actual_BAM_header_records_143_checks_passed',
            native_parser='native_output_and_SAM_header_parsers_verified_on_retained_native_bytes',
            metadata_extractor='actual_run_condition_depth_header_and_reference_input_bridge_106_checks_passed',
            deterministic_calculator='leaf_interval_partition_and_regions_132_checks_passed_saved_recalculation_verified',
            numerical_verification='separately_pinned_132_143_106_component_checks_not_full_episode_verification',
            invocation_contract='native_execution_result_and_authority_contract_defined_production_binding_unfinished')
    else:
        row.update(production_result_binding='native_components_verified_transport_refinement_verified_full_current_Workflow_unfinished',
            integration_verification='63_transport_and_83_custody_checks_passed_original_workflow_runs_still_separate')
    changes.append({'id': tool_id, 'before': before, 'after': deepcopy(row)})
assert all(a == b for a,b in zip(original['rows'],status['rows']) if a['id'] not in (ATAC,CHROMATIN))
assert original['resource_bindings'] == status['resource_bindings']
assert original['verification_evidence'] == status['verification_evidence'][:-2]
for key in original.keys() - {'rows','verification_evidence'}: assert original[key] == status[key]
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05': item['current_evidence'] += ' Update110: ' + atac_summary + ' ' + chromatin_summary + ' ' + shared
assert [(x['id'],x['original_item'],x['status']) for x in checklist] == [(x['id'],x['original_item'],x['status']) for x in previous['work_item_states']]
findings = deepcopy(previous['findings_requiring_repair'])
findings.append('Update110 correction to earlier incomplete transport classification: final focused/custody suites pass; all 38 broad failures reproduce on baseline. The separate BV-BRC declaration defect remains. ATAC numerical/header/input components pass; production execution/result/return wiring remains unfinished.')
raw = (json.dumps(status, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode()
update = {'schema':'tool_grader_progress_update_v1','date':'2026-10-27','author':'root',
 'recorded_at':datetime.now(timezone.utc).isoformat(),'previous_status_sha256':STATUS_SHA,
 'new_status_sha256':digest(raw),'scope_sha256_unchanged':SCOPE_SHA,'scope_changes':[],
 'changes':changes,'resource_binding_changes':[],'added_evidence':evidence,
 'numerical_grader_progress_tally':{'before':112,'after':112,'added_row_ids':[], 'meaning':previous['numerical_grader_progress_tally']['meaning']},
 'verified_bound_local_tool_mode_rows':{'before':42,'after':42},'remaining_fixed_rows_outside_tally':196,
 'completed_work':[atac_summary,chromatin_summary],'findings_requiring_repair':findings,
 'work_item_states':checklist,'unfinished_work':[x['current_evidence'] for x in checklist if x['status']!='complete'],
 'inventory_maintenance_counted_as_implementation_progress':False,'specific_pending_NCBI_job_verification_included':False,
 'complete_scientific_tools_claimed':0,'previous_goal_turn_classification':'verified_wait_original_451_and_465_handles_polled_live'}
save(ATTEMPT/'EVIDENCE_VERIFICATION.json',{'checks':checks,'reports':list(captured.values()),'live':live})
save(ATTEMPT/'STATUS_DIFF.json',{'changes':changes,'resource_binding_changes':[],'count_changes':[],
 'checklist_changes':[{'id':'U05','change':'appended evidence only'}]})
assert sha(STATUS)==STATUS_SHA and sha(HERE/'SCOPE.json')==SCOPE_SHA
save(UPDATE,update)
temporary=STATUS.with_name('.WORK_STATUS.110.writing')
with temporary.open('xb') as output:
    output.write(raw); output.flush(); os.fsync(output.fileno())
assert sha(STATUS)==STATUS_SHA
temporary.replace(STATUS)
assert json.loads(STATUS.read_bytes())==status
assert sha(STATUS)==update['new_status_sha256'] and sha(HERE/'SCOPE.json')==SCOPE_SHA
verification={'status':'passed','updated_tool_rows':2,'updated_resource_bindings':0,'fixed_tool_rows':308,
 'fixed_resource_bindings':288,'grader_tally':112,'verified_local_bindings':42,'remaining_rows':196,
 'all_other_status_content_preserved':True,'prior_evidence_preserved':True,'checklist_statuses_unchanged':True,
 'new_status_sha256':sha(STATUS),'scope_sha256_unchanged':SCOPE_SHA}
save(ATTEMPT/'ACCOUNTING_VERIFICATION.json',verification)
print(json.dumps(verification))
