"""Continuation from the commissioned task, carried from the old ``yield_estimator.py``
(``yield_controller`` -> ``_private_yield_controller``; README 7b).

``verified_source_leads`` accumulates (old ``AccumulationYieldController``): one credit unit per verified source,
without limit. Its controller (``FIXED_CONTROL``, ``items=None``; the nano-graphrag ``EstimatorController`` port) has
no cost: after 8 units attempted and 4 observed it fits nano-graphrag's yield model; a unit is flat when the upper
bound of the expected next marginal (hypervolume) credit is at or below gamma 0.06; it stops after 4 flat units in a
row (with ``items=None`` there is no input-list item stop). Every other task is a finite commission (old ``_FiniteLiteratureYieldController`` /
``CompletionYieldController``): the target is the old ``maximum_credit``, the task's
``credit_unit`` (the old ``maximum_credit``: one answer to the commission), read from the parent input. The cost is the old
task cutoff, now the episode's setting; the parameters are its settings. The old ``None`` (no private yield
binding) is not carried: the controller is always built from the task."""
from yield_control import AccumulationYieldController, CompletionYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    task = parent_input['task']
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController('source_coverage_improvement', initial_credit, FIXED_CONTROL,
                                           items=None)
    return CompletionYieldController('source_coverage_improvement', initial_credit, settings['cost'],
                                     task['credit_unit'],
                                     settings['parameters'])
