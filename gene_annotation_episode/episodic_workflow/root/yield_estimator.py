"""Continuation: the annotation credit accumulates without a declared limit, so the root's controller is the
accumulation controller of ``yield_control``. It is given the annotation credit after every step, forecasts the credit
the next step adds, and stops this episode after ``streak_length`` forecasts in a row whose upper bound is flat.
Nothing else ends this episode.

``ROOT_CONTROL`` is the root's own tuning (the owner, 2026-11-22: the window and the streak are "tuned parameters based
on what behavior you want"). The root's steps are of two costs: a commission of an axis head costs from minutes to
hours, and the making of an annotation's claims costs seconds and earns no credit by itself (it is what lets a head
check the annotation). The claims of several annotations may be made one after the other, so the window is long
enough that those steps alone do not end the episode: the first forecast comes after 4 steps and the episode stops
after 3 flat forecasts in a row, that is, after 6 steps in a row that earned nothing. These are first values; they are
to be tuned from the root's own run records.

The steps the root can take are a list that grows and shrinks as it works (``task.choices``: only steps with
something new to run on are offered), so the root counts the steps left after every unit (``items_remaining``) and the
controller ends the episode when none is left: every head ran fully and every claim was checked.

The annotation task sets no target and no maximum, so the controller takes nothing from ``parent_input`` (what
``messages/read_from_parent.py`` produced). The assignment is not read here."""
from yield_control import ADAPTIVE_CONTROL, AccumulationControl, AccumulationYieldController

from .task import choices

ROOT_CONTROL = AccumulationControl(ADAPTIVE_CONTROL.threshold, ADAPTIVE_CONTROL.gamma, ADAPTIVE_CONTROL.rho,
                                   streak_length=3, window_size=4, subsample_size=4, alpha=ADAPTIVE_CONTROL.alpha)


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('root', initial_credit, ROOT_CONTROL, items=None)


def items_remaining(summary):
    """The steps left to take: the ones ``task.choices`` offers now."""
    return len(choices(summary))
