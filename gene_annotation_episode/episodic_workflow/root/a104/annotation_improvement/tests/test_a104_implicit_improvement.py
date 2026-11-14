"""Preserve A104's existing unregistered improvement, including its failures.

These controls use genuine constructors/typed contracts and original method
oracles. Supplied returned actions are engineering ports. A missing original
nested task-credit definition is never replaced by a permissive projector.
"""
import ast
import asyncio
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import inspect
import json
from types import SimpleNamespace
import textwrap

import pytest

from ...tests.test_a104_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, original_node,
    own, root, forbidden,
)


@contextmanager
def improvement_workflow(directory, *, workflow_type=None):
    runtime = own('runtime')
    def configured(*args, **kwargs):
        return (workflow_type or runtime.Workflow)(*args, root_role='improvement', **kwargs)
    with actual_workflow(directory, workflow_type=configured) as workflow:
        yield workflow


def improvement(workflow, key='root'):
    return workflow.build('improvement', key, 'Resolve the original scientific distinction', workflow.store.validate_scope())


def test_improvement_uses_original_protocol_and_own_live_definers(tmp_path):
    runtime = own('runtime'); owner = own('annotation_improvement.episode')
    assert owner.ImprovementTask.__bases__ == (runtime._annotation_original_decision_source,)
    with improvement_workflow(tmp_path) as workflow:
        item = improvement(workflow)
        assert type(item.source) is owner.ImprovementTask
        assert workflow.specialist(item.source) is None
        assert workflow.declared_child_roles('improvement') == ('improvement',)
        assert workflow.tree.root.name == 'improvement'
        assert owner.is_improvement_parent(workflow, item.source)
        for name in ('__init__', 'checkpoint', 'restore', 'exchange_response', 'apply_response'):
            assert inspect.getattr_static(owner.ImprovementTask, name) is inspect.getattr_static(runtime.DecisionSource, name)
        for name, module in [('next', 'task'), ('call', 'provider'), ('execute', 'task_outcomes'), ('finish', 'to_parent')]:
            callback = getattr(owner.ImprovementTask, name)
            assert callback is getattr(own('annotation_improvement.' + module), name)
            assert callback.__globals__ is vars(runtime)
        for name in ('execute', 'finish'):
            current, = ast.parse(textwrap.dedent(inspect.getsource(getattr(owner.ImprovementTask, name)))).body
            assert ast.dump(current, include_attributes=False) == ast.dump(original_node('DecisionSource', name), include_attributes=False)
        assert own('annotation_improvement.instructions').instructions.__globals__ is vars(own('runtime_prompt'))


def test_original_and_private_improvement_saved_identity_and_projector(tmp_path):
    runtime = own('runtime')
    with improvement_workflow(tmp_path) as workflow:
        calls = []
        def projector(store, scope, **kwargs):
            assert store is workflow.store
            calls.append((runtime._plain(scope), kwargs))
            return {'credit': 1.25, 'a104_supplied_definition': 'original controlled projector'}
        workflow.project_credit = projector
        old = original_function('Workflow', 'build')(
            workflow, 'improvement', 'root', 'Resolve the original scientific distinction', workflow.store.validate_scope())
        saved = dict(workflow.journal.row('runtime_episodes', old.source.episode_id))
        current = improvement(workflow)
        assert type(old.source) is runtime.DecisionSource
        assert type(current.source) is own('annotation_improvement.episode').ImprovementTask
        assert current.source.episode_id == old.source.episode_id
        assert current.source.path == old.source.path == (('improvement', 'root'),)
        assert current.source.request.as_record() == old.source.request.as_record()
        assert dict(workflow.journal.row('runtime_episodes', current.source.episode_id)) == saved
        values = []
        for fn, source in [(original_function('Workflow', 'source_credit_view'), old.source),
                           (runtime.Workflow.source_credit_view, current.source)]:
            calls.clear(); values.append(fn(workflow, source))
            assert calls == [(runtime._plain(source.scope), {})]
        assert values[0] == values[1]
        assert values[1]['credit'] == 1.25


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
def test_original_nested_missing_credit_rejection_keeps_request_and_order(tmp_path, monkeypatch, parent_role):
    runtime = own('runtime')
    context = actual_workflow(tmp_path) if parent_role == 'annotation' else improvement_workflow(tmp_path)
    with context as workflow:
        parent = root(workflow) if parent_role == 'annotation' else improvement(workflow)
        source = parent.source
        schema = runtime._object({'unresolved': {'type': 'boolean'}})
        selection = {'kind': 'child', 'goal': 'Investigate the same unresolved question',
                     'scope': runtime._plain(source.scope), 'purpose': 'Return the actual unresolved state',
                     'schema_json': json.dumps(schema), 'initial_report_json': '{"unresolved": true}'}
        outgoing = own(('annotation_improvement.' if parent_role == 'improvement' else '') + 'to_child_annotation_improvement')
        callback = outgoing.prepare_parent_request
        actual_calls = []
        def traced(*args, **kwargs):
            actual_calls.append((args[3], args[5]))
            return callback(*args, **kwargs)
        monkeypatch.setattr(outgoing, 'prepare_parent_request', traced)
        original_build = original_function('Workflow', 'build')
        outcomes = []
        for original in (True, False):
            # The original and candidate perform the same real construction and
            # journal writes inside a rollback-only engineering transaction.
            workflow.store.db.execute('SAVEPOINT improvement_original_comparison')
            actual_calls.clear()
            try:
                with monkeypatch.context() as changed:
                    if original:
                        changed.setattr(workflow, 'build', original_build.__get__(workflow))
                    selected = original_function('Workflow', 'selected') if original else runtime.Workflow.selected
                    with pytest.raises(ValueError, match='^scientific_task_credit_not_declared:improvement$') as error:
                        selected(workflow, source, deepcopy(selection), 0)
                assert actual_calls == ([] if original else [(0, 'improvement')])
                assert workflow.store.db.execute('SELECT COUNT(*) FROM runtime_episodes').fetchone()[0] == 1
                outcomes.append((type(error.value), error.value.args))
            finally:
                workflow.store.db.execute('ROLLBACK TO improvement_original_comparison')
                workflow.store.db.execute('RELEASE improvement_original_comparison')
        assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('task_aware', (False, True))
def test_improvement_controller_preserves_actual_factory_order(tmp_path, task_aware):
    runtime = own('runtime'); numerical = own('numerical')
    with improvement_workflow(tmp_path) as workflow:
        source = improvement(workflow).source
        events = []; original_row = workflow.journal.row
        settings = numerical.YieldParameters()
        def row(*args, **kwargs):
            events.append(('journal', args))
            return original_row(*args, **kwargs)
        class Factory:
            @property
            def requires_original_task(self):
                events.append(('requires_original_task', task_aware)); return task_aware
            def __call__(self, path, initial, **kwargs):
                if task_aware:
                    assert kwargs['context'].role == 'improvement'
                    assert kwargs['context'].path == source.path
                    assert kwargs['task_key'] is kwargs['credit_definition'] is None
                else:
                    assert kwargs == {}
                events.append(('factory', path, initial, tuple(kwargs)))
                return numerical.YieldController('original-improvement-controller', initial, .5, settings)
        workflow.journal.row = row; workflow.controller_factory = Factory()
        traces = []
        for fn in (original_function('Workflow', 'controller'), runtime.Workflow.controller):
            events.clear(); result = fn(workflow, source.path)
            assert type(result) is runtime.ExecutionContextController
            assert result.controller.settings is settings and result.controller.cost == .5
            assert [event[0] for event in events] == ['journal', 'requires_original_task', 'factory']
            traces.append(list(events))
        assert traces[0] == traces[1]


@pytest.mark.parametrize('status', ('completed', 'invalid', 'failed', 'unavailable'))
def test_improvement_returned_units_enter_original_iterator(tmp_path, monkeypatch, status):
    runtime = own('runtime'); compared = []
    # Equal supplied clock input, not removal/normalization of real output.
    observed_time = '2026-11-13T00:00:00+00:00'
    monkeypatch.setattr(runtime, '_now', lambda: observed_time)
    for original in (True, False):
        with improvement_workflow(tmp_path / str(original)) as workflow:
            item = improvement(workflow); source = item.source
            if original:
                source.execute = original_function('DecisionSource', 'execute').__get__(source)
            # Improvement has the original unrestricted scientific tool gate;
            # use its real runtime wait-information declaration nonetheless.
            action = {'kind': 'tool', 'tool': 'episode.estimate_wait', 'arguments': {
                'condition': {'version': 'event_condition_v1', 'events': [], 'reconsider_at': None}}}
            declaration = runtime._wait_estimate_operation()
            assert declaration['name'] == action['tool']
            runtime.Draft202012Validator(declaration['input_schema']).validate(action['arguments'])
            # Preserve the original controller's real saved-model-call input.
            # Supplied engineering response, absent model execution and unknown
            # expectations/timing are separate from the executed action result.
            decision_schema = workflow.action_schema(source)
            decision_context = {'execution_expectations': None}
            decision_response = {'selection': deepcopy(action), 'report_update': {}}
            runtime.Draft202012Validator(decision_schema).validate(decision_response)
            workflow.journal.save('runtime_model_calls', {'episode_id': source.episode_id,
                'call_index': 0, 'purpose': 'decision',
                'request': runtime._json({'context': decision_context, 'schema': decision_schema}),
                'response': runtime._json(decision_response)})
            saved_call = dict(workflow.journal.row('runtime_model_calls', source.episode_id, 0))
            workflow.provider = SimpleNamespace(complete=forbidden)
            call = original_function('DecisionSource', 'call') if original else type(source).call
            response, index, context, schema = asyncio.run(call(source, {}, {}))
            assert (response, index, context, schema) == (decision_response, 0, decision_context, decision_schema)
            assert source.calls == 1
            assert dict(workflow.journal.row('runtime_model_calls', source.episode_id, 0)) == saved_call
            outcome = {'status': status, 'record_refs': [], 'changed_record_refs': [],
                       'feedback': {'category': 'controlled_original_return', 'status': status}}
            calls = []
            workflow.journal.measure = lambda *_: nullcontext()
            workflow.execute = lambda *_args, **_kwargs: (calls.append('returned'), deepcopy(outcome))[1]
            workflow.receive_native_outcome = lambda *_: None
            workflow.receive_outcome = lambda *_: None
            async def scoring(_source, _index, result): return result
            workflow.automatic_score_updates = scoring
            unit = workflow.selected(source, deepcopy(action), 0)
            async def next_unit(view, **kwargs):
                assert view.units_consumed == 0 and not kwargs
                return unit
            source.next = next_unit
            observed = asyncio.run(item.run_unit_async(workflow.context, expected_label=unit.label))
            saved = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
            rows = [dict(r) for r in workflow.store.db.execute('SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=?', (workflow.run_id, source.episode_id))]
            assert len(rows) == 1 and calls == ['returned']
            assert runtime.observes_action_outcome('tool', status)
            assert json.loads(saved['result'])['status'] == status and saved['credit'] is not None
            assert json.loads(saved['result'])['pending_work_after_action'] == {
                'version': 'pending_work_v2', 'captured_at': observed_time, 'items': []}
            replay = asyncio.run(workflow.selected(source, deepcopy(action), 0).acquire_async(workflow.context))
            assert calls == ['returned'] and replay.contribution.controller_input == observed.controller_input
            compared.append((json.loads(saved['action']), json.loads(saved['result']), saved['credit'], json.loads(rows[0]['observation'])))
    assert compared[0] == compared[1]


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
def test_nominal_parent_guards_do_not_compare_rebound_class_values(tmp_path, monkeypatch, parent_role):
    runtime = own('runtime')
    context = actual_workflow(tmp_path) if parent_role == 'annotation' else improvement_workflow(tmp_path)
    with context as workflow:
        source = (root(workflow) if parent_role == 'annotation' else improvement(workflow)).source
        calls = []
        class Rebound:
            def __eq__(self, other):
                calls.append('equality'); raise AssertionError('optional_selector_called_equality')
        workflow.job_episodes = SimpleNamespace(roles=('job_launch',))
        monkeypatch.setattr(runtime, 'HomologySubmission', Rebound())
        selector = own('episode').is_annotation_parent if parent_role == 'annotation' else own('annotation_improvement.episode').is_improvement_parent
        assert selector(workflow, source) is False
        assert calls == []


@pytest.mark.parametrize('boundary', ('workflow', 'public_source'))
def test_improvement_preserves_original_custom_source_precedence(tmp_path, monkeypatch, boundary):
    runtime = own('runtime'); original = runtime._annotation_original_decision_source
    class CallerSource(original): pass
    class CallerWorkflow(runtime.Workflow): pass
    if boundary == 'public_source':
        monkeypatch.setattr(runtime, 'DecisionSource', CallerSource)
    with improvement_workflow(tmp_path, workflow_type=CallerWorkflow if boundary == 'workflow' else None) as workflow:
        current = improvement(workflow)
        assert type(current.source) is (original if boundary == 'workflow' else CallerSource)
        assert own('annotation_improvement.episode').ImprovementTask.__bases__ == (original,)


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
@pytest.mark.parametrize('method', ('next', 'call', 'execute', 'finish', 'instruction_composer'))
def test_rebound_original_default_method_keeps_public_constructor(tmp_path, monkeypatch, parent_role, method):
    runtime = own('runtime')
    context = actual_workflow(tmp_path) if parent_role == 'annotation' else improvement_workflow(tmp_path)
    with context as workflow:
        def caller_method(self, *args, **kwargs):
            if method == 'instruction_composer':
                return ('original caller composer', args, kwargs)
            raise AssertionError('construction must not execute caller method')
        monkeypatch.setattr(runtime.DecisionSource, method, caller_method, raising=method != 'instruction_composer')
        current = root(workflow) if parent_role == 'annotation' else improvement(workflow)
        assert type(current.source) is runtime.DecisionSource
        assert inspect.getattr_static(type(current.source), method) is caller_method
        assert type(current.source) is runtime._annotation_original_decision_source
        if method == 'instruction_composer':
            context = {'controlled_original_context': True}
            assert workflow.services.instructions(current.source, context) == (
                'original caller composer', (context,), {})
