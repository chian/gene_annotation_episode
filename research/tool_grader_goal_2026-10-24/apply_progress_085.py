"""Record the accepted comparison contract and current scoped coding workloads."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_085.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_084.json')
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


rna = ROOT / 'verification/tool_graders_rna_comparison_contract_2026-10-26_362'
blast = ROOT / 'verification/tool_graders_blast_database_census_association_plan_2026-10-26_361'
pure = ROOT / 'verification/tool_graders_blast_population_pure_2026-10-26_363'
items = [evidence('RNA-COMPARISON-CONTRACT-085', 'accepted_pure_implementation_contract',
    '362 parent-defined comparison/scan input, numerical and selected-projection contracts accepted with additive exact ports. '
    'Fresh366 implements input and correspondence modules. Pure numerical and projection workloads are defined for independent '
    'assignment. Worker/host exact handoff review and user-facing presentation remain unfinished; no comparison capability counted.',
    [rna / name for name in ['PLAN_001.md', 'CONSUMER_FINDINGS_001.md', 'SOURCE_PINS_001.json', 'CONTRACT_ADDENDUM_001.md']]),
    evidence('BLAST-POPULATION-HANDOFFS-085', 'accepted_interface_addenda_and_delivered_component',
    '361 additive original bundle/manifest/source carriers and v3 native-report source identity defined.363 pure component '
    'delivered with reported215-check final targeted pass and10 synthetic numerical examples; root source acceptance pending. '
    '364 metadata and fresh365 iteration/actual-worker integration remain in progress. No integrated U06 completion claimed.',
    [blast / 'CONTRACT_ADDENDUM_001.md', blast / 'CONTRACT_ADDENDUM_002.md',
     pure / 'HANDOFF_001.md', pure / 'SOURCE_PINS_CURRENT_001.json', pure / 'VERIFICATION_SUMMARY_001.json'])]
assert not {e['id'] for e in items} & {e['id'] for e in status['verification_evidence']}
status['verification_evidence'].extend(items)
ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row['evidence_ids'].append(items[0]['id'])
    row['note'] += (' Update085:362 comparison/scan contracts and exact pure handoffs accepted;366 input/correspondence coding '
        'started. Parent chooses baseline, population, positions and requested return; scan ranking does not return all structures. '
        '360 shared review, comparison arithmetic, projections, host wiring and presentation remain unfinished. No tally change.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {c['id'] for c in changes} == ids
assert status['resource_bindings'] == original['resource_bindings']
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] += (' Update085:362 comparison/scan numerical contract accepted with exact pure-function '
            'handoffs;366 implements input/correspondence.360 shared integration review remains pending. '
            'No new RNA capability is verified or counted; numerical, projection, worker/host and presentation work remain.')
    elif item['id'] == 'U06':
        item['status'] = 'in_progress'
        item['current_evidence'] = ('361 and additive001/002 exact original-source handoffs accepted.363 pure component delivered '
            'with215 reported final targeted passes and10 synthetic examples; root source review pending.364 metadata and365 '
            'iteration/worker/typed-return integration are active. No U06 integrated completion; VDB policy unchanged.')
assert [(i['id'], i['original_item']) for i in checklist] == [(i['id'], i['original_item']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=items,
    numerical_grader_progress_tally=dict(before=110, after=110, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[], findings_requiring_repair=[], work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.085.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, numerical_grader_progress_tally=110,
    remaining_fixed_rows_outside_tally=198, new_status_sha256=sha(STATUS))))
