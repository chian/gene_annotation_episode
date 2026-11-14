from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a107.decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame
from gene_annotation_episode.episodic_workflow.root.a107.library.scientific_decision_presentation import text_instructions
from gene_annotation_episode.episodic_workflow.root.a107.library.literature_source_presentation import is_literature_experimental_context
from .task_reading_prompt import render_literature_experimental_prompt

def present_source_context(self, episode_id, role, instructions, context):
    """Render declared TASKs from reconstructed state; preserve other inputs."""

    def has_text_task(value):
        return is_literature_experimental_context(value)
    key = (episode_id, role)
    previous = self.scientific_prompt_states.get(key)
    state = None
    lookups = []
    if context.get('version') == DECISION_CONTEXT_VERSION:
        kind = context.get('kind')
        if kind == 'decision_bootstrap':
            if has_text_task(context.get('fields')):
                state = apply_state_frame(None, context)
                lookups = [row['lookup_result'] for row in context.get('restored_public_exchanges', ()) if 'lookup_result' in row]
            else:
                self.scientific_prompt_states.pop(key, None)
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
        renderer = render_literature_experimental_prompt
        rendered = renderer(state, instructions, lookup_results=lookups)
        self.scientific_prompt_states[key] = state
        return (rendered, text_instructions(instructions))
    if state is not None:
        self.scientific_prompt_states.pop(key, None)
    presented = context
    return (json.dumps(presented, allow_nan=False), instructions)
present_source_context.presentation_protocol = 'episode_context_presentation_v1'
