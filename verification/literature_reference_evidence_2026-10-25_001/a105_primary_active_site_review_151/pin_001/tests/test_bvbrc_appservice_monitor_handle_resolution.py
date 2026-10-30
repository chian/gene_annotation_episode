"""AppService handle resolution with production receipts and custody proofs.

Native responses and saved decisions are controlled fixtures. The separate
monitor Workflow test owns full shared-method_loop delivery and recovery.
"""
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.bvbrc_appservice_records import PROVIDER
from gene_annotation_episode.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.execution_contracts import canonical
from test_bvbrc_appservice_native_monitor import (
    assignment, consumer, dependency_monitor, h, observe,
)


def resolve(h, reference=None, *, context=None, namespace='execution_handle'):
    return h.d.api.appservice.resolve(
        h.monitor if context is None else context,
        h.target['handle'] if reference is None else reference, namespace)


@pytest.mark.parametrize('namespace', ['execution_handle', 'execution'])
def test_actual_assigned_handoff_resolves_without_work_or_observations(h, namespace):
    changes = h.store.db.total_changes
    files = sorted(path.relative_to(h.directory) for path in h.directory.rglob('*') if path.is_file())
    assert resolve(h, namespace=namespace) is True
    assert resolve(h, namespace=namespace) is True
    assert h.store.db.total_changes == changes
    assert sorted(path.relative_to(h.directory) for path in h.directory.rglob('*') if path.is_file()) == files
    assert h.d.client.calls == []
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def test_typed_monitor_target_uses_actual_assignment_and_original_handoff(h):
    c = consumer(h)
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['target'],
        'properties': {'target': c.monitor.fact_sources('monitor')['monitoring_target_handle']['report_schema']}}
    form = {'target': h.target['handle']}
    assert validate_form(form, schema, lambda ref, ns: resolve(h, ref, namespace=ns)) == form
    h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?',
        (h.d.saved.root.episode_id,))
    with pytest.raises(ReportBoundaryError) as failure:
        validate_form(form, schema, lambda ref, ns: resolve(h, ref, namespace=ns))
    assert failure.value.diagnostic == {
        'category': 'report_format', 'code': 'unknown_reference', 'field': 'report.target'}


@pytest.mark.parametrize('change', ['run', 'episode', 'assignment', 'request', 'scope'])
def test_forged_monitor_context_does_not_resolve_existing_handoff(h, change):
    context = h.monitor
    if change == 'run':
        context = replace(context, run_id='different-run')
    elif change == 'episode':
        context = replace(context, episode_id='different-episode')
    elif change == 'assignment':
        context = replace(context, assignment=assignment('different-target'))
    elif change == 'scope':
        context = replace(context, scope={'subject_refs': []})
    else:
        request = plain(context.request)
        request['goal']['objective'] = 'unselected work'
        context = replace(context, request=request)
    assert resolve(h, context=context) is False
    assert h.d.client.calls == []


@pytest.mark.parametrize('change', ['unreceived', 'late_receipt', 'commission', 'model_selection',
                                   'missing_selection', 'incomplete_submission'])
def test_invalid_original_commission_or_temporal_custody_is_false(h, change):
    saved, root = h.d.saved, h.d.saved.root
    context = h.monitor
    if change == 'unreceived':
        h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (root.episode_id,))
    elif change == 'late_receipt':
        h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (root.episode_id,))
        h.store.db.execute('DELETE FROM runtime_record_receipts WHERE episode_id=?', (root.episode_id,))
        context = saved.child(root, 'monitor', assignment(h.target['handle']), 4)
        saved.admit(root, h.d.launch, h.target['handle'])
    elif change in {'commission', 'model_selection'}:
        table = 'runtime_actions' if change == 'commission' else 'runtime_model_calls'
        row = saved.journal.row(table, root.episode_id, 3)
        field = 'action' if change == 'commission' else 'response'
        value = json.loads(row[field])
        selected = value if field == 'action' else value['selection']
        selected['assignment']['target_handle'] = 'different-target'
        saved.journal.save(table, {**row, field: canonical(value)})
    elif change == 'missing_selection':
        h.store.db.execute('DELETE FROM runtime_actions WHERE episode_id=? AND decision_index=3', (root.episode_id,))
        h.store.db.execute('DELETE FROM runtime_model_calls WHERE episode_id=? AND call_index=3', (root.episode_id,))
    else:
        key = h.handoff['value']['original_task']['submission_operation_key']
        h.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE episode_id=? AND decision_index=?',
            (h.d.context.episode_id, int(key.rsplit(':', 1)[1])))
    assert resolve(h, context=context) is False
    assert h.d.client.calls == []


def test_different_actual_handoff_is_not_the_assigned_or_received_target(h):
    _, context = h.d.saved.tree(launch_index=4)
    preparation = h.d.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}},
        context=context)
    h.d.client.value = {'id': '456', 'application_id': 'Homology', 'state_code': 'Q'}
    other = h.d.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []},
        context=context)
    assert h.d.api.read_target(other['source_ref'], context.scope)['execution_id'] == '456'
    h.d.client.calls.clear()
    assert resolve(h, other['source_ref']) is False
    assert resolve(h) is True
    assert h.d.client.calls == []


def test_support_receipt_and_forged_owned_source_are_not_execution_targets(h):
    preparation = h.d.api.appservice._own_receipts(h.d.context)[0]['source_ref']
    assert resolve(h, preparation) is False
    forged = h.d.saved.source(b'{}', provider=PROVIDER)['source_ref']
    assert resolve(h, forged) is False
    assert h.d.client.calls == []


def test_other_binding_references_defer_and_existing_launch_results_namespaces_survive(h):
    assert resolve(h, 'execution_other_binding') is None
    assert resolve(h, h.d.saved.source()['source_ref']) is None
    preparation = h.d.api.appservice._own_receipts(h.d.context)[0]['source_ref']
    assert resolve(h, preparation, context=h.d.context, namespace='bvbrc_appservice_support') is True
    assert resolve(h, context=h.d.context, namespace='execution_handoff') is True
    assert resolve(h, context=h.d.context, namespace='execution_result') is False
    results = h.d.results(h.handoff, index=4)
    assert resolve(h, context=results, namespace='execution_handoff') is True
    assert resolve(h, context=results, namespace='source') is True


@pytest.mark.parametrize('encoded', [False, True])
def test_unsaved_initial_target_requires_exact_saved_parent_model_selection(h, encoded):
    context = h.d.saved.child(h.d.saved.root, 'monitor', assignment(h.target['handle']),
        4, save=False, action=False, encoded=encoded)
    assert h.d.saved.journal.row('runtime_episodes', context.episode_id) is None
    assert h.d.saved.journal.row('runtime_actions', h.d.saved.root.episode_id, 4) is None
    assert resolve(h, context=context) is True
    # Read-only initial-form validation does not authorize native observation.
    with pytest.raises(ValueError, match='saved_context_required'):
        observe(h, 'query_tasks', context=context)
    assert h.d.client.calls == []


@pytest.mark.parametrize('change', ['missing_model', 'target', 'original_schema'])
def test_unsaved_target_never_uses_action_or_caller_claim_in_place_of_original_selection(h, change):
    saved, root = h.d.saved, h.d.saved.root
    context = saved.child(root, 'monitor', assignment(h.target['handle']), 4,
        save=False, model=change != 'missing_model')
    if change != 'missing_model':
        row = saved.journal.row('runtime_model_calls', root.episode_id, 4)
        if change == 'target':
            value = json.loads(row['response'])
            value['selection']['assignment']['target_handle'] = 'different-target'
            saved.journal.save('runtime_model_calls', {**row, 'response': canonical(value)})
        else:
            value = json.loads(row['request'])
            value['schema']['properties']['selection']['properties']['role'] = {'const': 'results'}
            saved.journal.save('runtime_model_calls', {**row, 'request': canonical(value)})
    assert resolve(h, context=context) is False


def test_same_target_recursive_monitor_keeps_original_parent_custody(h):
    child = h.d.saved.child(h.monitor, 'monitor', assignment(h.target['handle']), 0)
    assert resolve(h, context=child) is True
    h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?',
        (h.d.saved.root.episode_id,))
    assert resolve(h, context=child) is False
    assert h.d.client.calls == []


def test_received_dependency_and_child_target_use_original_progress_and_task_relation(h):
    c = consumer(h)
    parent, _ = dependency_monitor(h, c)
    child = h.d.saved.child(parent, 'monitor', assignment(h.target['handle']), 1)
    assert resolve(h, context=parent) is True
    assert resolve(h, context=child) is True
    assert h.store.db.execute('SELECT 1 FROM runtime_record_receipts WHERE episode_id=? AND record_ref=?',
        (parent.episode_id, h.target['handle'])).fetchone() is None
    assert h.d.client.calls == []


@pytest.mark.parametrize('change', ['unreceived', 'relation', 'selection_signature', 'commission', 'unsaved'])
def test_invalid_dependency_cannot_resolve_through_monitor_registry(h, change):
    c = consumer(h)
    parent, result = dependency_monitor(h, c)
    if change == 'unreceived':
        h.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE episode_id=? AND decision_index=0',
            (parent.episode_id,))
    elif change == 'relation':
        result['result']['dependencies'][0]['relation_ref'] = h.d.saved.source()['source_ref']
        h.store.db.execute('UPDATE runtime_progress_observations SET snapshot=? WHERE progress_ref=?',
            (canonical(result['result']), result['result']['progress_ref']))
        h.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=0',
            (canonical(result), parent.episode_id))
    elif change == 'selection_signature':
        h.store.db.execute('UPDATE runtime_progress_selections SET signature=? WHERE operation_key=?',
            ('forged', f'{parent.run_id}:{parent.episode_id}:0'))
    elif change == 'commission':
        row = h.d.saved.journal.row('runtime_actions', h.d.saved.root.episode_id, 4)
        value = json.loads(row['action'])
        value['assignment']['target_handle'] = h.target['handle']
        h.d.saved.journal.save('runtime_actions', {**row, 'action': canonical(value)})
    else:
        h.store.db.execute('DELETE FROM runtime_episodes WHERE episode_id=?', (parent.episode_id,))
    assert resolve(h, context=parent) is False
    assert h.d.client.calls == []


@pytest.mark.parametrize('late', [False, True])
def test_typed_dependency_return_preserves_original_receipt_cutoff(h, late):
    c = consumer(h)
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['handles'],
        'properties': {'handles': c.monitor.fact_sources('monitor')['monitoring_dependency_handles']['report_schema']}}
    parent, _ = dependency_monitor(h, c, schema=schema)
    root = h.d.saved.root
    h.store.db.execute('DELETE FROM runtime_report_attempts WHERE parent_episode_id=?', (root.episode_id,))
    h.store.db.execute('DELETE FROM runtime_record_receipts WHERE episode_id=?', (root.episode_id,))

    def receive():
        form = {'handles': [h.target['handle']]}
        h.d.saved.journal.save('runtime_forms', {'episode_id': parent.episode_id,
            'facts': canonical({'monitoring_dependency_handles': form['handles']}), 'form': canonical(form)})
        h.d.saved.journal.save('runtime_report_attempts', {'parent_episode_id': root.episode_id,
            'decision_index': 4, 'delivery_ref': 'delivery_dependency', 'child_episode_id': parent.episode_id,
            'contract': canonical(parent.request['report_contract']), 'form': canonical(form), 'failure': None})
        h.d.saved.receipts.receive(root.episode_id, form['handles'], kind='child_form', source_index=4)

    if not late:
        receive()
    child = h.d.saved.child(root, 'monitor', assignment(h.target['handle']), 5)
    if late:
        receive()
    assert resolve(h, context=child) is (not late)
    assert h.d.client.calls == []
