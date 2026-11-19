"""The root's continuation: one independent yield estimate per evidence axis.

Each returned axis invocation is one observation for that axis: the credit it
returned, at the root's progress receipt for that unit. The root stops only when
every axis's available upper bound on the credit of another whole invocation is
at or below that axis's own cutoff. An axis with no observation has an unknown
forecast, never zero. The controller state also carries the root credit
(``credit.annotation_hypervolume`` over the accumulated axis credits).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
from types import MappingProxyType

from yield_control import (AccumulationYieldEstimator, YieldParameters,
                           predicted_gain_upper_bound)
from method_loop import ClosedRecord

from .credit import annotation_hypervolume, finite_number


@dataclass(frozen=True)
class AxisReturn(ClosedRecord):
    """One root unit's controller input: the axis commissioned, the credit and finding its result carried,
    and the root's progress receipt for the unit."""
    axis: str
    credit: float
    finding: object  # non-empty text or record, as the axis's return form types it
    estimation_context: Mapping = field(default_factory=dict)

    def __post_init__(self):
        if type(self.axis) is not str or not self.axis:
            raise ValueError('axis_return_axis_required')
        object.__setattr__(self, 'credit', finite_number(self.credit, 'axis_return_credit:' + self.axis))
        if self.credit < 0:
            raise ValueError('axis_return_credit_must_not_be_negative:' + self.axis)
        if not ((type(self.finding) is str and self.finding.strip())
                or (isinstance(self.finding, Mapping) and self.finding)):
            raise ValueError('axis_return_finding_required:' + self.axis)
        if not isinstance(self.estimation_context, Mapping) or set(self.estimation_context) != {'progress_time'}:
            raise ValueError('axis_return_requires_its_progress_receipt:' + self.axis)

    def as_record(self):
        return json.loads(json.dumps({'axis': self.axis, 'credit': self.credit, 'finding': self.finding,
                                      'estimation_context': dict(self.estimation_context)},
                                     sort_keys=True, allow_nan=False))

    @classmethod
    def from_record(cls, record):
        if not isinstance(record, Mapping) or set(record) != {'axis', 'credit', 'finding', 'estimation_context'}:
            raise ValueError('axis_return_record_requires_axis_credit_finding_estimation_context')
        return cls(record['axis'], record['credit'], record['finding'], record['estimation_context'])


@dataclass(frozen=True)
class AnnotationState:
    """Axis returns observed, each axis's accumulated credit and forecast, the root credit and the stop decision."""
    units_observed: int
    axis_credits: Mapping
    credit: float
    arms: tuple
    stop: bool
    requests_transition: bool = False

    def as_record(self):
        return {'units_observed': self.units_observed, 'axis_credits': dict(self.axis_credits),
                'credit': self.credit, 'arms': [dict(arm) for arm in self.arms],
                'decision': {'stop': self.stop,
                             'decision_basis': 'every_axis_available_upper_bound_lte_own_cutoff'}}


class AnnotationController:
    """Per-axis yield estimation over the weighted axes; ``axis_cutoffs`` names exactly the same axes."""

    def __init__(self, axis_weights, axis_cutoffs, uncertainty_alpha):
        if not isinstance(axis_cutoffs, Mapping) or set(axis_cutoffs) != set(axis_weights):
            raise KeyError('annotation_cutoffs_must_name_exactly_the_weighted_axes')
        self._weights = axis_weights
        self._axes = tuple(axis_weights)
        self._cutoffs = {axis: finite_number(axis_cutoffs[axis], 'axis_cutoff:' + axis) for axis in self._axes}
        settings = YieldParameters(finite_number(uncertainty_alpha, 'uncertainty_alpha'))
        self._estimators = {axis: AccumulationYieldEstimator(settings) for axis in self._axes}
        self._credits = {axis: 0.0 for axis in self._axes}  # no axis has returned credit yet
        self._observed = 0

    def observe(self, label, value, *, is_root):
        if not isinstance(value, AxisReturn):
            raise TypeError('annotation_controller_observes_axis_returns:' + type(value).__name__)
        if value.axis not in self._estimators:
            raise KeyError('annotation_controller_axis_not_attached:' + value.axis)
        self._credits[value.axis] += value.credit
        self._estimators[value.axis].observe(value.credit, context=dict(value.estimation_context))
        self._observed += 1
        return self.state()

    def state(self):
        arms = []
        for axis in self._axes:
            estimate = self._estimators[axis].state()
            decision = predicted_gain_upper_bound(estimate.expected_next_gain, self._cutoffs[axis])
            arms.append({'axis': axis, 'credit': self._credits[axis],
                         'expected_additional_credit': estimate.expected_next_gain.as_record(),
                         'completed_invocation_observations': estimate.turns, 'cutoff': self._cutoffs[axis],
                         'stop_requested': decision.stop, 'forecast_unit': 'another_whole_axis_invocation'})
        credits = MappingProxyType(dict(self._credits))
        return AnnotationState(self._observed, credits, annotation_hypervolume(credits, self._weights),
                               tuple(arms), all(arm['stop_requested'] for arm in arms))

    def transitioned(self, epoch):
        raise RuntimeError('annotation_controller_has_no_epoch_transition:' + str(epoch))


__all__ = ['AnnotationController', 'AnnotationState', 'AxisReturn']
