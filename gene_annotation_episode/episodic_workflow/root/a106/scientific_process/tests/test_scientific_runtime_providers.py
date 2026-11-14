"""Finite original-provider controls for the existing A106 Scientific task.

The fixture retains the actual eight pre-correction private source bodies.
Engineering ports expose provider/callback timing; they do not run science,
child acquisition, a saved Workflow, or an earlier accepted test cohort.
The original oracle here is the authenticated A106 private definition before
provider restoration; earlier role specialization is a separate review scope.
"""
import ast
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace
import textwrap

import pytest

from ... import runtime

PACKAGE = runtime.__name__.rsplit('.', 1)[0] + '.scientific_process'
FIXTURE = Path(__file__).parent / 'fixtures/runtime_provider_originals.txt'
ORIGINALS = {
    'task': ('51f226464440cce4da33b6343ae5774ac220ddb907435f202ca17a61bf1728d3', 'ScientificInvestigationTask', ('next', 'apply_response', 'execute')),
    'task_decision': ('bad2d76a2034ae88346bd30e7f8afdd117e8a567ef84a3fdd5b7f9acbc02a4ce', 'ScientificTaskDecision', ('call', 'interpretation_context', 'exchange_schema', 'exchange_response', 'validate_contract_exchange_request', 'validate_contract_exchange_history', 'exchange_decision')),
    'task_state': ('4ef2a7dc819d306924432cadb4b8b2de6664b4e462f7df57de5c26181e4a888e', 'ScientificTaskState', ('__init__', 'record_execution_failure', 'restore_checkpoint', 'restore', 'record_effect')),
    'waiting': ('c8305c1243d97072450e51fad63e5a4ebece87b38c4cd27e48db16ca529f22e9', 'ScientificWaiting', ('_execute_selected_wait',)),
    'report_delivery': ('1227696c66bf7167bcdf732f853ef93b4dbe8aa5e29e591729a7f475d2008119', 'ScientificReportDelivery', ('finish',)),
    'decision_inputs': ('ab939d04ef4480ee695e65172db2d24509ff524df55236a787b716435b541e4a', 'ScientificDecisionInputs', ('decision_inputs',)),
    'standalone_credit_presentation': ('fd829f6642e7956a92cb916e7361fd4f8a3679d35b86dc6ae7a8ae23a6a4d02d', 'StandaloneScientificPresentation', ('decision_state', 'completed_work', 'exchange_yield_table')),
    'commissioned_credit_presentation': ('edf58f95db38bc8230ccee61001b3e90d91cd6b261cce0ec200b1a2b0869b0f6', 'CommissionedScientificPresentation', ('decision_state', 'exchange_yield_table')),
}


def original_node(module, name):
    bundle = json.loads(FIXTURE.read_text())
    assert set(bundle) == set(ORIGINALS)
    for key, (pin, _, _) in ORIGINALS.items():
        assert hashlib.sha256(bundle[key].encode()).hexdigest() == pin
    cls, = [n for n in ast.parse(bundle[module]).body if isinstance(n, ast.ClassDef) and n.name == ORIGINALS[module][1]]
    fn, = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    return deepcopy(fn)


def original(module, name):
    node = original_node(module, name)
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(FIXTURE), 'exec'), namespace)
    source = namespace[name]
    function = FunctionType(source.__code__, vars(runtime), source.__name__, source.__defaults__)
    function.__kwdefaults__ = source.__kwdefaults__
    return function


from .scientific_path_oracle import expected_current_node


def current(module, name):
    owner = importlib.import_module(PACKAGE + '.' + module)
    return vars(getattr(owner, ORIGINALS[module][1]))[name]


class ProviderFailure(Exception):
    pass


def test_exact_twenty_three_private_bodies_metadata_and_live_namespaces():
    checked = 0
    for module, (_, class_name, names) in ORIGINALS.items():
        owner = importlib.import_module(PACKAGE + '.' + module)
        cls = getattr(owner, class_name)
        for name in names:
            function = vars(cls)[name]
            inspected_class, = ast.parse('class _Inspected:\n' + inspect.getsource(function)).body
            node, = inspected_class.body
            assert ast.dump(node, include_attributes=False) == ast.dump(expected_current_node(original_node(module, name), module, name), include_attributes=False)
            assert function.__globals__ is vars(runtime)
            assert function.__module__ == owner.__name__ and function.__qualname__ == class_name + '.' + name
            assert function.__code__.co_filename == owner.__file__ and function.__closure__ is None
            old = original(module, name)
            assert function.__defaults__ == old.__defaults__ and function.__kwdefaults__ == old.__kwdefaults__
            checked += 1
    assert checked == 23
    task = importlib.import_module(PACKAGE + '.task').ScientificInvestigationTask
    assert task.finish is current('report_delivery', 'finish')
    assert task.__init__ is current('task_state', '__init__')
    assert task._execute_selected_wait is current('waiting', '_execute_selected_wait')
    assert task.call is current('task_decision', 'call')
    assert task.decision_inputs is current('decision_inputs', 'decision_inputs')
    router = importlib.import_module(PACKAGE + '.decision_state')
    assert router.ScientificDecisionState.credit_presentation.__globals__ is vars(router)
    composer = importlib.import_module(PACKAGE + '.task_instructions')
    assert task.instruction_composer is composer.instructions


@pytest.mark.parametrize('route', ('uncontracted', 'saved_form', 'fresh_form'))
@pytest.mark.parametrize('failure', (False, True), ids=('returned', 'provider_failure'))
def test_finish_original_late_providers_and_awaited_release(route, failure, monkeypatch):
    def exercise(function):
        events = []
        def late_record(value):
            events.append(('Record', value))
            if failure: raise ProviderFailure('late_record_failure')
            return {'record': value}
        def serialize(value):
            events.append(('_json', value)); return repr(value)
        def form(values, schema, facts):
            events.append(('form', values, schema, facts))
            runtime._json = serialize
            return {'fresh': True}
        def row(*args):
            events.append(('row', args))
            runtime.json = SimpleNamespace(loads=lambda value: events.append(('loads', value)) or {'saved': True})
            return {'form': 'saved-json'} if route == 'saved_form' else None
        def facts(source, completion_record):
            events.append(('facts', completion_record)); runtime.form_with_facts = form
            return {'finding': 'qualified'}
        async def release(episode_id):
            events.append(('release_enter', episode_id)); await asyncio.sleep(0)
            runtime.Record = late_record; events.append(('release_done', episode_id))
        workflow = SimpleNamespace(source_credit_view=lambda source: {'credit': .25}, pending_handles=lambda source: ['pending'],
            episode_bindings=SimpleNamespace(current_report_facts=lambda context: {'qualified': 'received'}),
            binding_context=lambda source: source, release=release, facts=facts,
            journal=SimpleNamespace(row=row, save=lambda *args: events.append(('save', args))))
        source = SimpleNamespace(workflow=workflow, episode_id='original-scientific-report', report_values={'unresolved': True},
            request=SimpleNamespace(report_contract=None if route == 'uncontracted' else SimpleNamespace(schema={'type': 'object'})))
        def frozen(*args, **kwargs): raise AssertionError('original_provider_was_read_too_early')
        with monkeypatch.context() as patch:
            for name in ('Record', '_json', 'form_with_facts'): patch.setattr(runtime, name, frozen)
            patch.setattr(runtime, 'json', SimpleNamespace(loads=frozen))
            try: result = ('returned', asyncio.run(function(source, {'completion': 'retained'})))
            except ProviderFailure as error: result = (type(error), str(error))
        return result, events
    before = exercise(original('report_delivery', 'finish'))
    after = exercise(current('report_delivery', 'finish'))
    assert after == before
    assert after[1][-2:] == [('release_done', 'original-scientific-report'), ('Record', {'credit': .25, 'pending_handles': ['pending'], 'qualified': 'received'} if route == 'uncontracted' else {'form': {'saved': True} if route == 'saved_form' else {'fresh': True}})]


@pytest.mark.parametrize('failure', (False, True), ids=('returned', 'provider_failure'))
def test_constructor_reads_schema_provider_after_message_callback(failure, monkeypatch):
    def exercise(function):
        events = []
        def schema(value):
            events.append(('schema', value))
            if failure: raise ProviderFailure('late_schema_failure')
            return {'original': value}
        def message():
            events.append('message'); runtime.interpretation_schema = schema
            return {'initial_report': {'unresolved': True}}
        workflow = SimpleNamespace(context='context', grains={'scientific_process': 'grain'})
        request = SimpleNamespace(message=SimpleNamespace(as_record=message), report_contract=SimpleNamespace(schema={'type': 'object'}))
        source = SimpleNamespace()
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'Episode', SimpleNamespace(identity=lambda *args, **kwargs: events.append(('identity', args, kwargs)) or SimpleNamespace(episode_id='source')))
            patch.setattr(runtime, 'interpretation_schema', lambda _: (_ for _ in ()).throw(AssertionError('early_schema')))
            try: result = function(source, workflow, (('scientific_process', 'child'),), request, 'scope')
            except ProviderFailure as error: result = (type(error), str(error))
        state = dict(vars(source)); state.pop('workflow'); state.pop('request')
        return result, state, events
    assert exercise(current('task_state', '__init__')) == exercise(original('task_state', '__init__'))


def test_exchange_schema_preserves_callee_lookup_before_argument_callback(monkeypatch):
    def exercise(function):
        events = []
        def old_object(value): events.append('old_object'); return {'old': value}
        def new_object(value): events.append('new_object'); return {'new': value}
        def lookup(*args):
            events.append('lookup'); runtime._object = new_object
            return {'lookup': 'contract'}
        with monkeypatch.context() as patch:
            patch.setattr(runtime, '_object', old_object); patch.setattr(runtime, 'composition_lookup_schema', lookup)
            result = function(SimpleNamespace(workflow=object()), {'properties': {'selection': {'type': 'object'}}})
        return result, events
    expected = exercise(original('task_decision', 'exchange_schema'))
    assert exercise(current('task_decision', 'exchange_schema')) == expected
    assert expected[1] == ['lookup', 'old_object', 'new_object', 'old_object']


@pytest.mark.parametrize('recognized', (True, False), ids=('late_exception', 'unrelated_exception'))
def test_wait_retains_late_exception_identity_after_await(recognized, monkeypatch):
    class LateTargetError(Exception): pass
    def exercise(function):
        events = []
        async def wait(*args):
            events.append('wait_enter'); await asyncio.sleep(0)
            runtime.EventTargetError = LateTargetError
            runtime._wait_target_feedback = lambda error, **kwargs: events.append(('feedback', str(error), kwargs)) or {'original': str(error)}
            events.append('wait_resume')
            raise LateTargetError('late_target') if recognized else TypeError('original_unrelated')
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'EventTargetError', ProviderFailure)
            patch.setattr(runtime, '_wait_target_feedback', lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('early_feedback')))
            try: result = asyncio.run(function(SimpleNamespace(workflow=SimpleNamespace(perform_selected_wait=wait)), {'condition': 'existing'}, 3))
            except TypeError as error: result = (type(error), str(error))
        return result, events
    assert exercise(current('waiting', '_execute_selected_wait')) == exercise(original('waiting', '_execute_selected_wait'))


def test_decision_inputs_reads_child_information_after_available_children(monkeypatch):
    def exercise(function):
        events = []
        def child_info(*args): events.append('late_child_info'); raise ProviderFailure('selected_child_information')
        def available(source):
            events.append('available'); runtime.child_option_information = child_info
            return ('actual-existing-child',)
        workflow = SimpleNamespace(resource_context=lambda source: None, shared_information_context=lambda source: None,
            launch_instructions=SimpleNamespace(context=lambda: {}, materialize=lambda value: None), available_child_roles=available)
        source = SimpleNamespace(workflow=workflow, request=SimpleNamespace(message=SimpleNamespace(as_record=lambda: {})))
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'child_option_information', lambda *_: (_ for _ in ()).throw(AssertionError('early_child_info')))
            with pytest.raises(ProviderFailure, match='^selected_child_information$') as error: function(source, {}, 0, None)
        return type(error.value), str(error.value), events
    expected = exercise(original('decision_inputs', 'decision_inputs'))
    assert exercise(current('decision_inputs', 'decision_inputs')) == expected
    assert expected[2] == ['available', 'late_child_info']


@pytest.mark.parametrize('module', ('standalone_credit_presentation', 'commissioned_credit_presentation'))
def test_yield_table_uses_provider_rebound_by_original_parameters(module, monkeypatch):
    def exercise(function):
        events = []
        def late_table(*args, **kwargs): events.append(('table', args, kwargs)); return {'retained': 'yield-table'}
        def parameters(value):
            events.append(('parameters', value)); runtime.yield_table = late_table
            return 'original-parameters'
        with monkeypatch.context() as patch:
            patch.setattr(runtime, '_category_yield_parameters', parameters)
            patch.setattr(runtime, 'yield_table', lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('early_yield_table')))
            result = function(SimpleNamespace(workflow=SimpleNamespace(controller_binding='binding'), episode_id='scientific'), {}, 2, 'journal')
        return result, events
    assert exercise(current(module, 'exchange_yield_table')) == exercise(original(module, 'exchange_yield_table'))


@pytest.mark.parametrize('status', ('invalid', 'failed', 'unavailable'))
def test_execute_returned_outcome_keeps_original_late_measurement_and_identity(status, monkeypatch):
    original_observes = runtime.observes_action_outcome
    def exercise(function):
        events = []
        selection = {'kind': 'tool', 'tool': 'existing.tool', 'arguments': {}}
        returned = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'feedback': {'original': status}}
        def late_observes(kind, value):
            events.append(('observes', kind, value)); return original_observes(kind, value)
        async def execute(*args, **kwargs):
            events.append(('execute', args[1:], kwargs)); await asyncio.sleep(0)
            runtime.observes_action_outcome = late_observes
            return deepcopy(returned)
        async def score(source, index, result): events.append(('score', index, deepcopy(result))); return result
        workflow = SimpleNamespace(
            journal=SimpleNamespace(row=lambda *args: None, save=lambda *args: events.append(('save', deepcopy(args))), measure=lambda *args: nullcontext()),
            scientific_process_binding=SimpleNamespace(validate_execution_context=lambda context: events.append('validate')),
            binding_context=lambda source: source, execution_binding=None, wait_inputs_version=None, completed_action_inputs_version=None,
            run_id='run', execute=execute, store=SimpleNamespace(transaction=lambda: nullcontext()),
            receive_native_outcome=lambda source, result, index: events.append(('native', deepcopy(result), index)),
            receive_outcome=lambda source, selected, result, index: events.append(('receive', deepcopy(selected), deepcopy(result), index)),
            automatic_score_updates=score, source_credit_view=lambda source: {'credit': .25},
            controller_value=lambda source, index, credit: {'decision_index': index, 'original_credit': credit})
        source = SimpleNamespace(workflow=workflow, path=(('scientific_process', 'child'),),
            episode_id='scientific', checkpoint=lambda: events.append('checkpoint'))
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'observes_action_outcome', lambda *_: (_ for _ in ()).throw(AssertionError('early_observation_provider')))
            result = asyncio.run(function(source, selection, 2))
        return result, deepcopy(source.last_outcome), source.last_outcome_index, source.feedback, events
    expected = exercise(original('task', 'execute'))
    actual = exercise(current('task', 'execute'))
    assert actual == expected
    assert actual[:3] == ({'decision_index': 2, 'original_credit': .25}, {'status': status, 'record_refs': [], 'changed_record_refs': [], 'feedback': {'original': status}}, 2)
    assert ('observes', 'tool', status) in actual[4]
    assert any(event[0] == 'receive' for event in actual[4] if isinstance(event, tuple))
