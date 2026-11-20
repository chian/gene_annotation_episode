"""Continuation: the commission is finite. The credit reaches ``handoff_unit + prepared_unit`` exactly when the
handoff exists and a usable prepared-data record is established, so the controller is the completion controller with
that target. Before that it ends when further commissions stop earning (a refused launch, a product that is not
usable, a job that does not end soon). ``settings`` is this episode's entry of the run's ``continuation``: ``cost``
(below the target) and ``parameters``. The target comes from the parent input."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('blast_database_preparation', initial_credit, settings['cost'],
                                     parent_input['handoff_unit'] + parent_input['prepared_unit'],
                                     settings['parameters'])
