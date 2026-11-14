"""A102's private source-parent prompt presentation."""
from __future__ import annotations

from .literature_experimental_prompt import _steering, _task


def render_reference_evidence_parent_prompt(state, instructions, *, lookup_results=()):
    descriptor = state.get('reference_evidence_parent')
    if not isinstance(descriptor, dict) or descriptor.get('version') != 'reference_evidence_parent_v1':
        raise ValueError('reference_evidence_parent_context_required')
    return _task(state, instructions) + '\n\n' + _steering(state, lookup_results)


__all__ = ['render_reference_evidence_parent_prompt']
