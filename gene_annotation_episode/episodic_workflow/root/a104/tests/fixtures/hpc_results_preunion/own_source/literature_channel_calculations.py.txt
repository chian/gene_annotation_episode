"""Pure electrical components for an explicitly interpreted source experiment.

Chord conductance combines current magnitude and driving voltage. It is neither
an I--V slope nor a reliability weight. Charge equivalents are not a specified
ion's flux. Source interpretation, source custody and later credit have other
owners; this module has no I/O or episode state.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a105_channel_components_v1"
PRIMITIVE_ORDER = ("current", "applied_voltage", "reversal_voltage")
QUANTITIES = (*PRIMITIVE_ORDER, "reported_conductance")
CURRENT_KINDS = ("signed_current", "current_step_magnitude", "unknown", "conflicting")
ARRANGEMENT_RELATIONS = ("same_electrical_arrangement_supported",
                         "different_electrical_arrangements", "unknown", "conflicting")
COMPONENTS = (*QUANTITIES, "absolute_driving_voltage", "chord_conductance",
              "charge_equivalent_rate", "chord_conductance_variance",
              "chord_conductance_standard_uncertainty")
UNITS = {"current": "pA", "applied_voltage": "mV", "reversal_voltage": "mV",
         "reported_conductance": "pS", "absolute_driving_voltage": "mV",
         "chord_conductance": "pS", "charge_equivalent_rate": "elementary_charge_equivalents_per_s",
         "chord_conductance_variance": "pS_squared", "chord_conductance_standard_uncertainty": "pS"}
MEANINGS = {
    "current": "Source current or current-step magnitude under the declared baseline; not an isolated ion flux.",
    "applied_voltage": "Source applied voltage under its retained sign convention.",
    "reversal_voltage": "Source reversal voltage under its own retained ionic conditions.",
    "reported_conductance": "Conductance reported by the source, separate from the defined chord calculation.",
    "absolute_driving_voltage": "Magnitude of applied minus applicable reversal voltage; the chord denominator.",
    "chord_conductance": "Current magnitude divided by driving-voltage magnitude under supported condition applicability; not differential conductance.",
    "charge_equivalent_rate": "Magnitude of electrical charge flow in elementary-charge equivalents per second; not ion identity, pore count or molecular turnover.",
    "chord_conductance_variance": "Conditional first-order variance of the defined chord from the supplied full primitive covariance.",
    "chord_conductance_standard_uncertainty": "Square root of conditional first-order chord variance; no confidence level is implied.",
}
SECTIONS = {name: "electrical_measurement" for name in QUANTITIES}
SECTIONS.update(absolute_driving_voltage="conditions_and_normalization",
                chord_conductance="conditions_and_normalization",
                charge_equivalent_rate="charge_attribution_limit",
                chord_conductance_variance="measurement_uncertainty",
                chord_conductance_standard_uncertainty="measurement_uncertainty")
ELEMENTARY_CHARGE_C = Fraction("1.602176634e-19")
_FIELDS = ("values", "exact_values", "measurement_keys", "current_kind",
           "arrangement_relation", "covariance", "variance_status", "origin")
_CHORD_CONDITIONS = ("reversal_condition_applicable_to_current_voltage",
                     "defined_chord_not_differential_conductance")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _finite(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def _float(value):
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) and (result != 0 or value == 0) else None


def _fraction(value, field):
    _keys(value, ("numerator", "denominator"), field)
    import re
    if (not isinstance(value["numerator"], str)
            or not re.fullmatch(r"-?[0-9]+", value["numerator"])
            or not isinstance(value["denominator"], str)
            or not re.fullmatch(r"[1-9][0-9]*", value["denominator"])):
        _fail("exact_rational_required", field)
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _validate(inputs):
    _keys(inputs, _FIELDS, "inputs")
    values = {}
    for field in ("values", "exact_values", "measurement_keys"):
        _keys(inputs[field], QUANTITIES, field)
    for name in QUANTITIES:
        value, exact = inputs["values"][name], inputs["exact_values"][name]
        if value is None:
            if exact is not None:
                _fail("exact_value_without_measurement", "exact_values." + name)
            values[name] = None
        else:
            _finite(value, "values." + name)
            values[name] = Fraction(str(value)) if exact is None else _fraction(exact, "exact_values." + name)
            if _float(values[name]) != value:
                _fail("exact_value_mismatch", "exact_values." + name)
        key = inputs["measurement_keys"][name]
        if key is not None and (not isinstance(key, str) or not key.strip()):
            _fail("nonempty_identity_required", "measurement_keys." + name)
    for field, allowed in (("current_kind", CURRENT_KINDS),
                            ("arrangement_relation", ARRANGEMENT_RELATIONS),
                            ("variance_status", ("known", "estimated", "unknown")),
                            ("origin", ("reported", "derived", "graph_derived", "synthetic"))):
        if not isinstance(inputs[field], str) or inputs[field] not in allowed:
            _fail("unsupported_" + field, field)
    if (inputs["current_kind"] == "current_step_magnitude"
            and values["current"] is not None and values["current"] < 0):
        _fail("nonnegative_current_magnitude_required", "values.current")
    if values["reported_conductance"] is not None and values["reported_conductance"] < 0:
        _fail("nonnegative_reported_conductance_required", "values.reported_conductance")

    matrix = None
    if inputs["covariance"] is not None:
        raw = inputs["covariance"]
        if (not isinstance(raw, list) or len(raw) != 3
                or any(not isinstance(row, list) or len(row) != 3 for row in raw)):
            _fail("three_by_three_covariance_required", "covariance")
        for i, row in enumerate(raw):
            for j, value in enumerate(row):
                _finite(value, f"covariance[{i}][{j}]")
        matrix = [[Fraction(str(value)) for value in row] for row in raw]
        if any(matrix[i][j] != matrix[j][i] for i in range(3) for j in range(3)):
            _fail("symmetric_covariance_required", "covariance")
        a, b, c = matrix[0]
        _, d, e = matrix[1]
        _, _, f = matrix[2]
        if any(value < 0 for value in (a, d, f, a*d-b*b, a*f-c*c, d*f-e*e,
                                      a*d*f+2*b*c*e-a*e*e-d*c*c-f*b*b)):
            _fail("positive_semidefinite_covariance_required", "covariance")
    for i, name in enumerate(QUANTITIES):
        for j, other in enumerate(QUANTITIES[:i]):
            key = inputs["measurement_keys"][name]
            if key is None or key != inputs["measurement_keys"][other]:
                continue
            if UNITS[name] != UNITS[other]:
                _fail("shared_measurement_dimension_mismatch", "measurement_keys." + name)
            if values[name] != values[other]:
                _fail("shared_measurement_value_mismatch", "measurement_keys." + name)
            if matrix is not None and i < 3 and j < 3 and (
                    matrix[i] != matrix[j] or any(row[i] != row[j] for row in matrix)):
                _fail("shared_measurement_covariance_mismatch", "covariance")
    return values, matrix


def _cell(name, value, formula, dependencies, inputs, *, reason=None,
          conditional=(), origin="derived"):
    if value is not None and reason is None:
        value = _float(value)
        if value is None:
            reason = "numerical_model_range"
    if reason is not None:
        value = None
    return {"value": value, "unit": UNITS[name], "status": "unavailable" if value is None else "populated",
            "formula": formula, "origin": origin, "unavailable_reason": reason,
            "section": SECTIONS[name], "meaning": MEANINGS[name],
            "conditional_on": list(conditional), "operand_roles": list(dependencies),
            "measurement_keys": list(dict.fromkeys(inputs["measurement_keys"][role]
                for role in dependencies if inputs["measurement_keys"][role] is not None))}


def _reason(inputs, values, roles):
    if any(values[role] is None for role in roles):
        return "electrical_inputs_not_supplied"
    relation = inputs["arrangement_relation"]
    return {"same_electrical_arrangement_supported": None,
            "different_electrical_arrangements": "different_electrical_arrangements",
            "unknown": "reversal_condition_applicability_not_supplied",
            "conflicting": "reversal_condition_applicability_conflicting"}[relation]


def populate_channel_components(inputs):
    """Populate canonical electrical cells, retaining separate physical owners.

    Inputs use pA, mV, mV and pS. Optional exact decimal-rational operands retain
    source precision through conversion. A supported arrangement means reversal
    conditions apply to the current/voltage calculation; it does NOT assert one
    acquisition, one bilayer, independent errors or an ohmic slope model.

    Covariance is in primitive order (current[pA], applied[mV], reversal[mV]).
    First-order uncertainty is unavailable at zero current's absolute-value
    cusp or zero driving voltage. Unknown covariance never means independent
    errors. Each derived cell has its original measurement dependencies.
    """
    values, matrix = _validate(inputs)
    cells = {name: _cell(name, values[name], name, (name,), inputs,
                reason="electrical_measurement_not_supplied" if values[name] is None else None,
                origin=inputs["origin"]) for name in QUANTITIES}
    dv_reason = _reason(inputs, values, ("applied_voltage", "reversal_voltage"))
    dv = None if dv_reason else values["applied_voltage"] - values["reversal_voltage"]
    cells["absolute_driving_voltage"] = _cell("absolute_driving_voltage", None if dv is None else abs(dv),
        "abs(applied_voltage-reversal_voltage)", ("applied_voltage", "reversal_voltage"), inputs,
        reason=dv_reason, conditional=_CHORD_CONDITIONS[:1])
    reason = _reason(inputs, values, PRIMITIVE_ORDER)
    if reason is None and inputs["current_kind"] in ("unknown", "conflicting"):
        reason = "current_kind_not_supplied" if inputs["current_kind"] == "unknown" else "current_kind_conflicting"
    if reason is None and dv == 0:
        reason = "zero_driving_voltage"
    current = values["current"]
    conductance = None if reason else 1000*abs(current)/abs(dv)
    cells["chord_conductance"] = _cell("chord_conductance", conductance,
        "1000*abs(current)/(abs(applied_voltage-reversal_voltage))", PRIMITIVE_ORDER, inputs,
        reason=reason, conditional=_CHORD_CONDITIONS)
    charge_reason = "electrical_measurement_not_supplied" if current is None else None
    if charge_reason is None and inputs["current_kind"] in ("unknown", "conflicting"):
        charge_reason = "current_kind_not_supplied" if inputs["current_kind"] == "unknown" else "current_kind_conflicting"
    charge = None if charge_reason else abs(current)*Fraction("1e-12")/ELEMENTARY_CHARGE_C
    cells["charge_equivalent_rate"] = _cell("charge_equivalent_rate", charge,
        "abs(current)*1e-12/1.602176634e-19", ("current",), inputs,
        reason=charge_reason, conditional=("electrical_charge_equivalents_only",))

    variance_reason = reason
    if variance_reason is None and current == 0:
        variance_reason = "absolute_current_not_differentiable_at_zero"
    if variance_reason is None and matrix is None:
        variance_reason = "primitive_covariance_not_supplied"
    if variance_reason is None and any(inputs["measurement_keys"][name] is None for name in PRIMITIVE_ORDER):
        variance_reason = "primitive_measurement_identity_not_supplied"
    if variance_reason is None and inputs["variance_status"] == "unknown":
        variance_reason = "primitive_variance_status_unknown"
    variance = uncertainty = None
    if variance_reason is None:
        sign_i, sign_d = 1 if current > 0 else -1, 1 if dv > 0 else -1
        gradient = (Fraction(1000*sign_i, 1)/abs(dv),
                    -1000*abs(current)*sign_d/(dv*dv),
                    1000*abs(current)*sign_d/(dv*dv))
        variance = sum(gradient[i]*matrix[i][j]*gradient[j] for i in range(3) for j in range(3))
        with localcontext() as context:
            context.prec = 80
            uncertainty = (Decimal(variance.numerator)/Decimal(variance.denominator)).sqrt()
    conditions = (*_CHORD_CONDITIONS, "first_order_covariance_propagation")
    cells["chord_conductance_variance"] = _cell("chord_conductance_variance", variance,
        "J*covariance*J_transpose; J=[1000*sign(I)/abs(D),-1000*abs(I)*sign(D)/D^2,1000*abs(I)*sign(D)/D^2]; D=V-E",
        PRIMITIVE_ORDER, inputs, reason=variance_reason, conditional=conditions)
    cells["chord_conductance_standard_uncertainty"] = _cell("chord_conductance_standard_uncertainty", uncertainty,
        "sqrt(chord_conductance_variance)", PRIMITIVE_ORDER, inputs,
        reason=variance_reason, conditional=conditions)
    return {"version": VERSION, "primitive_order": list(PRIMITIVE_ORDER),
            "inputs": deepcopy(inputs), "cells": cells,
            "interpretation_limits": ["no_ion_flux_attribution", "no_pore_or_polypeptide_normalization",
                "no_independent_preparation_count", "no_overall_reliability_grade", "no_annotation_credit"]}


__all__ = ["VERSION", "PRIMITIVE_ORDER", "QUANTITIES", "CURRENT_KINDS", "ARRANGEMENT_RELATIONS",
           "COMPONENTS", "UNITS", "MEANINGS", "SECTIONS", "ELEMENTARY_CHARGE_C", "populate_channel_components"]
