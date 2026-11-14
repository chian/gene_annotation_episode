"""Original A106 improvement boundaries; no new nested scientific credit.

Real Store/Workflow/Journal/Episode constructors and numerical controller are
used. Returned tool results are explicit engineering ports. The authentic
nested improvement credit rejection is retained before child acquisition.
"""
import asyncio
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import inspect
import json

import pytest

from ...tests.test_implicit_annotation_parent import (
    actual_workflow, module, root, original_function, predecessor_source,
    no_external,
)


@contextmanager
def improvement_workflow(directory):
    def configured(*args, **kwargs):
        return module('runtime').Workflow(*args, root_role='improvement', **kwargs)
    with actual_workflow(directory, cls=configured) as workflow:
        yield workflow


def improvement(workflow, key='root'):
    return workflow.build('improvement', key, 'Preserve the original unresolved finding',
                          workflow.store.validate_scope())


def test_improvement_has_substantive_live_owners_and_original_protocol(tmp_path):
    rt, owner = module('runtime'), module('annotation_improvement.episode')
    assert owner.ImprovementTask.__bases__ == (rt._annotation_original_DecisionSource,)
    with improvement_workflow(tmp_path) as workflow:
        source = improvement(workflow).source
        assert type(source) is owner.ImprovementTask
        assert workflow.tree.root.name == 'improvement'
        assert workflow.specialist(source) is None
        assert workflow.declared_child_roles('improvement') == ('improvement',)
        assert owner.is_improvement_parent(workflow, source)
        for name, home in [('__init__', 'from_parent'), ('next', 'task'), ('call', 'provider'),
                           ('execute', 'task_outcomes'), ('finish', 'to_parent')]:
            callback = inspect.getattr_static(owner.ImprovementTask, name)
            assert callback is getattr(module('annotation_improvement.' + home), name)
            assert callback.__globals__ is vars(rt)
        for name in ('checkpoint', 'restore', 'exchange_response', 'apply_response', 'instructions'):
            assert inspect.getattr_static(owner.ImprovementTask, name) is inspect.getattr_static(rt.DecisionSource, name)
        assert module('annotation_improvement.instructions').instructions.__globals__ is vars(module('runtime_prompt'))


def test_improvement_original_saved_request_credit_and_report(tmp_path):
    rt = module('runtime')
    with improvement_workflow(tmp_path) as workflow:
        scope = workflow.store.validate_scope()
        old = original_function('Workflow', 'build')(workflow, 'improvement', 'root',
            'Preserve the original unresolved finding', scope).source
        saved = dict(workflow.journal.row('runtime_episodes', old.episode_id))
        current = improvement(workflow).source
        assert type(old) is rt.DecisionSource
        assert type(current) is module('annotation_improvement.episode').ImprovementTask
        assert old.path == current.path == (('improvement', 'root'),)
        assert old.request.as_record() == current.request.as_record()
        assert old.episode_id == current.episode_id
        assert dict(workflow.journal.row('runtime_episodes', current.episode_id)) == saved
        for name in ('source_credit_view', 'working_state', 'facts'):
            before = original_function('Workflow', name)(workflow, old)
            after = getattr(rt.Workflow, name)(workflow, current)
            assert before == after
        with pytest.raises(rt.WorkflowError, match='reconstructed immutable assignment differs'):
            workflow.build('improvement', 'root', 'A changed objective', scope)


@pytest.mark.parametrize('role,member', [
    ('annotation', 'next'), ('annotation', 'call'), ('annotation', 'execute'),
    ('annotation', 'instruction_composer'),
    ('improvement', '__init__'), ('improvement', 'next'), ('improvement', 'call'),
    ('improvement', 'execute'), ('improvement', 'finish'), ('improvement', 'instruction_composer'),
])
def test_original_public_member_rebinding_keeps_exact_fallback(tmp_path, monkeypatch, role, member):
    rt = module('runtime')
    original = rt._annotation_original_DecisionSource
    events = []
    prior = vars(original).get(member)
    def replacement(*args, **kwargs):
        events.append(member)
        if member == '__init__':
            return prior(*args, **kwargs)
        if member == 'instruction_composer':
            return 'original caller instruction composer'
        raise AssertionError('constructor_must_not_invoke_rebound_' + member)
    value = staticmethod(replacement) if member == 'instruction_composer' else replacement
    monkeypatch.setattr(original, member, value, raising=member != 'instruction_composer')
    context = actual_workflow(tmp_path) if role == 'annotation' else improvement_workflow(tmp_path)
    with context as workflow:
        source = (root(workflow) if role == 'annotation' else improvement(workflow)).source
        assert type(source) is original
        assert events == (['__init__'] if member == '__init__' else [])
        if member == 'instruction_composer':
            assert workflow.services.instructions(source, {}) == 'original caller instruction composer'
            assert events == ['instruction_composer']


@pytest.mark.parametrize('parent_role', ['annotation', 'improvement'])
def test_original_nested_credit_rejection_through_real_selected_request(tmp_path, monkeypatch, parent_role):
    rt = module('runtime')
    context = actual_workflow(tmp_path) if parent_role == 'annotation' else improvement_workflow(tmp_path)
    with context as workflow:
        source = (root(workflow) if parent_role == 'annotation' else improvement(workflow)).source
        schema = rt._object({'unresolved': {'type': 'boolean'}})
        selection = {'kind': 'child', 'goal': 'Preserve the unresolved original question',
            'scope': rt._plain(source.scope), 'purpose': 'Return the original qualified finding',
            'schema_json': json.dumps(schema), 'initial_report_json': '{"unresolved":true}'}
        endpoint = module(('annotation_improvement.' if parent_role == 'improvement' else '')
                          + 'to_child_annotation_improvement')
        original_prepare = endpoint.prepare_request
        calls = []
        def traced(*args, **kwargs):
            calls.append((args[3], args[5]))
            return original_prepare(*args, **kwargs)
        monkeypatch.setattr(endpoint, 'prepare_request', traced)
        observed = []
        for original in (True, False):
            calls.clear()
            workflow.store.db.execute('SAVEPOINT original_improvement_boundary')
            try:
                with monkeypatch.context() as patched:
                    if original:
                        patched.setattr(workflow, 'build', original_function('Workflow', 'build').__get__(workflow))
                    parent = predecessor_source(workflow, source) if original else source
                    selected = original_function('Workflow', 'selected') if original else rt.Workflow.selected
                    with pytest.raises(ValueError, match='^scientific_task_credit_not_declared:improvement$') as error:
                        selected(workflow, parent, deepcopy(selection), 0)
                    observed.append((type(error.value), error.value.args))
                assert calls == ([] if original else [(0, 'improvement')])
                assert workflow.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
                assert workflow.store.db.execute('SELECT COUNT(*) FROM runtime_episodes').fetchone()[0] == 1
            finally:
                workflow.store.db.execute('ROLLBACK TO original_improvement_boundary')
                workflow.store.db.execute('RELEASE original_improvement_boundary')
        assert observed[0] == observed[1]


@pytest.mark.parametrize('task_aware', [False, True])
def test_improvement_controller_original_factory_order(tmp_path, task_aware):
    rt, numerical = module('runtime'), module('numerical')
    with improvement_workflow(tmp_path) as workflow:
        source = improvement(workflow).source
        events, old_row = [], workflow.journal.row
        settings = numerical.YieldParameters(uncertainty_alpha=0.05)
        def row(*args, **kwargs):
            events.append('journal')
            return old_row(*args, **kwargs)
        class Factory:
            @property
            def requires_original_task(self):
                events.append('requires_original_task')
                return task_aware
            def __call__(self, path, initial, **kwargs):
                events.append('factory')
                assert path == source.path
                if task_aware:
                    assert kwargs['context'].role == 'improvement'
                    assert kwargs['task_key'] is kwargs['credit_definition'] is None
                else:
                    assert kwargs == {}
                return numerical.YieldController('original_improvement', initial, 0.5, settings)
        workflow.journal.row, workflow.controller_factory = row, Factory()
        compared = []
        for fn in (original_function('Workflow', 'controller'), rt.Workflow.controller):
            events.clear()
            result = fn(workflow, source.path)
            assert result.controller.settings is settings and result.controller.cost == 0.5
            assert events == ['journal', 'requires_original_task', 'factory']
            compared.append(list(events))
        assert compared[0] == compared[1]


@pytest.mark.parametrize('status', ['completed', 'invalid', 'failed', 'unavailable'])
def test_improvement_returned_action_enters_original_iterator_and_replays(tmp_path, monkeypatch, status):
    rt = module('runtime')
    # Equal external clock input for the two original/current comparisons.
    # Keep the full original pending-work record; never strip its timestamp.
    captured_at = '2026-11-13T12:00:00+00:00'
    monkeypatch.setattr(rt, '_now', lambda: captured_at)
    compared = []
    for original in (True, False):
        with improvement_workflow(tmp_path / str(original)) as workflow:
            episode = improvement(workflow)
            source = episode.source
            if original:
                source.execute = original_function('DecisionSource', 'execute').__get__(source)
            action = {'kind': 'tool', 'tool': 'episode.estimate_wait', 'arguments': {
                'condition': {'version': 'event_condition_v1', 'events': [], 'reconsider_at': None}}}
            declaration = rt._wait_estimate_operation()
            assert declaration['name'] == action['tool']
            rt.Draft202012Validator(declaration['input_schema']).validate(action['arguments'])
            # A supplied saved model response is the original observation
            # controller's genuine decision-context prerequisite. It is not a
            # model/provider execution or a fabricated timing measurement.
            decision_schema = workflow.action_schema(source)
            decision_context = {'execution_expectations': None}
            decision_response = {'selection': deepcopy(action), 'report_update': {}}
            rt.Draft202012Validator(decision_schema).validate(decision_response)
            workflow.journal.save('runtime_model_calls', {'episode_id': source.episode_id,
                'call_index': 0, 'purpose': 'decision',
                'request': rt._json({'context': decision_context, 'schema': decision_schema}),
                'response': rt._json(decision_response)})
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
            async def next_unit(view, **kwargs):
                assert view.units_consumed == 0 and not kwargs
                return unit
            source.next = next_unit
            observed = asyncio.run(episode.run_unit_async(workflow.context, expected_label=unit.label))
            saved = dict(workflow.journal.row('runtime_actions', source.episode_id, 0))
            rows = [dict(row) for row in workflow.store.db.execute(
                'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=?', (workflow.run_id, source.episode_id))]
            assert len(rows) == 1 and calls == ['returned']
            assert rt.observes_action_outcome('tool', status)
            assert json.loads(saved['result'])['status'] == status and saved['credit'] is not None
            assert json.loads(saved['result'])['pending_work_after_action'] == {
                'version': 'pending_work_v2', 'captured_at': captured_at, 'items': []}
            replay = asyncio.run(workflow.selected(source, deepcopy(action), 0).acquire_async(workflow.context))
            assert calls == ['returned'] and replay.contribution.controller_input == observed.controller_input
            compared.append((json.loads(saved['action']), json.loads(saved['result']), saved['credit'],
                             json.loads(rows[0]['observation'])))
    assert compared[0] == compared[1]
