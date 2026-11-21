"""Continuation: the completion controller (``CompletionYieldController``): continue until the credit reaches the commission's finite
target (the database, the matrix and a graded clustering for each allowed inflation); the cost is ``settings['cost']`` times the
smallest credit unit of the commission, ``settings['parameters']`` are the estimator's."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    cost = settings['cost'] * min(parent_input['units'].values())
    return CompletionYieldController('all_vs_all', initial_credit, cost, parent_input['target'], settings['parameters'])
