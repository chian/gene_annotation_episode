"""Continuation of the page: ``verified_source_leads`` is the only task. It accumulates (``AccumulationYieldController``
with ``ADAPTIVE_CONTROL`` and ``items=None``): one credit unit per verified source, without limit; the page's yield
estimator alone stops it."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('source_evidence_examination', initial_credit, ADAPTIVE_CONTROL, items=None)
