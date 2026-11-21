"""A finite target: one credit per pair, so the controller stops the Episode at the last pair."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('closeness_probe', initial_credit, settings['cost'],
                                     float(len(parent_input['plan'])), settings['parameters'])
