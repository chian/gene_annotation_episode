"""Dispatch the configured provider with the original prompt renderer and conversation identity."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table
from .instructions import instructions

class NativeDecisionProvider:

    def conversation_key(self):
        callback = getattr(self.workflow.provider, 'conversation_key', None)
        return None if callback is None else callback(self.episode_id, 'REASONING')

    async def complete_decision(self, instructions, context, schema):
        provider = self.workflow.provider
        complete = getattr(provider, 'complete_with_presentation', None)
        if complete is not None:
            binding = self.workflow.specialist(self)
            return await complete(self.episode_id, 'REASONING', instructions, context, schema, prompt_renderer=binding.decision_prompt_renderer)
        return await provider.complete(self.episode_id, 'REASONING', instructions, context, schema)
