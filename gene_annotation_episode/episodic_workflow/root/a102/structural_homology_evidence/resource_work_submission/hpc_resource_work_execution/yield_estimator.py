"""Continuation, carried from the old episode (``ResourceCredit.credit_kind`` was ``operational``: no task key, no
credit definition, no target; the old runner's controller factory took the settings unchanged).

README 7b: the credit counts the distinct usable execution handoffs found (``credit.py``), which has no commissioned
amount and no declared maximum, so the controller is the accumulation controller. Its cost is the old cutoff and
comes from the episode's own entry of the ``continuation`` settings (``cost`` above zero, ``parameters`` the yield
parameters). When the resource is unavailable or unknown no handoff is found, the units earn nothing and the
forecast falls to the cost: the controller ends the Episode (nothing else does). The raw assignment is not read."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('hpc_resource_work_execution', initial_credit, settings['cost'],
                                       settings['parameters'])
