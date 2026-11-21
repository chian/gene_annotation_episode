"""Continuation: the monitor's information yield is the accumulation controller (README 7b), configured by this
Episode with nano-graphrag's fixed control (``FIXED_CONTROL``: fixed gamma, rho 0, streak 4). The run's
``continuation`` entry carries no setting for it; the controller takes no cost and no settings. The monitor's
input list size is not known at its start, so ``items`` is ``None``. Nothing else ends this Episode."""
from yield_control import AccumulationYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('monitor', initial_credit, FIXED_CONTROL, items=None)
