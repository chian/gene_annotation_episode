"""The root credit: one weighted offset-product hypervolume over the axis credits.

    credit = prod_i (1 + k * v_i) ** w_i - 1,    k = (1 - epsilon) / epsilon,  epsilon = 0.5 (k = 1)

Axis credits keep their own scales: they are never bounded, clamped or
rescaled. The axes are exactly the keys of the weights; every weighted axis
needs a credit and no other credit is admitted.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

HYPERVOLUME_EPSILON = 0.5
HYPERVOLUME_OFFSET = (1.0 - HYPERVOLUME_EPSILON) / HYPERVOLUME_EPSILON


def finite_number(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(what + '_must_be_a_finite_number:' + repr(value))
    return float(value)


def annotation_hypervolume(axis_credits, axis_weights):
    """The root credit over ``axis_credits`` (each >= 0, unbounded) with positive ``axis_weights``."""
    if not isinstance(axis_credits, Mapping) or not isinstance(axis_weights, Mapping):
        raise TypeError('hypervolume_credits_and_weights_must_be_mappings')
    if not axis_weights:
        raise ValueError('hypervolume_requires_weighted_axes')
    if set(axis_credits) != set(axis_weights):
        raise KeyError('hypervolume_credit_axes_differ_from_weighted_axes:missing='
                       + ','.join(sorted(map(str, set(axis_weights) - set(axis_credits))))
                       + ':unknown=' + ','.join(sorted(map(str, set(axis_credits) - set(axis_weights)))))
    volume = 1.0
    for axis in axis_weights:
        credit = finite_number(axis_credits[axis], 'axis_credit:' + str(axis))
        weight = finite_number(axis_weights[axis], 'axis_weight:' + str(axis))
        if credit < 0:
            raise ValueError('axis_credit_must_not_be_negative:' + str(axis) + ':' + repr(credit))
        if weight <= 0:
            raise ValueError('axis_weight_must_be_positive:' + str(axis) + ':' + repr(weight))
        volume *= (1.0 + HYPERVOLUME_OFFSET * credit) ** weight
    if not math.isfinite(volume):
        raise OverflowError('hypervolume_not_finite')
    return volume - 1.0


__all__ = ['HYPERVOLUME_EPSILON', 'HYPERVOLUME_OFFSET', 'annotation_hypervolume', 'finite_number']
