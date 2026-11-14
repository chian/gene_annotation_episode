"""Original scientific-parent monitor exchanges and saved redelivery counterpart."""
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.root.a101.delivery_counterpart import child_role_for_delivery
from gene_annotation_episode.episodic_workflow.root.a101.episode_journal import Journal, WorkflowError
from gene_annotation_episode.episodic_workflow.root.a101.episode_monitoring import ProgressProvider
from gene_annotation_episode.episodic_workflow.root.a101.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.a101.state import Store
from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.episode import ScientificProcessEpisode
from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.to_child_execution_progress_assessment import prepare_request
from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.execution_progress_assessment.tests.test_progress_task import setup_monitor


def test_parent_request_and_child_admission_keep_original_operands():
    monitor, context, _, _ = setup_monitor()
    parent = object.__new__(ScientificProcessEpisode)
    scientific = SimpleNamespace(role='scientific_process', path=(('scientific_process', 'science'),))
    original = plain(context.assignment)
    prepared = parent.prepare_child_request(scientific, 'monitor', original)
    assert prepared == original and prepared is not original
    assert monitor.prepare_assignment(scientific, 'monitor', prepared, {}, 'commission') == original
    monitor.services.annotation_task_required = lambda: True
    assert monitor.required_return_sources(scientific, 'monitor') == ('monitoring_progress_refs',)
    monitor.services.annotation_task_required = lambda: False
    assert monitor.required_return_sources(scientific, 'monitor') == ()
    assert parent.prepare_child_request(scientific, 'literature', original) is original
    with pytest.raises(ContractError):
        prepare_request({**original, 'extra': 'not part of the original assignment'})


def test_a101_monitor_does_not_execute_unbound_foreign_context_hooks():
    monitor, context, _, _ = setup_monitor()
    def foreign(*args, **kwargs):
        raise AssertionError('MACS2 is not part of this A101 implementation')
    monitor.services.macs2_peak_monitor_task = foreign
    parent = SimpleNamespace(role='scientific_process')
    monitor.prepare_assignment(parent, 'monitor', plain(context.assignment), {}, 'commission')
    assert 'selected_execution_task' not in monitor.decision_context(context, {})


def saved_workflow(tmp_path):
    store = Store(tmp_path / 'state')
    journal = Journal(store, 'run')
    parent = object.__new__(ScientificProcessEpisode)
    source = SimpleNamespace(episode_id='parent', path=(('scientific_process', 'science'),), scope={})
    provider = ProgressProvider(store, object(), run_id='run')
    workflow = SimpleNamespace(store=store, journal=journal, run_id='run', receipts=None,
        progress_provider=provider, specialist=lambda source: parent,
        binding_context=lambda source: source, is_job_source=lambda source: False)
    return store, workflow, source


def save_action(workflow, index, value):
    workflow.journal.save('runtime_actions', {'episode_id': 'parent', 'decision_index': index,
        'action': json.dumps(value), 'result': None, 'credit': None})


def save_child(workflow, path):
    workflow.journal.save('runtime_episodes', {'episode_id': 'child', 'path': json.dumps(path),
        'request': '{}', 'initial_credit': 0, 'state': 'yielded', 'completion': None, 'archive': None})


def save_attempt(workflow, index):
    workflow.journal.save('runtime_report_attempts', {'parent_episode_id': 'parent',
        'decision_index': index, 'delivery_ref': 'delivery', 'child_episode_id': 'child',
        'contract': '{}', 'form': None, 'failure': None})


def test_parent_runtime_receipt_and_redelivery_use_saved_monitor_counterpart(tmp_path):
    store, workflow, source = saved_workflow(tmp_path)
    try:
        save_action(workflow, 3, {'kind': 'episode_child', 'role': 'monitor'})
        save_child(workflow, (*source.path, ('monitor', 'child_3')))
        save_attempt(workflow, 3)
        # A repaired delivery is a different action; its report-attempt record
        # still names the original child rather than inventing a role.
        save_action(workflow, 7, {'kind': 'redeliver_report', 'delivery_ref': 'delivery'})
        save_attempt(workflow, 7)
        assert child_role_for_delivery(workflow, source, 3) == 'monitor'
        assert child_role_for_delivery(workflow, source, 7) == 'monitor'
        reference = 'progress_' + 'a' * 24
        workflow.progress_provider.read_progress = lambda ref, scope: {'progress_ref': ref}
        schema = obj({'progress': {'type': 'array', 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'episode_progress'}}})
        form = {'progress': [reference]}
        # The scientific parent must execute its private receiver, not generic
        # provider receive_form, while retaining the same database receipt.
        workflow.progress_provider.receive_form = lambda *args: pytest.fail('generic receiver selected')
        assert Workflow._receive_form(workflow, source, form, schema, 3) == []
        assert Workflow._receive_form(workflow, source, form, schema, 7, redelivery=True) == []
        assert workflow.progress_provider.received_progress_refs('parent') == [reference]
    finally:
        store.close()


@pytest.mark.parametrize('failure', ['missing', 'wrong_parent', 'role_conflict'])
def test_counterpart_rejection_never_chooses_a_different_parent(tmp_path, failure):
    store, workflow, source = saved_workflow(tmp_path)
    try:
        if failure == 'missing':
            save_action(workflow, 7, {'kind': 'redeliver_report', 'delivery_ref': 'missing'})
        else:
            save_action(workflow, 7, {'kind': 'episode_child', 'role': 'results' if failure == 'role_conflict' else 'monitor'})
            parent = (('scientific_process', 'other'),) if failure == 'wrong_parent' else source.path
            save_child(workflow, (*parent, ('monitor', 'child_3')))
            save_attempt(workflow, 7)
        with pytest.raises(WorkflowError, match='original_delivery_'):
            child_role_for_delivery(workflow, source, 7)
    finally:
        store.close()


def test_other_child_receipts_keep_the_original_provider_path(tmp_path):
    store, workflow, source = saved_workflow(tmp_path)
    try:
        save_action(workflow, 1, {'kind': 'episode_child', 'role': 'literature'})
        calls = []
        workflow.progress_provider.receive_form = lambda *args: calls.append(args)
        assert Workflow._receive_form(workflow, source, {}, obj({}), 1) == []
        assert len(calls) == 1
    finally:
        store.close()
