from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.action_contracts import action_schema as _private_action_schema
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy

import json

import inspect

from contextlib import nullcontext

from jsonschema import Draft202012Validator, ValidationError

from gene_annotation_episode.episodic_workflow.root.method_loop import ReportRedelivery

from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _decode_recorded_action_response

from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionFailure

from gene_annotation_episode.episodic_workflow.root.task_values import _json

from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, validate_form

from gene_annotation_episode.episodic_workflow.root.episode_contract_information import ContractInformationError

from gene_annotation_episode.episodic_workflow.root.boundary_validation import schema_failure_diagnostic

from gene_annotation_episode.episodic_workflow.root.episode_completion import observes_action_outcome

from collections.abc import Mapping

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _object, _recorded_action_generation_schema

from gene_annotation_episode.episodic_workflow.root.reference_selection import _references_in

from gene_annotation_episode.episodic_workflow.root.decision_context import VERSION as DECISION_CONTEXT_VERSION

from gene_annotation_episode.episodic_workflow.root.decision_context import apply_state_frame, model_snapshot, instructional_model_context

from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information

from gene_annotation_episode.episodic_workflow.root.composition_information import lookup_schema as composition_lookup_schema

from gene_annotation_episode.episodic_workflow.root.infernal_result_presentation import infernal_receiver_context

from gene_annotation_episode.episodic_workflow.root.method_loop import Episode

from gene_annotation_episode.episodic_workflow.root.task_values import Record, _plain, _json

from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionLeaf

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _object

from gene_annotation_episode.episodic_workflow.root.episode_completion import EFFECT_VERSION

from gene_annotation_episode.episodic_workflow.root.communication import interpretation_schema

from gene_annotation_episode.episodic_workflow.root.task_values import Record, _json

from gene_annotation_episode.episodic_workflow.root.communication import form_with_facts

import sqlite3

from jsonschema import ValidationError

from gene_annotation_episode.episodic_workflow.root import literature_numerical_contracts

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _recorded_assignment_transport, _ASSIGNMENT_TRANSPORT, _action_generation_schema

from gene_annotation_episode.episodic_workflow.root.task_values import _json, _plain, _digest

from gene_annotation_episode.episodic_workflow.root.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS as DECISION_EXCHANGE_INSTRUCTIONS, VERSION as DECISION_CONTEXT_VERSION

from gene_annotation_episode.episodic_workflow.root.decision_context import model_snapshot, instructional_model_context, state_frame

from gene_annotation_episode.episodic_workflow.root.decision_history import yield_table, lookup_attempts

from gene_annotation_episode.episodic_workflow.root.yield_parameters import _category_yield_parameters

from gene_annotation_episode.episodic_workflow.root.composition_information import child_options as child_option_information, requested_contract_information

from gene_annotation_episode.episodic_workflow.root.method_loop import SourceEnd

from gene_annotation_episode.episodic_workflow.root.task_values import _plain

from gene_annotation_episode.episodic_workflow.root.report_facts import FACT_SOURCES, FACT_MEANINGS

from gene_annotation_episode.episodic_workflow.root.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL

from gene_annotation_episode.tool_knowledge import INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS

from gene_annotation_episode.launch_instructions import INSTRUCTIONS as LAUNCH_INSTRUCTIONS

import subprocess

from gene_annotation_episode.acquisition import AcquisitionError

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.root.method_loop.durable import EventTargetError

from gene_annotation_episode.episodic_workflow.root.waiting import _wait_target_feedback

from gene_annotation_episode.episodic_workflow.root.goal import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT

from gene_annotation_episode.episodic_workflow.root.method_loop import Episode, SourceEnd

from gene_annotation_episode.episodic_workflow.root.communication import interpretation_schema, form_with_facts
from .task_state import HPCExecutionTaskState
from .task_protocol import HPCExecutionTaskProtocol
from .task_decision import HPCExecutionTaskDecision
from .task_instructions import HPCExecutionTaskInstructions
from .task_actions import HPCExecutionTaskActions
from .task_report import HPCExecutionTaskReport

from .decision_context import HPCExecutionTaskContext

class HPCExecutionTask(HPCExecutionTaskContext, HPCExecutionTaskState, HPCExecutionTaskProtocol, HPCExecutionTaskDecision, HPCExecutionTaskInstructions, HPCExecutionTaskActions, HPCExecutionTaskReport):
    async def next(self, view, *, delivery_ref=None):
        if delivery_ref is None:
            self._selection_view = view
            closed = self.workflow.journal.row('runtime_episodes', self.episode_id)
            if closed is not None and closed['state'] == 'yielded' and (closed['completion'] is not None):
                completion = json.loads(closed['completion'])
                if completion['ended_by'] == 'source_failed' and view.units_consumed == completion['actions']:
                    return SourceEnd('source_failed')
        if self.workflow.inprocess_replay is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.inprocess_replay.unit(self, view.units_consumed)
            if ready is not None:
                return ready
            self.restore_checkpoint()
            self._inprocess_replay_ready = True
            with self.workflow.store.transaction():
                self.workflow.inprocess_replay.capture(self)
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, json.loads(action['action']), index)
        if self.workflow.execution_binding is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            self.restore_checkpoint()
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, json.loads(action['action']), index)
            ready = self.workflow.next_return(self)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            await self.workflow.resolve_pending_deliveries(self, view)
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
        while True:
            original_call = self.workflow.journal.row('runtime_model_calls', self.episode_id, self.calls)
            if delivery_ref is None and original_call is None and (self._execution_context is not None):
                ready = self._execution_context._ready_owned_child(self.path)
                if ready is not None:
                    return ready
            original_request = json.loads(original_call['request']) if original_call is not None else None
            if original_request is not None and (original_call['response'] is not None or 'contract_information' in original_request or literature_numerical_contracts.SAVED_MEMBER in original_request):
                context, schema = (original_request['context'], original_request['schema'])
            else:
                context = self.assemble_decision_context(view)
                schema = _invoke_private_policy(self.workflow.action_schema, _private_action_schema, self)
                if delivery_ref is not None:
                    context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
            if delivery_ref is not None and context.get('pending_child_delivery', {}).get('delivery_ref') != delivery_ref:
                raise WorkflowError('restored_delivery_resolution_identity_conflict')
            from gene_annotation_episode.episodic_workflow.root.providers import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from gene_annotation_episode.episodic_workflow.root.episode_source_failure import record_source_failure
                record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, self.calls - 1, error)
                self.feedback = {'status': 'failed', 'category': 'decision_source', 'exception_type': type(error).__name__, 'detail': str(error)}
                self.checkpoint()
                if delivery_ref is not None:
                    raise
                return SourceEnd('source_failed')
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None else nullcontext():
                unit = self.apply_response(response, index, actual_context, schema)
            if unit is not None:
                return unit
