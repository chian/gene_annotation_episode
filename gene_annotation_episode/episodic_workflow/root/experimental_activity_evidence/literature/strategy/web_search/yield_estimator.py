"""Continuation: the one task, ``verified_source_leads``, accumulates (old ``YieldController``): one credit unit per
verified source, controlled by ``AccumulationYieldController`` with ``ADAPTIVE_CONTROL``
(nano-graphrag's EstimatorController), which has no cost and reads no settings. After W = 8 units attempted and m = 4
observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected next marginal
(hypervolume) credit is at or below the adaptive gamma (the larger of the one-result resolution and 0.1 x the median of
the recent productive credits); it stops after 4 flat units in a row. Its list is the search's hits that have not been
picked yet: the estimator also stops when none is left (nano-graphrag: a search whose results are used up ends). The list
is not known when the episode starts, so the episode counts it after each unit (``items_remaining``)."""
from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController

from .task import assessment_pending


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('web_search', initial_credit, ADAPTIVE_CONTROL, items=None)


def items_remaining(summary):
    """The number of hits not picked yet. None while the list is not settled: the provider search, the listing of the
    records' publications or Jev's assessment of the results is still to run, or the page of a fetched hit is owed."""
    if (summary['pending_search'] is not None or summary['pending_listing'] is not None or assessment_pending(summary)
            or summary['pending_page'] is not None):
        return None
    return len(summary['input_list'])
