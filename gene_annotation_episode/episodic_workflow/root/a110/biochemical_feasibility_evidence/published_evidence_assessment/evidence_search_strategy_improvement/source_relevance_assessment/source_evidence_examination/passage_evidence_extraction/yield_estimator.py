"""Continuation. The old ``yield_estimator.py`` named none (``yield_controller`` -> None: the old runner's generic
controller governed it). The credit is scientific information progress: one ``finding_unit`` for each distinct retained
typed finding, without a maximum and without a commissioned target. That is the accumulation controller (README 7b):
it takes no cost and stops by nano-graphrag's rule with the adaptive control (one unit is one model-selected tool call
over a source's passages, not one item of a known list, so ``items`` is None). ``parent_input`` is not needed to build
it (the unit of credit is in ``credit.py``)."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('passage_evidence_extraction', initial_credit, ADAPTIVE_CONTROL, items=None)
