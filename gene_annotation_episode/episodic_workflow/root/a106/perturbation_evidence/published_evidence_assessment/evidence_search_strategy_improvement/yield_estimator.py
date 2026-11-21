"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates: one credit unit per verified source, without limit. Its controller is
``AccumulationYieldController`` (nano-graphrag's ``EstimatorController``) with ``ADAPTIVE_CONTROL`` and
``items=None``; it takes no cost. After W = 8 units attempted and m = 4 observed it fits nano-graphrag's yield model;
a unit is flat when the upper bound of the expected next marginal (hypervolume) credit is at or below gamma, the
adaptive gamma = max(one-result resolution, 0.1 x median of recent productive credits); it stops after 4 flat units
in a row. With ``items=None`` the input list does not stop it.

Every other task is a finite commission (old ``_FiniteLiteratureYieldController`` / ``CompletionYieldController``): the target is the old ``maximum_credit``, the task's
``credit_unit`` (the old ``maximum_credit``: one answer to the commission), read from the parent input. The cost is the old
task cutoff, now the episode's setting; the parameters are its settings. The old ``None`` (no private yield
binding) is not carried: the controller is always built from the task."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('evidence_search_strategy_improvement', initial_credit, ADAPTIVE_CONTROL,
                                           items=None)
    return CompletionYieldController('evidence_search_strategy_improvement', initial_credit, settings['cost'],
                                     task['credit_unit'],
                                     settings['parameters'])
