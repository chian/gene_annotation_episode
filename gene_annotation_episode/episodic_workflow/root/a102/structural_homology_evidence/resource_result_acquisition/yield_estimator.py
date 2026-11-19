"""Continuation of the results acquisition episode.

The old episode had no ``yield_estimator.py`` and no controller hook: its goal said "Only the configured local
controller governs continuation", and the controller binding parameters were only shown to the model in the yield
table. The credit is the resource's own operational credit, which accumulates; the old results assignment
(``version``, ``handoff``, ``requested_data_selector``) fixes no target and no maximum, so the controller is the
accumulation one (README 7b). Its cost and parameters are this episode's settings; at cost zero it never stops."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('resource_result_acquisition', initial_credit, settings['cost'],
                                       settings['parameters'])
