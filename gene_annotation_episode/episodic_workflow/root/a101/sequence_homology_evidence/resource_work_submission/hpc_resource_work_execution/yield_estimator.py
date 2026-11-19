"""Continuation, carried from the old ``yield_estimator.py`` (``OriginalContinuation``).

The old file selected nothing itself: it handed the episode path and ``initial_credit`` to the old runner's
``controller_factory`` ("caller settings unchanged"; the credit kind ``operational`` meant no task key and no
credit definition). The owner's choice is recorded here (README 7b): the credit counts the distinct usable
execution handoffs found (``credit.py``), which has no commissioned amount, so the controller is the accumulation
controller. Its cost is the old cutoff and comes from the episode's own entry of the ``continuation`` settings
(``cost`` above zero, ``parameters`` the yield parameters). When the resource is unavailable or unknown no handoff
is found, the units earn nothing and the forecast falls to the cost: the controller ends the Episode (nothing
else does). The raw assignment is not read here."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('hpc_resource_work_execution', initial_credit, settings['cost'],
                                       settings['parameters'])
