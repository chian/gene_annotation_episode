"""Pure, condition-qualified experimental partner-removal components.

Input identities and condition completeness are supplied source interpretations.
Matching them is not a scientific-validity proof. Bounds here describe only
nonnegative censor domains conditional on reported means; reported spread is
retained without a sampling model or conversion to a confidence interval.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from itertools import product
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "literature_partner_components_v1"
INPUT_VERSION = "literature_partner_inputs_v1"
COMPONENTS = (
    "reference_rate", "omitted_rate", "addback_rate", "partner_loss",
    "partner_loss_fraction", "addback_gain", "addback_fraction",
    "restored_reference_fraction",
)
_ROLES = ("reference", "omitted", "addback")
_UNITS = ("pmol/min/mg", "nmol/min/mg", "umol/min/mg", "per_min", "per_s",
          "uM/min", "nM/min", "unreported")
_POINT = "point_only_not_uncertainty"
_DOMAIN = "conditional_input_domain_not_CI"
_ARM_FIELDS = (
    "subject_ref", "partner_ref", "partner_state", "endpoint_ref",
    "normalization_ref", "unit", "conditions", "measurement",
)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _closed(value, keys, field):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail("closed_fields_required", field)


def _text(value, field, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_identity_required", field)


def _enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail("unsupported_value", field)


def _number(value, field, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) not in (int, float) or (
            type(value) is float and not math.isfinite(value)):
        _fail("finite_number_required", field)
    if value < 0:
        _fail("nonnegative_value_required", field)


def _validate(inputs):
    _closed(inputs, ("version", "arms"), "inputs")
    if inputs["version"] != INPUT_VERSION:
        _fail("unsupported_input_version", "version")
    _closed(inputs["arms"], _ROLES, "arms")
    seen = {}
    for role, arm in inputs["arms"].items():
        path = "arms." + role
        if arm is None:
            continue
        _closed(arm, _ARM_FIELDS, path)
        for key in ("subject_ref", "partner_ref", "endpoint_ref", "normalization_ref"):
            _text(arm[key], path + "." + key, nullable=True)
        _enum(arm["partner_state"], ("present", "absent", "unreported"), path + ".partner_state")
        _enum(arm["unit"], _UNITS, path + ".unit")
        conditions = arm["conditions"]
        _closed(conditions, ("coverage", "factors"), path + ".conditions")
        _enum(conditions["coverage"], ("complete", "partial", "unreported"), path + ".conditions.coverage")
        factors = conditions["factors"]
        if not isinstance(factors, list):
            _fail("factor_list_required", path + ".conditions.factors")
        names = set()
        for index, factor in enumerate(factors):
            fp = f"{path}.conditions.factors[{index}]"
            _closed(factor, ("factor", "level", "unit"), fp)
            for key in ("factor", "unit"):
                _text(factor[key], fp + "." + key)
            if factor["factor"] in names:
                _fail("duplicate_condition_factor", fp + ".factor")
            names.add(factor["factor"])
            level = factor["level"]
            if level is not None:
                if isinstance(level, str):
                    _text(level, fp + ".level")
                elif type(level) not in (int, float) or (
                        type(level) is float and not math.isfinite(level)):
                    _fail("finite_condition_level_required", fp + ".level")
        if conditions["coverage"] == "unreported" and factors:
            _fail("unreported_conditions_have_factors", path + ".conditions")
        if conditions["coverage"] == "complete" and (
                not factors or any(f["level"] is None for f in factors)):
            _fail("complete_conditions_require_known_factors", path + ".conditions")
        measurement = arm["measurement"]
        _closed(measurement, ("measurement_id", "status", "value", "origin", "spread"), path + ".measurement")
        _text(measurement["measurement_id"], path + ".measurement.measurement_id", nullable=True)
        _enum(measurement["status"], ("observed", "upper_bound", "unreported"), path + ".measurement.status")
        _enum(measurement["origin"], ("reported", "graph_derived", "synthetic"), path + ".measurement.origin")
        _number(measurement["value"], path + ".measurement.value", nullable=True)
        if measurement["status"] == "unreported":
            if measurement["value"] is not None:
                _fail("unreported_measurement_has_value", path + ".measurement.value")
        elif measurement["value"] is None:
            _fail("observed_value_required", path + ".measurement.value")
        if arm["unit"] == "unreported" and measurement["status"] != "unreported":
            _fail("observed_unit_required", path + ".unit")
        spread = measurement["spread"]
        _closed(spread, ("kind", "magnitude"), path + ".measurement.spread")
        _enum(spread["kind"], ("SD", "SEM", "CI", "unspecified", "unreported"), path + ".measurement.spread.kind")
        _number(spread["magnitude"], path + ".measurement.spread.magnitude", nullable=True)
        if (spread["kind"] == "unreported") != (spread["magnitude"] is None):
            _fail("spread_kind_magnitude_mismatch", path + ".measurement.spread")
        identity = measurement["measurement_id"]
        if identity is not None:
            signature = (measurement["value"], measurement["status"], arm["unit"])
            if identity in seen and seen[identity] != signature:
                _fail("shared_measurement_conflict", path + ".measurement.measurement_id")
            seen[identity] = signature


def _factor_differences(first, second):
    left = {f["factor"]: f for f in first["conditions"]["factors"]}
    right = {f["factor"]: f for f in second["conditions"]["factors"]}
    different = set()
    for name in set(left) & set(right):
        a, b = left[name], right[name]
        if a["unit"] != b["unit"] or (
                a["level"] is not None and b["level"] is not None and a["level"] != b["level"]):
            different.add(name)
    return sorted(different)


def _check(first, omitted):
    if first is None or omitted is None:
        return {"status": "unresolved", "differing_factors": [],
                "unavailable_reason": "arm_unreported"}
    differences = _factor_differences(first, omitted)

    def result(status, reason):
        return {"status": status, "differing_factors": differences,
                "unavailable_reason": reason}

    # A known changed condition remains visible even if normalization or some
    # other relationship is also unknown. Unknown factor levels do not differ.
    if differences:
        return result("different", "nonpartner_conditions_differ")
    for key, stem in (("subject_ref", "subject"), ("partner_ref", "partner"),
                      ("endpoint_ref", "endpoint"), ("normalization_ref", "normalization")):
        if first[key] is None or omitted[key] is None:
            return result("unresolved", stem + "_unreported")
        if first[key] != omitted[key]:
            return result("different", stem + "_mismatch")
    if first["unit"] == "unreported" or omitted["unit"] == "unreported":
        return result("unresolved", "unit_unreported")
    if first["unit"] != omitted["unit"]:
        return result("different", "unit_mismatch")
    if first["partner_state"] != "present" or omitted["partner_state"] != "absent":
        return result("unresolved", "partner_presence_not_established")
    scopes = [{f["factor"] for f in arm["conditions"]["factors"]}
              for arm in (first, omitted)]
    if scopes[0] != scopes[1]:
        return result("unresolved", "condition_factor_scope_unresolved")
    if any(a["conditions"]["coverage"] != "complete" for a in (first, omitted)):
        return result("unresolved", "conditions_incomplete")
    keys = [a["measurement"]["measurement_id"] for a in (first, omitted)]
    if None in keys:
        return result("unresolved", "measurement_identity_unreported")
    if keys[0] == keys[1]:
        return result("unresolved", "role_measurement_not_distinct")
    return result("matched", None)


def _unit(arm):
    return None if arm is None or arm["unit"] == "unreported" else arm["unit"]


def _cell(unit, origin, *, value=None, lower=None, upper=None, bounded=False, reason=None):
    if reason is not None:
        status = "unavailable"
    elif value is None:
        status, reason = "bounded", "censored_point_unreported"
    else:
        status = "populated"
    return {"value": value, "lower": lower, "upper": upper, "unit": unit,
            "origin": origin, "bound_kind": _DOMAIN if bounded else _POINT,
            "status": status, "unavailable_reason": reason}


def _float(exact, direction=0):
    value = float(exact)
    if not math.isfinite(value) or (direction == 0 and value == 0 and exact != 0):
        raise OverflowError
    if direction < 0 and Fraction(value) > exact:
        value = math.nextafter(value, -math.inf)
    if direction > 0 and Fraction(value) < exact:
        value = math.nextafter(value, math.inf)
    if not math.isfinite(value):
        raise OverflowError
    return value


def _native(arm):
    if arm is None:
        return _cell(None, None, reason="arm_unreported")
    measurement, unit = arm["measurement"], _unit(arm)
    if measurement["status"] == "unreported":
        return _cell(unit, measurement["origin"], reason="measurement_unreported")
    value = measurement["value"]
    if measurement["status"] == "upper_bound":
        return _cell(unit, measurement["origin"], lower=0, upper=value, bounded=True)
    # Preserve the exact native numeric literal (including large integers).
    return _cell(unit, measurement["origin"], value=value, lower=value, upper=value)


def _domain(arm):
    if arm is None or arm["measurement"]["status"] == "unreported":
        return None
    value = Fraction(arm["measurement"]["value"])
    return (Fraction(0), value) if arm["measurement"]["status"] == "upper_bound" else (value, value)


def _calculate(arms, unit, function, *, prerequisite=None, denominator=None):
    if prerequisite is not None:
        return _cell(unit, "derived", reason=prerequisite)
    domains = [_domain(arm) for arm in arms]
    if any(domain is None for domain in domains):
        return _cell(unit, "derived", reason="measurement_unreported")
    vertices = list(product(*[tuple(set(domain)) for domain in domains]))
    if denominator == "positive_reference" and domains[0][0] <= 0:
        return _cell(unit, "derived", reason="nonpositive_reference_domain")
    if denominator == "nonzero_loss":
        low = domains[0][0] - domains[1][1]
        high = domains[0][1] - domains[1][0]
        if low <= 0 <= high:
            return _cell(unit, "derived", reason="zero_or_straddling_loss_domain")
    exact = [function(*values) for values in vertices]
    low, high = min(exact), max(exact)
    bounded = any(a["measurement"]["status"] == "upper_bound" for a in arms)
    try:
        value = _float(low) if low == high else None
        return _cell(unit, "derived", value=value, lower=_float(low, -1),
                     upper=_float(high, 1), bounded=bounded)
    except OverflowError:
        return _cell(unit, "derived", bounded=bounded, reason="numerical_model_range")


def populate_partner_components(inputs):
    """Populate native rates and condition-qualified removal/addback components.

    No statistical independence follows from distinct measurement identities.
    Censored variables share the same primitive at every occurrence, including
    both occurrences of the omitted-arm measurement in the restoration ratio.
    """
    _validate(inputs)
    w, o, a = (inputs["arms"][role] for role in _ROLES)
    checks = {"reference_omitted": _check(w, o), "addback_omitted": _check(a, o)}
    loss_reason = checks["reference_omitted"]["unavailable_reason"]
    gain_reason = checks["addback_omitted"]["unavailable_reason"]
    if w is not None and a is not None:
        wk, ak = (arm["measurement"]["measurement_id"] for arm in (w, a))
        if wk is not None and wk == ak:
            gain_reason = "role_measurement_not_distinct"
    triple_reason = loss_reason or gain_reason
    if triple_reason is None:
        keys = [arm["measurement"]["measurement_id"] for arm in (w, o, a)]
        if len(set(keys)) != 3:
            triple_reason = "role_measurement_not_distinct"
    loss_unit = _unit(w) if _unit(w) == _unit(o) else None
    gain_unit = _unit(a) if _unit(a) == _unit(o) else None
    cells = dict(zip(COMPONENTS[:3], (_native(w), _native(o), _native(a))))
    cells["partner_loss"] = _calculate((w, o), loss_unit, lambda w, o: w - o,
                                       prerequisite=loss_reason)
    cells["partner_loss_fraction"] = _calculate((w, o), "dimensionless",
        lambda w, o: (w - o) / w, prerequisite=loss_reason,
        denominator="positive_reference")
    cells["addback_gain"] = _calculate((a, o), gain_unit, lambda a, o: a - o,
                                       prerequisite=gain_reason)
    cells["addback_fraction"] = _calculate((w, o, a), "dimensionless",
        lambda w, o, a: (a - o) / (w - o), prerequisite=triple_reason,
        denominator="nonzero_loss")
    cells["restored_reference_fraction"] = _calculate((w, o, a), "dimensionless",
        lambda w, o, a: (a - o) / w, prerequisite=triple_reason,
        denominator="positive_reference")
    return {"version": VERSION, "inputs": deepcopy(inputs), "cells": cells,
            "comparison_checks": checks}


__all__ = ["VERSION", "COMPONENTS", "populate_partner_components"]
