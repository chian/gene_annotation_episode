"""Finite A105 amount comparisons, separate from activity and final credit.

Source interpretation, custody and unit conversion precede this boundary. Ratios
of target/total estimates are not automatically validated purity; nominal between-arm amounts
are not active concentrations or a response model. No saved rate is changed.
"""
from __future__ import annotations

import math

from .literature_amount_inputs import ROLES, validate_amount_calculation_inputs


VERSION = "a105_amount_components_v1"
COMPONENTS = ("numerator_amount", "denominator_amount", "amount_difference", "amount_ratio",
    "reciprocal_amount_ratio", "conditional_mass_denominator_factor", "amount_difference_variance",
    "amount_difference_standard_uncertainty", "amount_ratio_variance", "amount_ratio_standard_uncertainty",
    "reciprocal_amount_ratio_variance", "reciprocal_amount_ratio_standard_uncertainty")
REASONS = ("source_measurement_unavailable", "censored_measurement", "conflicting_measurement",
    "source_amount_unit_unreported", "unsupported_source_amount_unit",
    "amount_qualification_unknown", "amount_qualification_conflicting", "comparison_kind_unknown",
    "comparison_kind_conflicting", "pair_relationship_unknown", "pair_relationship_conflicting",
    "amount_basis_unknown", "amount_basis_conflicting", "amount_role_mismatch", "amount_kind_unresolved",
    "stock_relationship_unknown", "stock_relationship_conflicting", "different_stocks",
    "incompatible_amount_dimensions", "reused_source_observation", "zero_denominator_amount",
    "zero_numerator_amount", "mass_factor_not_applicable", "positive_mass_estimates_required",
    "amount_covariance_unreported", "numerical_model_range", "invalid_propagated_variance")


def _cell(value, unit, formula, *, reason=None, approximate=False, origin="derived", conditional=()):
    if value is not None and not math.isfinite(value):
        value, reason = None, "numerical_model_range"
    return {"value": value, "unit": unit, "status": "populated" if value is not None else "unavailable",
        "formula": formula, "origin": origin, "unavailable_reason": reason,
        "approximate": approximate, "conditional_on": list(conditional)}


def _individual_reason(row):
    if row is None:
        return "source_measurement_unavailable"
    if row["unavailable_reason"]:
        return row["unavailable_reason"]
    return {"observed": None, "unavailable": "source_measurement_unavailable",
        "censored": "censored_measurement", "conflicting": "conflicting_measurement"}[row["status"]]


def _pair_reason(inputs, individual_reasons):
    if any(individual_reasons.values()):
        return next(reason for reason in individual_reasons.values() if reason)
    quantities = inputs["quantities"]
    for row in quantities.values():
        if row["qualification"] in ("unknown", "conflicting"):
            return "amount_qualification_" + row["qualification"]
    for field in ("comparison_kind", "pair_relationship"):
        if inputs[field] in ("unknown", "conflicting"):
            return field + "_" + inputs[field]
    for row in quantities.values():
        if row["basis_status"] != "supported":
            return "amount_basis_" + row["basis_status"]
    n, d = (quantities[role] for role in ROLES)
    if n["unit"] != d["unit"]:
        return "incompatible_amount_dimensions"
    same_token = n["measurement_key"] == d["measurement_key"]
    same_physical = n["physical_observation_key"] is not None and n["physical_observation_key"] == d["physical_observation_key"]
    if same_token or same_physical:
        return "reused_source_observation"
    stock = inputs["comparison_kind"] == "stock_target_mass_estimate_over_total_mass_estimate"
    if stock:
        if n["unit"] != "mg/ml":
            return "incompatible_amount_dimensions"
        if (n["amount_role"], d["amount_role"]) != ("target_mass_estimate", "total_protein_mass_estimate"):
            return "amount_role_mismatch"
        if any(row["amount_kind"] not in ("measured", "estimated") for row in (n, d)):
            return "amount_kind_unresolved"
        relation = inputs["stock_relationship"]
        if relation != "same":
            return ("different_stocks" if relation in ("different", "not_applicable") else
                    "stock_relationship_" + relation)
    else:
        if n["unit"] != "uM":
            return "incompatible_amount_dimensions"
        if any(row["amount_role"] != "nominal_molecule_amount" for row in (n, d)):
            return "amount_role_mismatch"
        if any(row["amount_kind"] != "nominal" for row in (n, d)):
            return "amount_kind_unresolved"
    return None


def _divide(first, second, prior_reason, zero_reason):
    reason = prior_reason or (zero_reason if second == 0 else None)
    if reason:
        return None, reason
    try:
        value = first / second
        if not math.isfinite(value) or value == 0 and first != 0:
            return None, "numerical_model_range"
        return value, None
    except ArithmeticError:
        return None, "numerical_model_range"


def _propagated(matrix, gradient):
    try:
        value = math.fsum(gradient[i] * matrix[i][j] * gradient[j]
                         for i in range(2) for j in range(2))
        if not math.isfinite(value):
            return None, "numerical_model_range"
        if value < 0:
            return None, "invalid_propagated_variance"
        return value, None
    except (ArithmeticError, ValueError):
        return None, "numerical_model_range"


def populate_amount_components(inputs):
    """Populate twelve numerical components from explicitly related quantities.

    ``amount_ratio`` is numerator/denominator; signed difference is numerator
    minus denominator. The mass-denominator factor is the reciprocal alias for
    the supported same-stock target/total mass-estimate relationship, with
    strictly positive mass estimates. It is not applied to a rate here.

    Full covariance is already converted to canonical quantity units and owned
    by these ordered measurements. Difference propagation is linear. Nonlinear
    ratio propagation is first order and does not assert normality, confidence
    bounds or known variance when the supplied variance is estimated.
    """
    inputs = validate_amount_calculation_inputs(inputs)
    quantities = inputs["quantities"]
    reasons = {role: _individual_reason(quantities[role]) for role in ROLES}
    paired_reason = _pair_reason(inputs, reasons)
    rows = [quantities[role] for role in ROLES]
    n, d = (row["value"] if row else None for row in rows)
    unit = rows[0]["unit"] if rows[0] and rows[1] and rows[0]["unit"] == rows[1]["unit"] else None
    approximate = any(row and row["approximate"] for row in rows)
    conditions = ("source_role_and_pair_interpretations",)
    cells = {}
    for role, row in zip(ROLES, rows):
        cells[role + "_amount"] = _cell(None if reasons[role] else row["value"], row["unit"] if row else None,
            "source_" + role + "_amount", reason=reasons[role], approximate=bool(row and row["approximate"]),
            origin=row["origin"] if row else "derived")
        # Thresholds are retained without masquerading as point amounts.
        cells[role + "_amount"].update(threshold=row["value"] if row and row["status"] == "censored" else None,
            bound=row["bound"] if row else "none", qualification=row["qualification"] if row else "unknown")
    difference = n - d if paired_reason is None else None
    cells["amount_difference"] = _cell(difference, unit, "numerator-denominator", reason=paired_reason,
        approximate=approximate, conditional=conditions)
    ratio, ratio_reason = _divide(n, d, paired_reason, "zero_denominator_amount")
    reciprocal, reciprocal_reason = _divide(d, n, paired_reason, "zero_numerator_amount")
    cells["amount_ratio"] = _cell(ratio, "dimensionless", "numerator/denominator", reason=ratio_reason,
        approximate=approximate, conditional=conditions)
    cells["reciprocal_amount_ratio"] = _cell(reciprocal, "dimensionless", "denominator/numerator",
        reason=reciprocal_reason, approximate=approximate, conditional=conditions)
    factor_reason = ("mass_factor_not_applicable" if inputs["comparison_kind"] !=
        "stock_target_mass_estimate_over_total_mass_estimate" else reciprocal_reason)
    if factor_reason is None and (n <= 0 or d <= 0):
        factor_reason = "positive_mass_estimates_required"
    cells["conditional_mass_denominator_factor"] = _cell(None if factor_reason else reciprocal,
        "dimensionless", "reciprocal_amount_ratio_same_stock_mass_basis_alias", reason=factor_reason,
        approximate=approximate, conditional=(*conditions,
            "same_stock_rate_with_total_mass_denominator_required_before_application"))

    for name, value, reason, gradient_fn in (
        ("amount_difference", difference, paired_reason, lambda: (1., -1.)),
        ("amount_ratio", ratio, ratio_reason, lambda: (1 / d, -ratio / d)),
        ("reciprocal_amount_ratio", reciprocal, reciprocal_reason, lambda: (-reciprocal / n, 1 / n)),
    ):
        variance = None
        if reason is None and (value is None or not math.isfinite(value)):
            reason = "numerical_model_range"
        if reason is None and inputs["covariance"] is None:
            reason = "amount_covariance_unreported"
        if reason is None:
            try:
                variance, reason = _propagated(inputs["covariance"], gradient_fn())
            except ArithmeticError:
                reason = "numerical_model_range"
        nonlinear = name != "amount_difference"
        uncertainty_conditions = (*conditions, "first_order_covariance_propagation" if nonlinear else "linear_covariance_propagation")
        variance_unit = (f"({unit})^2" if unit else None) if not nonlinear else "dimensionless"
        error_unit = unit if not nonlinear else "dimensionless"
        cells[name + "_variance"] = _cell(variance, variance_unit, "J_" + name + "*covariance*J_transpose",
            reason=reason, approximate=approximate, conditional=uncertainty_conditions)
        cells[name + "_standard_uncertainty"] = _cell(math.sqrt(variance) if variance is not None else None,
            error_unit, "sqrt(" + name + "_variance)", reason=reason,
            approximate=approximate, conditional=uncertainty_conditions)
    return {"version": VERSION, "axis": "A105", "evaluation_scope": "source_amount_comparison",
        "inputs": inputs, "cells": cells, "comparison_kind": inputs["comparison_kind"],
        "variance_status": inputs["variance_status"], "covariance_origin": inputs["covariance_origin"],
        "mass_factor_alias_of": "reciprocal_amount_ratio", "mass_factor_applied_to_rate": False,
        "independent_preparation_count": None, "annotation_credit": None,
        "interpretation_limits": ["target_and_total_protein_are_different_measurands",
            "mass_fraction_estimate_is_not_automatically_validated_purity_or_active_fraction",
            "nominal_amount_ratio_is_not_amount_response_correction",
            "difference_of_target_and_total_estimates_is_not_contaminant_concentration",
            "source_amounts_do_not_establish_effect_isolation",
            "arithmetic_aliases_are_not_independent_evidence"]}


__all__ = ["VERSION", "COMPONENTS", "REASONS", "populate_amount_components"]
