"""Own fresh Resource decision inputs and received custody views."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table

class ResourceDecisionInputs:


    def decision_inputs(self, context, index, profile):
        resource_context = self.workflow.resource_context(self)
        if resource_context is not None:
            context = {**context, 'resource_context': resource_context}
        shared_context = self.workflow.shared_information_context(self)
        if shared_context is not None:
            context = {**context, 'shared_information_context': shared_context}
        context = {**context, 'launch_instruction_library': self.workflow.launch_instructions.context()}
        selected_instructions = self.workflow.launch_instructions.materialize(self.request.message.as_record().get('episode_assignment', {}).get('launch_instructions'))
        if selected_instructions is not None:
            context['selected_launch_instructions'] = selected_instructions
        if self.workflow.available_child_roles(self):
            context['child_options'] = _live_original_runtime.child_option_information(self.workflow, self)['text']
        supplied_initial = self.workflow.episode_bindings.initial_decision_context(self.workflow.binding_context(self))
        if set(supplied_initial).intersection(context):
            raise ValueError('initial_binding_context_field_conflict')
        context = {**context, **supplied_initial}
        work_results = context.pop('_completed_work_axis_results', {})
        if 'literature_completed_work' not in context and (not (isinstance(context.get('current_credit'), _live_original_runtime.Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit')):
            from gene_annotation_episode.episodic_workflow.root.a102.episode_work_report import completed_action_reports
            context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)
        from gene_annotation_episode.episodic_workflow.root.a102.library.hpc_prompt import is_hpc_context
        if is_hpc_context(context):
            from gene_annotation_episode.episodic_workflow.root.a102.episode_work_report import requested_action_history
            context['requested_action_history'] = requested_action_history(self.workflow, self, before=index)
        if 'pending_work' not in context:
            context = {**context, 'pending_work': self.workflow.pending_work(self)}
        binding = self.workflow.execution_expectations
        if binding is not None and binding.applies('launch_api'):
            context = {**context, 'execution_expectations': binding.capture('launch_api')}
        if self.workflow.resource_estimator is not None:
            if self.workflow.is_job_source(self):
                estimates = self.workflow.resource_estimator.estimate(context.get('execution_expectations'), job_ref=self.workflow.job_episodes.assignment(self)['job_ref'], sample=self.workflow.job_episodes.latest_sample(self, include_inherited=True))
            elif 'execution_expectations' in context:
                estimates = self.workflow.resource_estimator.estimate_context(context['execution_expectations'])
            else:
                estimates = None
            if estimates is not None:
                context = {**context, 'resource_tool_estimates': estimates}
        native_expectations = self.workflow.native_estimation_context(self, context)
        if native_expectations is not None:
            context = {**context, 'native_execution_expectations': native_expectations}
            if self.workflow.resource_estimator is not None:
                native_estimates = self.workflow.resource_estimator.estimate_context(native_expectations)
                context['resource_tool_estimates'] = [*context.get('resource_tool_estimates', []), *native_estimates]
        if self.workflow.permits_common_action(self, 'wait'):
            context['waiting_support'] = self.workflow.waiting_support(self, context)
        if profile is not None:
            context = {**context, 'contract_information_profile': profile}
        return context
from gene_annotation_episode.episodic_workflow.root.a102 import runtime as _live_original_runtime
