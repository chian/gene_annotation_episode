"""Saved supplied-measurement calculations; no fitting or source/native access."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction

from .calibrated_signal_contracts import (COMPONENTS_VERSION, QUALIFICATIONS,
    calculated_cell, exact_value, validate_calibrated_signal_components_shape,
    validate_calibrated_signal_selection, validate_calibrated_signal_sheet)


def _uncertainty_assessments(sheet):
    """Qualify supplied representations, without repairing or propagating them."""
    assessments = []
    def assess(raw, path, expected_unit, *, factor=False):
        if raw is None:
            return
        missing, conflicts, issues = [], [], []
        if raw["representation"] == "plus_minus":
            if raw["magnitude"] is None:
                missing.append("plus_minus_magnitude_missing")
            if raw["lower"] is not None or raw["upper"] is not None:
                conflicts.append("plus_minus_has_interval_endpoints")
        else:
            if raw["lower"] is None or raw["upper"] is None:
                missing.append("interval_endpoint_missing")
            elif raw["lower"] > raw["upper"]:
                conflicts.append("interval_endpoints_reversed")
            if raw["magnitude"] is not None:
                conflicts.append("interval_has_plus_minus_magnitude")
            if raw["statistic"] in {"SD", "SE", "standard_uncertainty"}:
                issues.append("interval_spread_statistic_relationship_unassessed")
        if raw["magnitude"] is not None and raw["magnitude"] < 0:
            conflicts.append("negative_uncertainty_magnitude")
        coverage = raw["coverage"]
        if raw["statistic"] == "CI":
            if coverage is None:
                coverage_state = "incomplete"
                issues.append("ci_coverage_not_supplied")
            elif not 0 < coverage < 1:
                coverage_state = "conflicting"
                issues.append("ci_coverage_outside_supported_open_unit_interval")
            else:
                coverage_state = "supplied_ci"
        elif coverage is not None:
            coverage_state = "unassessed"
            issues.append("coverage_with_non_ci_statistic_unassessed")
        else:
            coverage_state = "not_supplied"
        if factor:
            unit_state = "unassessed"
            issues.append("factor_uncertainty_unit_relationship_unassessed")
            if raw["unit"] is None:
                issues.append("uncertainty_unit_missing")
        elif raw["unit"] is None:
            unit_state = "missing"
            issues.append("uncertainty_unit_missing")
        elif expected_unit is None:
            unit_state = "unknown"
            issues.append("enclosing_uncertainty_unit_unknown")
        elif raw["unit"] != expected_unit:
            unit_state = "mismatched"
            issues.append("uncertainty_unit_mismatch")
        else:
            unit_state = "matched"
        assessments.append({"input_path": path,
            "representation_state": "conflicting" if conflicts else "incomplete" if missing else "consistent",
            "coverage_state": coverage_state, "unit_state": unit_state,
            "issues": missing + conflicts + issues, "statistical_validity": "not_assessed"})
    tolerance = sheet["association"]["tolerance"]
    assess(tolerance["uncertainty"], "/association/tolerance/uncertainty", tolerance["unit"])
    for i, sample in enumerate(sheet["samples"]):
        for j, measurement in enumerate(sample["measurements"]):
            signal = measurement["signal"]
            assess(signal["uncertainty"], f"/samples/{i}/measurements/{j}/signal/uncertainty", signal["unit"])
        if sample["dilution"] is not None:
            quantity = sample["dilution"]["factor"]
            assess(quantity["uncertainty"], f"/samples/{i}/dilution/factor/uncertainty", quantity["unit"])
    for i, calibration in enumerate(sheet["calibrations"]):
        offset = calibration["offset"]
        assess(offset["uncertainty"], f"/calibrations/{i}/offset/uncertainty", offset["unit"])
        assess(calibration["concentration_per_signal"]["uncertainty"],
            f"/calibrations/{i}/concentration_per_signal/uncertainty", None, factor=True)
        for j, threshold in enumerate(calibration["thresholds"]):
            assess(threshold["uncertainty"], f"/calibrations/{i}/thresholds/{j}/uncertainty", threshold["unit"])
    return assessments


def _associations(sample, species, policy):
    results, nearest_by_species = {}, {}
    tolerance = policy["tolerance"]
    for reference in species:
        reason = None
        if reference["reference_retention_time"] is None:
            reason = "reference_retention_time_missing"
        elif sample["context_ref"] is None or reference["context_ref"] is None:
            reason = "retention_time_context_unknown"
        elif sample["context_ref"] != reference["context_ref"]:
            reason = "retention_time_context_mismatch"
        elif any(unit is None for unit in (sample["retention_time_unit"], reference["retention_time_unit"], tolerance["unit"])):
            reason = "retention_time_unit_unknown"
        elif not sample["retention_time_unit"] == reference["retention_time_unit"] == tolerance["unit"]:
            reason = "retention_time_unit_mismatch"
        elif tolerance["value"] is None:
            reason = "retention_time_tolerance_missing"
        elif tolerance["relation"] != "point" or tolerance["value"] < 0:
            reason = "invalid_retention_time_tolerance"
        candidates, eligible = [], []
        for index, measurement in enumerate(sample["measurements"]):
            delta = None
            row_reason = reason or ("measurement_retention_time_missing" if measurement["retention_time"] is None else None)
            matches = None
            if row_reason is None:
                delta = abs(Fraction(measurement["retention_time"]) - Fraction(reference["reference_retention_time"]))
                matches = delta <= Fraction(tolerance["value"]) if policy["edge"] == "inclusive" else delta < Fraction(tolerance["value"])
                if matches:
                    eligible.append((delta, index))
            candidates.append({"measurement_id": measurement["measurement_id"], "measurement_ordinal": index,
                "absolute_rt_difference": None if delta is None else exact_value(delta), "eligible": matches, "reason": row_reason})
        qualifications = []
        if any(m["retention_time"] is None for m in sample["measurements"]):
            qualifications.append("incomplete_supplied_retention_time_population")
        nearest = [] if not eligible else [i for delta, i in eligible if delta == min(item[0] for item in eligible)]
        nearest_by_species[reference["species_id"]] = nearest
        state = "unavailable" if reason else "no_match" if not nearest else "ambiguous" if len(nearest) != 1 else "assigned"
        result = {"state": state, "reason": reason or ("no_matching_supplied_measurement" if not nearest else
            "equally_near_measurements" if len(nearest) != 1 else None),
            "measurement_id": sample["measurements"][nearest[0]]["measurement_id"] if state == "assigned" else None,
            "measurement_ordinal": nearest[0] if state == "assigned" else None, "candidates": candidates,
            "competing_species_ids": [], "qualifications": qualifications}
        results[reference["species_id"]] = result
    if any(result["state"] == "unavailable" for result in results.values()):
        for result in results.values():
            result["qualifications"].append("incomplete_declared_reference_association_population")
    owners = {}
    for species_id, nearest in nearest_by_species.items():
        for index in nearest:
            owners.setdefault(index, []).append(species_id)
    conflicts = {}
    for competing in owners.values():
        if len(competing) > 1:
            for species_id in competing:
                conflicts.setdefault(species_id, set()).update(competing)
    for species_id, competing in conflicts.items():
        if results[species_id]["reason"] == "equally_near_measurements":
            results[species_id]["qualifications"].append("equally_near_measurements")
        results[species_id].update(state="ambiguous", reason="measurement_shared_by_species",
            measurement_id=None, measurement_ordinal=None,
            competing_species_ids=[s["species_id"] for s in species if s["species_id"] in competing])
    return results


def _range_assessment(calibration, signal):
    interval = calibration["signal_range"]
    if interval is None:
        return "unknown", "calibration_signal_range_not_supplied"
    if interval["unit"] is None:
        return "invalid", "calibration_range_unit_unknown"
    if interval["unit"] != calibration["signal_unit"]:
        return "invalid", "calibration_range_unit_mismatch"
    lower, upper = interval["lower"], interval["upper"]
    if lower is None and upper is None:
        return "unknown", "calibration_signal_range_not_supplied"
    if lower is not None and upper is not None and lower > upper:
        return "invalid", "calibration_signal_range_inverted"
    outside = ((lower is not None and (signal < lower or signal == lower and not interval["lower_inclusive"]))
        or (upper is not None and (signal > upper or signal == upper and not interval["upper_inclusive"])))
    return ("outside", "outside_supplied_calibration_signal_range") if outside else ("within", None)


def _linear_reason(sample, reference, calibration, signal):
    offset, factor = calibration["offset"], calibration["concentration_per_signal"]
    if signal["value"] is None:
        return "signal_missing"
    if signal["relation"] != "point":
        return "bounded_signal_is_not_a_point_operand"
    if offset["value"] is None or factor["value"] is None:
        return "calibration_operand_missing"
    if offset["relation"] != "point":
        return "bounded_calibration_offset_is_not_a_point_operand"
    if factor["value"] <= 0:
        return "nonpositive_calibration_factor"
    if sample["signal_kind"] != calibration["signal_kind"]:
        return "calibration_signal_kind_mismatch"
    units = (sample["signal_unit"], signal["unit"], calibration["signal_unit"], offset["unit"], factor["signal_unit"])
    if any(unit is None for unit in units) or calibration["concentration_unit"] is None or factor["concentration_unit"] is None:
        return "calibration_unit_unknown"
    if len(set(units)) != 1 or calibration["concentration_unit"] != factor["concentration_unit"]:
        return "calibration_unit_mismatch"
    if reference["quantity_basis"] is None or calibration["quantity_basis"] is None:
        return "calibration_quantity_basis_unknown"
    if reference["quantity_basis"] != calibration["quantity_basis"]:
        return "calibration_quantity_basis_mismatch"
    if sample["context_ref"] is None or calibration["context_ref"] is None:
        return "calibration_context_unknown"
    if sample["context_ref"] != calibration["context_ref"]:
        return "calibration_context_mismatch"
    return None


def _censoring(calibration, calibration_index, aliquot, original):
    result = []
    for i, threshold in enumerate(calibration["thresholds"]):
        estimate = aliquot if threshold["concentration_basis"] == "aliquot" else original
        reason = estimate["reason"] if estimate["state"] == "unavailable" else None
        if reason is None:
            if threshold["value"] is None:
                reason = "threshold_missing"
            elif threshold["value"] < 0:
                reason = "negative_detection_or_quantification_threshold"
            elif threshold["unit"] is None or threshold["unit"] != estimate["unit"]:
                reason = "threshold_unit_mismatch"
            elif threshold["quantity_basis"] is None or threshold["quantity_basis"] != estimate["quantity_basis"]:
                reason = "threshold_quantity_basis_mismatch"
        lower = threshold["lower_bound"]
        if reason is None and lower is not None and (lower["unit"] != estimate["unit"] or lower["value"] > threshold["value"]
                or lower["value"] == threshold["value"] and (threshold["below_relation"] == "less_than" or not lower["inclusive"])):
            reason = "invalid_supplied_censoring_lower_bound"
        below = None
        if reason is None:
            exact = estimate["exact_value"]
            point = Fraction(int(exact["numerator"]), int(exact["denominator"]))
            limit = Fraction(threshold["value"])
            below = point < limit if threshold["below_relation"] == "less_than" else point <= limit
        result.append({"threshold_id": threshold["threshold_id"], "kind": threshold["kind"],
            "concentration_basis": threshold["concentration_basis"], "selected_relation": threshold["below_relation"],
            "state": "unavailable" if reason else "below" if below else "not_below", "reason": reason,
            "estimate": deepcopy(estimate), "reported_bound": None if not below else {
                "lower": None if lower is None else lower["value"],
                "lower_inclusive": None if lower is None else lower["inclusive"],
                "upper": threshold["value"], "upper_relation": threshold["below_relation"],
                "unit": threshold["unit"], "quantity_basis": deepcopy(threshold["quantity_basis"])},
            "input_paths": [f"/calibrations/{calibration_index}/thresholds/{i}"]})
    return result


def _row(sample, sample_index, reference, reference_index, association, calibrations):
    chosen = [(i, c) for i, c in calibrations if c["species_id"] == reference["species_id"]]
    calibration = chosen[0][1] if len(chosen) == 1 else None
    calibration_index = chosen[0][0] if calibration is not None else None
    reason = ("ambiguous_selected_calibrations" if len(chosen) > 1 else "calibration_not_selected" if not chosen else None)
    reason = association["reason"] if association["state"] != "assigned" else reason
    paths = [f"/samples/{sample_index}", f"/species/{reference_index}", "/association"]
    unit = None if calibration is None else calibration["concentration_unit"]
    basis = None if calibration is None else calibration["quantity_basis"]
    linear = None
    range_state, range_reason = "unavailable", reason
    qualifications = list(association["qualifications"])
    if calibration is not None:
        paths.append(f"/calibrations/{calibration_index}")
    if reason is None:
        measurement = sample["measurements"][association["measurement_ordinal"]]
        signal = measurement["signal"]
        reason = _linear_reason(sample, reference, calibration, signal)
        if reason is None:
            linear = ((Fraction(signal["value"]) - Fraction(calibration["offset"]["value"]))
                * Fraction(calibration["concentration_per_signal"]["value"]))
            range_state, range_reason = _range_assessment(calibration, signal["value"])
            if linear < 0:
                qualifications.append("negative_calculated_estimate_not_clamped")
    physical_reason = reason
    linear_qualifications = list(qualifications)
    if calibration is not None and reason is None:
        if calibration["applicability"] != "supported":
            physical_reason = "calibration_applicability_" + calibration["applicability"]
            linear_qualifications.append(physical_reason)
        if range_reason:
            physical_reason = physical_reason or range_reason
            linear_qualifications.append(range_reason)
    linear_cell = calculated_cell(linear, unit=unit, basis=basis,
        formula="(supplied_signal-supplied_offset)*supplied_concentration_per_signal", paths=paths,
        reason=reason, qualifications=linear_qualifications)
    aliquot = calculated_cell(linear if physical_reason is None else None, unit=unit, basis=basis,
        formula="linear_estimate_with_supplied_applicable_calibration_and_range", paths=paths,
        reason=physical_reason, qualifications=qualifications)
    dilution = sample["dilution"]
    dilution_reason = physical_reason
    factor = None
    if dilution_reason is None:
        if dilution is None:
            dilution_reason = "dilution_not_supplied"
        elif dilution["applicability"] != "supported":
            dilution_reason = "dilution_applicability_" + dilution["applicability"]
        else:
            quantity = dilution["factor"]
            factor = quantity["value"]
            if factor is None or factor <= 0:
                dilution_reason = "positive_dilution_factor_required"
            elif quantity["relation"] != "point":
                dilution_reason = "bounded_dilution_is_not_a_point_operand"
            elif quantity["unit"] != "dimensionless":
                dilution_reason = "explicit_dimensionless_dilution_required"
    original = calculated_cell(None if dilution_reason else linear * Fraction(factor), unit=unit, basis=basis,
        formula="aliquot_concentration*supplied_dilution_factor", paths=paths + [f"/samples/{sample_index}/dilution"],
        reason=dilution_reason, qualifications=qualifications)
    return {"sample_id": sample["sample_id"], "species_id": reference["species_id"],
        "sample_ordinal": sample_index, "species_ordinal": reference_index,
        "representation": sample["representation"], "signal_kind": sample["signal_kind"],
        "association": deepcopy(association), "selected_calibration_ids": [c["calibration_id"] for _, c in chosen],
        "calibration_id": None if calibration is None else calibration["calibration_id"],
        "calibration_range_state": range_state, "linear_estimate": linear_cell,
        "aliquot_concentration": aliquot, "original_sample_concentration": original,
        "censoring": [] if calibration is None else _censoring(calibration, calibration_index, aliquot, original),
        "qualifications": qualifications}


def calculate_calibrated_signal_components(sheet, *, selection):
    """Evaluate an explicit view without changing its stored association population.

    Input float operands retain their exact binary ratios. This function reads
    only supplied structured facts; it does not establish their experimental
    truth or choose units, calibration, species identities or missing values.
    """
    value = validate_calibrated_signal_sheet(sheet)
    selected = validate_calibrated_signal_selection(selection, value)
    analysis_ids = value["association"]["analysis_species_ids"]
    references = [s for s in value["species"] if s["species_id"] in analysis_ids]
    calibrations = [(i, c) for i, c in enumerate(value["calibrations"]) if c["calibration_id"] in selected["calibration_ids"]]
    rows, unassigned = [], []
    for i, sample in enumerate(value["samples"]):
        if sample["sample_id"] not in selected["sample_ids"]:
            continue
        associations = _associations(sample, references, value["association"])
        assigned = {a["measurement_id"] for a in associations.values() if a["state"] == "assigned"}
        unassigned.append({"sample_id": sample["sample_id"],
            "measurement_ids": [m["measurement_id"] for m in sample["measurements"] if m["measurement_id"] not in assigned]})
        for j, reference in enumerate(value["species"]):
            if reference["species_id"] in selected["species_ids"]:
                rows.append(_row(sample, i, reference, j, associations[reference["species_id"]], calibrations))
    assessments = _uncertainty_assessments(value)
    qualifications = list(QUALIFICATIONS)
    if any(assessment["issues"] for assessment in assessments):
        qualifications.append("supplied_uncertainty_has_unresolved_representation_coverage_or_unit_issues")
    result = {"version": COMPONENTS_VERSION, "sheet": value, "selection": selected,
        "population": {"supplied_sample_count": len(value["samples"]), "supplied_species_count": len(value["species"]),
            "selected_sample_count": len(selected["sample_ids"]), "selected_species_count": len(selected["species_ids"]),
            "returned_row_count": len(rows), "association_species_ids": list(analysis_ids),
            "association_competitor_basis": "declared_analysis_population", "replicate_pooling": False},
        "rows": rows, "uncertainty_assessments": assessments,
        "unassigned_measurements": unassigned, "qualifications": qualifications}
    return validate_calibrated_signal_components_shape(result)


def validate_calibrated_signal_components(components):
    """Authenticate deterministic saved components against their retained inputs."""
    value = validate_calibrated_signal_components_shape(components)
    expected = calculate_calibrated_signal_components(value["sheet"], selection=value["selection"])
    if value != expected:
        from .calibrated_signal_contracts import CalibratedSignalContractError
        raise CalibratedSignalContractError("inconsistent_saved_calibrated_signal_components", "/")
    return expected


__all__ = ["calculate_calibrated_signal_components", "validate_calibrated_signal_components"]
