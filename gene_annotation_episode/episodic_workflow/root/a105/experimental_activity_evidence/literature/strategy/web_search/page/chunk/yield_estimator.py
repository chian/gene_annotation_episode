"""Continuation: the commission is one extraction of one chunk, so it is finite. Its credit (the share of the
asked fields the extraction newly states) counts toward the target of all of them, and the estimator stops the
Episode when the forecast of the credit still to come is at or below its cost."""
from yield_control import CompletionYieldController

TARGET = 1.0


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('chunk', initial_credit, settings['cost'], TARGET,
                                     settings['parameters'])
