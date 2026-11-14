"""Original decision-frame reconstruction for an explicitly selected presentation.

Episode owners supply their applicability and text renderer. This module keeps
frame revision checks, restored/pending lookups, state caching and the original
non-text projection and serialization. It does not select an episode or task.
"""
from copy import deepcopy
import json
from .decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame


def present_decision_context(self, episode_id, role, instructions, context, *,
                             has_text_task, render_task, text_instructions,
                             infernal_receiver_context):
    key = (episode_id, role)
    previous = self.scientific_prompt_states.get(key)
    state = None
    lookups = []
    if context.get("version") == DECISION_CONTEXT_VERSION:
        kind = context.get("kind")
        if kind == "decision_bootstrap":
            if has_text_task(context.get("fields")):
                state = apply_state_frame(None, context)
                lookups = [row["lookup_result"] for row in
                    context.get("restored_public_exchanges", ()) if "lookup_result" in row]
            else:
                self.scientific_prompt_states.pop(key, None)
        elif kind == "decision_update" and previous is not None:
            state = apply_state_frame(previous, context)
        elif kind == "decision_update" and has_text_task(context.get("fields")):
            # A delta cannot establish the missing task/base state.
            state = apply_state_frame(None, context)
        elif kind == "decision_lookup_result" and previous is not None:
            state = previous
            lookups = [context.get("result")]
            if previous.get('contract_information_profile') == 'operation_contract_information_v1':
                lookups = list(context.get('pending_contract_information', ()))
                if context.get('result') not in lookups:
                    lookups.append(context.get('result'))
    elif has_text_task(context):
        # The legacy exchange protocol can carry a newly published process.
        # It already supplies the full state; its response schema is intact.
        state = deepcopy(context)
    if state is not None and has_text_task(state):
        rendered = render_task(state, instructions, lookups)
        self.scientific_prompt_states[key] = state
        return rendered, text_instructions(instructions)
    if state is not None:
        self.scientific_prompt_states.pop(key, None)
    # Legacy full contexts need the same received-result projection as
    # model_snapshot. Framed contexts were projected before their hashes
    # were computed; do not rewrite a frame or its revision here.
    presented = (context if context.get("version") == DECISION_CONTEXT_VERSION
                 else infernal_receiver_context(context))
    return json.dumps(presented, allow_nan=False), instructions
