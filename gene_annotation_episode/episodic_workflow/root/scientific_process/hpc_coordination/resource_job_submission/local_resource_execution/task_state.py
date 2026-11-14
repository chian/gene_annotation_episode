from __future__ import annotations

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

class LocalResourceTaskState:
    def __init__(self, workflow, path, request, scope):
        if not path or path[-1][0] != 'launch_local':
            raise ValueError('fixed_resource_task_identity_required')
        self.workflow, self.path, self.request, self.scope = (workflow, path, request, scope)
        self.episode_id = Episode.identity(workflow.context, workflow.grains[path[-1][0]], path[-1][1], parent_path=path[:-1]).episode_id
        self.calls = 0
        self.feedback = None
        self.last_outcome = None
        self.last_outcome_index = None
        self.report_values = _plain(request.message.as_record()['initial_report'])
        self.report_basis = []
        self._restored = False
        self._unfinished_own_actions = []
        self._source_revision = None
        self._latest_effect_index = None
        self._restored_source_state = None
        self._model_snapshot = None
        self._presented_conversation_key = None
        self._selection_view = None
        self._delivery_resolution_ref = None
        self._execution_context = None
        self._suspension_condition = None
        self._inprocess_replay_ready = False
        self.interpret_schema = interpretation_schema(request.report_contract.schema) if request.report_contract else _object({})
        from gene_annotation_episode.episodic_workflow.root.scientific_process.hpc_coordination.resource_job_submission.local_resource_execution.episode import LocalResourceBinding
        if type(workflow.specialist(self)) is not LocalResourceBinding:
            raise ValueError('fixed_resource_task_binding_required')

    def bind_execution_context(self, context):
        self._execution_context = context

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle, None if condition is None else {'episode_id': self.episode_id, 'dependency': condition})

    def record_execution_failure(self, error, *, unit=None):
        from gene_annotation_episode.episodic_workflow.root.episode_source_failure import record_source_failure
        import traceback
        diagnostic = self.workflow.archive.store(Record({'exception_type': type(error).__name__, 'traceback': traceback.format_exc()}))
        index = getattr(unit, 'decision_index', None)
        failure = record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, index if index is not None else max(0, self.calls - 1), error, category='episode_execution', cause_code='selected_operation_failed')
        self.feedback = {**failure, 'diagnostic_ref': str(diagnostic.path)}
        action = None if index is None else self.workflow.journal.row('runtime_actions', self.episode_id, index)
        if action is not None and action['result'] is None and (json.loads(action['action']).get('kind') in {'tool', 'reason'}):
            selection = json.loads(action['action'])
            outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'feedback': self.feedback}
            with self.workflow.store.transaction():
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': action['action'], 'result': _json(outcome), 'credit': None})
                credit = self.workflow.source_credit_view(self)['credit']
                value = self.workflow.controller_value(self, index, credit)
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': action['action'], 'result': _json(outcome), 'credit': credit})
                if self.workflow.execution_binding is not None:
                    self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=value, child_return=None)
            self.last_outcome, self.last_outcome_index = (outcome, index)
            self.checkpoint()
            return ActionLeaf(selection, extract=lambda _: value, result=lambda _, result: result, label=f"{selection['kind']}:{index}", decision_index=index)
        self.checkpoint()

    def restore_checkpoint(self):
        """Restore latest source state after replay, before receiving new work."""
        if self._restored_source_state is not None:
            saved = self._restored_source_state
            self._restored_source_state = None
            self.last_outcome_index = saved['last_outcome_index']
            self.last_outcome = None if self.last_outcome_index is None else json.loads(self.workflow.journal.row('runtime_actions', self.episode_id, self.last_outcome_index)['result'])
            self.feedback = saved['feedback']

    def restore(self):
        restored = self.workflow.completions.restore_source(self.episode_id)
        self.calls = restored['next_call_index']
        effect = restored['latest_effect']
        if effect is not None:
            self.report_values = effect['report_values']
            self.report_basis = effect['report_basis_refs']
            self.feedback = effect['feedback']
        index = restored['last_completed_decision_index']
        if index is not None:
            action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            self.last_outcome = json.loads(action['result'])
            self.last_outcome_index = index
        self._unfinished_own_actions = self.workflow.inprocess_replay.unfinished(self) if self.workflow.inprocess_replay is not None else restored['unfinished_own_action_indices']
        self._latest_effect_index = restored['latest_effect_index']
        self._restored_source_state = restored['source_state']
        if self._restored_source_state is not None:
            self._source_revision = self._restored_source_state['revision']
        if self.workflow.execution_binding is not None:
            self.workflow.recover_commissions(self)
        if self.workflow.progress_provider is not None:
            self.workflow.progress_provider.flush_notifications()
        self._restored = True

    def record_effect(self, index, state):
        if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None:
            self.workflow.completions.record_decision_effect(self.episode_id, index, {'version': EFFECT_VERSION, 'state': state, 'report_values': self.report_values, 'report_basis_refs': self.report_basis, 'feedback': self.feedback})
            self._latest_effect_index = index
            self.checkpoint()

    def checkpoint(self):
        if self.workflow.inprocess_replay is not None and (not self._inprocess_replay_ready):
            return
        if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None:
            if self.workflow.inprocess_replay is not None and self._inprocess_replay_ready:
                self.workflow.inprocess_replay.capture(self)
            saved = self.workflow.completions.checkpoint_source(self.episode_id, expected_revision=self._source_revision, latest_effect_index=self._latest_effect_index, last_outcome_index=self.last_outcome_index, feedback=self.feedback)
            self._source_revision = saved['revision']
