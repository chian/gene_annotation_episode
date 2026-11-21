"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``YieldController``, now ``AccumulationYieldController``): one credit unit
per verified source, without limit. Every other task is a finite commission (old ``_FiniteLiteratureYieldController``
with ``_RemainingCommissionedCredit``, now ``CompletionYieldController``): the target is the task's ``credit_unit``
(the old ``maximum_credit``: one answer to the commission), read from the parent input. The cost is the old task
cutoff, now the episode's setting; the parameters are its settings. The old ``None`` (no private yield binding) and
the old ``validate_yield_bindings`` declaration checks are not carried: the controller is always built from the
task, and the settings are the run's ``continuation`` entry."""
from yield_control import AccumulationYieldController, CompletionYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('passage_evidence_extraction', initial_credit, FIXED_CONTROL, items=None)
    return CompletionYieldController('passage_evidence_extraction', initial_credit, settings['cost'],
                                     task['credit_unit'], settings['parameters'])
