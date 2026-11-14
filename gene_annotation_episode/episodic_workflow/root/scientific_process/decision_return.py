from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.library.report_fact_assembly import facts as _private_report_facts
from .decision_contracts import (Mapping, nullcontext, inspect, json, sqlite3, subprocess, Draft202012Validator, ValidationError, AcquisitionError, ContractError, Episode, ReportRedelivery, SourceEnd, EventTargetError, interpretation_schema, validate_form, form_with_facts, ReportBoundaryError, WorkflowError, EFFECT_VERSION, observes_action_outcome, ContractInformationError, ActionLeaf, ActionFailure, Record, _plain, _json, _digest, _object, _action_generation_schema, _recorded_action_generation_schema, _recorded_assignment_transport, _decode_recorded_action_response, _ASSIGNMENT_TRANSPORT, _wait_target_feedback, schema_failure_diagnostic, _references_in, _category_yield_parameters, FACT_SOURCES, FACT_MEANINGS, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, literature_numerical_contracts, DECISION_EXCHANGE_PROTOCOL, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_INSTRUCTIONS, model_snapshot, state_frame, instructional_model_context, apply_state_frame, lookup_attempts, yield_table, infernal_receiver_context, composition_lookup_schema, child_option_information, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)

class ScientificDecisionReturn:
    async def finish(self, record):
        if self.request.report_contract is None:
            result = {"credit": self.workflow.source_credit_view(self)["credit"],
                'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(
                self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return Record(result)
        saved = self.workflow.journal.row("runtime_forms", self.episode_id)
        if saved and saved["form"] is not None:
            form = json.loads(saved["form"])
        else:
            facts = _invoke_private_policy(self.workflow.facts, _private_report_facts, self, completion_record=record)
            form = form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save("runtime_forms", {"episode_id": self.episode_id,
                "facts": _json({**facts, "interpretations": self.report_values}), "form": _json(form)})
        # This is the recorded candidate, not an admitted parent report.
        # The parent's separate report projection/admission can fail without
        # undoing completed science or losing the child's acquisition trace.
        await self.workflow.release(self.episode_id)
        return Record({"form": form})

