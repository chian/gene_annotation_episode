"""Continuation: the old episode had no continuation of its own (the old runner's default controller applied).
Its credit is information that accumulates (finding progress, never bounded), so the controller is accumulation:
nano-graphrag's function and stop rule at the leaf grain (a model-selected read or population call on the source);
it takes no cost and the episode has no list of items to exhaust."""
from yield_control import AccumulationYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('passage_evidence_extraction', initial_credit, FIXED_CONTROL, items=None)
