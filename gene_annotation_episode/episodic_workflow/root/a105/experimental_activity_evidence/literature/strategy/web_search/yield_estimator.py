"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``LiteratureYield.yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``YieldController``): one credit unit per verified source, controlled by
``AccumulationYieldController`` with ``ADAPTIVE_CONTROL`` and ``items=None`` (nano-graphrag's EstimatorController),
which has no cost and reads no settings. After W = 8 units attempted and m = 4 observed it fits nano-graphrag's yield
model; a unit is flat when the upper bound of the expected next marginal (hypervolume) credit is at or below the
adaptive gamma (the larger of the one-result resolution and 0.1 x the median of the recent productive credits); it
stops after 4 flat units in a row. With ``items=None`` it has no item stop: the search results running out do not end
it. Every other task is a finite commission (old ``_FiniteLiteratureYieldController`` with
``_RemainingCommissionedCredit``): the target is ``credit_unit``, read from the parent input, for every such task.
For an ``a105_experiments`` commission the credit is the sum of what its page children earned (``credit.py``: the
change of the resolution of the one commissioned candidate's subscoring sheet), so the one ``credit_unit`` is the whole
resolution going from 0 to 1; it is no longer ``credit_unit`` times the number of experiments. The cost is the old
task cutoff and the parameters the old ``uncertainty_alpha``, now the episode's settings. The old
``validate_yield_bindings`` checks of the cutoff and alpha are the controllers' own."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('web_search', initial_credit, ADAPTIVE_CONTROL, items=None)
    # The credit of an a105_experiments commission is the change of the commissioned candidate's resolution earned by its
    # pages (credit.py): one candidate, so the target is one credit_unit.
    target = task['credit_unit']
    return CompletionYieldController('web_search', initial_credit, settings['cost'], target,
                                     settings['parameters'])
