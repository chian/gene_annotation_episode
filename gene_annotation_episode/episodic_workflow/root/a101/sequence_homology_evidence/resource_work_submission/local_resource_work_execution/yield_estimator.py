"""Continuation of the local resource episode.

The old file selected nothing itself: it handed the episode path and the commission's initial credit to the
runner's controller factory, with no task key and no credit definition because the credit kind was
``operational``. The credit here is the resource's own operational credit, which accumulates; the commission
fixes no target and no maximum (the old assignment carries none), so the controller is the accumulation one.
Its cost and parameters are this episode's settings; at cost zero it never stops."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('local_resource_work_execution', initial_credit, settings['cost'],
                                       settings['parameters'])
