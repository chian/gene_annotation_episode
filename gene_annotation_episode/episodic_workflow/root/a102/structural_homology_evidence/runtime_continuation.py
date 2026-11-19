"""A102 credit and continuation on the generic runner (``episode_runtime``).

Each A102 binding's continuation is its own yield controller from
``yield_control`` (accumulation, bounded quality or completion), chosen
by the binding's own ``yield_controller(context, initial_credit, epoch)`` hook.
This module only connects those controllers to the contract:

- ``A102UnitInput`` is the controller input of one completed unit: the
  binding's cumulative credit after the unit (its own unbounded scale, never
  clamped or rescaled), the Episode's recorded progress-time receipt for that
  unit (``bound.progress.receipt(position)``; the estimator fits credit marks
  at these real times) and the record references the Episode had received.
  It is what the runner journals and ``restore_controller_input`` rebuilds.
- ``A102Continuation`` exposes the controller's own continuation decision as
  the boolean ``stop`` the contract requires on ``state()``; ``observe``
  returns the controller's own ``YieldStep``.
- ``A102RuntimeContext`` is the immutable identity/assignment view the A102
  binding hooks read (``context.role``, ``scope``, ``assignment``,
  ``received_record_refs``), built from the runner's ``BoundEpisode``.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType

from method_loop import ClosedRecord
from method_loop.jsonvalue import canonical

from yield_control import AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController
from gene_annotation_episode.episodic_workflow.episode_support.jobs.execution_timing import PROGRESS_TIME_VERSION

UNIT_INPUT_FIELDS = frozenset({'credit', 'estimation_context', 'received_record_refs'})


def _references(values, what):
    if isinstance(values, (str, bytes, Mapping)):
        raise TypeError(what + '_must_be_a_reference_list')
    values = tuple(values)
    if any(type(value) is not str or not value for value in values):
        raise ValueError(what + '_must_be_nonempty_text_references')
    if len(set(values)) != len(values):
        raise ValueError(what + '_must_not_repeat_a_reference')
    return values


def _credit(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(what + '_must_be_a_finite_number:' + repr(value))
    return float(value)


def _frozen(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_frozen(item) for item in value)
    return value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class A102RuntimeContext:
    """The identity and commission an A102 binding hook reads for one Episode.

    ``role`` is the binding's own A102 role (for example ``monitor``), not the
    path-qualified grain name; ``received_record_refs`` are the references the
    Episode has received so far, in receipt order.
    """
    run_id: str
    episode_id: str
    role: str
    path: tuple
    scope: Mapping
    assignment: Mapping
    request: Mapping
    received_record_refs: tuple = ()

    def __post_init__(self):
        for name in ('run_id', 'episode_id', 'role'):
            if type(getattr(self, name)) is not str or not getattr(self, name):
                raise ValueError('a102_runtime_context_' + name + '_required')
        object.__setattr__(self, 'path', tuple(tuple(part) for part in self.path))
        object.__setattr__(self, 'received_record_refs',
                           _references(self.received_record_refs, 'a102_received_record_refs'))
        for name in ('scope', 'assignment', 'request'):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise TypeError('a102_runtime_context_' + name + '_must_be_a_mapping')
            object.__setattr__(self, name, _frozen(json.loads(json.dumps(_plain(value), allow_nan=False))))

    def as_record(self):
        """The Episode identity and commission this context names (received references excluded)."""
        return {name: _plain(getattr(self, name)) for name in
                ('run_id', 'episode_id', 'role', 'path', 'scope', 'assignment', 'request')}

    @classmethod
    def from_bound(cls, bound, *, role, received_record_refs=()):
        assignment = bound.assignment
        if 'scope' not in assignment:
            raise KeyError('a102_assignment_scope_required:' + bound.binding_path)
        return cls(bound.run_id, bound.episode_id, role, bound.path, assignment['scope'], assignment,
                   bound.request.as_record(), tuple(received_record_refs))


def episode_epoch(bound):
    """The controller epoch of one Episode: the digest of its structural path."""
    return hashlib.sha256(canonical([list(part) for part in bound.path]).encode()).hexdigest()


@dataclass(frozen=True)
class A102UnitInput(ClosedRecord):
    """Controller input of one completed A102 unit."""
    credit: float
    progress_time: Mapping
    received_record_refs: tuple

    def __post_init__(self):
        object.__setattr__(self, 'credit', _credit(self.credit, 'a102_unit_credit'))
        if not isinstance(self.progress_time, Mapping) or self.progress_time.get('version') != PROGRESS_TIME_VERSION:
            raise ValueError('a102_unit_progress_time_receipt_required')
        object.__setattr__(self, 'progress_time', _frozen(_plain(self.progress_time)))
        object.__setattr__(self, 'received_record_refs',
                           _references(self.received_record_refs, 'a102_unit_received_record_refs'))

    def as_record(self):
        return {'credit': self.credit, 'estimation_context': {'progress_time': _plain(self.progress_time)},
                'received_record_refs': list(self.received_record_refs)}

    @classmethod
    def from_record(cls, record):
        if not isinstance(record, Mapping) or set(record) != UNIT_INPUT_FIELDS:
            raise ValueError('a102_unit_input_record_requires:' + ','.join(sorted(UNIT_INPUT_FIELDS)))
        context = record['estimation_context']
        if not isinstance(context, Mapping) or set(context) != {'progress_time'}:
            raise ValueError('a102_unit_input_estimation_context_requires_progress_time')
        return cls(record['credit'], context['progress_time'], tuple(record['received_record_refs']))


def unit_input(bound, position, credit, received_record_refs):
    """The controller input of unit ``position``: credit, its recorded progress receipt, received refs."""
    return A102UnitInput(credit, bound.progress.receipt(position), tuple(received_record_refs))


@dataclass(frozen=True)
class A102ContinuationState:
    """The A102 controller's state: its own continuation decision and full yield state."""
    stop: bool
    yield_state: object
    requests_transition: bool = False

    def as_record(self):
        return {'stop': self.stop, 'requests_transition': self.requests_transition,
                'yield_state': self.yield_state.as_record()}


class A102Continuation:
    """One A102 yield controller under the contract's controller protocol."""

    def __init__(self, controller):
        if not isinstance(controller, (AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController)):
            raise TypeError('a102_continuation_requires_an_a102_yield_controller:' + type(controller).__name__)
        self._controller = controller

    @property
    def epoch(self):
        return self._controller.epoch

    @property
    def controller(self):
        return self._controller

    def observe(self, unit_label, value, *, is_root):
        if not isinstance(value, A102UnitInput):
            raise TypeError('a102_continuation_observes_a102_unit_inputs:' + type(value).__name__)
        return self._controller.observe(unit_label, value, is_root)

    def state(self):
        current = self._controller.state()
        stop = current.decision.stop
        if type(stop) is not bool:
            raise TypeError('a102_continuation_decision_must_be_boolean')
        return A102ContinuationState(stop, current)

    def transitioned(self, epoch):
        return A102Continuation(self._controller.transitioned(epoch))


__all__ = ['A102Continuation', 'A102ContinuationState', 'A102RuntimeContext', 'A102UnitInput', 'episode_epoch',
           'unit_input']
