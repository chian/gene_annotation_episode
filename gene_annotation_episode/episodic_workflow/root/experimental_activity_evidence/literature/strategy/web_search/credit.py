"""Credit (owner, 2026-11-21): the strongest evidence at the closest relationship for the proposed annotation on the latest
sheet state this episode holds (the states its page child returned), minus the same on the sheet state it was given
(``literature_strongest_evidence``; 0 when it was given none). Counted as soon as a graded sheet is held; nothing the model
writes turns it on or off. A repeat, a weaker result or a more distant protein adds nothing, and it never falls. A child's
returned credit is information in the summary and is never added. Never bounded, clamped or rescaled."""
from method_loop import UNBOUNDED
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_strongest_evidence import (
    evidence_gain)


def credit(summary, records):
    value = evidence_gain(records, summary['sheet_state_refs'], summary['given_sheet_state_refs'],
                          summary['proposed_annotation_ref'])
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is taken as the next unit. A call the episode does not offer
    earns 0. The page child can return a result stronger or closer than the best held (it can acquire and judge new
    sources), by an amount nothing held now bounds: ``UNBOUNDED``. The provider search, Jev's measurement and the pick of a
    hit change no sheet: 0."""
    from .task import offered_actions
    if action_type not in offered_actions(summary, ctx):
        return 0.0
    if action_type == 'page':
        return UNBOUNDED
    return 0.0
