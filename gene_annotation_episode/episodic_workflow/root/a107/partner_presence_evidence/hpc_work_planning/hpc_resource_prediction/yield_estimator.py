"""Continuation, carried from the old ``yield_estimator.py`` (``HPCEpisodeYield.yield_controller``; README 7b).

The old binding required the commission's ``yield_bindings['hpc_prediction'] = {cutoff, parameters}`` (and
``require_commission_yield``) and built a ``YieldController`` over an ``HPCContinuationEstimator``. The model credit
accumulates without a maximum or a commissioned target, so the controller is the accumulation controller. The old
cutoff is its ``cost``; both values are this episode's entry of the run's ``continuation`` collaborator
(``settings['cost']``, ``settings['parameters']``): the commission is a Store record read by a tool, so
``read_from_parent`` cannot give its yield binding. An entry without them raises the old error. Cost zero never
stops an accumulating controller: the run's settings must give a cost above zero.

Not carried (README 3d, 7b): ``continuation_for_action`` (the exact-zero continuation packet written when no new
measured improvement was available) and ``practical_estimator`` (``HPCContinuationEstimator``); nothing but this
controller stops the Episode."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    if 'cost' not in settings or 'parameters' not in settings:
        raise ValueError('hpc_commission_yield_binding_required:hpc_prediction')
    return AccumulationYieldController('hpc_resource_prediction', initial_credit, settings['cost'],
                                       settings['parameters'])
