"""Supplied protease curves and observed native fits; saved calculation never fits.

The unchanged selected Biomni function owns polyfit/curve_fit. This sheet retains
its full observed locals and original return, including unavailable/nonfinite
results. Physical conversions require separately supplied applicable calibration.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import PurePosixPath

from .bivariate_covariance import assess_bivariate_covariance, propagate_bivariate_variance


SHEET_SCHEMA = "protease_kinetics_sheet_v1"
COMPONENTS_SCHEMA = "protease_kinetics_components_v2"
CAPTURE_VERSION = "molecular_sequence_execution_v3"
OPERATION = "analyze_protease_kinetics"
SOURCE_FILE_SHA256 = "9b8ea7ea1f712553025bdaf16f981d8bec62df6004efd0954ed90f33a394e018"
SOURCE_FUNCTION_SHA256 = "9ad74fa1c808c356f457748b2372e970b7c54bc960a5d41dba60375e9d91f36c"
MEASUREMENT_FIELDS = {"time_points", "fluorescence_data", "substrate_concentrations", "enzyme_concentration"}
SHEET_FIELDS = {"schema", "source_method", "numeric_interpretation", "measurements", "assay_context",
    "native_observation", "population", "issues", "qualifications"}
SOURCE_METHOD = {"callable": "biomni.tool.biochemistry." + OPERATION,
    "source_file_sha256": SOURCE_FILE_SHA256, "source_function_sha256": SOURCE_FUNCTION_SHA256,
    "initial_window": "first_max_5_floor_0_2_N_time_points_with_native_slicing",
    "slope_authority": "unchanged_native_numpy_polyfit_degree_1",
    "fit_authority": "unchanged_native_scipy_curve_fit", "parameter_order": ["vmax", "km"],
    "model": "vmax*S/(km+S)", "p0": ["max_initial_velocities", "mean_substrate_concentrations"],
    "bounds": {"lower": [0, 0], "upper": ["positive_infinity", "positive_infinity"]},
    "other_fit_options": "selected_scipy_version_defaults",
    "native_unit_claims": {"time": "s", "substrate": "uM", "enzyme": "uM",
        "vmax": "a.u./s", "kcat": "s^-1", "catalytic_efficiency": "uM^-1 s^-1"}}
QUALIFICATIONS = ["first_window_signal_slope_is_not_proof_of_an_initial_chemical_regime",
    "native_fit_is_unweighted_over_original_substrate_rows", "repeated_concentrations_are_not_inferred_replicates",
    "native_unit_labels_do_not_establish_supplied_units", "native_efficiency_uncertainty_omits_parameter_covariance",
    "fit_only_uncertainty_holds_calibration_and_enzyme_values_fixed", "no_total_uncertainty_or_function_probability"]


class ProteaseKineticsContractError(ValueError):
    def __init__(self, code, field):
        self.code, self.field = code, field
        super().__init__(code + ":" + field)


def _fail(code, field):
    raise ProteaseKineticsContractError(code, field)


def _copy(value):
    try:
        return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as error:
        raise ProteaseKineticsContractError("finite_json_or_explicit_native_tokens_required", "/") from error


def _same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) and (type(value) is not int or result == value) else None


def _decode(value):
    """Decode observed numeric containers without replacing nonfinite values."""
    if type(value) is dict:
        if value.get("type") == "ndarray" and set(value) == {"type", "dtype", "shape", "values"}:
            shape = value["shape"]
            if type(value["dtype"]) is not str or type(shape) is not list or any(type(n) is not int or n < 0 for n in shape):
                _fail("invalid_observed_array", "/native_observation/observer/locals")
            def dimensions(data, remaining):
                if not remaining:
                    return type(data) is not list
                return type(data) is list and len(data) == remaining[0] and all(dimensions(v, remaining[1:]) for v in data)
            if not dimensions(value["values"], shape):
                _fail("observed_array_shape_conflict", "/native_observation/observer/locals")
            return _decode(value["values"])
        if value.get("type") == "numpy_scalar" and set(value) == {"type", "dtype", "value"}:
            return _decode(value["value"])
        return deepcopy(value)
    if type(value) is list:
        return [_decode(v) for v in value]
    return value


def _context(raw):
    result = {"sample_key": None, "substrate_identity": None, "enzyme_identity": None, "conditions": None,
        "replicate_ids": None, "units": {"time": None, "signal": None, "substrate": None, "enzyme": None},
        "calibration": None, "enzyme_basis": "unknown", "product_per_cleavage": None}
    if raw is None:
        return result
    if type(raw) is not dict or set(raw) != set(result):
        _fail("closed_assay_context_required", "/assay_context")
    for name in ("sample_key", "substrate_identity", "enzyme_identity"):
        if raw[name] is not None and (type(raw[name]) is not str or not raw[name].strip()):
            _fail("identity_or_null_required", "/assay_context/" + name)
    if raw["replicate_ids"] is not None and (type(raw["replicate_ids"]) is not list or any(
            item is not None and (type(item) is not str or not item.strip()) for item in raw["replicate_ids"])):
        _fail("replicate_ids_or_null_required", "/assay_context/replicate_ids")
    units = raw["units"]
    if type(units) is not dict or set(units) != set(result["units"]):
        _fail("closed_declared_units_required", "/assay_context/units")
    for name, value in units.items():
        if value is not None and (type(value) is not str or not value.strip()):
            _fail("declared_unit_or_null_required", "/assay_context/units/" + name)
    if raw["enzyme_basis"] not in {"unknown", "total_enzyme_concentration", "active_site_concentration"}:
        _fail("enzyme_basis_required", "/assay_context/enzyme_basis")
    stoichiometry = raw["product_per_cleavage"]
    if stoichiometry is not None and (_number(stoichiometry) is None or stoichiometry <= 0):
        _fail("positive_product_stoichiometry_required", "/assay_context/product_per_cleavage")
    calibration = raw["calibration"]
    if calibration is not None:
        fields = {"schema", "response_per_product_concentration", "signal_unit", "product_concentration_unit",
            "curve_ordinals", "applicability", "source_ref"}
        if type(calibration) is not dict or set(calibration) != fields or calibration["schema"] != "protease_signal_calibration_v1":
            _fail("closed_calibration_required", "/assay_context/calibration")
        factor = calibration["response_per_product_concentration"]
        if _number(factor) is None or factor <= 0:
            _fail("positive_calibration_response_required", "/assay_context/calibration/response_per_product_concentration")
        if calibration["applicability"] not in {"supported", "unknown", "conflicting", "unsupported"}:
            _fail("calibration_applicability_required", "/assay_context/calibration/applicability")
        if type(calibration["curve_ordinals"]) is not list or any(type(i) is not int or i < 0 for i in calibration["curve_ordinals"]):
            _fail("original_curve_ordinals_required", "/assay_context/calibration/curve_ordinals")
        for name in ("signal_unit", "product_concentration_unit", "source_ref"):
            if type(calibration[name]) is not str or not calibration[name].strip():
                _fail("calibration_source_and_units_required", "/assay_context/calibration/" + name)
    return deepcopy(raw)


def _population(measurements):
    issues = []
    arrays = {}
    for name in ("time_points", "fluorescence_data", "substrate_concentrations"):
        value = measurements[name]
        arrays[name] = value if type(value) is list else None
        if type(value) is not list:
            issues.append({"code": "one_dimensional_array_required" if name != "fluorescence_data" else "curve_rows_required", "field": "/measurements/" + name})
    times, curves, substrates = (arrays[k] for k in ("time_points", "fluorescence_data", "substrate_concentrations"))
    nt = len(times) if times is not None else None
    ns = len(substrates) if substrates is not None else None
    requested = max(5, int(nt * .2)) if nt is not None else None
    indices = list(range(min(nt, requested))) if nt is not None else []
    for name, values in (("time_points", times), ("substrate_concentrations", substrates)):
        if values is not None:
            for i, value in enumerate(values):
                if _number(value) is None:
                    issues.append({"code": "finite_binary64_measurement_required", "field": f"/measurements/{name}/{i}"})
    rows = []
    for i in range(ns or 0):
        present = curves is not None and i < len(curves)
        curve = curves[i] if present else None
        state = "curve_missing" if not present else "present"
        if present and (type(curve) is not list or nt is None or len(curve) != nt):
            state = "invalid_curve_shape"
        if present and type(curve) is list and any(_number(v) is None for v in curve):
            state = "invalid_curve_values"
        if state != "present":
            issues.append({"code": state, "field": f"/measurements/fluorescence_data/{i}"})
        rows.append({"substrate_ordinal": i, "curve_ordinal": i if present else None, "curve_state": state,
            "native_vector_ordinal": i, "initial_window_indices": list(indices)})
    if curves is not None and ns is not None and len(curves) != ns:
        issues.append({"code": "curve_substrate_population_mismatch", "field": "/measurements/fluorescence_data"})
    if not times or len({times[i] for i in indices if _number(times[i]) is not None}) < 2:
        issues.append({"code": "distinct_initial_time_coordinates_unavailable", "field": "/measurements/time_points"})
    if ns == 0:
        issues.append({"code": "empty_substrate_population", "field": "/measurements/substrate_concentrations"})
    complete = not issues
    negative = [i for i, s in enumerate(substrates or []) if _number(s) is not None and s < 0]
    for i in negative:
        issues.append({"code": "negative_substrate_concentration", "field": f"/measurements/substrate_concentrations/{i}"})
    return {"time_point_count": nt, "substrate_count": ns, "supplied_curve_count": len(curves) if curves is not None else None,
        "requested_initial_point_count": requested, "actual_initial_point_count": len(indices), "rows": rows,
        "complete_supplied_curve_population": complete, "negative_substrate_ordinals": negative,
        "replicate_independence_inferred": False}, issues


def _closed(value, fields, field):
    if type(value) is not dict or set(value) != set(fields):
        _fail("closed_native_protocol_required", field)


def _path(value, field):
    if type(value) is not str or not value or any(c in value for c in "\0\n\r\\"):
        _fail("canonical_absolute_path_required", field)
    path = PurePosixPath(value)
    if not path.is_absolute() or str(path) != value or ".." in path.parts or value == "/":
        _fail("canonical_absolute_path_required", field)
    return path


def _pin(value, field):
    _closed(value, {"path", "sha256", "size_bytes"}, field)
    _path(value["path"], field + "/path")
    digest = value["sha256"]
    if type(digest) is not str or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        _fail("native_file_pin_required", field)
    if type(value["size_bytes"]) is not int or value["size_bytes"] < 0:
        _fail("native_file_pin_required", field)


def _native_request(request):
    _closed(request, {"version", "operation", "arguments", "deployment", "output_workspace", "environment"}, "/native_observation/request")
    if request["version"] != "molecular_sequence_request_v3" or request["operation"] != OPERATION:
        _fail("native_operation_conflict", "/native_observation/request")
    _closed(request["arguments"], MEASUREMENT_FIELDS | {"output_prefix", "output_dir"}, "/native_observation/request/arguments")
    prefix = request["arguments"]["output_prefix"]
    if type(prefix) is not str or not prefix or prefix in {".", ".."} or any(c in prefix for c in "/\\\0\n\r"):
        _fail("native_output_basename_required", "/native_observation/request/arguments/output_prefix")
    workspace = _path(request["output_workspace"], "/native_observation/request/output_workspace")
    output = _path(request["arguments"]["output_dir"], "/native_observation/request/arguments/output_dir")
    if not output.is_relative_to(workspace):
        _fail("native_output_workspace_conflict", "/native_observation/request")
    env = request["environment"]
    _closed(env, {"MPLBACKEND", "MPLCONFIGDIR", "XDG_CACHE_HOME"}, "/native_observation/request/environment")
    if env["MPLBACKEND"] != "Agg":
        _fail("native_environment_conflict", "/native_observation/request/environment/MPLBACKEND")
    for name in ("MPLCONFIGDIR", "XDG_CACHE_HOME"):
        if not _path(env[name], "/native_observation/request/environment/" + name).is_relative_to(workspace):
            _fail("native_environment_conflict", "/native_observation/request/environment/" + name)
    deployment = request["deployment"]
    _closed(deployment, {"version", "runtime", "module", "import_roots", "software_files_ref", "software_files_file"}, "/native_observation/request/deployment")
    if deployment["version"] != "molecular_sequence_deployment_v3":
        _fail("native_deployment_version_required", "/native_observation/request/deployment/version")
    _closed(deployment["runtime"], {"executable", "home"}, "/native_observation/request/deployment/runtime")
    _pin(deployment["runtime"]["executable"], "/native_observation/request/deployment/runtime/executable")
    _path(deployment["runtime"]["home"], "/native_observation/request/deployment/runtime/home")
    for name in ("module", "software_files_file"):
        _pin(deployment[name], "/native_observation/request/deployment/" + name)
    if deployment["module"]["sha256"] != SOURCE_FILE_SHA256:
        _fail("native_source_conflict", "/native_observation/request/deployment/module")
    if deployment["software_files_ref"] != "artifact_" + deployment["software_files_file"]["sha256"]:
        _fail("native_manifest_identity_conflict", "/native_observation/request/deployment/software_files_ref")
    roots = deployment["import_roots"]
    if type(roots) is not list or not roots or any(type(root) is not str for root in roots) or len(set(roots)) != len(roots):
        _fail("native_import_roots_required", "/native_observation/request/deployment/import_roots")
    for root in roots:
        _path(root, "/native_observation/request/deployment/import_roots")


def _native(capture, measurements):
    fields = {"version", "request", "request_canonical_sha256", "stage", "native_record", "native_call_state",
        "reference_data", "execution_receipt", "stdout", "stderr", "failure", "observer", "verification_failures"}
    if type(capture) is not dict or set(capture) != fields or capture.get("version") != CAPTURE_VERSION:
        _fail("protease_native_capture_required", "/native_observation")
    request = capture.get("request")
    if request is not None:
        _native_request(request)
        args = request["arguments"]
        if not MEASUREMENT_FIELDS <= set(args) or not _same({k: args[k] for k in MEASUREMENT_FIELDS}, measurements):
            _fail("native_measurement_conflict", "/native_observation/request/arguments")
        encoded = json.dumps(request, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        if capture["request_canonical_sha256"] != hashlib.sha256(encoded).hexdigest():
            _fail("native_request_digest_conflict", "/native_observation/request_canonical_sha256")
    elif capture.get("native_call_state") != "not_started":
        _fail("native_request_unavailable", "/native_observation/request")
    record = capture.get("native_record")
    if record is not None:
        _closed(record, {"schema", "outcome", "result_kind", "result", "failure", "source_identity"}, "/native_observation/native_record")
        if record["schema"] != "biomni_protease_kinetics_native_v1":
            _fail("native_record_schema_required", "/native_observation/native_record/schema")
    if capture["native_call_state"] not in {"not_started", "returned", "raised"}:
        _fail("native_terminal_state_required", "/native_observation/native_call_state")
    if capture["native_call_state"] != "not_started" and (type(record) is not dict or record.get("source_identity") is None):
        _fail("observed_native_source_required", "/native_observation/native_record")
    if capture["native_call_state"] == "not_started" and record is not None and (
            record["outcome"] != "not_called" or any(record[name] is not None for name in ("result", "result_kind", "failure"))):
        _fail("uncalled_native_outcome_conflict", "/native_observation/native_record")
    if record is not None and record.get("source_identity") is not None:
        source = record["source_identity"]
        _closed(source, {"path", "callable", "sha256"}, "/native_observation/native_record/source_identity")
        if source.get("callable") != OPERATION or source.get("sha256") != SOURCE_FUNCTION_SHA256 or request is None or source["path"] != request["deployment"]["module"]["path"]:
            _fail("native_source_conflict", "/native_observation/native_record/source_identity")
    if capture["native_call_state"] == "returned":
        text = record.get("result")
        if type(text) is not str:
            _fail("native_string_return_required", "/native_observation/native_record/result")
        source_error = type(text) is str and text.startswith("Error during analysis:")
        expected = "source_error" if source_error else "completed"
        if record.get("outcome") != expected or record.get("failure") is not None or capture["failure"] is not None:
            _fail("native_return_outcome_conflict", "/native_observation/native_record")
        if record.get("result_kind") != ("source_error_string" if source_error else "analysis_report"):
            _fail("native_error_string_conflict", "/native_observation/native_record/result_kind")
    if capture["native_call_state"] == "raised" and (record.get("outcome") != "raised" or record.get("failure") is None or record["result"] is not None or record["result_kind"] is not None
            or not _same(record["failure"], capture["failure"])):
        _fail("native_exception_outcome_conflict", "/native_observation/native_record")
    observer = capture.get("observer")
    _closed(observer, {"schema", "mechanism", "state", "reason", "selected_call_count", "selected_terminal_event_count",
        "profile_restored", "locals", "failures"}, "/native_observation/observer")
    if (observer["schema"] != "native_selected_return_observation_v1" or observer["mechanism"] != "selected_code_return_profile"
            or type(observer.get("locals")) is not dict or type(observer["failures"]) is not list
            or type(capture["verification_failures"]) is not list):
        _fail("native_observer_record_required", "/native_observation/observer")
    if observer["state"] not in {"not_started", "observing", "captured", "unavailable", "failed"} or any(
            type(observer[name]) is not int or not 0 <= observer[name] <= 1 for name in ("selected_call_count", "selected_terminal_event_count")):
        _fail("single_native_observation_required", "/native_observation/observer")
    if observer.get("state") == "captured" and (observer.get("selected_call_count") != 1 or observer.get("selected_terminal_event_count") != 1):
        _fail("single_native_observation_required", "/native_observation/observer")
    values = {k: _decode(v) for k, v in observer["locals"].items()}
    for name in MEASUREMENT_FIELDS:
        if name in values and not _same(values[name], measurements[name]):
            _fail("observed_native_input_conflict", "/native_observation/observer/locals/" + name)
    if "num_points" in values and type(measurements["time_points"]) is list and values["num_points"] != max(5, int(len(measurements["time_points"])*.2)):
        _fail("native_initial_window_conflict", "/native_observation/observer/locals/num_points")
    params = values.get("params")
    if type(params) is list and len(params) == 2:
        for i, name in enumerate(("vmax", "km")):
            if name in values and not _same(params[i], values[name]):
                _fail("native_parameter_alias_conflict", "/native_observation/observer/locals/" + name)
    return deepcopy(capture)


def populate_protease_kinetics_sheet(*, native_capture, measurements, assay_context=None):
    measurements = _copy(measurements)
    if type(measurements) is not dict or set(measurements) != MEASUREMENT_FIELDS:
        _fail("closed_protease_measurements_required", "/measurements")
    capture, context = _native(_copy(native_capture), measurements), _context(_copy(assay_context))
    population, issues = _population(measurements)
    if context["replicate_ids"] is not None and len(context["replicate_ids"]) != population["substrate_count"]:
        _fail("replicate_population_conflict", "/assay_context/replicate_ids")
    for row in population["rows"]:
        row["replicate_id"] = None if context["replicate_ids"] is None else context["replicate_ids"][row["substrate_ordinal"]]
    return {"schema": SHEET_SCHEMA, "source_method": deepcopy(SOURCE_METHOD),
        "numeric_interpretation": "retained_native_dtype_and_binary64_calculation", "measurements": measurements,
        "assay_context": context, "native_observation": capture, "population": population,
        "issues": issues, "qualifications": list(QUALIFICATIONS)}


def validate_protease_kinetics_sheet(sheet):
    value = _copy(sheet)
    if type(value) is not dict or set(value) != SHEET_FIELDS or value.get("schema") != SHEET_SCHEMA:
        _fail("protease_sheet_required", "/")
    expected = populate_protease_kinetics_sheet(native_capture=value["native_observation"],
        measurements=value["measurements"], assay_context=value["assay_context"])
    if not _same(value, expected):
        _fail("inconsistent_protease_sheet", "/")
    return expected


def _cell(value, unit, formula, *, origin="derived_saved_native_fit", reason=None, uncertainty=None, fields=()):
    if value is not None and _number(value) is None:
        value, reason = None, "nonfinite_or_unrepresentable_calculation"
    if uncertainty is not None and uncertainty.get("state") in {"present", "qualified"}:
        uncertainty = dict(uncertainty, standard_uncertainty_unit=unit, variance_unit=unit + " squared" if unit else None)
    return {"value": value, "unit": unit, "unit_state": "unknown" if unit is None else "declared_or_derived",
        "state": "unavailable" if value is None else "present", "reason": reason, "origin": origin,
        "formula_id": formula, "input_fields": list(fields),
        "uncertainty": uncertainty or {"state": "unavailable", "reason": "not_supplied_or_estimated"}}


def _covariance(value):
    assessment = {"schema": "protease_covariance_assessment_v1", "native_symmetry": "unavailable",
        "symmetric_part_positive_semidefinite": None, "assessment_arithmetic": "exact_rational_retained_entries",
        "propagation_basis": "symmetric_bilinear_part_of_observed_native_matrix",
        "statistical_covariance_validity": "unestablished", "qualifications": []}
    neutral = assess_bivariate_covariance(value)
    if neutral["status"] == "shape_invalid":
        return None, "native_covariance_unavailable", assessment
    if neutral["status"] == "entry_not_finite_binary64":
        return None, "native_covariance_nonfinite", assessment
    assessment["native_symmetry"] = neutral["symmetry"]
    if assessment["native_symmetry"] == "asymmetric":
        assessment["qualifications"].append("asymmetric_reported_matrix_bilinear_estimate_not_verified_statistical_covariance")
    if neutral["status"] == "symmetric_part_indefinite":
        assessment["symmetric_part_positive_semidefinite"] = False
        return None, "native_covariance_symmetric_part_indefinite", assessment
    assessment["symmetric_part_positive_semidefinite"] = True
    return value, None, assessment


def _uncertainty(gradient, matrix, reason, assessment):
    if matrix is None:
        return {"state": "unavailable", "reason": reason}
    try:
        neutral = propagate_bivariate_variance(gradient, matrix)
        if neutral["status"] != "present":
            return {"state": "unavailable", "reason": {
                "negative": "propagated_variance_negative",
                "overflow": "propagated_variance_overflow",
                "positive_underflow": "propagated_variance_positive_underflow",
                "numerical_range": "propagated_variance_numerical_range"}[neutral["status"]]}
        qualified = assessment["native_symmetry"] == "asymmetric"
        return {"state": "qualified" if qualified else "present", "variance": neutral["variance"],
            "standard_uncertainty": neutral["standard_uncertainty"],
            "method": "first_order_exact_reported_matrix_symmetric_bilinear_form", "parameter_order": ["vmax", "km"],
            "variance_status": "qualified_reported_matrix_bilinear_estimate" if qualified else "estimated",
            "covariance_basis": assessment["propagation_basis"], "native_matrix_symmetry": assessment["native_symmetry"],
            "statistical_covariance_validity": assessment["statistical_covariance_validity"],
            "qualifications": list(assessment["qualifications"]),
            "scope": "fit_only_conditional_on_held_calibration_enzyme_and_stoichiometry",
            "total_uncertainty": None, "total_uncertainty_reason": "calibration_enzyme_and_joint_relationships_unknown"}
    except OverflowError:
        return {"state": "unavailable", "reason": "propagated_variance_overflow"}
    except (ArithmeticError, ValueError):
        return {"state": "unavailable", "reason": "propagated_variance_numerical_range"}


def calculate_protease_kinetics_components(sheet):
    value = validate_protease_kinetics_sheet(sheet)
    capture, context, population = value["native_observation"], value["assay_context"], value["population"]
    observer, record = capture["observer"], capture.get("native_record")
    native = {k: _decode(v) for k, v in observer["locals"].items()}
    units, params = context["units"], native.get("params")
    reason = "native_fit_parameters_unavailable" if capture["native_call_state"] == "not_started" else None
    if type(params) is not list or len(params) != 2 or any(_number(p) is None or p < 0 for p in params):
        reason = reason or "native_fit_parameters_unavailable"
    qualifications = []
    if capture["native_call_state"] == "raised":
        qualifications.append("native_call_raised_after_observed_values")
    if record is not None and record.get("outcome") == "source_error":
        qualifications.append("native_source_returned_error_string")
    if observer["failures"]:
        qualifications.append("observer_has_separately_recorded_failures")
    if capture["verification_failures"]:
        qualifications.append("native_implementation_verification_incomplete")
    if not population["complete_supplied_curve_population"]:
        qualifications.append("native_fit_population_incompatible")
    if population["negative_substrate_ordinals"]:
        qualifications.append("negative_substrate_concentration")
    velocities = native.get("initial_velocities")
    n = population["substrate_count"]
    rate_reason = ("native_rate_vector_unavailable" if type(velocities) is not list or len(velocities) != n
        or any(_number(v) is None for v in velocities) else None)
    matrix, covariance_reason, covariance_assessment = _covariance(native.get("covariance"))
    vmax, km = params if reason is None else (None, None)
    substrates = value["measurements"]["substrate_concentrations"]
    model_reason = reason or ("native_substrate_vector_unavailable" if type(substrates) is not list or any(_number(s) is None for s in substrates) else None)
    rate_unit = units["signal"] + "/" + units["time"] if units["signal"] and units["time"] else None
    fit = {"state": "qualified" if reason is None and qualifications else "present" if reason is None else "unavailable", "reason": reason,
        "qualifications": qualifications, "complete_population_eligible": population["complete_supplied_curve_population"],
        "vmax": _cell(vmax, rate_unit, "observed_native_params_0", origin="native_fitted", reason=reason,
            fields=["/native_observation/observer/locals/params", "/assay_context/units"]),
        "km": _cell(km, units["substrate"], "observed_native_params_1", origin="native_fitted", reason=reason,
            fields=["/native_observation/observer/locals/params", "/assay_context/units/substrate"]),
        "parameter_order": ["vmax", "km"], "covariance": deepcopy(native.get("covariance")),
        "covariance_parameter_units": [rate_unit, units["substrate"]],
        "covariance_state": "unavailable" if matrix is None else "qualified" if covariance_assessment["native_symmetry"] == "asymmetric" else "present",
        "covariance_reason": covariance_reason, "covariance_assessment": covariance_assessment,
        "native_diagonal_only_uncertainty": {k: deepcopy(native[k]) for k in
            ("vmax_std", "km_std", "kcat_std", "catalytic_efficiency_std") if k in native},
        "model_rows": [], "model_prediction_reason": model_reason, "residual_sum_squares": None,
        "native_n_minus_parameter_count_diagnostic": n - 2 if type(n) is int else None,
        "residual_degrees_of_freedom": None, "residual_degrees_of_freedom_reason": reason or rate_reason or
            ("native_fit_population_incompatible" if not population["complete_supplied_curve_population"] else
             "insufficient_residual_population" if n is None or n <= 2 else "residual_summary_unavailable")}
    if model_reason is None:
        residuals = []
        for i, substrate in enumerate(substrates):
            prediction = residual = None
            row = population["rows"][i]
            observed_slope = velocities[i] if rate_reason is None and row["curve_state"] == "present" else None
            row_reason = "zero_model_denominator" if km + substrate == 0 else None
            try:
                if row_reason is None:
                    prediction = vmax * substrate / (km + substrate)
                    if not math.isfinite(prediction):
                        raise ArithmeticError()
                    if observed_slope is not None:
                        residual = observed_slope - prediction
                        if not math.isfinite(residual):
                            raise ArithmeticError()
                        residuals.append(residual)
                    else:
                        row_reason = rate_reason or "native_vector_slot_has_no_measured_curve"
            except (ArithmeticError, OverflowError):
                prediction = residual = None
                row_reason = "model_numerical_range"
            fit["model_rows"].append({"substrate_ordinal": i, "curve_ordinal": row["curve_ordinal"],
                "curve_state": row["curve_state"], "native_fit_vector_value": velocities[i] if rate_reason is None else None,
                "observed_signal_slope": observed_slope, "prediction": prediction, "residual": residual, "reason": row_reason})
        if len(residuals) == n:
            try:
                ss = math.fsum(r*r for r in residuals)
                fit["residual_sum_squares"] = ss if math.isfinite(ss) else None
                if math.isfinite(ss) and population["complete_supplied_curve_population"] and n > 2:
                    fit["residual_degrees_of_freedom"] = n - 2
                    fit["residual_degrees_of_freedom_reason"] = None
            except (ArithmeticError, OverflowError):
                pass
    calibration = context["calibration"]
    physical_reason = reason or ("native_fit_population_incompatible" if not population["complete_supplied_curve_population"] else
        "negative_substrate_concentration" if population["negative_substrate_ordinals"] else
        "native_implementation_verification_incomplete" if capture["verification_failures"] else None)
    if physical_reason is None:
        physical_reason = ("calibration_not_supplied" if calibration is None else
            "calibration_applicability_" + calibration["applicability"] if calibration["applicability"] != "supported" else
            "calibration_curve_population_conflict" if calibration["curve_ordinals"] != list(range(n)) else
            "compatible_declared_units_required" if units["time"] != "s" or units["substrate"] != "uM" or units["enzyme"] != "uM"
                or units["signal"] is None or calibration["signal_unit"] != units["signal"] or calibration["product_concentration_unit"] != "uM" else None)
    physical = {}
    factor = calibration["response_per_product_concentration"] if calibration else None
    enzyme = _number(value["measurements"]["enzyme_concentration"])
    stoichiometry = context["product_per_cleavage"]
    def put(name, unit, formula, calculation, gradient, why):
        number = None
        uncertainty = None
        if why is None:
            try:
                exact = calculation()
                number = float(exact)
                if not math.isfinite(number):
                    number, why = None, "physical_ratio_overflow"
                elif exact > 0 and number == 0:
                    number, why = None, "physical_ratio_positive_underflow"
                if why is None:
                    uncertainty = _uncertainty(gradient(), matrix, covariance_reason, covariance_assessment)
                else:
                    uncertainty = {"state": "unavailable", "reason": why}
            except OverflowError:
                number, why = None, "physical_ratio_overflow"
                uncertainty = {"state": "unavailable", "reason": why}
            except (ArithmeticError, ValueError):
                why = "physical_calculation_numerical_range"
        physical[name] = _cell(number, unit, formula, reason=why, uncertainty=uncertainty,
            fields=["/native_observation/observer/locals/params", "/native_observation/observer/locals/covariance",
                "/assay_context/units", "/assay_context/calibration", "/measurements/enzyme_concentration",
                "/assay_context/enzyme_basis", "/assay_context/product_per_cleavage"])
    put("product_vmax", "uM/s", "native_vmax/calibration_response", lambda: Fraction(vmax)/Fraction(factor),
        lambda: [Fraction(1)/Fraction(factor), Fraction(0)], physical_reason)
    enzyme_reason = physical_reason or ("positive_enzyme_concentration_required" if enzyme is None or enzyme <= 0 else None)
    put("product_formation_per_enzyme_concentration", "s^-1", "native_vmax/(calibration_response*supplied_enzyme_concentration)",
        lambda: Fraction(vmax)/Fraction(factor)/Fraction(enzyme),
        lambda: [Fraction(1)/Fraction(factor)/Fraction(enzyme), Fraction(0)], enzyme_reason)
    turnover_reason = enzyme_reason or ("product_per_cleavage_unknown" if stoichiometry is None else None)
    put("apparent_turnover", "s^-1", "native_vmax/(calibration_response*enzyme*product_per_cleavage)",
        lambda: Fraction(vmax)/Fraction(factor)/Fraction(enzyme)/Fraction(stoichiometry),
        lambda: [Fraction(1)/Fraction(factor)/Fraction(enzyme)/Fraction(stoichiometry), Fraction(0)], turnover_reason)
    kcat_reason = turnover_reason or ("active_site_concentration_basis_unestablished" if context["enzyme_basis"] != "active_site_concentration" else None)
    put("kcat", "s^-1", "apparent_turnover_with_supplied_active_site_basis",
        lambda: Fraction(vmax)/Fraction(factor)/Fraction(enzyme)/Fraction(stoichiometry),
        lambda: [Fraction(1)/Fraction(factor)/Fraction(enzyme)/Fraction(stoichiometry), Fraction(0)], kcat_reason)
    for name, why in (("apparent_catalytic_efficiency", turnover_reason), ("catalytic_efficiency", kcat_reason)):
        why = why or ("positive_km_required" if km is None or km <= 0 else None)
        put(name, "uM^-1 s^-1", "turnover/native_km", lambda: Fraction(vmax)/Fraction(factor)/Fraction(enzyme)/Fraction(stoichiometry)/Fraction(km),
            lambda: [Fraction(1)/Fraction(factor)/Fraction(enzyme)/Fraction(stoichiometry)/Fraction(km),
                -Fraction(vmax)/Fraction(factor)/Fraction(enzyme)/Fraction(stoichiometry)/(Fraction(km)**2)], why)
    return {"schema": COMPONENTS_SCHEMA, "sheet_schema": SHEET_SCHEMA, "source_method": deepcopy(SOURCE_METHOD),
        "population": deepcopy(population), "native_values": native,
        "native_return": None if record is None else {k: deepcopy(record.get(k)) for k in ("outcome", "result_kind", "result", "failure")},
        "fit_components": fit, "physical_components": physical, "issues": deepcopy(value["issues"]),
        "qualifications": list(QUALIFICATIONS), "function_probability": None}


__all__ = ["SHEET_SCHEMA", "COMPONENTS_SCHEMA", "MEASUREMENT_FIELDS", "ProteaseKineticsContractError",
    "populate_protease_kinetics_sheet", "validate_protease_kinetics_sheet", "calculate_protease_kinetics_components"]
