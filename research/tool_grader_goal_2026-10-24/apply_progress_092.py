"""Record verified protein components without counting an unfinished tool path."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_092.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_091.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 112
assert status['verified_bound_local_tool_mode_rows'] == 42
authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
assert sha(authority) == status['authority_sha256']
contracts = ROOT / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380'
b = ROOT / 'verification/tool_graders_protein_structure_calculations_2026-10-27_389'
c = ROOT / 'verification/tool_graders_protein_structure_execution_2026-10-27_390'
policy = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
paths = []
for packet, check, passes in [(b, 'check007', 58), (b, 'check008', 23), (c, 'check007', 52)]:
    directory = packet / check
    receipt = read(directory / 'receipt.json')
    assert receipt['returncode'] == 0 and receipt['metadata']['policy'] == policy
    assert receipt['source_pins_unchanged'] is True
    assert f'{passes} passed' in (directory / 'stdout.txt').read_text()
    assert read(directory / 'source_pins_before.json') == read(directory / 'source_pins_after.json')
    paths += [directory / name for name in ('receipt.json', 'stdout.txt', 'source_pins_before.json')]
assert read(b / 'check006/receipt.json')['returncode'] == 1
assert '1 failed' in (b / 'check006/stdout.txt').read_text()
paths += [b / name for name in ('HANDOFF_001.md', 'VERIFICATION_001.json', 'SOURCE_PINS_001.json',
    'check006/receipt.json', 'check006/stdout.txt', 'examples/held_out_saved_sheet.json',
    'examples/held_out_components.json')]
paths += [c / name for name in ('IMPLEMENTATION_AND_VERIFICATION_001.md',
    'HANDOFF_SOURCE_PINS_001.json', 'FILLED_NATIVE_EXAMPLES_001.json')]
paths += [contracts / name for name in ('ROOT_CONTRACT_ADDENDUM_004.md',
    'RESULT_CAPTURE_CONTRACT_005.md', 'ROOT_CONTRACT_ADDENDUM_006.md',
    'RESULT_WORKER_CONTRACT_007.md')]

# Keep the tested source sets distinct from the later shared format expansion.
tested_sources = {row['path']: row for row in read(b / 'SOURCE_PINS_001.json')['source_rows']}
tested_sources.update({row['path']: row for row in read(c / 'HANDOFF_SOURCE_PINS_001.json')})
drift = [dict(path=path, tested_sha256=row['sha256'], current_sha256=sha(ROOT / path))
    for path, row in sorted(tested_sources.items()) if sha(ROOT / path) != row['sha256']]
assert {row['path'] for row in drift} <= {'gene_annotation_episode/protein_structure_contracts.py'}
item = dict(id='PROTEIN-CALCULATION-EXECUTION-COMPONENTS-092',
    kind='component_verification_with_full_episode_path_unfinished',
    summary='B389 full suite passed58 checks and its later C-validator dependency replay passed23. '
        'C390 passed52 local execution/schema checks. Their original bounded receipts and stable '
        'executed pins are retained; these overlapping suites are not added as unique tests. '
        'Root fixed A explicit-map handling of a known zero-length sequence using a retained failing '
        'counterexample. The later A closed FileFormat expansion admits seven actual C capture formats; '
        'that post-test dependency change is explicit. D391 projections remain under final verification; '
        'fresh392 capture and393 result-worker coding use exact005/007 contracts. '
        'No complete protein path, prompt integration or tally increment is claimed.',
    reports=[dict(path=str(path.relative_to(ROOT)), sha256=sha(path)) for path in paths],
    post_verification_dependency_changes=drift)
assert item['id'] not in {e['id'] for e in status['verification_evidence']}
status['verification_evidence'].append(item)
protein_id = 'B-L107-compare_protein_structures'
changes, binding_changes = [], []
for row in status['rows']:
    if row['id'] != protein_id:
        continue
    before = deepcopy(row)
    row.update(overall='calculation_and_local_execution_components_tested_full_path_unfinished',
        source_presence='A_B_C_sources_present_D_projection_capture_result_worker_in_progress',
        tool_information='C390_local_information_and_contract_component_tests_passed',
        invocation_contract='C390_local_reservation_worker_replay_tested_registration_unfinished',
        numerical_sheet='B389_58_full_checks_23_dependency_replay_component_review_pending',
        native_parser='A386_and_B389_components_tested_root_assembly_review_pending',
        metadata_extractor='A386_component_tested_root_assembly_review_pending',
        deterministic_calculator='B389_numerical_and_saved_recalculation_components_tested',
        production_result_binding='D1_D2_and_shared_integration_unfinished',
        numerical_verification='B389_hand_checked_held_out_missing_nonunique_and_confidence_cases',
        integration_verification='component_only_no_complete_receiving_episode_proof',
        live_resource_verification='C390_real_local_workers_on_synthetic_native_format_inputs')
    row['evidence_ids'].append(item['id'])
    row['note'] += (' Update092: B58 tests plus23 dependency replay and C52 local tests are retained '
        'component evidence. The known-zero map repair is verified; the subsequent seven-format A '
        'extension is a recorded dependency change. D391 projection verification,392 capture,393 '
        'result worker and root custody/shared/prompt integration remain unfinished. This row is '
        'still outside112/308; no complete protein capability is claimed.')
    changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
for row in status['resource_bindings']:
    if row['id'] != protein_id + '::local':
        continue
    before = deepcopy(row)
    row.update(invocation_contract='C390_local_native_contract_and_lifecycle_component_tested',
        production_result_binding='not_integrated',
        integration_verification='C390_component_tests_only_no_actual_resource_registry_path',
        live_resource_verification='C390_real_local_workers_and_durable_native_lifecycle_on_synthetic_inputs',
        prerequisites_present='C390_selected_python_numpy_biopython_and_source_pins_exercised',
        native_format_observed='C390_actual_inventory_extraction_comparison_native_JSON_and_sealed_bundles')
    row['evidence_ids'].append(item['id'])
    binding_changes.append(dict(id=row['id'], before=before, after=deepcopy(row)))
assert len(changes) == len(binding_changes) == 1
assert all(a == z for a, z in zip(original['rows'], status['rows']) if a['id'] != protein_id)
assert all(a == z for a, z in zip(original['resource_bindings'], status['resource_bindings'])
    if a['id'] != protein_id + '::local')
checklist = deepcopy(previous['work_item_states'])
for entry in checklist:
    if entry['id'] == 'U05':
        entry['current_evidence'] += (' Update092: protein B/C numerical and local-execution '
            'component suites passed58/23 and52 respectively. Root repaired the known-zero map '
            'boundary; the subsequent capture-format extension is recorded. D391/392/393 and '
            'full shared receiving-episode wiring remain in progress.112/308 and42 accepted local '
            'bindings are unchanged; all196 remaining fixed rows and eight historical receipt '
            'failures stay open. W05/literature remain separate.')
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
        'Protein result custody, original received-prefix authority, projections, shared registration and all message boundaries remain unfinished.',
        'The A capture-format extension postdates B/C final tests; its current integration verification remains explicit work.',
        'Eight historical receipt failures remain under U05; U03 native/HPC work and all other fixed rows remain.'],
    work_item_states=checklist, unfinished_work=[x['current_evidence'] for x in checklist if x['status'] != 'complete'],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False,
    complete_scientific_tools_claimed=status['complete_scientific_tools_claimed'])
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.092.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps(dict(updated_tool_rows=1, updated_resource_bindings=1,
    numerical_grader_progress_tally=112, verified_bound_local_tool_mode_rows=42,
    remaining_fixed_rows_outside_tally=196, new_status_sha256=sha(STATUS))))
