"""Detached integrity checks for saved native kinetic selections and results.

No source bytes, reader/calculator functions, Store, model or arithmetic on
scientific measurements are used. Original-operation authentication is owned by
the repository. These checks retain the original scientific interpretations.
"""
from copy import deepcopy
import hashlib
import json
import math

from .domain import canonical, identity
from .literature_experimental_contracts import ExperimentalContractError
from .literature_kinetic_calculations import (
    VERSION as CALC_VERSION, INPUT_VERSION, COMPONENTS, FORMULAS, PARAMETER_UNITS,
    REASONS, INPUT_UNAVAILABLE_REASONS, CONDITIONAL_CODES,
)
from .literature_kinetic_inputs import (
    VERSION as EXTRACTION_VERSION, SELECTION_VERSION, SUBJECT_FIELDS, CONTEXT_FIELDS,
    COMPARISON_VALUES, QUALIFICATIONS, DEPENDENCY_RELEASES, SOURCE_KINDS,
    COUNT_STATUSES, COUNT_REASONS, COUNT_NOTATIONS, COUNT_RELATIONS,
)

VERSION = "a105_kinetic_saved_validation_v3"
WITNESS = ("source_ref", "representation", "start", "end", "quote")
LOCATOR = ("source_ref", "artifact_ref", "representation", "start", "end")
UNCERTAINTY = ("statistic", "magnitude", "interval", "confidence_level", "count",
    "repetition_basis", "estimate_basis")
OPERAND = ("parameter_kind", "unit", "value", "status", "relation", "approximate", "origin",
    "measurement_id", "physical_measurement_id", "subject", "context", "uncertainty", "source", "unavailable_reason")
CELL = ("value", "unit", "status", "formula", "origin", "unavailable_reason", "approximate",
    "conditional_on", "threshold", "relation")


def _fail(field):
    raise ExperimentalContractError("kinetic_saved_mismatch", field)


def _keys(value, fields, field):
    if type(value) is not dict or set(value) != set(fields):
        _fail(field)


def _equal(left, right, field):
    try:
        equal = canonical(left) == canonical(right)
    except (ValueError, TypeError, OverflowError):
        equal = False
    if not equal:
        _fail(field)


def _text(value, field, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value.strip():
        _fail(field)


def _enum(value, values, field):
    if type(value) is not str or value not in values:
        _fail(field)


def _number(value, field, nullable=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail(field)


def witnesses(value):
    if isinstance(value, dict):
        if set(value) == {*WITNESS, "artifact_ref"}:
            yield value
        else:
            for child in value.values():
                yield from witnesses(child)
    elif isinstance(value, list):
        for child in value:
            yield from witnesses(child)


def _witness(selected, saved, field):
    if selected is None:
        _equal(saved, None, field)
        return
    _keys(selected, WITNESS, field)
    _keys(saved, (*WITNESS, "artifact_ref"), field)
    _equal(selected, {k: saved[k] for k in WITNESS}, field)
    for name in ("source_ref", "artifact_ref", "quote"):
        _text(saved[name], field)
    _enum(saved["representation"], ("original", "text"), field)
    if (type(saved["start"]) is not int or type(saved["end"]) is not int
            or saved["start"] < 0 or saved["end"] <= saved["start"]
            or len(saved["quote"].encode("utf-8")) != saved["end"] - saved["start"]):
        _fail(field)


def _meaning(selected, saved, allowed, field):
    _keys(selected, ("value", "witnesses"), field)
    _keys(saved, ("value", "witnesses"), field)
    _enum(saved["value"], allowed, field)
    _equal(selected["value"], saved["value"], field)
    if type(selected["witnesses"]) is not list or type(saved["witnesses"]) is not list:
        _fail(field)
    if len(selected["witnesses"]) != len(saved["witnesses"]):
        _fail(field)
    for a, b in zip(selected["witnesses"], saved["witnesses"]):
        _witness(a, b, field)
    count = len({tuple(w[k] for k in LOCATOR) for w in saved["witnesses"]})
    minimum = 2 if saved["value"] == "conflicting" else 0 if saved["value"] in (
        "unknown", "unreported", "unspecified") else 1
    if count < minimum:
        _fail(field)


def _numeric_selection(selected, saved, field):
    if selected is None:
        _equal(saved, None, field)
        return
    _keys(selected, ("witness", "number_start", "number_end"), field)
    _keys(saved, ("selector", "raw_number", "value", "relation", "approximate"), field)
    selector = saved["selector"]
    _keys(selector, ("witness", "number_start", "number_end"), field)
    _witness(selected["witness"], selector["witness"], field)
    for k in ("number_start", "number_end"):
        if type(selector[k]) is not int or selector[k] != selected[k]:
            _fail(field)
    start, end = selector["number_start"], selector["number_end"]
    if not 0 <= start < end <= len(selector["witness"]["quote"]):
        _fail(field)
    _equal(saved["raw_number"], selector["witness"]["quote"][start:end], field)
    _number(saved["value"], field)
    _enum(saved["relation"], ("point", "lt", "le", "gt", "ge"), field)
    if type(saved["approximate"]) is not bool:
        _fail(field)


def _count_selection(selected, saved, field):
    """Authenticate saved associations without interpreting words again."""
    if selected is None:
        _equal(saved, None, field)
        return
    _keys(selected, ("witness", "number_start", "number_end"), field)
    _keys(saved, ("selector", "raw_number", "value", "relation", "approximate",
        "notation", "status", "unavailable_reason"), field)
    selector = saved["selector"]
    _keys(selector, ("witness", "number_start", "number_end"), field)
    _witness(selected["witness"], selector["witness"], field)
    for k in ("number_start", "number_end"):
        if type(selector[k]) is not int or selector[k] != selected[k]:
            _fail(field)
    start, end = selector["number_start"], selector["number_end"]
    if not 0 <= start < end <= len(selector["witness"]["quote"]):
        _fail(field)
    _equal(saved["raw_number"], selector["witness"]["quote"][start:end], field)
    _enum(saved["notation"], COUNT_NOTATIONS, field)
    _enum(saved["relation"], COUNT_RELATIONS, field)
    _enum(saved["status"], COUNT_STATUSES[1:], field)
    if saved["approximate"] is not None and type(saved["approximate"]) is not bool:
        _fail(field)
    if saved["value"] is not None and type(saved["value"]) is not int:
        _fail(field)
    reasons = {"exact": None, "qualified": "exact_count_qualified", "range_or_alternatives": "count_range_or_alternatives",
        "unsupported": "unsupported_count_literal", "not_positive": "positive_count_required"}
    _equal(saved["unavailable_reason"], reasons[saved["status"]], field)
    status, value = saved["status"], saved["value"]
    if status in ("exact", "qualified"):
        if value is None or value <= 0 or saved["notation"] == "unsupported":
            _fail(field)
        if type(saved["approximate"]) is not bool:
            _fail(field)
        if status == "exact" and (saved["relation"] != "point" or saved["approximate"]):
            _fail(field)
        if status == "qualified" and saved["relation"] == "point" and not saved["approximate"]:
            _fail(field)
    elif status == "not_positive":
        if value is None or value > 0 or saved["notation"] == "unsupported":
            _fail(field)
    elif value is not None or saved["relation"] != "unresolved" or saved["approximate"] is not None:
        _fail(field)
    if status == "unsupported" and saved["notation"] != "unsupported":
        _fail(field)


def _unit(selected, saved, field):
    if selected is None:
        _equal(saved, None, field)
        return
    _keys(saved, ("witness", "raw_unit", "canonical_unit", "multiplier", "unavailable_reason"), field)
    _witness(selected, saved["witness"], field)
    _equal(saved["raw_unit"], saved["witness"]["quote"], field)
    if saved["canonical_unit"] not in (*PARAMETER_UNITS.values(), None):
        _fail(field)
    _number(saved["multiplier"], field, True)
    if saved["unavailable_reason"] not in (None, "unsupported_source_kinetic_unit"):
        _fail(field)


def _uncertainty_values(value, field):
    _keys(value, UNCERTAINTY, field)
    _enum(value["statistic"], ("sd", "sem", "ci", "unspecified", "unreported"), field)
    _number(value["magnitude"], field, True)
    if value["magnitude"] is not None and value["magnitude"] < 0:
        _fail(field)
    interval = value["interval"]
    if interval is not None:
        if type(interval) is not list or len(interval) != 2:
            _fail(field)
        for point in interval:
            _number(point, field)
        if interval[0] > interval[1]:
            _fail(field)
    level = value["confidence_level"]
    _number(level, field, True)
    if level is not None and not 0 < level < 1:
        _fail(field)
    if (value["statistic"] == "ci" and value["magnitude"] is not None
            or value["statistic"] != "ci" and (interval is not None or level is not None)
            or value["statistic"] == "unreported" and value["magnitude"] is not None):
        _fail(field)
    if value["count"] is not None and (type(value["count"]) is not int or value["count"] < 1):
        _fail(field)
    _enum(value["repetition_basis"], ("biological_preparations", "technical_measurements", "unspecified"), field)
    _enum(value["estimate_basis"], ("fit_to_averaged_curve", "between_fitted_parameters", "unknown"), field)


def _uncertainty(selected, saved, parameter_unit, field):
    _keys(selected, ("statistic", "magnitude", "interval", "unit", "unit_relationship",
        "confidence_level", "count", "repetition_basis", "estimate_basis"), field)
    _keys(saved, ("meanings", "magnitude", "interval", "unit", "effective_unit", "confidence_level",
        "count", "canonical", "unavailable_reason"), field)
    meanings = {"statistic": ("sd", "sem", "ci", "unspecified", "unreported"),
        "unit_relationship": ("same_as_parameter", "explicit_unit", "unknown"),
        "repetition_basis": ("biological_preparations", "technical_measurements", "unspecified"),
        "estimate_basis": ("fit_to_averaged_curve", "between_fitted_parameters", "unknown")}
    _keys(saved["meanings"], meanings, field)
    for k, allowed in meanings.items():
        _meaning(selected[k], saved["meanings"][k], allowed, field)
    _numeric_selection(selected["magnitude"], saved["magnitude"], field)
    _count_selection(selected["count"], saved["count"], field)
    _unit(selected["unit"], saved["unit"], field)
    relationship = saved["meanings"]["unit_relationship"]["value"]
    _equal(saved["effective_unit"], saved["unit"] if relationship == "explicit_unit" else
        parameter_unit if relationship == "same_as_parameter" else None, field)
    if selected["interval"] is None:
        _equal(saved["interval"], None, field)
    else:
        interval = saved["interval"]
        _keys(interval, ("selector", "raw_values", "values"), field)
        _keys(interval["selector"], ("witness", "lower_start", "lower_end", "upper_start", "upper_end"), field)
        _witness(selected["interval"]["witness"], interval["selector"]["witness"], field)
        for side in ("lower", "upper"):
            for suffix in ("start", "end"):
                k = side + "_" + suffix
                _equal(interval["selector"][k], selected["interval"][k], field)
            start, end = (interval["selector"][side + "_" + k] for k in ("start", "end"))
            quote = interval["selector"]["witness"]["quote"]
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(quote):
                _fail(field)
        _equal(interval["raw_values"], [interval["selector"]["witness"]["quote"][
            interval["selector"][side + "_start"]:interval["selector"][side + "_end"]]
            for side in ("lower", "upper")], field)
        if type(interval["values"]) is not list or len(interval["values"]) != 2:
            _fail(field)
        for value in interval["values"]:
            _number(value, field)
    if selected["confidence_level"] is None:
        _equal(saved["confidence_level"], None, field)
    else:
        _keys(saved["confidence_level"], ("witness", "value"), field)
        _witness(selected["confidence_level"], saved["confidence_level"]["witness"], field)
        _number(saved["confidence_level"]["value"], field)
    _uncertainty_values(saved["canonical"], field)
    for k in ("statistic", "repetition_basis", "estimate_basis"):
        _equal(saved["canonical"][k], saved["meanings"][k]["value"], field)
    _equal(saved["canonical"]["confidence_level"], saved["confidence_level"]["value"] if saved["confidence_level"] else None, field)
    _equal(saved["canonical"]["count"], saved["count"]["value"] if saved["count"] and saved["count"]["status"] == "exact" else None, field)
    if saved["unavailable_reason"] not in (None, "source_uncertainty_unit_unavailable", "source_numeric_range"):
        _fail(field)


def _validate_saved_kinetic(selection, extraction, calculation):
    """Validate associations; immutable original snapshots supply numeric truth."""
    _keys(selection, ("version", "source_ref", "source_kind", "numerator", "denominator", "comparison"), "selection")
    _equal(selection["version"], SELECTION_VERSION, "selection.version")
    _text(selection["source_ref"], "selection.source_ref")
    _enum(selection["source_kind"], SOURCE_KINDS, "selection.source_kind")
    _keys(selection["comparison"], COMPARISON_VALUES, "selection.comparison")
    _keys(extraction, ("version", "source_ref", "source_kind", "operands", "comparison",
        "calculation_inputs", "input_unavailable_reasons", "source_refs", "implementation_dependencies"), "extraction")
    if extraction["version"] not in DEPENDENCY_RELEASES:
        _fail("extraction.version")
    for k in ("source_ref", "source_kind"):
        _equal(selection[k], extraction[k], k)
    _equal(extraction["implementation_dependencies"], DEPENDENCY_RELEASES[extraction["version"]], "dependencies")
    _keys(extraction["comparison"], COMPARISON_VALUES, "comparison")
    inputs = extraction["calculation_inputs"]
    _keys(inputs, ("version", "numerator", "denominator", *COMPARISON_VALUES), "inputs")
    _equal(inputs["version"], INPUT_VERSION, "inputs.version")
    for name, allowed in COMPARISON_VALUES.items():
        _meaning(selection["comparison"][name], extraction["comparison"][name], allowed, name)
        _equal(inputs[name], extraction["comparison"][name]["value"], name)
    _keys(extraction["operands"], ("numerator", "denominator"), "operands")
    _keys(extraction["input_unavailable_reasons"], ("numerator", "denominator"), "reasons")
    for role in ("numerator", "denominator"):
        selected, saved = selection[role], extraction["operands"][role]
        if selected is None:
            _equal(saved, None, role)
            _equal(inputs[role], None, role)
            _equal(extraction["input_unavailable_reasons"][role], ["source_measurement_unreported"], role)
            continue
        _keys(selected, ("parameter_kind", "subject", "context", "measurement_identity", "measurement", "qualification", "uncertainty"), role)
        _keys(saved, ("parameter_kind", "subject", "context", "measurement_identity", "number", "unit", "qualification",
            "approximate", "source_origin", "canonical_value", "uncertainty", "calculation_operand", "unavailable_reasons"), role)
        _meaning(selected["parameter_kind"], saved["parameter_kind"], (*PARAMETER_UNITS, "unknown", "conflicting"), role)
        _meaning(selected["qualification"], saved["qualification"], QUALIFICATIONS, role)
        for group, names in (("subject", SUBJECT_FIELDS), ("context", CONTEXT_FIELDS)):
            _keys(selected[group], names, role)
            _keys(saved[group], names, role)
            for name in names:
                _witness(selected[group][name], saved[group][name], role)
        _witness(selected["measurement_identity"], saved["measurement_identity"], role)
        measurement = selected["measurement"]
        if measurement is not None:
            _keys(measurement, ("number", "unit"), role)
        _numeric_selection(measurement["number"] if measurement else None, saved["number"], role)
        _unit(measurement["unit"] if measurement else None, saved["unit"], role)
        _uncertainty(selected["uncertainty"], saved["uncertainty"], saved["unit"], role)
        if type(saved["approximate"]) is not bool:
            _fail(role)
        number = saved["number"]
        qualification = saved["qualification"]["value"]
        _equal(saved["approximate"], bool(number and number["approximate"]
            or qualification == "source_qualified_approximate"), role)
        _equal(saved["source_origin"], "synthetic" if selection["source_kind"] == "synthetic_fixture" else "reported", role)
        _number(saved["canonical_value"], role, True)
        if (type(saved["unavailable_reasons"]) is not list or any(v not in (*INPUT_UNAVAILABLE_REASONS,
                "source_parameter_kind_unknown", "source_parameter_kind_conflicting") for v in saved["unavailable_reasons"])):
            _fail(role)
        _equal(inputs[role], saved["calculation_operand"], role)
        _equal(extraction["input_unavailable_reasons"][role], saved["unavailable_reasons"], role)
        qualification_reasons = [v for v in saved["unavailable_reasons"] if v.startswith("source_operand_qualification_")]
        _equal(qualification_reasons, ["source_operand_qualification_" + qualification]
            if qualification in ("unknown", "conflicting") else [], role)
        operand = inputs[role]
        if operand is not None:
            _keys(operand, OPERAND, role)
            _enum(operand["parameter_kind"], PARAMETER_UNITS, role)
            _equal(operand["parameter_kind"], saved["parameter_kind"]["value"], role)
            _enum(operand["status"], ("point", "censored", "missing", "conflicting"), role)
            expected_status = ("conflicting" if qualification == "conflicting" else "missing"
                if saved["unavailable_reasons"] else "point" if number and number["relation"] == "point" else "censored")
            _equal(operand["status"], expected_status, role)
            _number(operand["value"], role, True)
            _equal(operand["approximate"], saved["approximate"], role)
            _enum(operand["origin"], ("reported", "calculated", "synthetic"), role)
            _equal(operand["unavailable_reason"], saved["unavailable_reasons"][0] if saved["unavailable_reasons"] else None, role)
            if operand["status"] in ("point", "censored"):
                if operand["value"] is None or operand["unavailable_reason"] is not None:
                    _fail(role)
                _equal(operand["value"], saved["canonical_value"], role)
                _equal(operand["unit"], PARAMETER_UNITS[operand["parameter_kind"]], role)
            elif operand["value"] is not None:
                _fail(role)
            if operand["unit"] not in (None, PARAMETER_UNITS[operand["parameter_kind"]]):
                _fail(role)
            expected_relations = ("eq",) if operand["status"] == "point" else ("lt", "le", "gt", "ge") if operand["status"] == "censored" else ("none",)
            _enum(operand["relation"], expected_relations, role)
            if operand["status"] in ("point", "censored"):
                if number is None:
                    _fail(role)
                _equal(operand["relation"], "eq" if number["relation"] == "point" else number["relation"], role)
            for group in ("subject", "context"):
                _equal(operand[group], {k: w["quote"] if w else None for k, w in saved[group].items()}, role)
            _equal(operand["uncertainty"], saved["uncertainty"]["canonical"], role)
            number = saved["number"]
            witness = number["selector"]["witness"] if number else saved["parameter_kind"]["witnesses"][0]
            location = {k: witness[k] for k in LOCATOR}
            if number:
                ns = number["selector"]
                location.update(start=witness["start"] + len(witness["quote"][:ns["number_start"]].encode()),
                    end=witness["start"] + len(witness["quote"][:ns["number_end"]].encode()))
            _equal(operand["source"], location, role)
            _equal(operand["measurement_id"], identity("kinetic_source_token" if number else "kinetic_unavailable_record", location), role)
            physical = saved["measurement_identity"]
            _equal(operand["physical_measurement_id"], identity("kinetic_physical_observation", {k: physical[k] for k in LOCATOR}) if physical else None, role)
    refs = extraction["source_refs"]
    if (type(refs) is not list or len(refs) != len(set(refs))
            or set(refs) != {selection["source_ref"], *(w["source_ref"] for w in witnesses(extraction))}):
        _fail("source_refs")
    _keys(calculation, ("version", "axis", "evaluation_scope", "contrast_meaning", "inputs", "model", "measurement_keys",
        "physical_measurement_ids", "cells", "variance_status", "independent_preparation_count", "annotation_credit", "interpretation_limits"), "calculation")
    for k, expected in (("version", CALC_VERSION), ("axis", "A105"), ("evaluation_scope", "source_kinetic_parameter_contrast"),
            ("contrast_meaning", "numerator_parameter_exceeds_denominator"), ("model", None), ("variance_status", "not_supplied"),
            ("independent_preparation_count", None), ("annotation_credit", None)):
        _equal(calculation[k], expected, k)
    _equal(calculation["inputs"], inputs, "calculation.inputs")
    for field in ("measurement_keys", "physical_measurement_ids"):
        _keys(calculation[field], ("numerator", "denominator"), field)
    for role in ("numerator", "denominator"):
        operand = inputs[role]
        physical = operand["physical_measurement_id"] if operand else None
        _equal(calculation["physical_measurement_ids"][role], physical, role)
        encoded = json.dumps({"version": "kinetic_estimate_identity_v1", "operand": operand},
            sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        key = "kinetic_estimate_" + hashlib.sha256(encoded.encode()).hexdigest() if physical is not None else None
        _equal(calculation["measurement_keys"][role], key, role)
    _keys(calculation["cells"], COMPONENTS, "cells")
    for name, cell in calculation["cells"].items():
        _keys(cell, CELL, name)
        _equal(cell["formula"], FORMULAS[name], name)
        _number(cell["value"], name, True)
        _number(cell["threshold"], name, True)
        if type(cell["approximate"]) is not bool:
            _fail(name)
        if cell["unit"] not in (*PARAMETER_UNITS.values(), "dimensionless", "dimensionless_squared", None):
            _fail(name)
        _enum(cell["origin"], ("reported", "calculated", "synthetic", "derived", "proposed"), name)
        _enum(cell["relation"], ("eq", "lt", "le", "gt", "ge", "none"), name)
        _equal(cell["status"], "unavailable" if cell["value"] is None else "populated", name)
        if cell["unavailable_reason"] not in (*REASONS, None):
            _fail(name)
        if (cell["unavailable_reason"] is None) != (cell["value"] is not None):
            _fail(name)
        if type(cell["conditional_on"]) is not list or any(v not in CONDITIONAL_CODES for v in cell["conditional_on"]):
            _fail(name)
    for role in ("numerator", "denominator"):
        operand = inputs[role]
        cell = calculation["cells"][role + "_parameter"]
        reason = role + "_measurement_missing" if operand is None else operand["unavailable_reason"] or {
            "point": None, "censored": "censored_measurement", "missing": "source_measurement_missing",
            "conflicting": "conflicting_measurement"}[operand["status"]]
        _equal(cell["unavailable_reason"], reason, role)
        _equal(cell["value"], operand["value"] if operand and reason is None else None, role)
        _equal(cell["unit"], operand["unit"] if operand else None, role)
        _equal(cell["origin"], operand["origin"] if operand else "derived", role)
        _equal(cell["approximate"], bool(operand and operand["approximate"]), role)
        _equal(cell["relation"], operand["relation"] if operand else "none", role)
        _equal(cell["threshold"], operand["value"] if operand and operand["status"] == "censored" else None, role)
    for name in COMPONENTS[5:]:
        _equal(calculation["cells"][name]["value"], None, name)
    return deepcopy(extraction), deepcopy(calculation)


def validate_saved_kinetic(selection, extraction, calculation):
    """Validate saved types and bindings without new scientific interpretation."""
    try:
        return _validate_saved_kinetic(selection, extraction, calculation)
    except (KeyError, TypeError, ValueError, OverflowError, UnicodeError) as error:
        if isinstance(error, ExperimentalContractError):
            raise
        raise ExperimentalContractError("kinetic_saved_mismatch", "saved") from error


__all__ = ["VERSION", "witnesses", "validate_saved_kinetic"]
