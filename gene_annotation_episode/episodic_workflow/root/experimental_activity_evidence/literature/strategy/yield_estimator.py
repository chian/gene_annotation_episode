"""Continuation: the one task, ``verified_source_leads``, accumulates (old ``YieldController``): one credit unit per
verified source, without limit. Its ``AccumulationYieldController`` (nano-graphrag's EstimatorController port,
``ADAPTIVE_CONTROL``, ``items=None``) has no cost: after W = 8 units attempted and m = 4 observed it fits
nano-graphrag's yield model; a unit is flat when the upper bound of the expected next marginal (hypervolume) credit is
at or below gamma, the adaptive gamma = max(one-result resolution, 0.1 x median of recent productive credits); it stops
after 4 flat units in a row. With ``items=None`` no item count stops it."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('strategy', initial_credit, ADAPTIVE_CONTROL, items=None)
