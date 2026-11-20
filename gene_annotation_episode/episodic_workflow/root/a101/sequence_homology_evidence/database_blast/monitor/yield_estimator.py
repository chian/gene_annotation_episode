"""Continuation: a visit is finite. The visit is complete with the first check that shows a new fact, so the controller
is the completion controller with one information unit as its target; before that it ends when further checks stop being
expected to earn. The cost of one unit and the uncertainty parameter are this episode's settings (``cost``,
``parameters``); the unit comes from the parent input."""
import math

from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    cost, parameters = settings['cost'], settings['parameters']
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        raise ValueError('monitor_information_yield_values_invalid')
    return CompletionYieldController('database_blast_monitor', initial_credit, cost,
                                     parent_input['information_unit'], parameters)
