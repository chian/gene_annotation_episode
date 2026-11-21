"""Continuation: the completion controller over the leaf's credit (half the share of the commission's windows read plus
half the share of the asked fields the held records newly state, ``credit.credit``), target 1.0; it stops the Episode when
the forecast of the credit still to come is at or below its cost. Each new window earns its share of the coverage, so the
Episode reads on while windows remain. Not the forecast controller: see chunk/yield_estimator.py (a refused first
extraction never ends the Episode)."""
from yield_control import CompletionYieldController

TARGET = 1.0


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('report', initial_credit, settings['cost'], TARGET, settings['parameters'])
