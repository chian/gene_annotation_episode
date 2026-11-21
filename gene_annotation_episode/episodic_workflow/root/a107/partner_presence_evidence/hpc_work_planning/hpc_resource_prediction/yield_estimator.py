"""Continuation, carried from the old ``yield_estimator.py`` (``HPCEpisodeYield.yield_controller``; README 7b).

The old binding required the commission's ``yield_bindings['hpc_prediction'] = {cutoff, parameters}`` (and
``require_commission_yield``) and built a ``YieldController`` over an ``HPCContinuationEstimator``. The model credit
accumulates without a maximum or a commissioned target, so the controller is the accumulation controller:
nano-graphrag's function and stop rule (``ADAPTIVE_CONTROL``, the model-selected tool call grain). It takes no cost
and no settings, and the episode has no list of items, so ``items`` is None.

Not carried (README 3d, 7b): ``continuation_for_action`` (the exact-zero continuation packet written when no new
measured improvement was available) and ``practical_estimator`` (``HPCContinuationEstimator``); nothing but this
controller stops the Episode."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('hpc_resource_prediction', initial_credit, ADAPTIVE_CONTROL, items=None)
