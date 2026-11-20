"""Continuation: the commission is finite. The credit reaches ``prepared_unit`` exactly when a usable prepared record
is established, so the controller is the completion controller with that target: the Episode ends when the product is
usable. Before that it ends when further actions stop earning (a failed product, a job that does not end soon).
``settings`` is this episode's entry of the run's ``continuation``: ``cost`` (below the target) and ``parameters``.
The target comes from the parent input."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('results', initial_credit, settings['cost'], parent_input['prepared_unit'],
                                     settings['parameters'])
