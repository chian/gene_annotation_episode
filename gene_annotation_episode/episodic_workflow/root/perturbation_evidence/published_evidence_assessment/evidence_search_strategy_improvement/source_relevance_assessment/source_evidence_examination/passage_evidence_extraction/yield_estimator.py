"""Continuation: ``verified_source_leads`` accumulates (old ``AccumulationYieldController``): one credit unit per verified
source, at no cost. Its controller is ``AccumulationYieldController`` with ``FIXED_CONTROL`` (nano-graphrag's
``EstimatorController`` port): after W = 8 units attempted and m = 4 observed it fits nano-graphrag's yield model; a unit
is flat when the upper bound of the expected next marginal (hypervolume) credit is at or below gamma 0.06; it stops after 4
flat units in a row. The owner's one more stopping condition: when no item remains on the leaf's input list, stop. The list
is the commissioned chunks (``read_from_parent``'s ``spans``) and each extraction consumes one, so ``items`` is the number
of chunks to do."""
from yield_control import AccumulationYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('passage_evidence_extraction', initial_credit, FIXED_CONTROL,
                                       items=len(parent_input['spans']))
