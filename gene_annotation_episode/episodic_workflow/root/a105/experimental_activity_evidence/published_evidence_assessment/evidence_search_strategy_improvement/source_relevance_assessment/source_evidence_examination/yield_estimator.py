"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``SourceYield.yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``YieldController``): one credit unit per verified source, without
limit. Every other task is a finite commission (old ``_FiniteLiteratureYieldController`` with
``_RemainingCommissionedCredit``): the target is the old ``maximum_credit``, ``credit_unit`` times the number of
experiments for ``a105_experiments`` and ``credit_unit`` otherwise, read from the parent input. The cost is the
old task cutoff and the parameters the old ``uncertainty_alpha``, now the episode's settings. The old
``validate_yield_bindings`` checks of the cutoff and alpha are the controllers' own."""
from yield_control import AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('source_evidence_examination', initial_credit, settings['cost'],
                                           settings['parameters'])
    target = task['credit_unit'] * (len(task['experiments']) if task['kind'] == 'a105_experiments' else 1)
    return CompletionYieldController('source_evidence_examination', initial_credit, settings['cost'], target,
                                     settings['parameters'])
