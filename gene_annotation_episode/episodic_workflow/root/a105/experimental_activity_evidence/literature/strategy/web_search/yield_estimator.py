"""Continuation: the one task, ``verified_source_leads``, accumulates (old ``YieldController``): one credit unit per
verified source, controlled by ``AccumulationYieldController`` with ``ADAPTIVE_CONTROL`` and ``items=None``
(nano-graphrag's EstimatorController), which has no cost and reads no settings. After W = 8 units attempted and m = 4
observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected next marginal
(hypervolume) credit is at or below the adaptive gamma (the larger of the one-result resolution and 0.1 x the median of
the recent productive credits); it stops after 4 flat units in a row. With ``items=None`` it has no item stop: the
search results running out do not end it."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('web_search', initial_credit, ADAPTIVE_CONTROL, items=None)
