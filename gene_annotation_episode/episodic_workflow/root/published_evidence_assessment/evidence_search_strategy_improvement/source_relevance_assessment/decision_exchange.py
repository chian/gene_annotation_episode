from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.decision_contracts import (Mapping, nullcontext, inspect, json, sqlite3, subprocess, Draft202012Validator, ValidationError, AcquisitionError, ContractError, Episode, ReportRedelivery, SourceEnd, EventTargetError, interpretation_schema, validate_form, form_with_facts, ReportBoundaryError, WorkflowError, EFFECT_VERSION, observes_action_outcome, ContractInformationError, ActionLeaf, ActionFailure, Record, _plain, _json, _digest, _object, _action_generation_schema, _recorded_action_generation_schema, _recorded_assignment_transport, _decode_recorded_action_response, _ASSIGNMENT_TRANSPORT, _wait_target_feedback, schema_failure_diagnostic, _references_in, _category_yield_parameters, FACT_SOURCES, FACT_MEANINGS, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, literature_numerical_contracts, DECISION_EXCHANGE_PROTOCOL, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_INSTRUCTIONS, model_snapshot, state_frame, instructional_model_context, apply_state_frame, lookup_attempts, yield_table, infernal_receiver_context, composition_lookup_schema, child_option_information, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)

from .saved_exchange_contracts import LiteratureSavedExchangeContracts

from .saved_decision_exchange import LiteratureSavedDecisionExchange

class LiteratureDecisionExchange(LiteratureSavedDecisionExchange, LiteratureSavedExchangeContracts):
    async def call(self, context, schema):
        index, self.calls = self.calls, self.calls + 1
        journal = self.workflow.journal
        row = journal.row("runtime_model_calls", self.episode_id, index)
        row is None or row['response'] is None
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
            # Selected manuals are exact immutable assignment operands. Supply
            # their bodies only to new calls; saved calls above keep the context
            # originally dispatched, including an interrupted request.
            resource_context = self.workflow.resource_context(self)
            if resource_context is not None:
                context = {**context, 'resource_context': resource_context}
            shared_context = self.workflow.shared_information_context(self)
            if shared_context is not None:
                context = {**context, 'shared_information_context': shared_context}
            from gene_annotation_episode.episodic_workflow.root.component_source_access import decision_context as source_access_context
            source_access = source_access_context(self.workflow, self.workflow.binding_context(self))
            if source_access is not None:
                context = {**context, 'component_axis_source_access': source_access}
            context = {**context,
                'launch_instruction_library': self.workflow.launch_instructions.context()}
            selected_instructions = self.workflow.launch_instructions.materialize(
                self.request.message.as_record().get('episode_assignment', {}).get('launch_instructions'))
            if selected_instructions is not None:
                context['selected_launch_instructions'] = selected_instructions
            if self.workflow.available_child_roles(self):
                context['child_options'] = child_option_information(self.workflow, self)['text']
            supplied_initial = self.workflow.episode_bindings.initial_decision_context(
                self.workflow.binding_context(self))
            if set(supplied_initial).intersection(context):
                raise ValueError('initial_binding_context_field_conflict')
            context = {**context, **supplied_initial}
            # Receiver-specific native views are supplied above. Build the
            # factual work/credit report only after those authorized results
            # are available; saved calls retain their original context.
            work_results = context.pop('_completed_work_axis_results', {})
            if ('literature_completed_work' not in context and not (
                    isinstance(context.get('current_credit'), Mapping)
                    and context['current_credit'].get('mode') == 'annotation_axis_credit')):
                from gene_annotation_episode.episodic_workflow.root.episode_work_report import completed_action_reports
                context['completed_action_reports'] = completed_action_reports(
                    self.workflow, self, context, before=index,
                    received_axis_results=work_results)
            from gene_annotation_episode.episodic_workflow.root.execution_operand_presentation import is_hpc_context
            if is_hpc_context(context):
                from gene_annotation_episode.episodic_workflow.root.episode_work_report import requested_action_history
                context['requested_action_history'] = requested_action_history(
                    self.workflow, self, before=index)
            if 'pending_work' not in context:
                # Direct caller dispatches need the same authoritative
                # outstanding-work input as next(). Saved decisions above
                # retain the exact original context instead.
                context = {**context, 'pending_work': self.workflow.pending_work(self)}
            binding = self.workflow.execution_expectations
            if binding is not None and binding.applies(self.path[-1][0]):
                planning_scopes = ()
                if (self.path[-1][0] in binding.planning_roles
                        and self.workflow.job_episodes is not None):
                    jobs = self.workflow.job_episodes
                    if 'search_modes' in jobs.jobs.config:
                        options = jobs.prospective_execution_options(self.workflow.store, self.scope)
                        planning_scopes = list({value['execution_class'].ref: value['execution_class']
                                                for value in options}.values())
                        context = {**context, 'job_execution_options': [
                            {key: value[key] for key in ('query_ref', 'cpu', 'search_mode')}
                            | {'execution_class_ref': value['execution_class'].ref}
                            for value in options]}
                    else:
                        planning_scopes = jobs.prospective_execution_classes(self.workflow.store, self.scope)
                context = {**context, "execution_expectations": binding.capture(self.path[-1][0],
                    assignment=self.request.message.as_record().get("job_assignment"),
                    planning_scopes=planning_scopes)}
            if self.workflow.resource_estimator is not None:
                if self.workflow.is_job_source(self):
                    estimates = self.workflow.resource_estimator.estimate(
                        context.get("execution_expectations"),
                        job_ref=self.workflow.job_episodes.assignment(self)["job_ref"],
                        sample=self.workflow.job_episodes.latest_sample(self, include_inherited=True))
                elif "execution_expectations" in context:
                    # Supply expected execution costs before the owning episode
                    # chooses work. These classes describe proposed execution.
                    estimates = self.workflow.resource_estimator.estimate_context(
                        context["execution_expectations"])
                else:
                    estimates = None
                if estimates is not None:
                    context = {**context, "resource_tool_estimates": estimates}
            native_expectations = self.workflow.native_estimation_context(self, context)
            if native_expectations is not None:
                context = {**context, 'native_execution_expectations': native_expectations}
                if self.workflow.resource_estimator is not None:
                    native_estimates = self.workflow.resource_estimator.estimate_context(native_expectations)
                    context['resource_tool_estimates'] = [*context.get('resource_tool_estimates', []), *native_estimates]
            if self.workflow.native_event_information is not None:
                context['native_event_targets'] = self.workflow.native_event_information.read(
                    self.workflow.binding_context(self))
            if self.workflow.permits_common_action(self, 'wait'):
                context['waiting_support'] = self.workflow.waiting_support(self, context)
            if profile is not None:
                context = {**context, 'contract_information_profile': profile}
            saved = {"context": context, "schema": schema}
            if profile is None:
                frozen = self.workflow.freeze_literature_numerical_contracts(self, context, schema)
                if frozen is not None:
                    saved[literature_numerical_contracts.SAVED_MEMBER] = frozen
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
            response = await self.decision_completion()(self.episode_id, "REASONING", instructions,
                                                              context, _action_generation_schema(schema))
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": _json(response)})
        return response, index, saved["context"], schema

    def conversation_key(self):
        callback = getattr(self.workflow.provider, 'conversation_key', None)
        return None if callback is None else callback(self.episode_id, 'REASONING')

