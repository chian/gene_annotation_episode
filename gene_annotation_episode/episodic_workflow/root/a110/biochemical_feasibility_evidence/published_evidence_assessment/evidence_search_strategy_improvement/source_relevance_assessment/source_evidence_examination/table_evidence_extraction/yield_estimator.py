"""The old episode named no estimator or settings of its own (``yield_estimator.py``: ``continuation_task`` and
``yield_controller`` both returned None; ``credit_kind`` was ``scientific``). Its credit is the accumulating
scientific credit of the findings it retained, with no maximum and no commissioned target, so the controller is the
accumulation one (README 7b: ``numerical.YieldController``)."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('table_evidence_extraction', initial_credit, ADAPTIVE_CONTROL, items=None)
