"""Finite incoming/goal relocation controls on real A104 constructors.

The original runtime fixture is the constructor/expression oracle. Engineering
callback ports test ordering and live globals; no native work, iteration,
Scientific observation or whole-workflow restoration is claimed here.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import inspect
import pytest

from .test_a104_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, original_node, own,
)


def original_goal(name, objective, parent, contract):
    build = original_node('Workflow', 'build')
    preparation = build.body[0]
    assert isinstance(preparation, ast.If)
    assert ast.dump(preparation.test) == ast.dump(ast.parse('request_assembler is None', mode='eval').body)
    assignment, = [node for node in preparation.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'goal' for target in node.targets)]
    expression = ast.Expression(body=deepcopy(assignment.value))
    return eval(compile(ast.fix_missing_locations(expression), '<authenticated-original-goal>', 'eval'),
                vars(own('runtime')), {'name': name, 'goal_text': objective, 'parent': parent, 'contract': contract})


def check_real_initializer(directory, role):
    runtime = own('runtime')
    expected_class = type('OriginalDecisionSource', (runtime.DecisionSource,),
                          {'__init__': original_function('DecisionSource', '__init__')})
    private = own('episode').AnnotationTask if role == 'annotation' else own('annotation_improvement.episode').ImprovementTask
    with actual_workflow(directory) as workflow:
        item = workflow.build(role, 'custody', 'Retain the original commissioned question', workflow.store.validate_scope())
        assert type(item.source) is private
        assert item.source.request.goal.as_record() == original_goal(role, 'Retain the original commissioned question', None, None).as_record()
        arguments = (workflow, item.source.path, item.source.request, item.source.scope)
        expected = expected_class(*arguments)
        actual = private(*arguments)
        assert vars(actual) == vars(expected)
        assert actual.episode_id == item.source.episode_id
        assert type(actual).__init__.__globals__ is vars(runtime)
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()


def test_single_incoming_definer_and_inherited_descriptor_identity():
    runtime, incoming, state = own('runtime'), own('from_parent'), own('task_state')
    original = original_node('DecisionSource', '__init__')
    current = incoming.__init__
    assert runtime.DecisionSource.__init__ is current
    assert '__init__' not in vars(state)
    for cls in (own('episode').AnnotationTask, own('annotation_improvement.episode').ImprovementTask):
        assert '__init__' not in vars(cls)
        assert inspect.getattr_static(cls, '__init__') is current
    assert current.__globals__ is vars(runtime)
    assert current.__module__ == runtime.__name__
    assert current.__qualname__ == 'DecisionSource.__init__'
    assert current.__code__.co_filename == incoming.__file__
    candidate, = ast.parse(inspect.getsource(current)).body
    assert ast.dump(candidate, include_attributes=False) == ast.dump(original, include_attributes=False)
    assert all(callable(getattr(state, name)) for name in (
        'bind_execution_context', 'suspension_changed', 'restore_checkpoint', 'restore', 'record_effect', 'checkpoint'))


def test_actual_annotation_incoming_state_matches_original(tmp_path):
    check_real_initializer(tmp_path, 'annotation')


@pytest.mark.parametrize('failed_port', ('identity', 'plain', 'schema'))
def test_constructor_original_failure_order_and_live_globals(tmp_path, monkeypatch, failed_port):
    runtime = own('runtime')
    expected_class = type('OriginalDecisionSource', (runtime.DecisionSource,),
                          {'__init__': original_function('DecisionSource', '__init__')})
    class PortError(Exception): pass
    with actual_workflow(tmp_path) as workflow:
        item = workflow.build('annotation', 'ports', 'Original incoming boundaries', workflow.store.validate_scope())
        schema = runtime._object({'unresolved': {'type': 'boolean'}})
        contract = runtime.TypedReportContract('Retain the unresolved result', schema, lambda *_: False)
        request = runtime.EpisodeRequest(item.source.request.goal, runtime.Record({'initial_report': {'unresolved': None}}), contract)
        identity, plain, interpretation = runtime.Episode.identity, runtime._plain, runtime.interpretation_schema
        results = []
        for cls in (expected_class, own('episode').AnnotationTask):
            events = []
            def call_port(name, function, *args, **kwargs):
                events.append(name)
                if name == failed_port:
                    raise PortError('original_' + name)
                return function(*args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(runtime.Episode, 'identity', staticmethod(lambda *args, **kwargs: call_port('identity', identity, *args, **kwargs)))
                patch.setattr(runtime, '_plain', lambda *args, **kwargs: call_port('plain', plain, *args, **kwargs))
                patch.setattr(runtime, 'interpretation_schema', lambda *args, **kwargs: call_port('schema', interpretation, *args, **kwargs))
                with pytest.raises(PortError, match='^original_' + failed_port + '$') as error:
                    cls(workflow, item.source.path, request, item.source.scope)
            results.append((events, type(error.value), str(error.value)))
        assert results[0] == results[1]
        assert results[0][0][0] == 'identity' and results[0][0][-1] == failed_port
        if failed_port == 'schema':
            # The authentic _plain recursively visits the report and contract
            # schema; retain that complete original/current trace, rather
            # than assuming that each top-level conversion is one callback.
            assert len(results[0][0]) > 4
            assert all(event == 'plain' for event in results[0][0][1:-1])
        else:
            assert results[0][0] == {'identity': ['identity'], 'plain': ['identity', 'plain']}[failed_port]
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()


@pytest.mark.parametrize('child', (False, True), ids=('root', 'child'))
def test_goal_original_conditional_types_and_fields(child):
    runtime = own('runtime')
    parent = runtime.EpisodeGoal.root(objective='Existing parent question', result_contract={'role': 'annotation'}) if child else None
    contract = runtime.TypedReportContract('Unknown result', runtime._object({'unresolved': {'type': 'boolean'}}), lambda *_: False) if child else None
    actual = own('goal').prepare_goal('annotation', 'Original objective', parent, contract)
    expected = original_goal('annotation', 'Original objective', parent, contract)
    assert type(actual) is type(expected)
    assert actual.as_record() == expected.as_record()
    assert own('goal').prepare_goal.__globals__ is vars(runtime)


def test_goal_original_contract_error_position():
    runtime = own('runtime')
    parent = runtime.EpisodeGoal.root(objective='Original parent', result_contract={'role': 'annotation'})
    events = []
    class OriginalContractError(Exception): pass
    class Contract:
        @property
        def schema(self):
            events.append('schema')
            raise OriginalContractError('original_contract_schema')
    for prepare in (original_goal, own('goal').prepare_goal):
        events.clear()
        with pytest.raises(OriginalContractError, match='^original_contract_schema$'):
            prepare('annotation', 'Child question', parent, Contract())
        assert events == ['schema']
        events.clear()
        prepare('annotation', 'Root question', None, Contract())
        assert events == []


def test_goal_reads_actual_live_runtime_provider(monkeypatch):
    runtime = own('runtime'); marker = object(); events = []
    class GoalPort:
        @staticmethod
        def root(**kwargs):
            events.append(kwargs)
            return marker
    monkeypatch.setattr(runtime, 'EpisodeGoal', GoalPort)
    for prepare in (original_goal, own('goal').prepare_goal):
        assert prepare('annotation', 'Same question', None, None) is marker
    assert events == [{'objective': 'Same question', 'result_contract': {'role': 'annotation'}}] * 2


def test_rebound_public_constructor_remains_inherited(tmp_path, monkeypatch):
    runtime = own('runtime'); original = runtime.DecisionSource.__init__; seen = []
    def rebound(self, *args, **kwargs):
        seen.append(type(self))
        return original(self, *args, **kwargs)
    with actual_workflow(tmp_path) as workflow:
        monkeypatch.setattr(runtime.DecisionSource, '__init__', rebound)
        for role, expected in (('annotation', own('episode').AnnotationTask),
                               ('improvement', own('annotation_improvement.episode').ImprovementTask)):
            item = workflow.build(role, role, 'Original inherited constructor', workflow.store.validate_scope())
            assert type(item.source) is expected
            assert type(item.source).__init__ is rebound
        assert seen == [own('episode').AnnotationTask, own('annotation_improvement.episode').ImprovementTask]
