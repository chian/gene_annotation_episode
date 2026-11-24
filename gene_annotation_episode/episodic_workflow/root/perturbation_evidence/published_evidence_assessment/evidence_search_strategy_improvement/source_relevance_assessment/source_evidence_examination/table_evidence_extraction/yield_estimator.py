"""Continuation: ``verified_source_leads`` accumulates (old ``AccumulationYieldController``): one credit unit per verified
source, at no cost. Its controller is ``AccumulationYieldController`` with ``ADAPTIVE_CONTROL`` (nano-graphrag's
EstimatorController): after W = 8 units attempted and m = 4 observed it fits nano-graphrag's yield model; a unit is flat when
the upper bound of the expected next marginal (hypervolume) credit is at or below gamma, the adaptive gamma = max(one-result
resolution, 0.1 x median of recent productive credits); it stops after 4 flat units in a row. The owner's one more stopping
condition: when no item remains on the leaf's input list, stop. The list is the one commissioned table region and its
extraction consumes it, so ``items`` is 1."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL

ITEMS = 1        # the input list: the one table region of the commission


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('table_evidence_extraction', initial_credit, ADAPTIVE_CONTROL, items=ITEMS)
