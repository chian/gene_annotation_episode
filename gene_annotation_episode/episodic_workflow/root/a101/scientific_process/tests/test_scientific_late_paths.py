"""Six authentic original late-path boundaries, separate from provider oracles.

Original public runtime functions/AST come from the retained permanent original
fixture. Deterministic callbacks expose the exact later reads; no new role,
configured child admission, scientific operation or observation is asserted.
"""
import ast
import asyncio
from copy import deepcopy
from types import FunctionType, SimpleNamespace

import pytest

from ...tests.test_a101_implicit_parent_protocol import original_function, original_node, own
from ..task import ScientificInvestigationTask
from ..task_decision import ScientificTaskDecision
from ..decision_inputs import ScientificDecisionInputs

runtime = own('runtime')
SCIENTIFIC_PATH = (('scientific_process', 'original'),)
CHANGED_PATH = (('annotation', 'original'),)


class BoundaryReached(Exception):
    pass


def test_call_reads_path_after_original_journal_callback():
    def exercise(function):
        events = []
        source = SimpleNamespace(path=SCIENTIFIC_PATH, calls=0, episode_id='source')
        def row(*args):
            events.append('row'); source.path = CHANGED_PATH
            return None
        def profile(*args): events.append('profile'); raise BoundaryReached('original_profile')
        source.workflow = SimpleNamespace(journal=SimpleNamespace(row=row), contract_information_profile=profile,
            binding_context=lambda source: source,
            scientific_process_binding=SimpleNamespace(validate_execution_context=lambda context: events.append('scientific_validation')))
        with pytest.raises(BoundaryReached, match='^original_profile$') as error:
            asyncio.run(function(source, {}, {}))
        return type(error.value), str(error.value), source.calls, source.path, events
    expected = exercise(original_function('DecisionSource', 'call'))
    assert exercise(ScientificTaskDecision.call) == expected
    assert expected[-1] == ['row', 'profile']


def test_execute_reads_path_after_original_saved_action_probes():
    def exercise(function):
        events = []
        source = SimpleNamespace(path=SCIENTIFIC_PATH, episode_id='source')
        def row(*args): events.append('row'); source.path = CHANGED_PATH; return None
        def save(*args): events.append('save'); raise BoundaryReached('original_save')
        source.workflow = SimpleNamespace(journal=SimpleNamespace(row=row, save=save),
            binding_context=lambda source: source,
            scientific_process_binding=SimpleNamespace(validate_execution_context=lambda context: events.append('scientific_validation')))
        with pytest.raises(BoundaryReached, match='^original_save$') as error:
            asyncio.run(function(source, {'kind': 'tool', 'tool': 'existing', 'arguments': {}}, 0))
        return type(error.value), str(error.value), source.path, events
    expected = exercise(original_function('DecisionSource', 'execute'))
    assert exercise(ScientificInvestigationTask.execute) == expected
    assert expected[-1] == ['row', 'save']


def original_expectations():
    """Only the two adjacent original statements, without predicate rewriting."""
    call = original_node('DecisionSource', 'call')
    assignment, = [n for n in ast.walk(call) if isinstance(n, ast.Assign)
                   and ast.dump(n.value, include_attributes=False) == ast.dump(ast.parse('self.workflow.execution_expectations', mode='eval').body, include_attributes=False)]
    parents = [n for n in ast.walk(call) if isinstance(n, ast.If) and assignment in n.orelse]
    parent, = parents
    index = parent.orelse.index(assignment)
    conditional = parent.orelse[index + 1]
    assert isinstance(conditional, ast.If)
    assert ast.unparse(conditional.test) == 'binding is not None and binding.applies(self.path[-1][0])'
    function, = ast.parse('def original(self, context):\n    return context\n').body
    function.body = [deepcopy(assignment), deepcopy(conditional), function.body[0]]
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), '<original-runtime-expectations-statements>', 'exec'), namespace)
    return FunctionType(namespace['original'].__code__, vars(runtime))


@pytest.mark.parametrize('boundary', ('applies', 'planning', 'capture'))
def test_expectation_roles_follow_their_original_callback_positions(boundary):
    def exercise(function, complete):
        events = []
        source = SimpleNamespace(path=SCIENTIFIC_PATH, scope='scope')
        class Binding:
            planning_roles = ('annotation',) if boundary == 'planning' else ('scientific_process',)
            def applies(self, role):
                events.append(('applies', role))
                if boundary == 'planning': source.path = CHANGED_PATH
                return boundary != 'applies'
            def capture(self, role, **kwargs):
                events.append(('capture', role, kwargs)); return {'role': role, **kwargs}
        binding = Binding()
        def classes(store, scope):
            events.append(('planning', scope))
            if boundary == 'capture': source.path = CHANGED_PATH
            return []
        class Workflow:
            @property
            def execution_expectations(self):
                events.append('binding')
                if boundary == 'applies': source.path = CHANGED_PATH
                return binding
        workflow = Workflow()
        workflow.job_episodes = SimpleNamespace(jobs=SimpleNamespace(config={}), prospective_execution_classes=classes)
        workflow.store = object()
        workflow.resource_context = lambda source: None
        workflow.shared_information_context = lambda source: None
        workflow.launch_instructions = SimpleNamespace(context=lambda: {}, materialize=lambda value: None)
        workflow.available_child_roles = lambda source: ()
        workflow.binding_context = lambda source: source
        workflow.episode_bindings = SimpleNamespace(initial_decision_context=lambda context: {})
        workflow.resource_estimator = None
        workflow.native_estimation_context = lambda source, context: None
        workflow.native_event_information = None
        workflow.permits_common_action = lambda source, action: False
        source.workflow = workflow
        source.request = SimpleNamespace(message=SimpleNamespace(as_record=lambda: {'job_assignment': {'original': True}}))
        source.credit_presentation = lambda context: SimpleNamespace(completed_work=lambda source, value, index: value)
        context = {'launch_instruction_library': {}, 'pending_work': {}}
        result = function(source, deepcopy(context), 0, None) if complete else function(source, deepcopy(context))
        return result, source.path, events
    expected = exercise(original_expectations(), False)
    assert exercise(ScientificDecisionInputs.decision_inputs, True) == expected
    if boundary == 'applies': assert expected[-1] == ['binding', ('applies', 'annotation')]
    else:
        assert expected[-1][-1] == ('capture', 'annotation', {'assignment': {'original': True}, 'planning_scopes': []})


def test_report_grain_is_read_after_original_assignment_argument(monkeypatch):
    marker = object()
    def exercise(function):
        events = []
        source = SimpleNamespace(path=SCIENTIFIC_PATH, scope='scope', episode_id='source',
            _delivery_resolution_ref=None, report_values={}, interpret_schema={'type': 'object', 'properties': {'ready': {'type': 'boolean'}}, 'required': ['ready'], 'additionalProperties': False})
        def message():
            events.append('assignment'); source.path = CHANGED_PATH
            return {'job_assignment': {'original': True}}
        def validate(value, scope, **kwargs):
            events.append(('validate_report', value, scope, {key: value for key, value in kwargs.items() if key != 'source'}))
            assert kwargs['source'] is source
        source.request = SimpleNamespace(message=SimpleNamespace(as_record=message))
        source.record_effect = lambda *args: events.append(('effect', args))
        source.workflow = SimpleNamespace(journal=SimpleNamespace(row=lambda *args: None), decision_exchanges=None,
            permits_common_action=lambda source, action: False, execution_binding=None,
            selected=lambda *args: marker, resolver=lambda *args, **kwargs: lambda ref: True,
            validate_report=validate)
        with monkeypatch.context() as patch:
            patch.setattr(runtime, '_decode_recorded_action_response', lambda response, *args, **kwargs: response)
            result = function(source, {'selection': {'kind': 'tool'}, 'report_update': {'ready': True}}, 0,
                {'visible_record_refs': []}, {'properties': {'selection': {'type': 'object'}}})
        return result is marker, source.path, source.report_values, source.report_basis, source.feedback, events
    expected = exercise(original_function('DecisionSource', 'apply_response'))
    assert exercise(ScientificInvestigationTask.apply_response) == expected
    assert expected[:5] == (True, CHANGED_PATH, {'ready': True}, [], None)
    assert expected[-1][0] == 'assignment'
    assert expected[-1][1][3]['grain'] == 'annotation'
