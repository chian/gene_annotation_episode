"""Continuation: the head's credit counts retained findings without a limit, so its controller is accumulation.

Carried from the old ``yield_estimator.py`` (``SampleContextEvidenceYield.yield_controller``, task key
``A108:whole_axis_findings``; README 7b). The old estimator took the declared kind (accumulation, bounded_quality or
completion) and checked it against the projector's own ``yield_method`` and the digest of its credit definition. The
projector of this episode (``ScientificFindingProgress``) has the ``yield_method`` ``accumulation``, so the old
bounded-quality and completion branches could not be reached with it and are not carried; the old digest comparison of
the owner's declaration with ``projector.as_record()`` has no declaration to compare with now. The old ``None`` for a
workflow without yield bindings is not carried. The accumulation controller (nano-graphrag's ``EstimatorController``,
``ADAPTIVE_CONTROL``) takes no cost and no settings: after W=8 units attempted and m=4 observed it fits nano-graphrag's
yield model; a unit is flat when the upper bound of the expected next marginal (hypervolume) credit is at or below
gamma, the adaptive gamma = max(one-result resolution, 0.1 x median of recent productive credits); it stops after 4
flat units in a row. With ``items=None`` the episode has no input item list, so no item count stops it."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('sample_context_evidence', initial_credit, ADAPTIVE_CONTROL, items=None)
