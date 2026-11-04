"""Finite A105 NADH optical conversion, separate from interpretation and credit.

Inputs already have the declared canonical units and episode-owned scientific
meanings. This function neither reads sources nor chooses those meanings. It
subtracts a matched background once and supplies a net endpoint rate; epsilon
and path length are optical conversion operands, not calibration recovery k.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

import numpy as np

from .literature_experimental_contracts import ExperimentalContractError


OPERANDS_VERSION = "a105_nadh_optical_rate_operands_v1"
VERSION = "a105_nadh_optical_rate_cells_v1"
PRIMITIVE_ORDER = ("sample_slope", "blank_slope", "epsilon", "path_length")
_UNITS = ("absorbance/min", "absorbance/min", "mM^-1cm^-1", "cm")
_ENUMS = {
    "covariance_status": ("known", "estimated", "unknown"),
    "relation": ("applicable_extinction_relation", "not_applicable", "unknown", "conflicting"),
    "blank_role": ("matched_no_reaction_background", "condition_reference",
                   "component_omission", "unknown", "conflicting"),
    "same_endpoint": ("same", "different", "unknown"),
    "matched_window": ("same", "different", "unknown"),
    "rate_window": ("source_supported_rate_interval", "interval_mean_only", "static_only", "unknown"),
}
_FIELDS = {"version", *PRIMITIVE_ORDER, *_ENUMS, "covariance", "primitive_observation_refs"}
_RATE_FORMULA = "-1000*(sample_slope-blank_slope)/epsilon/path_length"
_VARIANCE_FORMULA = "J*covariance*J_transpose; J=(-1000/(epsilon*l),1000/(epsilon*l),-q/epsilon,-q/l)"


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _finite(value, field, *, nullable=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def _validate(operands):
    if not isinstance(operands, dict) or set(operands) != _FIELDS:
        _fail("closed_fields_required", "operands")
    if operands["version"] != OPERANDS_VERSION:
        _fail("unsupported_operands_version", "version")
    for name in PRIMITIVE_ORDER:
        _finite(operands[name], name, nullable=True)
    for name in ("epsilon", "path_length"):
        if operands[name] is not None and operands[name] <= 0:
            _fail("positive_optical_operand_required", name)
    for name, allowed in _ENUMS.items():
        if type(operands[name]) is not str or operands[name] not in allowed:
            _fail("unsupported_" + name, name)
    refs = operands["primitive_observation_refs"]
    if not isinstance(refs, list) or len(refs) != 4:
        _fail("four_primitive_observation_refs_required", "primitive_observation_refs")
    for i, ref in enumerate(refs):
        if ref is not None and (not isinstance(ref, str) or not ref.strip()):
            _fail("nonempty_observation_ref_required", f"primitive_observation_refs[{i}]")
    raw = operands["covariance"]
    if raw is not None:
        if (not isinstance(raw, list) or len(raw) != 4
                or any(not isinstance(row, list) or len(row) != 4 for row in raw)):
            _fail("four_by_four_covariance_required", "covariance")
        for i, row in enumerate(raw):
            for j, value in enumerate(row):
                _finite(value, f"covariance[{i}][{j}]")
        # Compare supplied values before conversion: distinct large integers
        # must not become falsely symmetric by rounding to the same float.
        if any(raw[i][j] != raw[j][i] for i in range(4) for j in range(i)):
            _fail("symmetric_covariance_required", "covariance")
        matrix = np.asarray(raw, dtype=float)
        if np.any(np.diag(matrix) < 0):
            _fail("positive_semidefinite_covariance_required", "covariance")
        scale = float(np.max(np.abs(matrix)))
        try:
            eigenvalues = np.linalg.eigvalsh(matrix / scale) if scale else np.zeros(4)
        except np.linalg.LinAlgError:
            _fail("covariance_eigendecomposition_failed", "covariance")
        # Existing calculator convention: tolerate eigensolver roundoff for a
        # singular PSD matrix. Do not repair, jitter or change any input entry.
        tolerance = 64 * np.finfo(float).eps * 4
        if not np.all(np.isfinite(eigenvalues)) or float(np.min(eigenvalues)) < -tolerance:
            _fail("positive_semidefinite_covariance_required", "covariance")
    for i, ref in enumerate(refs):
        if ref is None:
            continue
        for j in range(i):
            if ref != refs[j]:
                continue
            if _UNITS[i] != _UNITS[j]:
                _fail("reused_identity_dimension_mismatch", "primitive_observation_refs")
            left, right = operands[PRIMITIVE_ORDER[i]], operands[PRIMITIVE_ORDER[j]]
            if left is not None and right is not None and left != right:
                _fail("reused_identity_value_mismatch", "primitive_observation_refs")
            if raw is not None and any(raw[i][k] != raw[j][k] or raw[k][i] != raw[k][j]
                                       for k in range(4)):
                _fail("reused_identity_covariance_mismatch", "covariance")


def _rate_reason(operands):
    for name in PRIMITIVE_ORDER:
        if operands[name] is None:
            return "missing_" + name
    relation = operands["relation"]
    if relation != "applicable_extinction_relation":
        return "optical_relation_" + relation
    if operands["blank_role"] in ("unknown", "conflicting"):
        return "blank_role_unresolved"
    if operands["blank_role"] != "matched_no_reaction_background":
        return "blank_role_not_background"
    if operands["same_endpoint"] != "same":
        return "endpoint_mismatch_or_unknown"
    if operands["matched_window"] != "same":
        return "window_mismatch_or_unknown"
    if operands["rate_window"] != "source_supported_rate_interval":
        return "rate_interval_unestablished"
    return None


def _as_result(value):
    """Represent an exact arithmetic result as float without silent lost zero."""
    try:
        result = float(value)
    except OverflowError:
        return None, "numerical_model_range"
    if not math.isfinite(result) or (result == 0 and value != 0):
        return None, "numerical_model_range"
    return result, None


def _cell(value, unit, formula, reason, conditions):
    return {"value": value, "unit": unit,
            "status": "unavailable" if value is None else "populated",
            "formula": formula, "origin": "derived", "unavailable_reason": reason,
            "conditional_on": list(conditions)}


def calculate_nadh_optical_rate(operands):
    """Return signed uM/min rate and its conditional first-order variance.

    Reason precedence is missing primitives in PRIMITIVE_ORDER, relation, blank
    role, endpoint, matched window, rate interval, rate numerical range. Variance
    inherits a rate failure, then checks absent covariance, unknown covariance
    status, impossible negative propagated variance, and numerical range.

    Known or estimated covariance permits JΣJᵀ; its supplied status remains in
    the snapshot and conditional facts. Unknown identities never imply
    independence. Neither a positive rate nor supplied covariance establishes
    initial-rate linearity, normality, a likelihood, probability or credit.

    Exact rational arithmetic on the supplied finite numbers avoids avoidable
    intermediate overflow and preserves signed covariance cross terms. Final
    values must be representable finite floats; a nonzero result that rounds to
    zero is unavailable. No matrix entries or negative variance are clipped.
    """
    _validate(operands)
    snapshot = deepcopy(operands)
    conditions = [f"{name}={snapshot[name]}" for name in
                  ("relation", "blank_role", "same_endpoint", "matched_window", "rate_window")]
    reason = _rate_reason(snapshot)
    rate = exact_rate = None
    if reason is None:
        sample, blank, epsilon, length = (Fraction(snapshot[name]) for name in PRIMITIVE_ORDER)
        exact_rate = -1000 * (sample - blank) / epsilon / length
        rate, reason = _as_result(exact_rate)
    variance = None
    variance_reason = reason
    if variance_reason is None and snapshot["covariance"] is None:
        variance_reason = "covariance_unreported"
    if variance_reason is None and snapshot["covariance_status"] == "unknown":
        variance_reason = "covariance_status_unknown"
    if variance_reason is None:
        jacobian = (-1000 / (epsilon * length), 1000 / (epsilon * length),
                    -exact_rate / epsilon, -exact_rate / length)
        propagated = sum(jacobian[i] * Fraction(snapshot["covariance"][i][j]) * jacobian[j]
                         for i in range(4) for j in range(4))
        if propagated < 0:
            variance_reason = "invalid_propagated_variance"
        else:
            variance, variance_reason = _as_result(propagated)
    return {"version": VERSION, "endpoint": "NADH_depletion",
            "net_depletion_rate": _cell(rate, "uM/min", _RATE_FORMULA, reason, conditions),
            "net_depletion_variance": _cell(variance, "(uM/min)^2", _VARIANCE_FORMULA,
                variance_reason, [*conditions, "first_order_covariance_propagation",
                                  "covariance_status=" + snapshot["covariance_status"]]),
            "primitive_observation_refs": deepcopy(snapshot["primitive_observation_refs"]),
            "input_snapshot": snapshot}


__all__ = ["OPERANDS_VERSION", "VERSION", "PRIMITIVE_ORDER", "calculate_nadh_optical_rate"]
