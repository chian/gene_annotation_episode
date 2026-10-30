"""Record accepted census/receipt repairs and the assigned RNA scientific lane."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_079.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if UPDATE.exists():
    raise RuntimeError('Immutable update already exists')
previous = read(HERE / 'PROGRESS_UPDATE_078.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 108
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']

census = ROOT / 'verification/tool_graders_blast_vdb_census_relation_repair_2026-10-26_350'
boundary = ROOT / 'verification/tool_graders_blast_database_receipt_boundary_2026-10-26_352'
rna = ROOT / 'verification/tool_graders_rna_structure_plan_2026-10-26_349'
for packet, run, count in [(census, 'after_suite_001', 209), (boundary, 'after001', 33)]:
    receipt = read(packet / run / 'receipt.json')
    meta = receipt.get('metadata', receipt)
    assert receipt.get('returncode', meta.get('native_returncode')) == 0
    assert meta['policy'] == dict(memory_bytes=20*1024**3, scratch_bytes=4*1024**3, wall_seconds=None)
    assert f'{count} passed' in (packet / run / 'stdout.txt').read_text()
assert read(boundary / 'after001/source-before.json') == read(boundary / 'after001/source-after.json')

specs = [
    ('BLAST-VDB-CENSUS-REPAIRS-079', census,
     ['ROOT_REVIEW_001.md', 'HANDOFF_001.md', 'FINAL_PINS_001.json',
      'ARTIFACT_INDEX_001.json', 'after_suite_001/receipt.json', 'after_suite_001/stdout.txt'],
     'Both census-relation defects repaired and root accepted: 209 tests, including 29 new regressions, and 17 complete checked numerical examples. Optional unknown relations no longer invalidate baseline enumeration; contradictory available sample identities withhold correction. Original valid inputs and historical bytes remain unchanged.'),
    ('BLAST-DATABASE-RECEIPT-BOUNDARY-079', boundary,
     ['OWNERSHIP_001.md', 'REVIEW_001.md', 'BEFORE_PINS_001.json',
      'after001/source-before.json', 'after001/source-after.json', 'after001/receipt.json', 'after001/stdout.txt'],
     'Root repaired source-only receipt expansion and native artifact resolver fallback. 33 tests pass at stable source: actual legacy/new child returns withhold unrequested files, explicitly requested saved-sheet artifacts remain accessible, and historical records remain unchanged.'),
    ('RNA-SCIENTIFIC-CONTRACT-079', rna,
     ['PLAN.md', 'CONTRACT_ADDENDUM_001.md', 'CONTRACT_ADDENDUM_002.md'],
     'Independent RNA topology/parser/sheet/calculator interfaces accepted with explicit missing-native and original-input contracts. Fresh354 is assigned the four scientific modules. Result-publication/failed-bundle/presentation interfaces still need correction before that separate coding lane. No RNA implementation or completion is claimed.'),
]
evidence = []
for identity, packet, names, summary in specs:
    item = dict(id=identity, kind='reviewed_component' if packet != rna else 'accepted_coding_contract',
        summary=summary, reports=[dict(path=str((packet/name).relative_to(ROOT)), sha256=sha(packet/name)) for name in names],
        qualification='Supplied/synthetic verification and planning; no live database/API/HPC execution or tool tally increase.')
    assert not any(r['id'] == identity for r in status['verification_evidence'])
    status['verification_evidence'].append(item)
    evidence.append(item)

vdb = {'A-L070-blastn_vdb-database', 'A-L070-tblastn_vdb-database'}
rna_rows = {'B-L103-predict_rna_secondary_structure', 'B-L104-analyze_rna_secondary_structure_features'}
changes = []
for row in status['rows']:
    if row['id'] not in vdb | rna_rows:
        continue
    before = deepcopy(row)
    if row['id'] in vdb:
        row['overall'] = 'partial_vdb_census_and_receipt_repairs_verified_final_integration_pending'
        row['numerical_verification'] += '_350_repaired_inputs_209_combined_tests_and17_checked_examples'
        row['integration_verification'] += '_352_requested_artifact_boundary_33_checks_passed_at_stable_source'
        row['evidence_ids'].extend(e['id'] for e in evidence[:2])
        row['note'] += (' Update079:350 census repairs and root352 requested-artifact boundary accepted. '
            '347 captured/saved integration remains in progress: repeated HSP returns with different publication '
            'metadata reproduced a merge conflict. Saved-version failure mapping and final regressions remain '
            'under integration review. Both VDB rows remain outside108; no live native/HPC claim.')
    else:
        row['overall'] = 'scientific_contract_accepted_fresh_implementation_assigned'
        row['evidence_ids'].append(evidence[2]['id'])
        row['note'] += (' Update079:349 planning and additive002 scientific-lane contract accepted. '
            'Fresh354 assigned pure fields/parsers/calculators. No implemented fields or production binding '
            'is claimed yet. ViennaRNA absent in both probed environments; pure topology needs no native '
            'dependency. Separate result-publication and presentation interfaces still need correction.')
    changes.append(dict(group='rows', id=row['id'], before=before, after=deepcopy(row)))
assert len(changes) == 4
assert status['resource_bindings'] == original['resource_bindings']
assert [r['id'] for r in status['rows']] == [r['id'] for r in original['rows']]
assert all(a == b for a,b in zip(original['rows'],status['rows']) if a['id'] not in vdb | rna_rows)

checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U02':
        item['current_evidence'] = ('350 census corrections and352 requested-artifact receipt/resolver repair '
            'implemented and verified.347 final captured/saved integration continues, including the reproduced '
            'HSP publication-metadata replay conflict. Both VDB rows remain outside108.')
    if item['id'] == 'U05':
        item['current_evidence'] = ('All remaining fixed308 rows and resource bindings stay in scope. '
            'RNA scientific lane accepted with exact absent-input interfaces and assigned to fresh354. '
            '353 reviews remaining publication/presentation handoffs before those lanes are assigned. '
            'Neither RNA tool is counted; W05 and literature grading remain separate.')
assert [(i['id'],i['original_item'],i['status']) for i in checklist] == [
    (i['id'],i['original_item'],i['status']) for i in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=108,after=108,added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40,after=40), remaining_fixed_rows_outside_tally=200,
    completed_work=[e['summary'] for e in evidence[:2]],
    findings_requiring_repair=['347 reproduced an HSP publication-metadata conflict for captured/saved returns of the same calculation; integration correction and supported-order verification remain in progress.'],
    work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status']!='complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE/'SCOPE.json') == scope_sha
with UPDATE.open('x') as f:
    json.dump(update,f,indent=2,ensure_ascii=False)
    f.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.079.writing')
with temporary.open('xb') as f:
    f.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=4,updated_resource_bindings=0,scope_rows=308,
    numerical_grader_progress_tally=108,remaining_fixed_rows_outside_tally=200,new_status_sha256=sha(STATUS))))
