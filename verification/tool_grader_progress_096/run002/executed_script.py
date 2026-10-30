"""Append verified local/registration/shared components; keep the fixed tool tally."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_096.json'

def read(path):
    return json.loads(path.read_bytes())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_095.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 112
assert status['verified_bound_local_tool_mode_rows'] == 42
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']
reports = []
for suffix, check, summary in [
        ('local_resource_2026-10-27_405', 'check001', '36 passed'),
        ('local_resource_2026-10-27_405', 'check002', '25 passed'),
        ('resource_registration_2026-10-27_408', 'check001', '66 passed'),
        ('shared_integration_2026-10-27_409', 'check003', '52 passed')]:
    packet = ROOT / ('verification/tool_graders_protein_structure_' + suffix)
    directory = packet / check
    receipt = read(directory / 'receipt.json')
    pin_key = 'source_pins_unchanged' if suffix == 'local_resource_2026-10-27_405' else 'executed_source_pins_unchanged'
    assert receipt['returncode'] == 0 and receipt[pin_key]
    assert receipt['metadata']['policy'] == {
        'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}
    assert summary in (directory / 'stdout.txt').read_text()
    reports.extend([directory / 'receipt.json', directory / 'stdout.txt'])
    reports.extend(path for path in packet.iterdir() if path.is_file() and path.suffix in ('.md', '.json'))
failed = ROOT / 'verification/tool_graders_protein_structure_shared_integration_2026-10-27_409/check002'
assert read(failed / 'receipt.json')['returncode'] == 1
assert '1 failed, 32 passed' in (failed / 'stdout.txt').read_text()
reports.extend([failed / 'receipt.json', failed / 'stdout.txt'])

summary = ('Local resource405 passed61 distinct checks with actual inspection, AGST extraction, both comparison modes '
    'and an actual failed input-digest attempt followed by an explicit separate retry. Registration408 passed66 '
    'checks using actual406/407/397 constructors and saved factory reconstruction. Shared integration409 passed52 '
    'checks after fixing its runtime-handle resolver regression. Full native receiving-episode proof and message '
    'integration remain unfinished. No tool-count increment;112/308 remains.')
item = {'id': 'PROTEIN-LOCAL-REGISTRATION-SHARED-096',
    'kind': 'component_verification_with_full_episode_path_unfinished', 'summary': summary,
    'qualification': '405 uses actual native operations on synthetic engineering structures.408 tests declarations '
        'and reconstruction, not scientific execution.409 uses real host/receipt/return classes for pending and '
        'denied metadata paths; it does not establish successful complete protein result delivery. Its check002 '
        'retains32 passes and one regression introduced by root: Store lookup preceded durable runtime-handle '
        'resolution. The correction preserves the existing execution/execution_handle namespaces and check003 '
        'passes all52 cases.406/407 focused host verification and410 full Workflow work are still in progress. '
        'Existing401 and older historical failures are neither removed nor counted as passing.',
    'reports': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted(set(reports))],
    'snapshot_note': 'Each cited executed snapshot is immutable and unchanged. Concurrent checkout drift is '
        'recorded separately. Counts overlap across component/regression runs and are not a global test total.'}
assert item['id'] not in {row['id'] for row in status['verification_evidence']}
status['verification_evidence'].append(item)
protein_id = 'B-L107-compare_protein_structures'
changes, binding_changes = [], []
for row in status['rows']:
    if row['id'] != protein_id:
        continue
    before = deepcopy(row)
    row.update(overall='local_registration_and_shared_components_tested_full_result_path_unverified',
        source_presence='local_resource_registration_shared_hooks_and_result_host_present',
        production_result_binding='shared_dispatch_and_return_hooks_tested_successful_full_path_unverified',
        integration_verification='components_verified_complete_workflow_and_prompt_integration_open')
    row['evidence_ids'].append(item['id'])
    row['note'] += (' Update096:405 local resource61,408 registration66 and409 shared routing52 verified. '
        '409 fixed and retained its introduced runtime-handle resolver regression.406/407 real host/receipt '
        'verification and410 full Workflow communication are in progress. Protein result information/prompt '
        'presentation remains open. No complete tool or binding added.')
    changes.append({'id': row['id'], 'before': before, 'after': deepcopy(row)})
for row in status['resource_bindings']:
    if row['id'] != protein_id + '::local':
        continue
    before = deepcopy(row)
    row.update(production_result_binding='local_resource_registration_and_shared_hooks_tested_full_delivery_unverified',
        integration_verification='actual_resource_and_shared_boundaries_verified_full_workflow_open')
    row['evidence_ids'].append(item['id'])
    binding_changes.append({'id': row['id'], 'before': before, 'after': deepcopy(row)})
assert len(changes) == len(binding_changes) == 1
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] != protein_id)
assert all(a == b for a, b in zip(original['resource_bindings'], status['resource_bindings']) if a['id'] != protein_id + '::local')
checklist = deepcopy(previous['work_item_states'])
for row in checklist:
    if row['id'] == 'U05':
        row['current_evidence'] += (' Update096 records405/408/409 verified components.406/407 result-host '
            'verification,410 full selected-tool Workflow and protein result/prompt information remain open. '
            '409 introduced then corrected a runtime-handle resolver regression; the failed run is retained. '
            'The112/308 tally,42 local bindings,196 remaining rows and all prior historical failures remain unchanged.')
assert [(x['id'], x['original_item'], x['status']) for x in checklist] == [
    (x['id'], x['original_item'], x['status']) for x in previous['work_item_states']]
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-27', 'author': 'root',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'previous_status_sha256': before_sha,
    'new_status_sha256': hashlib.sha256(raw).hexdigest(), 'scope_sha256_unchanged': scope_sha,
    'scope_changes': [], 'changes': changes, 'resource_binding_changes': binding_changes, 'added_evidence': [item],
    'numerical_grader_progress_tally': {'before': 112, 'after': 112, 'added_row_ids': [],
        'meaning': previous['numerical_grader_progress_tally']['meaning']},
    'verified_bound_local_tool_mode_rows': {'before': 42, 'after': 42}, 'remaining_fixed_rows_outside_tally': 196,
    'completed_work': [summary], 'findings_requiring_repair': [
        '406/407 original result-host proof and410 full receiving-episode path remain unverified.',
        'Protein result information and decision-text presentation remain unfinished; no complete tool claim.',
        'Prior401 commission/policy/timing fixture failures and eight historical U05 failures remain.',
        'U03 native/HPC and all other fixed unfinished rows remain.'],
    'work_item_states': checklist, 'unfinished_work': [x['current_evidence'] for x in checklist if x['status'] != 'complete'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': status['complete_scientific_tools_claimed']}
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as handle:
    json.dump(update, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.096.writing')
with temporary.open('xb') as handle:
    handle.write(raw)
temporary.replace(STATUS)
print(json.dumps({'updated_tool_rows': 1, 'updated_resource_bindings': 1, 'grader_tally': 112,
    'verified_local_bindings': 42, 'remaining_rows': 196, 'new_status_sha256': sha(STATUS)}))
