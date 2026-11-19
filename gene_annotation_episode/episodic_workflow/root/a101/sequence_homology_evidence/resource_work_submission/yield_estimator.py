"""Continuation, carried from the old ``yield_estimator.py`` (``OriginalContinuation``).

The old file selected nothing itself: it handed the episode path and the initial credit to the old runner's
``controller_factory`` ("caller settings unchanged"; the credit kind ``operational`` meant no task key and no credit
definition). The choice is made here (README 7b): the credit counts the usable execution handoffs the Episode holds
(``credit.py``), and the commission fixes no amount to reach (``completion_target`` is the credit of one handoff, not
a total), so the controller is the accumulation controller. Its cost is the old cutoff and its parameters are the
yield parameters; both come from this episode's own entry of the ``continuation`` settings (``cost`` above zero, or
the controller never stops). When no resource is usable the units earn nothing and the forecast falls to the cost: the
controller ends the Episode (nothing else does). The raw assignment is not read here."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('resource_work_submission', initial_credit, settings['cost'],
                                       settings['parameters'])
