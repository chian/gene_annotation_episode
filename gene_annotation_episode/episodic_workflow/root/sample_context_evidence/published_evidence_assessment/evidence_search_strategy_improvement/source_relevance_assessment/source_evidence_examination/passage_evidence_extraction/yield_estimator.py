"""Continuation from the commissioned task: ``verified_source_leads`` accumulates (``AccumulationYieldController`` with
``FIXED_CONTROL``, nano-graphrag's EstimatorController): one credit unit per verified source, and no cost. After 8 units
attempted and 4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected next
marginal (hypervolume) credit is at or below gamma (fixed, 0.06); it stops after 4 flat units in a row. The input list
bounds it: the one commissioned chunk is consumed by its extraction, so the episode stops when no item remains."""
from yield_control import AccumulationYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('passage_evidence_extraction', initial_credit, FIXED_CONTROL,
                                       items=len(parent_input['spans']))
