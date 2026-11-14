"""Numerical A105 recovery components from a source-bound pair.

Recovery, bias and inverse correction share their original operands. They are
not independent experiments, calibration probabilities or annotation credit.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .domain import identity, validate_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_calibration_recovery_inputs import VERSION as INPUT_VERSION, NUMBER_ROLES

VERSION = "a105_calibration_recovery_components_v1"
COMPONENTS = ("nominal", "measured", "signed_difference", "recovery", "relative_bias",
              "percent_bias", "inverse_recovery", "reported_measured_spread", "measured_sd",
              "measured_cv", "reported_recovery", "displayed_minus_reported_recovery",
              "correction_for_other_measurement", "recovery_variance")
FORMULAS = {"nominal": "source_expected_quantity", "measured": "source_measured_quantity",
    "signed_difference": "measured-nominal", "recovery": "measured/nominal",
    "relative_bias": "measured/nominal-1", "percent_bias": "100*(measured/nominal-1)",
    "inverse_recovery": "nominal/measured", "reported_measured_spread": "source_measured_spread",
    "measured_sd": "source_measured_spread_when_explicitly_SD", "measured_cv": "measured_SD/measured",
    "reported_recovery": "source_reported_recovery_as_fraction",
    "displayed_minus_reported_recovery": "measured/nominal-reported_recovery",
    "correction_for_other_measurement": "requires_linked_target_measurement_and_applicable_recovery",
    "recovery_variance": "requires_measured_and_nominal_uncertainty_and_covariance"}
REASONS = ("nominal_not_supplied", "measured_not_supplied", "shared_unit_not_supplied",
    "nonpositive_nominal", "nonpositive_measured", "measured_spread_not_supplied",
    "spread_kind_not_SD", "reported_recovery_not_supplied", "reported_recovery_unit_not_supplied",
    "control_dimension_mismatch", "no_target_measurement_supplied",
    "denominator_uncertainty_and_covariance_not_supplied", "numerical_model_range")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _q(raw):
    if not isinstance(raw, dict) or set(raw) != {"numerator", "denominator"}:
        _fail("exact_rational_required", "exact_value")
    try:
        if not all(isinstance(raw[k], str) for k in raw):
            raise ValueError()
        numerator, denominator = int(raw["numerator"]), int(raw["denominator"])
        if denominator <= 0:
            raise ValueError()
        return Fraction(numerator, denominator)
    except (ValueError, ZeroDivisionError) as error:
        raise ExperimentalContractError("exact_rational_required", "exact_value") from error


def _float(value):
    try:
        number = float(value)
        if not math.isfinite(number) or number == 0 and value != 0:
            raise ValueError()
    except (ArithmeticError, ValueError):
        return None
    return number


def _validate(extraction):
    fields = {"version", "source_ref", "artifact_ref", "source_kind", "literals", "control_kind",
              "applicability", "spread_kind", "shared_unit", "reported_recovery_unit", "observations",
              "input_origins", "source_refs", "interpretation_limits"}
    if not isinstance(extraction, dict) or set(extraction) != fields or extraction["version"] != INPUT_VERSION:
        _fail("calibration_extraction_required", "extraction")
    from .literature_calibration_recovery_inputs import (SOURCE_KINDS, LITERAL_FIELDS, CONTROL_KINDS,
        APPLICABILITIES, SPREAD_KINDS, calibration_recovery_extraction_schema, _parse_unit, _unit_text)
    validate_schema(extraction, calibration_recovery_extraction_schema())
    if extraction["source_ref"] not in extraction["source_refs"]:
        _fail("calibration_source_record_mismatch", "source_refs")
    def witnesses(value):
        if isinstance(value, dict):
            if {"source_ref", "representation", "start", "end", "quote", "artifact_ref"} == set(value):
                if (value["end"] - value["start"] != len(value["quote"].encode("utf-8"))
                        or value["source_ref"] not in extraction["source_refs"]):
                    _fail("calibration_witness_record_mismatch", "witness")
            else:
                for child in value.values():
                    witnesses(child)
        elif isinstance(value, list):
            for child in value:
                witnesses(child)
    witnesses(extraction)
    if extraction["source_kind"] not in SOURCE_KINDS:
        _fail("unsupported_source_kind", "source_kind")
    origin = {"primary_source": "reported", "retained_extraction": "derived", "synthetic_fixture": "synthetic"}[extraction["source_kind"]]
    if extraction["input_origins"] != [origin]:
        _fail("input_origin_mismatch", "input_origins")
    if not isinstance(extraction["literals"], dict) or set(extraction["literals"]) != set(LITERAL_FIELDS):
        _fail("calibration_literal_fields_required", "literals")
    for name, values in (("control_kind", CONTROL_KINDS), ("applicability", APPLICABILITIES), ("spread_kind", SPREAD_KINDS)):
        item = extraction[name]
        if (not isinstance(item, dict) or set(item) != {"kind", "value", "witnesses"}
                or item["kind"] != "source_interpretation" or item["value"] not in values
                or not isinstance(item["witnesses"], list)):
            _fail("calibration_interpretation_required", name)
        unique = {(w["artifact_ref"], w["start"], w["end"]) for w in item["witnesses"]}
        required = 2 if item["value"] == "conflicting" else 0 if item["value"] in ("unknown",) else 1
        if len(unique) < required:
            _fail("interpretation_witness_required", name)
    shared_unit = extraction["shared_unit"]
    if shared_unit is not None:
        if (shared_unit["raw_unit"] != shared_unit["witness"]["quote"]
                or _parse_unit(shared_unit["raw_unit"]) != (shared_unit["unit"], _q(shared_unit["multiplier"]))):
            _fail("calibration_unit_record_mismatch", "shared_unit")
    recovery_unit = extraction["reported_recovery_unit"]
    if recovery_unit is not None:
        raw = " ".join(_unit_text(recovery_unit["raw_unit"]).lower().split())
        allowed = {"fraction": ("fraction", "dimensionless", "1"), "percent": ("%", "percent", "per cent")}
        expected_multiplier = Fraction(1, 100) if recovery_unit["value"] == "percent" else Fraction(1)
        if (recovery_unit["raw_unit"] != recovery_unit["witness"]["quote"] or raw not in allowed[recovery_unit["value"]]
                or _q(recovery_unit["multiplier"]) != expected_multiplier):
            _fail("calibration_unit_record_mismatch", "reported_recovery_unit")
    for name, literal in extraction["literals"].items():
        if literal is not None and literal["value"] != literal["witness"]["quote"]:
            _fail("calibration_literal_record_mismatch", name)
    observations = extraction["observations"]
    if not isinstance(observations, dict) or set(observations) != set(NUMBER_ROLES):
        _fail("calibration_observations_required", "observations")
    for role, observation in observations.items():
        if observation is None:
            continue
        if observation["origin"] != origin:
            _fail("input_origin_mismatch", role)
        native = _q(observation["native_exact_value"])
        try:
            token = Fraction(observation["raw_number"].replace("−", "-"))
        except (ValueError, ZeroDivisionError) as error:
            raise ExperimentalContractError("calibration_number_record_mismatch", role) from error
        if token != native or observation["native_value"] != _float(native) or _float(native) is None:
            _fail("calibration_number_record_mismatch", role)
        if role == "measured_spread" and native < 0:
            _fail("nonnegative_source_number_required", role)
        unit = extraction["reported_recovery_unit"] if role == "reported_recovery" else shared_unit
        normalized = None if unit is None else native * _q(unit["multiplier"])
        if (observation["value"] != (None if normalized is None else _float(normalized))
                or observation["exact_value"] != (None if normalized is None else {
                    "numerator": str(normalized.numerator), "denominator": str(normalized.denominator)})
                or observation["unit"] != (None if unit is None else unit["unit"])):
            _fail("calibration_conversion_record_mismatch", role)
        selector = observation["selector"]
        witness = selector["witness"]
        if not 0 <= selector["number_start"] < selector["number_end"] <= len(witness["quote"]):
            _fail("calibration_measurement_binding_mismatch", role)
        start = witness["start"] + len(witness["quote"][:selector["number_start"]].encode("utf-8"))
        end = witness["start"] + len(witness["quote"][:selector["number_end"]].encode("utf-8"))
        if (observation["number_start_bytes"] != start or observation["number_end_bytes"] != end
                or witness["quote"][selector["number_start"]:selector["number_end"]] != observation["raw_number"]
                or observation["measurement_key"] != identity("literature_measurement", {
                    "artifact_ref": witness["artifact_ref"], "number_start": start, "number_end": end})):
            _fail("calibration_measurement_binding_mismatch", role)


def populate_calibration_recovery(extraction):
    """Populate numerical sections without applying recovery to another experiment.

    An unresolved control role does not erase a supported numerical pair: its
    ratio remains descriptive, with explicit interpretation scope. A known
    control/dimension mismatch withholds interpreted recovery and bias; original
    measured quantities and their difference survive. No uncertainty of a ratio
    is manufactured from only numerator SD. No normality or independence follows.
    """
    _validate(extraction)
    data = deepcopy(extraction)
    observations = data["observations"]
    unit = None if data["shared_unit"] is None else data["shared_unit"]["unit"]
    control = data["control_kind"]["value"]
    mismatch = ((control == "reporter_standard" and unit not in (None, "nmol"))
                or (control == "enzyme_activity_spike" and unit not in (None, "nmol/min")))
    scope_reason = "control_dimension_mismatch" if mismatch else "control_kind_" + control if control in ("unknown", "conflicting") else None

    def value(role):
        item = observations[role]
        return None if item is None or item["exact_value"] is None else _q(item["exact_value"])

    def missing(role):
        if observations[role] is None:
            return role + "_not_supplied"
        if observations[role]["exact_value"] is None:
            return "reported_recovery_unit_not_supplied" if role == "reported_recovery" else "shared_unit_not_supplied"
        return None

    cells = {}
    def cell(name, val, output_unit, roles, *, reason=None, reported=False):
        numeric = None if val is None else _float(val)
        if val is not None and numeric is None:
            reason = "numerical_model_range"
        keys = list(dict.fromkeys(observations[r]["measurement_key"] for r in roles if observations[r] is not None))
        cells[name] = {"value": numeric, "unit": output_unit, "status": "populated" if numeric is not None else "unavailable",
            "origin": data["input_origins"][0] if reported else "derived", "input_origins": list(data["input_origins"]),
            "unavailable_reason": None if numeric is not None else reason, "formula": FORMULAS[name],
            "exact_value": None if numeric is None else {"numerator": str(val.numerator), "denominator": str(val.denominator)},
            "input_measurement_keys": keys, "conditional_on": ["source_role_assignments"]}

    n, m, sd, reported = (value(k) for k in NUMBER_ROLES)
    cell("nominal", n, unit, ("nominal",), reason=missing("nominal"), reported=True)
    cell("measured", m, unit, ("measured",), reason=missing("measured"), reported=True)
    pair_reason = missing("nominal") or missing("measured")
    cell("signed_difference", None if pair_reason else m-n, unit, ("nominal", "measured"), reason=pair_reason)
    ratio_reason = pair_reason or ("nonpositive_nominal" if n <= 0 else None) or ("control_dimension_mismatch" if mismatch else None)
    ratio = None if ratio_reason else m/n
    cell("recovery", ratio, "fraction", ("nominal", "measured"), reason=ratio_reason)
    cell("relative_bias", None if ratio is None else ratio-1, "fraction", ("nominal", "measured"), reason=ratio_reason)
    cell("percent_bias", None if ratio is None else 100*(ratio-1), "percent", ("nominal", "measured"), reason=ratio_reason)
    inverse_reason = ratio_reason or ("nonpositive_measured" if m <= 0 else None)
    cell("inverse_recovery", None if inverse_reason else n/m, "fraction", ("nominal", "measured"), reason=inverse_reason)
    cell("reported_measured_spread", sd, unit, ("measured_spread",), reason=missing("measured_spread"), reported=True)
    sd_reason = missing("measured_spread") or ("spread_kind_not_SD" if data["spread_kind"]["value"] != "SD" else None)
    cell("measured_sd", None if sd_reason else sd, unit, ("measured_spread",), reason=sd_reason, reported=True)
    cv_reason = sd_reason or missing("measured") or ("nonpositive_measured" if m <= 0 else None)
    cell("measured_cv", None if cv_reason else sd/m, "fraction", ("measured_spread", "measured"), reason=cv_reason)
    cell("reported_recovery", reported, "fraction", ("reported_recovery",), reason=missing("reported_recovery"), reported=True)
    discrepancy_reason = ratio_reason or missing("reported_recovery")
    cell("displayed_minus_reported_recovery", None if discrepancy_reason else ratio-reported,
         "fraction", ("nominal", "measured", "reported_recovery"), reason=discrepancy_reason)
    cell("correction_for_other_measurement", None, None, ("nominal", "measured"), reason="no_target_measurement_supplied")
    cell("recovery_variance", None, "fraction_squared", ("nominal", "measured", "measured_spread"),
         reason="denominator_uncertainty_and_covariance_not_supplied")
    return {"version": VERSION, "axis": "A105", "scope": "source_recovery_control",
            "extraction": data, "cells": cells, "section": "calibration_validity" if control == "reporter_standard" else
            "matrix_activity_response" if control == "enzyme_activity_spike" else "recovery_control_role_unresolved",
            "interpretation_scope_unavailable_reason": scope_reason,
            "precision_components": ["reported_measured_spread", "measured_sd", "measured_cv"],
            "qualifications": [*data["interpretation_limits"], "recovery_bias_and_inverse_share_original_operands",
                "no_overall_reliability_grade", "no_annotation_credit"], "annotation_credit": None}


__all__ = ["VERSION", "COMPONENTS", "FORMULAS", "REASONS", "populate_calibration_recovery"]
