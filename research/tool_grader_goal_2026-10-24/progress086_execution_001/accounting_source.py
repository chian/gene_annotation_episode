"""Record accepted components, a repaired review finding and unfinished integration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_086.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_085.json')
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


native = ROOT / 'verification/tool_graders_rna_structure_integration_2026-10-26_360'
rna = ROOT / 'verification/tool_graders_rna_comparison_contract_2026-10-26_362'
blast = ROOT / 'verification/tool_graders_blast_database_census_association_plan_2026-10-26_361'
pure = ROOT / 'verification/tool_graders_blast_population_pure_2026-10-26_363'
metadata = ROOT / 'verification/tool_graders_blast_population_metadata_2026-10-26_364'
inputs = ROOT / 'verification/tool_graders_rna_comparison_inputs_2026-10-26_366'
items = [
    evidence('RNA-SINGLE-INPUT-INTEGRATION-086', 'accepted_existing_integration_component',
        '360 shared single-input RNA integration accepted after full changed-consumer review, ten passing RNA Workflow tests, '
        'seven examples/eight result receipts and all38 native-artifact digest/length checks. The broader run has eight failures '
        'reproduced with pre-change modules. Comparison/scan/host/presentation work remains unfinished; no RNA tally increment.',
        [native / 'ROOT_REVIEW_001.md', native / 'FINAL_SOURCE_PINS.json', native / 'NUMERICAL_EXAMPLES.json']),
    evidence('BLAST-PURE-POPULATION-086', 'accepted_pure_scientific_component',
        '363 pure population qualification and saved numerical calculation accepted. Root inspected full affected scientific paths, '
        'both complete new test modules, actual215-pass final targeted receipt, all ten retained synthetic examples and current hashes. '
        'This is not a completed resource/worker/receiving-episode route.',
        [pure / 'ROOT_REVIEW_001.md', pure / 'SOURCE_PINS_CURRENT_001.json', pure / 'source_carrier_004/receipt.json',
         pure / 'examples_002/receipt.json']),
    evidence('BLAST-METADATA-REVIEW-086', 'delivered_component_and_repaired_root_finding',
        '364 metadata component delivered; full root adapter acceptance pending. Root reproduced and corrected one-sided null '
        'release/scope being labeled a known identity conflict. Final56-case focused run passed; original measurements and '
        'known-conflict exclusions preserved.365 worker/return integration and exact current failure resolution remain active.',
        [metadata / 'RESULTS_001.md', metadata / 'SOURCE_RECORD_SELECTION_002.md', metadata / 'ROOT_REVIEW_FINDING_001.md',
         metadata / 'root_unknown_final_011/receipt.json', metadata / 'root_unknown_final_011/source_after.json',
         blast / 'CONTRACT_ADDENDUM_003.md']),
    evidence('RNA-COMPARISON-HANDOFFS-086', 'accepted_pure_handoffs_and_active_coding',
        '366 input/correspondence delivered with122 final focused passes; root source acceptance pending. Fresh367 numerical '
        'and fresh368 selected-projection modules are active against accepted362 contracts. Aggregate scan metrics '
        'and explicit member-rank returns have separate enumerations. Exact tied-minimum numeric representation is defined without '
        'selecting a member/structure return. No completed comparison or prompt claimed.',
        [inputs / 'INTERFACES_001.md', inputs / 'HANDOFF_001.md', inputs / 'FINAL_SOURCE_PINS_001.sha256',
         rna / 'CONTRACT_ADDENDUM_002.md', rna / 'CONTRACT_ADDENDUM_003.md', rna / 'CONTRACT_ADDENDUM_004.md']),
]
assert not {e['id'] for e in items} & {e['id'] for e in status['verification_evidence']}
status['verification_evidence'].extend(items)
ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row['evidence_ids'].extend([items[0]['id'], items[3]['id']])
    row['note'] += (' Update086:360 single-input shared integration accepted;10 RNA Workflow tests pass and38 original native '
        'artifacts verified. Eight separate broader baseline failures remain.366 inputs delivered; root acceptance pending.367 '
        'numerical and368 selected-projection coding active. Multi-input worker/host integration and presentation unfinished. No tally change.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {c['id'] for c in changes} == ids
assert status['resource_bindings'] == original['resource_bindings']
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] += (' Update086:360 single-input integration accepted. Its broader eight baseline failures '
            'remain separate from completed U04.366 input/correspondence delivered with122 final focused passes; root acceptance '
            'pending.367 numerical and368 selected projection coding active; retained multi-input worker/host and presentation '
            'remain unfinished. Both RNA rows remain outside the tally.')
    elif item['id'] == 'U06':
        item['status'] = 'in_progress'
        item['current_evidence'] = ('363 pure component accepted with actual215 final targeted passes and ten synthetic examples. '
            '364 metadata delivered; full root adapter review pending. Root repaired one-sided unknown release/scope metadata '
            'classification with56 final focused passes.365 worker/typed-return integration is active;361 addendum003 preserves '
            'the original unproven-binding note while allowing exact source-validated population resolution to remove only its '
            'current mapped failure. No integrated U06 completion or tally increment; VDB policy unchanged.')
assert [(i['id'], i['original_item']) for i in checklist] == [(i['id'], i['original_item']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=items,
    numerical_grader_progress_tally=dict(before=110, after=110, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[items[0]['summary'], items[1]['summary'],
        'Specific one-sided missing release/scope metadata classification corrected and verified with56 focused passing cases; full adapter acceptance remains separate.'],
    findings_requiring_repair=[
        'Eight broader episode_receipts failures reproduce with pre-360 modules; no full-repository pass. They remain under U05 and are separate from the completed original U04 failures.',
        '365 must finish exact current failure classification and worker/typed-receiver verification before U06 acceptance.'],
    work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.086.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, numerical_grader_progress_tally=110,
    remaining_fixed_rows_outside_tally=198, new_status_sha256=sha(STATUS))))
