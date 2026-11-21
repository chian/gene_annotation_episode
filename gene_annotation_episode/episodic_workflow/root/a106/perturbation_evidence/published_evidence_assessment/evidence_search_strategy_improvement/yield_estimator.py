"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates: one credit unit per verified source, without limit. Its controller is
``AccumulationYieldController`` (nano-graphrag's ``EstimatorController``) with ``ADAPTIVE_CONTROL`` and
``items=None``; it takes no cost. After W = 8 units attempted and m = 4 observed it fits nano-graphrag's yield model;
a unit is flat when the upper bound of the expected next marginal (hypervolume) credit is at or below gamma, the
adaptive gamma = max(one-result resolution, 0.1 x median of recent productive credits); it stops after 4 flat units
in a row. With ``items=None`` the input list does not stop it. It is the only task this episode takes, so there is no
other controller."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('evidence_search_strategy_improvement', initial_credit, ADAPTIVE_CONTROL,
                                       items=None)
