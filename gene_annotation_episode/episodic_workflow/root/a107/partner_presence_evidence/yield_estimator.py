"""Continuation: accumulation only. The old ``yield_estimator.py`` opened ``YieldController(epoch, initial_credit,
cutoff, YieldParameters(uncertainty_alpha))`` for the declared task ``A107:<name>`` and raised
``scientific_yield_method_unavailable`` for a bounded-quality or completion declaration (README 7b, the
``numerical.YieldController`` row). Its credit is finding progress that accumulates and is never bounded, so the
controller is ``AccumulationYieldController``; its cost (the old ``cutoff``) and parameters
(``uncertainty_alpha``) are this episode's settings. The old declaration checks (task name, credit definition,
yield method) belonged to the old yield bindings and are not carried: nothing in the parent input is a target or a
maximum."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('partner_presence_evidence', initial_credit, settings['cost'],
                                       settings['parameters'])
