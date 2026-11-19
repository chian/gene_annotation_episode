"""The commission is finite: one credit per plan step."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('library_probe', initial_credit, settings['cost'],
                                     float(len(parent_input['plan'])), settings['parameters'])
