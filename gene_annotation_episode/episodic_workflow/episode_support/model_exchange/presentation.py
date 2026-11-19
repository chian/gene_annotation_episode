"""What the model sees for one decision: the decision context an episode assembles and how it is presented.

The old runner assembled the decision context through ``decision_inputs`` (optional pieces added only when
present, ``initial_binding_context_field_conflict`` on a clash) and its per-axis providers rendered declared
task contexts into text (``present_task_context``: ``has_text_task`` / ``renderer_for`` /
``text_instructions``). The new ``model_provider.complete`` sends ``context`` as one JSON input and renders
nothing, so an episode that presents a rendered text task sends it inside its context mapping.
"""
from __future__ import annotations

from collections.abc import Mapping


def extend_context(context, additions, *, conflict):
    """``context`` with every addition whose value is not ``None``; a name already present raises.

    ``conflict`` is the error code raised (as ``ValueError('<conflict>:<names>')``) when an addition names a
    field the context already has. ``None`` marks an optional input the episode does not have for this
    decision (the old ``if value is not None: context[name] = value``).
    """
    if not isinstance(context, Mapping) or not isinstance(additions, Mapping):
        raise TypeError('extend_context_requires_mappings')
    if type(conflict) is not str or not conflict:
        raise ValueError('extend_context_conflict_code_required')
    present = {name: value for name, value in additions.items() if value is not None}
    clash = sorted(set(present).intersection(context))
    if clash:
        raise ValueError(conflict + ':' + ','.join(clash))
    return {**context, **present}


def present_context(state, instructions, presentations, *, lookup_results, text_field):
    """Present one decision state through the first presentation that applies to it.

    ``presentations`` is an ordered sequence of ``(applies, render, instructions_for)``: ``applies(state)``
    says whether this presentation is for the state, ``render(state, instructions, lookup_results=...)``
    returns its text and ``instructions_for(instructions)`` the instructions sent with it. Returns
    ``(instructions, context)`` with the rendered text as ``{text_field: text}``. A state no presentation
    applies to raises ``LookupError``: an episode that sends some states as structured JSON lists that as its
    own last presentation.
    """
    if type(text_field) is not str or not text_field:
        raise ValueError('present_context_text_field_required')
    for item in presentations:
        applies, render, instructions_for = item
        if applies(state):
            text = render(state, instructions, lookup_results=list(lookup_results))
            if type(text) is not str or not text.strip():
                raise ValueError('presentation_rendered_no_text')
            sent = instructions_for(instructions)
            if type(sent) is not str or not sent.strip():
                raise ValueError('presentation_returned_no_instructions')
            return sent, {text_field: text}
    raise LookupError('no_presentation_applies_to_decision_state')


__all__ = ['extend_context', 'present_context']
