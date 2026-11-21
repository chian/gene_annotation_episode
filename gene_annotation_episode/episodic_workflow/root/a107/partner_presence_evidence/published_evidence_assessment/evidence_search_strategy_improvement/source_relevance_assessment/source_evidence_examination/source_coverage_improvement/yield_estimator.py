"""Continuation. The old file chose nothing (``continuation_task`` and ``yield_controller`` returned None: the old
runner's default controller). The credit is a count of retained findings, which accumulates without a declared
maximum or commissioned target (README 7b: ``numerical.YieldController`` -> ``AccumulationYieldController``). The
accumulation takes no cost: the controller is nano-graphrag's estimator and stop rule, and this episode picks the
fixed-gamma control because its unit is one model-selected tool call reading one bounded window of the source (a leaf
reading one window per unit). The episode works through no known list, so no item count is given."""
from yield_control import AccumulationYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('source_coverage_improvement', initial_credit, FIXED_CONTROL, items=None)
