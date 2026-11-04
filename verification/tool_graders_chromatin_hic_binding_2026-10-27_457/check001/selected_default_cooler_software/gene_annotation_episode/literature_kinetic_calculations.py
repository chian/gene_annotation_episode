"""Finite source kinetic-parameter contrasts, separate from annotation credit.

Readers authenticate source selections and normalize parameter-specific units.
The investigation supplies scientific relationships and model interpretations.
This pure boundary validates their shape and performs arithmetic; it does not
prove molecular identity, protocol comparability or scientific model validity.
Cell ``conditional_on`` lists formula prerequisites, including unmet ones named
by ``unavailable_reason``; it never certifies that a model was established.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a105_kinetic_contrast_sheet_v1"
INPUT_VERSION = "a105_kinetic_contrast_inputs_v1"
MODEL_VERSION = "a105_kinetic_log_model_v1"
ROLES = ("numerator", "denominator")
PARAMETER_UNITS = {"Km": "uM", "kcat": "per_min", "catalytic_efficiency": "uM^-1min^-1"}
COMPONENTS = (
    "numerator_parameter", "denominator_parameter", "parameter_difference",
    "parameter_ratio", "log_parameter_contrast", "log_contrast_variance",
    "log_contrast_standard_uncertainty", "source_profile_log_ratio", "source_signed_index",
)
FORMULAS = {
    "numerator_parameter": "source_numerator_parameter",
    "denominator_parameter": "source_denominator_parameter",
    "parameter_difference": "numerator_parameter-denominator_parameter",
    "parameter_ratio": "numerator_parameter/denominator_parameter",
    "log_parameter_contrast": "ln(numerator_parameter)-ln(denominator_parameter)",
    "log_contrast_variance": "Cnn+Cdd-2*Cnd",
    "log_contrast_standard_uncertainty": "sqrt(Cnn+Cdd-2*Cnd)",
    "source_profile_log_ratio": "e*abs(e)/(2*V)",
    "source_signed_index": "tanh(source_profile_log_ratio/2)",
}
INPUT_UNAVAILABLE_REASONS = (
    "source_measurement_unreported", "source_kinetic_unit_unreported",
    "unsupported_source_kinetic_unit", "source_operand_qualification_unknown",
    "source_operand_qualification_conflicting", "source_numeric_range",
)
REASONS = (*INPUT_UNAVAILABLE_REASONS,
    "numerator_measurement_missing", "denominator_measurement_missing",
    "source_measurement_missing", "censored_measurement", "conflicting_measurement",
    "parameter_kind_mismatch", "subject_relationship_different",
    "subject_relationship_unknown", "subject_relationship_conflicting",
    "parameter_definition_relationship_different", "parameter_definition_relationship_unknown",
    "parameter_definition_relationship_conflicting", "mixed_substrates_unsupported",
    "substrate_arrangement_unknown", "substrate_arrangement_conflicting",
    "comparison_scope_unknown", "comparison_scope_conflicting",
    "common_conditions_not_matched", "reused_source_observation",
    "conflicting_source_observation", "zero_denominator_parameter",
    "positive_parameters_required_for_log", "kinetic_log_model_unreported",
    "covariance_status_unknown", "known_log_covariance_required",
    "kinetic_observation_model_unspecified", "approximate_parameter_model_unsupported",
    "positive_log_contrast_variance_required", "numerical_model_range",
)
CONDITIONAL_CODES = (
    "supplied_subject_and_parameter_relationships", "reported_protocol_comparison",
    "declared_common_conditions", "supplied_log_covariance", "known_normal_log_parameters",
)
_INPUT_KEYS = ("version", *ROLES, "subject_relationship", "parameter_definition_relationship",
    "substrate_arrangement", "comparison_scope", "nonintended_conditions_relationship")
_OPERAND_KEYS = ("parameter_kind", "unit", "value", "status", "relation", "approximate",
    "origin", "measurement_id", "physical_measurement_id", "subject", "context", "uncertainty",
    "source", "unavailable_reason")
_SUBJECT_KEYS = ("organism", "genotype", "molecule", "construct")
_CONTEXT_KEYS = ("substrate", "preparation", "experiment", "experimental_system",
    "conditions", "endpoint", "normalization")
_SOURCE_KEYS = ("source_ref", "artifact_ref", "representation", "start", "end")
_UNCERTAINTY_KEYS = ("statistic", "magnitude", "interval", "confidence_level", "count",
    "repetition_basis", "estimate_basis")
_MODEL_KEYS = ("version", "measurement_order", "measurement_keys", "covariance", "variance_status",
    "observation_model", "log_basis", "origin", "source")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, expected, field):
    if type(value) is not dict or set(value) != set(expected):
        _fail("closed_fields_required", field)


def _enum(value, allowed, field):
    if type(value) is not str or value not in allowed:
        _fail("unsupported_kinetic_meaning", field)


def _text(value, field, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value.strip():
        _fail("nonempty_source_token_required", field)


def _number(value, field, *, nullable=False, nonnegative=False):
    if value is None and nullable:
        return
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        _fail("finite_number_required", field)
    if nonnegative and value < 0:
        _fail("nonnegative_number_required", field)


def _source(value, field):
    _keys(value, _SOURCE_KEYS, field)
    for name in ("source_ref", "artifact_ref"):
        _text(value[name], field + "." + name)
    _enum(value["representation"], ("original", "text", "retained_transcription", "synthetic"),
          field + ".representation")
    for name in ("start", "end"):
        if type(value[name]) is not int or value[name] < 0:
            _fail("nonnegative_integer_offset_required", field + "." + name)
    if value["end"] <= value["start"]:
        _fail("nonempty_source_span_required", field)


def _uncertainty(value, field):
    _keys(value, _UNCERTAINTY_KEYS, field)
    _enum(value["statistic"], ("sd", "sem", "ci", "unspecified", "unreported"), field + ".statistic")
    _number(value["magnitude"], field + ".magnitude", nullable=True, nonnegative=True)
    interval = value["interval"]
    if interval is not None:
        if type(interval) is not list or len(interval) != 2:
            _fail("uncertainty_interval_required", field + ".interval")
        for i, point in enumerate(interval):
            _number(point, f"{field}.interval[{i}]")
        if interval[0] > interval[1]:
            _fail("ordered_uncertainty_interval_required", field + ".interval")
    level = value["confidence_level"]
    _number(level, field + ".confidence_level", nullable=True)
    if level is not None and not 0 < level < 1:
        _fail("confidence_level_between_zero_and_one_required", field + ".confidence_level")
    if value["statistic"] == "ci":
        if value["magnitude"] is not None:
            _fail("ci_endpoints_not_halfwidth_required", field + ".magnitude")
    elif interval is not None or level is not None:
        _fail("ci_statistic_required", field)
    if value["statistic"] == "unreported" and value["magnitude"] is not None:
        _fail("unreported_uncertainty_must_be_null", field + ".magnitude")
    count = value["count"]
    if count is not None and (type(count) is not int or count < 1):
        _fail("positive_integer_count_required", field + ".count")
    _enum(value["repetition_basis"], ("biological_preparations", "technical_measurements", "unspecified"),
          field + ".repetition_basis")
    _enum(value["estimate_basis"], ("fit_to_averaged_curve", "between_fitted_parameters", "unknown"),
          field + ".estimate_basis")


def _operand(value, field):
    if value is None:
        return
    _keys(value, _OPERAND_KEYS, field)
    _enum(value["parameter_kind"], tuple(PARAMETER_UNITS), field + ".parameter_kind")
    _enum(value["status"], ("point", "censored", "missing", "conflicting"), field + ".status")
    if value["unit"] is None and value["status"] in ("missing", "conflicting"):
        pass
    elif type(value["unit"]) is not str or value["unit"] != PARAMETER_UNITS[value["parameter_kind"]]:
        _fail("canonical_kinetic_parameter_unit_required", field + ".unit")
    _enum(value["relation"], ("eq", "lt", "le", "gt", "ge", "none"), field + ".relation")
    if type(value["approximate"]) is not bool:
        _fail("boolean_required", field + ".approximate")
    _number(value["value"], field + ".value", nullable=True)
    expected = ("eq",) if value["status"] == "point" else (
        ("lt", "le", "gt", "ge") if value["status"] == "censored" else ("none",))
    if value["relation"] not in expected:
        _fail("kinetic_status_relation_mismatch", field + ".relation")
    reason = value["unavailable_reason"]
    if reason is not None:
        _enum(reason, INPUT_UNAVAILABLE_REASONS, field + ".unavailable_reason")
    if value["status"] in ("point", "censored"):
        if value["value"] is None:
            _fail("reported_value_required", field + ".value")
        if reason is not None:
            _fail("reported_value_cannot_have_unavailable_reason", field + ".unavailable_reason")
    elif value["value"] is not None:
        _fail("unavailable_point_must_be_null", field + ".value")
    if reason in ("source_kinetic_unit_unreported", "unsupported_source_kinetic_unit") and value["unit"] is not None:
        _fail("unavailable_source_unit_must_be_null", field + ".unit")
    _enum(value["origin"], ("reported", "graph_derived", "calculated", "synthetic"), field + ".origin")
    _text(value["measurement_id"], field + ".measurement_id")
    _text(value["physical_measurement_id"], field + ".physical_measurement_id", nullable=True)
    for group, names in (("subject", _SUBJECT_KEYS), ("context", _CONTEXT_KEYS)):
        _keys(value[group], names, field + "." + group)
        for name in names:
            _text(value[group][name], f"{field}.{group}.{name}", nullable=True)
    _uncertainty(value["uncertainty"], field + ".uncertainty")
    _source(value["source"], field + ".source")
    if value["source"]["representation"] == "synthetic" and value["origin"] != "synthetic":
        _fail("synthetic_origin_required", field + ".origin")


def validate_kinetic_inputs(inputs):
    """Return a detached closed input; scientific interpretations stay supplied."""
    _keys(inputs, _INPUT_KEYS, "inputs")
    _enum(inputs["version"], (INPUT_VERSION,), "inputs.version")
    meanings = {
        "subject_relationship": ("same_molecule_and_construct", "different", "unknown", "conflicting"),
        "parameter_definition_relationship": ("same", "different", "unknown", "conflicting"),
        "substrate_arrangement": ("separate_assays", "mixed_substrates", "unknown", "conflicting"),
        "comparison_scope": ("reported_protocols", "common_conditions", "unknown", "conflicting"),
        "nonintended_conditions_relationship": ("matched", "different", "unknown", "conflicting"),
    }
    for name, allowed in meanings.items():
        _enum(inputs[name], allowed, "inputs." + name)
    for role in ROLES:
        _operand(inputs[role], "inputs." + role)
    return deepcopy(inputs)


def _encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _operand_keys(inputs):
    keys = {}
    for role in ROLES:
        operand = inputs[role]
        keys[role] = ("kinetic_estimate_" + hashlib.sha256(_encoded({
            "version": "kinetic_estimate_identity_v1", "operand": operand}).encode("utf-8")).hexdigest()
            if operand is not None and operand["physical_measurement_id"] is not None else None)
    return keys


def kinetic_operand_keys(inputs):
    """Exact estimate keys; distinct keys never establish physical independence."""
    return _operand_keys(validate_kinetic_inputs(inputs))


def _model(value, keys):
    if value is None:
        return None
    _keys(value, _MODEL_KEYS, "model")
    for name, choices in (
        ("version", (MODEL_VERSION,)), ("variance_status", ("known", "estimated", "unknown")),
        ("observation_model", ("known_normal_log_parameters", "unspecified")),
        ("log_basis", ("natural_log_canonical_parameter",)), ("origin", ("reported", "derived", "synthetic")),
    ):
        _enum(value[name], choices, "model." + name)
    if type(value["measurement_order"]) is not list or value["measurement_order"] != list(ROLES):
        _fail("kinetic_model_measurement_order_mismatch", "model.measurement_order")
    owners = value["measurement_keys"]
    if (type(owners) is not list or len(owners) != 2
            or any(owner is not None and type(owner) is not str for owner in owners)
            or owners != [keys[role] for role in ROLES]):
        _fail("kinetic_model_measurement_owner_mismatch", "model.measurement_keys")
    if value["variance_status"] != "unknown" and any(owner is None for owner in owners):
        _fail("known_physical_measurement_owner_required", "model.measurement_keys")
    if value["source"] is not None:
        _source(value["source"], "model.source")
        if value["source"]["representation"] == "synthetic" and value["origin"] != "synthetic":
            _fail("synthetic_origin_required", "model.origin")
    elif value["variance_status"] != "unknown":
        _fail("kinetic_covariance_source_required", "model.source")
    matrix = value["covariance"]
    if matrix is None:
        if value["variance_status"] != "unknown":
            _fail("kinetic_covariance_required", "model.covariance")
    else:
        if type(matrix) is not list or len(matrix) != 2 or any(type(row) is not list or len(row) != 2 for row in matrix):
            _fail("kinetic_covariance_shape_required", "model.covariance")
        for i, row in enumerate(matrix):
            for j, number in enumerate(row):
                _number(number, f"model.covariance[{i}][{j}]")
        if matrix[0][1] != matrix[1][0]:
            _fail("symmetric_kinetic_covariance_required", "model.covariance")
        a, b, c = map(Fraction, (matrix[0][0], matrix[0][1], matrix[1][1]))
        if a < 0 or c < 0 or a * c < b * b:
            _fail("positive_semidefinite_kinetic_covariance_required", "model.covariance")
    return deepcopy(value)


def _individual_reason(operand, role):
    if operand is None:
        return role + "_measurement_missing"
    return operand["unavailable_reason"] or {
        "point": None, "missing": "source_measurement_missing", "censored": "censored_measurement",
        "conflicting": "conflicting_measurement"}[operand["status"]]


def _pair_reason(inputs, reasons):
    if any(reasons.values()):
        return next(reason for reason in reasons.values() if reason)
    n, d = (inputs[role] for role in ROLES)
    same_locator = all(n["source"][name] == d["source"][name] for name in _SOURCE_KEYS)
    same_physical = n["physical_measurement_id"] is not None and n["physical_measurement_id"] == d["physical_measurement_id"]
    if same_locator or same_physical or n["measurement_id"] == d["measurement_id"]:
        meanings = tuple(name for name in _OPERAND_KEYS if name not in (
            "source", "measurement_id", "physical_measurement_id", "origin"))
        return ("conflicting_source_observation" if any(n[name] != d[name] for name in meanings)
                else "reused_source_observation")
    if n["parameter_kind"] != d["parameter_kind"]:
        return "parameter_kind_mismatch"
    for name, supported in (("subject_relationship", "same_molecule_and_construct"),
                            ("parameter_definition_relationship", "same")):
        if inputs[name] != supported:
            return name + "_" + inputs[name]
    arrangement = inputs["substrate_arrangement"]
    if arrangement != "separate_assays":
        return "mixed_substrates_unsupported" if arrangement == "mixed_substrates" else "substrate_arrangement_" + arrangement
    scope = inputs["comparison_scope"]
    if scope in ("unknown", "conflicting"):
        return "comparison_scope_" + scope
    if scope == "common_conditions" and inputs["nonintended_conditions_relationship"] != "matched":
        return "common_conditions_not_matched"
    return None


def _finite(value):
    try:
        result = float(value)
    except (ArithmeticError, ValueError):
        return None, "numerical_model_range"
    if not math.isfinite(result) or result == 0 and value != 0:
        return None, "numerical_model_range"
    return result, None


def _sqrt(value):
    with localcontext() as context:
        context.prec = 80
        return _finite((Decimal(value.numerator) / Decimal(value.denominator)).sqrt())


def _cell(name, value, unit, *, reason=None, origin="derived", approximate=False, conditional=(), threshold=None, relation="none"):
    return {"value": value, "unit": unit, "status": "unavailable" if value is None else "populated",
        "formula": FORMULAS[name], "origin": origin, "unavailable_reason": reason,
        "approximate": approximate, "conditional_on": list(conditional), "threshold": threshold, "relation": relation}


def populate_kinetic_contrast(inputs, model=None):
    """Populate one explicitly scoped parameter contrast, preserving unknowns.

    Approximate descriptive arithmetic remains flagged; conditional known-normal
    scoring requires exact positive point operands, an explicit applicable model
    and positive known log-contrast variance. Source spreads/counts never create
    covariance. S/B are representations of one contribution, not independent
    scores. No cross-comparison aggregation or protocol correction occurs.
    """
    inputs = validate_kinetic_inputs(inputs)
    keys = _operand_keys(inputs)
    model = _model(model, keys)
    reasons = {role: _individual_reason(inputs[role], role) for role in ROLES}
    pair_reason = _pair_reason(inputs, reasons)
    n, d = (inputs[role] for role in ROLES)
    approximate = any(row is not None and row["approximate"] for row in (n, d))
    pair_unit = n["unit"] if n is not None and d is not None and n["unit"] == d["unit"] else None
    conditions = ("supplied_subject_and_parameter_relationships", "declared_common_conditions"
                  if inputs["comparison_scope"] == "common_conditions" else "reported_protocol_comparison")
    cells = {}
    for role in ROLES:
        row = inputs[role]
        name = role + "_parameter"
        cells[name] = _cell(name, row["value"] if reasons[role] is None else None,
            row["unit"] if row is not None else None, reason=reasons[role],
            origin=row["origin"] if row is not None else "derived",
            approximate=bool(row is not None and row["approximate"]),
            threshold=row["value"] if row is not None and row["status"] == "censored" else None,
            relation=row["relation"] if row is not None else "none")
    difference = ratio = e = None
    difference_reason = ratio_reason = log_reason = pair_reason
    if pair_reason is None:
        nf, df = Fraction(n["value"]), Fraction(d["value"])
        difference, difference_reason = _finite(nf - df)
        if df == 0:
            ratio_reason = "zero_denominator_parameter"
        else:
            ratio, ratio_reason = _finite(nf / df)
        if nf <= 0 or df <= 0:
            log_reason = "positive_parameters_required_for_log"
        else:
            # Difference of logs preserves extreme ratios. Nearby inputs use
            # exact subtraction before log1p to retain unequal estimates.
            e = math.log(n["value"]) - math.log(d["value"])
            if abs(nf - df) <= df / 2:
                relative, relative_reason = _finite((nf - df) / df)
                if relative_reason is None:
                    e = math.log1p(relative)
                else:
                    e, log_reason = None, relative_reason
            if e is not None:
                e, log_reason = _finite(e)
    for name, value, reason, unit in (
        ("parameter_difference", difference, difference_reason, pair_unit),
        ("parameter_ratio", ratio, ratio_reason, "dimensionless"),
        ("log_parameter_contrast", e, log_reason, "dimensionless"),
    ):
        cells[name] = _cell(name, value, unit, reason=reason, approximate=approximate, conditional=conditions)
    model_reason = log_reason
    if model_reason is None:
        model_reason = ("kinetic_log_model_unreported" if model is None else
                        "covariance_status_unknown" if model["variance_status"] == "unknown" else None)
    model_conditions = (*conditions, "supplied_log_covariance")
    variance_exact = None
    variance = uncertainty = None
    variance_reason = uncertainty_reason = model_reason
    if model_reason is None:
        matrix = model["covariance"]
        variance_exact = Fraction(matrix[0][0]) + Fraction(matrix[1][1]) - 2 * Fraction(matrix[0][1])
        variance, variance_reason = _finite(variance_exact)
        uncertainty, uncertainty_reason = _sqrt(variance_exact)
    cells["log_contrast_variance"] = _cell("log_contrast_variance", variance, "dimensionless_squared",
        reason=variance_reason, approximate=approximate, conditional=model_conditions)
    cells["log_contrast_standard_uncertainty"] = _cell("log_contrast_standard_uncertainty", uncertainty,
        "dimensionless", reason=uncertainty_reason, approximate=approximate, conditional=model_conditions)
    score_reason = model_reason
    if score_reason is None:
        if approximate:
            score_reason = "approximate_parameter_model_unsupported"
        elif model["variance_status"] != "known":
            score_reason = "known_log_covariance_required"
        elif model["observation_model"] != "known_normal_log_parameters":
            score_reason = "kinetic_observation_model_unspecified"
        elif variance_exact <= 0:
            score_reason = "positive_log_contrast_variance_required"
    score = index = None
    index_reason = score_reason
    score_conditions = (*model_conditions, "known_normal_log_parameters")
    if score_reason is None:
        ef = Fraction(e)
        score, score_reason = _finite(ef * abs(ef) / (2 * variance_exact))
        index_reason = score_reason
        if score_reason is None:
            index = math.tanh(score / 2)
            if abs(index) == 1 or index == 0 and score != 0:
                index, index_reason = None, "numerical_model_range"
    cells["source_profile_log_ratio"] = _cell("source_profile_log_ratio", score, "dimensionless",
        reason=score_reason, approximate=approximate, conditional=score_conditions)
    cells["source_signed_index"] = _cell("source_signed_index", index, "dimensionless",
        reason=index_reason, origin="proposed", approximate=approximate, conditional=score_conditions)
    return {"version": VERSION, "axis": "A105", "evaluation_scope": "source_kinetic_parameter_contrast",
        "contrast_meaning": "numerator_parameter_exceeds_denominator", "inputs": inputs, "model": model,
        "measurement_keys": keys, "physical_measurement_ids": {
            role: inputs[role]["physical_measurement_id"] if inputs[role] is not None else None for role in ROLES},
        "cells": cells, "variance_status": model["variance_status"] if model is not None else "not_supplied",
        "independent_preparation_count": None, "annotation_credit": None,
        "interpretation_limits": ["parameter_magnitude_is_not_complete_functional_specificity",
            "higher_Km_is_not_automatically_stronger_affinity_or_activity",
            "reported_protocol_comparison_is_not_automatically_common_condition_preference",
            "unknown_preparation_identity_is_not_independent_replication",
            "reported_spread_and_counts_are_not_log_covariance",
            "shared_physical_estimates_remain_dependent_across_comparisons",
            "ratio_log_profile_and_index_are_not_independent_evidence",
            "no_target_correspondence_or_annotation_credit"]}


__all__ = ["VERSION", "INPUT_VERSION", "MODEL_VERSION", "ROLES", "PARAMETER_UNITS", "COMPONENTS",
    "FORMULAS", "REASONS", "INPUT_UNAVAILABLE_REASONS", "CONDITIONAL_CODES", "validate_kinetic_inputs",
    "kinetic_operand_keys", "populate_kinetic_contrast"]
