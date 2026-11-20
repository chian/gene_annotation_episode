"""Continuation: the commission is finite. The credit reaches the handoff unit exactly when the handoff exists, so the
controller is the completion controller with that unit as its target: the episode ends at handoff, and before that
when further launches stop being expected to earn (a refused launch repeated). The cost of one unit and the
uncertainty parameter are this episode's settings (``cost``, ``parameters``); the target comes from the parent input,
which ``read_from_parent`` made from the assignment."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('all_vs_all_launch_local', initial_credit, settings['cost'],
                                     parent_input['handoff_unit'], settings['parameters'])
