"""Proposed A101 source-reading presentation on its admitted private state.

Review draft only: no source claim, target applicability or grading is inferred.
"""
from ..receiver_prompt import _task
from ..sequence_homology_evidence_prompt import _section, _values, render_episode_steering


def render_literature_source_prompt(state, instructions, *, lookup_results=()):
    """Retain the supplied A101 task and its actual source-local context."""
    task = [_task(state, instructions)]
    for key, title in (
        ('literature_assignment', 'Parent assignment and selected source operands'),
        ('literature_source_custody', 'Representations available for selected sources'),
    ):
        if key in state:
            _section(task, title, _values(state[key]))
    steering = [render_episode_steering(state, lookup_results=lookup_results)]
    for key, title in (
        ('own_literature_outcomes', 'Recorded own source acquisition and reading outcomes'),
        ('literature_history_meaning', 'Meaning of retained source-reading history'),
    ):
        if key in state:
            _section(steering, title, _values(state[key]))
    return '\n'.join(task) + '\n\n' + '\n'.join(steering)
