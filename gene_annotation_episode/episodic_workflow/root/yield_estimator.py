"""Continuation: the annotation credit accumulates without a declared limit, so the root's controller is the
accumulation controller of ``yield_control``. It is given the annotation credit after every axis commission and
stops this episode when its forecast upper bound of the next commission's gain is at or below the root's own
threshold, ``settings['cost']`` (the root's own entry of the run's continuation settings, with the estimator's
``settings['parameters']``). At a threshold of zero an accumulating controller never stops. Nothing else ends this
episode.

The annotation task sets no target and no maximum, so the controller takes nothing from ``parent_input`` (what
``messages/read_from_parent.py`` produced). The assignment is not read here."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('root', initial_credit, settings['cost'], settings['parameters'])
