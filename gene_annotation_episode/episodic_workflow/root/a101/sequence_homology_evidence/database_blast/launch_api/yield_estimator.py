"""Continuation: the commission is finite. The credit reaches the completion target exactly when the handoff is
established, so the controller is the completion controller with that target: the episode ends at the handoff, and
before that when further submissions stop being expected to earn. The cost of one unit and the uncertainty parameter
are this episode's settings (``cost``, ``parameters``); the target comes from the parent input."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('database_blast_launch_api', initial_credit, settings['cost'],
                                     parent_input['completion_target'], settings['parameters'])
