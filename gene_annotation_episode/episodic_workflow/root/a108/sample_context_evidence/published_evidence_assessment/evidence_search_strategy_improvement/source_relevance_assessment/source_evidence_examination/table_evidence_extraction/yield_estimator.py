"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``YieldController``, kind ``accumulation``): one credit unit per verified
source, without limit. Its controller is ``AccumulationYieldController`` with ``ADAPTIVE_CONTROL`` and ``items=None``
(nano-graphrag's EstimatorController), and it takes no cost. After W = 8 units attempted and m = 4 observed it fits
nano-graphrag's yield model; a unit is flat when the upper bound of the expected next marginal (hypervolume) credit is
at or below gamma, the adaptive gamma = max(one-result resolution, 0.1 x median of recent productive credits). It stops
after 4 flat units in a row; with ``items=None`` it has no input-list stop. The two ``source_answer`` tasks are finite commissions (old ``_FiniteLiteratureYieldController``
with ``_RemainingCommissionedCredit``, kind ``remaining_commissioned_credit``): a completion controller whose target is
the old ``maximum_credit``, the task's ``credit_unit``, read from the parent input. The cost is the old task cutoff and
the parameters the old ``uncertainty_alpha``: both are the episode's settings. The old ``None`` (no private yield
binding) is not carried: the controller is always built from the task. The old ``validate_yield_bindings`` checked the
owner's declarations when the binding was constructed; the controllers' own checks replace it."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('table_evidence_extraction', initial_credit, ADAPTIVE_CONTROL, items=None)
    return CompletionYieldController('table_evidence_extraction', initial_credit, settings['cost'],
                                     task['credit_unit'], settings['parameters'])
