"""Continuation: the commission is finite (the requested result files), so the controller is the completion
controller. The target is the number of requested files, read from the parent input; the cost and the estimator
parameters are this episode's settings. The controller stops the Episode when every requested file is held, or
earlier when further checks and fetches are not forecast to earn more than their cost."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('resource_result_acquisition', initial_credit, settings['cost'],
                                     float(len(parent_input['requested_names'])), settings['parameters'])
