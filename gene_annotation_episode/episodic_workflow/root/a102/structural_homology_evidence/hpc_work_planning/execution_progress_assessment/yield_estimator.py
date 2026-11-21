"""Continuation: the monitor's information yield is the accumulation controller (README 7b), a port of nano-graphrag's
EstimatorController, configured by this Episode with nano-graphrag's fixed control (``FIXED_CONTROL``). It takes no
cost and no settings; the run's ``continuation`` entry carries no setting for it. After at least W=8 units
attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected
next marginal (hypervolume) credit is at or below gamma, fixed at 0.06; it stops after 4 flat units in a row. The
monitor's input list size is not known at its start, so ``items`` is ``None`` and no item count ends it. Nothing
else ends this Episode."""
from yield_control import AccumulationYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('monitor', initial_credit, FIXED_CONTROL, items=None)
