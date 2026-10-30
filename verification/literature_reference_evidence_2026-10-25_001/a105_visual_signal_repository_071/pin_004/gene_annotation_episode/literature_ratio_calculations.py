"""Deterministic relative-signal components, without an overall evidence grade.

The caller establishes that the retained representations concern one specified
comparison and validates their physical source custody. A signal ratio is not a
calibrated molar amount, an isolated functional effect or a source likelihood.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "relative_signal_sheet_v1"
COMPONENTS = ("reported_ratio", "difference_from_reference", "log_reported_ratio",
              "calibrated_amount_ratio", "amount_adjusted_effect",
              "source_profile_log_ratio", "source_signed_index")
REASONS = ("no_ratio_observations", "source_measurement_unavailable",
           "source_representation_conflict", "incomplete_conflicting_representations",
           "zero_reported_ratio", "numerical_model_range",
           "amount_calibration_unreported", "response_model_unreported",
           "uncertainty_model_unreported")
_ORIGINS = ("reported", "synthetic", "visual_transcription")
_OBSERVATION_KEYS = ("value", "origin", "source", "uncertainty")
_UNCERTAINTY = {"kind": "unreported", "magnitude": None, "count": None,
                "sampling_basis": "unspecified"}
_NATIVE_KEYS = ("source_ref", "artifact_ref", "representation", "section_id",
                "paragraph_index", "paragraph_text", "expression", "expression_start",
                "expression_end")
_VISUAL_KEYS = ("source_ref", "artifact_ref", "representation", "original_source_ref",
                "original_artifact_ref", "printed_label", "image_region",
                "reference_printed_label", "reference_image_region")


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


def _ratio(value, field):
    if value is None:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)
    if value < 0:
        _fail("nonnegative_ratio_required", field)


def _printed_label(value, field):
    import re
    if not re.fullmatch(r"[+]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?", value):
        _fail("printed_ratio_number_required", field)
    try:
        number = float(value)
    except (ValueError, OverflowError):
        _fail("finite_number_required", field)
    _ratio(number, field)
    if number == 0 and any(c in "123456789" for c in value.lower().split("e", 1)[0]):
        _fail("numerical_model_range", field)
    return number


def _source(value, origin, field, observed_value):
    if not isinstance(value, dict):
        _fail("source_locator_required", field)
    representation = value.get("representation")
    if representation in ("primary_jats", "synthetic_fixture"):
        _keys(value, _NATIVE_KEYS, field)
        for name in ("source_ref", "artifact_ref", "section_id", "paragraph_text", "expression"):
            _text(value[name], field + "." + name)
        for name in ("paragraph_index", "expression_start", "expression_end"):
            _index(value[name], field + "." + name)
        start, end = value["expression_start"], value["expression_end"]
        if not 0 <= start < end <= len(value["paragraph_text"]):
            _fail("source_expression_out_of_bounds", field)
        if value["paragraph_text"][start:end] != value["expression"]:
            _fail("source_expression_mismatch", field)
        expected_origin = "synthetic" if representation == "synthetic_fixture" else "reported"
        if origin != expected_origin:
            _fail("source_origin_mismatch", field)
        # Text descriptions are preserved as witnesses but cannot make two
        # different numerical readings of one exact locator independent.
        identity = {name: value[name] for name in ("source_ref", "artifact_ref", "representation",
            "section_id", "paragraph_index", "expression_start", "expression_end")}
    elif representation == "retained_visual_transcription":
        _keys(value, _VISUAL_KEYS, field)
        for name in ("source_ref", "artifact_ref", "original_source_ref", "original_artifact_ref", "printed_label", "reference_printed_label"):
            _text(value[name], field + "." + name)
        for region_field in ("image_region", "reference_image_region"):
            region = value[region_field]
            if not isinstance(region, list) or len(region) != 4:
                _fail("image_region_required", field + "." + region_field)
            for index, coordinate in enumerate(region):
                _index(coordinate, f"{field}.{region_field}[{index}]")
            if region[0] >= region[2] or region[1] >= region[3]:
                _fail("nonempty_image_region_required", field + "." + region_field)
        numerator = _printed_label(value["printed_label"], field + ".printed_label")
        denominator = _printed_label(value["reference_printed_label"], field + ".reference_printed_label")
        if denominator <= 0:
            _fail("positive_visual_reference_required", field + ".reference_printed_label")
        ratio = numerator / denominator
        if not math.isfinite(ratio) or ratio == 0 and numerator != 0:
            _fail("numerical_model_range", field)
        if observed_value is not None and observed_value != ratio:
            _fail("visual_ratio_mismatch", field)
        if origin != "visual_transcription":
            _fail("source_origin_mismatch", field)
        # The same original image region is one retained reading location even
        # if copied into different transcription artifacts or assigned a new label.
        identity = {name: value[name] for name in ("original_source_ref", "original_artifact_ref", "image_region", "reference_image_region")}
    else:
        _fail("unknown_source_representation", field + ".representation")
    return json.dumps(identity, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _validate(observations):
    if not isinstance(observations, list):
        _fail("observation_list_required", "observations")
    result, seen = [], set()
    for index, observation in enumerate(observations):
        field = f"observations[{index}]"
        _keys(observation, _OBSERVATION_KEYS, field)
        _ratio(observation["value"], field + ".value")
        if observation["origin"] not in _ORIGINS:
            _fail("unknown_value_origin", field + ".origin")
        _keys(observation["uncertainty"], _UNCERTAINTY, field + ".uncertainty")
        if observation["uncertainty"] != _UNCERTAINTY:
            _fail("unreported_ratio_uncertainty_required", field + ".uncertainty")
        source_identity = _source(observation["source"], observation["origin"], field + ".source", observation["value"])
        # Collapse exact copies only. Conflicting readings of a shared source
        # identity survive; separate source locations are not called independent.
        full = json.dumps(observation, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if (source_identity, full) not in seen:
            seen.add((source_identity, full))
            result.append(deepcopy(observation))
    return result


def _cell(value, candidates, unit, formula, *, reason=None, origin="derived", conflict=False):
    if value is not None and not math.isfinite(value):
        value, reason, conflict = None, "numerical_model_range", False
    return {"value": value, "value_candidates": candidates, "unit": unit,
            "status": "conflicting" if conflict else "unavailable" if value is None else "populated",
            "formula": formula, "origin": origin, "unavailable_reason": reason,
            "conditional_on": []}


def populate_relative_signal(observations):
    """Populate alternative numerical descriptions of one received comparison.

    Candidate sets enumerate retained known representations, not confidence
    intervals or unobserved possibilities. Any null representation leaves the
    scalar unknown; ``candidate_set_complete`` then remains false. Separate
    representations do not create replicate counts or sampling precision.

    The unavailable amount-adjusted effect has no unit until its response-model
    endpoint is established. A missing unit is not declared dimensionless.
    """
    rows = _validate(observations)
    known = sorted({row["value"] for row in rows if row["value"] is not None})
    incomplete = not rows or any(row["value"] is None for row in rows)
    conflicting = len(known) > 1
    reason = ("no_ratio_observations" if not rows else
              "incomplete_conflicting_representations" if incomplete and conflicting else
              "source_measurement_unavailable" if incomplete else
              "source_representation_conflict" if conflicting else None)
    point = known[0] if not incomplete and not conflicting else None
    origins = {row["origin"] for row in rows}
    native_origin = next(iter(origins)) if len(origins) == 1 else "derived"
    # Incompleteness takes precedence for the status: known conflicting
    # candidates cannot be presented as an exhaustive representation set.
    conflict_status = conflicting and not incomplete
    cells = {"reported_ratio": _cell(point, known, "fraction", "reported_percent/100; or retained_printed_ratio",
                                      reason=reason, origin=native_origin, conflict=conflict_status)}
    difference_candidates = sorted({value - 1 for value in known})
    cells["difference_from_reference"] = _cell(point - 1 if point is not None else None,
        difference_candidates, "fraction", "reported_ratio-1", reason=reason, conflict=conflict_status)
    log_candidates = sorted({math.log(value) for value in known if value > 0})
    log_reason = "zero_reported_ratio" if 0 in known else reason
    cells["log_reported_ratio"] = _cell(math.log(point) if point is not None and point > 0 else None,
        log_candidates, "dimensionless", "ln(reported_ratio)", reason=log_reason,
        conflict=conflict_status and 0 not in known)
    for name, unit, formula, unavailable, origin in (
        ("calibrated_amount_ratio", "fraction", "applicable_calibrated_amount_response", "amount_calibration_unreported", "derived"),
        ("amount_adjusted_effect", None, "applicable_functional_response_at_matched_amount", "response_model_unreported", "derived"),
        ("source_profile_log_ratio", "dimensionless", "supported_joint_observation_model", "uncertainty_model_unreported", "derived"),
        ("source_signed_index", "dimensionless", "tanh(source_profile_log_ratio/2)", "uncertainty_model_unreported", "proposed"),
    ):
        cells[name] = _cell(None, [], unit, formula, reason=unavailable, origin=origin)
    return {"version": VERSION, "scope": "reported_relative_signal", "observations": rows,
            "cells": cells, "candidate_set_complete": not incomplete,
            "independent_preparation_count": None, "annotation_credit": None}


__all__ = ["VERSION", "COMPONENTS", "REASONS", "populate_relative_signal"]
