"""Continuation, carried from the old ``yield_estimator.py`` (``MonitorEpisodeYield.yield_controller`` and
``_monitor_information_yield``; README 7b: the monitor's information yield is the accumulation controller) and
``configuration.py`` (``MonitorConfiguration``).

The old monitor opened ``YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha=...))`` from
its own yield settings. The accumulation controller is now nano-graphrag's function and stop rule
(``ADAPTIVE_CONTROL``): it takes no cost and no settings, and the monitor has no list of items, so ``items`` is None.
Nothing else ends this Episode."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('monitor', initial_credit, ADAPTIVE_CONTROL, items=None)
