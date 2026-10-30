"""Record completed SAMstat episode verification and preserved harness qualifications."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
P = ROOT / 'verification/tool_graders_fastqutils_samstat_episode_2026-10-26_218'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '23109c3a2f3417cdea971cb0f7ee1f6f993678faafeae80ab8c63dc83a11d364'
assert not (HERE / 'PROGRESS_UPDATE_050.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope, scope_hash = read(scope_path), sha(scope_path)
handoff = read(P / 'VERIFICATION_HANDOFF_001.json')
references = []


def verify_references(value):
    if type(value) is dict:
        if {'path', 'sha256'} <= value.keys():
            path = Path(value['path'])
            assert sha(path) == value['sha256']
            references.append(path)
        for child in value.values():
            verify_references(child)
    elif type(value) is list:
        for child in value:
            verify_references(child)


verify_references(handoff)
assert len(references) == 33
manifest = read(Path(handoff['original216_manifest']))
assert len(manifest) == 1176
for name, expected in manifest.items():
    assert sha(Path(handoff['source_candidate']) / name) == expected
assert handoff['host_manual']['cases_passed'] == 2
workflow = handoff['shared_Workflow']
assert workflow['actual_loop_completed'] and workflow['actual_root_admission_succeeded']
assert workflow['completed_own_actions'] == workflow['observations'] == 14
replay = workflow['saved_replay']
assert replay['passed'] and replay['root_inward_contract_verified']
assert not any(replay[k] for k in ('forbidden_attempts', 'new_acquisition', 'new_actions', 'new_observations'))
assert replay['forged_value_rejections'] == 3
completed = read(Path(workflow['completed_before_replay_assertion']['path']))
counts = completed['counts']
assert sum(row['actions'] for row in counts) == sum(row['observations'] for row in counts) == 14
for row in counts:
    assert row['actions'] == row['observations']
    if row['role'] in {'launch', 'launch_api', 'results'}:
        assert row['marginal_gains'][-1] == {'launch': 2, 'launch_api': 2, 'results': 3}[row['role']]
        assert row['expected_next_gain'][-1]['value'] == 0
        assert row['expected_next_gain'][-1]['lower'] == row['expected_next_gain'][-1]['upper'] == 0
saved = read(Path(workflow['saved_reconstruction_and_rejections']['path']))
assert saved['original_actions_sha256'] == saved['final_actions_sha256']
assert not saved['forbidden_attempts'] and len(saved['rejections']) == 3
assert all(row['code'] == 'bvbrc_fastqutils_return_returned_facts_conflict' for row in saved['rejections'])
drift = read(P / 'REPOSITORY_CONFIG_DRIFT_001.json')
old = tomllib.loads(Path(drift['old_source']).read_text())
new = tomllib.loads(Path(drift['current_source']).read_text())
assert sha(Path(drift['old_source'])) == drift['old_sha256']
assert sha(Path(drift['current_source'])) == drift['current_sha256']
before_data = old['tool']['setuptools']['package-data'].pop('gene_annotation_episode')
after_data = new['tool']['setuptools']['package-data'].pop('gene_annotation_episode')
assert old == new
assert after_data == before_data + ['bvbrc_fastqutils_schemas.json',
    'bvbrc_fastqutils_legacy_v2_schemas.json', 'bvbrc_fastqutils_legacy_cutadapt_schemas.json']
assert read(P / 'workflow_replay_001/receipt.json')['exit_code'] == 0

names = ['VERIFICATION_HANDOFF_001.json', 'FINAL_EVIDENCE_REPORT_001.md',
    'NUMERICAL_AND_CUSTODY_001.json', 'FINAL_IMMUTABILITY_001.json',
    'REPOSITORY_CONFIG_DRIFT_001.json', 'SAVED_REPLAY_REPAIR_001.json',
    'host_run_001/receipt.json', 'workflow_run_001/receipt.json',
    'workflow_replay_001/receipt.json', 'test_samstat_workflow.py', 'test_workflow_saved_replay.py']
evidence = dict(id='FASTQUTILS-SAMSTAT-HOST-WORKFLOW-050',
    kind='retained_native_current_legacy_host_and_actual_current_shared_Workflow_verified',
    summary='Both current and legacy SAMstat host cases passed through actual selected AppService '
        'and Workspace custody, native parsing/calculation and two typed receiving boundaries. '
        'Current values 9/10 and 4/10 and legacy values 10/11 and 5/11 retained their populations '
        'and qualifications. The current-format actual Workflow completed 14 actions and 14 '
        'observations; launch/API/results retained final actual gains 2/2/3 while future expectations '
        'became exact zero. Saved-state-only replay passed the original inward root schema with '
        'all parser/calculator/transport/subprocess entrypoints disabled, no new work, and forged900 '
        'rejected by owner and both receivers. Root read the full Workflow/replay tests and verified '
        'all33 handoff references and1176 candidate hashes.',
    qualification='Original host runner exit1 came from packaging-only repository configuration '
        'drift. Root verified the only TOML change added three package-data files, with all other '
        'configuration unchanged. Original Workflow completed, then its test failed by requesting '
        'a nonexistent outward root contract; the separate replay verified saved state against '
        'the actual admitted child schema. Both terminal failures remain preserved, including '
        'volatile process-stat audit observation. No acquisition or Workflow was rerun. Choices, '
        'service transport, scientific credit and scientific continuation were controlled; '
        'practical controller and runtime were actual. No live BV-BRC producer/service, deployed '
        'SAMstat version, live model, HPC or W05 verification is claimed.',
    reports=[dict(path=str((P / name).relative_to(ROOT)), sha256=sha(P / name)) for name in names])
assert evidence['id'] not in {row['id'] for row in work['verification_evidence']}
work['verification_evidence'].append(evidence)
for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        if row['id'].split('::')[0] != 'C-L209-FastqUtils':
            continue
        row['evidence_ids'].append(evidence['id'])
        row['integration_verification'] = 'actual_baseline18actions18observations_and_current_SAMstat14actions14observations_verified_native_host_receivers_and_saved_replay_passed'
        if group == 'rows':
            row['overall'] = 'grader_implemented_applied_component_package_host_and_shared_Workflow_verified_live_service_unfinished'
            row['note'] += ' Update050: ' + evidence['summary'] + ' ' + evidence['qualification']

changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes.extend(dict(group=group, id=r['id'], before=previous[r['id']], after=deepcopy(r))
        for r in work[group] if r != previous[r['id']])
assert len(changes) == 2 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_hash
updated = (json.dumps(work, indent=2) + '\n').encode()
record = dict(schema='tool_grader_progress_update_v1', date='2026-10-26',
    recorded_at=datetime.now(timezone.utc).isoformat(), author='root',
    previous_status_sha256=hashlib.sha256(raw).hexdigest(), new_status_sha256=hashlib.sha256(updated).hexdigest(),
    scope_sha256_unchanged=scope_hash, scope_changes=False, changes=changes, added_evidence=[evidence],
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
with (HERE / 'PROGRESS_UPDATE_050.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps(dict(checkpoint=50, changed_rows_and_bindings=len(changes),
    status_sha256=record['new_status_sha256'], current_SAMstat_actions_and_observations=14)))
