"""Exact original goal expression and its real request-envelope selection."""
import ast
from copy import deepcopy
import hashlib
from pathlib import Path
from types import FunctionType, SimpleNamespace

import pytest

from .. import runtime
from .. import goal
from ..library.episode_request_envelope import assemble_request
from .test_implicit_annotation_parent import actual_workflow

FIXTURE = Path(__file__).parent / 'fixtures/implicit_annotation_parent/runtime.py.source'
FIXTURE_SHA = 'a98a5f609dce3f903817dc2d0a5ce468a85c40b0c1edd066645727e743fb1fd3'


def original_goal():
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA
    workflow, = [n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == 'Workflow']
    build, = [n for n in workflow.body if isinstance(n, ast.FunctionDef) and n.name == 'build']
    assignment, = [n for n in build.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'goal' for t in n.targets)]
    function = ast.parse('def original_goal(name, goal_text, parent, contract):\n    pass').body[0]
    function.body = [ast.Return(deepcopy(assignment.value))]
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(FIXTURE), 'exec'), namespace)
    return FunctionType(namespace['original_goal'].__code__, vars(runtime))


@pytest.mark.parametrize('mode', ['root', 'child', 'schema_failure', 'late_schema_rebind'])
def test_original_expression_evaluation_and_live_provider_order(mode, monkeypatch):
    parent = None if mode == 'root' else object()
    objective = {'question': 'Preserve the qualified unknown'}
    schema = {'type': 'object', 'properties': {}}
    expected = None
    for function in (original_goal(), goal.prepare_goal):
        events = []
        class Replacement:
            @staticmethod
            def child(*args, **kwargs):
                raise AssertionError('callee was incorrectly looked up after schema callback')
        class Provider:
            @staticmethod
            def root(**kwargs):
                events.append(('root', kwargs))
                return {'provider': 'original_selected_root', **kwargs}
            @staticmethod
            def child(actual_parent, **kwargs):
                assert actual_parent is parent
                events.append(('child', kwargs))
                return {'provider': 'original_selected_child', **kwargs}
        class Contract:
            @property
            def schema(self):
                events.append('schema')
                if mode == 'schema_failure':
                    raise ValueError('original_contract_schema_failure')
                if mode == 'late_schema_rebind':
                    runtime.EpisodeGoal = Replacement
                return schema
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'EpisodeGoal', Provider)
            try:
                result = ('returned', function('annotation', objective, parent, Contract()))
            except ValueError as error:
                result = (type(error), str(error))
        actual = (result, events)
        if expected is None: expected = actual
        else: assert actual == expected
    if mode == 'root': assert events[0][0] == 'root' and len(events) == 1
    elif mode == 'schema_failure': assert events == ['schema']
    else: assert events[0] == 'schema' and events[1][0] == 'child'
    assert goal.prepare_goal.__globals__ is vars(runtime)


@pytest.mark.parametrize('kind', ['root', 'child'])
def test_actual_goal_type_and_immutable_parent_link(kind):
    parent = None if kind == 'root' else runtime.EpisodeGoal.root(objective='Original root', result_contract={'role': 'annotation'})
    contract = SimpleNamespace(schema={'type': 'object', 'properties': {}, 'additionalProperties': False})
    original = original_goal()('annotation', 'Retain qualified findings', parent, contract)
    actual = goal.prepare_goal('annotation', 'Retain qualified findings', parent, contract)
    assert type(actual) is type(original) is runtime.EpisodeGoal
    assert actual == original and actual.goal_id == original.goal_id
    assert actual.parent_goal_id == ('' if parent is None else parent.goal_id)


@pytest.mark.parametrize('name', ['annotation', 'improvement'])
def test_actual_envelope_uses_existing_goal_route(tmp_path, monkeypatch, name):
    from ..annotation_improvement import goal as improvement_goal
    calls = []
    root_builder = goal.prepare_goal
    improvement_builder = improvement_goal.prepare_goal
    def root_call(*args):
        calls.append('annotation')
        return root_builder(*args)
    def improvement_call(*args):
        calls.append('improvement')
        return improvement_builder(*args)
    with actual_workflow(tmp_path / name) as workflow:
        scope = workflow.store.validate_scope()
        with monkeypatch.context() as patch:
            patch.setattr(goal, 'prepare_goal', root_call)
            patch.setattr(improvement_goal, 'prepare_goal', improvement_call)
            path, actual, message, identity, request = assemble_request(workflow, name, 'goal-boundary', 'Preserve original objective', scope)
        assert calls == [name]
        assert path == ((name, 'goal-boundary'),)
        assert actual == original_goal()(name, 'Preserve original objective', None, None)
        assert request.goal is actual and request.message.as_record()['initial_report'] == {}
        assert identity.episode_id and message['scope'] == scope
    # This stops at genuine immutable request construction: no child acquisition,
    # credit repair, model operation or scientific execution is claimed.
