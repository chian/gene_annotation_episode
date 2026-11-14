"""Actual Homology task boundaries compared with pinned original own bodies."""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace
from unittest.mock import patch

from .homology_direction_checks import actual, module, raw_rows

ROLES = ('job_launch', 'job_monitor', 'job_results')
HOMES = tuple((parent, role) for parent in ('annotation', 'improvement') for role in ROLES)


def retained(name):
    directory = Path(__file__).parent / 'fixtures' / 'homology_boundary_original'
    row = json.loads((directory / 'sources.json').read_text())['sources'][name]
    source = (directory / row['filename']).read_bytes()
    assert hashlib.sha256(source).hexdigest() == row['sha256']
    return source, row, directory / row['filename']


def original_class(value, kind):
    key = value.parent_home + '/' + value.binding.binding_path.split('/')[-1] + '/' + kind
    source, row, filename = retained(key)
    reference = ModuleType('retained_original_homology_' + kind.replace('.', '_'))
    reference.__file__ = str(filename)
    reference.__package__ = type(value.task).__module__.rsplit('.', 1)[0]
    exec(compile(source, str(filename), 'exec'), reference.__dict__)
    return getattr(reference, row['class'])


def original_controller():
    source, _, filename = retained('runtime.controller')
    namespace = {}
    exec(compile(source, str(filename), 'exec'), namespace)
    function = namespace['controller']
    # Original code reads live runtime globals, including supplied wrapper hooks.
    return FunctionType(function.__code__, vars(module('runtime')), function.__name__, function.__defaults__)


@contextmanager
def commissioned(directory, parent, role, *, persistent_rejections=False):
    assert type(persistent_rejections) is bool
    order = module('inprocess_replay').VERSION if persistent_rejections else None
    with actual(directory, parent=parent, role=role, receipts=True, inprocess_completion_order=order) as value:
        value.task = value.flow.selected(value.source, deepcopy(value.selection), 0).child.source
        assert type(value.task) is value.binding.decision_source_type
        assert value.flow.job_episode_for_path(value.task.path) is value.binding
        assert value.flow.specialist(value.task) is None
        assert value.flow.is_job_source(value.task)
        assert not value.flow.is_scientific_source(value.task)
        assert not value.flow.permits_common_action(value.task, 'reason')
        yield value


class BoundaryReached(Exception):
    pass


def task_context(value, *, original, pending):
    task, flow = value.task, value.flow
    observed = []
    boundary = BoundaryReached('provider boundary reached')
    events = []
    real_schema = flow.action_schema
    real_scientific = flow.is_scientific_source

    def scientific(source):
        assert source is task
        events.append('scientific_predicate')
        return real_scientific(source)

    def schema(source):
        assert source is task
        events.append('action_schema')
        return real_schema(source)

    def inputs(data, *, reports):
        events.append('model_inputs')
        assert tuple(reports) == ()
        return data

    async def call(context, schema):
        events.append('call')
        observed.append((deepcopy(context), deepcopy(schema)))
        raise boundary

    view = SimpleNamespace(units_consumed=0, child_reports=(),
        controller_state={'credit': 0.0}, model_inputs=inputs)
    selected = original_class(value, 'task.py').next if original else type(task).next
    with patch.object(flow, 'pending_work', return_value=deepcopy(pending)), \
            patch.object(flow, 'action_schema', side_effect=schema), \
            patch.object(flow, 'is_scientific_source', side_effect=scientific), \
            patch.object(task, 'call', side_effect=call):
        try:
            asyncio.run(selected(task, view))
        except BoundaryReached as error:
            assert error is boundary
        else:
            raise AssertionError('task did not reach its original provider boundary')
    assert len(observed) == 1 and events[-1] == 'call'
    assert events.index('model_inputs') < events.index('action_schema')
    assert events.index('scientific_predicate') < events.index('action_schema')
    return {'context': observed[0][0], 'schema': observed[0][1], 'events': events}


def compare_task_context(value):
    pending = value.flow.pending_work(value.task)
    before_rows = raw_rows(value.flow)
    before = task_context(value, original=True, pending=pending)
    after = task_context(value, original=False, pending=pending)
    assert after == before and raw_rows(value.flow) == before_rows
    assert before['context']['current_credit'] == value.flow.source_credit_view(value.task)['credit']
    return before


class RollbackObservation(Exception):
    pass


def decision_observation(value, case, *, original, context, schema):
    task, flow = value.task, value.flow
    assert case in {'fresh', 'provider_error', 'saved_replay'}
    task_before = dict(task.__dict__)
    before_rows = raw_rows(flow)
    events = []
    failure = ValueError('controlled_original_homology_provider_failure')
    response = {'selection': {'kind': 'tool', 'tool': 'homology.sample', 'arguments': {}},
        'report_update': {'state': 'unresolved'}}
    selected = original_class(value, 'decision_delivery.py').call if original else type(task).call
    observation = None

    class Provider:
        replay_forbidden = False

        def has_session(self, episode_id, purpose):
            assert episode_id == task.episode_id and purpose == 'REASONING'
            events.append('has_session')
            return False

        async def complete(self, episode_id, purpose, instructions, supplied, output_schema):
            assert not self.replay_forbidden
            assert episode_id == task.episode_id and purpose == 'REASONING'
            events.append({'provider': {'instructions': instructions,
                'context': deepcopy(supplied), 'schema': deepcopy(output_schema)}})
            if case == 'provider_error':
                raise failure
            return deepcopy(response)

    provider = Provider()
    try:
        with flow.store.transaction(), patch.object(flow, 'provider', provider):
            try:
                outcome = asyncio.run(selected(task, deepcopy(context), deepcopy(schema)))
            except ValueError as error:
                assert case == 'provider_error' and error is failure
                outcome = {'raised': 'ValueError', 'same_exception': True, 'message': str(error)}
            else:
                assert case != 'provider_error' and outcome[0] == response and outcome[1] == 0
            row = flow.journal.row('runtime_model_calls', task.episode_id, 0)
            assert row is not None and row['purpose'] == 'decision'
            recorded = {'request': json.loads(row['request']),
                'response': None if row['response'] is None else json.loads(row['response'])}
            assert recorded['response'] == (None if case == 'provider_error' else response)
            first_events = deepcopy(events)
            replay = None
            if case == 'saved_replay':
                task.calls = 0
                provider.replay_forbidden = True
                events.clear()
                replay = asyncio.run(selected(task, {'ignored': True}, {'ignored': True}))
                assert replay == outcome and events == []
            observation = {'outcome': outcome, 'recorded': recorded,
                'events': first_events, 'replay': replay}
            raise RollbackObservation
    except RollbackObservation:
        pass
    finally:
        task.__dict__.clear()
        task.__dict__.update(task_before)
    assert raw_rows(flow) == before_rows
    assert flow.journal.row('runtime_model_calls', task.episode_id, 0) is None
    assert sum(isinstance(event, dict) and 'provider' in event for event in observation['events']) == 1
    return observation


def compare_decision(value, case):
    pending = value.flow.pending_work(value.task)
    inputs = task_context(value, original=True, pending=pending)
    before = decision_observation(value, case, original=True,
        context=inputs['context'], schema=inputs['schema'])
    after = decision_observation(value, case, original=False,
        context=inputs['context'], schema=inputs['schema'])
    assert after == before


def compare_rejected_fresh_reason(value):
    task, flow = value.task, value.flow
    assert flow.execution_binding is None
    assert type(flow.inprocess_replay) is module('inprocess_replay').InProcessReplay
    assert flow.inprocess_completion_order == module('inprocess_replay').VERSION
    inputs = task_context(value, original=True, pending=flow.pending_work(task))
    response = {'selection': {'kind': 'reason', 'commit': {'interpretation_accounts': []}},
        'report_update': {'state': 'unresolved'}}
    observations = []
    before_rows = raw_rows(flow)
    original_call = original_class(value, 'decision_delivery.py').call
    for original in (True, False):
        saved = dict(task.__dict__)
        selected = original_class(value, 'task.py').apply_response if original else type(task).apply_response
        provider_calls = []

        class Provider:
            async def complete(self, episode_id, purpose, instructions, context, schema):
                assert episode_id == task.episode_id and purpose == 'REASONING'
                provider_calls.append((episode_id, purpose))
                return deepcopy(response)

        try:
            with flow.store.transaction(), patch.object(flow, 'provider', Provider()):
                task.calls = 12
                delivered, index, context, schema = asyncio.run(original_call(
                    task, deepcopy(inputs['context']), deepcopy(inputs['schema'])))
                assert index == 12 and delivered == response and len(provider_calls) == 1
                call = flow.journal.row('runtime_model_calls', task.episode_id, index)
                assert call['purpose'] == 'decision' and json.loads(call['response']) == response
                result = selected(task, deepcopy(delivered), index, context, schema)
                assert result is None and task.feedback['status'] == 'invalid'
                assert flow.journal.row('runtime_actions', task.episode_id, 12) is None
                rejected = flow._decision_rejection(task, 12, include_feedback=True)
                assert rejected is not None and rejected['state'] == 'rejected'
                observations.append({'feedback': deepcopy(task.feedback), 'rejection': rejected})
                raise RollbackObservation
        except RollbackObservation:
            pass
        finally:
            task.__dict__.clear()
            task.__dict__.update(saved)
        assert raw_rows(flow) == before_rows
        assert flow.journal.row('runtime_model_calls', task.episode_id, 12) is None
        assert flow._decision_rejection(task, 12, include_feedback=True) is None
    assert observations[0] == observations[1]


def controller_observation(value, case, *, original):
    flow, task, runtime = value.flow, value.task, module('runtime')
    assert case in {'plain', 'original_task', 'capture', 'factory_error'}
    calls = []
    captures = []
    wraps = []
    error = ValueError('original supplied controller factory failed')
    supplied = SimpleNamespace(epoch='original-controlled-epoch')
    real_wrapper = runtime.ExecutionContextController

    def factory(path, credit, **kwargs):
        bound = kwargs.get('context')
        calls.append({'path': path, 'credit': credit, 'kwargs': {
            **kwargs, **({'context': bound.as_record()} if bound is not None else {})},
            'received_record_refs': None if bound is None else tuple(bound.received_record_refs)})
        if case == 'factory_error':
            raise error
        return supplied

    factory.requires_original_task = case in {'original_task', 'capture'}

    def wrapper(controller, journal, episode_id, **kwargs):
        assert controller is supplied and journal is flow.journal and episode_id == task.episode_id
        wraps.append({'include_native': kwargs['include_native'],
            'has_capture': kwargs['capture_current_completion'] is not None})
        return real_wrapper(controller, journal, episode_id, **kwargs)

    def capture(episode_id, **kwargs):
        captures.append((episode_id, kwargs))
        return 'original-capture-return'

    with patch.object(flow, 'controller_factory', factory), \
            patch.object(flow, 'has_native_estimation', return_value=case == 'capture'), \
            patch.object(flow, 'completed_action_inputs_version', 'controlled' if case == 'capture' else None), \
            patch.object(flow, 'capture_completion_evidence', side_effect=capture), \
            patch.object(runtime, 'ExecutionContextController', side_effect=wrapper):
        selected = original_controller() if original else runtime.Workflow.controller
        try:
            result = selected(flow, task.path)
        except ValueError as caught:
            assert case == 'factory_error' and caught is error
            outcome = {'same_error': True, 'message': str(caught)}
        else:
            assert case != 'factory_error' and type(result) is real_wrapper
            assert result.controller is supplied and result.episode_id == task.episode_id
            outcome = {'epoch': result.epoch, 'include_native': result.include_native}
            if case == 'capture':
                unit = object()
                credit = object()
                assert result.capture_current_completion(unit, 7, credit) == 'original-capture-return'
                assert captures == [(task.episode_id, {'original_decision_index': 7,
                    'unit_ref': unit, 'controller_input': credit})]
            else:
                assert result.capture_current_completion is None
    assert len(calls) == 1
    assert calls[0]['credit'] == flow.journal.row('runtime_episodes', task.episode_id)['initial_credit']
    if factory.requires_original_task:
        assert calls[0]['kwargs']['task_key'] is None and calls[0]['kwargs']['credit_definition'] is None
        assert calls[0]['kwargs']['context']['role'] == value.role
        assert calls[0]['received_record_refs'] == tuple(flow.receipts.known(task.episode_id))
    else:
        assert calls[0]['kwargs'] == {}
    return {'outcome': outcome, 'calls': calls, 'wrapper': wraps, 'capture_count': len(captures)}


def compare_controller(value, case):
    before = controller_observation(value, case, original=True)
    after = controller_observation(value, case, original=False)
    assert after == before


def assert_private_yield_owner(value):
    callback = getattr(value.binding, 'yield_controller', None)
    assert callable(callback), 'missing private Homology yield owner'
    assert callback.__module__ == type(value.binding).__module__.rsplit('.', 1)[0] + '.yield_estimator'
    assert callback.__name__ == 'yield_controller'
