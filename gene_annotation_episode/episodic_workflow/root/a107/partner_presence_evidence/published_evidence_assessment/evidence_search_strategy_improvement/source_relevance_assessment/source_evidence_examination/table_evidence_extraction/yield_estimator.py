"""Continuation. The old file chose nothing (``continuation_task`` and ``yield_controller`` both returned None: the
old runner's default). The credit is the A107 finding progress (``ScientificFindingProgress``, one explicit unit per
retained finding, ``yield_method = 'accumulation'``), so the controller is the accumulation controller (README 7b:
``numerical.YieldController`` -> ``AccumulationYieldController``). The grain is one selected table or sheet read
through model-selected tool calls (nano-graphrag source_table), so the control is ``ADAPTIVE_CONTROL``; the episode
works through no known list, so ``items`` is None. Nothing in the parent input is a target or a maximum."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('table_evidence_extraction', initial_credit, ADAPTIVE_CONTROL, items=None)
