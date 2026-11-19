"""The commission is finite: one fact, extracted and confirmed."""
from yield_control import CompletionYieldController

TARGET = 2.0


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('fact_collection', initial_credit, settings['cost'], TARGET,
                                     settings['parameters'])
