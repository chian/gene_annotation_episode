"""Actual private Results task/ActionLeaf/iterator with controlled family returns.

The practical receipt, Store, Workflow, selected private task, journal action,
controller and unit observation are real. The test port supplies a completed
family call's outcome; it is not a native producer, authenticated seven-family
result, scientific grant, saved sheet or historical-workflow acceptance test.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from .api_cases import canonical, module, rows
from .native_progress_cases import NativeProgressCase
from .native_result_owner_controls import selected

PREDICATES = {
    'native_blast_standard_database_results': 'is_standard_blast_database_target',
    'native_blast_database_results': 'is_native_blast_database_target',
    'native_hmmer_preparation_results': 'is_native_hmmer_preparation_target',
    'native_hmmer_results': 'is_native_hmmer_target',
    'native_blast_results': 'is_native_blast_target',
}


def forbidden(*args, **kwargs):
    raise AssertionError('native_returned_unit_control_attempted_external_work')


def returned_unit(directory, home, family, status, phase, *, actual_native_admission=False):
    assert status in {'completed', 'invalid', 'failed', 'unavailable'}
    case = NativeProgressCase(Path(directory) / 'practical', home)
    try:
        runtime = module('runtime')
        tools = module('tools').ToolRegistry(case.store)
        def factory(services):
            return module(home + '/episode').ExecutionEpisode(services, store=case.store,
                directory=case.directory / 'private-results', run_id=case.run_id,
                resources=case.resources, initial_information={}, tool_registry=tools,
                handoff_unit=1., acquired_record_unit=1., log_window_bytes=8,
                log_roles=('stdout', 'stderr'), require_private_yield=True,
                task_yield_profiles={'results:native_finite_local': {'cutoff': .5, 'parameters': {}}})
        workflow = runtime.Workflow(case.store, tools, object(), case.directory / 'workflow',
            case.run_id, controller_factory=forbidden, project_credit=forbidden,
            episode_binding_factories=(factory,), episode_record_receipts=True,
            initial_known_record_refs=[case.reference], annotation_child_roles=(), root_role='results',
            wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': case.reference,
            'selector': {'path': str(Path(case.assignment['workspace']) / 'unread-output.txt'),
                'offset': 0, 'limit': 1}}
        episode = workflow.build('results', 'controlled-return', 'Preserve an acquired Results return',
            case.scope, episode_assignment=assignment)
        source, context = episode.source, workflow.binding_context(episode.source)
        owner = workflow.specialist(source)
        assert owner.binding_path == home and type(source) is owner.decision_source_type
        assert type(source).__module__ == module(home + '/task').__name__
        assert owner._target(context)['handle'] == case.reference
        actual_module, actor_type = selected(home, family, phase)
        actor = getattr(owner, family[0])
        # Optional original configuration may leave a family disabled. This
        # isolated dispatch port installs its actual class solely for this call;
        # no disabled family is admitted as a producer or persisted setting.
        if actor is None:
            actor = actor_type(owner)
        assert type(actor) is actor_type and actor.owner is owner and actor.store is case.store
        payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'result': {'controlled_family_return': family[0], 'retained_failure': status,
                'complete': False, 'scientific_producer_claimed': False},
            'feedback': {'category': 'controlled_returned_unit', 'code': 'original-' + status}}
        action = {'kind': 'tool', 'tool': 'execution.results.status', 'arguments': {}}
        calls = []
        original_actor_execute = actor.execute
        original_actor_applies = getattr(actor, 'applies', None)
        async def returned(actual_context, target, tool_name, arguments, operation_key):
            assert actual_context == context and target == owner._target(context)
            assert (tool_name, arguments) == (action['tool'], action['arguments'])
            assert operation_key == f'{case.run_id}:{source.episode_id}:0'
            calls.append((tool_name, deepcopy(arguments), operation_key))
            if actual_native_admission:
                # The real native actor sees a genuine ordinary practical
                # handoff, not a fabricated seven-family producer. Its original
                # authentication/target refusal is the behavior under test.
                with ExitStack() as original_ports:
                    if original_actor_applies is not None:
                        original_ports.enter_context(patch.object(actor, 'applies', original_actor_applies))
                    return await original_actor_execute(actual_context, target, tool_name, arguments, operation_key)
            return deepcopy(payload)
        # Admission/catalog operands and native profile predicates are named
        # dispatch-only test ports. Actual selected Task, Workflow execution,
        # action storage, credit projection and iterator observation stay real.
        work = module(home + '/work_operations')
        catalog = [{'name': action['tool'], 'input_schema': {'type': 'object',
            'properties': {}, 'required': [], 'additionalProperties': False}}]
        original_execute = owner.execute
        async def dispatch(actual_context, tool_name, arguments, operation_key):
            # These branch-selection ports end before the real task projects
            # credit or verifies completion; they cannot turn the controlled
            # generic handoff into an authenticated scientific native target.
            with ExitStack() as ports:
                ports.enter_context(patch.object(owner, 'catalog', lambda selected_context: deepcopy(catalog)))
                ports.enter_context(patch.object(owner.local_file_sources, 'applies', lambda selected_context: False))
                for name in ('native_blast_masking_results', 'native_blast_utility_results'):
                    instance = getattr(owner, name)
                    ports.enter_context(patch.object(instance, 'applies', lambda selected_context, name=name: name == family[0]))
                for native, predicate in PREDICATES.items():
                    ports.enter_context(patch.object(work, predicate, lambda target, native=native: native == family[0]))
                return await original_execute(actual_context, tool_name, arguments, operation_key)
        with ExitStack() as stack:
            stack.enter_context(patch.object(owner, family[0], actor))
            if actual_native_admission and family[0] == 'native_hmmer_preparation_results':
                reader = module('native_hmmer_preparation_returns').NativeHmmerPreparationReturns(owner)
                assert reader.owner is owner and reader.results is actor
                stack.enter_context(patch.object(owner, 'native_hmmer_preparation_returns', reader))
            stack.enter_context(patch.object(actor, 'execute', returned))
            stack.enter_context(patch.object(owner, 'execute', dispatch))
            unit = workflow.selected(source, deepcopy(action), 0)
            assert type(unit) is runtime.ActionLeaf and unit.decision_index == 0
            chosen = []
            async def select(view, **kwargs):
                assert not kwargs and view.units_consumed == 0
                chosen.append(view)
                return unit
            stack.enter_context(patch.object(source, 'next', select))
            try:
                observed = asyncio.run(episode.run_unit_async(workflow.context, expected_label=unit.label))
            except KeyError as error:
                assert actual_native_admission and family[0] == 'native_hmmer_results'
                assert error.args == ('native_hmmer',)
                assert len(chosen) == len(calls) == 1
                saved = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
                assert json.loads(saved['action']) == action and saved['result'] is saved['credit'] is None
                observed_rows = [dict(row) for row in case.store.db.execute(
                    'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=?',
                    (case.run_id, source.episode_id))]
                assert observed_rows == []
                return {'home': home, 'family': family[0], 'actual_native_admission': True,
                    'boundary': {'raised': {'type': 'builtins.KeyError', 'args': list(error.args)}},
                    'action': action, 'returned_outcome': False, 'observations': 0,
                    'native_producer_or_seven_family_admission_claimed': False}
            assert len(chosen) == len(calls) == 1
            saved = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
            actual_outcome = json.loads(saved['result'])
            assert json.loads(saved['action']) == action
            if actual_native_admission:
                assert family[0] != 'native_hmmer_results' and actual_outcome['status'] == 'invalid'
            else:
                assert actual_outcome == payload
            assert runtime.observes_action_outcome('tool', actual_outcome['status']) and saved['credit'] is not None
            observations = [dict(row) for row in case.store.db.execute(
                'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=?',
                (case.run_id, source.episode_id))]
            assert len(observations) == 1
            stored_observation = json.loads(observations[0]['observation'])
            assert stored_observation['decision_index'] == 0
            snapshot = rows(case.store)
            replayed = asyncio.run(workflow.selected(source, deepcopy(action), 0).acquire_async(workflow.context))
            assert len(calls) == 1 and rows(case.store) == snapshot
            assert replayed.contribution.controller_input == observed.controller_input
        if actual_native_admission:
            return {'home': home, 'family': family[0], 'actual_native_admission': True,
                'boundary': {'returned': actual_outcome}, 'action': action,
                'returned_outcome': True, 'observations': 1,
                'saved_action_replayed_without_execution': True,
                'native_producer_or_seven_family_admission_claimed': False}
        return {'home': home, 'family': family[0], 'status': status,
            'actual_actor': actual_module.__name__ + '.' + actor_type.__qualname__,
            'actual_task': type(source).__module__ + '.' + type(source).__qualname__,
            'action': json.loads(saved['action']), 'outcome': json.loads(saved['result']),
            'credit': saved['credit'], 'observation': stored_observation,
            'single_return_and_observation': True, 'saved_action_replayed_without_execution': True,
            'native_producer_or_seven_family_admission_claimed': False}
    finally:
        case.close()
