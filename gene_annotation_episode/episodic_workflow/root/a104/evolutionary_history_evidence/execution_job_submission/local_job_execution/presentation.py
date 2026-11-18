"""Original complete A104 LocalExecution context presentation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.providers import DECISION_CONTEXT_VERSION, _ordinary_runtime_receiver_context, apply_state_frame, deepcopy, is_api_launch_context, is_published_scientific_context, json, render_api_launch_prompt, render_evolutionary_history_evidence_prompt, text_instructions

def present_execution_context(provider, episode_id, role, instructions, context):
    """Render declared TASKs from reconstructed state; preserve other inputs."""
    from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_prompt import is_hpc_context, render_hpc_prompt
    from gene_annotation_episode.episodic_workflow.root.a104.library.monitor_prompt import is_monitor_context, render_monitor_prompt
    from gene_annotation_episode.episodic_workflow.root.a104.receiver_prompt import render_receiver_prompt
    from gene_annotation_episode.episodic_workflow.root.a104.native_profile_presentation import has_native_profile_receiver_context
    from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence_prompt import has_evolutionary_receiver_context
    from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence_prompt import is_selected_execution_context, render_selected_execution_prompt

    def has_text_task(value):
        return is_hpc_context(value) or is_published_scientific_context(value) or is_monitor_context(value) or is_api_launch_context(value) or is_selected_execution_context(value) or has_native_profile_receiver_context(value) or has_evolutionary_receiver_context(value) or _ordinary_runtime_receiver_context(value)
    key = (episode_id, role)
    previous = provider.scientific_prompt_states.get(key)
    state = None
    lookups = []
    if context.get('version') == DECISION_CONTEXT_VERSION:
        kind = context.get('kind')
        if kind == 'decision_bootstrap':
            if has_text_task(context.get('fields')):
                state = apply_state_frame(None, context)
                lookups = [row['lookup_result'] for row in context.get('restored_public_exchanges', ()) if 'lookup_result' in row]
            else:
                provider.scientific_prompt_states.pop(key, None)
        elif kind == 'decision_update' and previous is not None:
            state = apply_state_frame(previous, context)
        elif kind == 'decision_update' and has_text_task(context.get('fields')):
            state = apply_state_frame(None, context)
        elif kind == 'decision_lookup_result' and previous is not None:
            state = previous
            lookups = [context.get('result')]
            if previous.get('contract_information_profile') == 'operation_contract_information_v1':
                lookups = list(context.get('pending_contract_information', ()))
                if context.get('result') not in lookups:
                    lookups.append(context.get('result'))
    elif has_text_task(context):
        state = deepcopy(context)
    if state is not None and has_text_task(state):
        if is_hpc_context(state):
            renderer = render_hpc_prompt
        elif is_published_scientific_context(state):
            renderer = render_evolutionary_history_evidence_prompt
        elif is_api_launch_context(state):
            renderer = render_api_launch_prompt
        elif is_selected_execution_context(state):
            renderer = render_selected_execution_prompt
        elif is_monitor_context(state):
            renderer = render_monitor_prompt
        else:
            renderer = render_receiver_prompt
        rendered = renderer(state, instructions, lookup_results=lookups)
        provider.scientific_prompt_states[key] = state
        return (rendered, text_instructions(instructions))
    if state is not None:
        provider.scientific_prompt_states.pop(key, None)
    return (json.dumps(context, allow_nan=False), instructions)
present_execution_context.presentation_protocol = 'episode_context_presentation_v1'
