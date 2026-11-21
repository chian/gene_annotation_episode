"""Continuation: the credit accumulates (the handoff unit once, and the acquired-record unit per acquired record),
and acquired records may pass the handoff, so the controller is the accumulation controller (old: the plain
accumulating ``YieldController`` with ``PracticalYieldEstimator``, README 7b: ``'accumulation'``). The completion
controller is not used: this episode's credit has no finite target it reaches exactly.

The accumulation controller, a port of nano-graphrag's EstimatorController, takes no cost and no settings; it is
given the adaptive control (``ADAPTIVE_CONTROL``) and no list of items (``items=None``). After at least W=8 units
attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected
next marginal (hypervolume) credit is at or below gamma, the adaptive gamma = max(one-result resolution, 0.1 x
median of the recent productive credits), recomputed after every unit; it stops after 4 flat units in a row. With
``items=None`` no item count ends it. The old profile selection (``task_yield_profiles``, cutoff as cost) is
therefore not carried."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('api_job_execution', initial_credit, ADAPTIVE_CONTROL, items=None)
