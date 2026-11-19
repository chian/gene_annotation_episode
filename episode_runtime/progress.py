"""Per-unit progress-time receipts and per-decision clock points for one Episode (``episode_progress_time_v1``).

The runner gives every Episode a ``ProgressClock`` through its ``BoundEpisode``.
The Episode's origin point is captured once when the Episode is first built and
recorded in the run journal; each ``receipt(position)`` is captured once per
unit position and recorded, so a resumed run reads the recorded receipts back
instead of measuring again. Elapsed time is real monotonic time including idle
time on the same boot; it is not compute consumption. A receipt whose origin
was captured on another boot, or whose boot identity cannot be read, is
recorded with ``status='unavailable'`` and its reason; it is never estimated.

Every available receipt also carries the Episode's reference span: the
observation of its first available receipt (``reference_observation_monotonic_ns``)
and that observation's elapsed time from the origin (``reference_elapsed_seconds``).
The reference is recorded once with the first available receipt, so a credit
estimator can express later receipt times in units of the Episode's first
measured span instead of in action ranks. The clock decides nothing: credit and
continuation remain the binding's.

``decision_point(position)`` is the clock an episode's ``decide`` and ``action`` are shown (``ctx.clock``): the
time at which the Episode began choosing unit ``position``, captured once per position and recorded, so every
``decide`` call for that unit, and every replay of it on resume, sees the same time and rebuilds the same model
request. It never changes the reference span of the progress receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time

from yield_control import PROGRESS_TIME_VERSION

_ORIGIN = 'episode_runtime.progress_origin'
_REFERENCE = 'episode_runtime.progress_reference'
_RECEIPT = 'episode_runtime.progress_receipt.'
_DECISION = 'episode_runtime.decision_point.'


def _boot_id():
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip() or None
    except OSError:
        return None


def _point():
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'monotonic_ns': time.monotonic_ns(),
            'boot_id': _boot_id()}


@dataclass(frozen=True)
class DecisionClock:
    """The time ``decide`` and ``action`` are shown for the unit being chosen (recorded once per unit position).

    ``now`` is the UTC time at which the Episode began choosing this unit; ``began_at`` the UTC time the Episode
    began; ``elapsed_seconds`` the monotonic seconds between them (``None`` when ``status`` is ``'unavailable'``,
    with ``unavailable_reason``: the clocks cannot be compared, for example after a reboot); ``progress_time`` is
    the recorded progress receipt of the Episode's last completed unit (``None`` before the first)."""
    now: str
    began_at: str
    elapsed_seconds: object
    status: str
    unavailable_reason: object
    progress_time: object


class ProgressClock:
    """The progress-time receipts of one Episode, recorded in the run journal."""

    def __init__(self, recorder, *, run_id, episode_id):
        self._recorder, self.run_id, self.episode_id = recorder, run_id, episode_id
        self.origin = recorder.recorded(_ORIGIN, _point)

    def receipt(self, position):
        """The recorded progress-time receipt of unit ``position`` (captured once)."""
        if type(position) is not int or position < 0:
            raise ValueError('progress_receipt_position_must_be_a_nonnegative_integer:' + repr(position))
        return self._recorder.recorded(_RECEIPT + str(position), lambda: self._measure(position))

    def decision_point(self, position):
        """The recorded ``DecisionClock`` of the decision for unit ``position`` (captured once)."""
        if type(position) is not int or position < 0:
            raise ValueError('decision_point_position_must_be_a_nonnegative_integer:' + repr(position))
        point = self._recorder.recorded(_DECISION + str(position), self._elapsed)
        previous = None
        if position:
            found, previous = self._recorder.lookup(_RECEIPT + str(position - 1))
            if not found:
                raise LookupError('progress_receipt_not_recorded_for_completed_unit:' + str(position - 1))
        return DecisionClock(now=point['captured_at'], began_at=self.origin['captured_at'],
                             elapsed_seconds=point['elapsed_seconds'], status=point['status'],
                             unavailable_reason=point['unavailable_reason'], progress_time=previous)

    def _elapsed(self):
        now, origin = _point(), self.origin
        point = {'captured_at': now['captured_at'], 'elapsed_seconds': None, 'status': 'unavailable',
                 'unavailable_reason': None}
        if now['boot_id'] is None or origin['boot_id'] is None:
            point['unavailable_reason'] = 'boot_identity_unavailable'
        elif now['boot_id'] != origin['boot_id'] or now['monotonic_ns'] <= origin['monotonic_ns']:
            point['unavailable_reason'] = 'episode_clock_not_comparable'
        else:
            point.update(elapsed_seconds=(now['monotonic_ns'] - origin['monotonic_ns']) / 1e9, status='available')
        return point

    def _measure(self, position):
        now, origin = _point(), self.origin
        receipt = {'version': PROGRESS_TIME_VERSION, 'run_id': self.run_id, 'episode_id': self.episode_id,
                   'position': position, 'point_kind': 'progress_receipt', 'captured_at': now['captured_at'],
                   'observed_monotonic_ns': now['monotonic_ns'], 'boot_id': now['boot_id'],
                   'origin_captured_at': origin['captured_at'], 'origin_monotonic_ns': origin['monotonic_ns'],
                   'origin_boot_id': origin['boot_id'], 'elapsed_seconds': None,
                   'reference_observation_monotonic_ns': None, 'reference_elapsed_seconds': None,
                   'status': 'unavailable', 'unavailable_reason': None, 'clock': 'monotonic',
                   'time_unit': 'seconds', 'includes_idle_time': True, 'is_compute_consumption': False,
                   'reference_span': 'first_available_receipt_of_this_episode'}
        if now['boot_id'] is None or origin['boot_id'] is None:
            receipt['unavailable_reason'] = 'boot_identity_unavailable'
            return receipt
        if now['boot_id'] != origin['boot_id'] or now['monotonic_ns'] <= origin['monotonic_ns']:
            receipt['unavailable_reason'] = 'episode_clock_not_comparable'
            return receipt
        # The first available receipt fixes the reference span; later receipts reuse the recorded one.
        reference = self._recorder.recorded(_REFERENCE, lambda: {'boot_id': now['boot_id'],
                                                                  'monotonic_ns': now['monotonic_ns']})
        if reference['boot_id'] != now['boot_id'] or reference['monotonic_ns'] > now['monotonic_ns']:
            receipt['unavailable_reason'] = 'episode_reference_not_comparable'
            return receipt
        receipt.update(elapsed_seconds=(now['monotonic_ns'] - origin['monotonic_ns']) / 1e9,
                       reference_observation_monotonic_ns=reference['monotonic_ns'],
                       reference_elapsed_seconds=(reference['monotonic_ns'] - origin['monotonic_ns']) / 1e9,
                       status='available')
        return receipt


__all__ = ['DecisionClock', 'ProgressClock']
