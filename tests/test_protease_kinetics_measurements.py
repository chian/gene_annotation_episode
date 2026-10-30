"""Hand-calculated saved-data checks; these fixtures never claim native execution."""
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path

import pytest

from gene_annotation_episode.protease_kinetics_measurements import (
    SOURCE_FUNCTION_SHA256, SOURCE_FILE_SHA256, ProteaseKineticsContractError,
    populate_protease_kinetics_sheet, validate_protease_kinetics_sheet,
    calculate_protease_kinetics_components,
)


def supplied_fixture():
    measurements = {"time_points": [0, 1, 2, 3, 4],
        "fluorescence_data": [[0, 3, 6, 9, 12], [0, 6, 12, 18, 24], [0, 8, 16, 24, 32]],
        "substrate_concentrations": [1, 3, 6], "enzyme_concentration": .5}
    # Deliberate constructed retention fixture, separate from genuine-call tests.
    # Structural protocol example only: these paths/pins do not attest a run.
    selected_pin = {"path": "/constructed/runtime/python", "sha256": "0"*64, "size_bytes": 0}
    source_pin = {"path": "/constructed/biochemistry.py", "sha256": SOURCE_FILE_SHA256, "size_bytes": 41579}
    manifest_pin = {"path": "/constructed/software.json", "sha256": "0"*64, "size_bytes": 0}
    request = {"version": "molecular_sequence_request_v3", "operation": "analyze_protease_kinetics",
        "arguments": {**deepcopy(measurements), "output_prefix": "selected", "output_dir": "/constructed/output/native"},
        "deployment": {"version": "molecular_sequence_deployment_v3", "runtime": {"executable": selected_pin, "home": "/constructed/runtime"},
            "module": source_pin, "import_roots": ["/constructed/runtime"], "software_files_ref": "artifact_" + "0"*64,
            "software_files_file": manifest_pin}, "output_workspace": "/constructed/output",
        "environment": {"MPLBACKEND": "Agg", "MPLCONFIGDIR": "/constructed/output/config", "XDG_CACHE_HOME": "/constructed/output/cache"}}
    capture = {"version": "molecular_sequence_execution_v3", "request": request, "request_canonical_sha256": None, "stage": "completed",
        "native_record": {"schema": "biomni_protease_kinetics_native_v1", "outcome": "completed", "result_kind": "analysis_report", "failure": None,
            "result": "Vmax: 12.0000; KM: 3.0000", "source_identity": {"callable": "analyze_protease_kinetics",
                "sha256": SOURCE_FUNCTION_SHA256, "path": source_pin["path"]}}, "native_call_state": "returned", "reference_data": None,
        "execution_receipt": {}, "stdout": "", "stderr": "", "failure": None,
        "observer": {"schema": "native_selected_return_observation_v1", "mechanism": "selected_code_return_profile",
            "state": "captured", "reason": None, "selected_call_count": 1, "selected_terminal_event_count": 1,
            "profile_restored": True, "failures": [], "locals": {"initial_velocities": [3., 6., 8.],
                "params": [12., 3.], "vmax": 12., "km": 3., "covariance": [[4., 1.], [1., 1.]],
                "catalytic_efficiency_std": 2.9814239699997196}}, "verification_failures": []}
    context = {"sample_key": "constructed-numerical-fixture", "substrate_identity": None, "enzyme_identity": None,
        "conditions": None, "replicate_ids": None,
        "units": {"time": "s", "signal": "RFU", "substrate": "uM", "enzyme": "uM"},
        "calibration": {"schema": "protease_signal_calibration_v1", "response_per_product_concentration": 2,
            "signal_unit": "RFU", "product_concentration_unit": "uM", "curve_ordinals": [0, 1, 2],
            "applicability": "supported", "source_ref": "constructed-calibration-fixture"},
        "enzyme_basis": "total_enzyme_concentration", "product_per_cleavage": 1}
    refresh_request(capture)
    return measurements, capture, context


def refresh_request(capture):
    encoded = json.dumps(capture["request"], sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    capture["request_canonical_sha256"] = hashlib.sha256(encoded).hexdigest()


def replace_measurements(capture, measurements):
    capture["request"]["arguments"].update(deepcopy(measurements))
    refresh_request(capture)


def result_for(measurements, capture, context):
    return calculate_protease_kinetics_components(populate_protease_kinetics_sheet(
        measurements=measurements, native_capture=capture, assay_context=context))


def test_full_covariance_and_calibrated_apparent_turnover_hand_answer():
    data, capture, context = supplied_fixture()
    result = result_for(data, capture, context)
    assert result["schema"] == "protease_kinetics_components_v2"
    physical = result["physical_components"]
    assert physical["product_vmax"]["value"] == 6
    assert physical["apparent_turnover"]["value"] == 12
    assert physical["apparent_catalytic_efficiency"]["value"] == 4
    uncertainty = physical["apparent_catalytic_efficiency"]["uncertainty"]
    assert uncertainty["variance"] == pytest.approx(4/3)
    assert uncertainty["variance"] != pytest.approx(20/9)
    assert uncertainty["total_uncertainty"] is None
    assert physical["kcat"]["reason"] == "active_site_concentration_basis_unestablished"
    context["enzyme_basis"] = "active_site_concentration"
    assert result_for(data, capture, context)["physical_components"]["kcat"]["value"] == 12


def test_source_error_after_fit_keeps_true_parameters_and_original_error():
    data, capture, context = supplied_fixture()
    capture["native_record"].update(outcome="source_error", result_kind="source_error_string",
        result="Error during analysis: output could not be written")
    capture["observer"]["locals"].update(params=[12.000041, 3.], vmax=12.000041)
    result = result_for(data, capture, context)
    assert result["fit_components"]["vmax"]["value"] == 12.000041
    assert result["native_return"]["result"].startswith("Error during analysis:")
    assert result["native_values"]["catalytic_efficiency_std"] == 2.9814239699997196


def test_missing_curve_zero_is_not_an_observed_zero():
    data, capture, context = supplied_fixture()
    data["fluorescence_data"][2] = [0, 0, 0, 0, 0]
    replace_measurements(capture, data)
    capture["observer"]["locals"]["initial_velocities"][2] = 0
    complete = result_for(data, capture, context)
    assert complete["fit_components"]["state"] == "present"
    assert complete["fit_components"]["model_rows"][2]["observed_signal_slope"] == 0
    data["fluorescence_data"].pop()
    replace_measurements(capture, data)
    missing = result_for(data, capture, context)
    assert missing["native_values"]["initial_velocities"][2] == 0
    assert missing["population"]["rows"][2]["curve_state"] == "curve_missing"
    assert missing["fit_components"]["state"] == "qualified"
    assert missing["fit_components"]["vmax"]["value"] == 12
    assert missing["fit_components"]["model_rows"][2]["observed_signal_slope"] is None
    assert missing["fit_components"]["model_rows"][2]["native_fit_vector_value"] == 0
    assert missing["physical_components"]["apparent_turnover"]["value"] is None


def test_unknown_units_and_missing_calibration_do_not_erase_raw_fit():
    data, capture, _ = supplied_fixture()
    result = result_for(data, capture, None)
    assert result["fit_components"]["vmax"]["value"] == 12
    assert result["fit_components"]["vmax"]["unit"] is None
    assert result["physical_components"]["product_vmax"]["reason"] == "calibration_not_supplied"


@pytest.mark.parametrize("change,reason", [
    ({"applicability": "unknown"}, "calibration_applicability_unknown"),
    ({"curve_ordinals": [0, 1]}, "calibration_curve_population_conflict"),
    ({"product_concentration_unit": "mM"}, "compatible_declared_units_required"),
])
def test_inapplicable_calibration_is_not_silently_rescaled(change, reason):
    data, capture, context = supplied_fixture()
    context["calibration"].update(change)
    assert result_for(data, capture, context)["physical_components"]["product_vmax"]["reason"] == reason


def test_nonfinite_covariance_is_retained_without_losing_fitted_point():
    data, capture, context = supplied_fixture()
    capture["observer"]["locals"]["covariance"] = [[{"type": "nonfinite", "token": "inf"}, 0],
        [0, {"type": "nonfinite", "token": "inf"}]]
    result = result_for(data, capture, context)
    assert result["fit_components"]["vmax"]["value"] == 12
    assert result["fit_components"]["covariance_reason"] == "native_covariance_nonfinite"
    assert result["physical_components"]["apparent_turnover"]["uncertainty"]["state"] == "unavailable"


def test_native_exception_and_observer_failures_remain_separate():
    data, capture, context = supplied_fixture()
    capture["native_call_state"] = "raised"
    capture["native_record"].update(outcome="raised", result=None, result_kind=None, failure={"message": "original native failure"})
    capture["failure"] = deepcopy(capture["native_record"]["failure"])
    capture["observer"]["failures"] = [{"stage": "cleanup", "message": "observer failure"}]
    result = result_for(data, capture, context)
    assert result["native_return"]["failure"]["message"] == "original native failure"
    assert result["fit_components"]["state"] == "qualified"
    assert result["fit_components"]["vmax"]["value"] == 12


def test_saved_sheet_and_native_alias_conflicts_are_rejected():
    data, capture, context = supplied_fixture()
    sheet = populate_protease_kinetics_sheet(measurements=data, native_capture=capture, assay_context=context)
    sheet["population"]["rows"][0]["curve_ordinal"] = 2
    with pytest.raises(ProteaseKineticsContractError, match="inconsistent_protease_sheet"):
        validate_protease_kinetics_sheet(sheet)
    capture["observer"]["locals"]["vmax"] = 13
    with pytest.raises(ProteaseKineticsContractError, match="native_parameter_alias_conflict"):
        result_for(data, capture, context)


def test_saved_array_shape_conflict_is_rejected():
    data, capture, context = supplied_fixture()
    capture["observer"]["locals"]["params"] = {"type": "ndarray", "dtype": "float64", "shape": [3], "values": [12., 3.]}
    with pytest.raises(ProteaseKineticsContractError, match="observed_array_shape_conflict"):
        result_for(data, capture, context)


def test_zero_enzyme_and_zero_km_have_explicit_denominator_failures():
    data, capture, context = supplied_fixture()
    data["enzyme_concentration"] = 0
    replace_measurements(capture, data)
    assert result_for(data, capture, context)["physical_components"]["apparent_turnover"]["reason"] == "positive_enzyme_concentration_required"
    data["enzyme_concentration"] = .5
    replace_measurements(capture, data)
    capture["observer"]["locals"].update(params=[12., 0.], km=0.)
    assert result_for(data, capture, context)["physical_components"]["apparent_catalytic_efficiency"]["reason"] == "positive_km_required"


@pytest.mark.parametrize("change", ["request_version", "missing_output_argument", "numeric_report", "wrong_result_kind"])
def test_saved_capture_requires_actual_closed_v3_protocol(change):
    data, capture, context = supplied_fixture()
    if change == "request_version":
        capture["request"]["version"] = "molecular_sequence_request_v2"
    elif change == "missing_output_argument":
        del capture["request"]["arguments"]["output_dir"]
    elif change == "numeric_report":
        capture["native_record"]["result"] = 123
    else:
        capture["native_record"]["result_kind"] = "unexpected_return"
    refresh_request(capture)
    with pytest.raises(ProteaseKineticsContractError):
        result_for(data, capture, context)


@pytest.mark.parametrize("failure_stage", ["cleanup", "serialize:initial_velocities", "serialize:covariance"])
def test_independent_observed_parameters_survive_unrelated_observer_failure(failure_stage):
    data, capture, context = supplied_fixture()
    capture["observer"]["failures"] = [{"stage": failure_stage, "message": "constructed recorder failure"}]
    if failure_stage.startswith("serialize:"):
        del capture["observer"]["locals"][failure_stage.split(":")[1]]
    result = result_for(data, capture, context)
    assert result["fit_components"]["vmax"]["value"] == 12
    assert result["physical_components"]["apparent_turnover"]["value"] == 12
    if failure_stage == "serialize:covariance":
        assert result["physical_components"]["apparent_turnover"]["uncertainty"]["state"] == "unavailable"
    else:
        assert result["physical_components"]["apparent_turnover"]["uncertainty"]["state"] == "present"


def test_negative_substrate_is_native_fit_data_but_physically_incompatible():
    data, capture, context = supplied_fixture()
    data["substrate_concentrations"][0] = -.25
    replace_measurements(capture, data)
    result = result_for(data, capture, context)
    assert result["fit_components"]["vmax"]["value"] == 12
    assert result["physical_components"]["product_vmax"]["reason"] == "negative_substrate_concentration"


def test_two_rows_keep_n_minus_two_diagnostic_without_valid_residual_df():
    data, capture, context = supplied_fixture()
    data["substrate_concentrations"].pop()
    data["fluorescence_data"].pop()
    capture["observer"]["locals"]["initial_velocities"].pop()
    context["calibration"]["curve_ordinals"].pop()
    replace_measurements(capture, data)
    result = result_for(data, capture, context)
    assert result["fit_components"]["native_n_minus_parameter_count_diagnostic"] == 0
    assert result["fit_components"]["residual_degrees_of_freedom"] is None
    assert result["fit_components"]["residual_degrees_of_freedom_reason"] == "insufficient_residual_population"


def test_strongly_asymmetric_reported_matrix_uses_only_qualified_symmetric_bilinear_form():
    data, capture, context = supplied_fixture()
    raw = [[4., 7.], [-5., 1.]]  # Symmetric part is the original [[4,1],[1,1]].
    capture["observer"]["locals"]["covariance"] = deepcopy(raw)
    original = deepcopy(capture)
    result = result_for(data, capture, context)
    assert capture == original
    assert result["native_values"]["covariance"] == result["fit_components"]["covariance"] == raw
    assert result["fit_components"]["covariance_state"] == "qualified"
    assessment = result["fit_components"]["covariance_assessment"]
    assert assessment["native_symmetry"] == "asymmetric"
    assert assessment["symmetric_part_positive_semidefinite"] is True
    assert assessment["statistical_covariance_validity"] == "unestablished"
    uncertainty = result["physical_components"]["apparent_catalytic_efficiency"]["uncertainty"]
    assert uncertainty["state"] == "qualified"
    assert uncertainty["variance"] == pytest.approx(4/3)
    assert uncertainty["variance_status"] == "qualified_reported_matrix_bilinear_estimate"
    assert uncertainty["qualifications"] == assessment["qualifications"]
    assert uncertainty["standard_uncertainty_unit"] == "uM^-1 s^-1"
    assert uncertainty["total_uncertainty"] is None


@pytest.mark.parametrize("matrix", [[[1., 2.], [2., 1.]], [[4., 6.], [2., 1.]], [[-1., 0.], [0., 1.]]])
def test_indefinite_symmetric_bilinear_part_withholds_uncertainty_without_erasing_point(matrix):
    data, capture, context = supplied_fixture()
    capture["observer"]["locals"]["covariance"] = matrix
    result = result_for(data, capture, context)
    assert result["fit_components"]["vmax"]["value"] == 12
    assert result["fit_components"]["covariance"] == matrix
    assert result["fit_components"]["covariance_assessment"]["symmetric_part_positive_semidefinite"] is False
    uncertainty = result["physical_components"]["apparent_turnover"]["uncertainty"]
    assert uncertainty == {"state": "unavailable", "reason": "native_covariance_symmetric_part_indefinite"}


@pytest.mark.parametrize("matrix,variance", [([[1., 1.], [1., 1.]], 1.), ([[0., 0.], [0., 0.]], 0.)])
def test_exact_semidefinite_and_zero_forms_need_no_roundoff_clamp(matrix, variance):
    data, capture, context = supplied_fixture()
    capture["observer"]["locals"]["covariance"] = matrix
    result = result_for(data, capture, context)
    uncertainty = result["physical_components"]["apparent_catalytic_efficiency"]["uncertainty"]
    assert uncertainty["state"] == "present"
    assert uncertainty["variance"] == variance
    assert uncertainty["qualifications"] == []


def test_positive_final_variance_underflow_is_not_reported_as_zero():
    data, capture, context = supplied_fixture()
    capture["observer"]["locals"]["covariance"] = [[5e-324, 0.], [0., 0.]]
    result = result_for(data, capture, context)
    assert result["physical_components"]["product_vmax"]["value"] == 6
    assert result["physical_components"]["product_vmax"]["uncertainty"] == {
        "state": "unavailable", "reason": "propagated_variance_positive_underflow"}
    assert result["physical_components"]["apparent_turnover"]["uncertainty"]["variance"] == 5e-324


@pytest.mark.parametrize("vmax,factor,enzyme,reason", [
    (1e308, 1e308, 1e308, "propagated_variance_positive_underflow"),
    (1e-308, 1e-308, 1e-308, "propagated_variance_overflow"),
])
def test_gradients_use_exact_saved_ratios_before_any_binary64_range_loss(vmax, factor, enzyme, reason):
    data, capture, context = supplied_fixture()
    data["enzyme_concentration"] = enzyme
    replace_measurements(capture, data)
    capture["observer"]["locals"].update(params=[vmax, 3.], vmax=vmax)
    context["calibration"]["response_per_product_concentration"] = factor
    result = result_for(data, capture, context)
    cell = result["physical_components"]["apparent_turnover"]
    assert cell["state"] == "present" and cell["value"] > 0
    assert cell["uncertainty"] == {"state": "unavailable", "reason": reason}


def test_positive_physical_point_underflow_is_not_a_present_zero():
    data, capture, context = supplied_fixture()
    capture["observer"]["locals"].update(params=[5e-324, 3.], vmax=5e-324)
    result = result_for(data, capture, context)
    assert result["fit_components"]["vmax"]["value"] == 5e-324
    cell = result["physical_components"]["product_vmax"]
    assert cell["value"] is None and cell["reason"] == "physical_ratio_positive_underflow"
    assert result["physical_components"]["apparent_turnover"]["value"] == 5e-324


def test_intermediate_overflow_cannot_erase_finite_final_physical_ratio():
    data, capture, context = supplied_fixture()
    data["enzyme_concentration"] = 1e308
    replace_measurements(capture, data)
    capture["observer"]["locals"].update(params=[1e308, 3.], vmax=1e308)
    context["calibration"]["response_per_product_concentration"] = 1e-308
    result = result_for(data, capture, context)
    assert result["fit_components"]["vmax"]["value"] == 1e308
    assert result["physical_components"]["product_vmax"]["reason"] == "physical_ratio_overflow"
    cell = result["physical_components"]["product_formation_per_enzyme_concentration"]
    assert cell["state"] == "present" and math.isfinite(cell["value"]) and cell["value"] > 0
    with localcontext() as decimal_context:
        decimal_context.prec = 200
        expected = Decimal.from_float(1e308)/Decimal.from_float(1e-308)/Decimal.from_float(1e308)
        assert cell["value"] == float(expected)


def test_genuine_zero_point_and_zero_variance_stay_present_at_extreme_scale():
    data, capture, context = supplied_fixture()
    data["enzyme_concentration"] = 1e-308
    replace_measurements(capture, data)
    capture["observer"]["locals"].update(params=[0., 3.], vmax=0., covariance=[[0., 0.], [0., 0.]])
    context["calibration"]["response_per_product_concentration"] = 1e-308
    cell = result_for(data, capture, context)["physical_components"]["apparent_turnover"]
    assert cell["state"] == "present" and cell["value"] == 0 and cell["reason"] is None
    assert cell["uncertainty"]["state"] == "present" and cell["uncertainty"]["variance"] == 0


def test_retained239_saved_matrix_propagation_and_driver_preserve_original_observation(tmp_path, monkeypatch):
    filename = os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_SHEET")
    if filename is None:
        pytest.skip("saved native239 control requires the explicitly selected retained sheet")
    path = Path(filename)
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "5ce86df48853601e7d05472f30fcfef148116ad9031f5c4035d5f10f114a5765"
    sheet = json.loads(raw)
    original = deepcopy(sheet)
    from gene_annotation_episode import molecular_sequence_driver as driver
    def forbidden_native(*args, **kwargs):
        raise AssertionError("saved239 calculation attempted native fitting")
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", forbidden_native)
    import builtins
    actual_import = builtins.__import__
    def no_fitting_libraries(name, *args, **kwargs):
        if name.split(".")[0] in {"biomni", "scipy", "numpy", "matplotlib"}:
            raise AssertionError("saved239 calculation imported a native fitting library")
        return actual_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_fitting_libraries)
    result = calculate_protease_kinetics_components(sheet)
    matrix = [[0.0012492818700340505, 0.0007987989990607725],
        [0.0007987989990607723, 0.0006602109207055316]]
    assert result["schema"] == "protease_kinetics_components_v2"
    assert result["native_values"]["covariance"] == result["fit_components"]["covariance"] == matrix
    assert result["native_values"]["params"] == [11.959381204925378, 2.9671605866008814]
    # Independent high-precision decimal derivative/quadratic oracle, retaining
    # both unequal native off-diagonal values rather than averaging their bytes.
    with localcontext() as decimal_context:
        decimal_context.prec = 200
        vmax, km = map(Decimal.from_float, result["native_values"]["params"])
        assay = sheet["assay_context"]
        scale = (Decimal.from_float(float(assay["calibration"]["response_per_product_concentration"]))
            * Decimal.from_float(float(sheet["measurements"]["enzyme_concentration"]))
            * Decimal.from_float(float(assay["product_per_cleavage"])))
        g0, g1 = Decimal(1)/(scale*km), -vmax/(scale*km*km)
        a, b = map(Decimal.from_float, matrix[0])
        c, d = map(Decimal.from_float, matrix[1])
        expected = float(a*g0*g0 + (b+c)*g0*g1 + d*g1*g1)
    uncertainty = result["physical_components"]["apparent_catalytic_efficiency"]["uncertainty"]
    assert uncertainty["state"] == "qualified" and uncertainty["variance"] == expected > 0
    assert uncertainty["statistical_covariance_validity"] == "unestablished"
    assert uncertainty["total_uncertainty"] is None
    assert result["fit_components"]["native_diagonal_only_uncertainty"]["catalytic_efficiency_std"] == 0.07376034868518917
    assert result["physical_components"]["kcat"]["reason"] == "active_site_concentration_basis_unestablished"
    pin = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    request = {"version": driver.REQUEST_VERSION_V2, "mode": "saved_sheet", "attempt_identity":
        {key: "saved239-control" for key in driver._IDENTITY_FIELDS},
        "selection": {"operation": "analyze_protease_kinetics", "sheet_file": pin}, "scientific_context": None}
    request_bytes = json.dumps(request).encode()
    request_path = tmp_path / "saved239-request.json"
    request_path.write_bytes(request_bytes)
    output = tmp_path / "saved239-output"
    declaration = driver.run_molecular_sequence_driver(request_file={"path": str(request_path),
        "sha256": hashlib.sha256(request_bytes).hexdigest(), "size_bytes": len(request_bytes)}, output_directory=str(output))
    assert declaration["driver_failure"] is None
    assert declaration["native_call_state"] == "not_requested"
    assert (output / "sheet.json").read_bytes() == raw == path.read_bytes()
    assert json.loads((output / "components.json").read_bytes()) == result
    assert sheet == original
