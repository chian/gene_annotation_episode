"""Continuation: the old episode had no continuation of its own (``continuation_task`` and ``yield_controller`` of
the old ``yield_estimator.py`` both returned None: the old runner's default controller applied). Its credit is
finding progress that accumulates and is never bounded, so the controller is accumulation (README 7b, the
``numerical.YieldController`` row); its cost and parameters are this episode's settings. Nothing in the parent input
is a target or a maximum."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('evidence_search_strategy_improvement', initial_credit, settings['cost'],
                                       settings['parameters'])
