"""Continuation, carried from the old ``yield_estimator.py`` (``HPCEpisodeYield.yield_controller``) and
``configuration.py`` (``require_commission_yield``).

The old controller used ``commission['yield_bindings']['hpc_execution']`` (``{cutoff, parameters}``) with an
episode-local ``HPCContinuationEstimator``. README 7b: an episode cannot supply a forecast, so the nearest of the
three controllers is the completion controller; its cost is the old cutoff and its target is the credit of the
commission's obligations (the intent record: "target = the commission's obligation credits"). The pending
expectation, the collect and wait advice and the exact-zero forecast of ``continuation_for_action`` are not
carried: only the controller stops the Episode.

The commission comes from ``parent_input`` (``read_from_parent`` put it there); a commission without
``yield_bindings`` raises the old error."""
import math

from yield_control import CompletionYieldController

ROLE = 'hpc_execution'


def yield_controller(initial_credit, settings, parent_input):
    commission = parent_input['commission']
    if 'yield_bindings' not in commission:
        raise ValueError('hpc_commission_yield_binding_required:' + ROLE)
    chosen = commission['yield_bindings'][ROLE]
    target = math.fsum(row['credit'] for row in commission['obligations'].values())
    return CompletionYieldController('hpc_allocation_execution', initial_credit, chosen['cutoff'], target,
                                     chosen['parameters'])
