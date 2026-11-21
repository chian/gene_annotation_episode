"""Continuation. The old ``yield_estimator.py`` named none (``continuation_task`` and ``yield_controller`` both
returned None: the old runner's generic controller governed it). The credit is scientific information progress: one
``finding_unit`` for each distinct retained typed finding, without a maximum and without a commissioned target. That
is the accumulation controller (README 7b), which takes no cost and no settings: it is nano-graphrag's estimator and
stop rule. The unit is a model-selected search, fetch, read or child commission, a page/source grain, so the control
is ``ADAPTIVE_CONTROL``; the episode works through no known list, so ``items`` is None. ``parent_input`` is not needed
to build it (the unit of credit is in ``credit.py``). The old ``waiting.supports_wait = False`` has no counterpart:
the system has no wait."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('source_relevance_assessment', initial_credit, ADAPTIVE_CONTROL, items=None)
