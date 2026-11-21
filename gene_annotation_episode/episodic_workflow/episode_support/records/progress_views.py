"""Progress summaries an episode shows its model: measured time so far and its yield forecast.

* ``time_accounting(receipt)`` presents the Episode's recorded progress-time receipt of its last completed unit
  (``bound.progress.receipt(position - 1)``; ``None`` before any unit completed). It reports the measured elapsed
  real time since the Episode's origin, including idle time, exactly as recorded; an unavailable receipt stays
  unavailable with its reason. Nothing is estimated, and it is never compute consumption. It reads no clock: a
  decision-time reading would not be a recorded point.
* ``yield_table(controller_state, *, forecast_unit)`` presents a ``yield_control`` controller state
  (``view.controller_state``): the initial and current credit, every observed marginal credit in unit order, the
  forecast of the next marginal credit, the continuation cost and whether the controller requests a stop. Credits
  are shown unchanged.
"""
from __future__ import annotations

from collections.abc import Mapping

from yield_control import PROGRESS_TIME_VERSION

from yield_control import ForecastYieldState, YieldState

_TIME_FIELDS = ('position', 'status', 'unavailable_reason', 'elapsed_seconds', 'reference_elapsed_seconds',
                'captured_at', 'origin_captured_at', 'includes_idle_time', 'is_compute_consumption')


def time_accounting(receipt):
    """The measured progress time of the last completed unit, as recorded (see the module docstring)."""
    if receipt is None:
        return {'version': PROGRESS_TIME_VERSION, 'status': 'no_completed_unit', 'elapsed_seconds': None,
                'includes_idle_time': True, 'is_compute_consumption': False}
    if not isinstance(receipt, Mapping) or receipt.get('version') != PROGRESS_TIME_VERSION \
            or receipt.get('point_kind') != 'progress_receipt':
        raise ValueError('time_accounting_requires_an_episode_progress_receipt')
    return {'version': PROGRESS_TIME_VERSION, **{name: receipt[name] for name in _TIME_FIELDS}}


def yield_table(controller_state, *, forecast_unit):
    """The yield forecast an episode's controller holds now (see the module docstring)."""
    if type(forecast_unit) is not str or not forecast_unit:
        raise ValueError('yield_table_forecast_unit_required')
    if isinstance(controller_state, ForecastYieldState):
        # The forecast of each offered action is added to the decision by the system (``action_forecasts``).
        return {'version': 'episode_forecast_table_v1', 'epoch': controller_state.epoch,
                'initial_credit': controller_state.initial_credit, 'current_credit': controller_state.current_credit,
                'marginal_credits': list(controller_state.history), 'completed_units': len(controller_state.history),
                'stop_requested': controller_state.stop, 'parameters': controller_state.parameters.as_record(),
                'forecast_unit': forecast_unit}
    if not isinstance(controller_state, YieldState):
        raise TypeError('yield_table_requires_a_yield_control_state:' + type(controller_state).__name__)
    record = controller_state.as_record()
    decision = record['decision']
    return {'version': 'episode_yield_table_v1', 'epoch': record['epoch'],
            'initial_credit': record['initial_credit'], 'current_credit': record['current_credit'],
            'marginal_credits': list(record['scores']), 'completed_units': len(record['scores']),
            'expected_next_gain': decision['projected_gain'], 'continuation_cost': decision['continuation_cost'],
            'stop_requested': decision['stop'], 'decision_basis': decision['decision_basis'],
            'parameters': record['estimate']['parameters'], 'forecast_unit': forecast_unit}


__all__ = ['time_accounting', 'yield_table']
