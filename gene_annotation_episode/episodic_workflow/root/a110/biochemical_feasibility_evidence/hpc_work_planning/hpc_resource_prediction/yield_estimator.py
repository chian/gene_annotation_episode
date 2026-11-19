"""Continuation, carried from the old ``yield_estimator.py`` (``HPCEpisodeYield.yield_controller``).

README 7b: ``HPCContinuationEstimator`` and ``continuation_for_action`` have no controller of their own. The
credit here is a signed measured model improvement that accumulates, so the controller is the accumulation
controller. The old ``chosen = commission['yield_bindings'][role]`` (``cutoff`` and ``parameters``) is this episode's
entry of the run's ``continuation`` collaborator: ``{'cost': <old cutoff, finite and above zero>, 'parameters':
{...}}``; the commission is not read here (``read_from_parent`` produced no commission). An entry without them
raises the old error. ``continuation_for_action`` (the zero-expected-continuation packet written when there were no
validation ids, all training was used and every candidate had a fresh comparison) and ``practical_estimator`` are
deleted: nothing but this controller ends the Episode."""
import math

from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    if 'cost' not in settings or 'parameters' not in settings:
        raise ValueError('hpc_commission_yield_binding_required:hpc_prediction')
    cost, parameters = settings['cost'], settings['parameters']
    if (isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost <= 0
            or not isinstance(parameters, dict)):
        raise ValueError('explicit_hpc_commission_yield_binding_required:hpc_prediction')
    return AccumulationYieldController('hpc_resource_prediction', initial_credit, cost, parameters)
