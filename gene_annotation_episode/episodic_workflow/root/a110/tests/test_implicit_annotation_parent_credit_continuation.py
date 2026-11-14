"""Original configured projection/continuation boundaries, without iteration.

The actual numerical YieldController is constructed with explicit original
credit/cost/settings. No observe/continuation/native/provider operation runs.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
from types import SimpleNamespace
import pytest
from . import test_implicit_annotation_parent as boundary


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', boundary.forbidden)
    monkeypatch.setattr('socket.socket.connect', boundary.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', boundary.forbidden)


@pytest.mark.parametrize('snapshot_kind', ('list', 'dict_subclass'))
def test_invalid_credit_snapshot_rejects_before_any_source_dispatch(tmp_path, snapshot_kind):
    runtime = boundary.module('runtime')
    class BorrowedDictionary(dict):
        pass
    for original in (True, False):
        with boundary.actual_workflow(tmp_path / str(original)) as workflow:
            source = boundary.root(workflow).source
            if original:
                source = boundary.predecessor_source(workflow, source)
            workflow.is_job_source = boundary.forbidden
            workflow.specialist = boundary.forbidden
            snapshot = [] if snapshot_kind == 'list' else BorrowedDictionary()
            method = (boundary.original_function(runtime, 'Workflow', 'source_credit_view')
                      if original else runtime.Workflow.source_credit_view)
            with pytest.raises(TypeError, match='credit_binding_snapshot_must_be_dict'):
                method(workflow, source, binding_snapshot=snapshot)


@pytest.mark.parametrize('shape', ('scalar', 'mapping', 'nonfinite'))
def test_original_custom_projector_shape_and_failure_are_preserved(tmp_path, shape):
    runtime = boundary.module('runtime')
    observations = []
    for original in (True, False):
        with boundary.actual_workflow(tmp_path / str(original)) as workflow:
            source = boundary.root(workflow).source
            if original:
                source = boundary.predecessor_source(workflow, source)
            events = []
            def project(store, scope, **kwargs):
                assert store is workflow.store
                events.append(('project', deepcopy(scope), deepcopy(kwargs)))
                return (0.75 if shape == 'scalar' else float('inf') if shape == 'nonfinite'
                        else {'credit': 0.75, 'axis_components': {'controlled_unknown': 0.25},
                              'interpretation': 'Original caller-supplied unresolved calculation'})
            workflow.project_credit = project
            previous = workflow.specialist
            def specialist(value):
                events.append(('specialist', value.episode_id))
                return previous(value)
            workflow.specialist = specialist
            method = (boundary.original_function(runtime, 'Workflow', 'source_credit_view')
                      if original else runtime.Workflow.source_credit_view)
            try:
                value = method(workflow, source)
            except ValueError as error:
                assert shape == 'nonfinite'
                value = {'failure': boundary.failure(error)}
            else:
                assert shape != 'nonfinite' and value['credit'] == 0.75
                assert ('axis_components' in value) == (shape == 'mapping')
            assert sum(event[0] == 'project' for event in events) == 1
            observations.append((runtime._plain(value), events))
    assert observations[0] == observations[1]


@pytest.mark.parametrize('port', ('ordinary', 'original_task', 'journal_failure', 'factory_failure'))
def test_original_controller_identity_journal_factory_and_numerical_operands(tmp_path, monkeypatch, port):
    runtime = boundary.module('runtime')
    numerical = boundary.module('numerical')
    observations = []
    for original in (True, False):
        with boundary.actual_workflow(tmp_path / str(original)) as workflow:
            source = boundary.root(workflow).source
            events = []
            identity_before = runtime.Episode.identity
            journal_before = workflow.journal.row
            def identity(context, grain, key, **kwargs):
                events.append(('identity', grain.name, key, kwargs.get('parent_path', ())))
                return identity_before(context, grain, key, **kwargs)
            def row(table, *keys):
                events.append(('journal', table, keys))
                if port == 'journal_failure':
                    raise RuntimeError('controlled_original_journal_failure')
                return journal_before(table, *keys)
            def factory(path, initial, **kwargs):
                declaration = {key: value.as_record() if hasattr(value, 'as_record') else value
                               for key, value in kwargs.items()}
                events.append(('factory', path, initial, runtime._plain(declaration)))
                if port == 'factory_failure':
                    raise RuntimeError('controlled_original_factory_failure')
                return numerical.YieldController('original_credit_controller', initial, 0.5,
                    numerical.YieldParameters(uncertainty_alpha=0.05))
            if port == 'original_task':
                factory.requires_original_task = True
            workflow.controller_factory = factory
            workflow.journal.row = row
            method = (boundary.original_function(runtime, 'Workflow', 'controller')
                      if original else runtime.Workflow.controller)
            with monkeypatch.context() as patch:
                patch.setattr(runtime.Episode, 'identity', staticmethod(identity))
                try:
                    controller = method(workflow, source.path)
                except RuntimeError as error:
                    assert port in ('journal_failure', 'factory_failure')
                    value = {'failure': boundary.failure(error)}
                else:
                    assert port in ('ordinary', 'original_task')
                    assert type(controller) is runtime.ExecutionContextController
                    assert type(controller.controller) is numerical.YieldController
                    assert controller.journal is workflow.journal
                    value = {'episode_id': controller.episode_id, 'epoch': controller.epoch,
                        'initial_credit': controller.controller.initial_credit,
                        'cost': controller.controller.cost, 'settings': controller.controller.settings.as_record(),
                        'include_native': controller.include_native,
                        'capture_present': callable(controller.capture_current_completion)}
            assert [event[0] for event in events][:2] == ['identity', 'journal']
            assert [event[0] for event in events] == (['identity', 'journal'] if port == 'journal_failure'
                                                    else ['identity', 'journal', 'factory'])
            observations.append((value, events))
    assert observations[0] == observations[1]
