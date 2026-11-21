"""Continuation of the page: ``verified_source_leads`` is the only task. Its credit is the page's sheet credit
(``credit.py``) and accumulates, without limit; the page's yield estimator alone stops it."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('page', initial_credit, ADAPTIVE_CONTROL, items=None)
