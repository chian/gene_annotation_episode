"""Accept the two integrated RNA graders; preserve all other unfinished scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_091.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_090.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 110
assert status['verified_bound_local_tool_mode_rows'] == 40
authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
assert sha(authority) == status['authority_sha256']
packet = ROOT / 'verification/tool_graders_rna_original_prompt_delivery_2026-10-27_388'
policy = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
for check, passes, count in [('check003', 278, 808), ('check005_native', 3, 860)]:
    receipt = read(packet / check / 'receipt.json')
    assert receipt['returncode'] == 0 and receipt['metadata']['policy'] == policy
    assert receipt['live_source_pins_unchanged'] and receipt['executed_snapshot_pins_unchanged']
    assert f'{passes} passed' in (packet / check / 'stdout.txt').read_text()
    assert len(read(packet / check / 'source_pins_before.json')) == count
failed = read(packet / 'check004_workflow/receipt.json')
assert failed['returncode'] == 1 and failed['executed_snapshot_pins_unchanged']
assert '1 failed, 18 passed' in (packet / 'check004_workflow/stdout.txt').read_text()
drift = read(packet / 'WORKFLOW_LIVE_SOURCE_DRIFT_004.json')
assert {row['path'] for row in drift} == {
    'gene_annotation_episode/protein_structure_' + name + '.py'
    for name in ('contracts', 'formats', 'metadata', 'sequences')}
assert len(read(packet / 'FILLED_CURRENT_NATIVE_RETURNS_002.json')['examples']) == 3
for row in read(packet / 'MESSAGE_SOURCE_PINS_001.json'):
    assert sha(ROOT / row['path']) == row['sha256'], row['path']

paths = [packet / name for name in (
    'MESSAGE_VERIFICATION_001.md', 'WORKFLOW_VERIFICATION_002.md', 'MESSAGE_SOURCE_PINS_001.json',
    'FILLED_CURRENT_NATIVE_RETURNS_002.json', 'WORKFLOW_LIVE_SOURCE_DRIFT_004.json',
    'check003/receipt.json', 'check003/stdout.txt', 'check003/source_pins_before.json',
    'check004_workflow/receipt.json', 'check004_workflow/stdout.txt',
    'check005_native/receipt.json', 'check005_native/stdout.txt',
    'check005_native/source_pins_before.json')]
paths += [ROOT / 'verification' / name for name in (
    'tool_graders_rna_original_result_presentation_2026-10-27_387/HANDOFF.md',
    'tool_graders_rna_original_result_presentation_2026-10-27_387/check004/receipt.json',
    'tool_graders_rna_one_structure_workflow_2026-10-27_385/VERIFICATION_001.md',
    'tool_graders_rna_one_structure_workflow_2026-10-27_385/check004/receipt.json',
    'tool_graders_rna_one_structure_workflow_2026-10-27_385/LIVE_SOURCE_DRIFT_001.json')]
item = dict(id='RNA-ORIGINAL-MESSAGES-AND-CURRENT-WORKFLOW-091',
    kind='accepted_numerical_grader_and_declared_local_episode_path',
    summary='387 original presentation and388 recurring TASK/provider wiring accepted. '
        '388 check003 passed278 combined message checks with808 stable live/executed pins. '
        'Current388 check004 passed all18 one-input Workflow cases before a missing native dependency '
        'probe caused a harness failure; its845 executed pins stayed unchanged and live drift was '
        'limited to four protein files. Corrected snapshot check005 passed all3 original native '
        'Workflow modes with860 stable live/executed pins. Existing385 check004 passed98 overlapping '
        'cases including actual pair/scan compatibility on its explicitly retained earlier snapshot. '
        'Exact requested structures remain separate from compact scan rank/tie/gap returns. '
        'Two original RNA rows now count under the existing numerical-grader tally definition; '
        'no extra rows for comparisons or presentation. Eight historical broader receipt failures remain.',
    reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths])
contracts = ROOT / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380'
protein_evidence = dict(id='PROTEIN-STRUCTURE-CONTRACTS-AND-CODING-091',
    kind='defined_interfaces_and_unaccepted_implementation_in_progress',
    summary='380 exact contracts and additive002/003 define A inputs/maps, B numerical sheets/calculators, '
        'C native execution and D custody/projections. Fresh386,389 and390 implement A/B/C in parallel. '
        'Root found and386 reproduced unselected-chain/model invalidation and PDB acceptance of CIF-style '
        'uncertainty; the corrected A suite reports85 passing tests and awaits root component acceptance. '
        'No protein component, complete path or tally '
        'increment is accepted in this update.',
    reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in (
        contracts / 'SHARED_CONTRACT_001.md', contracts / 'ROOT_CONTRACT_ADDENDUM_002.md',
        contracts / 'ROOT_CONTRACT_ADDENDUM_003.md')])
for value in (item, protein_evidence):
    assert value['id'] not in {e['id'] for e in status['verification_evidence']}
    status['verification_evidence'].append(value)
rna_ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
protein_id = 'B-L107-compare_protein_structures'
changes = []
for row in status['rows']:
    if row['id'] not in rna_ids | {protein_id}:
        continue
    before = deepcopy(row)
    if row['id'] in rna_ids:
        row.update(overall='numerical_grader_and_declared_local_episode_path_verified',
            source_presence='single_input_comparison_and_all_rna_message_paths_reviewed',
            production_result_binding='single_input_comparison_selected_structure_scan_and_all_rna_message_boundaries_verified',
            integration_verification='accepted360_372_paths_385_98_snapshot_checks_388_278_messages_18_current_one_input_3_current_native',
            live_resource_verification='388_current_viennarna_2_7_0_local_prediction_evaluation_topology_workflows_verified')
        row['evidence_ids'].append(item['id'])
        row['note'] += (' Update091: original single-input messages and the genuine one-input retained '
            'structure return are implemented and accepted. Current shared wiring passes278 message checks, '
            '18 one-input Workflow cases and3 native modes. The native dependency snapshot failure and '
            'four unrelated protein source changes remain explicitly recorded. Accepted earlier pair/scan '
            'paths retain parent-selected returns, complete saved data and unchanged credit semantics. '
            'This row now counts in112/308; no comparison/presentation row is added. Broader historical '
            'receipt failures and other deployments remain open; no full-repository pass is claimed.')
    else:
        row.update(overall='input_calculation_execution_implementation_in_progress',
            source_presence='exact_contracts_and_input_execution_sources_present_under_review',
            tool_information='local_tool_information_source_present_unverified',
            invocation_contract='defined_contract_local_execution_implementation_in_progress',
            numerical_sheet='implementation_in_progress_not_verified',
            native_parser='pdb_mmcif_component_implemented_final_review_pending',
            metadata_extractor='component_implemented_final_review_pending',
            deterministic_calculator='implementation_in_progress_not_verified')
        row['evidence_ids'].append(protein_evidence['id'])
        row['note'] += (' Update091: exact380 interfaces and002/003 clarifications precede fresh A386/B389/C390 '
            'coding. Input/parser review found concrete isolated-selection and numeric-format defects; '
            'the corrected A suite reports85 passes and awaits root acceptance. No whole protein path or tally acceptance.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {x['id'] for x in changes} == rna_ids | {protein_id}
binding_ids = {identifier + '::local' for identifier in rna_ids}
binding_changes = []
for row in status['resource_bindings']:
    if row['id'] not in binding_ids:
        continue
    before = deepcopy(row)
    row.update(production_result_binding='single_input_comparison_and_all_rna_message_boundaries_verified',
        integration_verification='388_278_messages_18_current_one_input_3_current_native_workflows_plus_accepted_pair_scan',
        live_resource_verification='388_current_local_viennarna_2_7_0_prediction_evaluation_topology_verified',
        prerequisites_present='actual_viennarna_2_7_0_native_dependencies_used_and_pinned_in388check005',
        native_format_observed='388_actual_native_rna_json_and_full_local_bundles_acquired')
    row['evidence_ids'].append(item['id'])
    binding_changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert len(binding_changes) == 2
status['verified_bound_local_tool_mode_rows'] = 42
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in rna_ids | {protein_id})
assert all(a == b for a, b in zip(original['resource_bindings'], status['resource_bindings']) if a['id'] not in binding_ids)
checklist = deepcopy(previous['work_item_states'])
for entry in checklist:
    if entry['id'] == 'U05':
        entry['current_evidence'] += (' Update091: the remaining original RNA message and single-input '
            'structure work is accepted with current278 message checks,18 one-input Workflow cases and3 '
            'native modes. Both RNA rows now enter112/308 and local bindings42. Protein A/B/C implementation '
            'continues against380/002/003; D and shared protein integration remain unfinished. Eight historical '
            'receipt failures and all remaining196 fixed rows stay open. W05/literature remain separate.')
assert [(x['id'], x['original_item'], x['status']) for x in checklist] == [
    (x['id'], x['original_item'], x['status']) for x in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-27', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, resource_binding_changes=binding_changes,
    added_evidence=[item, protein_evidence],
    numerical_grader_progress_tally=dict(before=110, after=112, added_row_ids=sorted(rna_ids),
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=42), remaining_fixed_rows_outside_tally=196,
    completed_work=[item['summary']], findings_requiring_repair=[
        'Eight historical receipt-test failures remain separate under U05.',
        'Protein input, calculation and execution implementation remains under verification; custody/projection/shared integration remains unfinished.',
        'Authentic native-mode/HPC work under U03 and all other fixed tool rows remain.'],
    work_item_states=checklist, unfinished_work=[x['current_evidence'] for x in checklist if x['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.091.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=len(changes), updated_resource_bindings=len(binding_changes),
    numerical_grader_progress_tally=112, verified_bound_local_tool_mode_rows=42,
    remaining_fixed_rows_outside_tally=196, new_status_sha256=sha(STATUS))))
