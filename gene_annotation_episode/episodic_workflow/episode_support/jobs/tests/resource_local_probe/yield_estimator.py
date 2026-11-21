"""A finite target: one credit per plan step, so the controller stops the Episode at the plan's last step."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('resource_local_probe', initial_credit, settings['cost'],
                                     float(len(parent_input['plan'])), settings['parameters'])
