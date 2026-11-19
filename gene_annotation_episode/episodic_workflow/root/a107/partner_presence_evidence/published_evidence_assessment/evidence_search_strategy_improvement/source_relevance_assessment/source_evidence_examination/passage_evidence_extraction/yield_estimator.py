"""Continuation: the old episode had no continuation of its own (the old runner's default controller applied).
Its credit is information that accumulates (finding progress, never bounded), so the controller is accumulation;
its cost and parameters are the episode's own settings."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('passage_evidence_extraction', initial_credit, settings['cost'],
                                       settings['parameters'])
