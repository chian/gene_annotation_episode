"""Descriptive source binding-parameter cells, without an observation model.

The reader supplies already selected, normalized source rows. These calculations
retain IC50 and reported Hill Kd as different parameter kinds. A reported limit
permits arithmetic on its printed threshold; it does not identify a true
parameter bound or a confidence bound. Neither fit spread nor a minimum count
supplies a joint sampling model, covariance or preparation independence.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "binding_parameter_sheet_v1"
COMPONENTS = (
    "reference_parameter", "test_parameter", "reference_reported_spread",
    "test_reported_spread", "reference_relative_spread", "test_relative_spread",
    "native_parameter_ratio", "log_native_parameter_ratio",
    "source_profile_log_ratio", "source_signed_index",
)
FORMULAS = {
    "reference_parameter": "reference_row.value",
    "test_parameter": "test_row.value",
    "reference_reported_spread": "reference_row.reported_spread",
    "test_reported_spread": "test_row.reported_spread",
    "reference_relative_spread": "reference_reported_spread/abs(reference_parameter)",
    "test_relative_spread": "test_reported_spread/abs(test_parameter)",
    "native_parameter_ratio": "test_parameter/reference_parameter",
    "log_native_parameter_ratio": "ln(test_parameter)-ln(reference_parameter)",
    "source_profile_log_ratio": "applicable_joint_binding_observation_model",
    "source_signed_index": "tanh(source_profile_log_ratio/2)",
}
REASONS = (
    "missing_reference_arm", "missing_test_arm", "conflicting_source_identity",
    "ambiguous_reference_arm", "ambiguous_test_arm", "source_measurement_unavailable",
    "reported_spread_requires_point_operand", "reported_spread_unavailable",
    "nonfinite_calculation", "calculation_underflow", "two_censored_operands_unsupported",
    "comparison_context_mismatch", "binding_observation_model_unimplemented",
)
UNAVAILABLE_REASONS = REASONS
_EXTRACTION_KEYS = (
    "version", "parameter_kind", "unit", "uncertainty_basis",
    "minimum_experiment_count", "reference_rows", "test_rows",
)
_ROW_KEYS = (
    "value", "relation", "reported_spread", "origin", "source", "subject",
    "state", "experiment", "ligand",
)
_SOURCE_KEYS = (
    "source_ref", "artifact_ref", "representation", "table_id", "row_index",
    "locator", "expression",
)
_UNCERTAINTY_BASES = (
    "fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown",
)
_RELATIONS = ("eq", "gt", "ge", "lt", "le", "unreported")
_INVERSE_RELATION = {"eq": "eq", "gt": "lt", "ge": "le", "lt": "gt", "le": "ge"}
_ORIGINS = {
    "primary_table": "reported", "synthetic_fixture": "synthetic",
    "retained_visual_transcription": "visual_transcription",
}


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, keys, field):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail("closed_fields_required", field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _index(value, field):
    if type(value) is not int or value < 0:
        _fail("nonnegative_integer_offset_required", field)


def _number(value, field, *, positive=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)
    if positive and value <= 0:
        _fail("positive_parameter_required", field)
    if not positive and value < 0:
        _fail("nonnegative_spread_required", field)


def _source(source, origin, field):
    _keys(source, _SOURCE_KEYS, field)
    for name in ("source_ref", "artifact_ref", "table_id", "expression"):
        _text(source[name], field + "." + name)
    representation = source["representation"]
    if not isinstance(representation, str) or representation not in _ORIGINS:
        _fail("unknown_source_representation", field + ".representation")
    if origin != _ORIGINS[representation]:
        _fail("source_origin_mismatch", field + ".origin")
    _index(source["row_index"], field + ".row_index")
    locator = source["locator"]
    if representation == "retained_visual_transcription":
        _keys(locator, ("original_source_ref", "original_artifact_ref", "image_region"),
              field + ".locator")
        for name in ("original_source_ref", "original_artifact_ref"):
            _text(locator[name], field + ".locator." + name)
        region = locator["image_region"]
        if not isinstance(region, list) or len(region) != 4:
            _fail("image_region_required", field + ".locator.image_region")
        for index, coordinate in enumerate(region):
            _index(coordinate, f"{field}.locator.image_region[{index}]")
        if region[0] >= region[2] or region[1] >= region[3]:
            _fail("nonempty_image_region_required", field + ".locator.image_region")
    else:
        _keys(locator, ("row_index", "column"), field + ".locator")
        _index(locator["row_index"], field + ".locator.row_index")
        _text(locator["column"], field + ".locator.column")


def _serialized(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _physical_identity(row):
    source = row["source"]
    if source["representation"] == "retained_visual_transcription":
        # Copies of an original image cell still refer to one physical cell.
        return _serialized(source["locator"])
    return _serialized({name: source[name] for name in
                        ("source_ref", "artifact_ref", "table_id", "row_index", "locator")})


def _validate(extraction):
    _keys(extraction, _EXTRACTION_KEYS, "extraction")
    if extraction["version"] != "binding_parameter_extraction_v1":
        _fail("unsupported_extraction_version", "version")
    if extraction["parameter_kind"] not in ("ic50", "reported_hill_kd"):
        _fail("unsupported_parameter_kind", "parameter_kind")
    if extraction["unit"] != "nM":
        _fail("normalized_nM_required", "unit")
    if extraction["uncertainty_basis"] not in _UNCERTAINTY_BASES:
        _fail("unsupported_uncertainty_basis", "uncertainty_basis")
    count = extraction["minimum_experiment_count"]
    if count is not None and (type(count) is not int or count <= 0):
        _fail("positive_integer_count_required", "minimum_experiment_count")
    result = deepcopy(extraction)
    for arm in ("reference_rows", "test_rows"):
        rows = extraction[arm]
        if not isinstance(rows, list):
            _fail("rows_required", arm)
        retained, seen = [], set()
        for index, row in enumerate(rows):
            field = f"{arm}[{index}]"
            _keys(row, _ROW_KEYS, field)
            for name in ("subject", "state", "experiment", "ligand"):
                _text(row[name], field + "." + name)
            if row["relation"] not in _RELATIONS:
                _fail("unknown_censor_relation", field + ".relation")
            if row["relation"] == "unreported":
                if row["value"] is not None or row["reported_spread"] is not None:
                    _fail("unreported_value_and_spread_must_be_null", field)
            else:
                _number(row["value"], field + ".value", positive=True)
                if row["reported_spread"] is not None:
                    if row["relation"] != "eq":
                        _fail("censored_spread_unsupported", field + ".reported_spread")
                    _number(row["reported_spread"], field + ".reported_spread")
            _source(row["source"], row["origin"], field + ".source")
            # Only exact copies collapse. Equal values at different locations
            # do not become one measurement or an inferred replicate sample.
            full = _serialized(row)
            if full not in seen:
                seen.add(full)
                retained.append(deepcopy(row))
        result[arm] = retained
    return result


def _conflicting_identities(extraction):
    readings, conflicts = {}, set()
    for row in extraction["reference_rows"] + extraction["test_rows"]:
        identity = _physical_identity(row)
        reading = tuple(row[name] for name in
            ("value", "relation", "reported_spread", "subject", "state", "experiment", "ligand"))
        if identity in readings and readings[identity] != reading:
            conflicts.add(identity)
        readings[identity] = reading
    return conflicts


def _select(rows, arm, conflicts):
    if not rows:
        return None, f"missing_{arm}_arm", False
    if any(_physical_identity(row) in conflicts for row in rows):
        return None, "conflicting_source_identity", True
    # The original visual cell identifies the observation. Transcription
    # wrappers and array positions are retained above without becoming extra
    # numerical operands. Conflicting readings were rejected before selection.
    operands = {}
    for index, row in enumerate(rows):
        key = (_physical_identity(row) if row["source"]["representation"] ==
               "retained_visual_transcription" else index)
        operands.setdefault(key, row)
    if len(operands) != 1:
        return None, f"ambiguous_{arm}_arm", True
    row = next(iter(operands.values()))
    if row["relation"] == "unreported":
        return row, "source_measurement_unavailable", False
    return row, None, False


def _cell(value, unit, formula, *, relation="eq", reason=None, conflict=False,
          origin="derived"):
    limit = value is not None and relation != "eq"
    return {
        "value": value, "relation": relation if value is not None else "unreported",
        "unit": unit,
        "status": ("conflicting" if conflict else "unavailable" if value is None
                   else "reported_limit" if limit else "populated"),
        "formula": formula, "origin": origin, "unavailable_reason": reason,
        "bound_kind": "reported_limit_arithmetic" if limit else None,
        "confidence_bound": None, "parameter_identification_bound": None,
    }


def _divide(numerator, denominator):
    try:
        value = numerator / denominator
    except (ArithmeticError, ValueError):
        return None, "nonfinite_calculation"
    if not math.isfinite(value):
        return None, "nonfinite_calculation"
    if value == 0 and numerator != 0:
        return None, "calculation_underflow"
    return value, None


def populate_binding_contrast(extraction):
    """Populate finite point/one-limit descriptions of a selected comparison.

    Ratio and log ratio are alternative representations of one contrast, not
    independent evidence. Limits retain their printed direction and threshold
    meaning. Sampling uncertainties, preparation independence and annotation
    credit are never inferred. Partial arm cells survive unavailable contrasts.
    This interface compares ligands within one subject, state and experiment;
    different comparison contexts retain raw arm cells without a ratio or log.
    """
    extracted = _validate(extraction)
    conflicts = _conflicting_identities(extracted)
    selected = {}
    cells = {}
    for arm in ("reference", "test"):
        row, reason, conflict = _select(extracted[arm + "_rows"], arm, conflicts)
        selected[arm] = row, reason, conflict
        value = row["value"] if row is not None and reason is None else None
        cells[arm + "_parameter"] = _cell(value, "nM", FORMULAS[arm + "_parameter"],
            relation=row["relation"] if row is not None else "unreported",
            reason=reason, conflict=conflict)
        spread_reason = reason
        if spread_reason is None and row["relation"] != "eq":
            spread_reason = "reported_spread_requires_point_operand"
        if spread_reason is None and row["reported_spread"] is None:
            spread_reason = "reported_spread_unavailable"
        spread = row["reported_spread"] if spread_reason is None else None
        cells[arm + "_reported_spread"] = _cell(spread, "nM",
            FORMULAS[arm + "_reported_spread"], reason=spread_reason, conflict=conflict)
        relative, relative_reason = (None, spread_reason) if spread_reason else _divide(spread, abs(value))
        cells[arm + "_relative_spread"] = _cell(relative, "fraction",
            FORMULAS[arm + "_relative_spread"],
            reason=relative_reason, conflict=conflict)

    reference, reference_reason, reference_conflict = selected["reference"]
    test, test_reason, test_conflict = selected["test"]
    reason = reference_reason or test_reason
    if reason is None and any(reference[name] != test[name]
                              for name in ("subject", "state", "experiment")):
        reason = "comparison_context_mismatch"
    pair_conflict = reference_conflict or test_conflict
    relation = "unreported"
    ratio = log_ratio = None
    ratio_reason = log_reason = reason
    if reason is None:
        a, b = reference["value"], test["value"]
        ar, br = reference["relation"], test["relation"]
        if ar != "eq" and br != "eq":
            ratio_reason = log_reason = "two_censored_operands_unsupported"
        else:
            relation = br if ar == "eq" else _INVERSE_RELATION[ar]
            ratio, ratio_reason = _divide(b, a)
            # The log survives even when division overflows or underflows.
            log_ratio = math.log(b) - math.log(a)
            if log_ratio == 0 and b != a:
                # Recover nearby unequal operands lost in subtraction of logs.
                log_ratio = math.log1p((b - a) / a)
            if not math.isfinite(log_ratio):
                log_ratio, log_reason = None, "nonfinite_calculation"
            elif log_ratio == 0 and b != a:
                log_ratio, log_reason = None, "calculation_underflow"
    cells["native_parameter_ratio"] = _cell(ratio, "fraction",
        FORMULAS["native_parameter_ratio"], relation=relation,
        reason=ratio_reason, conflict=pair_conflict)
    cells["log_native_parameter_ratio"] = _cell(log_ratio, "dimensionless",
        FORMULAS["log_native_parameter_ratio"], relation=relation,
        reason=log_reason, conflict=pair_conflict)
    for name in ("source_profile_log_ratio", "source_signed_index"):
        cells[name] = _cell(None, "dimensionless", FORMULAS[name],
            reason="binding_observation_model_unimplemented",
            origin="proposed" if name == "source_signed_index" else "derived")
    return {
        "version": VERSION, "parameter_kind": extracted["parameter_kind"], "unit": "nM",
        "reference_rows": extracted["reference_rows"], "test_rows": extracted["test_rows"],
        "uncertainty_basis": extracted["uncertainty_basis"],
        "minimum_experiment_count": extracted["minimum_experiment_count"],
        "independent_preparation_count": None, "cells": cells, "annotation_credit": None,
    }


__all__ = ["VERSION", "COMPONENTS", "FORMULAS", "REASONS", "UNAVAILABLE_REASONS",
           "populate_binding_contrast"]
