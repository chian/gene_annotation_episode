"""Continuation of the results acquisition episode.

The old file selected nothing itself: it handed the episode path and the commission's initial credit to the
runner's controller factory, with no task key and no credit definition because the credit kind was
``operational``. The credit here is the resource's own operational credit, which accumulates; the old results
assignment (``version``, ``handoff``, ``requested_data_selector``) fixes no target and no maximum, so the controller
is the accumulation one (README 7b) with ``ADAPTIVE_CONTROL``. It takes no cost and no settings. After at least
W=8 units attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the
expected next marginal (hypervolume) credit is at or below gamma, the adaptive gamma = max(one-result resolution,
0.1 x median of recent productive credits); it stops after 4 flat units in a row. The episode works through no
known input list (``items=None``), so it never stops for want of items."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('resource_result_acquisition', initial_credit, ADAPTIVE_CONTROL, items=None)
