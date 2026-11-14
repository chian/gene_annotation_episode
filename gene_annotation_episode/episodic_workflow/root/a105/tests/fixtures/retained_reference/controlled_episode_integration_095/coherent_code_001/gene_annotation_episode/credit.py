"""Numerical hypervolume arithmetic; the categorical annotation scorer is retired.

A numerical component sheet must supply actual values before annotation scoring
can be bound. No category-to-number policy or default evidence vector exists.
Historical run values remain in their receipts and are not reprojected here.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Mapping

from .evidence_geometry import _number


FORMULA_VERSION = "offset_normalized_product_hypervolume_v1"
# Compatibility names for old imports, not a usable scoring configuration.
AXES = ()
PROJECTION_VERSION = "categorical_annotation_projection_retired_v1"
LEGACY_INTEGRATION = "partition_product_sum_v1"
STABLE_INTEGRATION = "equal_component_integer_mass_v1"


class AnnotationScoringUnavailable(ValueError):
    """An absent scoring function is not a zero-valued annotation."""


def unavailable_annotation_score():
    return {"status": "unavailable", "annotation_score": None,
            "reason": "numerical_evidence_component_scorer_not_bound"}


def _retired():
    raise AnnotationScoringUnavailable(
        "categorical_annotation_scoring_retired_use_original_snapshot_for_historical_replay")


class CreditPolicy:
    """Retired entry point retained only to give stale callers a precise error."""

    def __init__(self, *args, **kwargs):
        _retired()

    @classmethod
    def from_record(cls, value):
        _retired()


def project_credit(*args, **kwargs):
    """Do not turn historical assessment labels into numerical evidence."""
    _retired()


@dataclass(frozen=True)
class HypervolumeParameters:
    """Explicit arithmetic inputs, independent of any scientific scoring sheet.

    Weights are weights of already computed numeric components. This object has
    no default axes, no interpretation-label weights and no measurement mapper.
    It neither supplies evidence nor defines how experiments are combined.
    """

    axis_weights: tuple
    epsilon: float

    def __post_init__(self):
        rows = (self.axis_weights.items() if isinstance(self.axis_weights, Mapping)
                else self.axis_weights)
        weights = []
        for axis, weight in rows:
            if not isinstance(axis, str) or not axis.strip():
                raise ValueError("hypervolume_axis_name_required")
            weights.append((axis, _number(weight, "axis_weight")))
        if not weights or len(dict(weights)) != len(weights):
            raise ValueError("hypervolume_axes_must_be_nonempty_and_unique")
        if not any(weight > 0 for _, weight in weights):
            raise ValueError("hypervolume_needs_positive_weight")
        epsilon = _number(self.epsilon, "epsilon", maximum=1)
        if not 0 < epsilon < 1:
            raise ValueError("epsilon_must_be_strictly_between_zero_and_one")
        object.__setattr__(self, "axis_weights", tuple(weights))
        object.__setattr__(self, "epsilon", epsilon)


def softened_hypervolume(evidence, policy=None):
    """Preserve the existing product formula on explicit numerical operands.

    Every axis needs a measured/computed value. Missing or unknown is not zero.
    No component calculation or new ten-axis aggregation policy is chosen here.
    """
    if not isinstance(policy, HypervolumeParameters):
        raise AnnotationScoringUnavailable("explicit_numeric_hypervolume_parameters_required")
    if not isinstance(evidence, Mapping) or set(evidence) != set(dict(policy.axis_weights)):
        raise ValueError("hypervolume_requires_every_explicit_numeric_component")
    exponent = sum(weight for _, weight in policy.axis_weights)
    baseline = policy.epsilon ** exponent
    volume = math.prod((policy.epsilon + (1-policy.epsilon) *
        _number(evidence[axis], axis, maximum=1)) ** weight
        for axis, weight in policy.axis_weights)
    return min(1., max(0., (volume-baseline)/(1-baseline)))
