"""Preserve original provider selection, state frames, priority and JSON fallback."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.providers import DECISION_CONTEXT_VERSION, apply_state_frame, deepcopy, json, text_instructions
from .presentation_selection import source_presentation_selection

def present_source_decision(self, episode_id, role, instructions, context):
    """Render declared TASKs from reconstructed state; preserve other inputs."""
    has_text_task, renderer_for = source_presentation_selection()
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
        renderer = renderer_for(state)
        rendered = renderer(state, instructions, lookup_results=lookups)
        self.scientific_prompt_states[key] = state
        return (rendered, _live_original_providers.text_instructions(instructions))
    if state is not None:
        self.scientific_prompt_states.pop(key, None)
    return (_live_original_providers.json.dumps(context, allow_nan=False), instructions)
present_source_decision.provider_presentation = present_source_decision
from gene_annotation_episode.episodic_workflow.root.a102 import providers as _live_original_providers
