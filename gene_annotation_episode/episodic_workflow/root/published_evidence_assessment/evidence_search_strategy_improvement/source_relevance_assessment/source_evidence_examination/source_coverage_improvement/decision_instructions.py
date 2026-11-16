from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.decision_contracts import (Mapping, nullcontext, inspect, json, sqlite3, subprocess, Draft202012Validator, ValidationError, AcquisitionError, ContractError, Episode, ReportRedelivery, SourceEnd, EventTargetError, interpretation_schema, validate_form, form_with_facts, ReportBoundaryError, WorkflowError, EFFECT_VERSION, observes_action_outcome, ContractInformationError, ActionLeaf, ActionFailure, Record, _plain, _json, _digest, _object, _action_generation_schema, _recorded_action_generation_schema, _recorded_assignment_transport, _decode_recorded_action_response, _ASSIGNMENT_TRANSPORT, _wait_target_feedback, schema_failure_diagnostic, _references_in, _category_yield_parameters, FACT_SOURCES, FACT_MEANINGS, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, literature_numerical_contracts, DECISION_EXCHANGE_PROTOCOL, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_INSTRUCTIONS, model_snapshot, state_frame, instructional_model_context, apply_state_frame, lookup_attempts, yield_table, infernal_receiver_context, composition_lookup_schema, child_option_information, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)

class LiteratureDecisionInstructions:
    def instructions(self, context):
        instructions = (self.workflow.job_implementation(path=self.path).instructions(self.path[-1][0])
                        if self.workflow.is_job_source(self) else INSTRUCTIONS)
        specialist = self.workflow.specialist(self)
        if specialist is not None:
            specialized = specialist.instructions(self.workflow.binding_context(self))
            instructions = (specialized if getattr(specialist, 'replaces_default_instructions', False)
                            else instructions + '\n' + specialized)
        if self.workflow.permits_common_action(self, 'reason'):
            instructions += '\n' + REASONING_COMMIT_REQUIREMENT
        if 'tool_knowledge' in context:
            instructions += KNOWLEDGE_INSTRUCTIONS
        if 'launch_instruction_library' in context:
            instructions += LAUNCH_INSTRUCTIONS
        instructions += ('\nWhen pending_child_delivery is supplied, the selected child has finished '
            'its work but its typed return has not been delivered. Complete that existing '
            'acquisition by selecting redeliver_report with a corrected form. Use only the '
            'saved child facts and interpretations for this repair and preserve '
            'current_report_update. The supplied selection schema describes the available '
            'communication operation; this repair does not select new scientific work.')
        if self.workflow.permits_common_action(self, 'wait'):
            instructions += ('\nA pending_child_ handle names your original in-process child, '
                'not an external event-provider target. To give its existing scheduler time '
                'to collect owned work, select wait with that handle, event returned, '
                'after_cursor 0 and reconsider_at null. An earlier ready owned sibling may '
                'wake this wait first; its original return is then collected before another '
                'decision. Waiting only reports readiness and earns no scientific credit. '
                'In-process state_changed/progress_committed events and mixed external '
                'wait conditions are not supported by this collection channel.')
        if (self.workflow.native_event_information is not None
                and self.workflow.permits_common_action(self, 'wait')):
            instructions += ('\nThe separate native_event_targets input names native notification '
                'targets assigned or actually received by this episode. A target is registration '
                'metadata, not proof that submission succeeded. Its state_changed event means '
                'the original service exit receipt was committed; the service may still be '
                'closing, so this does not establish result readiness or a child episode return. '
                'after_cursor records an event cursor actually received, initially zero. Select '
                'your own wait condition and subsequent status/monitor/result work. Request the '
                'native_event_targets source in original child forms when that handoff is needed. '
                'No event probability, gain or scientific credit follows from registration or '
                'passing time alone.')
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            history_guidance = INSTRUCTIONS[INSTRUCTIONS.index('On a fresh provider conversation,'):
                INSTRUCTIONS.index('Do not execute native provider tools.')]
            instructions = instructions.replace(history_guidance,
                'Use request_context exchanges for your own attempt metadata and selected inputs; '
                'these create no completed action or observation. Read exact previously received '
                'outcomes with the ordinary episode.history tool, view=records and selected '
                'decision_indices. That read supplies its own ordinary action observation and '
                'does not execute or credit the historical work again.\n')
        return instructions

