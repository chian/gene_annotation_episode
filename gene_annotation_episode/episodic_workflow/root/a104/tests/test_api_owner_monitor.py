"""Actual Launch-exported progress over original controlled API handoffs.

The HTTP response fixture is the existing required own-A104 fixture. Real
Store/Journal/action/receipt/target qualification and saved progress operations
remain in use. This helper adds no API-bearing HPC commission or native job.
"""
import asyncio
import json
import os
from copy import deepcopy
from types import SimpleNamespace

import pytest

from .api_cases import Case, HOMES, canonical, module, rows
from .api_owner_progress import MonitorCase


@pytest.fixture(params=HOMES, ids=HOMES)
def monitored(request, tmp_path):
    value = Case(tmp_path, request.param)
    try:
        result = value.act('api.uniprot.record')
        assert result['status'] == 'completed'
        value.handoff = result['result']['handoff_ref']
        value.launch_home = value.home.removesuffix('/api_job_execution')
        value.launch = module(value.launch_home + '/episode').ExecutionEpisode(value.services, **value.options)
        value.progress = value.launch.job_progress_provider
        assert value.progress.targets.api_execution is value.launch.api_execution
        yield value
    finally:
        value.close()


def test_actual_launch_progress_uses_retained_response_and_replays(monitored, record_property):
    value = monitored; progress = value.progress
    before_calls = deepcopy(value.client.calls)
    target = progress.targets.read_target(value.handoff, value.scope)
    assert target['resource_kind'] == 'api' and target['origin_episode_id'] == value.episode_id
    fields = ['execution_status']
    key = value.run_id + ':controlled-launch-monitor:0'
    first = progress.observe(value.handoff, fields, value.scope, operation_key=key)
    assert value.client.calls == before_calls
    captured = rows(value.store)
    assert progress.observe(value.handoff, fields, value.scope, operation_key=key) == first
    assert rows(value.store) == captured and value.client.calls == before_calls
    assert progress.latest_saved_observation(value.handoff, value.scope) is not None
    if os.environ.get('A104_API_OWNER_PHASE') == 'connected':
        observer = progress.targets.api_observer
        assert observer.reader is value.launch.api_execution
        family = value.launch_home.removesuffix('execution_job_submission')
        assert type(observer).__module__ == module(family + 'execution_progress_assessment/api_observer').__name__
        assert not hasattr(value.launch.api_execution, 'observe_target')
        assert not hasattr(value.launch.api_execution, 'execute')
    record_property('original_launch_progress', json.dumps(canonical({
        'launch_home': value.launch_home, 'target': target, 'selection': {'handle': value.handoff,
            'fields': fields, 'scope': value.scope, 'operation_key': key},
        'returned': first, 'transport_calls': value.client.calls,
        'operation_rows': captured['runtime_execution_progress_operations'],
        'custody_rows': captured['runtime_execution_progress_custody'],
        'snapshot_rows': captured['runtime_execution_progress_snapshots'],
        'same_key_all_rows_unchanged': True, 'controlled_http_response': True}), sort_keys=True))
    # Exercise the actual monitor action with an explicitly configured custom
    # service. Its authentic saved snapshot is obtained first; the callback
    # selection itself must not be replaced by the new default APIObserver.
    custom = MonitorCase(value.directory / 'configured-monitor-service', value.home)
    try:
        snapshot = custom.progress.observe(custom.handoff, fields, custom.scope,
            permitted_committed_record_types=[], operation_key=custom.run_id + ':custom-monitor-input:0')
        visits = []
        def configured(handle, requested, scope, **operands):
            visits.append(canonical({'handle': handle, 'requested': requested, 'scope': scope, 'operands': operands}))
            return deepcopy(snapshot)
        custom.services.observe_progress = configured
        transport = deepcopy(custom.api.client.calls)
        actual = asyncio.run(custom.task.task.execute(custom.chosen, 0)).as_record()
        assert visits == [{'handle': custom.handoff, 'requested': fields, 'scope': custom.scope,
            'operands': {'permitted_committed_record_types': [], 'operation_key': custom.key}}]
        assert custom.api.client.calls == transport
        assert len(custom.task.executions) == len(custom.task.observations) == len(custom.task.projections) == 1
        assert custom.task.task.last_outcome['result'] == snapshot
        record_property('original_configured_monitor_service', json.dumps(canonical({'visits': visits,
            'returned_payload': custom.task.task.last_outcome, 'controller_input': actual,
            'credit_view': custom.task.projections[0], 'transport_calls': transport,
            'original_custom_service_precedence': True}), sort_keys=True))
    finally:
        custom.close()


def test_actual_launch_target_qualification_precedes_observer(monitored, monkeypatch, record_property):
    value = monitored; target = value.progress.targets.read_target(value.handoff, value.scope)
    reader = value.progress.targets
    dispatch = getattr(reader, 'api_observer', None) or reader.api_execution
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError('invalid_target_reached_native_observation')
    monkeypatch.setattr(dispatch, 'observe_target', forbidden)
    changed = deepcopy(target); changed['execution_id'] = 'different-original-execution'
    before = rows(value.store)
    with pytest.raises((ValueError, module('domain').ContractError)) as caught:
        reader.observe_target(changed, operation_key=value.run_id + ':target-qualification:0')
    assert calls == [] and rows(value.store) == before
    record_property('original_target_denial', json.dumps({'type': type(caught.value).__module__ + '.' + type(caught.value).__qualname__,
        'message': str(caught.value), 'observer_calls': 0, 'all_rows_unchanged': True}, sort_keys=True))


def test_optional_external_observer_preserves_target_and_call_operands(monitored, record_property):
    # The optional port exists only after the actual split. The same target
    # first passes the original reader's real qualification path.
    if os.environ.get('A104_API_OWNER_PHASE') != 'connected':
        pytest.skip('new mechanical optional port; original behavior captured by the two unchanged boundaries')
    value = monitored; target = value.progress.targets.read_target(value.handoff, value.scope)
    original_observer = value.progress.targets.api_observer
    observed = original_observer.observe_target(target, operation_key=value.run_id + ':original-observer:0')
    visits = []
    def custom(actual, **operands):
        visits.append({'target': deepcopy(actual), 'operands': deepcopy(operands)})
        return deepcopy(observed)
    reader = module('execution_progress').ExecutionTargetReader(value.store, run_id=value.run_id,
        directory=value.options['directory'], resources=value.options['resources'],
        api_execution=value.launch.api_execution, api_observer=SimpleNamespace(observe_target=custom))
    key = value.run_id + ':custom-observer:0'
    before = rows(value.store)
    returned = reader.observe_target(target, operation_key=key)
    assert returned == observed
    assert visits == [{'target': target, 'operands': {'operation_key': key}}]
    assert rows(value.store) == before
    record_property('explicit_observer_port', json.dumps(canonical({'returned': returned, 'visits': visits,
        'original_qualification_retained': True, 'configured_reader_identity_preserved': reader.api_execution is value.launch.api_execution}), sort_keys=True))
