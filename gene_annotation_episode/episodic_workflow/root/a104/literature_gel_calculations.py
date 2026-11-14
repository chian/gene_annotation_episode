"""Exact descriptive gel display components, with explicit shared measurements.

These fractions describe the selected 8-bit image darkness. They are neither
molecular occupancy nor binding constants, sampling probabilities or annotation
credit. The direct competition contrast survives cancellation of an unavailable
baseline. Coherent ROI alternatives remain alternatives of this one measurement.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .literature_gel_inputs import (
    _canonical, _fail, _fraction, _hash, _keys, _rational, _same,
    validate_gel_extraction,
)


VERSION = "gel_lane_sheet_v1"
VERSION_V2 = "gel_lane_sheet_v2"
COMPARISON_VERSION = "gel_competition_comparison_v1"


def gel_comparison_schema():
    text = {"type": "string", "minLength": 1}
    properties = {"version": {"const": COMPARISON_VERSION},
        "baseline_lane_id": {"anyOf": [text, {"type": "null"}]},
        "protein_lane_id": text,
        "competitor_lane_id": {"anyOf": [text, {"type": "null"}]}}
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _comparison(value, extraction):
    _keys(value, ("version", "baseline_lane_id", "protein_lane_id", "competitor_lane_id"), "comparison")
    if value["version"] != COMPARISON_VERSION:
        _fail("unsupported_gel_comparison_version", "comparison.version")
    ids = {lane["lane_id"] for lane in extraction["selection"]["lanes"]}
    for role in ("baseline", "protein", "competitor"):
        lane_id = value[role + "_lane_id"]
        if lane_id is None and role != "protein":
            continue
        if not isinstance(lane_id, str) or lane_id not in ids:
            _fail("selected_gel_lane_required", "comparison." + role + "_lane_id")
    return deepcopy(value)


def _cell(value, formula, dependencies, *, reason=None, unit="display_fraction", qualifications=()):
    exact = None if value is None else _rational(value)
    projected = None
    projection_reason = None
    if value is not None:
        try:
            projected = float(value)
            if not math.isfinite(projected) or projected == 0 and value != 0:
                projected, projection_reason = None, "numerical_projection_range"
        except OverflowError:
            projection_reason = "numerical_projection_range"
    return {"value": projected, "exact": exact, "unit": unit, "formula": formula,
        "status": "unavailable" if value is None else "calculated",
        "unavailable_reason": reason, "projection_reason": projection_reason,
        "dependencies": deepcopy(dependencies), "qualifications": list(qualifications),
        "sampling_standard_uncertainty": None, "confidence_interval": None}


def _number(cell):
    return None if cell["exact"] is None else _fraction(cell["exact"])


def _overlap(a, b):
    return (a is not None and b is not None and max(a[0], b[0]) < min(a[2], b[2])
            and max(a[1], b[1]) < min(a[3], b[3]))


def _inside(inner, outer):
    return inner is not None and outer is not None and (
        outer[0] <= inner[0] < inner[2] <= outer[2]
        and outer[1] <= inner[1] < inner[3] <= outer[3])


def _region_dependency(image, lane, band, background, method=None):
    result = {"source_ref": image["source_ref"], "artifact_ref": image["artifact_ref"],
        "image_byte_sha256": image["byte_sha256"], "lane_id": lane,
        "signal_region": deepcopy(band), "background_region": deepcopy(background)}
    if method is not None:
        result["background_method"] = method
    return result


def _lane(row, image):
    bands = row["bands"]
    method = row.get("background_method")
    selected = [band for band in bands if band["role"] in ("shifted", "free")]
    dependencies = [_region_dependency(image, row["lane_id"], band["region"], row["background"]["region"], method)
                    for band in selected]
    qualifications = []
    if any(_overlap(band["region"], row["background"]["region"]) for band in bands):
        qualifications.append("selected_background_overlaps_band")
    if any(band["corrected_signal"]["exact"] is not None
           and _fraction(band["corrected_signal"]["exact"]) < 0 for band in bands):
        qualifications.append("negative_background_corrected_band_retained")
    overlap = any(_overlap(a["region"], b["region"]) for i, a in enumerate(selected) for b in selected[i+1:])
    def summed(role):
        group = [band for band in selected if band["role"] == role]
        reason = "band_role_not_selected" if not group else next((
            band["corrected_signal"]["unavailable_reason"] for band in group
            if band["corrected_signal"]["unavailable_reason"]), None)
        if any(_overlap(a["region"], b["region"]) for i, a in enumerate(group) for b in group[i+1:]):
            reason = "overlapping_band_regions"
        value = None if reason else sum((_fraction(band["corrected_signal"]["exact"]) for band in group), Fraction())
        return _cell(value, "sum_background_corrected_" + role + "_bands",
            [_region_dependency(image, row["lane_id"], b["region"], row["background"]["region"], method) for b in group],
            reason=reason, unit="display_darkness_sum", qualifications=qualifications)
    shifted, free = summed("shifted"), summed("free")
    reason = "overlapping_band_regions" if overlap else shifted["unavailable_reason"] or free["unavailable_reason"]
    total = None if reason else _number(shifted) + _number(free)
    total_cell = _cell(total, "shifted_plus_free_display_darkness", dependencies,
                       reason=reason, unit="display_darkness_sum", qualifications=qualifications)
    fraction_reason = reason or ("nonpositive_total_display_darkness" if total <= 0 else None)
    fraction = None if fraction_reason else _number(shifted) / total
    if fraction is not None and not 0 <= fraction <= 1:
        qualifications.append("display_fraction_outside_unit_interval_retained")
    fraction_cell = _cell(fraction, "shifted_divided_by_shifted_plus_free_display_darkness",
                         dependencies, reason=fraction_reason, qualifications=qualifications)
    # The off-band diagnostic requires every declared band, including other bands,
    # to be a nonoverlapping subset of the declared whole-lane region.
    whole = row["whole_lane_corrected_signal"]
    off_reason = whole["unavailable_reason"]
    if off_reason is None and any(not _inside(b["region"], row["whole_lane"]["region"]) for b in bands):
        off_reason = "bands_not_inside_whole_lane"
    if off_reason is None and any(_overlap(a["region"], b["region"]) for i, a in enumerate(bands) for b in bands[i+1:]):
        off_reason = "overlapping_band_regions"
    off_reason = off_reason or next((b["corrected_signal"]["unavailable_reason"] for b in bands
                                    if b["corrected_signal"]["unavailable_reason"]), None)
    whole_value = None if whole["exact"] is None else _fraction(whole["exact"])
    if off_reason is None and whole_value <= 0:
        off_reason = "nonpositive_whole_lane_display_darkness"
    off_value = None if off_reason else (whole_value - sum(
        (_fraction(b["corrected_signal"]["exact"]) for b in bands), Fraction())) / whole_value
    off_dependencies = [_region_dependency(image, row["lane_id"], row["whole_lane"]["region"], row["background"]["region"], method)] + [
        _region_dependency(image, row["lane_id"], b["region"], row["background"]["region"], method) for b in bands]
    black_reason = "band_role_not_selected" if not selected else next((
        b["measurement"]["unavailable_reason"] for b in selected
        if b["measurement"]["unavailable_reason"]), None)
    if overlap:
        black_reason = "overlapping_band_regions"
    black = None if black_reason else Fraction(sum(b["measurement"]["zero_gray_count"] for b in selected),
                                              sum(b["measurement"]["pixel_count"] for b in selected))
    black_dependencies = [_region_dependency(image, row["lane_id"], band["region"], None) for band in selected]
    return {"lane_id": row["lane_id"], "cells": {"shifted_display_darkness": shifted,
        "free_display_darkness": free, "selected_total_display_darkness": total_cell,
        "shifted_display_fraction": fraction_cell,
        "off_band_display_fraction": _cell(off_value, "whole_lane_minus_selected_bands_divided_by_whole_lane",
            off_dependencies, reason=off_reason, qualifications=("display_diagnostic_not_calibrated_recovery",)),
        "display_black_pixel_fraction": _cell(black, "zero_gray_pixels_divided_by_selected_band_pixels",
            black_dependencies, reason=black_reason, qualifications=("display_black_pixels_do_not_establish_native_saturation",))}}


def _scientific_interpretation(by_id, comparison):
    reasons, states = [], []
    for role in ("baseline", "protein", "competitor"):
        lane_id = comparison[role + "_lane_id"]
        if lane_id is None:
            reasons.append(role + "_lane_not_selected")
            states.append("unknown")
            continue
        row = by_id[lane_id]
        for name in ("subject", "construct", "endpoint", "condition", "control_role"):
            state = row[name]["state"]
            if state != "known":
                reasons.append(role + "_" + name + "_" + state)
                states.append(state)
    protein = by_id[comparison["protein_lane_id"]]
    competitor_id = comparison["competitor_lane_id"]
    if competitor_id is not None:
        competitor = by_id[competitor_id]
        for name in ("subject", "construct", "endpoint"):
            if (protein[name]["state"] == competitor[name]["state"] == "known"
                    and protein[name]["value"] != competitor[name]["value"]):
                reasons.append("protein_competitor_" + name + "_mismatch")
                states.append("conflicting")
    expected_roles = {"baseline": "protein_free", "protein": "protein_present", "competitor": "competitor"}
    for role, expected in expected_roles.items():
        lane_id = comparison[role + "_lane_id"]
        if lane_id is not None:
            actual = by_id[lane_id]["control_role"]
            if actual["state"] == "known" and actual["value"] != expected:
                reasons.append(role + "_role_does_not_establish_requested_experimental_meaning")
                states.append("unknown")
    return {"status": "conflicting" if "conflicting" in states else "unknown" if states else "descriptive_only",
        "reasons": reasons,
        "comparability_outside_intended_change": "not_established_by_display_arithmetic",
        "effect_isolation": "not_established_by_display_arithmetic"}


def _calculate(extraction, comparison):
    by_id = {row["lane_id"]: row for row in extraction["selection"]["lanes"]}
    assignments = []
    for assignment in extraction["assignments"]:
        lanes = [_lane(row, extraction["image"]) for row in assignment["lanes"]]
        lookup = {row["lane_id"]: row["cells"] for row in lanes}
        def selected(role):
            lane_id = comparison[role + "_lane_id"]
            return None if lane_id is None else lookup[lane_id]["shifted_display_fraction"]
        base, protein, competitor = (selected(role) for role in ("baseline", "protein", "competitor"))
        def difference(first, second, formula):
            reason = ("comparison_lane_not_selected" if first is None or second is None
                      else first["unavailable_reason"] or second["unavailable_reason"])
            value = None if reason else _number(first) - _number(second)
            dependencies = ([] if first is None else first["dependencies"]) + ([] if second is None else second["dependencies"])
            return _cell(value, formula, dependencies, reason=reason)
        delta = difference(protein, base, "protein_fraction_minus_baseline_fraction")
        residual_delta = difference(competitor, base, "competitor_fraction_minus_baseline_fraction")
        direct = difference(protein, competitor, "protein_fraction_minus_competitor_fraction")
        ratio_reason = delta["unavailable_reason"] or residual_delta["unavailable_reason"]
        if ratio_reason is None and _number(delta) == 0:
            ratio_reason = "zero_protein_associated_display_shift"
        residual = None if ratio_reason else _number(residual_delta) / _number(delta)
        displaced = None if residual is None else 1 - residual
        factorized = None if displaced is None else _number(delta) * displaced
        dependencies = delta["dependencies"] + residual_delta["dependencies"]
        common_qualifications = ["shared_measurements_not_independent_evidence"]
        if displaced is not None and not 0 <= displaced <= 1:
            common_qualifications.append("displaced_display_fraction_outside_unit_interval_retained")
        cells = {"protein_associated_display_shift": delta,
            "competitor_residual_display_fraction": _cell(residual, "competitor_minus_baseline_divided_by_protein_minus_baseline",
                dependencies, reason=ratio_reason, qualifications=common_qualifications),
            "displaced_display_fraction": _cell(displaced, "one_minus_competitor_residual_display_fraction",
                dependencies, reason=ratio_reason, qualifications=common_qualifications),
            "factorized_competitor_sensitive_shift": _cell(factorized, "protein_associated_shift_times_displaced_fraction",
                dependencies, reason=ratio_reason, qualifications=common_qualifications),
            "direct_competitor_sensitive_shift": direct}
        # Only actual used P/C pixels are dependencies of the direct result.
        direct["qualifications"].append("baseline_cancels_from_direct_form")
        if comparison["baseline_lane_id"] is not None:
            direct["qualifications"].append("cancellation_does_not_establish_baseline_measurement")
        if protein is not None and competitor is not None and _same(
            [{k: v for k, v in d.items() if k != "lane_id"} for d in protein["dependencies"]],
            [{k: v for k, v in d.items() if k != "lane_id"} for d in competitor["dependencies"]]):
            direct["qualifications"].append("same_physical_display_measurement_reused_nondiscriminating")
        protein_total = lookup[comparison["protein_lane_id"]]["selected_total_display_darkness"]
        for row in lanes:
            numerator = row["cells"]["selected_total_display_darkness"]
            reason = numerator["unavailable_reason"] or protein_total["unavailable_reason"]
            if reason is None and _number(protein_total) <= 0:
                reason = "nonpositive_reference_total_display_darkness"
            value = None if reason else _number(numerator) / _number(protein_total)
            row["cells"]["display_total_ratio_to_protein_lane"] = _cell(value,
                "selected_total_divided_by_protein_lane_selected_total",
                numerator["dependencies"] + protein_total["dependencies"], reason=reason,
                qualifications=("display_diagnostic_not_calibration_recovery",))
            row["scientific_context"] = deepcopy(by_id[row["lane_id"]])
        assignments.append({"assignment_id": assignment["assignment_id"], "lanes": lanes, "cells": cells,
            "scientific_interpretation": _scientific_interpretation(by_id, comparison),
            "dependence": {"same_image": True, "baseline_reused_in_factorized_form": comparison["baseline_lane_id"] is not None,
                "direct_baseline_coefficient": 0, "independence_established": False,
                "factorization_equal_to_direct": None if factorized is None or _number(direct) is None else factorized == _number(direct)}})
    component_names = list(assignments[0]["cells"])
    sensitivity = {}
    for name in component_names:
        available = [(a["assignment_id"], _number(a["cells"][name])) for a in assignments if _number(a["cells"][name]) is not None]
        sensitivity[name] = {"kind": "explicit_available_roi_assignment_range_not_sampling_interval",
            "status": "no_available_values" if not available else "complete" if len(available) == len(assignments) else "partial",
            "bounds_unavailable_assignments": False,
            "lower": None if not available else _rational(min(v for _, v in available)),
            "upper": None if not available else _rational(max(v for _, v in available)),
            "included_assignment_ids": [key for key, _ in available],
            "unavailable_assignment_ids": [a["assignment_id"] for a in assignments if _number(a["cells"][name]) is None],
            "sampling_confidence_level": None}
    result = {"version": VERSION if extraction["version"] == "gel_lane_extraction_v1" else VERSION_V2,
        "extraction_digest": extraction["extraction_digest"],
        "comparison": deepcopy(comparison), "context": deepcopy(extraction["selection"]["context"]),
        "origin": extraction["origin"], "assignments": assignments, "roi_sensitivity": sensitivity,
        "sampling_uncertainty": {"status": "not_supplied", "value": None},
        "detector_response_calibration": {"status": "not_supplied", "value": None},
        "unimplemented_quantities": ["calibrated_molecular_occupancy", "binding_observation_likelihood"],
        "independent_preparation_count": None, "annotation_credit": None}
    result["sheet_digest"] = _hash(_canonical(result))
    return result


def populate_gel_components(extraction, comparison):
    """Populate exact fractions and comparisons over nominated coherent ROIs."""
    checked = validate_gel_extraction(extraction["selection"], extraction)
    return _calculate(checked, _comparison(comparison, checked))


def validate_gel_sheet(extraction, comparison, sheet, *, expected_extraction_digest=None):
    """Check saved component relationships without public reader/populator calls."""
    checked = validate_gel_extraction(extraction["selection"], extraction,
                                      expected_digest=expected_extraction_digest)
    expected = _calculate(checked, _comparison(comparison, checked))
    if not _same(expected, sheet):
        _fail("saved_gel_sheet_mismatch", "sheet")
    return deepcopy(sheet)


__all__ = ["VERSION", "VERSION_V2", "COMPARISON_VERSION", "gel_comparison_schema", "populate_gel_components",
           "validate_gel_sheet"]
