"""Production AppService monitor with real custody and controlled native bytes.

These saved selections exercise actual execution/consumer ports. They do not
claim a configured model, live BV-BRC service, or a full method_loop run.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
from method_loop.durable import DurableExecutionStore

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.bvbrc_appservice_monitor import AppServiceMonitor, PROVIDER
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_progress import ExecutionProgressProvider
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_host import ProductionDriver
from test_durable_episode import commission_spec


STAMP = '2026-10-24T12:00:00+00:00'


def assignment(handle, fields=FIELDS):
    return {'version': 'monitor_assignment_v1', 'target_handle': handle,
        'requested_fields': list(fields), 'known_progress_refs': [],
        'permitted_committed_record_types': []}


@pytest.fixture
def h(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('native monitor verification attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    with Store(tmp_path / 'state') as store:
        d = ProductionDriver(store, tmp_path)
        d.tree()
        handoff = d.launch_task()
        d.saved.admit(d.launch, d.context, handoff['source_ref'])
        d.saved.admit(d.saved.root, d.launch, handoff['source_ref'])
        monitor = d.saved.child(d.saved.root, 'monitor', assignment(handoff['source_ref']), 3)
        target = d.api.read_target(handoff['source_ref'], monitor.scope)
        d.client.calls.clear()
        d.client.value = {'123': {'id': '123', 'app': 'Homology', 'status': 'running',
            'submit_time': '2026-10-24 12:00:00', 'start_time': '0000-00-00 00:00:00',
            'completed_time': None, 'elapsed_time': '01:02:03'}}
        yield SimpleNamespace(d=d, store=store, monitor=monitor, target=target,
            handoff=handoff, directory=tmp_path)


def select(h, choice, *, context=None, fields=FIELDS, index=None, tool='progress.observe', arguments=None):
    context = h.monitor if context is None else context
    if index is None:
        index = h.store.db.execute('SELECT coalesce(max(decision_index),-1)+1 FROM runtime_actions '
            'WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()[0]
    arguments = {'requested_fields': list(fields), 'native_operation': choice} if arguments is None else arguments
    h.d.saved.journal.save('runtime_actions', {'episode_id': context.episode_id,
        'decision_index': index, 'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': arguments}),
        'result': None, 'credit': None})
    return f'{context.run_id}:{context.episode_id}:{index}', arguments


def observe(h, choice, *, key=None, context=None, fields=FIELDS):
    context = h.monitor if context is None else context
    if key is None:
        key, _ = select(h, choice, context=context, fields=fields)
    return h.d.api.observe_target(h.target, operation_key=key,
        native_operation=choice, observation_context=context)


def retained(h, key):
    directory = h.d.api.directory / 'observations' / digest(key)
    response = _read(directory / 'response.json')
    return directory, response, None if response['snapshot'] is None else h.d.api._load_snapshot(response['snapshot'])


def log_reply(h, monkeypatch, content, *, status=200, complete=True, error=None):
    native = h.d.client.task_info
    def call(task, file):
        original = native(task, file)
        transport = {**original.transport, 'status': status, 'body_complete': complete,
            'received_body_bytes': len(content), 'headers': {'content-length': str(len(content))}}
        snapshot = replace(original, content=content, transport=transport)
        if error is not None:
            raise AcquisitionError(error, snapshot=snapshot, phase='http_response',
                retry_after=7, submission_outcome='unknown', diagnostic={'kind': 'controlled_partial'})
        return snapshot
    monkeypatch.setattr(h.d.client, 'task_info', call)


def consumer(h, *, limit=8, roles=('stdout', 'stderr')):
    native = ExecutionProgressProvider(h.store, run_id=h.monitor.run_id, directory=h.directory,
        resources={'selected-api': CONFIG}, api_execution=h.d.api,
        log_window_bytes=limit, log_roles=roles)
    progress = ProgressProvider(h.store, DurableExecutionStore(h.directory / 'durable'),
        run_id=h.monitor.run_id, job_provider=native)
    workflow = SimpleNamespace(run_id=h.monitor.run_id, store=h.store,
        tools=ToolRegistry(h.store), progress_provider=progress)
    workflow.progress_selection = lambda ctx: {'known_progress_refs': progress.received_progress_refs(ctx.episode_id)}
    services = WorkflowServices(workflow)
    return SimpleNamespace(native=native, progress=progress, monitor=MonitorEpisodes(services), services=services)


def run_monitor(h, c, context, key, arguments):
    result = asyncio.run(c.monitor.execute(context, 'progress.observe', arguments, key))
    if result['status'] in {'completed', 'partial'}:
        row = h.d.saved.journal.row('runtime_actions', context.episode_id, int(key.rsplit(':', 1)[1]))
        h.d.saved.journal.save('runtime_actions', {**row, 'result': canonical(result), 'credit': 0})
        c.progress.receive_outcome(context.episode_id, result, context.scope, key + ':own_progress')
        h.d.saved.receipts.receive(context.episode_id, result['record_refs'], kind='own_action',
            source_index=int(key.rsplit(':', 1)[1]))
    return result


def test_status_selects_original_task_and_native_units_without_first_mutation(h):
    key, _ = select(h, 'query_tasks')
    result = observe(h, 'query_tasks', key=key)
    assert result['state'] == 'running' and result['result_available'] is False
    assert result['measurements'] == result['logs'] == []
    assert result['native']['state_observed'] is True
    assert result['native']['native_timing'] == {
        'submit_time': '2026-10-24 12:00:00', 'start_time': '0000-00-00 00:00:00',
        'completed_time': None, 'elapsed_time': '01:02:03'}
    assert result['native']['timing_representation'] == {'timestamp_timezone': None, 'elapsed_time_unit': 'SQL_TIMEDIFF'}
    call, = h.d.client.calls
    assert call[0] == 'rpc' and call[1]['method'] == 'AppService.query_tasks' and call[1]['params'] == [['123']]
    directory, response, snapshot = retained(h, key)
    intent = _read(directory / 'intent.json')
    assert intent['operation_key'] == key and intent['name'] == 'progress.observe'
    assert intent['observation_context'] == h.monitor.as_record() and intent['target'] == h.target
    bound = intent['prepared']['bound_inputs']
    assert bound['resolved']['original_task'] == h.handoff['value']['original_task']
    assert bound['original_job_owner'] == h.handoff['value']['original_job_owner']
    assert response['failure'] is None and snapshot.request['rpc']['method'] == 'AppService.query_tasks'
    for name in ('native_record', 'parameters', 'task_records', 'text', 'data', 'bytes_base64'):
        assert name not in result['native']


def test_status_then_log_makes_one_different_call_without_restamping_state(h):
    previous = observe(h, 'query_tasks')
    key, _ = select(h, 'stdout')
    result = observe(h, 'stdout', key=key)
    assert result['state'] == 'unknown' and result['failure_code'] is None
    assert result['native']['state_observed'] is False and 'native_timing' not in result['native']
    assert 'execution_state_not_observed' in result['native']['qualification_codes']
    assert previous['state'] == 'running'
    assert [call[0] for call in h.d.client.calls] == ['rpc', 'task_info']
    assert h.d.client.calls[-1] == ('task_info', '123', 'stdout')
    assert base64.b64decode(result['logs'][0]['bytes_base64']) == b'native log\n'
    assert 'text' not in canonical(result['native']) and 'bytes_base64' not in canonical(result['native'])


@pytest.mark.parametrize('choice', [None, '', 'status', 'task_info', 'job_result_id', 1, ['stdout']])
def test_missing_or_wrong_native_choice_rejects_before_call(h, choice):
    key, _ = select(h, 'query_tasks')
    with pytest.raises((ValueError, ContractError), match='native_operation'):
        observe(h, choice, key=key)
    assert h.d.client.calls == []


@pytest.mark.parametrize('change', ['missing', 'dict', 'wrong_episode', 'assignment', 'run', 'unsaved'])
def test_context_is_actual_saved_monitor_not_caller_claim(h, change):
    key, _ = select(h, 'query_tasks')
    context = h.monitor
    if change == 'missing':
        context = None
    elif change == 'dict':
        context = context.as_record()
    elif change == 'wrong_episode':
        context = replace(context, episode_id='unrelated')
    elif change == 'assignment':
        context = replace(context, assignment=assignment('another-source'))
    elif change == 'run':
        context = replace(context, run_id='another-run')
    else:
        h.store.db.execute('DELETE FROM runtime_episodes WHERE episode_id=?', (context.episode_id,))
    with pytest.raises((ValueError, ContractError)):
        h.d.api.observe_target(h.target, operation_key=key, native_operation='query_tasks', observation_context=context)
    assert h.d.client.calls == []


@pytest.mark.parametrize('change', ['action', 'operation', 'index', 'extra_arg', 'expanded_fields', 'target', 'parent_assignment'])
def test_original_selection_target_and_commission_are_exact(h, change):
    key, arguments = select(h, 'query_tasks')
    target = deepcopy(h.target)
    if change == 'action':
        select(h, 'query_tasks', index=0, tool='api.bvbrc_appservice.status')
    elif change == 'operation':
        select(h, 'stderr', index=0)
    elif change == 'index':
        key += ':observe'
    elif change == 'extra_arg':
        select(h, 'query_tasks', index=0, arguments={**arguments, 'bound_inputs': {}})
    elif change == 'expanded_fields':
        select(h, 'query_tasks', index=0, fields=['invented'])
    elif change == 'target':
        target['execution_id'] = 'other-task'
    else:
        row = h.d.saved.journal.row('runtime_actions', h.d.saved.root.episode_id, 3)
        action = json.loads(row['action'])
        action['assignment']['target_handle'] = 'another-source'
        h.d.saved.journal.save('runtime_actions', {**row, 'action': canonical(action)})
    with pytest.raises((ValueError, ContractError)):
        h.d.api.observe_target(target, operation_key=key, native_operation='query_tasks', observation_context=h.monitor)
    assert h.d.client.calls == []


def test_handoff_visibility_or_inherited_prefix_without_typed_return_is_not_custody(h):
    h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (h.d.saved.root.episode_id,))
    assert h.target['handle'] in h.d.saved.receipts.known(h.monitor.episode_id)
    with pytest.raises(ValueError, match='handoff_not_possessed_before_commission'):
        observe(h, 'query_tasks')
    assert h.d.client.calls == []


def test_earlier_commission_returning_after_monitor_assignment_cannot_supply_original_input(h):
    parent = h.d.saved.root
    # Bind a new monitor before the parent receives its original launch return.
    h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (parent.episode_id,))
    h.store.db.execute('DELETE FROM runtime_record_receipts WHERE episode_id=?', (parent.episode_id,))
    monitor = h.d.saved.child(parent, 'monitor', assignment(h.target['handle']), 4)
    h.d.saved.admit(parent, h.d.launch, h.target['handle'])
    with pytest.raises(ValueError, match='handoff_not_received_before_commission'):
        observe(h, 'query_tasks', context=monitor)
    assert h.d.client.calls == []


def test_same_target_monitor_commissions_trace_to_original_possessing_parent(h):
    child = h.d.saved.child(h.monitor, 'monitor', assignment(h.target['handle']), 0)
    result = observe(h, 'query_tasks', context=child)
    assert result['state'] == 'running' and len(h.d.client.calls) == 1
    h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (h.d.saved.root.episode_id,))
    with pytest.raises(ValueError, match='handoff_not_possessed_before_commission'):
        observe(h, 'stderr', context=child)
    assert len(h.d.client.calls) == 1


def test_saved_response_replay_is_identical_and_never_calls_again(h, monkeypatch):
    key, _ = select(h, 'query_tasks')
    result = observe(h, 'query_tasks', key=key)
    monkeypatch.setattr(h.d.service, 'invoke', lambda *_: pytest.fail('replay invoked transport'))
    assert observe(h, 'query_tasks', key=key) == result
    directory, _, _ = retained(h, key)
    (directory / 'observation.json').unlink()
    assert observe(h, 'query_tasks', key=key) == result
    assert len(h.d.client.calls) == 1


def test_changed_arguments_cannot_reuse_saved_operation(h):
    key, _ = select(h, 'stdout')
    observe(h, 'stdout', key=key)
    select(h, 'stderr', index=0)
    with pytest.raises(ValueError, match='operation_key_reused_for_different_work'):
        observe(h, 'stderr', key=key)
    assert len(h.d.client.calls) == 1


def test_interrupted_issue_with_no_response_stays_unknown_without_retry(h, monkeypatch):
    def interrupt(rpc):
        h.d.client.calls.append(('rpc', rpc))
        raise KeyboardInterrupt()
    monkeypatch.setattr(h.d.client, 'rpc', interrupt)
    key, _ = select(h, 'query_tasks')
    with pytest.raises(KeyboardInterrupt):
        observe(h, 'query_tasks', key=key)
    result = observe(h, 'query_tasks', key=key)
    assert result['state'] == 'unknown' and result['failure_code'] == 'api_observation_response_unknown'
    assert observe(h, 'query_tasks', key=key) == result and len(h.d.client.calls) == 1


def test_interruption_after_response_recovers_from_retained_bytes(h, monkeypatch):
    decode = h.d.service.decode
    monkeypatch.setattr(h.d.service, 'decode', lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    key, _ = select(h, 'stderr')
    with pytest.raises(KeyboardInterrupt):
        observe(h, 'stderr', key=key)
    _, response, snapshot = retained(h, key)
    assert snapshot.content == b'native log\n' and response['failure'] is None
    monkeypatch.setattr(h.d.service, 'decode', decode)
    assert observe(h, 'stderr', key=key)['state'] == 'unknown'
    assert len(h.d.client.calls) == 1


@pytest.mark.parametrize('status,complete,error,logs', [
    (200, False, 'bvbrc_response_body_incomplete', True),
    (403, True, 'bvbrc_http_403', False), (404, True, None, False)])
def test_structured_partial_and_http_failures_retain_exact_snapshot(h, monkeypatch, status, complete, error, logs):
    content = b'retained\x00\xff partial\n'
    log_reply(h, monkeypatch, content, status=status, complete=complete, error=error)
    key, _ = select(h, 'stderr')
    result = observe(h, 'stderr', key=key)
    assert result['state'] == 'unknown' and bool(result['logs']) is logs
    _, response, snapshot = retained(h, key)
    assert snapshot.content == content and snapshot.transport['body_complete'] is complete
    assert snapshot.transport['status'] == status
    if error is not None:
        assert result['failure_code'] == error
        assert response['failure']['diagnostic'] == {'kind': 'controlled_partial'}
        assert response['failure']['retry_after'] == 7
    native_source = h.store.get(result['native']['source_ref'])
    assert native_source['provider'] == PROVIDER
    assert h.store.get_artifact(native_source['artifact_ref']) == content
    assert observe(h, 'stderr', key=key) == result and len(h.d.client.calls) == 1


@pytest.mark.parametrize('value', [{}, {'other': {'id': 'other', 'status': 'running'}},
    {'123': {'id': '123', 'app': 'different-app', 'status': 'completed'}}])
def test_status_failure_is_unknown_job_state_and_retains_native_reply(h, value):
    h.d.client.value = value
    key, _ = select(h, 'query_tasks')
    result = observe(h, 'query_tasks', key=key)
    assert result['state'] == 'unknown' and result['failure_code'] == 'original_task_mismatch'
    assert result['native']['state_observed'] is False and 'native_timing' not in result['native']
    _, _, snapshot = retained(h, key)
    assert json.loads(snapshot.content)['result'] == [value]


@pytest.mark.parametrize('content', [b'', b'prefix\nlast log\n', b'prefix\x00\xff'])
def test_real_monitor_consumer_bounds_window_preserves_raw_bytes_and_unknown_state(h, monkeypatch, content):
    log_reply(h, monkeypatch, content)
    c = consumer(h, limit=4)
    key, args = select(h, 'stdout')
    result = run_monitor(h, c, h.monitor, key, args)
    assert result['status'] == 'completed', result
    snapshot = result['result']
    assert snapshot['execution_status']['lifecycle_state'] is None
    assert snapshot['execution_status']['native']['logs'] == []
    assert 'bytes_base64' not in canonical(snapshot) and 'text' not in snapshot['execution_status']['native']['native']
    window, = snapshot['log_windows']
    assert h.store.get_artifact(window['artifact_ref']) == content[-4:]
    source = h.store.get(window['source_ref'])
    metadata = json.loads(h.store.get_artifact(source['request_ref']))
    assert metadata['original_start_byte'] == max(0, len(content) - 4)
    assert metadata['original_end_byte'] == metadata['observed_file_size'] == len(content)
    _, _, raw = retained(h, key)
    assert raw.content == content
    returned = asyncio.run(c.monitor.execute(h.monitor, 'progress.log',
        {'progress_ref': snapshot['progress_ref'], 'log_index': 0}, key + ':local-log'))
    if b'\xff' in content[-4:]:
        assert returned['status'] == 'invalid' and returned['feedback']['code'] == 'source_not_utf8_text'
    else:
        assert returned['status'] == 'completed' and returned['result']['text'] == content[-4:].decode()
    assert len(h.d.client.calls) == 1
    # The helper/provider did not manufacture a controller observation.
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('fields,roles', [(['execution_status'], ('stdout', 'stderr')), (list(FIELDS), ('stderr',))])
def test_unrequested_or_excluded_log_windows_stay_internal(h, fields, roles):
    c = consumer(h, roles=roles)
    key, args = select(h, 'stdout', fields=fields)
    result = run_monitor(h, c, h.monitor, key, args)
    assert result['status'] == 'completed'
    assert result['result']['log_windows'] == []
    assert 'bytes_base64' not in canonical(result['result'])
    _, _, raw = retained(h, key)
    assert raw.content == b'native log\n'


def test_provider_window_preserves_nonzero_native_offset(h, monkeypatch):
    c = consumer(h, limit=3)
    original = h.d.api.observe_target
    def shifted(*args, **kwargs):
        value = original(*args, **kwargs)
        value['logs'][0].update(offset=7, observed_size=18)
        return value
    monkeypatch.setattr(h.d.api, 'observe_target', shifted)
    key, args = select(h, 'stdout')
    result = run_monitor(h, c, h.monitor, key, args)
    assert result['status'] == 'completed', result
    window, = result['result']['log_windows']
    source = h.store.get(window['source_ref'])
    metadata = json.loads(h.store.get_artifact(source['request_ref']))
    assert metadata['original_start_byte'] == 15 and metadata['original_end_byte'] == 18
    assert metadata['observed_file_size'] == 18
    assert retained(h, key)[2].content == b'native log\n'


def test_consumer_publication_failure_recovers_native_capture_without_call(h, monkeypatch):
    c = consumer(h)
    validate = c.progress._validate_exposed
    monkeypatch.setattr(c.progress, '_validate_exposed', lambda *_: (_ for _ in ()).throw(ContractError('interrupted')))
    key, args = select(h, 'stdout')
    result = asyncio.run(c.monitor.execute(h.monitor, 'progress.observe', args, key))
    assert result['status'] == 'invalid' and len(h.d.client.calls) == 1
    monkeypatch.setattr(c.progress, '_validate_exposed', validate)
    result = run_monitor(h, c, h.monitor, key, args)
    assert result['status'] == 'completed' and len(h.d.client.calls) == 1


def test_log_window_policy_requires_positive_limit(h):
    with pytest.raises(ValueError, match='log_window_bytes_required'):
        consumer(h, limit=0)


def dependency_monitor(h, c, *, schema=None):
    """Expose the real submit relationship on its actual durable API owner."""
    spec = commission_spec(h.directory, key='original-api')
    producer = h.d.context
    spec.update(run_id=producer.run_id, parent={'episode_id': h.d.launch.episode_id,
        'goal_id': h.d.launch.request['goal']['goal_id'], 'path': plain(h.d.launch.path)},
        child={'episode_id': producer.episode_id, 'role': producer.role,
            'key': producer.path[-1][1], 'path': plain(producer.path),
            'request': plain(producer.request), 'scope': plain(producer.scope)})
    c.progress.durable_store.commission(spec)
    operation = h.handoff['value']['original_task']['submission_operation_key']
    relationship = c.native.dependency_from_outcome(producer, h.d.last_outcome, operation)
    c.progress.expose(spec['handle'], operation_key=operation + ':physical_target', dependencies=[relationship])
    parent = h.d.saved.child(h.d.saved.root, 'monitor', assignment(spec['handle']), 4, schema=schema)
    key, args = select(h, None, context=parent, arguments={'requested_fields': ['dependencies']})
    result = run_monitor(h, c, parent, key, args)
    assert result['status'] == 'completed', result
    assert result['record_refs'] == [] and result['result']['dependencies'] == [relationship]
    return parent, result


def test_different_dependency_uses_actual_prior_completed_progress_and_submit_relation(h):
    c = consumer(h)
    parent, result = dependency_monitor(h, c)
    child = h.d.saved.child(parent, 'monitor', assignment(h.target['handle']), 1)
    assert observe(h, 'query_tasks', context=child)['state'] == 'running'
    assert len(h.d.client.calls) == 1
    # The proof came from the delivered specific observation, not a copied
    # handoff reference in the parent's scientific record receipt ledger.
    assert h.store.db.execute('SELECT 1 FROM runtime_record_receipts WHERE episode_id=? AND record_ref=?',
        (parent.episode_id, h.target['handle'])).fetchone() is None
    assert result['result']['dependencies'][0]['relation_ref'].startswith('source_')


def test_dependency_visibility_without_received_prior_observation_is_not_custody(h):
    c = consumer(h)
    parent, _ = dependency_monitor(h, c)
    h.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE episode_id=? AND decision_index=0',
        (parent.episode_id,))
    child = h.d.saved.child(parent, 'monitor', assignment(h.target['handle']), 1)
    assert c.services.dependencies(parent.assignment['target_handle'], parent.scope)
    with pytest.raises(ValueError, match='handoff_not_possessed_before_commission'):
        observe(h, 'query_tasks', context=child)
    assert h.d.client.calls == []


def test_different_dependency_rejects_unrelated_relation_source(h):
    c = consumer(h)
    parent, result = dependency_monitor(h, c)
    snapshot = result['result']
    source = h.store._caller_source({'unrelated': True}, 'unrelated')
    snapshot['dependencies'][0]['relation_ref'] = source['id']
    h.store.db.execute('UPDATE runtime_progress_observations SET snapshot=? WHERE progress_ref=?',
        (canonical(snapshot), snapshot['progress_ref']))
    h.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=0',
        (canonical(result), parent.episode_id))
    child = h.d.saved.child(parent, 'monitor', assignment(h.target['handle']), 1)
    with pytest.raises(ValueError, match='dependency_source_conflict'):
        observe(h, 'query_tasks', context=child)
    assert h.d.client.calls == []


@pytest.mark.parametrize('changed', ['snapshot', 'selection_signature'])
def test_dependency_requires_original_c8_snapshot_and_selection_identity(h, changed):
    c = consumer(h)
    parent, result = dependency_monitor(h, c)
    if changed == 'snapshot':
        snapshot = result['result']
        snapshot['result_available'] = not snapshot['result_available']
        h.store.db.execute('UPDATE runtime_progress_observations SET snapshot=? WHERE progress_ref=?',
            (canonical(snapshot), snapshot['progress_ref']))
        h.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=0',
            (canonical(result), parent.episode_id))
    else:
        h.store.db.execute('UPDATE runtime_progress_selections SET signature=? WHERE operation_key=?',
            ('different-signature', f'{parent.run_id}:{parent.episode_id}:0'))
    child = h.d.saved.child(parent, 'monitor', assignment(h.target['handle']), 1)
    with pytest.raises(ValueError, match='dependency_(observation_identity|selection)_conflict'):
        observe(h, 'query_tasks', context=child)
    assert h.d.client.calls == []


@pytest.mark.parametrize('late', [False, True])
def test_requested_typed_dependency_return_preserves_original_receiving_cutoff(h, late):
    c = consumer(h)
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['handles'],
        'properties': {'handles': c.monitor.fact_sources('monitor')['monitoring_dependency_handles']['report_schema']}}
    parent, _ = dependency_monitor(h, c, schema=schema)
    root = h.d.saved.root
    h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (root.episode_id,))
    h.store.db.execute('DELETE FROM runtime_record_receipts WHERE episode_id=?', (root.episode_id,))

    def receive():
        form = {'handles': [h.target['handle']]}
        h.d.saved.journal.save('runtime_forms', {'episode_id': parent.episode_id,
            'facts': canonical({'monitoring_dependency_handles': form['handles']}), 'form': canonical(form)})
        h.d.saved.journal.save('runtime_report_attempts', {'parent_episode_id': root.episode_id,
            'decision_index': 4, 'delivery_ref': 'delivery_dependency', 'child_episode_id': parent.episode_id,
            'contract': canonical(parent.request['report_contract']), 'form': canonical(form), 'failure': None})
        h.d.saved.receipts.receive(root.episode_id, form['handles'], kind='child_form', source_index=4)

    if not late:
        receive()
    child = h.d.saved.child(root, 'monitor', assignment(h.target['handle']), 5)
    if late:
        receive()
        with pytest.raises(ValueError, match='handoff_not_received_before_commission'):
            observe(h, 'query_tasks', context=child)
        assert h.d.client.calls == []
    else:
        assert observe(h, 'query_tasks', context=child)['state'] == 'running'
        assert len(h.d.client.calls) == 1


def test_native_transport_failure_without_snapshot_replays_exact_failure(h, monkeypatch):
    def fail(rpc):
        h.d.client.calls.append(('rpc', rpc))
        raise AcquisitionError('bvbrc_native_transport_failed', phase='http_request',
            diagnostic={'exception_type': 'TimeoutError'}, submission_outcome='unknown')
    monkeypatch.setattr(h.d.client, 'rpc', fail)
    key, _ = select(h, 'query_tasks')
    result = observe(h, 'query_tasks', key=key)
    assert result['state'] == 'unknown' and result['failure_code'] == 'bvbrc_native_transport_failed'
    _, response, snapshot = retained(h, key)
    assert snapshot is None and response['failure']['diagnostic'] == {'exception_type': 'TimeoutError'}
    assert observe(h, 'query_tasks', key=key) == result and len(h.d.client.calls) == 1


def test_incomplete_status_cannot_report_running_even_when_prefix_is_parseable(h, monkeypatch):
    rpc = h.d.client.rpc
    def partial(command):
        snapshot = rpc(command)
        snapshot = replace(snapshot, transport={**snapshot.transport, 'body_complete': False})
        raise AcquisitionError('bvbrc_response_body_incomplete', snapshot=snapshot, phase='http_response')
    monkeypatch.setattr(h.d.client, 'rpc', partial)
    result = observe(h, 'query_tasks')
    assert result['state'] == 'unknown' and result['native']['state_observed'] is False
    assert result['failure_code'] == 'bvbrc_response_body_incomplete'


def test_other_task_log_response_is_retained_without_projecting_its_bytes(h, monkeypatch):
    task_info = h.d.client.task_info
    def wrong(task, file):
        return task_info('different-task', file)
    monkeypatch.setattr(h.d.client, 'task_info', wrong)
    key, _ = select(h, 'stdout')
    result = observe(h, 'stdout', key=key)
    assert result['state'] == 'unknown' and result['logs'] == result['outputs'] == []
    assert result['failure_code'] == 'native_response_invalid'
    assert retained(h, key)[2].content == b'native log\n'


def test_interruption_before_issue_stays_unissued_and_does_not_start_on_recovery(h, monkeypatch):
    from gene_annotation_episode import bvbrc_appservice_monitor as module
    immutable = module._immutable
    def stop_before_issue(path, value):
        if path.name == 'issued.json':
            raise KeyboardInterrupt()
        return immutable(path, value)
    monkeypatch.setattr(module, '_immutable', stop_before_issue)
    key, _ = select(h, 'query_tasks')
    with pytest.raises(KeyboardInterrupt):
        observe(h, 'query_tasks', key=key)
    monkeypatch.setattr(module, '_immutable', immutable)
    result = observe(h, 'query_tasks', key=key)
    assert result['state'] == 'unknown' and result['failure_code'] == 'api_observation_not_issued'
    assert h.d.client.calls == []
    assert not (retained(h, key)[0] / 'issued.json').exists()


def test_interruption_carrying_actual_response_retains_it_exactly(h, monkeypatch):
    rpc = h.d.client.rpc
    def stop_with_response(command):
        snapshot = rpc(command)
        error = KeyboardInterrupt()
        error.snapshot = snapshot
        raise error
    monkeypatch.setattr(h.d.client, 'rpc', stop_with_response)
    key, _ = select(h, 'query_tasks')
    with pytest.raises(KeyboardInterrupt):
        observe(h, 'query_tasks', key=key)
    assert retained(h, key)[1]['failure'] is None
    assert observe(h, 'query_tasks', key=key)['state'] == 'running'
    assert len(h.d.client.calls) == 1


def test_reopened_production_executor_recovers_same_original_response(h, monkeypatch):
    from gene_annotation_episode.api_service_execution import APIServiceExecution
    key, _ = select(h, 'stdout')
    original = observe(h, 'stdout', key=key)
    h.store.db.commit()
    with Store(h.directory / 'state') as reopened:
        api = APIServiceExecution(reopened, run_id=h.monitor.run_id, directory=h.directory,
            configuration={'selected-api': CONFIG}, tool_registry=SimpleNamespace(store=reopened, clients={}),
            handoff_unit=2, acquired_record_unit=3)
        monkeypatch.setattr(api.services['selected-api'], 'invoke', lambda *_: pytest.fail('reopen reissued request'))
        context = api.appservice.custody.context(h.monitor.episode_id)
        assert api.observe_target(h.target, operation_key=key, native_operation='stdout', observation_context=context) == original


def test_unrequested_raw_native_fields_do_not_escape_status_projection(h):
    h.d.client.value['123'].update(text='arbitrary log text', bytes_base64='c2VjcmV0',
        embedded={'large': 'raw native details'})
    key, _ = select(h, 'query_tasks')
    result = observe(h, 'query_tasks', key=key)
    assert 'arbitrary log text' not in canonical(result) and 'c2VjcmV0' not in canonical(result)
    assert 'raw native details' not in canonical(result)
    assert json.loads(retained(h, key)[2].content)['result'][0]['123']['text'] == 'arbitrary log text'


def test_repeated_status_observations_earn_no_duplicate_information(h):
    from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
    c = consumer(h)
    snapshots = []
    for _ in range(2):
        key, args = select(h, 'query_tasks')
        outcome = run_monitor(h, c, h.monitor, key, args)
        snapshots.append(outcome['result']['progress_ref'])
    credit = ProgressInformationCredit(c.progress, information_unit=1)
    selection = {'run_id': h.monitor.run_id, 'episode_id': h.monitor.episode_id,
        'known_progress_refs': snapshots, 'initial_progress_refs': []}
    result = credit(h.monitor, selection)
    assert result['newly_informative_received_snapshot_count'] == 1 and result['credit'] == 1
    assert len(h.d.client.calls) == 2


def test_saved_status_only_selection_never_emits_readable_log_rows(h):
    key, _ = select(h, 'stdout', fields=['execution_status'])
    result = observe(h, 'stdout', key=key)
    assert result['logs'] == result['outputs'] == []
    assert retained(h, key)[2].content == b'native log\n'


def test_provider_cannot_expand_fields_beyond_actual_saved_native_selection(h):
    c = consumer(h)
    key, _ = select(h, 'stdout', fields=['execution_status'])
    with pytest.raises(ContractError, match='selected_fields_conflict'):
        c.native.observe(h.target['handle'], ['execution_status', 'log_windows'], h.monitor.scope,
            operation_key=key, native_operation='stdout', observation_context=h.monitor)
    assert h.d.client.calls == []
    assert not (h.d.api.directory / 'observations' / digest(key)).exists()


@pytest.mark.parametrize('status,expected,observed', [(None, 'unknown', False),
    ('unrecognized', 'unknown', True), ('failed', 'failed', True), ('completed', 'completed', True)])
def test_query_preserves_missing_unknown_and_terminal_native_states(h, status, expected, observed):
    h.d.client.value['123']['status'] = status
    result = observe(h, 'query_tasks')
    assert result['state'] == expected and result['native']['state_observed'] is observed
    assert result['native']['native_status'] == status
    assert result['native']['native_timing']['elapsed_time'] == '01:02:03'
    assert result['result_available'] is False
