"""Controlled monitor boundaries; no live-job or autonomous-science claim."""
import asyncio
from copy import deepcopy
from contextlib import nullcontext
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.execution_progress_assessment.episode import MonitorEpisode


def setup_monitor():
    snapshot = {'progress_ref': 'progress_aaaaaaaaaaaaaaaaaaaaaaaa', 'target_handle': 'target',
        'execution_status': {'lifecycle_state': 'executing'}, 'result_available': False,
        'observed_at': '2026-11-11T00:00:00Z', 'log_windows': [],
        'committed_record_refs': [], 'dependencies': []}
    received = []
    services = SimpleNamespace(
        reference_in_scope=lambda *args: True,
        read_progress=lambda ref, scope: deepcopy(snapshot),
        progress_selection=lambda context: {'known_progress_refs': list(received)},
        observe_progress=lambda *args, **kwargs: deepcopy(snapshot),
        read_record=lambda ref: {'record_type': 'source'},
        dependencies=lambda *args: [{'handle': 'dependent'}],
        describe_progress_target=lambda *args: None,
        bound_role_credit=lambda context, selection: {'credit': len(received)},
        own_outcomes=lambda *args, **kwargs: {'records': [], 'next_offset': None})
    assignment = {'version': 'monitor_assignment_v1', 'target_handle': 'target',
        'requested_fields': ['execution_status'], 'known_progress_refs': [],
        'permitted_committed_record_types': []}
    context = BindingContext('run', 'monitor', 'monitor', (('monitor', 'monitor'),),
                             {}, assignment, {'goal': {'objective': 'Resolve target progress'}})
    return MonitorEpisode(services), context, received, snapshot


def test_observe_uses_original_target_and_records_actual_snapshot():
    binding, context, received, snapshot = setup_monitor()
    result = asyncio.run(binding.execute(context, 'progress.observe',
        {'requested_fields': ['execution_status']}, 'observe-one'))
    assert result['status'] == 'completed'
    assert result['progress_refs'] == ['progress_aaaaaaaaaaaaaaaaaaaaaaaa']
    assert result['result'] == snapshot
    assert binding.credit_view(context, {}) == {'credit': 0}
    received.extend(result['progress_refs'])
    assert binding.credit_view(context, {}) == {'credit': 1}


@pytest.mark.parametrize('tool,arguments,code', [
    ('progress.observe', {'requested_fields': ['measurements']}, 'monitor_observation_expands_requested_fields'),
    ('progress.read', {'progress_ref': 'progress_aaaaaaaaaaaaaaaaaaaaaaaa'}, 'monitor_progress_not_received'),
    ('unavailable', {}, 'tool_not_available_to_monitor_role')])
def test_invalid_executed_operation_retains_invalid_outcome(tool, arguments, code):
    binding, context, _, _ = setup_monitor()
    result = asyncio.run(binding.execute(context, tool, arguments, 'invalid-one'))
    assert result['status'] == 'invalid'
    assert result['progress_refs'] == []
    assert result['feedback']['code'] == code


def test_recursive_assignment_preserves_exposed_direct_dependency():
    binding, context, _, _ = setup_monitor()
    selection = {**dict(context.assignment), 'target_handle': 'dependent'}
    selection['requested_fields'] = list(selection['requested_fields'])
    selection['known_progress_refs'] = []
    selection['permitted_committed_record_types'] = []
    assert binding.prepare_assignment(context, 'monitor', selection, {}, 'child-one') == selection
    with pytest.raises(ContractError, match='monitor_child_target_not_exposed_direct_dependency'):
        binding.prepare_assignment(context, 'monitor', {**selection, 'target_handle': 'unexposed'}, {}, 'child-two')


def test_report_uses_delivered_information_without_polling():
    binding, context, received, _ = setup_monitor()
    def forbidden(*args, **kwargs):
        raise AssertionError('report construction must not acquire progress')
    binding.services.observe_progress = forbidden
    empty = binding.facts(context, {})
    assert empty['monitoring_execution_state'] is None
    received.append('progress_aaaaaaaaaaaaaaaaaaaaaaaa')
    assert binding.facts(context, {})['monitoring_execution_state'] == 'executing'
    assert binding.decision_context(context, {})['monitor_received_progress_refs'] == ['progress_aaaaaaaaaaaaaaaaaaaaaaaa']
    assert binding.decision_context(context, {})['monitor_goal']['objective'] == {'objective': 'Resolve target progress'}


def test_yield_settings_and_descriptor_preserved():
    binding, context, _, _ = setup_monitor()
    configured = MonitorEpisode(binding.services, information_unit=2,
        yield_settings={'kind': 'information_accumulation', 'cutoff': 0.25, 'uncertainty_alpha': 0.05})
    assert configured.as_record()['configuration']['information_unit'] == 2
    assert configured.yield_controller(context, 0, 'epoch') is not None
    assert 'wait' in configured.permitted_common_actions(context)


def test_private_task_preserves_invalid_action_and_replays_without_observing_again():
    from gene_annotation_episode.episodic_workflow.root.a107.hpc_work_planning.execution_progress_assessment.task import ProgressMonitoringTask
    binding, context, _, _ = setup_monitor()
    saved, calls, outcomes = {}, [], []
    journal = SimpleNamespace(row=lambda table, episode, index: saved.get(index),
        save=lambda table, row: saved.__setitem__(row['decision_index'], row),
        measure=lambda *args: nullcontext())

    async def execute(source, name, arguments, **kwargs):
        calls.append(name)
        return await binding.execute(context, name, arguments, kwargs['operation_key'])

    async def score(source, index, result):
        return result

    task = object.__new__(ProgressMonitoringTask)
    task.episode_id, task.path, task.scope = 'monitor', context.path, {}
    task.checkpoint = lambda: None
    task.workflow = SimpleNamespace(journal=journal, run_id='run', execution_binding=None,
        pending_work=lambda source: [], execute=execute,
        receive_native_outcome=lambda *args: None,
        receive_outcome=lambda source, selection, result, index: outcomes.append((index, result['status'])),
        automatic_score_updates=score, source_credit_view=lambda source: {'credit': 0},
        controller_value=lambda source, index, credit: {'index': index, 'credit': credit})
    selection = {'kind': 'tool', 'tool': 'progress.observe', 'arguments': {'requested_fields': ['measurements']}}
    first = asyncio.run(task.execute(selection, 0))
    second = asyncio.run(task.execute(selection, 0))
    assert first == second == {'index': 0, 'credit': 0}
    assert calls == ['progress.observe']
    assert outcomes == [(0, 'invalid')]
    assert json.loads(saved[0]['result'])['status'] == 'invalid'
    assert json.loads(saved[0]['action']) == selection


def test_private_child_receipt_preserves_provider_delivery_identity(tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a107.episode_monitoring import ProgressProvider
    from gene_annotation_episode.episodic_workflow.root.a107.state import Store
    from gene_annotation_episode.episodic_workflow.root.a107.domain import obj
    binding, context, _, snapshot = setup_monitor()
    schema = obj({'progress': {'type': 'array', 'items': {
        'type': 'string', 'format': 'reference', 'x-reference-namespace': 'episode_progress'}}})
    form = {'progress': [snapshot['progress_ref']]}
    with Store(tmp_path / 'state') as store:
        provider = ProgressProvider(store, object(), run_id='run')
        provider.read_progress = lambda ref, scope: deepcopy(snapshot)
        original = provider.receive_form(context.episode_id, form, schema, context.scope, 'delivery')
        private = binding.receive_child_progress(context, form, schema, 'delivery', provider)
        assert private == original == form['progress']
        assert provider.received_progress_refs(context.episode_id) == form['progress']
        from gene_annotation_episode.episodic_workflow.root.a107.runtime import Workflow
        workflow = SimpleNamespace(receipts=None, progress_provider=provider,
            specialist=lambda source: binding, binding_context=lambda source: context,
            run_id='run', is_job_source=lambda source: False)
        assert Workflow._receive_form(workflow, context, form, schema, 0) == []
        assert Workflow._receive_form(workflow, context, form, schema, 0, redelivery=True) == []
        assert provider.received_progress_refs(context.episode_id) == form['progress']
        with pytest.raises(ContractError, match='progress_delivery_identity_conflict'):
            binding.receive_child_progress(context, {'progress': []}, schema, 'delivery', provider)
