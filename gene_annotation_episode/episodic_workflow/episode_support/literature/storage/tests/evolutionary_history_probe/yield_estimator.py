"""The commission is finite: its credit reaches the number of library calls of the plan."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('evolutionary_history_probe', initial_credit, settings['cost'], float(len(parent_input['plan'])),
                                     settings['parameters'])
