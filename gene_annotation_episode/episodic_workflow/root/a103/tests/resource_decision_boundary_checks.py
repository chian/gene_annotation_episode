"""Compare actual private Resource decisions with retained original own bodies."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from .resource_task_checks import fixture, make_task, own


def original_class(role):
    directory = Path(__file__).parent / 'fixtures' / 'resource_task_decision_original'
    manifest = json.loads((directory / 'sources.json').read_text())
    row = manifest['roles'][role]
    source = (directory / row['filename']).read_bytes()
    assert hashlib.sha256(source).hexdigest() == row['sha256']
    module = ModuleType('retained_original_a103_resource_decision_' + role)
    module.__file__ = str(directory / row['filename'])
    # Exact retained original private source, with its original runtime imports.
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module.ResourceTaskDecision


def decision_observation(value, case, *, original):
    assert case in {'fresh', 'provider_error', 'saved_replay'}
    task = make_task(value)
    if original:
        reference = object.__new__(original_class(value.role))
        reference.__dict__.update(task.__dict__)
        task = reference
    events = []
    failure = ValueError('controlled_resource_provider_failure')
    response = {'selection': {'kind': 'reason', 'evidence': []}, 'report_update': {}}
    supplied_context = {
        'goal': {'objective': 'Preserve the actual Resource decision boundary'},
        'scope': deepcopy(value.scope), 'working_state': {'records': []},
        'visible_record_refs': [], 'current_credit': 0.0, 'role': value.role,
        'assignment': deepcopy(value.assignment), 'pending_work': [],
        '_completed_work_axis_results': {'tool_attachments': []},
    }
    schema = {'type': 'object', 'properties': {
        'selection': {'type': 'object'}, 'report_update': {'type': 'object'}},
        'required': ['selection', 'report_update'], 'additionalProperties': False}

    def port(name, result):
        def supplied(*args, **kwargs):
            events.append(name)
            return deepcopy(result)
        return supplied

    class Provider:
        replay_forbidden = False

        def has_session(self, episode_id, purpose):
            assert episode_id == task.episode_id and purpose == 'REASONING'
            events.append('has_session')
            return False

        async def complete(self, episode_id, purpose, instructions, context, output_schema):
            assert not self.replay_forbidden, 'saved decision redispatched provider'
            assert episode_id == task.episode_id and purpose == 'REASONING'
            assert instructions == 'Controlled original Resource instructions'
            events.append({'provider': {'episode_id': episode_id, 'purpose': purpose,
                'instructions': instructions, 'context': deepcopy(context),
                'output_schema': deepcopy(output_schema)}})
            if case == 'provider_error':
                raise failure
            return deepcopy(response)

    provider = Provider()
    host = SimpleNamespace(
        journal=value.journal, store=value.store, provider=provider,
        contract_information_profile=port('profile', None), decision_protocol=None,
        resource_context=port('resource_context', {'selected': value.role}),
        shared_information_context=port('shared_context', {'received': []}),
        launch_instructions=SimpleNamespace(
            context=port('instruction_library', {'version': 'controlled'}),
            materialize=port('materialize', None)),
        available_child_roles=port('child_roles', ()),
        episode_bindings=SimpleNamespace(initial_decision_context=port('initial_context', {'original_binding_input': True})),
        binding_context=lambda source: value.context,
        pending_work=port('pending_work', []), execution_expectations=None,
        resource_estimator=None, native_estimation_context=port('native_estimation', None),
        native_event_information=SimpleNamespace(read=port('native_events', {'targets': []})),
        permits_common_action=lambda source, kind: kind in value.binding.permitted_common_actions(value.context),
        waiting_support=port('waiting_support', {'original': True}),
        freeze_literature_numerical_contracts=port('numerical_contracts', None),
        receipts=None, history_preview=port('history_preview', {'original': []}),
        services=SimpleNamespace(instructions=port('instructions', 'Controlled original Resource instructions')),
    )
    task.workflow = host
    reports = own('episode_work_report')
    hpc = own('library.hpc_prompt')
    before_context = deepcopy(supplied_context)
    with ExitStack() as stack:
        stack.enter_context(patch.object(reports, 'completed_action_reports', port('completed_reports', [])))
        stack.enter_context(patch.object(hpc, 'is_hpc_context', port('hpc_predicate', False)))
        if case == 'provider_error':
            try:
                asyncio.run(task.call(supplied_context, schema))
            except ValueError as error:
                assert error is failure and type(error) is ValueError
                outcome = {'raised': 'builtins.ValueError', 'message': str(error), 'same_exception': True}
            else:
                raise AssertionError('controlled provider error was not propagated')
        else:
            outcome = asyncio.run(task.call(supplied_context, schema))
            assert outcome[0] == response and outcome[1] == 0 and outcome[3] == schema
        row = value.journal.row('runtime_model_calls', task.episode_id, 0)
        assert row is not None and row['purpose'] == 'decision'
        recorded = {'request': json.loads(row['request']),
            'response': None if row['response'] is None else json.loads(row['response'])}
        if case == 'provider_error':
            assert recorded['response'] is None
        else:
            assert recorded['response'] == response
        first_events = deepcopy(events)
        replay = None
        if case == 'saved_replay':
            task.calls = 0
            provider.replay_forbidden = True
            events.clear()
            replay = asyncio.run(task.call({'ignored_fresh_input': True}, {'ignored_schema': True}))
            assert replay == outcome and events == ['profile']
    assert supplied_context == before_context
    assert sum(isinstance(event, dict) and 'provider' in event for event in first_events) == 1
    return {'outcome': outcome, 'recorded': recorded, 'events': first_events,
        'replay': replay, 'input_unchanged': True}


def compare_decision_boundary(home, output, case):
    with fixture(home, output / 'original') as value:
        before = decision_observation(value, case, original=True)
    with fixture(home, output / 'current') as value:
        after = decision_observation(value, case, original=False)
    assert after == before
    return after
