"""Continuation: the old episode had no continuation of its own (``continuation_task`` and ``yield_controller`` of
the old ``yield_estimator.py`` both returned None: the old runner's default controller applied). Its credit is
finding progress that accumulates and is never bounded, so the controller is accumulation (README 7b, the
``numerical.YieldController`` row): nano-graphrag's function and stop rule (``ADAPTIVE_CONTROL``); it takes no cost
and no settings, and the episode has no list of items. Nothing in the parent input is a target or a maximum."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('source_relevance_assessment', initial_credit, ADAPTIVE_CONTROL, items=None)
