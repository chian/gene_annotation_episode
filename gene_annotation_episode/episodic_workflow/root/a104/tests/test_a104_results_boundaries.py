"""Actual A104 Results request/receipt dispatch with retained original journals.

Uses the required original-admission fixture. Native acquisition, attribution
and scientific timing producers are not exercised by these boundary checks.
"""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from .test_a104_results_preservation import binding_home, frame, own_module, rows
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources


@pytest.fixture
def parent_binding(frame, binding_home):
    return own_module(binding_home.rsplit('/', 1)[0] + '/episode').HPCEpisode(SimpleNamespace(),
        store=frame.store, run_id=frame.run_id, directory=frame.store.path / 'workflow',
        resources=resources(), commissions={})


def boundary(frame, parent_binding):
    progress, attributed = [], []
    workflow = SimpleNamespace(store=frame.store, journal=frame.journal, run_id=frame.run_id,
        receipts=frame.receipts, specialist=lambda source: parent_binding,
        binding_context=lambda source: frame.parent, is_job_source=lambda source: False,
        progress_provider=SimpleNamespace(receive_form=lambda *args: progress.append(args)),
        episode_bindings=SimpleNamespace(received_form_references=lambda *args: []),
        native_timing_information=None, job_episodes=None,
        receive_tool_attributions=lambda *args, **kwargs: attributed.append((args, kwargs)) or [])
    source = SimpleNamespace(episode_id=frame.parent.episode_id, path=frame.parent.path, scope=frame.scope)
    return workflow, source, progress, attributed


def test_prepared_parent_request_reaches_original_saved_child_admission(frame, parent_binding):
    before = rows(frame.store)
    prepared = parent_binding.prepare_child_request(frame.parent, 'results', deepcopy(frame.assignment))
    assert prepared == frame.assignment
    admitted = frame.prepare(assignment=prepared)
    assert admitted == frame.assignment and admitted is not prepared
    admitted['selector']['offset'] = 99
    assert frame.prepare(assignment=prepared) == frame.assignment
    assert rows(frame.store) == before


def test_runtime_uses_original_cached_child_projection_before_live_ports(frame, parent_binding, monkeypatch):
    runtime = own_module('runtime')
    workflow, source, progress, attributed = boundary(frame, parent_binding)
    before = rows(frame.store)
    calls = []
    receiver_factory = getattr(parent_binding, 'child_report_receiver', None)
    receiver = None if receiver_factory is None else receiver_factory('results')
    if receiver is not None:
        def select(role):
            assert role == 'results'
            def receive(*args, **kwargs):
                calls.append((args[4], kwargs))
                return receiver(*args, **kwargs)
            return receive
        monkeypatch.setattr(parent_binding, 'child_report_receiver', select)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved admission cannot reacquire native bytes')
    monkeypatch.setattr(frame.store, 'get_artifact', forbidden)
    assert runtime.Workflow._receive_form(workflow, source, frame.form, frame.schema, frame.index) == [frame.result_ref]
    assert progress == attributed == [] and rows(frame.store) == before
    assert calls == ([(frame.index, {'redelivery': False})] if receiver is not None else [])


def test_results_redelivery_resolves_original_child_without_repricing(frame, parent_binding):
    runtime = own_module('runtime')
    workflow, source, progress, attributed = boundary(frame, parent_binding)
    original_action = dict(frame.journal.row('runtime_actions', source.episode_id, frame.index))
    original_receipts = [tuple(row) for row in frame.store.db.execute('SELECT * FROM runtime_record_receipts')]
    frame.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': 2,
        'action': runtime._json({'kind': 'redeliver_report', 'delivery_ref': 'original-results-delivery'}),
        'result': None, 'credit': None})
    old = dict(frame.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
        'AND parent_episode_id=? AND decision_index=?', (frame.run_id, source.episode_id, frame.index)).fetchone())
    frame.journal.save('runtime_report_attempts', {key: value for key, value in {
        **old, 'decision_index': 2, 'delivery_ref': 'original-results-delivery'}.items() if key != 'run_id'})
    assert own_module('delivery_counterpart').child_role_for_delivery(workflow, source, 2) == 'results'
    assert runtime.Workflow._receive_form(workflow, source, frame.form, frame.schema, 2, redelivery=True) == [frame.result_ref]
    assert [args[-1] for args in progress] == [f'{frame.run_id}:{source.episode_id}:2:typed_form']
    assert attributed[0][1] == {'kind': 'report_redelivery'}
    assert dict(frame.journal.row('runtime_actions', source.episode_id, frame.index)) == original_action
    assert [tuple(row) for row in frame.store.db.execute('SELECT * FROM runtime_record_receipts')] == original_receipts
    assert frame.store.db.execute('SELECT child_episode_id FROM runtime_report_attempts WHERE run_id=? '
        'AND parent_episode_id=? AND decision_index=2', (frame.run_id, source.episode_id)).fetchone()[0] == frame.child.episode_id


@pytest.mark.parametrize('text_context', (False, True))
def test_actual_presentation_preserves_json_text_bootstrap_update_and_lookup(frame, text_context):
    provider_type = own_module('providers')._SessionConnection
    original = object.__new__(provider_type)
    selected = object.__new__(provider_type)
    original.scientific_prompt_states, selected.scientific_prompt_states = {}, {}
    renderer = getattr(frame.owner, 'decision_prompt_renderer', None)
    decision = own_module('decision_context')
    state = {'execution_result': {'status': 'partial', 'qualifications': ['original', 'unverified']}}
    if text_context:
        state['hpc_execution_job'] = {'original_request': 'retained'}
    updated = {**deepcopy(state), 'execution_result': {'status': 'failed', 'qualifications': ['original']}}
    sequence = [state, decision.state_frame(state), decision.state_frame(updated, state),
        {'version': decision.VERSION, 'kind': 'decision_lookup_result', 'result': {'original': ['full', 'lookup']}}]
    for context in sequence:
        expected = original._presentation(frame.child.episode_id, 'REASONING', 'Original goal', deepcopy(context))
        actual = selected._presentation(frame.child.episode_id, 'REASONING', 'Original goal', deepcopy(context), prompt_renderer=renderer)
        assert actual == expected and selected.scientific_prompt_states == original.scientific_prompt_states
        if not text_context:
            assert actual == (json.dumps(context, allow_nan=False), 'Original goal')
        else:
            assert actual[0].startswith('TASK\nOriginal goal')


def test_parent_descriptors_read_current_results_files(frame, parent_binding, binding_home):
    descriptor = parent_binding.as_record()
    assert descriptor == parent_binding.as_record()
    assert descriptor['configuration']['resources'] == resources()
    if hasattr(frame.owner, 'decision_source_type'):
        task = own_module(binding_home + '/task').ResultsTask
        assert frame.owner.decision_source_type is task
        assert not issubclass(task, own_module('runtime').DecisionSource)
        assert parent_binding.child_report_receiver('results').__module__.endswith('.from_child_execution_result_acquisition')
        assert frame.owner.prepare_assignment.__module__.endswith('.from_parent')
        assert frame.owner.decision_prompt_renderer.presentation_protocol == 'episode_context_presentation_v1'
