"""Original A101 credit, report, waiting and continuation ownership controls.

Actual constructors and original projector/controller interfaces are used.
Controlled results do not assert scientific correctness, autonomous decisions,
native execution, or whole saved-workflow restoration.
"""
import ast
from contextlib import nullcontext
import inspect
import textwrap
import pytest

from .test_a101_implicit_parent_protocol import (
    actual_workflow, no_external_execution, original_function, original_node, own, root,
)


@pytest.mark.parametrize('method', (
    'receive_form', '_receive_form', 'wait_estimate', 'validate_wait_selection',
    'waiting_support', 'perform_selected_wait', 'receive_outcome',
))
def test_shared_original_workflow_method_has_one_live_definer(method):
    runtime = own('runtime')
    current = inspect.getattr_static(runtime.Workflow, method)
    assert current.__globals__ is vars(runtime)
    assert current.__qualname__ == 'Workflow.' + method
    candidate, = ast.parse(textwrap.dedent(inspect.getsource(current))).body
    assert ast.dump(candidate, include_attributes=False) == ast.dump(original_node('Workflow', method), include_attributes=False)
    owner = ('library.source_return_admission' if method in ('receive_form', '_receive_form')
             else 'received_outcomes' if method == 'receive_outcome' else 'decision_waiting')
    assert current is getattr(own(owner), method)


@pytest.mark.parametrize('shape', ('scalar', 'components', 'failure'))
def test_original_projector_inputs_results_and_failure_order(tmp_path, shape):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        calls = []
        class ProjectorFailure(Exception): pass
        def projector(store, scope, **kwargs):
            assert store is workflow.store
            calls.append((scope, kwargs))
            if shape == 'failure':
                raise ProjectorFailure('original A101 projector boundary')
            return 2.0 if shape == 'scalar' else {
                'credit': 2.0, 'axis_components': {'controlled-original-component': 2.0},
                'a101_sheet': {'source': 'controlled-original-projector'},
            }
        workflow.project_credit = projector
        results = []
        for fn in (original_function('Workflow', 'source_credit_view'), runtime.Workflow.source_credit_view):
            calls.clear()
            if shape == 'failure':
                with pytest.raises(ProjectorFailure, match='original A101 projector boundary') as error:
                    fn(workflow, source)
                result = (type(error.value), error.value.args)
            else:
                result = fn(workflow, source)
                assert result['credit'] == 2.0
                if shape == 'components':
                    assert result['a101_sheet'] == {'source': 'controlled-original-projector'}
            assert calls == [(runtime._plain(source.scope), {})]
            results.append((result, list(calls)))
        assert results[0] == results[1]


@pytest.mark.parametrize('snapshot', ([], ()))
def test_invalid_credit_snapshot_rejected_before_any_original_dispatch(tmp_path, snapshot):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        calls = []
        def forbidden(*args, **kwargs):
            calls.append('dispatch'); raise AssertionError('credit_validation_order_changed')
        workflow.is_job_source = forbidden
        workflow.specialist = forbidden
        workflow.project_credit = forbidden
        for fn in (original_function('Workflow', 'source_credit_view'), runtime.Workflow.source_credit_view):
            with pytest.raises(TypeError, match='credit_binding_snapshot_must_be_dict'):
                fn(workflow, source, binding_snapshot=snapshot)
        assert calls == []


@pytest.mark.parametrize('task_aware', (False, True))
def test_controller_keeps_original_journal_factory_order_and_settings(tmp_path, task_aware):
    runtime = own('runtime'); numerical = own('numerical')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        events = []
        settings = numerical.YieldParameters()
        original_row = workflow.journal.row
        def row(*args, **kwargs):
            events.append(('journal', args))
            return original_row(*args, **kwargs)
        class Factory:
            @property
            def requires_original_task(self):
                events.append(('requires_original_task', task_aware))
                return task_aware
            def __call__(self, path, initial, **kwargs):
                if task_aware:
                    context = kwargs['context']
                    assert type(context) is runtime.BindingContext
                    assert context.path == source.path and context.role == 'annotation'
                    assert context.episode_id == source.episode_id
                    assert kwargs['task_key'] is kwargs['credit_definition'] is None
                else:
                    assert kwargs == {}
                events.append(('factory', path, initial, tuple(kwargs)))
                return numerical.YieldController('actual-original-controller', initial, .5, settings)
        workflow.journal.row = row
        workflow.controller_factory = Factory()
        traces = []
        for fn in (original_function('Workflow', 'controller'), runtime.Workflow.controller):
            events.clear()
            actual = fn(workflow, source.path)
            assert type(actual) is runtime.ExecutionContextController
            assert type(actual.controller) is numerical.YieldController
            assert actual.controller.settings is settings and actual.controller.cost == .5
            assert actual.controller.epoch == 'actual-original-controller'
            assert events[0] == ('journal', ('runtime_episodes', source.episode_id))
            assert [e[0] for e in events] == ['journal', 'requires_original_task', 'factory']
            traces.append(list(events))
        assert traces[0] == traces[1]


def test_annotation_report_projection_keeps_original_fields_and_callback(tmp_path):
    runtime = own('runtime')
    with actual_workflow(tmp_path) as workflow:
        source = root(workflow).source
        calls = []
        def annotation_score(store, scope, **kwargs):
            assert store is workflow.store
            calls.append((scope, kwargs))
            return {'credit': .75}
        workflow.project_annotation_score = annotation_score
        outcomes = []
        for fn in (original_function('Workflow', 'facts'), runtime.Workflow.facts):
            calls.clear()
            facts = fn(workflow, source, completion_record=None)
            assert facts['annotation_score'] == .75 and facts['credit'] == 0.0
            assert calls == [(runtime._plain(source.scope), {})]
            outcomes.append((facts, list(calls)))
        assert outcomes[0] == outcomes[1]
