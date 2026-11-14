"""Private HPC planning/allocation decision inputs."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.runtime import child_option_information

class HPCWorkDecisionInputs:


    def decision_inputs(self, context, index, profile):
        resource_context = self.workflow.resource_context(self)
        if resource_context is not None:
            context = {**context, 'resource_context': resource_context}
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
        if 'literature_completed_work' not in context:
            from gene_annotation_episode.episodic_workflow.root.a107.episode_work_report import completed_action_reports
            context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)
        from gene_annotation_episode.episodic_workflow.root.a107.library.hpc_prompt import is_hpc_context
        if is_hpc_context(context):
            from gene_annotation_episode.episodic_workflow.root.a107.episode_work_report import requested_action_history
            context['requested_action_history'] = requested_action_history(self.workflow, self, before=index)
        if 'pending_work' not in context:
            context = {**context, 'pending_work': self.workflow.pending_work(self)}
        binding = self.workflow.execution_expectations
        if binding is not None and binding.applies('hpc'):
            context = {**context, 'execution_expectations': binding.capture('hpc')}
        if self.workflow.resource_estimator is not None:
            if 'execution_expectations' in context:
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
from gene_annotation_episode.episodic_workflow.root.a107 import runtime as _live_original_runtime
