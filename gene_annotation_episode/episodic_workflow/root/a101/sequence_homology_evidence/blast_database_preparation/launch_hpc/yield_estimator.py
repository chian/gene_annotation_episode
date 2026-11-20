"""Continuation: the commission is finite. The credit reaches ``handoff_unit`` exactly when the handoff exists, so the
controller is the completion controller with that target: the Episode ends at the handoff. Before that it ends when
further launch attempts stop earning (a refused launch). ``settings`` is this episode's entry of the run's
``continuation``: ``cost`` (below the target) and ``parameters``. The target comes from the parent input."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('launch_hpc', initial_credit, settings['cost'], parent_input['handoff_unit'],
                                     settings['parameters'])
