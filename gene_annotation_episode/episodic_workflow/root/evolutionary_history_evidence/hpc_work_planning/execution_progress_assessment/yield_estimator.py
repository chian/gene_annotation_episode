"""Continuation, carried from the old ``yield_estimator.py`` (``MonitorEpisodeYield.yield_controller`` and
``_monitor_information_yield``; README 7b: the monitor's information yield is the accumulation controller) and
``configuration.py`` (``MonitorConfiguration``).

The old monitor had two modes. With its own yield settings (exactly ``{kind: 'information_accumulation', cutoff >=
0, uncertainty_alpha in (0, 1)}``) it opened ``YieldController(epoch, initial_credit, cutoff,
YieldParameters(uncertainty_alpha=...))``; without them asking for the controller raised
``monitor_private_yield_binding_not_enabled``. Now: ``settings`` is this episode's entry of the run's
``continuation`` collaborator, ``{'cost': <old cutoff, >= 0>, 'parameters': {'uncertainty_alpha': ...}}``; an entry
without them raises the same error and invalid values raise ``monitor_information_yield_values_invalid``. They are
only checked: neither reaches the controller, which takes no cost. The controller is the accumulation controller, a
port of nano-graphrag's EstimatorController, configured with nano-graphrag's adaptive control (``ADAPTIVE_CONTROL``).
After at least W=8 units attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the
upper bound of the expected next marginal (hypervolume) credit is at or below gamma, the adaptive gamma = max(one-
result resolution, 0.1 x median of recent productive credits); it stops after 4 flat units in a row. The monitor's
input list size is not known at its start, so ``items`` is ``None`` and no item count ends it. Nothing else ends
this Episode."""
import math

from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    if 'cost' not in settings or 'parameters' not in settings:
        raise ValueError('monitor_private_yield_binding_not_enabled')
    cost, parameters = settings['cost'], settings['parameters']
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        raise ValueError('monitor_information_yield_values_invalid')
    alpha = parameters.get('uncertainty_alpha') if isinstance(parameters, dict) else None
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0 < alpha < 1:
        raise ValueError('monitor_information_yield_values_invalid')
    return AccumulationYieldController('monitor', initial_credit, ADAPTIVE_CONTROL, items=None)
