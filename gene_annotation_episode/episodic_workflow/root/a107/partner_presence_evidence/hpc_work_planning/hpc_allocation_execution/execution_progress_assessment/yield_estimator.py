"""Continuation, carried from the old ``yield_estimator.py`` (``MonitorEpisodeYield.yield_controller`` and
``_monitor_information_yield``; README 7b: the monitor's information yield is the accumulation controller) and
``configuration.py`` (``MonitorConfiguration``).

The old monitor opened ``YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha=...))`` from
its own yield settings. The accumulation controller is now a port of nano-graphrag's EstimatorController, configured
by this Episode with nano-graphrag's adaptive control (``ADAPTIVE_CONTROL``). It takes no cost and no settings. After
at least W=8 units attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound
of the expected next marginal (hypervolume) credit is at or below gamma, the adaptive threshold max(one-result
resolution, 0.1 x median of recent productive credits); it stops after 4 flat units in a row. The monitor has no list
of items, so ``items`` is ``None`` and no item count ends it. Nothing else ends this Episode."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('monitor', initial_credit, ADAPTIVE_CONTROL, items=None)
