"""Pure source-only perturbation/restoration point components for A106.

The caller identifies the experimental design, endpoint calibration, actual
measurement identities and the bounds on nuisance effects. This calculator
does not infer those facts, acquire evidence, transfer annotations, or compute
annotation credit. The proposed source index is a convention, not a probability.
Joint uncertainty is unreported in this finite first interface.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a106_source_restoration_v1"
PRIMITIVE_ORDER = ("W", "K", "R", "A_reference", "A_restored", "B_pert", "B_rest")
COMPONENTS = (
    "reference_endpoint", "perturbed_endpoint", "restored_endpoint",
    "perturbation_difference", "symmetric_effect", "restoration_fraction_raw",
    "restoration_agreement", "amount_comparability", "perturbation_isolation",
    "restoration_isolation", "effect_isolation", "reference_restoration_index",
    "reference_index_lower", "reference_index_upper",
)
_ENDPOINT_ROLES = ("W", "K", "R", "B_pert", "B_rest")
_EXPOSURE_ROLES = ("A_reference", "A_restored")
_RESTORATION_DESIGNS = (
    "native_deletion_restoration", "selective_perturbation_restoration",
)
_ENUMS = {
    "endpoint_unit": ("events_per_100000_cells", "fraction", "CFU_per_mL", "minutes", "per_min", "unreported"),
    "exposure_unit": ("molecules_per_cell", "normalized_signal", "fraction", "mg_per_mL", "unreported"),
    "design": (*_RESTORATION_DESIGNS, "cas_free_reconstitution", "variant_replacement", "other_explicit", "unknown", "conflicting"),
    "measurement_status": ("validated_ratio_scale", "qualitative_only", "unknown", "conflicting"),
    "same_endpoint_scope": ("yes", "no", "unknown", "conflicting"),
    "amount_role": ("nuisance", "intended_change", "unknown"),
    "origin": ("reported", "graph_derived", "derived", "synthetic"),
}
_ENDPOINT_CONDITIONS = ("validated_ratio_scale", "same_endpoint_scope", "distinct_role_measurements")
_RESTORATION_CONDITIONS = (*_ENDPOINT_CONDITIONS, "explicit_restoration_design")
REASONS = (
    "endpoint_unreported", "numerical_model_range", "ratio_scale_not_validated",
    "same_endpoint_not_established", "restoration_design_not_established",
    "endpoint_inputs_unreported", "role_measurement_identity_unreported",
    "role_measurement_not_distinct", "zero_endpoint_sum",
    "zero_perturbation_difference", "amount_is_intended_change",
    "nuisance_amount_role_unreported", "amount_inputs_unreported",
    "zero_amount_denominator", "effect_bound_unreported",
    "zero_effect_denominator", "orientation_unreported",
    "joint_uncertainty_unreported",
)
CONDITIONAL_CODES = (
    *_RESTORATION_CONDITIONS, "nuisance_amount_comparison", "supplied_effect_bound",
    "supplied_effect_bounds", "source_restoration_convention",
)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _fields(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _validate(inputs):
    _fields(inputs, ("values", "measurement_keys", *_ENUMS, "orientation"), "inputs")
    for field in ("values", "measurement_keys"):
        _fields(inputs[field], PRIMITIVE_ORDER, field)
    for role in PRIMITIVE_ORDER:
        value = inputs["values"][role]
        if value is not None:
            try:
                valid = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                valid = False
            if not valid:
                _fail("finite_number_required", "values." + role)
            if value < 0:
                _fail("nonnegative_value_required", "values." + role)
        key = inputs["measurement_keys"][role]
        if key is not None and (not isinstance(key, str) or not key.strip()):
            _fail("nonempty_identity_required", "measurement_keys." + role)
    for field, allowed in _ENUMS.items():
        if not isinstance(inputs[field], str) or inputs[field] not in allowed:
            _fail("unsupported_" + field, field)
    orientation = inputs["orientation"]
    if orientation is not None and (type(orientation) is not int or orientation not in (-1, 1)):
        _fail("signed_orientation_required", "orientation")
    for unit_field, roles in (("endpoint_unit", _ENDPOINT_ROLES), ("exposure_unit", _EXPOSURE_ROLES)):
        if inputs[unit_field] == "unreported" and any(inputs["values"][role] is not None for role in roles):
            _fail("observed_unit_required", unit_field)
    if inputs["measurement_status"] == "qualitative_only" and any(
            inputs["values"][role] is not None for role in ("W", "K", "R")):
        _fail("qualitative_endpoint_has_no_numeric_values", "values")
    # Identity equality is an explicit caller declaration. Equal numeric values
    # under different keys do not imply a shared observation or independence.
    units = {role: inputs["exposure_unit"] if role in _EXPOSURE_ROLES else inputs["endpoint_unit"]
             for role in PRIMITIVE_ORDER}
    seen = {}
    for role in PRIMITIVE_ORDER:
        key = inputs["measurement_keys"][role]
        if key is None:
            continue
        if key in seen:
            other = seen[key]
            if inputs["values"][role] != inputs["values"][other]:
                _fail("shared_measurement_value_mismatch", "measurement_keys." + role)
            if units[role] != units[other]:
                _fail("shared_measurement_unit_mismatch", "measurement_keys." + role)
        else:
            seen[key] = role


def _cell(value, unit, formula, *, reason=None, origin="derived", conditional=()):
    if value is not None and reason is None:
        try:
            converted = float(value)
        except (OverflowError, ValueError):
            converted = None
        if converted is None or not math.isfinite(converted) or (converted == 0 and value != 0):
            value, reason = None, "numerical_model_range"
        else:
            value = converted
    return {"value": value, "unit": unit,
            "status": "unavailable" if value is None else "populated",
            "formula": formula, "origin": origin,
            "unavailable_reason": reason, "conditional_on": list(conditional)}


def _endpoint_reason(inputs, roles, *, restoration=False):
    if inputs["measurement_status"] != "validated_ratio_scale":
        return "ratio_scale_not_validated"
    if inputs["same_endpoint_scope"] != "yes":
        return "same_endpoint_not_established"
    if restoration and inputs["design"] not in _RESTORATION_DESIGNS:
        return "restoration_design_not_established"
    if any(inputs["values"][role] is None for role in roles):
        return "endpoint_inputs_unreported"
    keys = [inputs["measurement_keys"][role] for role in roles]
    if any(key is None for key in keys):
        return "role_measurement_identity_unreported"
    if len(set(keys)) != len(keys):
        return "role_measurement_not_distinct"
    return None


def _clip(value):
    return max(Fraction(0), min(Fraction(1), value))


def populate_source_restoration(inputs):
    """Populate native endpoints and conditional source-only point components.

    W/K/R are reference, perturbed and restored endpoint observations. A values
    describe one nominated nuisance amount comparison outside the intended
    change; B values are supplied bounds in endpoint units on alternative
    contributions to the perturbation/restoration effects. Bounds are never
    inferred from absent controls. Orientation +/-1 specifies the assertion's
    direction and affects only the final signed source index.

    All intermediate arithmetic uses exact rationals of the supplied finite
    numbers. Each final cell independently reports a range failure if it cannot
    be represented as a finite nonzero float. A failing raw fraction does not
    erase a representable clipped agreement. No uncertainty interval or
    independent replication claim follows from these point calculations.
    """
    _validate(inputs)
    values = {role: None if value is None else Fraction(value)
              for role, value in inputs["values"].items()}
    cells = {}
    for role, component in zip(("W", "K", "R"), COMPONENTS[:3]):
        cells[component] = _cell(values[role], inputs["endpoint_unit"], role,
            reason="endpoint_unreported" if values[role] is None else None,
            origin=inputs["origin"])

    reason = _endpoint_reason(inputs, ("W", "K"))
    difference = theta = None
    theta_reason = reason
    if reason is None:
        difference = values["W"] - values["K"]
        if values["W"] + values["K"] == 0:
            theta_reason = "zero_endpoint_sum"
        else:
            theta = difference / (values["W"] + values["K"])
    cells["perturbation_difference"] = _cell(difference, inputs["endpoint_unit"], "W-K",
        reason=reason, conditional=_ENDPOINT_CONDITIONS)
    cells["symmetric_effect"] = _cell(theta, "dimensionless", "(W-K)/(W+K)",
        reason=theta_reason, conditional=_ENDPOINT_CONDITIONS)

    restoration_reason = _endpoint_reason(inputs, ("W", "K", "R"), restoration=True)
    raw = agreement = None
    if restoration_reason is None:
        if difference == 0:
            restoration_reason = "zero_perturbation_difference"
        else:
            raw = (values["R"] - values["K"]) / difference
            agreement = _clip(1 - abs(values["R"] - values["W"]) / abs(difference))
    cells["restoration_fraction_raw"] = _cell(raw, "dimensionless", "(R-K)/(W-K)",
        reason=restoration_reason, conditional=_RESTORATION_CONDITIONS)
    cells["restoration_agreement"] = _cell(agreement, "dimensionless", "clip(1-abs(R-W)/abs(W-K),0,1)",
        reason=restoration_reason, origin="proposed", conditional=_RESTORATION_CONDITIONS)

    amount = None
    amount_reason = None
    if inputs["amount_role"] != "nuisance":
        amount_reason = "amount_is_intended_change" if inputs["amount_role"] == "intended_change" else "nuisance_amount_role_unreported"
    elif any(values[role] is None for role in _EXPOSURE_ROLES):
        amount_reason = "amount_inputs_unreported"
    elif max(values[role] for role in _EXPOSURE_ROLES) == 0:
        amount_reason = "zero_amount_denominator"
    else:
        amount = min(values[role] for role in _EXPOSURE_ROLES) / max(values[role] for role in _EXPOSURE_ROLES)
    cells["amount_comparability"] = _cell(amount, "dimensionless", "min(A_reference,A_restored)/max(A_reference,A_restored)",
        reason=amount_reason, origin="proposed", conditional=("nuisance_amount_comparison",))

    isolation_values, isolation_reasons = [], []
    for component, bound, contrast, prerequisite, conditions in (
        ("perturbation_isolation", "B_pert", difference, reason, _ENDPOINT_CONDITIONS),
        ("restoration_isolation", "B_rest", None if restoration_reason else values["R"]-values["K"], restoration_reason, _RESTORATION_CONDITIONS),
    ):
        isolated = None
        isolation_reason = prerequisite
        if isolation_reason is None:
            if values[bound] is None:
                isolation_reason = "effect_bound_unreported"
            elif contrast == 0:
                isolation_reason = "zero_effect_denominator"
            else:
                isolated = _clip(1 - values[bound] / abs(contrast))
        cells[component] = _cell(isolated, "dimensionless",
            "clip(1-B_pert/abs(W-K),0,1)" if bound == "B_pert" else "clip(1-B_rest/abs(R-K),0,1)",
            reason=isolation_reason, origin="proposed", conditional=(*conditions, "supplied_effect_bound"))
        isolation_values.append(isolated)
        isolation_reasons.append(isolation_reason)
    isolation_reason = next((item for item in isolation_reasons if item is not None), None)
    isolation = min(isolation_values) if isolation_reason is None else None
    cells["effect_isolation"] = _cell(isolation, "dimensionless", "min(perturbation_isolation,restoration_isolation)",
        reason=isolation_reason, origin="proposed", conditional=(*_RESTORATION_CONDITIONS, "supplied_effect_bounds"))

    index_reason = next((item for item in (theta_reason, restoration_reason, amount_reason, isolation_reason) if item is not None), None)
    if index_reason is None and inputs["orientation"] is None:
        index_reason = "orientation_unreported"
    index = inputs["orientation"] * theta * agreement * amount * isolation if index_reason is None else None
    cells["reference_restoration_index"] = _cell(index, "dimensionless",
        "orientation*symmetric_effect*restoration_agreement*amount_comparability*effect_isolation",
        reason=index_reason, origin="proposed", conditional=("source_restoration_convention",))
    for component in COMPONENTS[-2:]:
        cells[component] = _cell(None, "dimensionless", "joint_uncertainty_bound(reference_restoration_index)",
            reason="joint_uncertainty_unreported", origin="proposed", conditional=("source_restoration_convention",))
    return {"version": VERSION, "inputs": deepcopy(inputs),
            "primitive_order": list(PRIMITIVE_ORDER), "cells": cells}


def populate_source_summary_restoration(extraction, *, origin):
    """Versioned summary extension; the original point calculator stays exact."""
    from .literature_perturbation_summary import populate_summary_restoration
    return populate_summary_restoration(extraction, origin=origin)


__all__ = ["VERSION", "PRIMITIVE_ORDER", "COMPONENTS", "REASONS",
           "CONDITIONAL_CODES", "populate_source_restoration", "populate_source_summary_restoration"]
