from gene_annotation_episode.episodic_workflow.root.a103.providers import DECISION_CONTEXT_VERSION, _ordinary_runtime_receiver_context, apply_state_frame, deepcopy, is_api_launch_context, is_published_scientific_context, json, render_api_launch_prompt, render_scientific_process_prompt, text_instructions

def present_job_results_task(self, episode_id, role, instructions, context):
    """Render declared TASKs from reconstructed state; preserve other inputs."""
    from gene_annotation_episode.episodic_workflow.root.a103.library.hpc_prompt import is_hpc_context, render_hpc_prompt
    from gene_annotation_episode.episodic_workflow.root.a103.library.monitor_prompt import is_monitor_context, render_monitor_prompt
    from gene_annotation_episode.episodic_workflow.root.a103.receiver_prompt import render_receiver_prompt
    from gene_annotation_episode.episodic_workflow.root.a103.native_profile_presentation import has_native_profile_receiver_context
    from gene_annotation_episode.episodic_workflow.root.a103.scientific_process_prompt import is_selected_execution_context, render_selected_execution_prompt

    def has_text_task(value):
        return is_hpc_context(value) or _live_original_providers.is_published_scientific_context(value) or is_monitor_context(value) or _live_original_providers.is_api_launch_context(value) or is_selected_execution_context(value) or has_native_profile_receiver_context(value) or _live_original_providers._ordinary_runtime_receiver_context(value)
    key = (episode_id, role)
    previous = self.scientific_prompt_states.get(key)
    state = None
    lookups = []
    if context.get('version') == _live_original_providers.DECISION_CONTEXT_VERSION:
        kind = context.get('kind')
        if kind == 'decision_bootstrap':
            if has_text_task(context.get('fields')):
                state = _live_original_providers.apply_state_frame(None, context)
                lookups = [row['lookup_result'] for row in context.get('restored_public_exchanges', ()) if 'lookup_result' in row]
            else:
                self.scientific_prompt_states.pop(key, None)
        elif kind == 'decision_update' and previous is not None:
            state = _live_original_providers.apply_state_frame(previous, context)
        elif kind == 'decision_update' and has_text_task(context.get('fields')):
            state = _live_original_providers.apply_state_frame(None, context)
        elif kind == 'decision_lookup_result' and previous is not None:
            state = previous
            lookups = [context.get('result')]
            if previous.get('contract_information_profile') == 'operation_contract_information_v1':
                lookups = list(context.get('pending_contract_information', ()))
                if context.get('result') not in lookups:
                    lookups.append(context.get('result'))
    elif has_text_task(context):
        state = _live_original_providers.deepcopy(context)
    if state is not None and has_text_task(state):
        if is_hpc_context(state):
            renderer = render_hpc_prompt
        elif _live_original_providers.is_published_scientific_context(state):
            renderer = _live_original_providers.render_scientific_process_prompt
        elif _live_original_providers.is_api_launch_context(state):
            renderer = _live_original_providers.render_api_launch_prompt
        elif is_selected_execution_context(state):
            renderer = render_selected_execution_prompt
        elif is_monitor_context(state) and (not has_native_profile_receiver_context(state)):
            renderer = render_monitor_prompt
        else:
            renderer = render_receiver_prompt
        rendered = renderer(state, instructions, lookup_results=lookups)
        self.scientific_prompt_states[key] = state
        return (rendered, _live_original_providers.text_instructions(instructions))
    if state is not None:
        self.scientific_prompt_states.pop(key, None)
    return (_live_original_providers.json.dumps(context, allow_nan=False), instructions)
present_job_results_task.provider_presentation = present_job_results_task
from gene_annotation_episode.episodic_workflow.root.a103 import providers as _live_original_providers
