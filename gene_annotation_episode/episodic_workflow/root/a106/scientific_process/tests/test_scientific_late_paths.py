"""Five original A106 role reads after their original callbacks.

The whole original call/execute/apply_response methods come from the permanent
runtime fixture. Only the two-statement original execution-expectations block
is isolated for the extracted decision_inputs comparison. Explicit cutoff ports
stop before model work, child acquisition or science; no role is registered.
"""
import ast
import asyncio
from copy import deepcopy
import hashlib
from pathlib import Path
from types import FunctionType, SimpleNamespace

import pytest

from ... import runtime
from ..task import ScientificInvestigationTask
from ..task_decision import ScientificTaskDecision
from ..decision_inputs import ScientificDecisionInputs

FIXTURE = Path(__file__).parents[2] / 'tests/fixtures/implicit_annotation_parent/runtime.py.source'
FIXTURE_SHA = 'a98a5f609dce3f903817dc2d0a5ce468a85c40b0c1edd066645727e743fb1fd3'


class BoundaryStop(Exception):
    pass


def original(name):
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA
    cls, = [n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == 'DecisionSource']
    source_name = 'call' if name == 'expectations' else name
    node, = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == source_name]
    node = deepcopy(node)
    if name == 'expectations':
        branch, = [n for n in node.body if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == 'row']
        index, = [i for i,n in enumerate(branch.orelse) if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == 'binding']
        block = branch.orelse[index:index+2]
        assert ast.unparse(block[0].value) == 'self.workflow.execution_expectations'
        assert ast.unparse(block[1].test) == 'binding is not None and binding.applies(self.path[-1][0])'
        assert sum(isinstance(n, ast.Subscript) and ast.unparse(n) == 'self.path[-1][0]' for n in ast.walk(block[1])) == 2
        node = ast.parse('def expectations(self, context):\n    pass').body[0]
        node.body = block
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(FIXTURE), 'exec'), namespace)
    function = namespace[node.name]
    result = FunctionType(function.__code__, vars(runtime), function.__name__, function.__defaults__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


def changed_path(role):
    return () if role == 'malformed' else ((role, 'existing'),)


def outcome(call):
    try:
        return ('returned', call())
    except (BoundaryStop, IndexError) as error:
        return (type(error), str(error))


@pytest.mark.parametrize('role', ('scientific_process', 'annotation', 'malformed'))
@pytest.mark.parametrize('boundary', ('call', 'execute'))
def test_original_role_guard_after_journal_callback(boundary, role):
    def exercise(function):
        events = []
        source = SimpleNamespace(path=(('scientific_process', 'initial'),), calls=0, episode_id='source')
        def row(*args):
            events.append(('row', args)); source.path = changed_path(role)
            return None
        def context(value):
            assert value is source; events.append('binding_context'); return 'original_context'
        def validate(value): events.append(('validate', value))
        def stop(*args):
            events.append('cutoff'); raise BoundaryStop('original_post_guard_boundary')
        source.workflow = SimpleNamespace(journal=SimpleNamespace(row=row, save=stop),
            scientific_process_binding=SimpleNamespace(validate_execution_context=validate),
            binding_context=context, contract_information_profile=stop)
        args = ({}, {}) if boundary == 'call' else ({'kind': 'tool', 'tool': 'unacquired', 'arguments': {}}, 3)
        result = outcome(lambda: asyncio.run(function(source, *args)))
        return result, events, source.calls
    before = exercise(original(boundary))
    current = ScientificTaskDecision.call if boundary == 'call' else ScientificInvestigationTask.execute
    assert exercise(current) == before
    expected = [('row', ('runtime_model_calls' if boundary == 'call' else 'runtime_actions', 'source', 0 if boundary == 'call' else 3))]
    if role == 'scientific_process': expected += ['binding_context', ('validate', 'original_context')]
    if role != 'malformed': expected += ['cutoff']
    assert before[1] == expected
    assert before[0][0] is (IndexError if role == 'malformed' else BoundaryStop)


@pytest.mark.parametrize('role', ('scientific_process', 'annotation', 'malformed'))
@pytest.mark.parametrize('site', ('applies', 'capture'))
def test_original_execution_expectation_role_argument_after_callback(site, role):
    def exercise(function, private):
        events = []
        source = SimpleNamespace(path=(('scientific_process', 'initial'),),
            request=SimpleNamespace(message=SimpleNamespace(as_record=lambda: {})))
        def applies(actual_role):
            events.append(('applies', actual_role))
            if site == 'applies': raise BoundaryStop('original_applies_boundary')
            source.path = changed_path(role)
            return True
        def capture(actual_role):
            events.append(('capture', actual_role)); raise BoundaryStop('original_capture_boundary')
        binding = SimpleNamespace(applies=applies, capture=capture)
        class Workflow:
            @property
            def execution_expectations(self):
                events.append('binding_getter')
                if site == 'applies': source.path = changed_path(role)
                return binding
        workflow = Workflow()
        workflow.resource_context = lambda source: None
        workflow.shared_information_context = lambda source: None
        workflow.launch_instructions = SimpleNamespace(context=lambda: {}, materialize=lambda selection: None)
        workflow.available_child_roles = lambda source: ()
        workflow.episode_bindings = SimpleNamespace(initial_decision_context=lambda context: {})
        workflow.binding_context = lambda source: source
        workflow.pending_work = lambda source: {}
        source.credit_presentation = lambda context: SimpleNamespace(completed_work=lambda actual_source, actual_context, index: actual_context)
        source.workflow = workflow
        result = outcome(lambda: function(source, {}, 0, None) if private else function(source, {}))
        return result, events
    before = exercise(original('expectations'), False)
    assert exercise(ScientificDecisionInputs.decision_inputs, True) == before
    expected = ['binding_getter']
    if site == 'capture': expected += [('applies', 'scientific_process')]
    if role != 'malformed': expected += [(site, role)]
    assert before[1] == expected
    assert before[0][0] is (IndexError if role == 'malformed' else BoundaryStop)


@pytest.mark.parametrize('role', ('scientific_process', 'annotation', 'malformed'))
def test_original_report_grain_after_assignment_message_callback(role):
    def exercise(function):
        events = []
        source = SimpleNamespace(path=(('scientific_process', 'initial'),), episode_id='source', scope='existing_scope',
            _delivery_resolution_ref=None, interpret_schema={'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False})
        def message():
            events.append('assignment_message'); source.path=changed_path(role)
            return {'job_assignment': {'existing': 'assignment'}}
        source.request = SimpleNamespace(message=SimpleNamespace(as_record=message))
        def selected(actual_source, selection, index):
            assert actual_source is source; events.append(('selected_port', selection, index)); return object()
        def validate(admitted, scope, **kwargs):
            assert kwargs['source'] is source
            events.append(('validate_report', admitted, scope, kwargs['assignment'], kwargs['grain'], kwargs['schema']))
            raise BoundaryStop('original_report_grain_boundary')
        source.workflow = SimpleNamespace(journal=SimpleNamespace(row=lambda *args: None),
            decision_exchanges=None, permits_common_action=lambda source, kind: False, execution_binding=None,
            selected=selected, resolver=lambda scope, source: lambda ref: True, validate_report=validate)
        response={'selection': {'kind': 'tool', 'tool': 'unacquired', 'arguments': {}}, 'report_update': {}}
        schema={'type': 'object', 'properties': {'selection': {'type': 'object'}, 'report_update': source.interpret_schema},
                'required': ['selection','report_update'], 'additionalProperties': False}
        result=outcome(lambda: function(source,response,2,{'visible_record_refs':[]},schema))
        return result,events
    before=exercise(original('apply_response'))
    assert exercise(ScientificInvestigationTask.apply_response)==before
    assert before[1][1]=='assignment_message'
    assert before[0][0] is (IndexError if role=='malformed' else BoundaryStop)
    if role!='malformed': assert before[1][-1][0]=='validate_report' and before[1][-1][4]==role
