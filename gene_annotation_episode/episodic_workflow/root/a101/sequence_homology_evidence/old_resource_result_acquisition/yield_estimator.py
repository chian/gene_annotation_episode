"""Continuation of the results acquisition episode.

The old file selected nothing itself: it handed the episode path and the commission's initial credit to the
runner's controller factory, with no task key and no credit definition because the credit kind was
``operational``. The credit here is the resource's own operational credit, which accumulates; the old results
assignment (``version``, ``handoff``, ``requested_data_selector``) fixes no target and no maximum, so the controller
is the accumulation one (README 7b). Its cost and parameters are this episode's settings; at cost zero it never
stops."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('resource_result_acquisition', initial_credit, settings['cost'],
                                       settings['parameters'])
