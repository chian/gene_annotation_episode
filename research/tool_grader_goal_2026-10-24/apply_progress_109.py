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
UPDATE = HERE / 'PROGRESS_UPDATE_109.json'
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
GOAL_SHA = '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
STATUS_SHA = '47581e57c38a7e00578c627fdb2f2aa481964d9d8a0213ecf60217d4932e64f1'
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
assert sha(GOAL) == GOAL_SHA and sha(STATUS) == STATUS_SHA
assert sha(HERE / 'SCOPE.json') == SCOPE_SHA
previous = read(HERE / 'PROGRESS_UPDATE_108.json')
scope = read(HERE / 'SCOPE.json')
status = read(STATUS)
original = deepcopy(status)
assert previous['new_status_sha256'] == STATUS_SHA
assert previous['scope_sha256_unchanged'] == SCOPE_SHA
assert status['authority_sha256'] == GOAL_SHA == scope['authority']['sha256']
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
        'previously_recorded_in_update108': repeated,
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


reader, reader_check = receipt_check('tool_graders_chromatin_hic_reader_2026-10-27_455/check007', 0)
result = read(reader / 'TEST_RESULT.json')
assert result == {'tests_run': 21, 'failures': 0, 'errors': 0, 'skips': 0, 'successful': True}
reader_check.update(passed=21, failed=0, errors=0)
receipt_check('tool_graders_chromatin_hic_records_2026-10-27_456/check007', 0,
              tests=(64, 0, 0), repeated=True)
receipt_check('tool_graders_chromatin_hic_binding_2026-10-27_457/check002', 0,
              tests=(9, 0, 0), repeated=True)
transport, transport_check = receipt_check('tool_graders_composed_assignment_transport_2026-10-27_458/check008', 0,
                                          tests=(56, 0, 0))
transport_check['scope'] = 'original_recorded_pins_before_later_custody_refinement'
transport_check['production_pins'] = [pin for pin in read(transport / 'source_pins_before.json')
    if pin['path'].endswith(('/gene_annotation_episode/runtime.py', '/gene_annotation_episode/bvbrc_appservice_custody.py'))]
receipt_check('tool_graders_composed_assignment_transport_2026-10-27_458/baseline001', 1,
              tests=(0, 3, 0))
receipt_check('tool_graders_composed_assignment_transport_2026-10-27_458/check010', 1,
              tests=(169, 38, 0))
receipt_check('tool_graders_composed_assignment_transport_2026-10-27_458/check011', 1,
              tests=(62, 1, 0))
custody, custody_check = receipt_check('tool_graders_composed_assignment_transport_2026-10-27_458/custody005', 0,
                                     tests=(3, 0, 0))
custody_check['scope'] = 'diagnostic_reproduced_direct_pending_call_ambiguity_not_refinement_acceptance'
for packet, attempt in [('tool_graders_chromatin_workflow_2026-10-27_451', 'check003'),
                        ('tool_graders_chromatin_hic_workflow_2026-10-27_459', 'check002')]:
    receipt_check(packet + '/' + attempt, -11)
for mode in ('periodic', 'no_periodic'):
    directory, diagnostic = receipt_check(
        'tool_graders_chromatin_hic_workflow_2026-10-27_459/diagnostic002_' + mode, 0)
    result = read(directory / 'RESULT.json')
    assert result['mode'] == mode and result['completed_iterations'] == 256
    assert result['native_dispatches'] == result['new_workflow_actions'] == 0
    assert result['original_practical_credit'] == 7.0
    assert capture(directory / 'fatal-faults.txt') == b''
    diagnostic.update(result=result, scope='isolated_schema_and_credit_diagnostic_cause_unconfirmed')

review = ROOT / 'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_COMPONENT_REVIEW_016.md'
capture(review)
for relative in [
    'tool_graders_chromatin_workflow_2026-10-27_451/CHECK003_CRASH.md',
    'tool_graders_chromatin_hic_workflow_2026-10-27_459/DIAGNOSTIC_EVIDENCE_001.md',
    'tool_graders_chromatin_hic_workflow_2026-10-27_459/check002/FAILURE_EVIDENCE.json']:
    capture(ROOT / 'verification' / relative)

live = []
for relative in ['tool_graders_chromatin_workflow_2026-10-27_451/check004',
                 'tool_graders_chromatin_hic_workflow_2026-10-27_459/check003',
                 'tool_graders_composed_assignment_transport_2026-10-27_458/check010']:
    directory = ROOT / 'verification' / relative
    handle = read(directory / 'handle.json')
    read(directory / 'selected_request.json')
    read(directory / 'source_pins_before.json')
    observed = subprocess.run(['systemctl', '--user', 'show', handle['unit'],
        '--property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,MemoryMax,MemorySwapMax,RuntimeMaxUSec'],
        capture_output=True, text=True, check=True)
    properties = dict(line.split('=', 1) for line in observed.stdout.splitlines() if '=' in line)
    live.append({'attempt': relative, 'observed_at': datetime.now(timezone.utc).isoformat(),
        'unit': handle['unit'], 'systemd_properties': properties,
        'final_receipt_present': (directory / 'receipt.json').exists(),
        'junit_present': (directory / 'junit.xml').exists(),
        'scope': 'read_only_status_observation_no_collection_result_claims_require_separate_receipts'})
save(ATTEMPT / 'LIVE_OBSERVATIONS.json', live)

atac_packet = ROOT / 'verification/tool_graders_atac_differential_plan_2026-10-27_460'
prerequisite, _ = receipt_check('tool_graders_atac_differential_plan_2026-10-27_460/prerequisite001', 0)
native, _ = receipt_check('tool_graders_atac_differential_plan_2026-10-27_460/native001', 0)
math_directory, math_check = receipt_check('tool_graders_atac_differential_plan_2026-10-27_460/math001', 0,
                                         tests=(36, 0, 0))
math_check['scope'] = 'per_interval_numerical_leaf_only_full_sheet_parser_partition_binding_unfinished'
capture(atac_packet / 'NUMERICAL_LEAF_CONTRACT_004.md')
software = read(prerequisite / 'prepared_software.json')
assert software['scientific_execution'] is False
assert software['source_sha256'] == '8d56bc37fb823fc6387d78138ce968405c54a0a8cd9776682705fd0983252d16'
assert sha(prerequisite / 'MACS2-2.2.9.1.tar.gz') == software['source_sha256']
assert capture(prerequisite / 'macs2_version.stdout.txt').strip() == b'macs2 2.2.9.1'
commands = read(native / 'commands.json')
assert len(commands) == 4 and all(item['returncode'] == 0 for item in commands)
assert [item['name'] for item in commands] == ['explicit_bdgdiff', 'condition1_callpeak', 'condition2_callpeak', 'bam_bdgdiff']
manifest = read(native / 'NATIVE_FILES.json')
assert manifest['native_cli_commands'] == 4 and manifest['separate_native_score_export']
assert manifest['production_grader'] is False and manifest['biological_validation'] is False
for item in manifest['files']:
    data = capture(native / item['path'])
    assert digest(data) == item['sha256'] and len(data) == item['size_bytes']
diagnostic = read(native / 'explicit_tracks/NATIVE_DIAGNOSTIC.json')
assert diagnostic['condition_factors'] == [1, 0.5]
assert diagnostic['arrays'][0]['native_positions'] == [0, 100, 200, 300, 400]
assert diagnostic['arrays'][0]['native_condition1_vs_condition2'][1] == 17.7408447265625
assert diagnostic['arrays'][0]['native_condition1_vs_condition2'][3] == -12.148710250854492
for name, expected in [('condition1', ['0', '100', '17.7408']),
                       ('condition2', ['200', '300', '12.1487']),
                       ('common', ['100', '200', '5.42506e-07'])]:
    record = capture(native / 'explicit_tracks' / (name + '.bed')).decode().splitlines()[1].split('\t')
    assert [record[1], record[2], record[4]] == expected
depths = read(native / 'bam_outputs/DEPTH_INPUTS.json')
assert [(d['count'], d['depth_millions']) for d in depths] == [(100, 0.0001), (200, 0.0002)]
for name in ('PREPARATION_SCOPE_001.md', 'NATIVE_FINDINGS_003.md'):
    capture(atac_packet / name)

chromatin_summary = (
    '455/check007 passed 21 final HIC reader methods with retained immutable pins, including '
    'complete observations surviving malformed compressed tails while implicit zeros remain unauthorized. '
    'Root component review016 records the final reader and present-weight validation review. '
    '456/check007 64 passes and 457/check002 9 native producer/worker passes remain separately pinned '
    'evidence already recorded in update108, without recounting. 458/check008 passed 56 focused '
    'transport cases at its recorded runtime/custody pins; later custody005 three-case diagnostics '
    'reproduced a direct pending-call ambiguity. The subsequent shared-marker/custody/exchange-proof '
    'refinement is not covered by those 56 passes; check011 ended with 62 passes and 1 failure, '
    'whose classification remains with its owner. 458/check010 ended with 169 passes and 38 failures. 458/baseline001 '
    'reproduced exactly three sampled pre-repair consumer failures; this does not classify every '
    'failure in check010; the full baseline comparison remains unfinished and no full-repository pass is claimed. '
    '451/check003 and 459/check002 both ended with native SIGSEGV returncode -11, unchanged executed '
    'source/interpreter pins and no JUnit report. The truncated periodic stack samples do not identify '
    'the cause. Both isolated 459 diagnostic002 arms passed 256 iterations; cause remains unconfirmed. '
    'Controlled 451/check004 and 459/check003 keep their original handles and frozen pre-refinement '
    'production/input snapshots with the periodic sampler removed; their complete Workflow outcomes '
    'remain unverified here. Original 451/check001 six-pass pre-HIC history remains valid only for '
    'that snapshot. Model-facing text, further native formats/versions, complete current integration '
    'and live HPC remain unfinished. Root retains acceptance authority.')
atac_summary = (
    '460/prerequisite001 prepared actual MACS2 2.2.9.1 in isolated Python 3.11.13; native001 executed '
    'four successful CLI commands and a separately declared native array export on explicit synthetic '
    'inputs. Both original terminal/quiescent receipts preserve 20 GiB RAM, zero swap, 4 GiB monitored '
    'scratch, no wall limit and unchanged run pins. Complete raw tracks, BAMs, native arrays and outputs '
    'remain retained. MACS2 bdgdiff reports the input signal interval 100-200 as BED 0-100, input '
    '300-400 as BED 200-300, and input 200-300 as BED 100-200; native scores are 17.7408, 12.1487 '
    'and 5.42506e-07. Native stored positions are 0,100,200,300,400 rather than segment ends '
    '100,200,300,400,500. These are demonstrated defective coordinates, not validated accessibility '
    'intervals. Actual callpeak filtered counts 100 and 200 supply depths 0.0001 and 0.0002 million '
    'tags, giving factors 1 and 0.5. Separately, math001 passed 36 tests for the new per-interval '
    'numerical leaf at unchanged source/interpreter pins: all 15 retained native array values match '
    'exactly, and saved operands support recalculation without network or subprocess execution. '
    'That leaf accepts joined numerical operands and returns three inspectable likelihood components; '
    'it does not parse files or produce region coordinates. Full numerical sheet, native parsers, '
    'common-interval partition calculation, library binding and complete episode path remain '
    'unfinished under root/fresh461 contracts. No new grader is counted.')
shared_summary = ('Counts remain 112/308 numerical graders, 42 verified local bindings, 196 outside '
    'the tally and zero complete scientific tools. All earlier failures and unfinished fixed scope '
    'remain; U03/U05 stay open. W05 annotation aggregation and literature remain separate.')
chromatin_paths = [p for p in captured if p.startswith('verification/') and 'atac_differential_plan_' not in p]
atac_paths = [p for p in captured if 'atac_differential_plan_' in p]
evidence = [
    {'id': 'CHROMATIN-HIC-TRANSPORT-FAILURES-109',
     'kind': 'separate_component_passes_retained_SIGSEGV_and_pending_current_verification',
     'summary': chromatin_summary, 'checks': [c for c in checks if 'atac_differential_plan_' not in c['attempt']],
     'reports': [deepcopy(captured[p]) for p in chromatin_paths],
     'original_handle_observations': live, 'complete_tool_acceptance': False},
    {'id': 'ATAC-NATIVE-PREPARATION-COORDINATE-DEFECT-109',
     'kind': 'prerequisites_native_format_and_numerical_leaf_verified_full_grader_unfinished',
     'summary': atac_summary, 'checks': [c for c in checks if 'atac_differential_plan_' in c['attempt']],
     'reports': [deepcopy(captured[p]) for p in atac_paths],
     'native_files_verified': len(manifest['files']), 'complete_tool_acceptance': False}]
existing_ids = {item['id'] for item in status['verification_evidence']}
assert all(item['id'] not in existing_ids for item in evidence)
status['verification_evidence'].extend(evidence)
changes = []
for tool_id in (CHROMATIN, ATAC):
    row = next(item for item in status['rows'] if item['id'] == tool_id)
    before = deepcopy(row)
    if tool_id == CHROMATIN:
        row.update(
            native_parser='Cooler_and_HIC_v9_component_checks_passed_final_partial_retention_review_recorded',
            production_result_binding='original_Cooler_Workflow_and_HIC_native_worker_verified_current_transport_refinement_open',
            integration_verification='focused_transport_original_pins_passed_current_Workflow_SIGSEGV_retained_controlled_runs_unverified')
        row['evidence_ids'].append(evidence[0]['id'])
        row['note'] += ' Update109: ' + chromatin_summary + ' ' + shared_summary
    else:
        row.update(overall='native_preparation_and_numerical_leaf_full_grader_unfinished',
            source_presence='upstream_wrapper_and_MACS2_2_2_9_1_native_source_inspected',
            tool_information='concrete_contract_definition_in_progress_no_library_binding',
            invocation_contract='isolated_native_preparation_and_four_CLI_calls_observed_production_contract_unimplemented',
            numerical_sheet='not_implemented_contract_definition_in_progress',
            native_parser='not_implemented_native_formats_and_coordinate_defect_observed',
            metadata_extractor='not_implemented_supplied_condition_and_native_depth_examples_retained',
            deterministic_calculator='per_interval_numerical_leaf_36_checks_passed_full_sheet_partition_calculation_unfinished',
            production_result_binding='not_implemented',
            numerical_verification='native_coordinate_defect_depth_operands_and_15_native_score_values_verified_full_grader_unfinished',
            integration_verification='not_implemented',
            live_resource_verification='isolated_MACS2_prerequisite_and_synthetic_native_execution_verified_no_episode_binding')
        row['evidence_ids'].append(evidence[1]['id'])
        row['note'] += ' Update109: ' + atac_summary + ' ' + shared_summary
    changes.append({'id': tool_id, 'before': before, 'after': deepcopy(row)})
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in (CHROMATIN, ATAC))
assert original['resource_bindings'] == status['resource_bindings']
assert original['verification_evidence'] == status['verification_evidence'][:-2]
for key in original.keys() - {'rows', 'verification_evidence'}:
    assert original[key] == status[key]
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] += ' Update109: ' + chromatin_summary + ' ' + atac_summary + ' ' + shared_summary
assert [(x['id'], x['original_item'], x['status']) for x in checklist] == [
    (x['id'], x['original_item'], x['status']) for x in previous['work_item_states']]
assert {x['id'] for x in checklist if x['status'] == 'complete'} == {'U01', 'U02', 'U04', 'U06', 'U07', 'U08', 'U09'}
assert {x['id'] for x in checklist if x['status'] == 'open'} == {'U03', 'U05'}
findings = deepcopy(previous['findings_requiring_repair'])
findings.extend([
    'Update109: the initial composed-assignment correction has 56 passes at its original pins; custody005 exposed an additional pending-call ambiguity. Current refinement, broader regression classification and complete current Workflow results remain unfinished. Both native SIGSEGV failures are retained; cause is unconfirmed.',
    'Update109: actual MACS2 2.2.9.1 bdgdiff displaces explicit track intervals by one segment in the observed fixture. Preserve raw reported coordinates. The per-interval score leaf has 36 passing checks; valid derived region coordinates, the full sheet/parser/partition calculator and library path remain unfinished.'])
raw = (json.dumps(status, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-27', 'author': 'root',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'previous_status_sha256': STATUS_SHA,
    'new_status_sha256': digest(raw), 'scope_sha256_unchanged': SCOPE_SHA,
    'scope_changes': [], 'changes': changes, 'resource_binding_changes': [], 'added_evidence': evidence,
    'numerical_grader_progress_tally': {'before': 112, 'after': 112, 'added_row_ids': [],
        'meaning': previous['numerical_grader_progress_tally']['meaning']},
    'verified_bound_local_tool_mode_rows': {'before': 42, 'after': 42},
    'remaining_fixed_rows_outside_tally': 196,
    'completed_work': [
        'Verified retained final HIC reader 21-pass receipt and root component review; referenced already recorded 64/9-pass evidence without recounting.',
        'Verified the 56-pass transport snapshot, three-case ambiguity diagnostic, 169/38 broader result and 62/1 refinement result. The three sampled baseline failures do not classify all failures.',
        'Preserved both -11 Workflow failures and paired 256-iteration diagnostics without claiming a crash cause or current Workflow pass.',
        'Verified actual isolated MACS2 prerequisite and four native CLI calls, all 30 native artifact identities, and the explicit coordinate defect.',
        'Verified 36 passing ATAC per-interval numerical-leaf checks, including exact equality to all 15 native score values and saved-data recalculation; full ATAC grader remains unfinished.'],
    'findings_requiring_repair': findings, 'work_item_states': checklist,
    'unfinished_work': [x['current_evidence'] for x in checklist if x['status'] != 'complete'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
save(ATTEMPT / 'EVIDENCE_VERIFICATION.json', {'checks': checks, 'reports': list(captured.values()),
    'native_artifacts_verified': len(manifest['files']), 'original_handle_observations': live,
    'authority_sha256': GOAL_SHA, 'scope_sha256': SCOPE_SHA, 'prior_status_sha256': STATUS_SHA})
save(ATTEMPT / 'STATUS_DIFF.json', {'changes': changes, 'resource_binding_changes': [],
    'added_evidence_ids': [e['id'] for e in evidence], 'count_changes': [],
    'checklist_changes': [{'id': 'U05', 'change': 'appended current_evidence only'}]})
assert sha(STATUS) == STATUS_SHA and sha(HERE / 'SCOPE.json') == SCOPE_SHA and sha(GOAL) == GOAL_SHA
with UPDATE.open('x') as output:
    json.dump(update, output, indent=2, ensure_ascii=False, allow_nan=False)
    output.write('\n')
    output.flush()
    os.fsync(output.fileno())
temporary = STATUS.with_name('.WORK_STATUS.109.writing')
with temporary.open('xb') as output:
    output.write(raw)
    output.flush()
    os.fsync(output.fileno())
assert sha(STATUS) == STATUS_SHA
temporary.replace(STATUS)
after = json.loads(STATUS.read_bytes())
assert after == status and sha(STATUS) == update['new_status_sha256']
assert sha(HERE / 'SCOPE.json') == SCOPE_SHA and sha(GOAL) == GOAL_SHA
verification = {'status': 'passed', 'updated_tool_rows': 2, 'updated_resource_bindings': 0,
    'fixed_tool_rows': 308, 'fixed_resource_bindings': 288, 'grader_tally': 112,
    'verified_local_bindings': 42, 'remaining_rows': 196, 'complete_scientific_tools': 0,
    'all_other_status_content_preserved': True, 'prior_evidence_preserved': True,
    'prior_findings_preserved': True, 'checklist_statuses_unchanged': True,
    'single_atomic_status_replacement': True, 'new_status_sha256': sha(STATUS),
    'progress_update_sha256': sha(UPDATE), 'scope_sha256_unchanged': SCOPE_SHA,
    'authority_sha256_unchanged': GOAL_SHA}
save(ATTEMPT / 'ACCOUNTING_VERIFICATION.json', verification)
print(json.dumps(verification))
