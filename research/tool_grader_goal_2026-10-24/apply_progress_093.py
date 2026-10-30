"""Record completed protein components; retain the unfinished whole-tool count."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_093.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_092.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 112
assert status['verified_bound_local_tool_mode_rows'] == 42
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']
policy = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
evidence_paths = []
checks = [
    ('projections_2026-10-27_391', 'check007', 51, 'executed_source_pins_unchanged'),
    ('capture_2026-10-27_392', 'check001', 64, 'executed_source_pins_unchanged'),
    ('result_worker_2026-10-27_393', 'check004', 79, 'executed_snapshot_pins_unchanged'),
    ('shared_sources_2026-10-27_395', 'check002', 57, 'executed_source_pins_unchanged'),
]
for suffix, check, passes, pin_key in checks:
    packet = ROOT / ('verification/tool_graders_protein_structure_' + suffix)
    directory = packet / check
    receipt = read(directory / 'receipt.json')
    assert receipt['returncode'] == 0 and receipt['metadata']['policy'] == policy
    assert receipt[pin_key] is True
    assert f'{passes} passed' in (directory / 'stdout.txt').read_text()
    evidence_paths.extend(directory / name for name in ('receipt.json', 'stdout.txt'))
    evidence_paths.extend(p for p in packet.iterdir() if p.is_file() and p.suffix in ('.md', '.json'))
contracts = ROOT / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380'
evidence_paths.extend(contracts / name for name in (
    'RESULT_WORKER_CLARIFICATIONS_008.md', 'ROOT_CONTRACT_ADDENDUM_009.md'))
drift_receipt = read(ROOT / 'verification/tool_graders_protein_structure_shared_sources_2026-10-27_395/check002/receipt.json')
assert {x['before']['path'] for x in drift_receipt['checkout_source_drift']} == {
    'gene_annotation_episode/protein_structure_result_worker.py'}
item = dict(id='PROTEIN-RESULT-COMPONENTS-093',
    kind='component_verification_with_full_episode_path_unfinished',
    summary='Protein D391 selected-result projection tests passed51; D2a392 retained capture tests passed64; '
        'D2b393 original-result/saved-recalculation worker tests passed79. Root395 passed57 tests, '
        'including the existing52 execution tests plus5 same-original-file tests. The real native '
        'driver compared separate chains from one PDB and recovered the expected translation. '
        'These overlapping suites are component evidence, not a completed episode path. '
        'No tool tally increment is claimed.',
    reports=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in sorted(set(evidence_paths))],
    executed_snapshot_note='All four final executed snapshots remained unchanged. In395, only the '
        'unimported result-worker file changed live during393 work;393 independently verified its final version.',
    current_source_pins=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in [
        ROOT / 'gene_annotation_episode/protein_structure_result_views.py',
        ROOT / 'gene_annotation_episode/native_protein_structure_acquisition.py',
        ROOT / 'gene_annotation_episode/protein_structure_result_worker.py',
        ROOT / 'gene_annotation_episode/native_protein_structure_contracts.py']])
assert item['id'] not in {e['id'] for e in status['verification_evidence']}
status['verification_evidence'].append(item)
protein_id = 'B-L107-compare_protein_structures'
changes, binding_changes = [], []
for row in status['rows']:
    if row['id'] != protein_id:
        continue
    before = deepcopy(row)
    row.update(overall='scientific_execution_and_result_components_tested_full_path_unfinished',
        source_presence='A_B_C_D1_capture_and_result_worker_present_host_integration_unfinished',
        invocation_contract='C390_and_root395_same_file_selection_execution_tested_registration_unfinished',
        production_result_binding='projection_capture_and_worker_components_tested_host_and_receipt_wiring_unfinished',
        integration_verification='component_only_no_complete_receiving_episode_proof',
        live_resource_verification='real_local_workers_and_two_chain_same_PDB_native_execution_on_synthetic_inputs')
    row['evidence_ids'].append(item['id'])
    row['note'] += (' Update093: D391/392/393 component suites passed51/64/79. Root395 passed57 '
        'checks including all52 execution tests and5 same-original-file checks. Original native '
        'results and explicit saved recalculations remain separate; invalid diagnostic files do '
        'not grant numerical or saved-sheet use. Host preparation/publication, receipt authority, '
        'sequence operands, resource registration and message integration remain unfinished. '
        'This row stays outside112/308.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
for row in status['resource_bindings']:
    if row['id'] != protein_id + '::local':
        continue
    before = deepcopy(row)
    row.update(invocation_contract='C390_and_root395_native_execution_and_shared_file_roles_tested',
        production_result_binding='component_tests_passed_host_path_not_integrated',
        integration_verification='component_only_no_actual_resource_registry_and_receiving_episode_path')
    row['evidence_ids'].append(item['id'])
    binding_changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert len(changes) == len(binding_changes) == 1
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] != protein_id)
assert all(a == b for a, b in zip(original['resource_bindings'], status['resource_bindings']) if a['id'] != protein_id + '::local')
checklist = deepcopy(previous['work_item_states'])
for entry in checklist:
    if entry['id'] == 'U05':
        entry['current_evidence'] += (' Update093: protein projection/capture/result-worker suites '
            'passed51/64/79; root same-source repair passed57 including the existing52 execution '
            'checks. Host custody/publication/receipt/operand/shared/message wiring remains open. '
            '112/308,42 local bindings,196 remaining rows and eight historical receipt failures '
            'are unchanged. W05 and literature remain separate.')
assert [(x['id'], x['original_item'], x['status']) for x in checklist] == [
    (x['id'], x['original_item'], x['status']) for x in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = dict(schema='tool_grader_progress_update_v1', date='2026-10-27', author='root',
    recorded_at=datetime.now(timezone.utc).isoformat(), previous_status_sha256=before_sha,
    new_status_sha256=hashlib.sha256(raw).hexdigest(), scope_sha256_unchanged=scope_sha,
    scope_changes=[], changes=changes, resource_binding_changes=binding_changes, added_evidence=[item],
    numerical_grader_progress_tally=dict(before=112, after=112, added_row_ids=[],
        meaning=previous['numerical_grader_progress_tally']['meaning']),
    verified_bound_local_tool_mode_rows=dict(before=42, after=42), remaining_fixed_rows_outside_tally=196,
    completed_work=[item['summary']], findings_requiring_repair=[
        'Protein host preparation/publication, original received-prefix authority, normal sequence operands, resource registration and message integration remain unfinished.',
        'Complete protein receiving-episode verification remains unfinished; component checks do not establish that path.',
        'Eight historical receipt failures remain under U05; U03 native/HPC work and other fixed rows remain.'],
    work_item_states=checklist, unfinished_work=[x['current_evidence'] for x in checklist if x['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.093.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=1, updated_resource_bindings=1,
    numerical_grader_progress_tally=112, verified_bound_local_tool_mode_rows=42,
    remaining_fixed_rows_outside_tally=196, new_status_sha256=sha(STATUS))))
