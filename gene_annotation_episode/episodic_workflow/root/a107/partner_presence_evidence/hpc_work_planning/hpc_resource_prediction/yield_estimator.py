"""Continuation, carried from the old ``yield_estimator.py`` (``HPCEpisodeYield.yield_controller``; README 7b).

The old binding required the commission's ``yield_bindings['hpc_prediction'] = {cutoff, parameters}`` (and
``require_commission_yield``) and built a ``YieldController`` over an ``HPCContinuationEstimator``. The model credit
accumulates without a maximum or a commissioned target, so the controller is the accumulation controller
(``AccumulationYieldController``, the port of nano-graphrag's ``EstimatorController``) with ``ADAPTIVE_CONTROL`` (the
model-selected tool call grain) and ``items=None`` (the episode has no list of items). It takes no cost and no
settings. After W=8 units attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the
upper bound of the expected next marginal (hypervolume) credit is at or below the adaptive gamma (the larger of the
one-result resolution and 0.1 times the median of the recent productive credits), and the controller stops the
Episode after 4 flat units in a row. With ``items=None`` no item count stops it.

Not carried (README 3d, 7b): ``continuation_for_action`` (the exact-zero continuation packet written when no new
measured improvement was available) and ``practical_estimator`` (``HPCContinuationEstimator``); nothing but this
controller stops the Episode."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('hpc_resource_prediction', initial_credit, ADAPTIVE_CONTROL, items=None)
