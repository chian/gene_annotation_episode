"""Exact-attempt recursive native monitoring with controlled PBS transports.

The remote worker and qstat subprocess are real; PBS is a local fixture. These
tests run no live scheduler, network/model service, or scientific investigation.
"""
import base64
from collections import Counter
from copy import deepcopy
import json
import gc
import hashlib
import os
from pathlib import Path
import stat
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
            configuration = {'kind': 'local', 'workspace': str(spec.workspace), 'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}}
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


def _two_stored_handoffs(e):
    """Existing controlled PBS transport and real selected receipt publications."""
    _, first, _ = start(e)
    collected, _ = execute(e.remote, e.value, 'practical.job.collect', key='run-1:episode-1:1')
    second, _ = e.publish(collected, 1, tool_name='practical.job.collect')
    assert first != second
    return first, second


def test_operation_local_handoff_reader_counts_equal_values_and_detached_aliases(environment, monkeypatch):
    e = environment
    refs = _two_stored_handoffs(e)
    reader = e.native.targets
    expected = {}
    for ref in refs:
        target = reader.read_target(ref, e.scope)
        expected[ref] = (target, reader.usable_handoff(target), reader.returnable_handoff(target))
    assert expected[refs[0]][0]['execution_id'] == expected[refs[1]][0]['execution_id']
    before = tuple(e.store.db.iterdump()), files(e.state.directory)
    calls, original = [], reader.receipts.read
    def counted(ref, scope):
        calls.append((ref, canonical(plain(scope))))
        return original(ref, scope)
    monkeypatch.setattr(reader.receipts, 'read', counted)
    with e.store.read_snapshot():
        read = reader._handoff_reader()
        for ref in refs:
            assert read(ref, e.scope) == expected[ref]
            changed = read(ref, deepcopy(e.scope))
            changed[0]['assignment']['requested_job']['argv'][0] = 'changed detached view'
            assert read(ref, e.scope) == expected[ref]
        assert Counter(calls) == Counter((ref, canonical(e.scope)) for ref in refs)
        broad = e.store.validate_scope()
        assert broad != e.scope
        assert read(refs[0], broad) == expected[refs[0]]
        assert calls[-1] == (refs[0], canonical(broad))
    with e.store.read_snapshot():
        fresh = reader._handoff_reader()
        assert fresh(refs[0], e.scope) == expected[refs[0]]
    assert Counter(calls)[(refs[0], canonical(e.scope))] == 2
    assert (tuple(e.store.db.iterdump()), files(e.state.directory)) == before
    assert not [row for row in e.remote.calls if row[1]['mode'] == 'observe_execution']


@pytest.mark.parametrize('fault', ['scope', 'body', 'resource', 'target', 'cycle'])
def test_operation_local_handoff_reader_keeps_denials_and_retries_failed_reads(environment, monkeypatch, fault):
    e = environment
    _, ref, _ = start(e)
    reader = e.native.targets
    scope, selected = deepcopy(e.scope), ref
    target = reader.read_target(ref, e.scope)
    if fault == 'scope':
        scope = {'subject_refs': [e.store.targets()[1]['id']]}
    elif fault == 'body':
        source = e.store.get(ref)
        body = json.loads(e.store.get_artifact(source['artifact_ref']))
        body['receipt']['arguments'] = {'different': 'selected action'}
        artifact = e.store.artifact(canonical(body), 'application/json')
        selected = e.store.put('source', reader.receipts._source_payload(body,
            artifact, source['request_ref']), origin='tool')['id']
    elif fault == 'resource':
        configuration = deepcopy(reader.resources)
        configuration['fixture-hpc']['workspace'] = str(e.tmp_path / 'unselected-workspace')
        monkeypatch.setattr(reader, 'resources', configuration)
    calls, original = [], reader.receipts.read
    def counted(reference, receiving):
        calls.append((reference, canonical(plain(receiving))))
        return original(reference, receiving)
    monkeypatch.setattr(reader.receipts, 'read', counted)
    before = tuple(e.store.db.iterdump()), files(e.state.directory)
    with e.store.read_snapshot():
        read = reader._handoff_reader()
        if fault in {'scope', 'body', 'resource'}:
            for _ in range(2):
                with pytest.raises(ContractError, match='execution_target_unavailable_or_outside_scope'):
                    read(selected, scope)
            assert calls == [(selected, canonical(scope))] * 2
        elif fault == 'target':
            assert read(ref, scope)[0] == target
            changed = {**target, 'execution_id': 'different.aurora'}
            with pytest.raises(ContractError, match='execution_target_identity_conflict'):
                reader.returnable_handoff(changed)
            assert read(ref, scope)[0] == target
        else:
            receipt_reads = {}
            reader._native(ref, scope, _receipt_reads=receipt_reads)
            count = len(calls)
            with pytest.raises(ValueError, match='receipt_ancestry_cycle'):
                reader._native(ref, scope, _seen=(ref,), _receipt_reads=receipt_reads)
            assert len(calls) == count
    assert (tuple(e.store.db.iterdump()), files(e.state.directory)) == before
    assert not [row for row in e.remote.calls if row[1]['mode'] == 'observe_execution']


def test_one_fact_pass_publishes_before_snapshot_and_authenticates_each_stored_source_once(environment, monkeypatch):
    """Engineering facts routing around actual immutable selected PBS receipts."""
    from gene_annotation_episode.execution_episodes import ExecutionEpisodes
    e = environment
    refs = _two_stored_handoffs(e)
    reader = e.native.targets
    expected = sorted(ref for ref in refs if reader.returnable_handoff(reader.read_target(ref, e.scope)))
    owner = ExecutionEpisodes.__new__(ExecutionEpisodes)
    owner.store, owner.run_id, owner.api_execution = e.store, e.context.run_id, None
    owner.job_progress_provider = e.native
    inactive = SimpleNamespace(applies=lambda *_: False)
    for name in ('native_blast_masking_results', 'native_blast_utility_results',
            'native_fluorescence_results', 'native_protein_structure_results', 'native_hmmer_results'):
        setattr(owner, name, inactive)
    for name in ('native_flux_balance_results', 'native_expression_nmf_results', 'atac_results',
            'native_chromatin_interaction_results', 'native_genomic_overlap_results',
            'rna_structure_comparison_results', 'native_rna_structure_results',
            'native_blast_standard_database_results', 'native_blast_database_results',
            'native_hmmer_preparation_results', 'native_infernal_preparation_results',
            'native_blast_results', 'native_infernal_results'):
        setattr(owner, name, None)
    owner.local_file_sources = inactive
    owner._has_appservice = lambda: False
    owner._practical_context = lambda context: context
    owner._selection = lambda context, supplied=None: dict(run_id=context.run_id,
        episode_id=context.episode_id, known_record_refs=[*refs, refs[0]], initial_known_record_refs=[])
    published = []
    def published_facts(context, completion):
        assert not e.store.db.in_transaction
        published.append(context.episode_id)
        return dict(practical_completed=False, practical_receipt_refs=list(refs))
    owner._delegate = lambda context: SimpleNamespace(facts=published_facts)
    calls, original = [], reader.receipts.read
    def counted(reference, scope):
        assert e.store.db.in_transaction
        calls.append((reference, canonical(plain(scope))))
        return original(reference, scope)
    monkeypatch.setattr(reader.receipts, 'read', counted)
    before = tuple(e.store.db.iterdump()), files(e.state.directory)
    actual = owner._live_facts(e.context, {})
    assert actual['execution_handoff_refs'] == expected
    assert actual['execution_completed'] is False
    assert actual['practical_receipt_refs'] == list(refs)
    assert actual['execution_result_refs'] == actual['execution_file_source_refs'] == []
    assert published == [e.context.episode_id]
    assert Counter(calls) == Counter((ref, canonical(e.scope)) for ref in refs)
    assert (tuple(e.store.db.iterdump()), files(e.state.directory)) == before


def test_retained_original_lumpy_handoffs_use_one_operation_local_metadata_read(tmp_path, monkeypatch):
    """Opt-in original native receipts; no workflow continuation or scientific work."""
    selected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESOURCE_PREFIX')
    expected_sha = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESOURCE_PREFIX_SHA256')
    if not selected or not expected_sha:
        pytest.skip('requires the explicitly pinned original LUMPY resource prefix')
    prefix = Path(selected).resolve(strict=True)
    raw = prefix.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_sha
    proof = json.loads(raw)
    assert proof['version'] == 'lumpy_resource_workflow_proof_v1'
    assert proof['native_seal']['outcome'] == 'succeeded' and proof['native_seal']['returncode'] == 0
    original = Path(proof['directory']).resolve(strict=True)
    store_path = Path(proof['store_directory']).resolve(strict=True)
    assert store_path.parent == original and prefix.parent == original

    def inventory(directory):
        result = {}
        for path in sorted(directory.rglob('*')):
            # WAL/SHM may exist transiently while actual SQLite owners are open.
            if path.name.endswith(('-wal', '-shm')):
                continue
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode):
                body = path.read_bytes()
                result[str(path.relative_to(directory))] = dict(mode=stat.S_IMODE(mode),
                    size_bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
            elif stat.S_ISLNK(mode):
                result[str(path.relative_to(directory))] = dict(mode=stat.S_IMODE(mode),
                    symlink=os.readlink(path))
        return result

    before_files = inventory(original)
    before_family = {path.name: dict(size_bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), mode=stat.S_IMODE(path.stat().st_mode))
        for path in sorted(store_path.glob('state.sqlite3*')) if path.is_file()}
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode import native_lumpy_execution as lumpy
    from gene_annotation_episode import vcf_result_measurements as variants
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_lumpy_resource_workflow import _assemble

    forbidden_calls = []
    def forbidden(*args, **kwargs):
        forbidden_calls.append('forbidden work')
        raise AssertionError('retained handoff metadata read attempted work or publication')
    class NoDecisions:
        async def complete(self, *args, **kwargs):
            return forbidden(*args, **kwargs)
        async def release(self, *args, **kwargs):
            return forbidden(*args, **kwargs)
    for name in ('prepare_job', 'start_prepared', 'start_job', 'resume_start', 'status',
            'collect', 'cancel', 'release', 'run_blocking', 'wait_job'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    monkeypatch.setattr(native_lifecycle.NativeJobHandle, 'read', forbidden)
    for name in ('prepare_local_lumpy', 'run_lumpy', 'freeze_lumpy_software_binding', '_verify_native_runtime'):
        monkeypatch.setattr(lumpy, name, forbidden)
    for name in ('parse_vcf_sheet', 'calculate_vcf_components', 'project_vcf_return'):
        monkeypatch.setattr(variants, name, forbidden)
    monkeypatch.setattr(ToolRegistry, 'execute', forbidden)
    monkeypatch.setattr(Workflow, 'build', forbidden)
    for name in ('put', 'artifact', 'register_material', 'create_problem'):
        monkeypatch.setattr(Store, name, forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)

    store = workflow = tools = owner = None
    outcome = dict(version='lumpy_retained_handoff_metadata_v1', prefix=str(prefix),
        prefix_sha256=expected_sha, passed=False, native_work_executed=False)
    try:
        store = Store(store_path)
        before_rows = tuple(store.db.iterdump())
        workflow, tools = _assemble(store, proof, NoDecisions())
        owner = workflow.episode_bindings.for_role('results')
        reader = owner.job_progress_provider.targets
        authority = EpisodeReturnRecords(store, proof['run_id'], failure_prefix='lumpy_retained_metadata_')
        context = authority.context(proof['native_plan']['identity']['episode_id'])
        assert context.role == 'launch_local'
        authority.authenticate(context)
        row = store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (proof['run_id'], context.episode_id)).fetchone()
        assert row is not None
        form = json.loads(row['form'])
        assert form['completed'] is True
        refs = form['references']
        assert len(refs) == len(set(refs)) == 2
        expected, operations = {}, set()
        for reference in refs:
            body = reader.receipts.read(reference, context.scope)
            operations.add(body['receipt']['tool_name'])
            target = reader.read_target(reference, context.scope)
            assert target['origin_episode_id'] == context.episode_id
            assert target['execution_id'] == proof['native_plan']['identity']['execution_id']
            expected[reference] = (target, reader.usable_handoff(target), reader.returnable_handoff(target))
        assert operations == {'practical.job.start', 'practical.job.collect'}
        calls, original_read = [], reader.receipts.read
        def counted(reference, scope):
            calls.append((reference, canonical(plain(scope))))
            return original_read(reference, scope)
        monkeypatch.setattr(reader.receipts, 'read', counted)
        with store.read_snapshot():
            read = reader._handoff_reader()
            for reference in refs:
                assert read(reference, context.scope) == expected[reference]
                changed = read(reference, context.scope)
                changed[0]['assignment']['requested_job']['argv'][0] = 'detached mutation'
                assert read(reference, deepcopy(plain(context.scope))) == expected[reference]
            assert Counter(calls) == Counter((ref, canonical(plain(context.scope))) for ref in refs)
        first_operation = list(calls)
        with store.read_snapshot():
            fresh = reader._handoff_reader()
            for reference in refs:
                assert fresh(reference, context.scope) == expected[reference]
        assert Counter(calls) == Counter({key: 2 for key in first_operation})
        assert tuple(store.db.iterdump()) == before_rows
        assert forbidden_calls == []
        outcome.update(passed=True, source_refs=refs, episode_id=context.episode_id,
            receiving_scope=plain(context.scope), stored_operations=sorted(operations),
            first_operation_receipt_reads=[dict(source_ref=ref, scope=json.loads(scope)) for ref, scope in first_operation],
            fresh_operation_reauthenticated=True, exact_original_rows=True,
            logical_rows_sha256=hashlib.sha256('\n'.join(before_rows).encode()).hexdigest())
    except BaseException as error:
        outcome['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            store.close()
        owner = workflow = tools = store = None
        gc.collect()
        after_files = inventory(original)
        after_family = {path.name: dict(size_bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), mode=stat.S_IMODE(path.stat().st_mode))
            for path in sorted(store_path.glob('state.sqlite3*')) if path.is_file()}
        files_equal = after_files == before_files
        family_equal = {key: value for key, value in after_family.items() if not key.endswith(('-wal', '-shm'))} == {
            key: value for key, value in before_family.items() if not key.endswith(('-wal', '-shm'))}
        prefix_equal = prefix.read_bytes() == raw
        outcome.update(passed=outcome['passed'] and files_equal and family_equal and prefix_equal,
            original_files_unchanged=files_equal, original_prefix_unchanged=prefix_equal,
            original_sqlite_family_before=before_family,
            original_sqlite_family_after=after_family,
            original_file_inventory_sha256=hashlib.sha256(canonical(before_files).encode()).hexdigest(),
            forbidden_work_attempts=forbidden_calls)
        (tmp_path / 'LUMPY_RETAINED_HANDOFF_METADATA.json').write_text(json.dumps(outcome, indent=2) + '\n')
        assert files_equal and family_equal and prefix_equal
