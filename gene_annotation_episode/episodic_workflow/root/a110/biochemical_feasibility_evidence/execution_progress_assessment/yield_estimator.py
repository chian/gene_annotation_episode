"""Continuation, carried from the old ``yield_estimator.py`` (``MonitorEpisodeYield.yield_controller`` and
``_monitor_information_yield``) and ``configuration.py`` (``MonitorConfiguration``).

README 7b: ``_monitor_information_yield`` is the accumulation controller: ``AccumulationYieldController``, a port of
nano-graphrag's EstimatorController, configured by this Episode with ``ADAPTIVE_CONTROL`` and ``items=None`` (the
monitor's input list size is not known at its start, so no item count ends it). It takes no cost. After at least
W=8 units attempted and m=4 observed it fits nano-graphrag's yield model; a unit is flat when the upper bound of the
expected next marginal (hypervolume) credit is at or below gamma, which is adaptive: gamma = max(one-result
resolution, 0.1 x median of the recent productive credits); it stops after 4 flat units in a row. ``settings`` is
this episode's entry of the run's ``continuation`` collaborator and must still carry ``{'cost': <number >= 0>,
'parameters': {'uncertainty_alpha': <in (0, 1)>}}`` (without them ``monitor_private_yield_binding_not_enabled``,
with invalid values ``monitor_information_yield_values_invalid``), but neither reaches the controller: ``cost`` is
the cost of a check in the estimate table (``task.py``). A110 has
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
