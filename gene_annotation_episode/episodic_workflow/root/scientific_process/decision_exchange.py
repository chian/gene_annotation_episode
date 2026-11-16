from __future__ import annotations
from .decision_contracts import (Mapping, nullcontext, inspect, json, sqlite3, subprocess, Draft202012Validator, ValidationError, AcquisitionError, ContractError, Episode, ReportRedelivery, SourceEnd, EventTargetError, interpretation_schema, validate_form, form_with_facts, ReportBoundaryError, WorkflowError, EFFECT_VERSION, observes_action_outcome, ContractInformationError, ActionLeaf, ActionFailure, Record, _plain, _json, _digest, _object, _action_generation_schema, _recorded_action_generation_schema, _recorded_assignment_transport, _decode_recorded_action_response, _ASSIGNMENT_TRANSPORT, _wait_target_feedback, schema_failure_diagnostic, _references_in, _category_yield_parameters, FACT_SOURCES, FACT_MEANINGS, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, literature_numerical_contracts, DECISION_EXCHANGE_PROTOCOL, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_INSTRUCTIONS, model_snapshot, state_frame, instructional_model_context, apply_state_frame, lookup_attempts, yield_table, infernal_receiver_context, composition_lookup_schema, child_option_information, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)

from .saved_exchange_contracts import ScientificSavedExchangeContracts

from .internal_decision_presentation import ScientificInternalDecisionPresentation

from .saved_decision_exchange import ScientificSavedDecisionExchange

from .new_decision_inputs import ScientificNewDecisionInputs

from .decision_provider import ScientificDecisionProvider

class ScientificDecisionExchange(ScientificDecisionProvider, ScientificNewDecisionInputs, ScientificSavedDecisionExchange, ScientificInternalDecisionPresentation, ScientificSavedExchangeContracts):
    async def call(self, context, schema):
        index, self.calls = self.calls, self.calls + 1
        journal = self.workflow.journal
        row = journal.row("runtime_model_calls", self.episode_id, index)
        if (row is None or row['response'] is None) and self.path[-1][0] == 'scientific_process':
            self.workflow.scientific_process_binding.validate_execution_context(
                self.workflow.binding_context(self))
        profile = self.workflow.contract_information_profile(self)
        if row:
            saved = json.loads(row["request"])
            if row["purpose"] != "decision":
                raise WorkflowError("saved decision contract differs from reconstruction")
            # Historical and interrupted decisions retain the actual contract
            # supplied at dispatch. Additions to today's tool catalog belong to
            # new decisions, not retrospective reconstruction of earlier ones.
            schema = saved["schema"]
            context = saved["context"]
            try:
                _recorded_assignment_transport(saved)
            except ValueError as error:
                raise WorkflowError(str(error)) from error
            if (profile is None) != ('contract_information' not in saved):
                raise WorkflowError('original_contract_information_profile_changed')
            if profile is not None:
                self.workflow.validate_contract_information(saved)
            if literature_numerical_contracts.SAVED_MEMBER in saved:
                if profile is not None:
                    raise WorkflowError('original_literature_numerical_profile_mismatch')
                literature_numerical_contracts.validate_frozen_contracts(saved)
            if (self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL
                    and saved.get('decision_protocol') != DECISION_EXCHANGE_PROTOCOL):
                raise WorkflowError('pending_decision_requires_original_protocol')
            if row["response"] is not None:
                if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
                    if profile is not None:
                        self.validate_contract_exchange_history(saved, index)
                    context = self.interpretation_context(context,
                        self.workflow.decision_exchanges.rows(self.episode_id, index))
                return json.loads(row["response"]), index, context, schema
        else:
            context, saved = self.prepare_new_decision_inputs(context, schema, index, profile)
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            if row is None:
                saved = {**saved, 'decision_protocol': DECISION_EXCHANGE_PROTOCOL}
                if profile is not None:
                    saved['contract_information'] = self.workflow.freeze_contract_information(self, context, schema)
                    self.workflow.validate_contract_information(saved)
                if (self.workflow.receipts is not None and not self.workflow.is_job_source(self)
                        and not self.workflow.uses_received_record_context(self)):
                    self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                        kind='decision_input', source_index=index)
                journal.save('runtime_model_calls', {'episode_id': self.episode_id,
                    'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': None})
            return await self.exchange_decision(context, schema, index, saved)
        return await self.dispatch_direct_decision(context, schema, index, saved, row, journal)

