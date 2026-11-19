"""The commission is finite: its credit counts toward the number of commissioned scenarios."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('library_probe', initial_credit, settings['cost'],
                                     float(len(parent_input['plan'])), settings['parameters'])
