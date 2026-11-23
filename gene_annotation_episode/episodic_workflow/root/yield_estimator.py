"""Continuation: the annotation credit accumulates without a declared limit, so the root's controller is the
accumulation controller of ``yield_control``. It is given the annotation credit after every axis commission, forecasts
the credit the next commission adds, and stops this episode after ``streak_length`` forecasts in a row whose upper
bound is flat. Nothing else ends this episode.

``ROOT_CONTROL`` is the root's own tuning (the owner, 2026-11-22: the window and the streak are "tuned parameters based
on what behavior you want"). A commission of an axis head costs from minutes to hours, so the root forecasts early:
its first forecast after 3 commissions, and it stops after 2 flat forecasts in a row. These are first values, set
before any root run; they are to be tuned from the root's own run records.

The annotation task sets no target and no maximum, so the controller takes nothing from ``parent_input`` (what
``messages/read_from_parent.py`` produced). The assignment is not read here."""
from yield_control import ADAPTIVE_CONTROL, AccumulationControl, AccumulationYieldController

ROOT_CONTROL = AccumulationControl(ADAPTIVE_CONTROL.threshold, ADAPTIVE_CONTROL.gamma, ADAPTIVE_CONTROL.rho,
                                   streak_length=2, window_size=3, subsample_size=3, alpha=ADAPTIVE_CONTROL.alpha)


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('root', initial_credit, ROOT_CONTROL, items=None)
