"""Continuation. The old file chose nothing (both of its methods returned None: the old runner's default). The
credit is the A101 native correspondence, whose projector declares ``yield_method = 'bounded_quality'`` with
``native_score_maximum`` (README 7b: ``BoundedYieldController`` -> ``BoundedQualityYieldController``, maximum the
projector's declared maximum). The cost and parameters are this episode's settings. Nothing in the parent input is
a target or a maximum."""
from yield_control import BoundedQualityYieldController

from .credit import NATIVE_SCORE_MAXIMUM


def yield_controller(initial_credit, settings, parent_input):
    return BoundedQualityYieldController('evidence_search_strategy_improvement', initial_credit, settings['cost'],
                                         NATIVE_SCORE_MAXIMUM, settings['parameters'])
