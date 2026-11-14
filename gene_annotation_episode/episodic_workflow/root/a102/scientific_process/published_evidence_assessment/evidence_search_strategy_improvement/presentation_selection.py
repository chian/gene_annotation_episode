"""Select named presentation libraries for this private source's supplied context."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.providers import _ordinary_runtime_receiver_context, is_api_launch_context, is_published_scientific_context, render_api_launch_prompt, render_scientific_process_prompt

def source_presentation_selection():
    """Retain per-call imports, predicate order and accepted caller operands."""
    from gene_annotation_episode.episodic_workflow.root.a102.library.hpc_prompt import is_hpc_context, render_hpc_prompt
    from gene_annotation_episode.episodic_workflow.root.a102.library.monitor_prompt import is_monitor_context, render_monitor_prompt
    from gene_annotation_episode.episodic_workflow.root.a102.receiver_prompt import render_receiver_prompt
    from gene_annotation_episode.episodic_workflow.root.a102.scientific_process_prompt import is_selected_execution_context, render_selected_execution_prompt

    def has_text_task(value):
        return is_hpc_context(value) or _live_original_providers.is_published_scientific_context(value) or is_monitor_context(value) or _live_original_providers.is_api_launch_context(value) or is_selected_execution_context(value) or _live_original_providers._ordinary_runtime_receiver_context(value)

    def renderer_for(state):
        if is_hpc_context(state):
            renderer = render_hpc_prompt
        elif _live_original_providers.is_published_scientific_context(state):
            renderer = _live_original_providers.render_scientific_process_prompt
        elif _live_original_providers.is_api_launch_context(state):
            renderer = _live_original_providers.render_api_launch_prompt
        elif is_selected_execution_context(state):
            renderer = render_selected_execution_prompt
        elif is_monitor_context(state):
            renderer = render_monitor_prompt
        else:
            renderer = render_receiver_prompt
        return renderer
    return (has_text_task, renderer_for)
from gene_annotation_episode.episodic_workflow.root.a102 import providers as _live_original_providers
