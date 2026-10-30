"""Record verified RNA comparison paths without changing scope or the tally."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_089.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_088.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 110
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']
base = ROOT / 'verification'
contract = base / 'tool_graders_rna_comparison_contract_2026-10-26_362'
adapters = base / 'tool_graders_rna_comparison_results_2026-10-26_371'
shared = base / 'tool_graders_rna_comparison_shared_integration_2026-10-26_372'
pure = base / 'tool_graders_rna_comparison_presentation_2026-10-27_378'
scientific = base / 'tool_graders_rna_scientific_text_integration_2026-10-27_379'
for packet, check in ((adapters, 'check009'), (shared, 'check005'),
        (shared, 'check006'), (shared, 'check007'), (pure, 'check004'), (scientific, 'check004')):
    receipt = read(packet / check / 'receipt.json')
    assert receipt['returncode'] == 0
    assert receipt['metadata']['policy'] == dict(memory_bytes=20 * 1024**3,
        scratch_bytes=4 * 1024**3, wall_seconds=None)
    if packet == scientific:
        assert receipt['live_source_pins_unchanged'] and receipt['executed_snapshot_pins_unchanged']
    elif packet == adapters:
        assert receipt['source_pins_unchanged'] is False
        before = {r['path']: r['sha256'] for r in read(packet / check / 'source_pins_before.json')}
        after = {r['path']: r['sha256'] for r in read(packet / check / 'source_pins_after.json')}
        changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
        assert len(changed) == 7 and all(p.startswith('gene_annotation_episode/literature_') for p in changed)
    else:
        assert receipt['source_pins_unchanged']

for filename, digest in {
    'rna_structure_comparison_results.py': '2e1a4dfe2ac409018dc87073ea7897399b30904f8d7140a12adcf754304a5bcc',
    'execution_episodes.py': '3d54dae5e11b218562f2c7f43f469b4abb8c451c109c05b1cc69f088ce8ab074',
    'execution_progress.py': '2da934e8e3bb5decac2466e5278a45cea51e8fbd7252bcd5bb66552ce1cbc6df',
    'rna_structure_comparison_presentation.py': '0e64f7fe886427208517c46e95135b82d7396f33b22e2b0ea66d83fa547cdcd2',
    'scientific_process_prompt.py': 'd806b5198fb8ae7bebd5fbe2d1324d30cf92ad4e8c5769aa53e9103c1cec5cbe',
}.items():
    assert sha(ROOT / 'gene_annotation_episode' / filename) == digest


def evidence(identifier, kind, summary, paths):
    return dict(id=identifier, kind=kind, summary=summary,
        reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths])


items = [
    evidence('RNA-COMPARISON-WORKFLOW-089', 'accepted_retained_comparison_integration',
        'E009 passed five focused final-guard cases; global pins changed only in seven unrelated literature files. '
        'Shared005 passed 24 checks with stable sources before that guard;006 passed two original regressions;007 '
        'passed the final actual Workflow namespace case with all 74 listed pins unchanged. Selected original '
        'handoffs resolve; unselected handoffs do not. Actual typed pair/scan returns, one observation per own action, '
        'zero new acquisition credit and ordinary practical completion are verified with synthetic scientific inputs. '
        'No new native experiment, model judgment or whole-tool completion is claimed.',
        [contract / 'ROOT_INTEGRATION_REVIEW_001.md', adapters / 'HANDOFF_001.md',
         adapters / 'check009/receipt.json', adapters / 'CHECK009_SOURCE_DRIFT_001.diff',
         shared / 'HANDOFF_001.md', shared / 'check005/receipt.json', shared / 'check006/receipt.json',
         shared / 'check007/receipt.json', shared / 'SOURCE_PINS_FINAL_001.json',
         shared / 'FILLED_ACTUAL_PAIR_001.json', shared / 'FILLED_ACTUAL_SCAN_001.json']),
    evidence('RNA-SCIENTIFIC-RECEIVER-TEXT-089', 'accepted_scoped_presentation_integration',
        'Pure378 final004 passed 27 tests. Scientific379 final004 passed 80 overlapping tests:32 new scientific '
        'receiver checks,27 pure checks and21 existing regressions, with live and executed snapshots unchanged. '
        'Actual controlled turn/start text preserves full original TASK and selected RNA tables through bootstrap, '
        'update, lookup and restoration. Two structures render only when requested; aggregate scans return selected '
        'rank/ties/gap/coverage without structures. Root/results and old single-input presentation remain unfinished.',
        [pure / 'VERIFICATION_001.md', pure / 'check004/receipt.json',
         scientific / 'VERIFICATION_001.md', scientific / 'FINAL_DIFF_001.diff',
         scientific / 'check004/receipt.json', scientific / 'FINAL_SOURCE_IDENTITIES_001.json',
         scientific / 'FILLED_RENDERED_EXAMPLES_001.json']),
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
        overall='single_input_and_comparison_workflow_verified_scientific_receiver_text_verified_other_rna_presentation_unfinished',
        source_presence='single_input_and_retained_comparison_paths_reviewed_scientific_text_integration_reviewed',
        invocation_contract='single_input_child_owned_workflow_and_selected_retained_comparison_binding_verified',
        production_result_binding='single_input_and_comparison_worker_typed_returns_and_scientific_text_verified_root_results_text_unfinished',
        integration_verification='360_single_input_workflow_accepted_371_final_five_cases_372_24_plus_two_original_plus_final_namespace_379_80_text_checks',
    )
    row['evidence_ids'].extend(e['id'] for e in items)
    row['note'] += (' Update089: comparison adapters and shared Workflow path accepted for the tested scope. '
        'E009 global source drift is explicitly limited to seven unrelated literature files; shared007 tests final '
        'namespace correction with stable listed pins.379 independently pins the renderer files omitted from372. '
        'Scientific receiver TASK stays unchanged; selected tables are verified at the controlled provider boundary. '
        'Root/results/legacy recipient and original single-input text remain unfinished. The two local binding rows '
        'now record existing verified component evidence instead of stale not_assessed values. No new tally entry, '
        'live scientific run, root-tool restoration, W05 scoring or literature implementation is claimed.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {c['id'] for c in changes} == ids
binding_changes = []
for binding in status['resource_bindings']:
    if binding['id'] not in {identifier + '::local' for identifier in ids}:
        continue
    before = deepcopy(binding)
    binding.update(
        invocation_contract='single_input_and_retained_comparison_child_owned_contracts_verified',
        production_result_binding='single_input_and_comparison_workflow_verified_remaining_presentation_unfinished',
        integration_verification='360_single_input_372_retained_comparison_workflow_379_scientific_text_verified',
        live_resource_verification='360_actual_local_single_input_viennarna_2_7_0_retained_comparisons_use_synthetic_inputs_no_new_native_run',
        prerequisites_present='recorded_viennarna_2_7_0_execution_in360_not_reprobed_in089',
        native_format_observed='360_original_native_rna_json_observed_new_comparison_fixtures_labeled_synthetic',
    )
    binding['evidence_ids'].extend(e['id'] for e in items)
    binding_changes.append(dict(id=binding['id'], before=before, after=deepcopy(binding)))
assert len(binding_changes) == 2
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)
assert all(a == b for a, b in zip(original['resource_bindings'], status['resource_bindings'])
    if a['id'] not in {identifier + '::local' for identifier in ids})
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] += (' Update089: final RNA retained-comparison adapter and shared Workflow checks '
            'are accepted. Pure selected presentation and scientific-recipient text are implemented;80 final focused '
            'text checks passed. Root/results/legacy and original single-input RNA presentation remain unfinished, '
            'alongside eight historical receipt-test failures. Fresh380 is completing exact shared protein structure '
            'contracts and the existing scientific-child sequence.align handoff trace before independent coding. '
            'No protein implementation or new tool count is claimed. Other fixed rows remain in scope.')
assert [(i['id'], i['original_item'], i['status']) for i in checklist] == [
    (i['id'], i['original_item'], i['status']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-27', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, resource_binding_changes=binding_changes, added_evidence=items,
    numerical_grader_progress_tally=dict(before=110, after=110, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[e['summary'] for e in items],
    findings_requiring_repair=[
        'Eight historical receipt-test failures remain separate under U05.',
        'RNA results/root/legacy receiver and old single-input presentation remain unfinished.',
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
temporary = STATUS.with_name('.WORK_STATUS.089.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=len(changes), updated_resource_bindings=len(binding_changes),
    numerical_grader_progress_tally=110, remaining_fixed_rows_outside_tally=198,
    new_status_sha256=sha(STATUS))))
