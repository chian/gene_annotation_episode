"""Complete original own-A104 source presentation state machine."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.providers import DECISION_CONTEXT_VERSION, _ordinary_runtime_receiver_context, apply_state_frame, deepcopy, is_api_launch_context, is_published_scientific_context, json, render_api_launch_prompt, render_scientific_process_prompt, text_instructions

def source_presentation_selection():
    from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_prompt import is_hpc_context, render_hpc_prompt
    from gene_annotation_episode.episodic_workflow.root.a104.library.monitor_prompt import is_monitor_context, render_monitor_prompt
    from gene_annotation_episode.episodic_workflow.root.a104.receiver_prompt import render_receiver_prompt
    from gene_annotation_episode.episodic_workflow.root.a104.literature_experimental_prompt import is_literature_experimental_context
    from gene_annotation_episode.episodic_workflow.root.a104.library.source_component_prompt import render_component_axis_literature_prompt, with_fact_contract_instructions
    from gene_annotation_episode.episodic_workflow.root.a104.native_profile_presentation import has_native_profile_receiver_context
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process_prompt import has_evolutionary_receiver_context
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process_prompt import is_selected_execution_context, render_selected_execution_prompt

    def has_text_task(value):
        return is_hpc_context(value) or is_published_scientific_context(value) or is_monitor_context(value) or is_api_launch_context(value) or is_literature_experimental_context(value) or is_selected_execution_context(value) or has_native_profile_receiver_context(value) or has_evolutionary_receiver_context(value) or _ordinary_runtime_receiver_context(value)

    def renderer_for(state):
        if is_hpc_context(state):
            return render_hpc_prompt
        elif is_literature_experimental_context(state):
            return render_component_axis_literature_prompt
        elif is_published_scientific_context(state):
            return render_scientific_process_prompt
        elif is_api_launch_context(state):
            return render_api_launch_prompt
        elif is_selected_execution_context(state):
            return render_selected_execution_prompt
        elif is_monitor_context(state):
            return render_monitor_prompt
        else:
            return render_receiver_prompt

    return has_text_task, renderer_for, with_fact_contract_instructions
