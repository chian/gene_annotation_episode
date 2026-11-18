"""Private HPC planning/allocation decision inputs."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import child_option_information

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
            context['child_options'] = child_option_information(self.workflow, self)['text']
        supplied_initial = self.workflow.episode_bindings.initial_decision_context(self.workflow.binding_context(self))
        if set(supplied_initial).intersection(context):
            raise ValueError('initial_binding_context_field_conflict')
        context = {**context, **supplied_initial}
        work_results = context.pop('_completed_work_axis_results', {})
        if 'literature_completed_work' not in context:
            from gene_annotation_episode.episodic_workflow.root.a104.episode_work_report import completed_action_reports
            context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)
        from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_prompt import is_hpc_context
        if is_hpc_context(context):
            from gene_annotation_episode.episodic_workflow.root.a104.episode_work_report import requested_action_history
            context['requested_action_history'] = requested_action_history(self.workflow, self, before=index)
        if 'pending_work' not in context:
            context = {**context, 'pending_work': self.workflow.pending_work(self)}
        binding = self.workflow.execution_expectations
        if binding is not None and binding.applies('hpc'):
            planning_scopes = ()
            if 'hpc' in binding.planning_roles and self.workflow.job_episodes is not None:
                jobs = self.workflow.job_episodes
                if 'search_modes' in jobs.jobs.config:
                    options = jobs.prospective_execution_options(self.workflow.store, self.scope)
                    planning_scopes = list({value['execution_class'].ref: value['execution_class'] for value in options}.values())
                    context = {**context, 'job_execution_options': [{key: value[key] for key in ('query_ref', 'cpu', 'search_mode')} | {'execution_class_ref': value['execution_class'].ref} for value in options]}
                else:
                    planning_scopes = jobs.prospective_execution_classes(self.workflow.store, self.scope)
            context = {**context, 'execution_expectations': binding.capture('hpc', assignment=self.request.message.as_record().get('job_assignment'), planning_scopes=planning_scopes)}
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
        if self.workflow.permits_common_action(self, 'wait'):
            context['waiting_support'] = self.workflow.waiting_support(self, context)
        if profile is not None:
            context = {**context, 'contract_information_profile': profile}
        return context


def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'HPCWorkDecisionInputs.decision_inputs': HPCWorkDecisionInputs.__dict__['decision_inputs']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.decision_inputs')
    setattr(HPCWorkDecisionInputs, 'decision_inputs', bound['HPCWorkDecisionInputs.decision_inputs'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
