"""Independent numerical examples for supplied CD arithmetic, not native runs."""
from copy import deepcopy
import builtins
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.circular_dichroism_measurements import (
    INPUT_SCHEMA, CircularDichroismContractError,
    populate_circular_dichroism_sheet, validate_circular_dichroism_sheet,
    calculate_circular_dichroism_components,
)


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")


def supplied():
    return {"schema": INPUT_SCHEMA, "sample_key": None, "sample_type": "protein",
        "spectrum": {"wavelength_unit": "nm", "signal_unit": "mdeg",
            "wavelength_data": [190., 191., 195., 197., 215., 220., 310.],
            "cd_signal_data": [1., 2., 3., -1., -1., -2., 9.]},
        "thermal": {"temperature_unit": "degC", "signal_unit": "mdeg", "measurement_wavelength_nm": 222.,
            "temperature_data": [20., 30., 40., 50., 60.], "thermal_cd_data": [0., 2., 5., 8., 10.]}}


def calculate(value):
    return calculate_circular_dichroism_components(populate_circular_dichroism_sheet(measurements=value))


def summary(result):
    return {row["name"]: row for row in result["thermal"]["summary"]}


def issue_pairs(result):
    return {(row["code"], row["field"]) for row in result["issues"]}


def test_independent_sign_count_and_thermal_example_preserves_exact_values():
    values = supplied()
    sheet = populate_circular_dichroism_sheet(measurements=values)
    result = calculate_circular_dichroism_components(sheet)
    assert sheet["measurements"]["supplied"] == values
    features = result["spectrum"]["features"]
    assert [row["count"]["value"] for row in features] == [3, 2, 1]
    assert [row["selected_indices"] for row in features] == [[0, 1, 2], [4, 5], [3]]
    assert [row["population_count"] for row in features] == [3, 2, 2]
    assert all(row["count_denominator"] is None for row in features)
    assert result["spectrum"]["source_structure_label"] == "predominantly alpha-helical"
    cells = summary(result)
    assert [row["relative_signal"]["value"] for row in result["thermal"]["relative_signal"]] == [0., .2, .5, .8, 1.]
    middle = result["thermal"]["relative_signal"][2]["relative_signal"]
    assert (middle["numerator"], middle["denominator"], middle["unit"]) == (5., 10., "dimensionless")
    assert cells["sampled_midpoint_index"]["value"] == 2
    assert cells["sampled_midpoint_temperature"]["value"] == 40.
    assert result["thermal"]["transition_point_indices"] == [2]  # .2 and .8 excluded
    assert cells["transition_point_count"]["value"] == 1
    assert cells["source_endpoint_span_per_point"]["numerator"] == 40.
    assert cells["source_endpoint_span_per_point"]["denominator"] == 5
    assert cells["source_endpoint_span_per_point"]["value"] == 8.
    assert cells["source_transition_width"]["value"] == 8.
    assert result["thermal"]["width_divisor_point_count"] == 5
    assert result["thermal"]["source_cooperativity_label"] == "moderately cooperative"
    assert result["source_method"]["native_execution"] is False
    assert all(cell["uncertainty"]["state"] == "unavailable" for cell in cells.values())
    assert "relative_signal_is_not_a_measured_unfolded_fraction" in result["qualifications"]
    json.dumps(result, allow_nan=False)


def test_strict_protein_tie_and_unsampled_windows_remain_source_heuristics():
    value = supplied(); value["thermal"] = None
    value["spectrum"].update(wavelength_data=[190., 215., 250.], cd_signal_data=[1., -1., 0.])
    result = calculate(value)
    assert [row["count"]["value"] for row in result["spectrum"]["features"]] == [1, 1, 0]
    assert result["spectrum"]["source_structure_label"] == "mixed or predominantly random coil"
    assert result["spectrum"]["features"][2]["population_count"] == 0
    value["spectrum"].update(wavelength_data=[190., 215., 197.], cd_signal_data=[0., -0., 0.])
    zero = calculate(value)
    assert [row["count"]["value"] for row in zero["spectrum"]["features"]] == [0, 0, 0]
    assert [row["population_count"] for row in zero["spectrum"]["features"]] == [1, 1, 1]


def test_nucleic_acid_existence_precedence_is_not_largest_count_or_peak_finding():
    value = supplied(); value.update(sample_type="nucleic_acid", thermal=None)
    value["spectrum"].update(wavelength_data=[270., 280., 290., 295., 300.],
        cd_signal_data=[10., 10., 0., -1., 0.])
    assert calculate(value)["spectrum"]["source_structure_label"] == "B-form characteristics"
    value["spectrum"]["cd_signal_data"][2] = 1e-300
    result = calculate(value)
    assert [row["count"]["value"] for row in result["spectrum"]["features"]] == [1, 2]
    assert result["spectrum"]["source_structure_label"] == "G-quadruplex characteristics"


def test_duplicate_wavelengths_and_unsorted_positions_are_not_deduplicated_or_sorted():
    value = supplied(); value["thermal"] = None
    value["spectrum"].update(wavelength_data=[220., 190., 190., 195.], cd_signal_data=[-1., 1., 1., 1.])
    result = calculate(value)
    assert result["spectrum"]["features"][0]["selected_indices"] == [1, 2, 3]
    assert result["spectrum"]["features"][1]["selected_indices"] == [0]
    assert result["spectrum"]["features"][0]["count"]["value"] == 3


def test_sampled_midpoint_first_tie_and_nonuniform_N_divisor_are_preserved():
    value = supplied()
    value["thermal"].update(temperature_data=[0., 1., 100., 101.], thermal_cd_data=[0., 1., 3., 4.])
    result = calculate(value); cells = summary(result)
    assert cells["sampled_midpoint_index"]["value"] == 1
    assert cells["sampled_midpoint_temperature"]["value"] == 1.
    assert cells["source_transition_width"]["value"] == 50.5  # (101/4)*2, not (101/3)*2
    assert result["thermal"]["transition_point_indices"] == [1, 2]
    assert "binary64_temperature_steps_not_identical" in result["thermal"]["qualifications"]


def test_reversed_temperature_source_width_is_retained_only_as_qualified_heuristic():
    value = supplied()
    value["thermal"].update(temperature_data=[40., 30., 20., 10.], thermal_cd_data=[0., 1., 3., 4.])
    result = calculate(value); cells = summary(result)
    assert cells["sampled_midpoint_temperature"]["value"] == 30.
    assert cells["source_transition_width"]["value"] == -15.
    assert result["thermal"]["source_cooperativity_label"] == "highly cooperative (sharp transition)"
    assert "temperature_order_not_strictly_increasing" in result["thermal"]["qualifications"]


def test_zero_endpoint_span_remains_derived_zero_with_order_qualification():
    value = supplied()
    value["thermal"].update(temperature_data=[20., 30., 20.], thermal_cd_data=[0., 5., 10.])
    result = calculate(value)
    assert summary(result)["source_transition_width"]["value"] == 0.
    assert "zero_endpoint_temperature_difference" in result["thermal"]["qualifications"]
    assert result["thermal"]["source_cooperativity_label"] == "non-cooperative (broad transition)"


@pytest.mark.parametrize("signals,reason", [([2., 2., 2.], "zero_signal_range"),
    ([-1e308, 0., 1e308], "arithmetic_overflow")])
def test_undefined_normalization_retains_measured_extrema_and_valid_spectrum(signals, reason):
    value = supplied(); value["thermal"].update(temperature_data=[20., 30., 40.], thermal_cd_data=signals)
    result = calculate(value)
    assert result["spectrum"]["state"] == "present"
    assert result["thermal"]["state"] == "partial"
    assert summary(result)["signal_minimum"]["value"] == min(signals)
    assert summary(result)["signal_maximum"]["value"] == max(signals)
    assert result["thermal"]["relative_signal"] == []
    assert result["thermal"]["source_cooperativity_label"] is None
    assert (reason, "/thermal/thermal_cd_data") in issue_pairs(result)
    json.dumps(result, allow_nan=False)


def test_temperature_arithmetic_overflow_preserves_normalization_and_sampled_midpoint():
    value = supplied(); value["thermal"].update(temperature_data=[-1e308, 0., 1e308], thermal_cd_data=[0., 5., 10.])
    result = calculate(value); cells = summary(result)
    assert result["thermal"]["state"] == "partial"
    assert cells["sampled_midpoint_temperature"]["value"] == 0.
    assert cells["source_transition_width"]["value"] is None
    assert len(result["thermal"]["relative_signal"]) == 3
    assert ("arithmetic_overflow", "/thermal/temperature_data") in issue_pairs(result)
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("bad,reason", [(float("nan"), "nonfinite_value"), (float("inf"), "nonfinite_value"),
    (-float("inf"), "nonfinite_value"), (True, "non_numeric_value"), ([1.], "non_numeric_value"),
    ("1", "non_numeric_value"), (2**53 + 1, "not_exactly_representable_binary64")])
def test_invalid_spectral_values_preserve_positions_and_independent_thermal_result(bad, reason):
    value = supplied(); value["spectrum"]["cd_signal_data"][1] = bad
    sheet = populate_circular_dichroism_sheet(measurements=value)
    result = calculate_circular_dichroism_components(json.loads(json.dumps(sheet, allow_nan=False)))
    assert result["spectrum"]["state"] == "invalid_input" and result["spectrum"]["features"] == []
    assert result["thermal"]["state"] == "present"
    assert (reason, "/spectrum/cd_signal_data/1") in issue_pairs(result)
    assert len(sheet["measurements"]["supplied"]["spectrum"]["cd_signal_data"]) == 7


@pytest.mark.parametrize("field", ["wavelength_data", "cd_signal_data"])
def test_mismatched_spectral_lengths_never_truncate_or_broadcast(field):
    value = supplied(); value["spectrum"][field].pop()
    result = calculate(value)
    assert ("paired_length_mismatch", "/spectrum") in issue_pairs(result)
    assert result["spectrum"]["features"] == []
    assert result["thermal"]["state"] == "present"


@pytest.mark.parametrize("replacement,reason", [(None, "missing_spectrum"),
    ({}, "coordinate_unit_required"), ([], "expected_object")])
def test_missing_or_malformed_spectrum_does_not_discard_valid_thermal_data(replacement, reason):
    value = supplied(); value["spectrum"] = replacement
    result = calculate(value)
    assert any(row["code"] == reason for row in result["issues"])
    assert result["thermal"]["state"] == "present"


def test_optional_thermal_absence_differs_from_missing_half_pair_and_observed_empty_arrays():
    value = supplied(); value["thermal"] = None
    absent = calculate(value)
    assert absent["thermal"]["state"] == "not_supplied" and not absent["issues"]
    value = supplied(); del value["thermal"]["thermal_cd_data"]
    missing = calculate(value)
    assert ("missing_array", "/thermal/thermal_cd_data") in issue_pairs(missing)
    assert missing["spectrum"]["state"] == "present" and missing["thermal"]["summary"] == []
    value["thermal"].update(temperature_data=[], thermal_cd_data=[])
    empty = calculate(value)
    assert ("empty_array", "/thermal/temperature_data") in issue_pairs(empty)
    assert ("empty_array", "/thermal/thermal_cd_data") in issue_pairs(empty)


def test_units_sample_type_and_measurement_schema_do_not_get_guessed():
    value = supplied(); value["spectrum"]["wavelength_unit"] = "angstrom"
    result = calculate(value)
    assert ("coordinate_unit_required", "/spectrum/wavelength_unit") in issue_pairs(result)
    assert result["spectrum"]["features"] == [] and result["thermal"]["state"] == "present"
    value = supplied(); value["sample_type"] = "Protein"
    assert calculate(value)["spectrum"]["source_structure_label"] is None
    value = supplied(); value["schema"] = "unknown_method"
    result = calculate(value)
    assert result["spectrum"]["state"] == result["thermal"]["state"] == "incompatible"
    assert result["thermal"]["summary"] == []
    value = supplied(); value["spectrum"]["signal_unit"] = value["thermal"]["signal_unit"] = "unknown"
    result = calculate(value)
    assert result["spectrum"]["state"] == result["thermal"]["state"] == "present"
    assert "signal_unit_unknown" in result["spectrum"]["qualifications"]
    assert summary(result)["signal_minimum"]["unit"] == "unknown"


def test_malformed_literal_retention_tag_does_not_turn_into_a_measurement():
    value = supplied()
    value["spectrum"]["cd_signal_data"][0] = {"$cd_retained_invalid_value": {"kind": "nonfinite_float", "token": "nan"}}
    result = calculate(value)
    assert ("non_numeric_value", "/spectrum/cd_signal_data/0") in issue_pairs(result)
    assert result["spectrum"]["features"] == []


@pytest.mark.parametrize("marker", ["$cd_retained_invalid_value", "$cd_retained_object"])
def test_root_marker_collision_preserves_valid_siblings_and_saved_partial_recalculation(marker):
    value = supplied()
    value[marker] = {"kind": "nonfinite_float", "token": "nan"}
    sheet = populate_circular_dichroism_sheet(measurements=value)
    frozen = json.loads(json.dumps(sheet, allow_nan=False))
    result = calculate_circular_dichroism_components(frozen)
    assert ("unknown_field", "/" + marker) in issue_pairs(result)
    assert [row["count"]["value"] for row in result["spectrum"]["features"]] == [3, 2, 1]
    assert summary(result)["sampled_midpoint_temperature"]["value"] == 40.
    assert result == calculate_circular_dichroism_components(sheet)


@pytest.mark.parametrize("fault", ["count", "native_claim", "qualification", "unknown_field"])
def test_saved_sheet_relationships_cannot_be_relabelled_or_inconsistently_changed(fault):
    sheet = populate_circular_dichroism_sheet(measurements=supplied())
    if fault == "count": sheet["measurements"]["spectrum"]["coordinate_count"] += 1
    elif fault == "native_claim": sheet["source_method"]["native_execution"] = True
    elif fault == "qualification": sheet["qualifications"] = []
    else: sheet["invented_score"] = 1
    with pytest.raises(CircularDichroismContractError) as caught:
        validate_circular_dichroism_sheet(sheet)
    assert caught.value.issue["code"] == "inconsistent_sheet"


def test_saved_recalculation_is_detached_and_needs_no_native_library_or_io(monkeypatch):
    value = supplied(); original = deepcopy(value)
    sheet = populate_circular_dichroism_sheet(measurements=value)
    frozen = json.loads(json.dumps(sheet, allow_nan=False))
    expected = calculate_circular_dichroism_components(frozen)
    value["spectrum"]["cd_signal_data"][0] = 999.
    assert frozen["measurements"]["supplied"] == original
    real_import = builtins.__import__
    def imports(name, *args, **kwargs):
        if name.split(".")[0] in {"numpy", "scipy"}: raise AssertionError("unexpected native calculation")
        return real_import(name, *args, **kwargs)
    def forbidden(*args, **kwargs): raise AssertionError("unexpected I/O or acquisition")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", imports)
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        actual = calculate_circular_dichroism_components(frozen)
    assert actual == expected
    assert frozen == sheet
    actual["thermal"]["relative_signal"].clear()
    assert len(calculate_circular_dichroism_components(frozen)["thermal"]["relative_signal"]) == 5


def test_original_source_outputs_match_the_independent_supplied_example(tmp_path):
    # Execute the complete pinned source on labelled numerical control data.
    # This verifies native output meanings, not an experimental measurement.
    source = (Path(__file__).resolve().parents[1] /
        "reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/biochemistry.py")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        "9b8ea7ea1f712553025bdaf16f981d8bec62df6004efd0954ed90f33a394e018")
    spec = importlib.util.spec_from_file_location("cd_original_source_control", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = supplied()
    result = calculate(value)
    log = module.analyze_circular_dichroism_spectra(
        sample_name="supplied_numeric_control", sample_type=value["sample_type"],
        wavelength_data=value["spectrum"]["wavelength_data"],
        cd_signal_data=value["spectrum"]["cd_signal_data"],
        temperature_data=value["thermal"]["temperature_data"],
        thermal_cd_data=value["thermal"]["thermal_cd_data"], output_dir=str(tmp_path))
    assert result["spectrum"]["source_structure_label"] in log
    assert result["thermal"]["source_cooperativity_label"] in log
    assert "Estimated melting temperature (Tm): 40.0°C" in log
    spectral = (tmp_path / "supplied_numeric_control_cd_spectrum_analysis.txt").read_text().splitlines()
    assert spectral[0] == "Wavelength (nm)\tCD Signal"
    assert [[float(cell) for cell in line.split("\t")] for line in spectral[1:]] == [
        [190., 1.], [191., 2.], [195., 3.], [197., -1.], [215., -1.], [220., -2.], [310., 9.]]
    thermal = (tmp_path / "supplied_numeric_control_thermal_denaturation.txt").read_text().splitlines()
    assert thermal[0] == "Temperature (°C)\tCD Signal\tUnfolded Fraction"
    assert [[float(cell) for cell in line.split("\t")] for line in thermal[1:]] == [
        [20., 0., 0.], [30., 2., .2], [40., 5., .5], [50., 8., .8], [60., 10., 1.]]
