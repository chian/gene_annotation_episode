"""Continuation: the credit accumulates (the handoff unit once, and the acquired-record unit per acquired record),
and acquired records may pass the handoff, so the controller is the accumulation controller (old: the plain
accumulating ``YieldController`` with ``PracticalYieldEstimator``, README 7b: ``'accumulation'``). The completion
controller is not used: this episode's credit has no finite target it reaches exactly.

The accumulation controller takes no cost and no settings: its estimator and stop rule are nano-graphrag's, with
the adaptive control (``ADAPTIVE_CONTROL``), and it is not limited by an input list here (``items=None``). The old
profile selection (``task_yield_profiles``, cutoff as cost) is therefore not carried."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('api_job_execution', initial_credit, ADAPTIVE_CONTROL, items=None)
