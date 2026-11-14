"""Actual private parent admission for the original legacy_annotation -> legacy_annotation edge."""
from gene_annotation_episode.episodic_workflow.root import action_execution as _original


def admit_return(workflow, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _original._digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': index})[:24]
    owned = workflow.episode_branch_lifecycle == _original.EPISODE_BRANCH_LIFECYCLE
    action = workflow.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else _original.json.loads(action['result']).get('delivery_resolution_index')
    saved = workflow.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None or not owned else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (workflow.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise _original.ReportDeliveryError(_original.Record(_original.json.loads(saved['failure'])))
        admitted = _original.json.loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
        except _original.ReportBoundaryError as error:
            feedback = workflow.delivery_feedback(delivery_ref, error)
            workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
            raise _original.ReportDeliveryError(_original.Record(feedback)) from error
        workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else _original.json.loads(saved['contract'])['measurements']['schema']
    references = workflow.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
    return (admitted, references)


def admit_unowned_return(workflow, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _original._digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': index})[:24]
    try:
        admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
    except _original.ReportBoundaryError as error:
        feedback = workflow.delivery_feedback(delivery_ref, error)
        workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
        raise _original.ReportDeliveryError(_original.Record(feedback)) from error
    workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    workflow.receive_form(source, admitted, schema, index)
    return admitted
