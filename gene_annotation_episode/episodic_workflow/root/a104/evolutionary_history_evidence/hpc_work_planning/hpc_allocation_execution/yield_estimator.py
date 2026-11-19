"""Continuation, carried from the old ``yield_estimator.py`` (``HPCEpisodeYield.yield_controller``) and
``configuration.py``: the old controller was ``YieldController(epoch, initial_credit, cutoff, YieldParameters(...),
estimate_with_context=HPCContinuationEstimator)`` with ``cutoff`` and ``parameters`` from the commission's
``yield_bindings['hpc_execution']``, and a commission without them raised ``hpc_commission_yield_binding_required``.
README 7b: the credit accumulates, so the accumulation controller; the old episode-local estimator
(``HPCContinuationEstimator``, ``continuation_for_action``, ``practical_estimator``) is deleted and nothing replaces it.
``settings`` is this episode's entry of the run's ``continuation`` collaborator,
``{'cost': <old cutoff, > 0>, 'parameters': {...}}``. Nothing else ends this Episode."""
import math

from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    if 'cost' not in settings or 'parameters' not in settings:
        raise ValueError('hpc_commission_yield_binding_required:hpc_execution')
    cost, parameters = settings['cost'], settings['parameters']
    if (isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost <= 0
            or not isinstance(parameters, dict)):
        raise ValueError('explicit_hpc_commission_yield_binding_required:hpc_execution')
    return AccumulationYieldController('hpc_allocation_execution', initial_credit, cost, parameters)
