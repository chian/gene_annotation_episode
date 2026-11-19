"""The A110 head's own decision instructions and credit on the generic runner (episode_runtime).

The head runs the A110 unit source (``unit_source.UnitSource``) with its own A110
tool registry, the tools its commissioner selected (``tools``, C6) and these
instructions: the A110 axis guidance, the action protocol and the reasoning
commit requirement. Its credit is the A110 finding credit
(``unit_source.finding_credit``): one unit per distinct retained finding among
the assessments the head knows; unbounded.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import (
    REASONING_COMMIT_REQUIREMENT)
from .axis_task_context import scientific_guidance
from .unit_source import PROTOCOL, finding_credit


def instructions():
    """The head's decision instructions: the A110 axis guidance, the action protocol, the commit requirement."""
    return scientific_guidance() + PROTOCOL + '\n' + REASONING_COMMIT_REQUIREMENT


def head_credit(store, scope, known_assessment_refs):
    """The head's cumulative credit and retained finding count over the assessments it knows."""
    return finding_credit(store, scope, known_assessment_refs)


__all__ = ['head_credit', 'instructions']
