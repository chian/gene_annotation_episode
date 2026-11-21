"""Continuation: the commission is finite (a handoff and its receiving check), so the controller is the completion
controller. The target is the sum of the two credit units of the commission, from the parent input; the cost and
the estimator parameters are this episode's settings. The controller stops the Episode at the target, or earlier
when further actions are not forecast to earn more than their cost."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('local_resource_work_execution', initial_credit, settings['cost'],
                                     parent_input['completion_target'], settings['parameters'])
