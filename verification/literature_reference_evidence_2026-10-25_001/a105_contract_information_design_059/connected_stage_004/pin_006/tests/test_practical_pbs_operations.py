"""Exercise the real remote worker locally against explicit fake PBS commands."""
import ast
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode import practical_pbs_operations as pbs
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.execution_inventory import canonical_bytes, make_catalog


REAL_RUN = subprocess.run


def assignment(workspace, *, argv=None, environment=None):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'job-1',
        'resource_kind': 'hpc', 'workspace': str(workspace), 'endpoint': 'completed_job_outputs',
        'requested_job': {'argv': argv or ['/bin/true'], 'environment': environment or {}},
        'progress_requirements': [{'key': 'outputs', 'credit': 1, 'predicate': {
            'kind': 'requested_job_outputs', 'output_paths': [str(workspace/'result.txt')]}}],
        'completion_keys': ['outputs'], 'initial_context': {
            'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}}


def state(value):
    return SimpleNamespace(assignment=value, run_id='run-1', episode_id='episode-1',
        context=lambda: deepcopy(value['initial_context']))


@pytest.fixture
def remote(tmp_path, monkeypatch):
    workspace = tmp_path/'project'
    workspace.mkdir()
    commands = tmp_path/'pbs-bin'
    commands.mkdir()
    database = tmp_path/'fake-pbs'
    database.mkdir()
    qsub = '''import json,os,pathlib,subprocess,sys
root=pathlib.Path(os.environ['FAKE_PBS_ROOT']);args=sys.argv[1:]
count=root/'submissions';count.write_text(str(int(count.read_text())+1) if count.exists() else '1')
job_id=str(12344+int(count.read_text()))+'.aurora'
def arg(key):return args[args.index(key)+1]
record={'Job_Name':arg('-N'),'Account_Name':arg('-A'),'queue':arg('-q'),'Priority':812,
    'base_score':23.5,'project_priority':61,
    'Variable_List':{'EPISODE_SUBMISSION_TOKEN':arg('-v').split('=',1)[1]},
    'job_state':'Q','qtime':100,'ctime':99,'Resource_List':{'walltime':'00:01:00'}}
(root/'job.json').write_text(json.dumps(record));(root/'qsub-argv.json').write_text(json.dumps(args))
(root/(job_id+'.json')).write_text(json.dumps(record))
if os.environ.get('FAKE_PBS_EXECUTE')=='1':
    env=dict(os.environ,PBS_JOBID=job_id)
    with open(arg('-o'),'wb') as out,open(arg('-e'),'wb') as err:
        subprocess.run(['/bin/bash',args[-1]],env=env,stdout=out,stderr=err)
print('accepted without a job identifier' if os.environ.get('FAKE_PBS_BAD_REPLY')=='1' else job_id)
if os.environ.get('FAKE_PBS_NONZERO_AFTER_ACCEPT')=='1':
    print('submission client lost the server reply',file=sys.stderr);sys.exit(1)
'''
    qstat = '''import json,os,pathlib,sys
root=pathlib.Path(os.environ['FAKE_PBS_ROOT']);record=json.loads((root/(sys.argv[-1]+'.json')).read_text())
if (root/'status-unavailable').exists():sys.exit(153)
if (root/'finished').exists():record.update(job_state='F',Exit_status=0,stime=110,obittime=120)
if (root/'wrong-token').exists():record['Variable_List']['EPISODE_SUBMISSION_TOKEN']='wrong'
print(json.dumps({'Jobs':{sys.argv[-1]:record}}))
'''
    qselect = '''import json,os,pathlib,sys
root=pathlib.Path(os.environ['FAKE_PBS_ROOT'])
if (root/'selection-enabled').exists():
    for path in sorted(root.glob('*.aurora.json')):
        if json.loads(path.read_text())['Job_Name']==sys.argv[-1]:print(path.name[:-5])
'''
    for name, body in [('qsub', qsub), ('qstat', qstat), ('qselect', qselect)]:
        path = commands/name
        path.write_text('#!'+sys.executable+'\n'+body)
        path.chmod(0o700)
    calls = []

    def ssh_run(argv, **kwargs):
        assert argv[:-1] == ['mock-ssh', 'explicit-bastion', 'explicit-aurora']
        calls.append((argv, json.loads(kwargs['input'])))
        env = dict(os.environ, PATH=str(commands)+os.pathsep+os.environ['PATH'],
                   FAKE_PBS_ROOT=str(database))
        return REAL_RUN([sys.executable, '-B', '-c', pbs._REMOTE_WORKER], env=env, **kwargs)

    monkeypatch.setattr(pbs.subprocess, 'run', ssh_run)
    configuration = {'kind': 'pbs_ssh', 'workspace': str(workspace),
        'ssh_argv': ['mock-ssh', 'explicit-bastion', 'explicit-aurora'],
        'python_executable': sys.executable, 'account': 'EpiCalib'}
    return SimpleNamespace(workspace=workspace, database=database, calls=calls,
        operations=pbs.PBSPracticalOperations(configuration), configuration=configuration)


def execute(remote, value, tool, arguments=None, key='operation-1'):
    return asyncio.run(remote.operations.execute(state(value), tool, arguments or {}, key))


def test_initial_inspection_does_not_submit_or_create_operation_directories(remote):
    value = assignment(remote.workspace)
    outcome = remote.operations.initial_outcome(value)
    assert outcome['facts']['paths'] == [{'path': str(remote.workspace/'result.txt'),
        'exists': False, 'object_type': 'missing', 'sha256': None}]
    assert 'requested_job' not in outcome['facts']
    assert list(remote.workspace.iterdir()) == []
    assert not (remote.database/'submissions').exists()


def test_actual_command_nonzero_outcome_is_retained_without_reexecution(remote):
    value = assignment(remote.workspace)
    counter = remote.workspace/'counter'
    arguments = {'argv': ['/bin/sh', '-c', 'echo x >> '+str(counter)+'; exit 7'], 'environment': {}}
    first, after = execute(remote, value, 'practical.command.run', arguments)
    second, _ = execute(remote, value, 'practical.command.run', arguments)
    assert first == second
    assert after is None
    assert first['facts']['command']['returncode'] == 7
    assert counter.read_text() == 'x\n'
    assert first['native_outcome']['stdout']['path'].startswith(str(remote.workspace))


def test_reusing_operation_identity_with_other_command_rejects(remote):
    value = assignment(remote.workspace)
    execute(remote, value, 'practical.command.run', {'argv': ['/bin/true'], 'environment': {}})
    with pytest.raises(ValueError, match='practical_pbs_operation_identity_conflict'):
        execute(remote, value, 'practical.command.run', {'argv': ['/bin/false'], 'environment': {}})


def test_lost_reply_recovers_original_durable_command_result(remote, monkeypatch):
    value = assignment(remote.workspace)
    arguments = {'argv': ['/bin/echo', 'actual outcome'], 'environment': {}}
    original_invoke = remote.operations._invoke
    captured = []

    def lose_reply(request):
        captured.append(original_invoke(request))
        raise ConnectionError('lost after remote execution')

    monkeypatch.setattr(remote.operations, '_invoke', lose_reply)
    with pytest.raises(ConnectionError):
        execute(remote, value, 'practical.command.run', arguments)
    monkeypatch.setattr(remote.operations, '_invoke', original_invoke)
    assert execute(remote, value, 'practical.command.run', arguments) == captured[0]


def test_pending_uncertain_command_is_not_reexecuted(remote):
    value = assignment(remote.workspace)
    execute(remote, value, 'practical.command.run', {'argv': ['/bin/true'], 'environment': {}})
    result = next(remote.workspace.rglob('result.json'))
    result.unlink()  # Simulate interruption after side effect and before receipt publication.
    next(remote.workspace.rglob('command-result.json')).unlink()
    with pytest.raises(ValueError, match='practical_pbs_command_outcome_unknown_no_reexecution'):
        execute(remote, value, 'practical.command.run', {'argv': ['/bin/true'], 'environment': {}})


def test_pbs_submission_uses_account_and_project_output_and_preserves_original_id(remote):
    value = assignment(remote.workspace)
    arguments = {'queue': 'explicit-queue', 'resources': ['select=1:ncpus=4', 'walltime=00:01:00', 'filesystems=flare']}
    first, _ = execute(remote, value, 'practical.job.start', arguments)
    second, _ = execute(remote, value, 'practical.job.start', arguments)
    assert first == second
    job = first['facts']['requested_job']
    assert job['execution_id'] == '12345.aurora'
    assert job['status'] == 'submitted'
    assert job['handoff']['monitor_operation'] == 'practical.job.status'
    argv = json.loads((remote.database/'qsub-argv.json').read_text())
    assert argv[argv.index('-A')+1] == 'EpiCalib'
    assert argv[argv.index('-q')+1] == 'explicit-queue'
    for option in ('-o', '-e'):
        assert Path(argv[argv.index(option)+1]).is_relative_to(remote.workspace)
    assert Path(argv[-1]).is_relative_to(remote.workspace)
    assert (remote.database/'submissions').read_text() == '1'


def test_uncertain_qsub_never_resubmits_and_later_status_can_recover_original_id(remote):
    value = assignment(remote.workspace, environment={'FAKE_PBS_BAD_REPLY': '1'})
    arguments = {'queue': 'test', 'resources': ['select=1', 'walltime=00:01:00']}
    first, _ = execute(remote, value, 'practical.job.start', arguments)
    assert first['facts']['requested_job']['status'] == 'unknown'
    assert first['facts']['requested_job']['handoff'] is None
    uncertain, _ = execute(remote, value, 'practical.job.status', key='status-1')
    assert uncertain['facts']['requested_job']['status'] == 'unknown'
    assert (remote.database/'submissions').read_text() == '1'
    (remote.database/'selection-enabled').touch()
    recovered, _ = execute(remote, value, 'practical.job.status', key='status-2')
    assert recovered['facts']['requested_job']['execution_id'] == '12345.aurora'
    assert recovered['facts']['requested_job']['status'] == 'submitted'
    assert (remote.database/'submissions').read_text() == '1'


def test_new_submission_choice_does_not_replace_existing_job(remote):
    value = assignment(remote.workspace)
    execute(remote, value, 'practical.job.start', {'queue': 'first', 'resources': ['select=1']})
    with pytest.raises(ValueError, match='practical_pbs_submission_identity_conflict'):
        execute(remote, value, 'practical.job.start', {'queue': 'other', 'resources': ['select=2']}, key='other')
    assert (remote.database/'submissions').read_text() == '1'


def test_status_exposes_queue_priority_and_original_timing_fields(remote):
    value = assignment(remote.workspace)
    execute(remote, value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    observed, _ = execute(remote, value, 'practical.job.status', key='status')
    fields = observed['native_outcome']['pbs_fields']
    assert fields['Priority'] == 812
    assert fields['base_score'] == 23.5
    assert fields['project_priority'] == 61
    assert fields['queue'] == 'test'
    assert fields['qtime'] == 100
    assert fields['ctime'] == 99
    assert 'estimated_duration_seconds' not in fields


def test_past_submission_does_not_invent_current_state_when_qstat_is_unavailable(remote):
    value = assignment(remote.workspace)
    execute(remote, value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    (remote.database/'status-unavailable').touch()
    observed, _ = execute(remote, value, 'practical.job.status', key='status')
    assert observed['facts']['requested_job']['execution_id'] == '12345.aurora'
    assert observed['facts']['requested_job']['status'] == 'unknown'
    assert observed['native_outcome']['status_query_returncode'] == 153
    assert observed['native_outcome']['pbs_fields'] == {}


def test_only_explicit_digest_predicates_hash_file_bytes(remote):
    output = remote.workspace/'result.txt'
    output.write_text('existing result')
    selected = remote.workspace/'specific-small-manifest.json'
    selected.write_text('actual manifest')
    value = assignment(remote.workspace)
    value['progress_requirements'].append({'key': 'manifest', 'credit': 0,
        'predicate': {'kind': 'file_sha256', 'path': str(selected),
            'sha256': hashlib.sha256(selected.read_bytes()).hexdigest()}})
    paths = {item['path']: item for item in remote.operations.initial_outcome(value)['facts']['paths']}
    assert paths[str(output)]['sha256'] is None
    assert paths[str(selected)]['sha256'] == hashlib.sha256(selected.read_bytes()).hexdigest()


def test_completed_actual_test_command_and_outputs_validate_original_requested_job(remote):
    output = remote.workspace/'result.txt'
    value = assignment(remote.workspace, argv=['/bin/sh', '-c', 'printf actual > '+str(output)],
        environment={'FAKE_PBS_EXECUTE': '1'})
    outcome, _ = execute(remote, value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    assert outcome['facts']['requested_job']['status'] == 'completed'
    assert outcome['facts']['requested_job']['returncode'] == 0
    assert output.read_text() == 'actual'
    assert outcome['native_outcome']['exit_receipt']['duration_seconds'] >= 0
    validations = assess_validations(value, outcome, value['initial_context'], tool_name='practical.job.start')
    assert validations[0]['satisfied']


def test_wrong_pbs_job_token_is_rejected(remote):
    value = assignment(remote.workspace)
    execute(remote, value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    (remote.database/'wrong-token').touch()
    with pytest.raises(ValueError, match='practical_pbs_job_identity_conflict'):
        execute(remote, value, 'practical.job.status', key='status')


def test_project_paths_are_checked_on_remote_side_and_context_is_explicit(remote):
    value = assignment(remote.workspace)
    with pytest.raises(ValueError, match='practical_write_outside_workspace'):
        execute(remote, value, 'practical.file.write', {'path': '/home/chian/forbidden', 'text': 'never'})
    directory = remote.workspace/'work'
    execute(remote, value, 'practical.directory.create', {'path': str(directory)}, key='mkdir')
    _, context = execute(remote, value, 'practical.context.set',
        {'cwd': str(directory), 'environment': {'EXPLICIT': 'value'}}, key='context')
    assert context == {'revision': 1, 'cwd': str(directory), 'environment': {'EXPLICIT': 'value'}}


def test_reply_identity_validation_and_explicit_configuration(remote, monkeypatch):
    invalid = deepcopy(remote.configuration)
    del invalid['ssh_argv']
    with pytest.raises(ValueError, match='explicit_pbs_practical_configuration_required'):
        pbs.PBSPracticalOperations(invalid)

    def false_reply(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, json.dumps({
            'version': 'practical_pbs_reply_v1', 'request_sha256': '0'*64,
            'result': {'outcome': {'facts': {}}, 'context_after': None}}).encode(), b'')

    monkeypatch.setattr(pbs.subprocess, 'run', false_reply)
    with pytest.raises(ValueError, match='practical_pbs_reply_identity_conflict'):
        remote.operations.initial_outcome(assignment(remote.workspace))


def test_remote_workers_use_python36_compatible_syntax():
    ast.parse(pbs._REMOTE_WORKER, feature_version=(3, 6))
    ast.parse(pbs._JOB_DRIVER, feature_version=(3, 6))


def test_explicit_inventory_read_returns_exact_bytes_without_remote_write(remote):
    path = remote.workspace/'catalog.json'
    raw = b'{"actual":"bytes preserved"}\n'
    path.write_bytes(raw)
    assert asyncio.run(remote.operations.read_inventory(str(path))) == raw
    assert list(remote.workspace.iterdir()) == [path]


def test_selected_inventory_refresh_retains_original_catalog_on_replay(remote):
    value = assignment(remote.workspace)
    path = remote.workspace/'catalog.json'
    catalog = make_catalog(resource_id='aurora', workspace=str(remote.workspace), components=[])
    path.write_bytes(canonical_bytes(catalog))
    first, _ = execute(remote, value, 'practical.inventory.refresh', {'path': str(path)})
    assert first['inventory_catalog'] == catalog
    changed = dict(catalog, resource_id='changed')
    path.write_bytes(canonical_bytes(changed))
    replay, _ = execute(remote, value, 'practical.inventory.refresh', {'path': str(path)})
    assert replay['inventory_catalog'] == catalog


def test_inventory_read_rejects_home_and_symlink_escape(remote, tmp_path):
    with pytest.raises(ValueError, match='practical_inventory_path_outside_workspace'):
        asyncio.run(remote.operations.read_inventory('/home/chian/catalog.json'))
    target = tmp_path/'outside-catalog.json'
    target.write_text('{}')
    link = remote.workspace/'escape.json'
    link.symlink_to(target)
    with pytest.raises(ValueError, match='practical_write_outside_workspace'):
        asyncio.run(remote.operations.read_inventory(str(link)))


def test_command_receipt_recovers_after_final_publication_interruption(remote):
    value = assignment(remote.workspace)
    counter = remote.workspace/'once-only'
    arguments = {'argv': ['/bin/sh', '-c', 'echo once >> '+str(counter)+'; echo retained; exit 9'],
        'environment': {}}
    original, _ = execute(remote, value, 'practical.command.run', arguments)
    next(remote.workspace.rglob('result.json')).unlink()
    recovered, _ = execute(remote, value, 'practical.command.run', arguments)
    assert recovered == original
    assert recovered['facts']['command']['returncode'] == 9
    assert recovered['native_outcome']['stdout']['text'] == 'retained\n'
    assert counter.read_text() == 'once\n'


def test_unchanged_context_does_not_increment_revision(remote):
    value = assignment(remote.workspace)
    _, context = execute(remote, value, 'practical.context.set',
        {'cwd': str(remote.workspace), 'environment': {}})
    assert context == value['initial_context']


@pytest.mark.parametrize('constraints', [
    {'account': 'unapproved-account'}, {'queue': 'other'}, {'resources': ['select=256']},
    {'allowed_queues': ['other']}, {'allocation': {'resources': ['select=256']}},
    {'cpu': 4}, {'allocation': {'cpu': 4}},
])
def test_parent_constraints_are_not_silently_substituted(remote, constraints):
    value = assignment(remote.workspace)
    value['constraints'] = constraints
    with pytest.raises(ValueError, match='practical_pbs_.*constraint'):
        execute(remote, value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    assert not (remote.database/'submissions').exists()


def test_matching_parent_native_allocation_is_retained(remote):
    value = assignment(remote.workspace)
    value['constraints'] = {'account': 'EpiCalib', 'allocation': {
        'queue': 'test', 'resources': ['select=1']}}
    outcome, _ = execute(remote, value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    assert outcome['facts']['requested_job']['execution_id'] == '12345.aurora'


def test_invalid_environment_name_rejected_before_remote_action(remote):
    value = assignment(remote.workspace)
    with pytest.raises(ValueError, match='invalid_practical_environment'):
        execute(remote, value, 'practical.command.run', {'argv': ['/bin/true'], 'environment': {'bad-name': 'x'}})
    assert remote.calls == []


def test_missing_context_directory_is_a_completed_failed_transition(remote):
    value = assignment(remote.workspace)
    missing = remote.workspace/'not-created-yet'
    outcome, after = execute(remote, value, 'practical.context.set',
        {'cwd': str(missing), 'environment': {}})
    assert after is None
    assert outcome['native_outcome'] == {'status': 'failed', 'failure': {
        'code': 'practical_working_directory_missing', 'path': str(missing)}}
    assert next(remote.workspace.rglob('result.json')).exists()
    execute(remote, value, 'practical.directory.create', {'path': str(missing)}, key='repair')
    _, after = execute(remote, value, 'practical.context.set',
        {'cwd': str(missing), 'environment': {}}, key='retry-transition')
    assert after['cwd'] == str(missing)


def test_file_write_missing_parent_preserves_actual_failure_then_allows_repair(remote):
    value = assignment(remote.workspace)
    path = remote.workspace/'missing'/'script.py'
    outcome, after = execute(remote, value, 'practical.file.write', {'path': str(path), 'text': 'print(1)'})
    assert after is None
    assert outcome['native_outcome']['failure']['code'] == 'practical_filesystem_operation_failed'
    assert outcome['native_outcome']['failure']['exception_type'] == 'FileNotFoundError'
    execute(remote, value, 'practical.directory.create', {'path': str(path.parent)}, key='mkdir')
    completed, _ = execute(remote, value, 'practical.file.write',
        {'path': str(path), 'text': 'print(1)'}, key='write-after-repair')
    assert completed['native_outcome']['sha256'] == hashlib.sha256(b'print(1)').hexdigest()


def test_directory_failure_retains_partial_path_facts(remote):
    value = assignment(remote.workspace)
    path = remote.workspace/'not-a-directory'
    path.write_text('existing')
    outcome, _ = execute(remote, value, 'practical.directory.create', {'path': str(path)})
    assert outcome['native_outcome']['failure']['exception_type'] == 'FileExistsError'
    assert outcome['facts']['paths'][0]['object_type'] == 'missing'


def test_failed_job_can_be_explicitly_repaired_and_retried_without_replay_submission(remote):
    output = remote.workspace/'result.txt'
    repaired = remote.workspace/'repaired'
    value = assignment(remote.workspace, argv=['/bin/sh', '-c',
        'if test -f '+str(repaired)+'; then printf recovered > '+str(output)+'; else exit 9; fi'],
        environment={'FAKE_PBS_EXECUTE': '1'})
    arguments = {'queue': 'test', 'resources': ['select=1']}
    original, _ = execute(remote, value, 'practical.job.start', arguments)
    assert original['facts']['requested_job']['status'] == 'failed'
    assert original['facts']['requested_job']['execution_id'] == '12345.aurora'
    execute(remote, value, 'practical.file.write', {'path': str(repaired), 'text': 'fixed'}, key='repair')
    retry_arguments = {**arguments, 'retry_failed_execution_id': '12345.aurora'}
    retry, _ = execute(remote, value, 'practical.job.start', retry_arguments, key='explicit-retry')
    assert retry['facts']['requested_job']['status'] == 'completed'
    assert retry['facts']['requested_job']['execution_id'] == '12346.aurora'
    assert retry['native_outcome']['retry_of_execution_id'] == '12345.aurora'
    assert retry['native_outcome']['attempt_id'] != original['native_outcome']['attempt_id']
    assert output.read_text() == 'recovered'
    assert execute(remote, value, 'practical.job.start', retry_arguments, key='explicit-retry')[0] == retry
    assert execute(remote, value, 'practical.job.start', arguments)[0] == original
    current, _ = execute(remote, value, 'practical.job.status', key='current')
    assert current['facts']['requested_job']['execution_id'] == '12346.aurora'
    assert (remote.database/'submissions').read_text() == '2'


def test_explicit_retry_rejects_active_unknown_and_foreign_current_job(remote):
    value = assignment(remote.workspace)
    arguments = {'queue': 'test', 'resources': ['select=1']}
    execute(remote, value, 'practical.job.start', arguments)
    retry = {**arguments, 'retry_failed_execution_id': '12345.aurora'}
    active, _ = execute(remote, value, 'practical.job.start', retry, key='active-retry')
    assert active['native_outcome']['failure']['code'] == 'practical_pbs_retry_requires_verified_terminal_failure'
    assert active['facts']['requested_job']['status'] == 'submitted'
    (remote.database/'status-unavailable').touch()
    unknown, _ = execute(remote, value, 'practical.job.start', retry, key='unknown-retry')
    assert unknown['facts']['requested_job']['status'] == 'unknown'
    assert unknown['native_outcome']['failure']['code'] == 'practical_pbs_retry_requires_verified_terminal_failure'
    foreign, _ = execute(remote, value, 'practical.job.start',
        {**arguments, 'retry_failed_execution_id': '99999.foreign'}, key='foreign-retry')
    assert foreign['native_outcome']['failure']['code'] == 'practical_pbs_retry_execution_identity_conflict'
    assert (remote.database/'submissions').read_text() == '1'


def test_retry_pointer_published_before_submission_recovers_same_attempt(remote, monkeypatch):
    value = assignment(remote.workspace, argv=['/bin/false'], environment={'FAKE_PBS_EXECUTE': '1'})
    arguments = {'queue': 'test', 'resources': ['select=1']}
    execute(remote, value, 'practical.job.start', arguments)
    retry = {**arguments, 'retry_failed_execution_id': '12345.aurora'}
    original_worker = pbs._REMOTE_WORKER
    interrupted_worker = original_worker.replace('ledger=submit_attempt(ledger,ledger_path,job_directory)',
        "raise RuntimeError('simulated after durable pointer and before submission')")
    monkeypatch.setattr(pbs, '_REMOTE_WORKER', interrupted_worker)
    with pytest.raises(ValueError, match='simulated after durable pointer'):
        execute(remote, value, 'practical.job.start', retry, key='retry-after-crash')
    assert (remote.database/'submissions').read_text() == '1'
    pointer = json.loads(next(remote.workspace.rglob('current.json')).read_text())
    assert pointer['operation_key'] == 'retry-after-crash'
    monkeypatch.setattr(pbs, '_REMOTE_WORKER', original_worker)
    recovered, _ = execute(remote, value, 'practical.job.start', retry, key='retry-after-crash')
    assert recovered['facts']['requested_job']['execution_id'] == '12346.aurora'
    assert (remote.database/'submissions').read_text() == '2'


def test_selected_invalid_inventory_and_missing_file_are_repairable_completed_failures(remote):
    value = assignment(remote.workspace)
    path = remote.workspace/'catalog.json'
    missing, _ = execute(remote, value, 'practical.inventory.refresh', {'path': str(path)}, key='missing')
    assert missing['inventory_failure']['code'] == 'inventory_read_failed'
    assert 'inventory_catalog' not in missing
    execute(remote, value, 'practical.file.write', {'path': str(path), 'text': 'invalid JSON'}, key='write-bad')
    invalid, _ = execute(remote, value, 'practical.inventory.refresh', {'path': str(path)}, key='invalid')
    assert invalid['inventory_failure']['code'] == 'inventory_catalog_invalid'
    assert 'inventory_bytes_base64' in invalid
    assert 'inventory_catalog' not in invalid
    good = make_catalog(resource_id='aurora', workspace=str(remote.workspace), components=[])
    execute(remote, value, 'practical.file.write', {'path': str(path), 'text': json.dumps(good)}, key='repair-catalog')
    refreshed, _ = execute(remote, value, 'practical.inventory.refresh', {'path': str(path)}, key='refresh-good')
    assert refreshed['inventory_catalog'] == good
    replay, _ = execute(remote, value, 'practical.inventory.refresh', {'path': str(path)}, key='invalid')
    assert replay == invalid


def test_selected_file_read_returns_exact_recorded_byte_window(remote):
    value = assignment(remote.workspace)
    path = remote.workspace/'setup.log'
    path.write_bytes(b'prefix\nactual setup output\ntail')
    arguments = {'path': str(path), 'offset': 7, 'limit': 6}
    original, _ = execute(remote, value, 'practical.file.read', arguments)
    observed = original['native_outcome']
    assert observed['path'] == str(path)
    assert observed['offset'] == 7
    assert observed['returned_bytes'] == 6
    assert observed['size_bytes'] == 31
    assert base64.b64decode(observed['bytes_base64']) == b'actual'
    assert observed['text_utf8'] == 'actual'
    path.write_bytes(b'changed since selected read')
    replay, _ = execute(remote, value, 'practical.file.read', arguments)
    assert replay == original


def test_pbs_action_validation_performs_no_remote_or_filesystem_work(remote):
    value = assignment(remote.workspace)
    remote.operations.validate_action(value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    assert remote.calls == []


def test_nonzero_qsub_client_exit_keeps_job_outcome_unknown_until_verified(remote):
    value = assignment(remote.workspace, environment={'FAKE_PBS_NONZERO_AFTER_ACCEPT': '1'})
    arguments = {'queue': 'test', 'resources': ['select=1']}
    initial, _ = execute(remote, value, 'practical.job.start', arguments)
    assert initial['facts']['requested_job']['status'] == 'unknown'
    assert initial['facts']['requested_job']['returncode'] is None
    assert initial['facts']['requested_job']['handoff'] is None
    assert initial['native_outcome']['submission_outcome']['returncode'] == 1
    denied, _ = execute(remote, value, 'practical.job.start',
        {**arguments, 'retry_failed_execution_id': initial['facts']['requested_job']['execution_id']}, key='retry-unknown')
    assert denied['facts']['requested_job']['status'] == 'unknown'
    assert denied['native_outcome']['failure']['code'] == 'practical_pbs_retry_requires_actual_job_id'
    (remote.database/'selection-enabled').touch()
    recovered, _ = execute(remote, value, 'practical.job.status', key='recover')
    assert recovered['facts']['requested_job']['execution_id'] == '12345.aurora'
    assert recovered['facts']['requested_job']['status'] == 'submitted'
    assert (remote.database/'submissions').read_text() == '1'


@pytest.mark.parametrize('constraints', [
    {'invented_constraint': 1}, {'allowed_accounts': 'EpiCalib'}, {'allowed_queues': 'test'},
    {'allowed_accounts': ['EpiCalib', 'EpiCalib']}, {'allowed_queues': [None]},
])
def test_unknown_constraints_and_nonlist_allowed_values_fail_before_remote_work(remote, constraints):
    value = assignment(remote.workspace)
    value['constraints'] = constraints
    with pytest.raises(ValueError, match='practical_pbs_constraint_'):
        remote.operations.validate_action(value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    assert remote.calls == []
    assert list(remote.workspace.iterdir()) == []
    value['constraints'] = {'account': 'wrong'}
    with pytest.raises(ValueError, match='practical_pbs_account_constraint_conflict'):
        remote.operations.validate_action(value, 'practical.job.start', {'queue': 'test', 'resources': ['select=1']})
    assert remote.calls == []
