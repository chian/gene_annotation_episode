from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.library.report_fact_assembly import facts as _private_report_facts
from gene_annotation_episode.episodic_workflow.root.a103.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.a103.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a103.runtime import ActionFailure
from gene_annotation_episode.episodic_workflow.root.a103.runtime import ActionLeaf
from gene_annotation_episode.episodic_workflow.root.a103.composition_information import CONTRACT_INFORMATION_OPERATIONS
from gene_annotation_episode.episodic_workflow.root.a103.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a103.episode_contract_information import ContractInformationError
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import VERSION as DECISION_CONTEXT_VERSION
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a103.episode_completion import EFFECT_VERSION
from gene_annotation_episode.episodic_workflow.root.a103.method_loop.episode import Episode
from gene_annotation_episode.episodic_workflow.root.a103.method_loop.durable import EventTargetError
from gene_annotation_episode.episodic_workflow.root.a103.runtime import FACT_MEANINGS
from gene_annotation_episode.episodic_workflow.root.a103.runtime import FACT_SOURCES
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.a103.runtime import Record
from gene_annotation_episode.episodic_workflow.root.a103.communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.a103.method_loop.episode import ReportRedelivery
from gene_annotation_episode.episodic_workflow.root.a103.method_loop.episode import SourceEnd
from jsonschema import ValidationError
from gene_annotation_episode.episodic_workflow.root.a103.episode_journal import WorkflowError
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _ASSIGNMENT_TRANSPORT
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _action_generation_schema
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _category_yield_parameters
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _decode_recorded_action_response
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _digest
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _json
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _object
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _plain
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _recorded_action_generation_schema
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _recorded_assignment_transport
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _references_in
from gene_annotation_episode.episodic_workflow.root.a103.runtime import _wait_target_feedback
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import apply_state_frame
from gene_annotation_episode.episodic_workflow.root.a103.composition_information import child_options as child_option_information
from gene_annotation_episode.episodic_workflow.root.a103.composition_information import lookup_schema as composition_lookup_schema
from gene_annotation_episode.episodic_workflow.root.a103.communication import form_with_facts
import inspect
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import instructional_model_context
from gene_annotation_episode.episodic_workflow.root.a103.communication import interpretation_schema
from gene_annotation_episode.episodic_workflow.root.a103.composition_information import is_contract_information
import json
from gene_annotation_episode.episodic_workflow.root.a103.decision_history import lookup_attempts
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import model_snapshot
from contextlib import nullcontext
from gene_annotation_episode.episodic_workflow.root.a103.episode_completion import observes_action_outcome
from gene_annotation_episode.episodic_workflow.root.a103.composition_information import requested_contract_information
from gene_annotation_episode.episodic_workflow.root.a103.boundary_validation import schema_failure_diagnostic
import sqlite3
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import state_frame
import subprocess
from gene_annotation_episode.episodic_workflow.root.a103.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.a103.decision_history import yield_table

class LegacyImprovementReportDelivery:


    async def finish(self, record):
        if self.request.report_contract is None:
            result = {'credit': self.workflow.source_credit_view(self)['credit'], 'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return _live_original_runtime.Record(result)
        saved = self.workflow.journal.row('runtime_forms', self.episode_id)
        if saved and saved['form'] is not None:
            form = _live_original_runtime.json.loads(saved['form'])
        else:
            facts = _invoke_private_policy(self.workflow.facts, _private_report_facts, self, completion_record=record)
            form = _live_original_runtime.form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _live_original_runtime._json({**facts, 'interpretations': self.report_values}), 'form': _live_original_runtime._json(form)})
        await self.workflow.release(self.episode_id)
        return _live_original_runtime.Record({'form': form})
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
