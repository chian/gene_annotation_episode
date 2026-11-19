"""Continuation. The old file chose nothing (``continuation_task`` and ``yield_controller`` returned None: the old
runner's default controller). The credit is a count of retained findings, which accumulates without a declared
maximum or commissioned target (README 7b: ``numerical.YieldController`` -> ``AccumulationYieldController``). The cost
and the parameters are this episode's settings; nothing in the parent input is a target or a maximum, so nothing of
the parent input is read."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('source_coverage_improvement', initial_credit, settings['cost'],
                                       settings['parameters'])
