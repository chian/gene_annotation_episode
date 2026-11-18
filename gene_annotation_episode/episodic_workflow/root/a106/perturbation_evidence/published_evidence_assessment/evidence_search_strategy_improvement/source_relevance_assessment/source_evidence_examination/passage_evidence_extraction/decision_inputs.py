"""Private A106 literature_targeted decision inputs."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import Mapping, child_option_information

from .decision_presentation import prepare_completed_work

class LiteratureDecisionInputs:

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
            context['child_options'] = _a106_original_global_child_option_information()(self.workflow, self)['text']
        supplied_initial = self.workflow.episode_bindings.initial_decision_context(self.workflow.binding_context(self))
        if _a106_original_global_set()(supplied_initial).intersection(context):
            raise _a106_original_global_ValueError()('initial_binding_context_field_conflict')
        context = {**context, **supplied_initial}
        prepare_completed_work(self, context, index)
        if 'pending_work' not in context:
            context = {**context, 'pending_work': self.workflow.pending_work(self)}
        binding = self.workflow.execution_expectations
        if binding is not None and binding.applies(self.path[-1][0]):
            context = {**context, 'execution_expectations': binding.capture(self.path[-1][0])}
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

    def current_decision_inputs(self, view, delivery_ref):
        context = self.decision_state(view)
        schema = self.workflow.action_schema(self)
        if delivery_ref is not None:
            context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
        return context, schema


def _a106_original_global_ValueError():
    return ValueError


def _a106_original_global_child_option_information():
    return child_option_information


def _a106_original_global_set():
    return set


def _bind_original_task_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a106.library.live_runtime_functions import bind_functions
    getters = {'_a106_original_global_ValueError': '_a106_original_global_ValueError', '_a106_original_global_child_option_information': '_a106_original_global_child_option_information', '_a106_original_global_set': '_a106_original_global_set'}
    globals().update(bind_functions(namespace, {name: globals()[name] for name in getters},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=getters, defining_module='gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.decision_inputs'))

from gene_annotation_episode.episodic_workflow.root.a106 import runtime as _a106_original_runtime
_bind_original_task_runtime_providers(vars(_a106_original_runtime))
