"""A105 source-activity correction and explicitly conditional numerical evidence.

This finite boundary consumes already identified, unit-consistent operands. It
performs no source reading, experimental interpretation, target correspondence,
annotation-credit aggregation or episode continuation. Unknown operands remain
unknown. Estimated covariance is retained without being promoted to a known
normal sampling model.
"""
from __future__ import annotations

from copy import deepcopy
import math

import numpy as np

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a105_corrected_activity_v1"
PRIMITIVE_ORDER = ("q", "g", "k", "E", "u", "v")
COMPONENTS = ("corrected_activity", "effect_variance", "effect_standard_uncertainty",
              "effect_precision", "source_profile_log_ratio", "source_presence_index")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _finite(value, field, *, nullable=False, nonnegative=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)
    if nonnegative and value < 0:
        _fail("nonnegative_variance_required", field)


def _cell(value, unit, formula, *, reason=None, origin="derived", conditional=()):
    if value is not None and not math.isfinite(value):
        value, reason = None, "numerical_model_range"
    return {"value": value, "unit": unit,
            "status": "unavailable" if value is None else "populated",
            "formula": formula, "origin": origin, "unavailable_reason": reason,
            "conditional_on": list(conditional)}


def _validate(inputs):
    keys = {"values", "covariance", "variance_status", "distinct_residual_variance",
            "observation_model"}
    if not isinstance(inputs, dict) or set(inputs) != keys:
        _fail("closed_fields_required", "inputs")
    values = inputs["values"]
    if not isinstance(values, dict) or set(values) != set(PRIMITIVE_ORDER):
        _fail("closed_fields_required", "values")
    for name in PRIMITIVE_ORDER:
        _finite(values[name], "values." + name, nullable=True)
    # Normalization/calibration and the reference response are positive physical
    # denominators. A negative noisy q remains permissible and visible.
    for name in ("k", "E", "u", "v"):
        if values[name] is not None and values[name] <= 0:
            _fail("positive_normalization_operand_required", "values." + name)
    _finite(inputs["distinct_residual_variance"], "distinct_residual_variance",
            nullable=True, nonnegative=True)
    if inputs["variance_status"] not in ("known", "estimated", "unknown"):
        _fail("unsupported_variance_status", "variance_status")
    if inputs["observation_model"] not in ("none", "known_normal_nonnegative_presence"):
        _fail("unsupported_observation_model", "observation_model")
    raw = inputs["covariance"]
    if raw is None:
        return None
    if (not isinstance(raw, list) or len(raw) != 6
            or any(not isinstance(row, list) or len(row) != 6 for row in raw)):
        _fail("six_by_six_covariance_required", "covariance")
    for i, row in enumerate(raw):
        for j, value in enumerate(row):
            _finite(value, f"covariance[{i}][{j}]")
    matrix = np.asarray(raw, dtype=float)
    if not np.array_equal(matrix, matrix.T):
        _fail("symmetric_covariance_required", "covariance")
    if np.any(np.diag(matrix) < 0):
        _fail("positive_semidefinite_covariance_required", "covariance")
    # Scale before eigendecomposition to avoid overflow; no jitter or covariance
    # repair. An indefinite input is rejected even when the requested direction
    # happens to have a positive quadratic form.
    scale = float(np.max(np.abs(matrix)))
    try:
        eig = np.linalg.eigvalsh(matrix / scale) if scale else np.zeros(6)
    except np.linalg.LinAlgError:
        _fail("covariance_eigendecomposition_failed", "covariance")
    # eigvalsh has rounding error even for exact rank-deficient covariance. The
    # tolerance accepts only numerical residue and never modifies the matrix.
    tolerance = 64 * np.finfo(float).eps * 6
    if not np.all(np.isfinite(eig)) or float(np.min(eig)) < -tolerance:
        _fail("positive_semidefinite_covariance_required", "covariance")
    return matrix


def populate_corrected_activity(inputs):
    """Populate the existing source correction model and its numerical cells.

    Primitive order is ``q,g,k,E,u,v``: net preparation rate, independently
    measured contaminating contribution, calibration recovery, molecule amount,
    and a separate same-endpoint test/reference condition response. Rates use
    uM/min, E uses uM, k is dimensionless. Consequently a is per_min and the
    supplied distinct residual variance is per_min_squared. The condition-control
    comparison excludes the variable intentionally tested. Those relationships
    must be established before this calculator receives operands.

    JΣJᵀ is first-order derivative propagation for this nonlinear correction;
    supplying known primitive covariance does not prove the corrected effect is
    exactly normal. The explicit observation model is a conditional assumption,
    not a conclusion of arithmetic. The presence index is a proposed bounded
    transformation, not function probability or target-transfer credit.
    """
    matrix = _validate(inputs)
    values = inputs["values"]
    missing = [name for name in PRIMITIVE_ORDER if values[name] is None]
    effect = gradient = None
    gradient_reason = None
    effect_reason = "correction_inputs_unreported" if missing else None
    if not missing:
        q, g, k, amount, test, reference = (float(values[key]) for key in PRIMITIVE_ORDER)
        try:
            effect = ((q - g) / k / amount) * (reference / test)
            if not math.isfinite(effect) or (effect == 0 and q != g):
                effect, effect_reason = None, "numerical_model_range"
            else:
                factor = (reference / test) / k / amount
                gradient = np.array([factor, -factor, -effect / k, -effect / amount,
                    -effect / test, effect / reference], dtype=float)
                if not np.all(np.isfinite(gradient)):
                    gradient, gradient_reason = None, "numerical_model_range"
        except (ArithmeticError, ValueError):
            effect_reason = "numerical_model_range"
    cells = {"corrected_activity": _cell(effect, "per_min", "(q-g)*v/(k*E*u)",
                                         reason=effect_reason)}
    variance = None
    variance_reason = effect_reason or gradient_reason
    if variance_reason is None and matrix is None:
        variance_reason = "primitive_covariance_unreported"
    if variance_reason is None and inputs["distinct_residual_variance"] is None:
        variance_reason = "distinct_residual_variance_unreported"
    if variance_reason is None:
        try:
            # fsum preserves signed cross terms; unknown covariance was rejected
            # above rather than being replaced by an independence assumption.
            propagated = math.fsum(float(gradient[i]) * float(matrix[i, j]) * float(gradient[j])
                                  for i in range(6) for j in range(6))
            variance = math.fsum([propagated, float(inputs["distinct_residual_variance"])])
            if not math.isfinite(variance):
                variance, variance_reason = None, "numerical_model_range"
            elif variance < 0:
                # No clipping of an impossible propagated variance.
                variance, variance_reason = None, "invalid_propagated_variance"
        except (ArithmeticError, ValueError):
            variance_reason = "numerical_model_range"
    propagation_condition = ("first_order_covariance_propagation",)
    cells["effect_variance"] = _cell(variance, "per_min_squared",
        "J*covariance*J_transpose+distinct_residual_variance", reason=variance_reason,
        conditional=propagation_condition)
    cells["effect_standard_uncertainty"] = _cell(
        math.sqrt(variance) if variance is not None else None, "per_min",
        "sqrt(effect_variance)", reason=variance_reason, conditional=propagation_condition)
    positive_reason = variance_reason or ("positive_effect_variance_required" if variance == 0 else None)
    try:
        precision = 1 / variance if positive_reason is None else None
    except ArithmeticError:
        precision, positive_reason = None, "numerical_model_range"
    cells["effect_precision"] = _cell(precision, "min_squared", "1/effect_variance",
        reason=positive_reason, conditional=propagation_condition)
    score_reason = positive_reason
    if score_reason is None and inputs["variance_status"] != "known":
        score_reason = "known_variance_required"
    if score_reason is None and inputs["observation_model"] != "known_normal_nonnegative_presence":
        score_reason = "observation_model_unspecified"
    score = None
    if score_reason is None:
        try:
            # Divide first to avoid unnecessary overflow in a^2.
            z = max(0., effect) / math.sqrt(variance)
            score = z * z / 2
            if not math.isfinite(score) or (score == 0 and effect > 0):
                score, score_reason = None, "numerical_model_range"
        except ArithmeticError:
            score_reason = "numerical_model_range"
    conditions = (*propagation_condition, "known_variance", "known_normal_nonnegative_presence")
    cells["source_profile_log_ratio"] = _cell(score, "dimensionless",
        "max(0,corrected_activity)^2/(2*effect_variance)", reason=score_reason,
        conditional=conditions)
    cells["source_presence_index"] = _cell(math.tanh(score / 2) if score is not None else None,
        "dimensionless", "tanh(source_profile_log_ratio/2)", reason=score_reason,
        origin="proposed", conditional=conditions)
    return {"version": VERSION, "primitive_order": list(PRIMITIVE_ORDER),
            "inputs": deepcopy(inputs), "cells": cells}


__all__ = ["VERSION", "PRIMITIVE_ORDER", "COMPONENTS", "populate_corrected_activity"]
