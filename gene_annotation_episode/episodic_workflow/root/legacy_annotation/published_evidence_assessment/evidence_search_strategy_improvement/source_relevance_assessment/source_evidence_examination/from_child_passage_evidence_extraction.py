"""Root-owned action_execution.py"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionLeaf
from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_INFORMATION_OPERATIONS
from gene_annotation_episode.domain import ContractError
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.workflow_values import EPISODE_BRANCH_LIFECYCLE
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.method_loop import ReportDeliveryError
from gene_annotation_episode.episodic_workflow.root.workflow_values import TimedChildUnit
from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract
from jsonschema import ValidationError
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
from gene_annotation_episode.episodic_workflow.root.task_values import _digest
from gene_annotation_episode.episodic_workflow.root.task_values import _json
from gene_annotation_episode.episodic_workflow.root.composition_information import metadata_catalog as composition_catalog
import inspect
from gene_annotation_episode.episodic_workflow.root.communication import interpretation_schema
import json
from gene_annotation_episode.tool_knowledge import catalog as knowledge_catalog
from gene_annotation_episode.launch_instructions import catalog as launch_instruction_catalog
from contextlib import nullcontext
from gene_annotation_episode.episodic_workflow.root.boundary_validation import parse_json_object
from gene_annotation_episode.episodic_workflow.root.native_timing_information import read_measurement
from gene_annotation_episode.episodic_workflow.root.composition_information import restricted_root
from gene_annotation_episode.episodic_workflow.root.communication import validate_form


def admit_return(workflow, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _request_runtime._digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': index})[:24]
    owned = workflow.episode_branch_lifecycle == _request_runtime.EPISODE_BRANCH_LIFECYCLE
    action = workflow.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else _request_runtime.json.loads(action['result']).get('delivery_resolution_index')
    saved = workflow.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None or not owned else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (workflow.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
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
