"""Continuation of the page: ``verified_source_leads`` is the only task. Its credit is the page's sheet credit
(``credit.py``) and accumulates, without limit; the page's yield estimator alone stops it. Its list is the paper's
candidates (prose chunks and table regions) no leaf has consumed yet: the estimator also stops when none is left
(nano-graphrag: a page with nothing left to hand out ends). The list is not known when the page starts, so the page
counts it after each unit (``items_remaining``)."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController

from .task import CANDIDATES_OF_SLOT


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('page', initial_credit, ADAPTIVE_CONTROL, items=None)


def items_remaining(summary):
    """The number of candidates no leaf has consumed. None while the list is not settled: Jev has not assessed the paper's
    candidates yet, or returned leaf records still wait for the sheet update (a unit the page owes)."""
    if summary['content_assessment_ref'] is None or summary['unused_leaf_record_refs']:
        return None
    return sum(len(summary[name]) for name in CANDIDATES_OF_SLOT.values())
