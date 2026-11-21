"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``LiteratureYield.yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``YieldController``): one credit unit per verified source, without
limit. Its ``AccumulationYieldController`` (nano-graphrag's EstimatorController port, ``ADAPTIVE_CONTROL``,
``items=None``) has no cost: after W = 8 units attempted and m = 4 observed it fits nano-graphrag's yield model; a
unit is flat when the upper bound of the expected next marginal (hypervolume) credit is at or below gamma, the
adaptive gamma = max(one-result resolution, 0.1 x median of recent productive credits); it stops after 4 flat units
in a row. With ``items=None`` no item count stops it. Every other task is a finite commission (old ``_FiniteLiteratureYieldController`` with
``_RemainingCommissionedCredit``): the target is the old ``maximum_credit``, ``credit_unit`` times the number of
experiments for ``a105_experiments`` and ``credit_unit`` otherwise, read from the parent input. The cost is the
old task cutoff and the parameters the old ``uncertainty_alpha``, now the episode's settings. The old
``validate_yield_bindings`` checks of the cutoff and alpha are the controllers' own."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('strategy', initial_credit, ADAPTIVE_CONTROL, items=None)
    target = task['credit_unit'] * (len(task['experiments']) if task['kind'] == 'a105_experiments' else 1)
    return CompletionYieldController('strategy', initial_credit, settings['cost'], target,
                                     settings['parameters'])
