"""The commission is finite: its credit counts toward one, the whole of the commissioned reading."""
from yield_control import CompletionYieldController

TARGET = 1.0


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('fact_extraction', initial_credit, settings['cost'], TARGET,
                                     settings['parameters'])
