"""Private A103 literature_search decision inputs."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.runtime import Mapping, child_option_information

class SourceTaskDecisionInputs:


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
            from gene_annotation_episode.episodic_workflow.root.a103.episode_work_report import completed_action_reports
            context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)
        from gene_annotation_episode.episodic_workflow.root.a103.library.hpc_prompt import is_hpc_context
        if is_hpc_context(context):
            from gene_annotation_episode.episodic_workflow.root.a103.episode_work_report import requested_action_history
            context['requested_action_history'] = requested_action_history(self.workflow, self, before=index)
        if 'pending_work' not in context:
            context = {**context, 'pending_work': self.workflow.pending_work(self)}
        binding = self.workflow.execution_expectations
        if binding is not None and binding.applies('literature_search'):
            planning_scopes = ()
            if 'literature_search' in binding.planning_roles and self.workflow.job_episodes is not None:
                jobs = self.workflow.job_episodes
                if 'search_modes' in jobs.jobs.config:
                    options = jobs.prospective_execution_options(self.workflow.store, self.scope)
                    planning_scopes = list({value['execution_class'].ref: value['execution_class'] for value in options}.values())
                    context = {**context, 'job_execution_options': [{key: value[key] for key in ('query_ref', 'cpu', 'search_mode')} | {'execution_class_ref': value['execution_class'].ref} for value in options]}
                else:
                    planning_scopes = jobs.prospective_execution_classes(self.workflow.store, self.scope)
            context = {**context, 'execution_expectations': binding.capture('literature_search', assignment=self.request.message.as_record().get('job_assignment'), planning_scopes=planning_scopes)}
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
        if self.workflow.native_event_information is not None:
            context['native_event_targets'] = self.workflow.native_event_information.read(self.workflow.binding_context(self))
        if profile is not None:
            context = {**context, 'contract_information_profile': profile}
        return context
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
