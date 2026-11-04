"""Exact-attempt recursive native monitoring with controlled PBS transports.

The remote worker and qstat subprocess are real; PBS is a local fixture. These
tests run no live scheduler, network/model service, or scientific investigation.
"""
import base64
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from method_loop.durable import DurableExecutionStore
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_monitoring import ProgressProvider
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_progress import ExecutionProgressProvider
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.progress_records import validate_resource_observation
from gene_annotation_episode.state import Store
from test_practical_pbs_operations import remote, assignment, execute


FIELDS = ['execution_status', 'measurements', 'log_windows', 'committed_record_refs',
          'dependencies', 'result_available']


@pytest.fixture
def environment(tmp_path, remote):
    with Store(tmp_path/'store') as store:
        fasta = tmp_path/'targets.faa'
        fasta.write_text('>target\nMKWAA\n>other\nMTAQ\n')
        store.create_problem(fasta, molecule='protein')
        scope = store.validate_scope({'subject_refs': [store.targets()[0]['id']]})
        value = assignment(remote.workspace)
        value['resource_id'] = 'fixture-hpc'
        request = {'message': {'scope': scope, 'episode_assignment': value}}
        context = BindingContext('run-1', 'episode-1', 'launch_hpc',
            (('annotation', 'root'), ('launch_hpc', 'native')), scope, value, request)
        journal = Journal(store, context.run_id)
        with store.transaction():
            journal.save('runtime_episodes', {'episode_id': context.episode_id,
                'path': canonical(plain(context.path)), 'request': canonical(request),
                'initial_credit': 0, 'state': 'running'})
        state = PracticalState(tmp_path/'practical', context.run_id, context.episode_id, value)
        receipts = PracticalReceiptInformation(store, context.run_id)
        def publish(outcome, index=0, arguments=None, tool_name='practical.job.start'):
            key = f'{context.run_id}:{context.episode_id}:{index}'
            if arguments is None:
                arguments = {'queue': 'test', 'resources': ['select=1']} if tool_name == 'practical.job.start' else {}
            with store.transaction():
                journal.save('runtime_actions', {'episode_id': context.episode_id,
                    'decision_index': index, 'action': canonical({'kind': 'tool',
                        'tool': tool_name, 'arguments': arguments}),
                    'result': None, 'credit': None})
            state.begin(key, tool_name, arguments)
            receipt = state.finish(key, outcome, assess_validations(value, outcome,
                state.context(), tool_name=tool_name))
            ref = receipts.publish(context, receipt)
            result = {'status': 'completed', 'record_refs': [ref],
                'changed_record_refs': [], 'result': receipt}
            with store.transaction():
                store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? '
                    'AND episode_id=? AND decision_index=?',
                    (canonical(result), context.run_id, context.episode_id, index))
            return ref, result
        resources = {'fixture-hpc': remote.configuration}
        native = ExecutionProgressProvider(store, run_id=context.run_id,
            directory=tmp_path/'execution', resources=resources, api_execution=None,
            log_window_bytes=7, log_roles=('stdout', 'stderr'))
        durable = DurableExecutionStore(tmp_path/'durable')
        progress = ProgressProvider(store, durable, run_id=context.run_id, job_provider=native)
        yield SimpleNamespace(store=store, scope=scope, value=value, remote=remote,
            context=context, publish=publish, state=state, native=native, progress=progress,
            durable=durable, resources=resources, tmp_path=tmp_path)


def start(e, index=0, retry=None):
    arguments = {'queue': 'test', 'resources': ['select=1']}
    if retry is not None:
        arguments['retry_failed_execution_id'] = retry
    outcome, _ = execute(e.remote, e.value, 'practical.job.start', arguments,
        key=f'run-1:episode-1:{index}')
    reference, result = e.publish(outcome, index, arguments)
    return outcome, reference, result


def files(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


def test_old_pbs_target_survives_retry_and_corrupt_current_pointer(environment):
    e = environment
    first, ref, result = start(e)
    first_id = first['facts']['requested_job']['execution_id']
    record_path = e.remote.database/(first_id+'.json')
    record = json.loads(record_path.read_text())
    record.update(job_state='F', Exit_status=7, stime=110, obittime=120)
    record_path.write_text(json.dumps(record))
    second, _, _ = start(e, index=1, retry=first_id)
    assert second['facts']['requested_job']['execution_id'] != first_id
    for pointer in e.remote.workspace.rglob('current.json'):
        pointer.write_text('{"invalid":"must not read current"}')
    target = e.native.targets.read_target(ref, e.scope)
    assert target['execution_id'] == first_id
    before = files(e.state.directory)
    observed = e.progress.observe(ref, FIELDS, e.scope, operation_key='monitor:original')
    status = observed['execution_status']
    assert status['version'] == 'resource_execution_status_v1'
    assert status['lifecycle_state'] == 'returned'
    assert status['native']['state'] == 'failed' and status['native']['returncode'] == 7
    assert status['native']['native']['pbs_job_id'] == first_id
    assert {row['name']: row['value'] for row in observed['measurements']} == {
        'pbs_queue_wait_seconds': 10, 'pbs_total_turnaround_seconds': 20}
    assert files(e.state.directory) == before
    assert (e.remote.database/'submissions').read_text() == '2'
    assert e.remote.calls[-1][1]['mode'] == 'observe_execution'
    assert e.remote.calls[-1][1]['attempt_id'] == first['native_outcome']['attempt_id']
    # Both provider layers replay before opening the target or transport.
    def forbid(*args, **kwargs):
        pytest.fail('replay must not poll, read logs, or open launch state')
    e.native.targets.read_target = forbid
    e.native.targets.observe_target = forbid
    e.native.targets.operations['fixture-hpc']._invoke = forbid
    assert e.progress.observe(ref, FIELDS, e.scope, operation_key='monitor:original') == observed
    assert e.native.observe(ref, FIELDS, e.scope, operation_key='monitor:original')['execution_status'] == status


def test_raw_log_bytes_custody_and_selected_output_read_do_not_touch_launch(environment):
    e = environment
    outcome, ref, _ = start(e)
    # Native source contains the actual attempt log path, not a reconstructed
    # representation of its lossy UTF-8 display.
    path = outcome['native_outcome']['stdout']['path']
    from pathlib import Path
    raw = b'prefix\x00\xff\xfeend\n'
    Path(path).write_bytes(raw)
    before = files(e.state.directory)
    snapshot = e.progress.observe(ref, FIELDS, e.scope, operation_key='monitor:logs')
    assert len(snapshot['log_windows']) == 1
    window = snapshot['log_windows'][0]
    assert e.store.get_artifact(window['artifact_ref']) == raw[-7:]
    source = e.store.get(window['source_ref'])
    metadata = json.loads(e.store.get_artifact(source['request_ref']))
    assert metadata['original_start_byte'] == len(raw)-7
    assert metadata['original_end_byte'] == len(raw)
    assert metadata['observed_file_size'] == len(raw)
    target = e.native.targets.read_target(ref, e.scope)
    selected = e.native.targets.read_file(target, path=path, offset=7, limit=3)
    assert base64.b64decode(selected['bytes_base64']) == raw[7:10]
    assert selected['returned_bytes'] == 3
    assert files(e.state.directory) == before
    assert not snapshot['measurements']  # qtime without stime is not a duration.
    assert (e.remote.database/'submissions').read_text() == '1'


def test_scope_original_request_and_supplied_target_identity_are_qualified(environment):
    e = environment
    _, ref, _ = start(e)
    target = e.native.targets.read_target(ref, e.scope)
    changed = deepcopy(target)
    changed['execution_id'] = '99999.aurora'
    with pytest.raises(ContractError, match='identity_conflict'):
        e.native.targets.observe_target(changed, operation_key='forged')
    changed = deepcopy(target)
    changed['assignment']['requested_job']['argv'] = ['/bin/false']
    with pytest.raises(ContractError, match='identity_conflict'):
        e.native.targets.observe_target(changed, operation_key='forged-request')
    other = e.store.targets()[1]['id']
    with pytest.raises(ContractError, match='outside_scope'):
        e.native.targets.read_target(ref, {'subject_refs': [other]})
    assert len([call for call in e.remote.calls if call[1]['mode'] == 'observe_execution']) == 0


def test_one_real_dependency_is_exposed_after_committed_native_handoff(environment):
    e = environment
    _, ref, result = start(e)
    relation = e.native.dependency_from_outcome(e.context, result, 'run-1:episode-1:0')
    assert relation['kind'] == 'job' and relation['handle'] == ref
    assert e.native.dependency_from_outcome(e.context, result, 'run-1:episode-1:0') == relation
    saved = e.store.get(relation['relation_ref'])
    body = json.loads(e.store.get_artifact(saved['artifact_ref']))
    assert body['owner_episode_id'] == e.context.episode_id
    assert body['target']['execution_id'] == e.native.targets.read_target(ref, e.scope)['execution_id']
    assert e.native.direct_dependencies(ref, e.scope) == []
    assert len([call for call in e.remote.calls if call[1]['mode'] == 'observe_execution']) == 0


def test_receipt_aliases_share_first_durable_physical_dependency_and_retry_is_distinct(environment):
    e = environment
    first, first_ref, first_result = start(e)
    first_id = first['facts']['requested_job']['execution_id']
    relationship = e.native.dependency_from_outcome(e.context, first_result, 'run-1:episode-1:0')
    record_path = e.remote.database/(first_id+'.json')
    record = json.loads(record_path.read_text())
    record.update(job_state='F', Exit_status=7, stime=110, obittime=120)
    record_path.write_text(json.dumps(record))
    collected, _ = execute(e.remote, e.value, 'practical.job.collect', key='run-1:episode-1:1')
    alias_ref, alias_result = e.publish(collected, 1, tool_name='practical.job.collect')
    assert alias_ref != first_ref
    # Reconstruct the provider to prove identity is durable rather than an
    # in-memory set of seen handles. Every source still reads its exact target.
    restored = ExecutionProgressProvider(e.store, run_id=e.context.run_id,
        directory=e.tmp_path/'execution', resources=e.resources, api_execution=None,
        log_window_bytes=7, log_roles=('stdout', 'stderr'))
    assert restored.targets.read_target(first_ref, e.scope)['execution_id'] == first_id
    assert restored.targets.read_target(alias_ref, e.scope)['execution_id'] == first_id
    assert restored.dependency_from_outcome(e.context, alias_result, 'run-1:episode-1:1') == relationship
    assert relationship['handle'] == first_ref
    assert e.store.db.execute('SELECT count(*) FROM runtime_execution_progress_dependencies').fetchone()[0] == 1
    assert len([row for row in e.store.list('source')
        if row.get('provider') == 'execution.progress.relationship']) == 1
    retried, retry_ref, retry_result = start(e, index=2, retry=first_id)
    retry_relationship = restored.dependency_from_outcome(e.context, retry_result, 'run-1:episode-1:2')
    assert retried['facts']['requested_job']['execution_id'] != first_id
    assert retry_relationship['handle'] == retry_ref != first_ref
    assert retry_relationship['relation_ref'] != relationship['relation_ref']
    assert e.store.db.execute('SELECT count(*) FROM runtime_execution_progress_dependencies').fetchone()[0] == 2
    assert (e.remote.database/'submissions').read_text() == '2'
    assert len([call for call in e.remote.calls if call[1]['mode'] == 'observe_execution']) == 0


def test_resource_capture_survives_later_c8_publication_failure(environment, monkeypatch):
    e = environment
    _, ref, _ = start(e)
    original = e.progress._validate_exposed
    def reject_publication(*args, **kwargs):
        raise ContractError('fixture_publication_interrupted')
    monkeypatch.setattr(e.progress, '_validate_exposed', reject_publication)
    with pytest.raises(ContractError, match='fixture_publication_interrupted'):
        e.progress.observe(ref, FIELDS, e.scope, operation_key='monitor:recovered')
    assert e.store.db.execute('SELECT count(*) FROM runtime_execution_progress_operations '
        'WHERE operation_key=?', ('monitor:recovered',)).fetchone()[0] == 1
    def forbid_native(*args, **kwargs):
        pytest.fail('saved resource custody must precede C8 retry')
    monkeypatch.setattr(e.native.targets, 'observe_target', forbid_native)
    monkeypatch.setattr(e.progress, '_validate_exposed', original)
    restored = e.progress.observe(ref, FIELDS, e.scope, operation_key='monitor:recovered')
    assert restored['execution_status']['native']['state'] == 'submitted'
    assert len([call for call in e.remote.calls if call[1]['mode'] == 'observe_execution']) == 1


def test_resource_credit_excludes_bytes_read_times_and_open_elapsed(environment):
    e = environment
    _, ref, _ = start(e)
    baseline = e.progress.observe(ref, FIELDS, e.scope, operation_key='base')
    first = json.loads((e.remote.database/'12345.aurora.json').read_text())
    # New actual queue-duration information, not elapsed time, is eligible.
    first.update(job_state='R', stime=115)
    (e.remote.database/'12345.aurora.json').write_text(json.dumps(first))
    active = e.progress.observe(ref, FIELDS, e.scope, operation_key='active')
    from pathlib import Path
    original = e.native.targets.receipts.read(ref, e.scope)
    stdout = Path(original['receipt']['outcome']['native_outcome']['stdout']['path'])
    stdout.write_bytes(b'x')
    with_log = e.progress.observe(ref, FIELDS, e.scope, operation_key='with-log')
    stdout.write_bytes(b'longer bytes\xff')
    growing = e.progress.observe(ref, FIELDS, e.scope, operation_key='growing')
    context = BindingContext(e.context.run_id, 'monitor', 'monitor', (('monitor', 'm'),),
        e.scope, {}, {})
    credit = ProgressInformationCredit(e.progress, information_unit=2.5)
    view = credit(context, {'run_id': e.context.run_id, 'episode_id': 'monitor',
        'initial_progress_refs': [baseline['progress_ref']],
        'known_progress_refs': [active['progress_ref'], with_log['progress_ref'], growing['progress_ref']]})
    # Running/queue measurement is one received contribution; first stdout
    # availability is another. Its later byte growth contributes zero.
    assert view['credit'] == 5
    assert view['newly_informative_received_snapshot_count'] == 2
    assert [row['progress_ref'] for row in view['monitoring_information_contributions']] == [
        active['progress_ref'], with_log['progress_ref']]


@pytest.mark.parametrize('mutation', [
    lambda value: value.update(observed_at='2026-10-22T00:00:00'),
    lambda value: value['logs'][0].update(bytes_base64='not base64'),
    lambda value: value['logs'][0].update(offset=500),
    lambda value: value['outputs'][0].update(available=False),
    lambda value: value['measurements'].append({'measure': 'made-up', 'seconds': float('nan')}),
])
def test_resource_observation_rejects_unqualified_time_bytes_and_finite_values(mutation):
    observation = {'observed_at': '2026-10-22T00:00:00Z', 'state': 'running',
        'returncode': None, 'failure_code': None, 'result_available': False,
        'measurements': [], 'outputs': [{'role': 'stdout', 'available': True,
            'bytes': 1, 'writer_closed': False}], 'logs': [{'role': 'stdout',
            'path': '/project/out', 'offset': 0, 'observed_size': 1, 'bytes_base64': 'eA=='}],
        'provenance_refs': [], 'native': {}}
    mutation(observation)
    with pytest.raises(ContractError):
        validate_resource_observation(observation)


@pytest.mark.parametrize('handoff_state, expected_dependency_state', [
    ('SUCCESS', 'returned'), ('STARTED', 'executing')])
def test_real_api_port_delegation_commits_get_intent_before_progress_projection(
        tmp_path, handoff_state, expected_dependency_state):
    from api_execution_fixture import APIHarness
    from test_public_search import Client, snapshot
    from gene_annotation_episode.tools import ToolRegistry
    with Store(tmp_path/'api-store') as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = ToolRegistry(store, clients=Client())
        owner = APIHarness(tools)
        tools.clients.hmmer_status = lambda job: snapshot({'task': {'status': handoff_state}})
        ref = owner.handoff()
        launch_before = [dict(row) for row in store.db.execute('SELECT * FROM api_execution_actions')]
        native = ExecutionProgressProvider(store, run_id='api-run', directory=tmp_path/'api',
            resources={'ebi': {'kind': 'hmmer_api'}}, api_execution=owner.api,
            log_window_bytes=8, log_roles=())
        provider = ProgressProvider(store, DurableExecutionStore(tmp_path/'api-durable'),
            run_id='api-run', job_provider=native)
        calls = []
        def get_status(job):
            # The API owns this durable intent and commits it before HTTP;
            # provider projection must not turn that commit into a savepoint.
            import sqlite3
            connection = sqlite3.connect(store.path/'state.sqlite3')
            try:
                row = connection.execute('SELECT observation FROM api_execution_observations '
                    'WHERE operation_key=?', ('monitor:api',)).fetchone()
                assert row is not None and row[0] is None
            finally:
                connection.close()
            calls.append(job)
            return snapshot({'task': {'status': 'STARTED'}})
        tools.clients.hmmer_status = get_status
        selected = provider.observe(ref, FIELDS, owner.context.scope, operation_key='monitor:api')
        assert selected['execution_status']['native']['state'] == 'running'
        assert selected['measurements'] == [] and selected['log_windows'] == []
        assert len(calls) == 1
        assert native.scope(ref) == plain(owner.context.scope)
        assert provider.observe(ref, FIELDS, owner.context.scope, operation_key='monitor:api') == selected
        assert len(calls) == 1
        assert [dict(row) for row in store.db.execute('SELECT * FROM api_execution_actions')] == launch_before
        outcome = owner.api._own_results(owner.context)[-1]
        relation = native.dependency_from_outcome(owner.context, outcome, 'api-run:api-child:1')
        assert relation['handle'] == ref
        assert relation['state'] == expected_dependency_state
        assert len(calls) == 1


def test_real_local_closed_launch_is_observed_without_reopening_history(tmp_path):
    from pathlib import Path
    from gene_annotation_episode import native_lifecycle as native
    from test_practical_runtime import make_assignment, host, Choices, selected, run
    spec = make_assignment(tmp_path/'local-project', reuse=True, held=True, endpoint='usable_handoff')
    # Real subprocess output intentionally has bytes that a UTF-8 display loses.
    spec.script.write_text(spec.body + '\nimport sys\nsys.stdout.buffer.write(bytes([255,0,254]))\n')
    with Store(tmp_path/'local-store') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        origin = host(store, tmp_path/'local-run', spec.assignment,
            Choices([selected('practical.job.start')]))
        handle = None
        try:
            closed = run(origin)
            state = origin.binding.state(origin.context)
            original_history = deepcopy(closed.as_record())
            action = origin.workflow.journal.row('runtime_actions', origin.context.episode_id, 0)
            reference, = json.loads(action['result'])['record_refs']
            execution_id = state.receipts()[0]['outcome']['facts']['requested_job']['execution_id']
            handle = native.NativeJobHandle(Path(execution_id))
            configuration = {'kind': 'local', 'workspace': str(spec.workspace), 'policy': {
                'memory_bytes': 128*1024**2, 'scratch_bytes': 8*1024**2, 'wall_seconds': None}}
            adapter = ExecutionProgressProvider(store, run_id=origin.context.run_id,
                directory=tmp_path/'local-execution', resources={'local': configuration},
                api_execution=None, log_window_bytes=8, log_roles=('stdout', 'stderr'))
            progress = ProgressProvider(store, DurableExecutionStore(tmp_path/'local-durable'),
                run_id=origin.context.run_id, job_provider=adapter)
            before = files(state.directory)
            running = progress.observe(reference, FIELDS, origin.context.scope, operation_key='local:running')
            assert running['execution_status']['native']['state'] in {'running', 'submitted'}
            assert running['measurements'] == []
            (spec.work/'release').touch()
            assert native.wait_job(handle).returncode == 0
            completed = progress.observe(reference, FIELDS, origin.context.scope, operation_key='local:done')
            assert completed['execution_status']['native']['state'] == 'completed'
            assert [row['name'] for row in completed['measurements']] == ['systemd_service_wall_seconds']
            windows = [store.get_artifact(row['artifact_ref']) for row in completed['log_windows']]
            assert b'\xff\x00\xfe' in windows
            assert files(state.directory) == before
            assert closed.as_record() == original_history
            assert len(list(spec.workspace.rglob('native.json'))) == 1
        finally:
            (spec.work/'release').touch()
            if handle is not None:
                native.wait_job(handle)
