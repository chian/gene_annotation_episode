"""A101's existing improvement source and its original conditional failures.

Actual constructors, Store, Journal, typed request and continuation controller
are used. Supplied returned results exercise the iterator, not wait execution,
native work, model autonomy or successful nested scientific credit.
"""
import ast
import asyncio
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import inspect
import json
import textwrap
import pytest

from ...tests.test_a101_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, original_node, own, root,
)


from ...tests.a101_implicit_parent_test_context import improvement_workflow, improvement


def test_private_improvement_has_actual_own_definitions_and_live_namespaces(tmp_path):
    runtime = own('runtime'); task = own('annotation_improvement.task').ImprovementTask
    assert task.__bases__ == (runtime._a101_annotation_original_source_type,)
    with improvement_workflow(tmp_path) as workflow:
        item = improvement(workflow)
        assert type(item.source) is task and workflow.specialist(item.source) is None
        assert workflow.tree.root.name == 'improvement'
        assert workflow.declared_child_roles('improvement') == ('improvement',)
        assert own('annotation_improvement.episode').is_improvement_source(workflow, item.source)
        for name, module in (('__init__', 'from_parent'), ('next', 'task'), ('call', 'task_provider'),
                             ('execute', 'task_outcomes'), ('finish', 'to_parent'),
                             ('suspension_changed', 'waiting'), ('decision_state', 'internal_summary')):
            fn = inspect.getattr_static(task, name)
            assert fn is getattr(own('annotation_improvement.' + module), name)
            assert fn.__globals__ is vars(runtime)
        for name in ('__init__', 'execute', 'finish', 'suspension_changed'):
            actual, = ast.parse(textwrap.dedent(inspect.getsource(getattr(task, name)))).body
            assert ast.dump(actual, include_attributes=False) == ast.dump(original_node('DecisionSource', name), include_attributes=False)
        for name in ('checkpoint', 'restore', 'apply_response', 'exchange_response'):
            assert inspect.getattr_static(task, name) is inspect.getattr_static(runtime.DecisionSource, name)
        assert own('annotation_improvement.task_instructions').instructions.__globals__ is vars(own('runtime_prompt'))


def test_original_improvement_goal_saved_request_credit_and_report_are_preserved(tmp_path):
    runtime = own('runtime')
    with improvement_workflow(tmp_path) as workflow:
        calls = []
        def projector(store, scope, **kwargs):
            assert store is workflow.store
            calls.append((runtime._plain(scope), kwargs))
            return {'credit': 1.25, 'a101_supplied_definition': 'original controlled projector'}
        workflow.project_credit = projector
        old = original_function('Workflow', 'build')(workflow, 'improvement', 'root',
            'Resolve the original annotation question', workflow.store.validate_scope())
        saved = dict(workflow.journal.row('runtime_episodes', old.source.episode_id))
        current = improvement(workflow)
        assert type(old.source) is runtime.DecisionSource
        assert type(current.source) is own('annotation_improvement.task').ImprovementTask
        assert current.source.request.as_record() == old.source.request.as_record()
        assert current.source.path == old.source.path == (('improvement', 'root'),)
        assert current.source.episode_id == old.source.episode_id
        assert dict(workflow.journal.row('runtime_episodes', current.source.episode_id)) == saved
        values = []
        for fn, source in ((original_function('Workflow', 'source_credit_view'), old.source),
                           (runtime.Workflow.source_credit_view, current.source)):
            calls.clear(); values.append(fn(workflow, source))
            assert calls == [(runtime._plain(source.scope), {})]
        assert values[0] == values[1] and values[1]['credit'] == 1.25
        assert original_function('Workflow', 'facts')(workflow, old.source) == runtime.Workflow.facts(workflow, current.source)
        assert original_function('Workflow', 'source_credit_binding')(workflow, old.source) == workflow.source_credit_binding(current.source)


@pytest.mark.parametrize('task_aware', (False, True))
def test_improvement_continuation_keeps_original_factory_order_and_settings(tmp_path, task_aware):
    runtime = own('runtime'); numerical = own('numerical')
    with improvement_workflow(tmp_path) as workflow:
        source = improvement(workflow).source
        events = []; original_row = workflow.journal.row; settings = numerical.YieldParameters()
        def row(*args, **kwargs):
            events.append(('journal', args)); return original_row(*args, **kwargs)
        class Factory:
            @property
            def requires_original_task(self):
                events.append(('requires_original_task', task_aware)); return task_aware
            def __call__(self, path, initial, **kwargs):
                if task_aware:
                    assert type(kwargs['context']) is runtime.BindingContext
                    assert kwargs['context'].role == 'improvement' and kwargs['context'].path == source.path
                    assert kwargs['task_key'] is kwargs['credit_definition'] is None
                else:
                    assert kwargs == {}
                events.append(('factory', path, initial, tuple(kwargs)))
                return numerical.YieldController('actual-improvement-controller', initial, .5, settings)
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
def test_improvement_returned_actions_enter_original_iterator_and_replay(tmp_path, monkeypatch, status):
    runtime = own('runtime'); compared = []
    supplied_time = '2026-11-13T00:00:00+00:00'
    monkeypatch.setattr(runtime, '_now', lambda: supplied_time)
    for original in (True, False):
        with improvement_workflow(tmp_path / str(original)) as workflow:
            item = improvement(workflow); source = item.source
            if original:
                source.execute = original_function('DecisionSource', 'execute').__get__(source)
            action = {'kind': 'tool', 'tool': 'episode.estimate_wait', 'arguments': {
                'condition': {'version': 'event_condition_v1', 'events': [], 'reconsider_at': None}}}
            declared, = [entry for entry in workflow.catalog(source.scope, source=source) if entry['name'] == action['tool']]
            runtime.Draft202012Validator(declared['input_schema']).validate(action['arguments'])
            # Explicit supplied saved-response port; keep actual Journal/call
            # replay and unknown model expectations/timing, without a provider.
            decision_schema = workflow.action_schema(source)
            decision_context = {'execution_expectations': None}
            decision_response = {'selection': deepcopy(action), 'report_update': {}}
            runtime.Draft202012Validator(decision_schema).validate(decision_response)
            workflow.journal.save('runtime_model_calls', {'episode_id': source.episode_id,
                'call_index': 0, 'purpose': 'decision',
                'request': runtime._json({'context': decision_context, 'schema': decision_schema}),
                'response': runtime._json(decision_response)})
            saved_call = dict(workflow.journal.row('runtime_model_calls', source.episode_id, 0))
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
            assert type(unit) is runtime.ActionLeaf
            async def next_unit(view, **kwargs):
                assert view.units_consumed == 0 and not kwargs
                return unit
            source.next = next_unit
            observed = asyncio.run(item.run_unit_async(workflow.context, expected_label=unit.label))
            saved = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
            observations = [dict(row) for row in workflow.store.db.execute(
                'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=?', (workflow.run_id, source.episode_id))]
            assert len(observations) == 1 and calls == ['returned']
            assert runtime.observes_action_outcome('tool', status)
            assert json.loads(saved['result'])['status'] == status and saved['credit'] is not None
            assert json.loads(saved['result'])['pending_work_after_action'] == {
                'version': 'pending_work_v2', 'captured_at': supplied_time, 'items': []}
            replay = asyncio.run(workflow.selected(source, deepcopy(action), 0).acquire_async(workflow.context))
            assert calls == ['returned'] and replay.contribution.controller_input == observed.controller_input
            compared.append((json.loads(saved['action']), json.loads(saved['result']), saved['credit'], json.loads(observations[0]['observation'])))
    assert compared[0] == compared[1]


@pytest.mark.parametrize('boundary', ('workflow', 'public_source'))
def test_improvement_keeps_original_custom_source_precedence(tmp_path, monkeypatch, boundary):
    runtime = own('runtime'); original = runtime._a101_annotation_original_source_type
    class CallerSource(original): pass
    class CallerWorkflow(runtime.Workflow): pass
    if boundary == 'public_source': monkeypatch.setattr(runtime, 'DecisionSource', CallerSource)
    with improvement_workflow(tmp_path, workflow_type=CallerWorkflow if boundary == 'workflow' else None) as workflow:
        current = improvement(workflow)
        assert type(current.source) is (original if boundary == 'workflow' else CallerSource)
        assert own('annotation_improvement.task').ImprovementTask.__bases__ == (original,)


@pytest.mark.parametrize('role,name', (
    ('annotation', 'next'), ('annotation', 'call'), ('annotation', 'execute'),
    ('annotation', 'decision_state'), ('annotation', 'instruction_composer'),
    ('improvement', '__init__'), ('improvement', 'next'), ('improvement', 'call'),
    ('improvement', 'execute'), ('improvement', 'finish'), ('improvement', 'suspension_changed'),
    ('improvement', 'decision_state'), ('improvement', 'instruction_composer'),
))
def test_private_selection_keeps_rebound_original_descriptors_without_early_callbacks(tmp_path, monkeypatch, role, name):
    runtime = own('runtime'); original = runtime._a101_annotation_original_source_type
    context = actual_workflow(tmp_path) if role == 'annotation' else improvement_workflow(tmp_path)
    with context as workflow:
        calls = []
        class OriginalOverride(Exception): pass
        def replacement(*args, **kwargs):
            calls.append(name)
            if name == 'instruction_composer': return 'original caller composer'
            raise OriginalOverride(name)
        monkeypatch.setattr(original, name, staticmethod(replacement) if name == 'instruction_composer' else replacement, raising=False)
        selector = (own('episode').selects_annotation_parent if role == 'annotation'
                    else own('annotation_improvement.episode').selects_improvement_parent)
        assert selector(workflow, role, (), None) is False and calls == []
        build = lambda: workflow.build(role, 'rebound', 'Preserve the original caller descriptor', workflow.store.validate_scope())
        if name == '__init__':
            with pytest.raises(OriginalOverride, match='^__init__$'): build()
            assert calls == ['__init__']
        else:
            item = build(); assert type(item.source) is original and calls == []
            if name == 'instruction_composer':
                assert workflow.services.instructions(item.source, {}) == 'original caller composer'
                assert calls == ['instruction_composer']


def test_private_improvement_wait_state_notification_matches_original(tmp_path):
    with improvement_workflow(tmp_path) as workflow:
        source = improvement(workflow).source
        condition = {'version': 'event_condition_v1', 'events': [], 'reconsider_at': None}
        assert workflow.execution_handle is None
        for value in (condition, None):
            observations = []
            for fn in (original_function('DecisionSource', 'suspension_changed'), type(source).suspension_changed):
                source._suspension_condition = 'prior'
                fn(source, deepcopy(value)); observations.append(source._suspension_condition)
            assert observations == [value, value]
