"""Continuation. The old file chose nothing (``continuation_task`` and ``yield_controller`` both returned None: the
old runner's default). The credit is the A103 context credit, whose projector declares
``yield_method = 'bounded_quality'`` with ``native_score_maximum`` (README 7b: ``BoundedYieldController`` ->
``BoundedQualityYieldController``, maximum the projector's declared maximum). The cost and parameters are this
episode's settings. Nothing in the parent input is a target or a maximum."""
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)


def yield_controller(initial_credit, settings, parent_input):
    return BoundedQualityYieldController('source_evidence_examination', initial_credit, settings['cost'],
                                         A103ContextCredit.native_score_maximum, settings['parameters'])
