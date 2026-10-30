"""Supplied-data numerical controls, not an instrument or biological validation."""
from copy import deepcopy
from fractions import Fraction
import builtins
import json
import os
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.calibrated_signal_contracts import (CalibratedSignalContractError,
    SELECTION_VERSION, validate_calibrated_signal_sheet)
from gene_annotation_episode.calibrated_signal_sheet import populate_calibrated_signal_sheet
from gene_annotation_episode.calibrated_signal_calculations import (calculate_calibrated_signal_components,
    validate_calibrated_signal_components)


def source(pointer=""):
    return {"source_ref": "supplied_engineering_control", "pointer": pointer}


def quantity(value, unit, relation="point"):
    return {"value": value, "unit": unit, "relation": relation, "uncertainty": None, "source": source()}


def uncertainty():
    return {"representation": "plus_minus", "magnitude": 0.2, "lower": None, "upper": None,
        "statistic": "unspecified", "coverage": None, "unit": "supplied_signal_unit", "source": source("/uncertainty")}


def supplied_inputs():
    basis = {"kind": "mass_of_element", "identity": "As"}
    sample = {"sample_id": "sample-A", "source": source("/sample"), "context_ref": "supplied-method-A",
        "context_facts": [{"name": "reported_condition", "value": "supplied only", "unit": None, "source": source()}],
        "representation": "sampled_points", "signal_kind": "sampled_signal", "retention_time_unit": "supplied_rt_unit",
        "signal_unit": "supplied_signal_unit", "measurements": [{"measurement_id": "point-1", "retention_time": 5,
            "signal": quantity(23, "supplied_signal_unit"), "source": source("/points/0")}],
        "dilution": {"factor": quantity(2, "dimensionless"), "applicability": "supported", "source": source("/dilution")}}
    species = {"species_id": "species-A", "label": "supplied arsenic species", "reference_retention_time": 5,
        "retention_time_unit": "supplied_rt_unit", "context_ref": "supplied-method-A", "quantity_basis": basis,
        "source": source("/reference")}
    calibration = {"calibration_id": "cal-A", "species_id": "species-A", "signal_kind": "sampled_signal",
        "signal_unit": "supplied_signal_unit", "concentration_unit": "supplied_mass_per_volume_unit",
        "quantity_basis": deepcopy(basis), "offset": quantity(3, "supplied_signal_unit"),
        "concentration_per_signal": {"value": .5, "signal_unit": "supplied_signal_unit",
            "concentration_unit": "supplied_mass_per_volume_unit", "uncertainty": None, "source": source("/factor")},
        "applicability": "supported", "context_ref": "supplied-method-A", "context_facts": [],
        "signal_range": {"lower": 0, "upper": 100, "lower_inclusive": True, "upper_inclusive": True,
            "unit": "supplied_signal_unit", "source": source("/range")}, "thresholds": [], "source": source("/calibration")}
    association = {"method": "unique_nearest", "analysis_species_ids": ["species-A"],
        "tolerance": quantity(1, "supplied_rt_unit"), "edge": "inclusive", "collision_policy": "ambiguous", "source": source()}
    return {"samples": [sample], "species": [species], "calibrations": [calibration], "association": association}


def selection(*, samples=("sample-A",), species=("species-A",), calibrations=("cal-A",)):
    return {"version": SELECTION_VERSION, "sample_ids": list(samples),
        "species_ids": list(species), "calibration_ids": list(calibrations)}


def calculate(inputs=None, selected=None):
    sheet = populate_calibrated_signal_sheet(**(supplied_inputs() if inputs is None else inputs))
    return calculate_calibrated_signal_components(sheet, selection=selection() if selected is None else selected)


def threshold(value=10, *, relation="less_than", kind="LOD", basis="aliquot"):
    return {"threshold_id": kind + "-supplied", "kind": kind, "value": value,
        "unit": "supplied_mass_per_volume_unit", "quantity_basis": {"kind": "mass_of_element", "identity": "As"},
        "concentration_basis": basis, "below_relation": relation, "lower_bound": None,
        "uncertainty": None, "source": source("/threshold")}


def test_explicit_signal_offset_factor_and_dilution_have_independent_known_values():
    inputs = supplied_inputs()
    before = deepcopy(inputs)
    result = calculate(inputs)
    row = result["rows"][0]
    assert inputs == before
    assert row["representation"] == "sampled_points" and row["signal_kind"] == "sampled_signal"
    assert row["association"]["measurement_id"] == "point-1"
    for name, expected in (("linear_estimate", 10), ("aliquot_concentration", 10), ("original_sample_concentration", 20)):
        cell = row[name]
        assert cell["value"] == expected
        assert cell["exact_value"] == {"numerator": str(expected), "denominator": "1"}
        assert cell["unit"] == "supplied_mass_per_volume_unit"
        assert cell["quantity_basis"] == {"kind": "mass_of_element", "identity": "As"}
    assert row["censoring"] == []
    assert result["population"]["returned_row_count"] == 1
    assert not ({"score", "confidence", "annotation_credit", "total", "predominant_species", "speciation_completeness"} & result.keys())
    assert validate_calibrated_signal_components(result) == result


@pytest.mark.parametrize("representation,kind", [("declared_peaks", "peak_height"), ("declared_peaks", "integrated_area")])
def test_declared_features_retain_their_supplied_signal_meaning(representation, kind):
    data = supplied_inputs()
    data["samples"][0].update(representation=representation, signal_kind=kind)
    data["calibrations"][0]["signal_kind"] = kind
    row = calculate(data)["rows"][0]
    assert (row["representation"], row["signal_kind"]) == (representation, kind)
    assert row["aliquot_concentration"]["value"] == 10


@pytest.mark.parametrize("signal,expected", [(3, 0), (0, -1.5), (-1, -2)])
def test_zero_and_negative_estimates_are_points_and_are_not_clamped(signal, expected):
    data = supplied_inputs()
    data["samples"][0]["measurements"][0]["signal"]["value"] = signal
    data["calibrations"][0]["signal_range"]["lower"] = -10
    row = calculate(data)["rows"][0]
    assert row["aliquot_concentration"]["value"] == expected
    assert row["original_sample_concentration"]["value"] == expected * 2
    assert ("negative_calculated_estimate_not_clamped" in row["qualifications"]) == (expected < 0)


@pytest.mark.parametrize("edge,state", [("inclusive", "assigned"), ("exclusive", "no_match")])
def test_retention_time_tolerance_edge_is_selected(edge, state):
    data = supplied_inputs()
    data["samples"][0]["measurements"][0]["retention_time"] = 6
    data["association"]["edge"] = edge
    row = calculate(data)["rows"][0]
    assert row["association"]["state"] == state
    assert row["association"]["candidates"][0]["absolute_rt_difference"] == {"numerator": "1", "denominator": "1"}


def test_duplicate_retention_times_are_retained_and_ties_are_not_first_match():
    data = supplied_inputs()
    second = deepcopy(data["samples"][0]["measurements"][0])
    second["measurement_id"] = "point-2"
    data["samples"][0]["measurements"].append(second)
    result = calculate(data)
    row = result["rows"][0]
    assert row["association"]["state"] == "ambiguous"
    assert row["association"]["reason"] == "equally_near_measurements"
    assert row["association"]["measurement_id"] is None
    assert len(row["association"]["candidates"]) == 2
    assert result["unassigned_measurements"][0]["measurement_ids"] == ["point-1", "point-2"]
    assert row["linear_estimate"]["value"] is None


def test_declared_competing_species_cannot_be_hidden_by_returned_view():
    data = supplied_inputs()
    other = deepcopy(data["species"][0])
    other["species_id"] = "species-B"
    data["species"].append(other)
    data["association"]["analysis_species_ids"].append("species-B")
    row = calculate(data)["rows"][0]
    assert row["association"]["reason"] == "measurement_shared_by_species"
    assert row["association"]["competing_species_ids"] == ["species-A", "species-B"]
    data["association"]["analysis_species_ids"] = ["species-A"]
    isolated = calculate(data)
    assert isolated["rows"][0]["association"]["state"] == "assigned"
    assert isolated["population"]["supplied_species_count"] == 2
    assert isolated["population"]["association_species_ids"] == ["species-A"]
    with pytest.raises(CalibratedSignalContractError, match="selected_species_outside_analysis_population"):
        calculate(data, selection(species=("species-B",)))


def test_tied_species_remains_a_competitor_for_another_species_unique_nearest_point():
    data = supplied_inputs()
    data["samples"][0]["measurements"][0]["retention_time"] = 4
    second = deepcopy(data["samples"][0]["measurements"][0])
    second.update(measurement_id="point-2", retention_time=6)
    data["samples"][0]["measurements"].append(second)
    other = deepcopy(data["species"][0])
    other.update(species_id="species-B", reference_retention_time=4)
    data["species"].append(other)
    data["association"]["analysis_species_ids"].append("species-B")
    row = calculate(data, selection(species=("species-B",)))["rows"][0]
    assert row["association"]["reason"] == "measurement_shared_by_species"
    assert row["association"]["competing_species_ids"] == ["species-A", "species-B"]


@pytest.mark.parametrize("mutation,cell,reason", [
    ("missing_signal", "linear_estimate", "signal_missing"),
    ("bounded_signal", "linear_estimate", "bounded_signal_is_not_a_point_operand"),
    ("missing_offset", "linear_estimate", "calibration_operand_missing"),
    ("zero_factor", "linear_estimate", "nonpositive_calibration_factor"),
    ("negative_factor", "linear_estimate", "nonpositive_calibration_factor"),
    ("missing_dilution", "original_sample_concentration", "dilution_not_supplied"),
    ("zero_dilution", "original_sample_concentration", "positive_dilution_factor_required"),
    ("unknown_applicability", "aliquot_concentration", "calibration_applicability_unknown"),
    ("missing_unit", "linear_estimate", "calibration_unit_unknown"),
    ("signal_unit", "linear_estimate", "calibration_unit_mismatch"),
    ("factor_unit", "linear_estimate", "calibration_unit_mismatch"),
    ("mixed_basis", "linear_estimate", "calibration_quantity_basis_mismatch"),
    ("context", "linear_estimate", "calibration_context_mismatch"),
    ("kind", "linear_estimate", "calibration_signal_kind_mismatch"),
])
def test_missing_or_incompatible_operands_never_become_measurements(mutation, cell, reason):
    data = supplied_inputs()
    sample, calibration = data["samples"][0], data["calibrations"][0]
    if mutation == "missing_signal": sample["measurements"][0]["signal"]["value"] = None
    elif mutation == "bounded_signal": sample["measurements"][0]["signal"]["relation"] = "less_than"
    elif mutation == "missing_offset": calibration["offset"]["value"] = None
    elif mutation == "zero_factor": calibration["concentration_per_signal"]["value"] = 0
    elif mutation == "negative_factor": calibration["concentration_per_signal"]["value"] = -1
    elif mutation == "missing_dilution": sample["dilution"] = None
    elif mutation == "zero_dilution": sample["dilution"]["factor"]["value"] = 0
    elif mutation == "unknown_applicability": calibration["applicability"] = "unknown"
    elif mutation == "missing_unit": sample["signal_unit"] = None
    elif mutation == "signal_unit": sample["signal_unit"] = "different-signal-unit"
    elif mutation == "factor_unit": calibration["concentration_per_signal"]["concentration_unit"] = "different-concentration-unit"
    elif mutation == "mixed_basis": calibration["quantity_basis"] = {"kind": "amount_of_analyte", "identity": "As"}
    elif mutation == "context": calibration["context_ref"] = "different-context"
    elif mutation == "kind": calibration["signal_kind"] = "integrated_area"
    result = calculate(data)
    assert result["rows"][0][cell]["value"] is None
    assert result["rows"][0][cell]["reason"] == reason
    assert result["sheet"]["samples"] == data["samples"]
    assert result["sheet"]["calibrations"] == data["calibrations"]


def test_time_units_are_not_silently_converted_or_inferred():
    data = supplied_inputs()
    data["samples"][0]["retention_time_unit"] = "s"
    data["species"][0]["retention_time_unit"] = "min"
    data["association"]["tolerance"]["unit"] = "min"
    row = calculate(data)["rows"][0]
    assert row["association"]["state"] == "unavailable"
    assert row["association"]["reason"] == "retention_time_unit_mismatch"


@pytest.mark.parametrize("mutation,state,reason", [
    ("outside", "outside", "outside_supplied_calibration_signal_range"),
    ("edge", "outside", "outside_supplied_calibration_signal_range"),
    ("missing", "unknown", "calibration_signal_range_not_supplied"),
    ("inverted", "invalid", "calibration_signal_range_inverted"),
    ("unit", "invalid", "calibration_range_unit_mismatch"),
])
def test_algebraic_estimate_is_separate_from_range_valid_physical_concentration(mutation, state, reason):
    data = supplied_inputs()
    calibration = data["calibrations"][0]
    if mutation == "outside": calibration["signal_range"]["upper"] = 20
    elif mutation == "edge": calibration["signal_range"].update(upper=23, upper_inclusive=False)
    elif mutation == "missing": calibration["signal_range"] = None
    elif mutation == "inverted": calibration["signal_range"].update(lower=30, upper=20)
    elif mutation == "unit": calibration["signal_range"]["unit"] = "other"
    row = calculate(data)["rows"][0]
    assert row["linear_estimate"]["value"] == 10
    assert row["linear_estimate"]["state"] == "qualified"
    assert reason in row["linear_estimate"]["qualifications"]
    assert row["calibration_range_state"] == state
    assert row["aliquot_concentration"]["value"] is None and row["aliquot_concentration"]["reason"] == reason


@pytest.mark.parametrize("relation,state", [("less_than", "not_below"), ("less_or_equal", "below")])
def test_selected_threshold_relation_keeps_original_estimate_and_unknown_lower_bound(relation, state):
    data = supplied_inputs()
    data["calibrations"][0]["thresholds"] = [threshold(relation=relation), threshold(11, kind="LOQ")]
    row = calculate(data)["rows"][0]
    detection, quantification = row["censoring"]
    assert detection["kind"] == "LOD" and detection["state"] == state
    assert detection["selected_relation"] == relation
    assert detection["estimate"]["value"] == 10
    assert row["aliquot_concentration"]["value"] == 10
    assert quantification["kind"] == "LOQ" and quantification["state"] == "below"
    assert quantification["reported_bound"]["lower"] is None
    assert quantification["reported_bound"]["lower_inclusive"] is None
    assert quantification["reported_bound"]["upper"] == 11


def test_original_sample_threshold_and_only_supplied_lower_bound_are_kept():
    data = supplied_inputs()
    limit = threshold(21, basis="original_sample")
    limit["lower_bound"] = {"value": 0, "inclusive": True, "unit": limit["unit"], "source": source()}
    data["calibrations"][0]["thresholds"] = [limit]
    censor = calculate(data)["rows"][0]["censoring"][0]
    assert censor["estimate"]["value"] == 20
    assert censor["reported_bound"]["lower"] == 0 and censor["reported_bound"]["lower_inclusive"] is True


@pytest.mark.parametrize("mutation,reason", [("missing", "threshold_missing"), ("unit", "threshold_unit_mismatch"),
    ("basis", "threshold_quantity_basis_mismatch"), ("negative", "negative_detection_or_quantification_threshold"),
    ("lower", "invalid_supplied_censoring_lower_bound")])
def test_threshold_unknowns_do_not_invent_censoring(mutation, reason):
    data = supplied_inputs()
    limit = threshold(11)
    if mutation == "missing": limit["value"] = None
    elif mutation == "unit": limit["unit"] = "other-unit"
    elif mutation == "basis": limit["quantity_basis"] = {"kind": "mass_of_analyte", "identity": "compound-A"}
    elif mutation == "negative": limit["value"] = -1
    elif mutation == "lower": limit["lower_bound"] = {"value": 12, "inclusive": True, "unit": limit["unit"], "source": source()}
    data["calibrations"][0]["thresholds"] = [limit]
    censor = calculate(data)["rows"][0]["censoring"][0]
    assert censor["state"] == "unavailable" and censor["reason"] == reason
    assert censor["estimate"]["value"] == 10 and censor["reported_bound"] is None


def test_partial_populations_keep_missing_coordinates_without_claiming_absence():
    data = supplied_inputs()
    missing = deepcopy(data["samples"][0]["measurements"][0])
    missing.update(measurement_id="missing-coordinate", retention_time=None)
    data["samples"][0]["measurements"].append(missing)
    result = calculate(data)
    row = result["rows"][0]
    assert row["association"]["state"] == "assigned" and row["aliquot_concentration"]["value"] == 10
    assert "incomplete_supplied_retention_time_population" in row["aliquot_concentration"]["qualifications"]
    assert result["unassigned_measurements"][0]["measurement_ids"] == ["missing-coordinate"]
    data["samples"][0]["measurements"] = []
    absent = calculate(data)["rows"][0]
    assert absent["association"]["state"] == "no_match" and absent["linear_estimate"]["value"] is None


def test_selected_samples_are_not_pooled_and_calibration_ambiguity_is_not_first_match():
    data = supplied_inputs()
    duplicate = deepcopy(data["samples"][0])
    duplicate["sample_id"] = "sample-B"
    duplicate["measurements"][0]["signal"]["value"] = 43
    data["samples"].append(duplicate)
    result = calculate(data, selection(samples=("sample-B",)))
    assert len(result["rows"]) == 1 and result["rows"][0]["aliquot_concentration"]["value"] == 20
    assert result["rows"][0]["sample_ordinal"] == 1 and result["population"]["replicate_pooling"] is False
    other = deepcopy(data["calibrations"][0])
    other["calibration_id"] = "cal-B"
    data["calibrations"].append(other)
    row = calculate(data, selection(calibrations=("cal-A", "cal-B")))["rows"][0]
    assert row["calibration_id"] is None and row["linear_estimate"]["reason"] == "ambiguous_selected_calibrations"


@pytest.mark.parametrize("signal,factor,reason", [(1e308, 1e308, "binary64_overflow"), (1e-200, 1e-200, "binary64_nonzero_underflow")])
def test_exact_calculation_survives_unrepresentable_binary64_display(signal, factor, reason):
    data = supplied_inputs()
    data["samples"][0]["measurements"][0]["signal"]["value"] = signal
    data["calibrations"][0]["offset"]["value"] = 0
    data["calibrations"][0]["concentration_per_signal"]["value"] = factor
    data["calibrations"][0]["signal_range"].update(lower=0, upper=signal)
    cell = calculate(data)["rows"][0]["aliquot_concentration"]
    assert cell["value"] is None and cell["reason"] == reason
    actual = Fraction(int(cell["exact_value"]["numerator"]), int(cell["exact_value"]["denominator"]))
    assert actual == Fraction(signal) * Fraction(factor) and actual != 0


def test_original_concentration_uses_exact_operands_instead_of_underflowed_intermediate():
    data = supplied_inputs()
    data["samples"][0]["measurements"][0]["signal"]["value"] = 1e-200
    data["samples"][0]["dilution"]["factor"]["value"] = 1e308
    data["calibrations"][0]["offset"]["value"] = 0
    data["calibrations"][0]["concentration_per_signal"]["value"] = 1e-200
    row = calculate(data)["rows"][0]
    assert row["aliquot_concentration"]["value"] is None
    assert row["aliquot_concentration"]["reason"] == "binary64_nonzero_underflow"
    exact = Fraction(1e-200) * Fraction(1e-200) * Fraction(1e308)
    original = row["original_sample_concentration"]
    assert original["value"] == float(exact) and original["value"] != 0
    assert original["exact_value"] == {"numerator": str(exact.numerator), "denominator": str(exact.denominator)}


def test_uncertainty_ranges_and_context_are_supplied_facts_not_combined_error_bars():
    data = supplied_inputs()
    data["samples"][0]["measurements"][0]["signal"]["uncertainty"] = uncertainty()
    data["calibrations"][0]["concentration_per_signal"]["uncertainty"] = uncertainty()
    result = calculate(data)
    assert result["sheet"]["samples"] == data["samples"]
    assert result["sheet"]["calibrations"] == data["calibrations"]
    assert result["rows"][0]["aliquot_concentration"]["uncertainty"] == {
        "state": "not_propagated", "reason": "no_selected_joint_uncertainty_model"}
    signal, factor = result["uncertainty_assessments"]
    assert signal["input_path"] == "/samples/0/measurements/0/signal/uncertainty"
    assert signal["representation_state"] == "consistent" and signal["unit_state"] == "matched"
    assert signal["coverage_state"] == "not_supplied" and signal["issues"] == []
    assert factor["unit_state"] == "unassessed"
    assert factor["issues"] == ["factor_uncertainty_unit_relationship_unassessed"]
    assert signal["statistical_validity"] == factor["statistical_validity"] == "not_assessed"


@pytest.mark.parametrize("mutation,issue", [
    ("plus_missing", "plus_minus_magnitude_missing"),
    ("plus_endpoints", "plus_minus_has_interval_endpoints"),
    ("negative_magnitude", "negative_uncertainty_magnitude"),
    ("interval_missing", "interval_endpoint_missing"),
    ("interval_reversed", "interval_endpoints_reversed"),
    ("interval_magnitude", "interval_has_plus_minus_magnitude"),
    ("unit_missing", "uncertainty_unit_missing"),
    ("unit_mismatch", "uncertainty_unit_mismatch"),
    ("ci_missing", "ci_coverage_not_supplied"),
    ("ci_zero", "ci_coverage_outside_supported_open_unit_interval"),
    ("ci_one", "ci_coverage_outside_supported_open_unit_interval"),
    ("ci_negative", "ci_coverage_outside_supported_open_unit_interval"),
    ("ci_above", "ci_coverage_outside_supported_open_unit_interval"),
    ("non_ci_coverage", "coverage_with_non_ci_statistic_unassessed"),
    ("interval_spread", "interval_spread_statistic_relationship_unassessed"),
])
def test_uncertainty_conflicts_are_preserved_and_do_not_erase_valid_point_quantities(mutation, issue):
    data = supplied_inputs()
    supplied = uncertainty()
    if mutation == "plus_missing": supplied["magnitude"] = None
    elif mutation == "plus_endpoints": supplied.update(lower=1, upper=2)
    elif mutation == "negative_magnitude": supplied["magnitude"] = -0.2
    elif mutation == "interval_missing": supplied.update(representation="interval", magnitude=None, lower=1)
    elif mutation == "interval_reversed": supplied.update(representation="interval", magnitude=None, lower=2, upper=1)
    elif mutation == "interval_magnitude": supplied.update(representation="interval", lower=1, upper=2)
    elif mutation == "unit_missing": supplied["unit"] = None
    elif mutation == "unit_mismatch": supplied["unit"] = "different-unit"
    elif mutation == "ci_missing": supplied["statistic"] = "CI"
    elif mutation == "ci_zero": supplied.update(statistic="CI", coverage=0)
    elif mutation == "ci_one": supplied.update(statistic="CI", coverage=1)
    elif mutation == "ci_negative": supplied.update(statistic="CI", coverage=-0.1)
    elif mutation == "ci_above": supplied.update(statistic="CI", coverage=1.1)
    elif mutation == "non_ci_coverage": supplied.update(statistic="SD", coverage=.95)
    elif mutation == "interval_spread": supplied.update(representation="interval", magnitude=None, lower=1, upper=2, statistic="SE")
    data["samples"][0]["measurements"][0]["signal"]["uncertainty"] = supplied
    result = calculate(data)
    assert result["sheet"]["samples"][0]["measurements"][0]["signal"]["uncertainty"] == supplied
    assessment, = result["uncertainty_assessments"]
    assert assessment["input_path"] == "/samples/0/measurements/0/signal/uncertainty"
    assert issue in assessment["issues"] and assessment["statistical_validity"] == "not_assessed"
    assert "supplied_uncertainty_has_unresolved_representation_coverage_or_unit_issues" in result["qualifications"]
    assert result["rows"][0]["aliquot_concentration"]["value"] == 10
    assert result["rows"][0]["original_sample_concentration"]["value"] == 20
    assert validate_calibrated_signal_components(result) == result


def test_reported_ci_and_unspecified_intervals_are_not_converted_or_inferred():
    data = supplied_inputs()
    reported = uncertainty()
    reported.update(representation="interval", magnitude=None, lower=1, upper=2, statistic="CI", coverage=.95)
    data["samples"][0]["measurements"][0]["signal"]["uncertainty"] = reported
    result = calculate(data)
    assessment, = result["uncertainty_assessments"]
    assert assessment["representation_state"] == "consistent" and assessment["coverage_state"] == "supplied_ci"
    assert assessment["issues"] == [] and assessment["statistical_validity"] == "not_assessed"
    reported.update(statistic="unspecified", coverage=None)
    unspecified = calculate(data)["uncertainty_assessments"][0]
    assert unspecified["coverage_state"] == "not_supplied" and unspecified["issues"] == []


@pytest.mark.parametrize("mutation", ["extra", "missing_policy", "duplicate_sample", "duplicate_point", "unknown_analysis",
    "bool", "nan", "representation"])
def test_invalid_or_ambiguous_structural_inputs_are_rejected(mutation):
    data = supplied_inputs()
    if mutation == "extra": data["samples"][0]["guessed_units"] = "unit"
    elif mutation == "missing_policy": del data["association"]["edge"]
    elif mutation == "duplicate_sample": data["samples"].append(deepcopy(data["samples"][0]))
    elif mutation == "duplicate_point": data["samples"][0]["measurements"] *= 2
    elif mutation == "unknown_analysis": data["association"]["analysis_species_ids"] = ["unknown"]
    elif mutation == "bool": data["samples"][0]["measurements"][0]["signal"]["value"] = True
    elif mutation == "nan": data["samples"][0]["measurements"][0]["signal"]["value"] = float("nan")
    elif mutation == "representation": data["samples"][0]["signal_kind"] = "peak_height"
    with pytest.raises(CalibratedSignalContractError): populate_calibrated_signal_sheet(**data)


def test_saved_sheet_recalculation_needs_no_sources_files_native_modules_or_network(monkeypatch):
    data = supplied_inputs()
    supplied = uncertainty()
    supplied.update(lower=3, magnitude=-.2)
    data["samples"][0]["measurements"][0]["signal"]["uncertainty"] = supplied
    original = calculate(data)
    saved = json.loads(json.dumps(original["sheet"]))
    def forbidden(*args, **kwargs):
        raise AssertionError("saved calculation attempted external work")
    real_import = builtins.__import__
    def no_scientific_imports(name, *args, **kwargs):
        assert not name.startswith(("numpy", "scipy", "biomni", "gene_annotation_episode.native_",
            "gene_annotation_episode.acquisition")), name
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(builtins, "__import__", no_scientific_imports)
    assert validate_calibrated_signal_sheet(saved) == saved
    assert calculate_calibrated_signal_components(saved, selection=original["selection"]) == original


def test_saved_uncertainty_assessment_is_authenticated_against_unchanged_supplied_facts():
    data = supplied_inputs()
    data["calibrations"][0]["concentration_per_signal"]["uncertainty"] = uncertainty()
    result = calculate(data)
    result["uncertainty_assessments"][0]["unit_state"] = "matched"
    with pytest.raises(CalibratedSignalContractError, match="inconsistent_saved_calibrated_signal_components"):
        validate_calibrated_signal_components(result)


@pytest.mark.parametrize("field", ["value", "qualification", "association"])
def test_saved_component_authentication_rejects_changed_derived_claims(field):
    result = calculate()
    if field == "value": result["rows"][0]["aliquot_concentration"]["value"] = 100
    elif field == "qualification": result["qualifications"] = []
    elif field == "association": result["rows"][0]["association"]["measurement_id"] = "other"
    with pytest.raises(CalibratedSignalContractError, match="inconsistent_saved_calibrated_signal_components"):
        validate_calibrated_signal_components(result)
