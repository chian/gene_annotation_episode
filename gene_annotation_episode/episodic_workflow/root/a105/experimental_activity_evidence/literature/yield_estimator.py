"""Continuation: the one task, ``verified_source_leads``, accumulates (old ``YieldController``): one credit unit per
verified source, without limit. Its controller is ``AccumulationYieldController`` with ``ADAPTIVE_CONTROL`` and
``items=None`` (no input list), nano-graphrag's estimator controller, and it has no cost: after W = 8 units attempted
and m = 4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected next
marginal (hypervolume) credit is at or below the adaptive gamma, max(one-result resolution, 0.1 x the median of the
recent productive credits); it stops after 4 flat units in a row (with ``items=None`` there is no item list to run
out)."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('literature', initial_credit, ADAPTIVE_CONTROL, items=None)
