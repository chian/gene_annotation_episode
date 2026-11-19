"""Continuation: an accumulation controller (README 7b: the old ``HPCContinuationEstimator`` and its continuation
packet, ``continuation_for_action`` and ``practical_estimator``, are deleted; the credit is the ledger's, which
accumulates with the accepted accomplishment, the model improvement and the validated forecasts, has no declared maximum
and is not bounded by the commission's obligations, since the model and validation components are signed and extra).

The cost and the estimator parameters are the old commission's ``yield_bindings['hpc']`` (``cutoff`` and
``parameters``; ``require_commission_yield``), now this episode's settings (``cost`` is the old cutoff): the commission
is a Store record read by a tool, so ``read_from_parent`` cannot give its yield binding. A missing setting raises
(the old ``hpc_commission_yield_binding_required``). It reads nothing of ``parent_input``. The cost must be above zero
or the controller never stops. Every other stop test of the old episode is deleted: the scale clamp
``min(1.0, ...)`` of the old continuation valuation, the active credit ceiling and the pending-collect packet go with
the estimator."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    if 'cost' not in settings or 'parameters' not in settings:
        raise ValueError('hpc_commission_yield_binding_required:hpc')
    return AccumulationYieldController('hpc_work_planning', initial_credit, settings['cost'],
                                       settings['parameters'])
