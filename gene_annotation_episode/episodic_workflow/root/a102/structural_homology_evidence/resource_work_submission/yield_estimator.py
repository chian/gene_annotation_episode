"""Continuation: the work has a definite end, a usable execution handoff for the assigned work, so the controller
is the completion controller. The target is the commission's ``completion_target`` (read by ``read_from_parent``);
the cost and the estimator parameters are this episode's settings."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('resource_work_submission', initial_credit, settings['cost'],
                                     parent_input['completion_target'], settings['parameters'])
