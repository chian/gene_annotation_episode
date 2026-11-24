"""Continuation from the commissioned task: ``verified_source_leads`` accumulates (``AccumulationYieldController`` with
``ADAPTIVE_CONTROL``, nano-graphrag's EstimatorController): one credit unit per verified source, and no cost. After W = 8
units attempted and m = 4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected
next marginal (hypervolume) credit is at or below gamma, the adaptive gamma = max(one-result resolution, 0.1 x median of
recent productive credits). It stops after 4 flat units in a row. The input list bounds it: each commissioned window is
consumed by its extraction, so the episode stops when no window remains."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('source_coverage_improvement', initial_credit, ADAPTIVE_CONTROL,
                                       items=len(parent_input['spans']))
