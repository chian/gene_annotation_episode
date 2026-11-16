from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.method_loop import ReportDeliveryError
from gene_annotation_episode.episodic_workflow.root.task_values import _digest
import json

def admit_return(workflow, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _request_runtime._digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': index})[:24]
    action = workflow.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else _request_runtime.json.loads(action['result']).get('delivery_resolution_index')
    saved = workflow.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (workflow.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise _request_runtime.ReportDeliveryError(_request_runtime.Record(_request_runtime.json.loads(saved['failure'])))
        admitted = _request_runtime.json.loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
        except _request_runtime.ReportBoundaryError as error:
            feedback = workflow.delivery_feedback(delivery_ref, error)
            workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
            raise _request_runtime.ReportDeliveryError(_request_runtime.Record(feedback)) from error
        workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else _request_runtime.json.loads(saved['contract'])['measurements']['schema']
    references = workflow.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
    return (admitted, references)

from gene_annotation_episode.episodic_workflow.root import action_execution as _request_runtime
