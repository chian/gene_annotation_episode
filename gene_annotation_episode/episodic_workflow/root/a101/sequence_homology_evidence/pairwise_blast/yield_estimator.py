"""Continuation: the commission is finite. The credit reaches the information unit exactly when a grading is saved, so
the controller is the completion controller with that unit as its target: the episode ends when the correspondence is
established, and before that when further actions stop being expected to earn. The cost of an action and the
uncertainty parameter are this episode's settings (``cost``, ``parameters``); the target comes from the parent
input, which ``read_from_parent`` made from the assignment."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('pairwise_blast', initial_credit, settings['cost'],
                                     parent_input['information_unit'], settings['parameters'])
