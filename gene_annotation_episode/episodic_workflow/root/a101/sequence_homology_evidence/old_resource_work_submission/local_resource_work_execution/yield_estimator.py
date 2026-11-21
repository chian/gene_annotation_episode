"""Continuation of the local resource episode.

The old file selected nothing itself: it handed the episode path and the commission's initial credit to the
runner's controller factory, with no task key and no credit definition because the credit kind was
``operational``. The credit here is the resource's own operational credit, which accumulates; the commission
fixes no target and no maximum (the old assignment carries none), so the controller is the accumulation one.
It takes no cost. With ``ADAPTIVE_CONTROL`` (one resource tool unit is not a single chunk read), after at least
W=8 units attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the
expected next marginal (hypervolume) credit is at or below gamma, the adaptive gamma = max(one-result resolution,
0.1 x median of recent productive credits); it stops after 4 flat units in a row. The episode works through no known
list, so ``items=None``: there is no item count to run out."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('local_resource_work_execution', initial_credit, ADAPTIVE_CONTROL, items=None)
