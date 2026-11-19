"""Continuation. The old ``yield_estimator.py`` named none (``yield_controller`` -> None: the old runner's generic
controller governed it). The credit is scientific information progress: one ``finding_unit`` for each distinct retained
typed finding, without a maximum and without a commissioned target. That is the accumulation controller (README 7b,
old ``numerical.YieldController``). The cost is the old cutoff, now the episode's setting; ``parameters`` are its
estimator settings. ``parent_input`` is not needed to build it (the unit of credit is in ``credit.py``)."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('passage_evidence_extraction', initial_credit, settings['cost'],
                                       settings['parameters'])
