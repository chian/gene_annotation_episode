"""Complete A110 native presentation with original dynamic predicates."""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a110.decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame
from gene_annotation_episode.episodic_workflow.root.a110.library.scientific_decision_presentation import _ordinary_runtime_receiver_context, is_published_scientific_context, text_instructions
from gene_annotation_episode.episodic_workflow.root.a110.scientific_process.task_decision import render_scientific_process_prompt

def present_context(provider, episode_id, role, instructions, context):
    """Render declared TASKs from reconstructed state; preserve other inputs."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.hpc_prompt import is_hpc_context, render_hpc_prompt
    from gene_annotation_episode.episodic_workflow.root.a110.library.monitor_prompt import is_monitor_context, render_monitor_prompt
    from gene_annotation_episode.episodic_workflow.root.a110.library.scientific_decision_presentation import is_selected_execution_context, render_selected_execution_prompt
    from gene_annotation_episode.episodic_workflow.root.a110.receiver_prompt import render_receiver_prompt

    def has_text_task(value):
        return is_hpc_context(value) or _live_original_providers.is_published_scientific_context(value) or is_monitor_context(value) or is_selected_execution_context(value) or _live_original_providers._ordinary_runtime_receiver_context(value)
    key = (episode_id, role)
    previous = provider.scientific_prompt_states.get(key)
    state = None
    lookups = []
    if context.get('version') == _live_original_providers.DECISION_CONTEXT_VERSION:
        kind = context.get('kind')
        if kind == 'decision_bootstrap':
            if has_text_task(context.get('fields')):
                state = _live_original_providers.apply_state_frame(None, context)
                lookups = [row['lookup_result'] for row in context.get('restored_public_exchanges', ()) if 'lookup_result' in row]
            else:
                provider.scientific_prompt_states.pop(key, None)
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
        elif is_selected_execution_context(state):
            renderer = render_selected_execution_prompt
        elif is_monitor_context(state):
            renderer = render_monitor_prompt
        else:
            renderer = render_receiver_prompt
        rendered = renderer(state, instructions, lookup_results=lookups)
        provider.scientific_prompt_states[key] = state
        return (rendered, _live_original_providers.text_instructions(instructions))
    if state is not None:
        provider.scientific_prompt_states.pop(key, None)
    return (_live_original_providers.json.dumps(context, allow_nan=False), instructions)
present_context.presentation_protocol = 'episode_context_presentation_v1'
from gene_annotation_episode.episodic_workflow.root.a110 import providers as _live_original_providers
