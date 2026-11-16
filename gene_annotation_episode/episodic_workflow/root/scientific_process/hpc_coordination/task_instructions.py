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

class HPCCoordinationTaskInstructions:
    def instructions(self, context):
        instructions = self.workflow.job_episodes.instructions(self.path[-1][0]) if self.workflow.is_job_source(self) else INSTRUCTIONS
        specialist = self.workflow.specialist(self)
        if specialist is not None:
            specialized = specialist.instructions(self.workflow.binding_context(self))
            instructions = specialized if getattr(specialist, 'replaces_default_instructions', False) else instructions + '\n' + specialized
        if self.workflow.permits_common_action(self, 'reason'):
            instructions += '\n' + REASONING_COMMIT_REQUIREMENT
        if 'tool_knowledge' in context:
            instructions += KNOWLEDGE_INSTRUCTIONS
        if 'launch_instruction_library' in context:
            instructions += LAUNCH_INSTRUCTIONS
        instructions += '\nWhen pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work.'
        if self.workflow.permits_common_action(self, 'wait'):
            instructions += '\nA pending_child_ handle names your original in-process child, not an external event-provider target. To give its existing scheduler time to collect owned work, select wait with that handle, event returned, after_cursor 0 and reconsider_at null. An earlier ready owned sibling may wake this wait first; its original return is then collected before another decision. Waiting only reports readiness and earns no scientific credit. In-process state_changed/progress_committed events and mixed external wait conditions are not supported by this collection channel.'
        if self.workflow.native_event_information is not None and self.workflow.permits_common_action(self, 'wait'):
            instructions += '\nThe separate native_event_targets input names native notification targets assigned or actually received by this episode. A target is registration metadata, not proof that submission succeeded. Its state_changed event means the original service exit receipt was committed; the service may still be closing, so this does not establish result readiness or a child episode return. after_cursor records an event cursor actually received, initially zero. Select your own wait condition and subsequent status/monitor/result work. Request the native_event_targets source in original child forms when that handoff is needed. No event probability, gain or scientific credit follows from registration or passing time alone.'
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            history_guidance = INSTRUCTIONS[INSTRUCTIONS.index('On a fresh provider conversation,'):INSTRUCTIONS.index('Do not execute native provider tools.')]
            instructions = instructions.replace(history_guidance, 'Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again.\n')
        return instructions
