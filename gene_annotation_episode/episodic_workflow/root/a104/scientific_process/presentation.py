"""Complete original A104 presentation precedence and transport state."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.providers import DECISION_CONTEXT_VERSION, _ordinary_runtime_receiver_context, apply_state_frame, deepcopy, is_api_launch_context, is_published_scientific_context, json, render_api_launch_prompt, render_scientific_process_prompt, text_instructions

def present_scientific_context(provider, episode_id, role, instructions, context):
    from .presentation_selection import task_presentation_selection
    has_text_task, renderer_for = task_presentation_selection()
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
        renderer = renderer_for(state)
        rendered = renderer(state, instructions, lookup_results=lookups)
        provider.scientific_prompt_states[key] = state
        return (rendered, text_instructions(instructions))
    if state is not None:
        provider.scientific_prompt_states.pop(key, None)
    return (json.dumps(context, allow_nan=False), instructions)
present_scientific_context.presentation_protocol = 'episode_context_presentation_v1'
