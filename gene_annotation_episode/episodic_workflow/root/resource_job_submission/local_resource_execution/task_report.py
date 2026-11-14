from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.library.report_fact_assembly import facts as _private_report_facts

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

class LocalResourceTaskReport:
    async def finish(self, record):
        if self.request.report_contract is None:
            result = {'credit': self.workflow.source_credit_view(self)['credit'], 'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return Record(result)
        saved = self.workflow.journal.row('runtime_forms', self.episode_id)
        if saved and saved['form'] is not None:
            form = json.loads(saved['form'])
        else:
            facts = _invoke_private_policy(self.workflow.facts, _private_report_facts, self, completion_record=record)
            form = form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _json({**facts, 'interpretations': self.report_values}), 'form': _json(form)})
        await self.workflow.release(self.episode_id)
        return Record({'form': form})
