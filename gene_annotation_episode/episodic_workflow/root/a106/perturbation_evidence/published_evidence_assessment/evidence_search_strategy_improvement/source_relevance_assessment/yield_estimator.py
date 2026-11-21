"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``AccumulationYieldController``): one credit unit per verified source,
without limit. Every other task is a finite commission (old ``_FiniteLiteratureYieldController`` /
``CompletionYieldController``): the target is the old ``maximum_credit``, the task's
``credit_unit`` (the old ``maximum_credit``: one answer to the commission), read from the parent input. The cost is the old
task cutoff, now the episode's setting; the parameters are its settings. The old ``None`` (no private yield
binding) is not carried: the controller is always built from the task."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('source_relevance_assessment', initial_credit, ADAPTIVE_CONTROL,
                                           items=None)
    return CompletionYieldController('source_relevance_assessment', initial_credit, settings['cost'],
                                     task['credit_unit'],
                                     settings['parameters'])
