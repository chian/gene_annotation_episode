"""Continuation, carried from the old ``yield_estimator.py`` (``ExperimentalActivityEvidenceYield.yield_controller``;
README 7b): the head's only credit is accumulated distinct findings, whose projector declared
``yield_method = 'accumulation'`` for the task ``A105:whole_axis_findings``, so its controller is the accumulation
controller, a port of nano-graphrag's EstimatorController, with the adaptive threshold and the head's own window and
streak (``HEAD_CONTROL`` below) and no list of items (``items=None``). It takes no cost and no settings. After its
first W units it fits nano-graphrag's yield model and forecasts the next unit's added (hypervolume) credit; a unit is
flat when the upper bound of that forecast is at or below gamma, the adaptive gamma = max(one-result resolution, 0.1 x
median of the recent productive credits), recomputed after every unit; it stops after a streak of flat forecasts in a
row. With ``items=None`` no item count ends it. The old
configuration admitted accumulation, bounded_quality and completion, but this head's projector fixed
``yield_method = 'accumulation'``, so the accumulation controller is the one; the old declaration checks
(``credit_definition`` digest against the projector record, ``yield_method`` against ``kind``) have nothing left to
compare: the kind is fixed and the finding unit is the commission's own (``parent_input['evidence_task']``, which
``credit.py`` projects with)."""
from yield_control import ADAPTIVE_CONTROL, AccumulationControl, AccumulationYieldController

# The head's own tuning of the adaptive control (owner, 2026-11-22: the window and the streak are tuned parameters; tune
# them to the cost:benefit seen in real runs). Same estimator, same adaptive threshold; only the first fit and the streak
# differ: first forecast after 3 units (W = 3, m = 3), stop after 2 flat forecasts in a row.
# Why, from the real runs a105_head_popz_chpt_17 and _18: a unit of the head is a whole literature round (about 1.7 hours,
# about 300 model calls; the round already looks until its own estimator stops it) or a cheap record query that earns
# nothing. Run 18's head earned 0.249 in its first round and nothing in the 1.7 hours of its second; with W = 8 and a
# streak of 4 it could not stop before about 11 units. Replayed on run 18's recorded head history these settings stop it
# at its 4th unit, straight after the round that earned nothing; when every unit is a round, that is 3 rounds after the
# last gain at the most.
HEAD_CONTROL = AccumulationControl(ADAPTIVE_CONTROL.threshold, ADAPTIVE_CONTROL.gamma, ADAPTIVE_CONTROL.rho,
                                   streak_length=2, window_size=3, subsample_size=3, alpha=ADAPTIVE_CONTROL.alpha)


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('experimental_activity_evidence', initial_credit, HEAD_CONTROL, items=None)
