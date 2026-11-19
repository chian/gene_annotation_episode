"""Continuation: an accumulation controller (README 7b: the old ``HPCContinuationEstimator`` and its continuation
packet, ``continuation_for_action`` and ``practical_estimator``, are deleted; the credit is the owner ledger's, which
accumulates with the accepted accomplishment, the model improvement and the validated forecasts and has no declared
maximum or finite target of its own).

The cost and the estimator parameters are the old commission's ``yield_bindings['hpc_execution']`` (``cutoff`` and
``parameters``), now this episode's settings; a missing setting raises ``KeyError`` (the old
``hpc_commission_yield_binding_required``). It reads nothing of ``parent_input``. The cost must be above zero or the
controller never stops. Every other stop test of the old episode is deleted."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('hpc_allocation_execution', initial_credit, settings['cutoff'],
                                       settings['parameters'])
