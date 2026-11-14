from __future__ import annotations
from .decision_contracts import (Mapping, nullcontext, inspect, json, sqlite3, subprocess, Draft202012Validator, ValidationError, AcquisitionError, ContractError, Episode, ReportRedelivery, SourceEnd, EventTargetError, interpretation_schema, validate_form, form_with_facts, ReportBoundaryError, WorkflowError, EFFECT_VERSION, observes_action_outcome, ContractInformationError, ActionLeaf, ActionFailure, Record, _plain, _json, _digest, _object, _action_generation_schema, _recorded_action_generation_schema, _recorded_assignment_transport, _decode_recorded_action_response, _ASSIGNMENT_TRANSPORT, _wait_target_feedback, schema_failure_diagnostic, _references_in, _category_yield_parameters, FACT_SOURCES, FACT_MEANINGS, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, literature_numerical_contracts, DECISION_EXCHANGE_PROTOCOL, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_INSTRUCTIONS, model_snapshot, state_frame, instructional_model_context, apply_state_frame, lookup_attempts, yield_table, infernal_receiver_context, composition_lookup_schema, child_option_information, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)

from .saved_exchange_contracts import ScientificSavedExchangeContracts

from .internal_decision_presentation import ScientificInternalDecisionPresentation

from .saved_decision_exchange import ScientificSavedDecisionExchange

class ScientificDecisionProvider:

    async def dispatch_direct_decision(self, context, schema, index, saved, row, journal):
        has_session = getattr(self.workflow.provider, "has_session", lambda *_: False)
        if (not has_session(self.episode_id, "REASONING")
                and "restored_episode_history" not in context):
            # Restore the authoritative scientific/runtime state through the
            # existing replay path, not by rehydrating all archived contexts.
            # The fresh native conversation receives only a bounded metadata
            # index; exact older selections/outcomes are an ordinary own read.
            context = {**context, "restored_episode_history":
                self.workflow.history_preview(self, before=index)}
        context = instructional_model_context(context)
        # Save the exact supplied context, including its bounded operational
        # index, before dispatch. Completed historical calls are returned above
        # unchanged. Metadata contains no old contexts, so it cannot nest them.
        transport = (saved.get('assignment_transport') if row is not None else
            {'version': _ASSIGNMENT_TRANSPORT, 'action_schema_sha256': _digest(schema)})
        saved = {"context": context, "schema": schema,
            **({literature_numerical_contracts.SAVED_MEMBER: saved[literature_numerical_contracts.SAVED_MEMBER]}
                if literature_numerical_contracts.SAVED_MEMBER in saved else {})}
        if transport is not None:
            saved['assignment_transport'] = transport
        if (self.workflow.receipts is not None and not self.workflow.is_job_source(self)
                and not self.workflow.uses_received_record_context(self)):
            # Scientific information is admitted through explicit inputs,
            # own outcomes and requested returns, independently of the scalar
            # credit callable. Other role inputs retain their existing delivery.
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                kind='decision_input', source_index=index)
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": None})
        with journal.measure("runtime_model_calls", self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.workflow.provider.complete(self.episode_id, "REASONING", instructions,
                                                              context, _action_generation_schema(schema))
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": _json(response)})
        return response, index, saved["context"], schema

    async def dispatch_exchange_decision(self, request, index, exchange_index, journal, exchanges):
        with journal.measure('runtime_model_calls', self.episode_id, index):
            with exchanges.measure(self.episode_id, index, exchange_index):
                response = await self.workflow.provider.complete(self.episode_id, 'REASONING',
                    request['instructions'], request['context'], request['output_schema'])
        return response
