"""Private A106 source-evidence parent prompt binding."""
from __future__ import annotations

from collections.abc import Mapping

from gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_prompt import _steering, _task
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_prompt import REFERENCE_PARENT_TASK


VERSION = 'reference_evidence_parent_v1'


def _descriptor(state):
    marker = state.get('literature_experimental_work') if isinstance(state, Mapping) else None
    descriptor = state.get('reference_evidence_parent') if isinstance(state, Mapping) else None
    if (not isinstance(marker, Mapping)
            or marker.get('version') != 'literature_experimental_task_v1'
            or marker.get('aspect') != 'reference_evidence_parent'
            or marker.get('evidence_axis') != 'A106'
            or not isinstance(descriptor, Mapping)
            or descriptor.get('version') != VERSION):
        raise ValueError('reference_evidence_parent_context_required')
    references = descriptor.get('source_refs')
    if (not isinstance(references, (list, tuple))
            or any(not isinstance(ref, str) or not ref for ref in references)
            or len(set(references)) != len(references)):
        raise ValueError('reference_evidence_parent_source_assignment_required')
    return descriptor


def render_reference_evidence_parent_prompt(state, instructions, *, lookup_results=()):
    """Render the A106 parent's own task, state, outcomes, and admitted returns."""
    _descriptor(state)
    return _task(state, instructions) + '\n\n' + _steering(state, lookup_results)


__all__ = ['VERSION', 'REFERENCE_PARENT_TASK', 'render_reference_evidence_parent_prompt']
