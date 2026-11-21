"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``AccumulationYieldController``): one credit unit per verified source,
without limit. A source answer is one answer to the commission (old ``_FiniteLiteratureYieldController`` /
``CompletionYieldController`` with the commissioned ``credit_unit`` as its finite target): the target is
``task['credit_unit']`` from the parent input. This episode's credit for a source answer is at most one
``credit_unit`` (screening counts the own declarations and assessment returns at most one answer), so it cannot
pass the target. The cost is the old task cutoff, now the episode's setting; the parameters are its settings."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('source_relevance_assessment', initial_credit, ADAPTIVE_CONTROL,
                                           items=None)
    return CompletionYieldController('source_relevance_assessment', initial_credit, settings['cost'],
                                     task['credit_unit'], settings['parameters'])
