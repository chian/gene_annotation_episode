"""Continuation, carried from the old ``yield_estimator.py`` (``PerturbationEvidenceYield.yield_controller``) at
97308b94c, mapped by README 7b. The task key is ``A106:whole_axis_findings``; the projector of the task,
``ScientificFindingProgress``, declares ``yield_method = 'accumulation'`` (finding units accumulate without a
declared limit), so the old ``YieldController`` is the ``AccumulationYieldController`` of the system. The old cutoff is
its cost and the old ``parameters`` are the episode's settings. Nothing but this controller ends the Episode.

Not carried: the old declaration lookup ``yield_bindings[task]`` (the settings of the episode are its own entry of the
run's ``continuation`` collaborator), the old comparison of the declared ``credit_definition`` digest with the
projector's record and of the declared ``kind`` with the projector's ``yield_method`` (checks of the configuration the
caller makes), and the other two kinds of the old declaration (``bounded_quality`` and ``completion``: this
projector's method is accumulation, so a declaration of another kind was an error)."""
from yield_control import AccumulationYieldController

TASK = 'A106:whole_axis_findings'


def yield_controller(initial_credit, settings, parent_input):
    if parent_input['task_key'] != TASK:
        raise ValueError('scientific_yield_binding_missing_for_task:' + parent_input['task_key'])
    return AccumulationYieldController('perturbation_evidence', initial_credit, settings['cost'],
                                       settings['parameters'])
