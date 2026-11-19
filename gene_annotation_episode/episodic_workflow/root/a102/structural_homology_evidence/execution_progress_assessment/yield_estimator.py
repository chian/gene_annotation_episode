"""The A102 monitor's continuation (carried from ``yield_estimator.py`` and ``configuration.py``).

The old private binding ``monitor_information_accumulation_v1`` forecast the next action's information credit and
stopped when the predicted upper gain was at or below the cutoff: the accumulation controller (README 7b,
``_monitor_information_yield``). The old cutoff is the controller's ``cost`` and ``uncertainty_alpha`` is its
parameter, both from this episode's own ``settings``. Nothing here reads the assignment.
"""
from yield_control import AccumulationYieldController

EPOCH = 'monitor'


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController(EPOCH, initial_credit, settings['cost'], settings['parameters'])
