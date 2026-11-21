"""Continuation of the local resource episode.

The old file selected nothing itself: it handed the episode path and the commission's initial credit to the
runner's controller factory, with no task key and no credit definition because the credit kind was
``operational``. The credit here is the resource's own operational credit, which accumulates; the commission
fixes no target and no maximum (the old assignment carries none), so the controller is the accumulation one.
It takes no cost: it runs nano-graphrag's adaptive-gamma stop rule (one resource tool unit is not a single chunk
read) and the episode works through no known list, so it has no item count."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('local_resource_work_execution', initial_credit, ADAPTIVE_CONTROL, items=None)
