"""Continuation from the commissioned task, carried from the old ``yield_estimator.py`` (README 7b).

``verified_source_leads`` accumulates (old ``YieldController``, kind ``accumulation``): one credit unit per verified
source, without limit. Its controller is ``AccumulationYieldController`` with ``ADAPTIVE_CONTROL`` and ``items=None``
(nano-graphrag's ``EstimatorController``) and has no cost: after W = 8 units attempted and m = 4 observed it fits
nano-graphrag's yield model; a unit is flat when the upper bound of the expected next marginal (hypervolume) credit is
at or below gamma (adaptive: gamma = max(one-result resolution, 0.1 x median of recent productive credits)); it stops
after 4 flat units in a row. The finite ``source_answer`` tasks and their completion controller are no longer accepted
and are removed."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('published_evidence_assessment', initial_credit, ADAPTIVE_CONTROL, items=None)
