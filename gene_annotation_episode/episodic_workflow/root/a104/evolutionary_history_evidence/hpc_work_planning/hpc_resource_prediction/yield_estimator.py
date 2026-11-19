"""Continuation, carried from the old ``yield_estimator.py`` (``HPCEpisodeYield.yield_controller``; README 7b).

The old code opened the plain accumulating ``YieldController(epoch, initial_credit, cutoff, YieldParameters)`` with
the commission's ``yield_bindings['hpc_prediction']`` (``{cutoff, parameters}``) and an ``HPCContinuationEstimator``
bound to the cutoff. The credit is a signed measured gain (a mean log score difference) with no maximum and no
commissioned target, so the controller is ``AccumulationYieldController`` (the old commission check,
``validate_commission``, already opened an accumulating controller from each binding); the binding is read from the
parent input (``read_from_parent``: the field ``yield_binding``, a new field), and the old cutoff is the
controller's cost (it must be above zero for the controller to stop the Episode).

Not carried: ``continuation_for_action`` (the zero-continuation packet recorded when the commission had no
validation ids, every available case was trained, candidates were compared and the queue observation was fresh) and
``practical_estimator`` (the ``HPCContinuationEstimator`` that verified the packet against the ledger): an episode
cannot supply a forecast, and a completion packet is not a controller input. When units stop earning the forecast
falls to the cost and the controller stops the Episode; nothing else does."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    chosen = parent_input['yield_binding']
    return AccumulationYieldController('hpc_resource_prediction', initial_credit, chosen['cutoff'],
                                       chosen['parameters'])
