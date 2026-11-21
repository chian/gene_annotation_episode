"""Continuation, carried from the old ``yield_estimator.py`` (``MonitorEpisodeYield.yield_controller`` and
``_monitor_information_yield``) and ``configuration.py`` (``MonitorConfiguration``).

The old monitor had a private information-accumulation binding: exactly ``{kind: 'information_accumulation',
cutoff >= 0, uncertainty_alpha in (0, 1)}``, opened as ``YieldController(epoch, initial_credit, cutoff,
YieldParameters(uncertainty_alpha=...))``; without it asking for the controller raised
``monitor_private_yield_binding_not_enabled``. README 7b: ``_monitor_information_yield`` is the accumulation
controller. ``settings`` is this episode's entry of the run's ``continuation`` collaborator, ``{'cost': <old
cutoff, >= 0>, 'parameters': {'uncertainty_alpha': ...}}``; an entry without them raises the old error. A110 has
no BLAST status target (no API execution), so there is no completion variant. Nothing here reads the assignment
and nothing else ends this Episode."""
import math

from yield_control import ADAPTIVE_CONTROL, AccumulationYieldController

EPOCH = 'monitor'


def yield_controller(initial_credit, settings, parent_input):
    if 'cost' not in settings or 'parameters' not in settings:
        raise ValueError('monitor_private_yield_binding_not_enabled')
    cost, parameters = settings['cost'], settings['parameters']
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        raise ValueError('monitor_information_yield_values_invalid')
    alpha = parameters.get('uncertainty_alpha') if isinstance(parameters, dict) else None
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0 < alpha < 1:
        raise ValueError('monitor_information_yield_values_invalid')
    return AccumulationYieldController(EPOCH, initial_credit, ADAPTIVE_CONTROL, items=None)
