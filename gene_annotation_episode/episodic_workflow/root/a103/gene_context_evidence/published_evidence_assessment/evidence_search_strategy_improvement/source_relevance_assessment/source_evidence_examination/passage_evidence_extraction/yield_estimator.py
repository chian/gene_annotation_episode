"""The credit is a bounded quality: the A103 context credit has a declared maximum (its native score maximum)."""
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)


def yield_controller(initial_credit, settings, parent_input):
    return BoundedQualityYieldController('passage_evidence_extraction', initial_credit, settings['cost'],
                                         A103ContextCredit.native_score_maximum, settings['parameters'])
