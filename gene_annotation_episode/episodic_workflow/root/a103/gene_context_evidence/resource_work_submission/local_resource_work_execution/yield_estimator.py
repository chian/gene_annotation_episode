"""Continuation: the work has a definite end, one usable execution handoff for the assigned job, so the
controller is the completion controller (README 7b). The old file selected nothing itself ("original continuation
factory selection; caller settings unchanged") and handed the initial credit to the caller's controller factory.

The target is the commission's ``completion_target`` (a new field of the assignment, read by
``read_from_parent``); the cost and the estimator parameters are this episode's settings."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('local_resource_work_execution', initial_credit, settings['cost'],
                                     parent_input['completion_target'], settings['parameters'])
