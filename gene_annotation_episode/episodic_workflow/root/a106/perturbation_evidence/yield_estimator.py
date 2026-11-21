"""Continuation, carried from the old ``yield_estimator.py`` (``PerturbationEvidenceYield.yield_controller``) at
97308b94c, mapped by README 7b. The task key is ``A106:whole_axis_findings``; the projector of the task,
``ScientificFindingProgress``, declares ``yield_method = 'accumulation'`` (finding units accumulate without a
declared limit), so the old ``YieldController`` is the ``AccumulationYieldController`` of the system, a port of
nano-graphrag's EstimatorController, configured with ``ADAPTIVE_CONTROL`` and ``items=None``. It takes no cost and
reads no settings (the old cutoff and ``parameters`` are not carried). After at least W=8 units attempted and m=4
observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected next marginal
(hypervolume) credit is at or below the adaptive gamma, max(one-result resolution, 0.1 x median of the recent
productive credits); it stops after 4 flat units in a row (with ``items=None`` no item count stops it). Nothing but
this controller ends the Episode.

Not carried: the old declaration lookup ``yield_bindings[task]`` (the controller reads no settings), the old comparison of the declared ``credit_definition`` digest with the
projector's record and of the declared ``kind`` with the projector's ``yield_method`` (checks of the configuration the
caller makes), and the other two kinds of the old declaration (``bounded_quality`` and ``completion``: this
projector's method is accumulation, so a declaration of another kind was an error)."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController

TASK = 'A106:whole_axis_findings'


def yield_controller(initial_credit, settings, parent_input):
    if parent_input['task_key'] != TASK:
        raise ValueError('scientific_yield_binding_missing_for_task:' + parent_input['task_key'])
    return AccumulationYieldController('perturbation_evidence', initial_credit, ADAPTIVE_CONTROL, items=None)
