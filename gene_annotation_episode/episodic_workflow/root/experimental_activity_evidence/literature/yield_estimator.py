"""Continuation: the one task, ``verified_source_leads``, accumulates (old ``YieldController``): one credit unit per
verified source, without limit. Its controller is ``AccumulationYieldController`` with ``items=None`` (no input list),
nano-graphrag's estimator controller, and it has no cost: after the first W units it fits nano-graphrag's yield model
and forecasts the next unit's added (hypervolume) credit; a unit is flat when the upper bound of that forecast is at or
below the adaptive gamma, max(one-result resolution, 0.1 x the median of the recent productive credits); it stops after
a streak of flat forecasts in a row.

The round's own tuning of the adaptive control (owner, 2026-11-22: the window and the streak are tuned parameters; tune
them to the cost:benefit seen in real runs): first forecast after 5 units (W = 5, m = 4), stop after 3 flat forecasts in
a row, so 7 units at the least. Same estimator and threshold as ``ADAPTIVE_CONTROL`` (W = 8, streak 4, 11 units at the
least). Why, from the four finished rounds of the real runs a105_head_popz_chpt_10, _14, _17 and _18: a unit is one search
strategy (about 9 minutes, about 27 model calls); the three rounds that earned made their last gain at their 1st, 4th and
5th strategy and then ran 6 to 10 more that earned nothing. Replayed on those recorded histories these settings keep
all the credit the rounds earned and end them after 7 strategies instead of 11. The strategy, the search and the page
below keep ``ADAPTIVE_CONTROL``: the same replay shows their gains arriving as late as their 8th to 10th unit, and any
shorter setting cut credit that was found."""
from yield_control import ADAPTIVE_CONTROL, AccumulationControl, AccumulationYieldController

LITERATURE_CONTROL = AccumulationControl(ADAPTIVE_CONTROL.threshold, ADAPTIVE_CONTROL.gamma, ADAPTIVE_CONTROL.rho,
                                         streak_length=3, window_size=5, subsample_size=4, alpha=ADAPTIVE_CONTROL.alpha)


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('literature', initial_credit, LITERATURE_CONTROL, items=None)
