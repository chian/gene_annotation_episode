"""Pure, conditional Michaelis--Menten transport-response arithmetic.

Operands are source-mean concentrations in uM, with curve and physical
measurement identities supplied by the caller. This boundary neither discovers
those identities nor converts a printed spread into sampling covariance. Its
response is an operand for an appropriate downstream effect correction, never a
reliability weight, likelihood, annotation score, or credit.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a105_transport_response_v1"
PRIMITIVE_ORDER = ("substrate_test", "substrate_reference", "km")
COMPONENTS = ("substrate_test", "substrate_reference", "apparent_km",
              "test_saturation", "reference_saturation", "condition_response",
              "log_condition_response", "condition_response_variance",
              "condition_response_standard_uncertainty")
_CONDITIONS = ("same_kinetic_curve", "michaelis_menten_response")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _fields(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _finite(value, field, *, nullable=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def _validate(inputs):
    _fields(inputs, ("values", "curve_keys", "measurement_keys", "covariance",
                     "variance_status", "observation_model", "origin"), "inputs")
    _fields(inputs["values"], PRIMITIVE_ORDER, "values")
    for name in PRIMITIVE_ORDER:
        _finite(inputs["values"][name], "values." + name, nullable=True)
    for field in ("curve_keys", "measurement_keys"):
        _fields(inputs[field], PRIMITIVE_ORDER, field)
        for name in PRIMITIVE_ORDER:
            value = inputs[field][name]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                _fail("nonempty_identity_required", field + "." + name)
    for field, allowed in (
        ("variance_status", ("known", "estimated", "unknown")),
        ("observation_model", ("michaelis_menten", "unknown")),
        ("origin", ("reported", "derived", "graph_derived", "synthetic")),
    ):
        if not isinstance(inputs[field], str) or inputs[field] not in allowed:
            _fail("unsupported_" + field, field)

    raw = inputs["covariance"]
    matrix = None
    if raw is not None:
        if (not isinstance(raw, list) or len(raw) != 3
                or any(not isinstance(row, list) or len(row) != 3 for row in raw)):
            _fail("three_by_three_covariance_required", "covariance")
        for i, row in enumerate(raw):
            for j, value in enumerate(row):
                _finite(value, f"covariance[{i}][{j}]")
        matrix = [[Fraction(value) for value in row] for row in raw]
        if any(matrix[i][j] != matrix[j][i] for i in range(3) for j in range(3)):
            _fail("symmetric_covariance_required", "covariance")
        # For a symmetric 3x3 matrix, nonnegative *all* principal minors
        # characterize PSD, including singular matrices. Exact rational checks
        # avoid scale-dependent eigenvalue tolerance, repair, or artificial jitter.
        a, b, c = matrix[0]
        _, d, e = matrix[1]
        _, _, f = matrix[2]
        minors = (a, d, f, a*d-b*b, a*f-c*c, d*f-e*e,
                  a*d*f + 2*b*c*e - a*e*e - d*c*c - f*b*b)
        if any(minor < 0 for minor in minors):
            _fail("positive_semidefinite_covariance_required", "covariance")

    identities = inputs["measurement_keys"]
    for i, left in enumerate(PRIMITIVE_ORDER):
        for j in range(i):
            right = PRIMITIVE_ORDER[j]
            if identities[left] is None or identities[left] != identities[right]:
                continue
            if inputs["values"][left] != inputs["values"][right]:
                _fail("shared_measurement_value_mismatch", "measurement_keys." + left)
            if matrix is not None and (matrix[i] != matrix[j]
                    or any(matrix[k][i] != matrix[k][j] for k in range(3))):
                _fail("shared_measurement_covariance_mismatch", "covariance")
    return matrix


def _float(value):
    """Convert an exact result without representing nonzero underflow as zero."""
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(result) or (result == 0 and value != 0):
        return None
    return result


def _cell(value, unit, formula, *, reason=None, origin="derived", conditional=()):
    if reason is None and value is not None:
        value = _float(value)
        if value is None:
            reason = "numerical_model_range"
    return {"value": value, "unit": unit,
            "status": "unavailable" if value is None else "populated",
            "formula": formula, "origin": origin, "unavailable_reason": reason,
            "conditional_on": list(conditional)}


def _reason(inputs, names):
    if any(inputs["values"][name] is None for name in names):
        return "concentration_inputs_unreported"
    if any(inputs["values"][name] <= 0 for name in names):
        return "positive_concentration_required"
    keys = [inputs["curve_keys"][name] for name in names]
    if any(key is None for key in keys):
        return "kinetic_curve_identity_unreported"
    if any(key != keys[0] for key in keys):
        return "different_kinetic_curves"
    if inputs["observation_model"] != "michaelis_menten":
        return "observation_model_unspecified"
    return None


def _log_ratio(value):
    # Near unity, log1p preserves a small response contrast; constructing a
    # floating response first would round that contrast away. Outside that
    # interval decimal logarithms also handle responses outside float range.
    delta = value - 1
    if abs(delta) < Fraction(1, 2):
        small = _float(delta)
        return None if small is None else math.log1p(small)
    with localcontext() as context:
        context.prec = 80
        return (Decimal(value.numerator).ln() - Decimal(value.denominator).ln())


def populate_transport_response(inputs):
    """Populate native inputs, saturation, response and conditional uncertainty.

    ``covariance`` is a supplied full 3x3 matrix in uM² in primitive order.
    Reusing a physical measurement key requires identical native values and
    covariance rows/columns. Equal values under distinct keys remain distinct
    random variables. Covariance propagation requires all physical identities;
    unknown covariance, ownership or status never implies independence.

    All three response operands must belong to the same caller-identified
    kinetic curve under the selected Michaelis--Menten model. Saturations use
    only their own substrate/Km pair. Known or estimated covariance permits
    *first-order* propagation; it does not establish a sampling distribution.
    In the variance formula, St/Sr denote substrate_test/substrate_reference;
    Jh is the response gradient in the declared primitive order.
    Rational arithmetic keeps h, its derivatives and J C Jᵀ stable through
    extreme intermediate ranges and signed covariance cancellation. Each cell
    separately reports unavailable if its final value exceeds float range.
    """
    matrix = _validate(inputs)
    values = inputs["values"]
    cells = {}
    for primitive, name in zip(PRIMITIVE_ORDER, COMPONENTS[:3]):
        cells[name] = _cell(values[primitive], "uM", primitive,
                            reason="concentration_unreported" if values[primitive] is None else None,
                            origin=inputs["origin"])
    for substrate, name in (("substrate_test", "test_saturation"),
                            ("substrate_reference", "reference_saturation")):
        reason = _reason(inputs, (substrate, "km"))
        value = None
        if reason is None:
            s, k = Fraction(values[substrate]), Fraction(values["km"])
            value = s / (k + s)
        cells[name] = _cell(value, "dimensionless", f"{substrate}/(km+{substrate})",
                            reason=reason, conditional=_CONDITIONS)

    reason = _reason(inputs, PRIMITIVE_ORDER)
    response = log_response = gradient = None
    if reason is None:
        st, sr, k = (Fraction(values[name]) for name in PRIMITIVE_ORDER)
        response = st*(k+sr)/(sr*(k+st))
        log_response = _log_ratio(response)
        # Km appears once as a physical primitive, shared by both saturations.
        jlog = (k/(st*(k+st)), -k/(sr*(k+sr)), 1/(k+sr)-1/(k+st))
        gradient = tuple(response * derivative for derivative in jlog)
    cells["condition_response"] = _cell(response, "dimensionless",
        "substrate_test*(km+substrate_reference)/(substrate_reference*(km+substrate_test))",
        reason=reason, conditional=_CONDITIONS)
    cells["log_condition_response"] = _cell(log_response, "dimensionless",
        "log(condition_response)", reason=reason or (
            "numerical_model_range" if log_response is None else None), conditional=_CONDITIONS)

    variance_reason = reason
    if variance_reason is None and matrix is None:
        variance_reason = "primitive_covariance_unreported"
    if variance_reason is None and any(
            inputs["measurement_keys"][name] is None for name in PRIMITIVE_ORDER):
        variance_reason = "primitive_measurement_identity_unreported"
    if variance_reason is None and inputs["variance_status"] == "unknown":
        variance_reason = "primitive_variance_status_unknown"
    variance = uncertainty = None
    if variance_reason is None:
        variance = sum(gradient[i]*matrix[i][j]*gradient[j]
                       for i in range(3) for j in range(3))
        with localcontext() as context:
            context.prec = 80
            uncertainty = (Decimal(variance.numerator)/Decimal(variance.denominator)).sqrt()
    conditions = (*_CONDITIONS, "first_order_covariance_propagation")
    cells["condition_response_variance"] = _cell(variance, "dimensionless_squared",
        "Jh*covariance*Jh_transpose; Jh=h*[km/(St*(km+St)),-km/(Sr*(km+Sr)),1/(km+Sr)-1/(km+St)]",
        reason=variance_reason, conditional=conditions)
    cells["condition_response_standard_uncertainty"] = _cell(uncertainty, "dimensionless",
        "sqrt(condition_response_variance)", reason=variance_reason, conditional=conditions)
    return {"version": VERSION, "primitive_order": list(PRIMITIVE_ORDER),
            "inputs": deepcopy(inputs), "cells": cells}


__all__ = ["VERSION", "PRIMITIVE_ORDER", "COMPONENTS", "populate_transport_response"]
