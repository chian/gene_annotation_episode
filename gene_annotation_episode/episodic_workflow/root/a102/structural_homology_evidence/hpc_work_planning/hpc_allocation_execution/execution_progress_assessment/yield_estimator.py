"""Continuation, carried from the old ``yield_estimator.py`` (``MonitorEpisodeYield.yield_controller`` and
``_monitor_information_yield``; README 7b: the monitor's information yield is the accumulation controller) and
``configuration.py`` (``MonitorConfiguration``).

The old monitor had two modes. With its own yield settings (exactly ``{kind: 'information_accumulation', cutoff >=
0, uncertainty_alpha in (0, 1)}``) it opened ``YieldController(epoch, initial_credit, cutoff,
YieldParameters(uncertainty_alpha=...))``; without them asking for the controller raised
``monitor_private_yield_binding_not_enabled``. Now: ``settings`` is this episode's entry of the run's
``continuation`` collaborator, ``{'cost': <old cutoff, >= 0>, 'parameters': {'uncertainty_alpha': ...}}``; an entry
without them raises the same error. The cutoff is the controller's ``cost``. Nothing else ends this Episode."""
import math

from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController


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
