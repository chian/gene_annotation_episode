"""Record verified comparison messages; preserve scope and scientific tally."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_090.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_089.json')
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
packet = ROOT / 'verification/tool_graders_rna_comparison_prompt_delivery_2026-10-27_383'
receipt = read(packet / 'check002/receipt.json')
assert receipt['returncode'] == 0
assert receipt['live_source_pins_unchanged'] and receipt['executed_snapshot_pins_unchanged']
assert receipt['metadata']['policy'] == dict(memory_bytes=20 * 1024**3,
    scratch_bytes=4 * 1024**3, wall_seconds=None)
assert '195 passed' in (packet / 'check002/stdout.txt').read_text()
pins = read(packet / 'check002/source_pins_before.json')
assert len(pins) == 793
for filename, digest in {
    'providers.py': '440423d225d0a7962e7618e74060ea7e88fa797eb3b86285bb9abc7acab5fbc1',
    'execution_episodes.py': '2fca0831bf8622b24bc71ecf45112af03904beaa4f7481a6c3ae95b744e0dbaf',
    'rna_structure_comparison_prompt.py': '42b5c62601af486942414872841ca003bccb1baf7eacdf26d2a556ac7607b1a4',
    'rna_structure_comparison_receiver_prompt.py': '47d598867eabb2c253589fbe0a6be4ed906e99de9576f84d8e64d2ad12c7e529',
    'scientific_process_prompt.py': 'd806b5198fb8ae7bebd5fbe2d1324d30cf92ad4e8c5769aa53e9103c1cec5cbe',
    'rna_structure_comparison_presentation.py': '0e64f7fe886427208517c46e95135b82d7396f33b22e2b0ea66d83fa547cdcd2',
}.items():
    relative = 'gene_annotation_episode/' + filename
    assert sha(ROOT / relative) == digest
    assert any(row['path'] == relative and row['sha256'] == digest for row in pins)

paths = [packet / 'VERIFICATION_001.md', packet / 'check002/receipt.json',
    packet / 'check002/source_pins_before.json', packet / 'check002/source_pins_after.json',
    packet / 'check002/snapshot_pins_after.json', packet / 'check002/stdout.txt',
    ROOT / 'verification/tool_graders_rna_comparison_contract_2026-10-26_362/PRESENTATION_HANDOFF_014.md',
    ROOT / 'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_015.md']
item = dict(id='RNA-COMPARISON-MESSAGE-DELIVERY-090', kind='accepted_scoped_presentation_integration',
    summary='381 results TASK,382 general parent TASK and383 provider dispatch are implemented. '
        'Final383 check002 passed195 overlapping tests with all793 live and executed source pins unchanged. '
        'The receiving capability is recognized from an empty initial group so the first later child return '
        'retains the full original TASK and fixed developer instructions. Exact selected pair/scan facts, '
        'lookup, reconstruction and legacy branches are verified at controlled turn/start. No live model, '
        'new scientific execution or new complete Workflow was run. Original single-input messages remain unfinished.',
    reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths])
assert item['id'] not in {e['id'] for e in status['verification_evidence']}
status['verification_evidence'].append(item)
ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row.update(
        overall='single_input_and_comparison_workflow_verified_comparison_messages_verified_original_single_input_messages_unfinished',
        source_presence='single_input_and_retained_comparison_paths_reviewed_comparison_message_delivery_reviewed',
        production_result_binding='single_input_and_comparison_typed_paths_and_comparison_results_parent_scientific_text_verified_original_text_unfinished',
        integration_verification='360_single_input_372_comparison_workflow_379_scientific_text_383_195_combined_message_checks')
    row['evidence_ids'].append(item['id'])
    row['note'] += (' Update090: comparison results, root and legacy receiving-parent TASK/STEERING are now '
        'verified through the controlled provider boundary, including empty bootstrap followed by first child facts. '
        '195 combined tests passed with stable live/executed sources; these overlap earlier evidence. '
        'Requested structures stay separate from compact scan returns. The original single-input RNA message '
        'path remains unfinished;384 is defining that contract and checking the existing genuine one-input '
        'structure-only route. No new native/model run, complete Workflow, literature grading or W05 change. '
        'Neither RNA row enters the110/308 tally yet.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {c['id'] for c in changes} == ids
binding_ids = {identifier + '::local' for identifier in ids}
binding_changes = []
for binding in status['resource_bindings']:
    if binding['id'] not in binding_ids:
        continue
    before = deepcopy(binding)
    binding.update(
        production_result_binding='single_input_and_comparison_workflow_and_comparison_messages_verified_original_single_input_messages_unfinished',
        integration_verification='360_single_input_372_comparison_workflow_383_195_comparison_message_checks')
    binding['evidence_ids'].append(item['id'])
    binding_changes.append(dict(id=binding['id'], before=before, after=deepcopy(binding)))
assert len(binding_changes) == 2
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)
assert all(a == b for a, b in zip(original['resource_bindings'], status['resource_bindings'])
    if a['id'] not in binding_ids)
checklist = deepcopy(previous['work_item_states'])
for entry in checklist:
    if entry['id'] == 'U05':
        entry['current_evidence'] += (' Update090: comparison results/root/legacy messages are implemented and '
            'verified in383 final195-test provider suite with stable sources. Original single-input RNA '
            'messages and a real Workflow verification of the existing one-input structure-only request remain '
            'unfinished.384 is specifying those exact handoffs.380 continues exact protein structure shared '
            'contracts; protein implementation has not begun. Eight historical receipt failures and all other '
            'fixed rows remain. No tally increment or new live scientific experiment.')
assert [(i['id'], i['original_item'], i['status']) for i in checklist] == [
    (i['id'], i['original_item'], i['status']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-27', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, resource_binding_changes=binding_changes, added_evidence=[item],
    numerical_grader_progress_tally=dict(before=110, after=110, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[item['summary']],
    findings_requiring_repair=[
        'Original single-input RNA message paths remain unfinished;384 is defining exact handoffs.',
        'Existing one-input structure-only route requires truthful TASK wording and real Workflow verification.',
        'Eight historical receipt-test failures remain separate under U05.',
        'Protein structure exact shared contracts precede its unstarted coding workloads.'],
    work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.090.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=len(changes), updated_resource_bindings=len(binding_changes),
    numerical_grader_progress_tally=110, remaining_fixed_rows_outside_tally=198,
    new_status_sha256=sha(STATUS))))
