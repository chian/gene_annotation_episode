"""Record accepted RNA components and repair stale structured status columns."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_087.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_086.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 110
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']


def evidence(identifier, kind, summary, paths):
    return dict(id=identifier, kind=kind, summary=summary,
        reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths])


base = ROOT / 'verification'
contract = base / 'tool_graders_rna_comparison_contract_2026-10-26_362'
prefix = base / 'tool_graders_received_report_prefix_2026-10-26_373'
presentation = base / 'tool_graders_rna_comparison_presentation_plan_2026-10-26_374'
items = [
    evidence('RNA-COMPARISON-COMPONENTS-087', 'accepted_components_not_complete_episode_path',
        'Root accepted complete comparison input, numerical, selected-projection and retained-worker modules plus exact shared '
        'return registration. Actual final checks: A122; B230 including the same122 A; C97; D56; shared registration50. '
        'All exit0 with unchanged sources. Counts overlap and are not summed. Actual bounded calculation workers processed '
        'synthetic and retained inputs; this is not new native RNA execution. E371 and shared372 final verification remains pending.',
        [contract / 'ROOT_COMPONENT_REVIEW_001.md',
         base / 'tool_graders_rna_comparison_inputs_2026-10-26_366/check005/receipt.json',
         base / 'tool_graders_rna_comparison_calculations_2026-10-26_367/check003/receipt.json',
         base / 'tool_graders_rna_comparison_views_2026-10-26_368/check003/receipt.json',
         base / 'tool_graders_rna_comparison_worker_2026-10-26_369/check003/receipt.json',
         base / 'tool_graders_rna_comparison_boundary_2026-10-26_370/check001/receipt.json']),
    evidence('RECEIVED-REPORT-PREFIX-087', 'accepted_shared_authority_and_transaction_fix',
        'Actual report arrival is frozen at child construction, including actual null-source failure forms. Late lower-index '
        'reports do not acquire retrospective authority. Existing rows are not upgraded from later history. Constructor/binding '
        'preserve caller transactions. Final135passed,8knownbaseline cases explicitly deselected,exit0,unchanged sources. '
        'Those eight unresolved failures remain recorded separately; no full-suite pass or extra scientific record/credit.',
        [prefix / 'ROOT_REVIEW_001.md', prefix / 'check002/receipt.json', prefix / 'check002/source_after.json',
         contract / 'CONTRACT_ADDENDUM_010.md', contract / 'CONTRACT_ADDENDUM_011.md']),
    evidence('RNA-COMPARISON-PRESENTATION-PLAN-087', 'planning_only_not_implemented',
        'F374 traced actual results, published scientific and annotation/root receiving paths and drafted detailed TASK plus '
        'parent-selected STEERING. Root printed the compact scan example and recurring scan TASK for running user feedback. '
        'Current provider/renderer gaps remain: comparison results acquisition wording, selected rows duplicated/raw-rendered '
        'or omitted, and nonpublished receiver JSON. No presentation production code changed; no prompt completion claimed.',
        [presentation / 'PLAN_001.md']),
    evidence('RNA-INTEGRATION-INTERMEDIATE-087', 'verified_subsets_final_integration_pending',
        'E371 check007 four rollback/ancestor/caller-authority cases passed with unchanged sources. Shared372 check006 two '
        'existing single-input native RNA Workflow regressions passed with unchanged sources. Final E008 and shared005 '
        'are still running at this record; no final adapter/full-comparison Workflow acceptance is implied.',
        [base / 'tool_graders_rna_comparison_results_2026-10-26_371/check007/receipt.json',
         base / 'tool_graders_rna_comparison_shared_integration_2026-10-26_372/check006/receipt.json']),
]
assert not {e['id'] for e in items} & {e['id'] for e in status['verification_evidence']}
status['verification_evidence'].extend(items)
ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row.update(
        overall='single_input_workflow_and_comparison_components_verified_comparison_integration_and_presentation_unfinished',
        source_presence='single_input_shared_path_and_comparison_components_reviewed_comparison_adapters_pending_final_acceptance',
        invocation_contract='single_input_child_owned_workflow_verified_retained_comparison_binding_under_final_verification',
        production_result_binding='single_input_workflow_accepted_comparison_worker_and_exact_return_schema_accepted_final_comparison_adapters_pending',
        integration_verification='single_input_360_accepted_ten_workflow_checks_comparison_371_372_final_verification_in_progress',
        live_resource_verification='actual_viennarna_2_7_0_single_input_local_workflow_verified_comparisons_use_saved_inputs_no_new_native_run')
    row['evidence_ids'].extend(e['id'] for e in items)
    row['note'] += (' Update087:corrected stale structured columns that still said360 shared review pending/not assessed; '
        '086 had already accepted that single-input path. Comparison A-D and exact return registration now accepted as '
        'components. Shared frozen received-report prefix/transaction repair verified135pass with8knownbaseline exclusions. '
        'E371 and shared372 final checks running. F374 presentation remains planning-only, with scan TASK/STEERING printed '
        'for feedback. No RNA row/tally increment; no full-repository pass.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {c['id'] for c in changes} == ids
assert status['resource_bindings'] == original['resource_bindings']
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] += (' Update087:corrected RNA structured status to accepted360 single-input Workflow. '
            'Comparison A-D and return registration accepted; frozen-report-prefix/transaction fix verified135pass with '
            'eight knownbaseline exclusions. E371/shared372 final integration checks in progress. Presentation remains '
            'planning-only with parent-question-specific scan TASK/STEERING printed. Both RNA rows remain outside tally.')
    elif item['id'] == 'U06':
        item['current_evidence'] += (' Update087:365 delivered its worker/typed-return handoff and retained examples. '
            'Fresh375 is reviewing complete final paths and source-pinned receipts read-only; root acceptance remains pending.')
assert [(i['id'], i['original_item']) for i in checklist] == [(i['id'], i['original_item']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=items,
    numerical_grader_progress_tally=dict(before=110, after=110, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[items[0]['summary'], items[1]['summary']],
    findings_requiring_repair=[
        'Eight broader receipt baseline failures remain under U05, distinct from the completed original U04 repairs.',
        'RNA comparison results and receiving-episode presentation still requires implementation after concrete user feedback.',
        'Final comparison adapter/Workflow verification and BLAST365 complete-path acceptance remain outstanding.'],
    work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.087.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, numerical_grader_progress_tally=110,
    remaining_fixed_rows_outside_tally=198, new_status_sha256=sha(STATUS))))
