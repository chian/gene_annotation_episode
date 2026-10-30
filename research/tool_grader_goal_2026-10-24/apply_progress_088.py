"""Record accepted U06 verification without changing the fixed tool scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_088.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_087.json')
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
integration = base / 'tool_graders_blast_database_population_integration_2026-10-26_365'
review = base / 'tool_graders_blast_population_review_2026-10-26_375'
final = base / 'tool_graders_blast_population_final_hosts_2026-10-26_376'
for rows in read(integration / 'SOURCE_PINS_CURRENT_002.json').values():
    for entry in rows:
        path = ROOT / entry['path']
        assert sha(path) == entry['sha256']
        assert path.stat().st_size == entry['size_bytes']
for path in [integration / part / 'receipt.json' for part in
             ('final_custody_009', 'remaining_hosts_010', 'alias_011')] + [final / 'check001/receipt.json']:
    receipt = read(path)
    assert receipt['returncode'] == 0
    assert read(path.parent / 'before-source-pins.json') == read(path.parent / 'after-source-pins.json')


def evidence(identifier, kind, summary, paths):
    return dict(id=identifier, kind=kind, summary=summary,
        reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths])


contract = base / 'tool_graders_rna_comparison_contract_2026-10-26_362'
rna = base / 'tool_graders_rna_comparison_results_2026-10-26_371'
items = [
    evidence('BLAST-POPULATION-ASSOCIATION-INTEGRATION-088', 'accepted_bounded_U06_repair',
        'U06 explicit original-native-database/census association accepted after fresh375 complete-path review and root376 '
        'final-source follow-up: nine positive host cases passed, five deselected, exit0, source pins unchanged. Together '
        'with365 final25+20+1,55 distinct new cases have final-production-source receipts. Actual selected workers, '
        'calculators, publication and typed-return functions are exercised by synthetic hosts which manually journal '
        'actions/delivery; this is not a new complete method_loop/controller investigation or live database/HPC run. '
        'The existing conditional function kernel is unchanged. No new tool count; profile/domain and VDB contracts unchanged.',
        [final / 'ROOT_ACCEPTANCE_001.md', final / 'check001/receipt.json',
         final / 'check001/before-source-pins.json', final / 'check001/after-source-pins.json',
         review / 'REVIEW_001.md', review / 'SOURCE_COMPARISON_001.json',
         integration / 'SOURCE_PINS_CURRENT_002.json',
         integration / 'final_custody_009/receipt.json',
         integration / 'remaining_hosts_010/receipt.json', integration / 'alias_011/receipt.json']),
    evidence('RNA-COMPARISON-REMAINING-REPAIRS-088', 'known_pending_namespace_and_fixture_repairs',
        'E008 finished67pass1fail. Its failure is an invalid empty parent-form fixture. Before/after source changes are '
        'only literature_episodes.py,literature_experimental_prompt.py,literature_reference_parent_prompt.py; no claim '
        'that the broad snapshot is unchanged. Separate inspection found selected nonanchor handoffs incorrectly denied '
        'and unselected known handoffs admitted by generic fallback. Addenda012/013 define the correction and focused '
        'verification. Shared005 remains running at this accounting checkpoint; production edits await its completion. '
        'Presentation374 remains unimplemented. Neither RNA row is added to the tally.',
        [rna / 'check008/receipt.json', rna / 'check008/stdout.txt',
         rna / 'check008/source_pins_before.json', rna / 'check008/source_pins_after.json',
         contract / 'CONTRACT_ADDENDUM_012.md', contract / 'CONTRACT_ADDENDUM_013.md']),
]
assert not {e['id'] for e in items} & {e['id'] for e in status['verification_evidence']}
status['verification_evidence'].extend(items)
ids = {f'A-L069-{name}-database' for name in ('blastn', 'blastp', 'blastx', 'tblastn', 'tblastx')}
ids.update(('A-L070-psiblast-database', 'A-L070-deltablast-database'))
rna_ids = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in ids | rna_ids:
        continue
    before = deepcopy(row)
    if row['id'] in ids:
        row['production_result_binding'] += '_explicit_selected_native_operand_census_association_verified'
        row['integration_verification'] += '_U06_55_final_production_source_synthetic_host_cases_verified'
        row['evidence_ids'].append(items[0]['id'])
        row['note'] += (' Update088:bounded U06 association repair accepted after fresh375 complete-path review and '
            'root376 nine-case final-source follow-up.55 distinct new integration/custody cases have final-production-source '
            'receipts; earlier277 regression passes remain historical. Synthetic hosts exercise actual workers/calculators '
            'and typed returns but manually journal actions/closure/delivery. No new full method_loop investigation, '
            'native database search, resource deployment or calibrated annotation probability. Original source fields, '
            'unknown release/scope, failure history and quality locators are preserved. Saved public calculation and '
            'worker reuse are verified; no new standard/PSI/DELTA episode-accessible saved-function selector is claimed.')
    else:
        row['integration_verification'] += '_E008_67pass1_invalid_fixture_fail_namespace_fix_and_shared005_pending'
        row['evidence_ids'].append(items[1]['id'])
        row['note'] += (' Update088:E008 ended67pass1invalid-empty-form-fixture failure; only three unrelated literature '
            'files changed during that broad snapshot. Selected/unselected original handoff namespace defects are '
            'explicitly scoped in362addenda012/013. Shared005 remains running. These facts do not establish final '
            'comparison adapter acceptance or prompt implementation. User scan/two-structure direction is already '
            'preserved verbatim in362addendum006; it is not replaced by another paraphrased record.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {c['id'] for c in changes} == ids | rna_ids
binding_changes = []
for binding in status['resource_bindings']:
    if binding['id'] not in {identifier + '::hpc' for identifier in ids}:
        continue
    before = deepcopy(binding)
    binding['production_result_binding'] += '_explicit_native_operand_census_association_verified_synthetically'
    binding['integration_verification'] += '_U06_final_source_synthetic_host_worker_and_return_verification_accepted'
    binding['evidence_ids'].append(items[0]['id'])
    binding_changes.append(dict(id=binding['id'], before=before, after=deepcopy(binding)))
assert len(binding_changes) == 7
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids | rna_ids)
assert all(a == b for a, b in zip(original['resource_bindings'], status['resource_bindings'])
           if a['id'] not in {identifier + '::hpc' for identifier in ids})
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U06':
        item['status'] = 'complete'
        item['current_evidence'] += (' Update088:bounded U06 is complete. Fresh375 reviewed complete affected paths and '
            'all119 saved example artifact references; all16 final pins match. Root376 reran the nine positive hosts '
            'left at the earlier worker version:9pass5deselected,exit0,unchanged sources. Final-source55distinct new '
            'cases plus prior accepted pure/metadata evidence support the explicit selected-operand/census association. '
            'Original observations and formulas remain; U03 live-resource/native-format work remains open. No tally increase.')
    elif item['id'] == 'U05':
        item['current_evidence'] += (' Update088:RNA E008 ended67pass1invalid-empty-form-fixture failure; broad source '
            'changes were confined to three unrelated literature modules. Shared005 still running. Explicit selected '
            'nonanchor/unselected handoff resolver corrections are scoped in362addenda012/013 and await the source '
            'freeze release. Prompt374 remains unimplemented. Fresh377 is planning the required B-L107 protein '
            'structure comparison contract only; no protein implementation or count is claimed.')
assert [(i['id'], i['original_item']) for i in checklist] == [(i['id'], i['original_item']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-27', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, resource_binding_changes=binding_changes, added_evidence=items,
    numerical_grader_progress_tally=dict(before=110, after=110, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[items[0]['summary']],
    findings_requiring_repair=[
        'Eight broader receipt baseline failures remain under U05, distinct from completed U04.',
        'RNA selected/unselected original handoff namespaces and the invalid empty-form test fixture need the scoped repair.',
        'Final RNA adapter/Workflow verification and comparison TASK/STEERING implementation remain outstanding.'],
    work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.088.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=len(changes), updated_resource_bindings=len(binding_changes),
    U06='complete', numerical_grader_progress_tally=110, remaining_fixed_rows_outside_tally=198,
    new_status_sha256=sha(STATUS))))
