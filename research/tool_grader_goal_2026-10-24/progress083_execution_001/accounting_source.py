"""Record accepted VDB numerical graders; preserve all live-resource limits."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_083.json'
POLICY = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_082.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 108
assert status['verified_bound_local_tool_mode_rows'] == 40
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']

calculator = ROOT / 'verification/tool_graders_blast_vdb_function_calculators_2026-10-26_344'
integration = ROOT / 'verification/tool_graders_blast_vdb_function_integration_2026-10-26_347'
for run_name in ('run_012', 'example_run_004'):
    receipt = read(calculator / run_name / 'receipt.json')
    assert receipt['native_returncode'] == 0 and receipt['policy'] == POLICY
assert '180 passed' in (calculator / 'run_012/stdout.txt').read_text()
for run_name, code, summary in (
    ('run012', 1, '18 failed, 429 passed, 5 deselected'),
    ('run013', 0, '29 passed'),
):
    receipt = read(integration / run_name / 'receipt.json')
    assert receipt['returncode'] == receipt['metadata']['native_returncode'] == code
    assert receipt['metadata']['policy'] == POLICY
    assert summary in (integration / run_name / 'stdout.txt').read_text()
index = read(integration / 'final_evidence_001/EVIDENCE_INDEX.json')
assert len(index) == 35
for artifact in index:
    path = ROOT / artifact['path']
    assert path.stat().st_size == artifact['size_bytes']
    assert sha(path) == artifact['sha256']
assert sha(ROOT / 'gene_annotation_episode/blast_vdb_function_calculators.py') == '31d88b0d724ced992c6ca69aab7161632ada3e24d91f2f264387b03d31ef749a'

specs = [
    ('BLAST-VDB-FUNCTION-CALCULATORS-083', calculator,
     ['ROOT_REVIEW_001.md', 'HANDOFF_001.md', 'run_012/receipt.json', 'run_012/stdout.txt',
      'example_run_004/receipt.json', 'NUMERICAL_EXAMPLES_001.md'],
     'Accepted numerical fields and deterministic VDB function calculations. The recorded component run passed180 tests;20 retained examples and347 later worker/form examples were reviewed. Historical source generations remain separately identified.'),
    ('BLAST-VDB-FUNCTION-EPISODE-083', integration,
     ['ROOT_REVIEW_001.md', 'HANDOFF_001.md', 'run012/receipt.json', 'run012/stdout.txt',
      'run013/receipt.json', 'run013/stdout.txt', 'run013/request.json',
      'final_evidence_001/EVIDENCE_INDEX.json', 'final_evidence_001/NUMERICAL_PROJECTIONS.json'],
     'Accepted declared synthetic selected-child, retained-worker and requested typed-return paths for both VDB programs, including authorized offline saved-sheet recalculation. Run012 remains429passed/18failed/5deselected; run013 passed all29 targeted repair checks including the18 prior failures. All35 indexed evidence artifacts were rechecked.'),
]
evidence = []
for ident, packet, names, summary in specs:
    item = dict(id=ident, kind='root_reviewed_numerical_grader_and_declared_episode_path',
        summary=summary,
        reports=[dict(path=str((packet / name).relative_to(ROOT)), sha256=sha(packet / name)) for name in names],
        qualification='Supplied synthetic outputs and controlled PBS integration. Authentic native-mode coverage and actual HPC execution remain unfinished. No final-current-whole-tree broad pass or full-goal completion is claimed.')
    assert not any(old['id'] == ident for old in status['verification_evidence'])
    status['verification_evidence'].append(item)
    evidence.append(item)

ids = {'A-L070-blastn_vdb-database', 'A-L070-tblastn_vdb-database'}
changes = []
for row in status['rows']:
    if row['id'] not in ids:
        continue
    before = deepcopy(row)
    row.update(overall='numerical_grader_implemented_declared_synthetic_episode_path_verified_live_and_extended_native_inputs_unfinished',
        deterministic_calculator='geometry_taxonomy_quality_population_and_candidate_function_components_implemented_separate_complete_census_adjustment_verified',
        production_result_binding='selected_child_bounded_worker_frozen_function_families_typed_returns_and_authorized_saved_sheet_recalculation_verified')
    row['numerical_verification'] += '_344_180_component_checks_and20_examples_347_11_numerical_projections_reviewed_scopes_overlap'
    row['integration_verification'] += '_347_actual_function_returns_and_saved_generation_verified_29_targeted_repairs_passed_old429pass18fail_broad_receipt_preserved'
    row['evidence_ids'] += [item['id'] for item in evidence]
    row['note'] += (' Update083: root accepted344 function calculations and347 declared synthetic selected-child/worker/typed-return integration. '
        'Both VDB rows enter the implemented-grader tally:108 to110. Unadjusted0.8/0.2 and supplied-census-adjusted0.5/0.5 reach actual forms; '
        'saved parameter changes preserve prior generations and use no acquisition/native rerun. The failed broad run is retained and all18 failures '
        'are covered by the29-pass repair run. Later shared RNA changes are not attributed to historical receipts. '
        'Authentic native formats and live HPC execution remain unfinished. U06 sequence-path/census association is separate from VDB.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert {item['id'] for item in changes} == ids

binding_changes = []
for binding in status['resource_bindings']:
    if binding['id'] not in {ident + '::hpc' for ident in ids}:
        continue
    before = deepcopy(binding)
    binding['production_result_binding'] = 'original_attempt_capture_numerical_worker_function_families_typed_returns_and_authorized_saved_calculation_verified'
    binding['integration_verification'] += '_347_function_and_saved_generation_paths_verified_with_declared_synthetic_inputs_live_execution_unverified'
    binding['evidence_ids'] += [item['id'] for item in evidence]
    binding_changes.append(dict(id=binding['id'], before=before, after=deepcopy(binding)))
assert len(binding_changes) == 2
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] not in ids)
assert all(a == b for a, b in zip(original['resource_bindings'], status['resource_bindings']) if a['id'] not in {i + '::hpc' for i in ids})

checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U02':
        item['status'] = 'complete'
        item['current_evidence'] = ('344 complete numerical calculation and347 declared synthetic episode paths accepted after full root review. '
            'Two VDB graders now count:110/308. Actual function returns and saved recalculation preserve measurements and old observations. '
            'The old failed broad receipt remains;29 targeted repairs pass, includingall18 failures. U03 authentic native/HPC work stays open.')
assert [(i['id'], i['original_item']) for i in checklist] == [(i['id'], i['original_item']) for i in previous['work_item_states']]
assert all(a == b for a, b in zip(previous['work_item_states'], checklist) if a['id'] != 'U02')
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-26', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, resource_binding_changes=binding_changes, added_evidence=evidence,
    numerical_grader_progress_tally=dict(before=108, after=110, added_row_ids=sorted(ids),
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=40, after=40), remaining_fixed_rows_outside_tally=198,
    completed_work=[item['summary'] for item in evidence], findings_requiring_repair=[], work_item_states=checklist,
    unfinished_work=[i['current_evidence'] for i in checklist if i['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.083.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=2, updated_resource_bindings=2,
    numerical_grader_progress_tally=110, remaining_fixed_rows_outside_tally=198,
    new_status_sha256=sha(STATUS))))
