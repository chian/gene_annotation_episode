"""Pure custody-neutral envelopes and literal views of the existing CD core.

The numerical sheet and calculator remain in circular_dichroism_measurements.
These contracts validate shapes and relationships and copy retained values;
they never evaluate spectral signs, thermal normalization, midpoint or width.
No validation here establishes a producer, receipt or permission to read a File.
"""
from copy import deepcopy
import json
import math
import re

from . import circular_dichroism_measurements as core


CD_TOOL = "analyze_circular_dichroism_spectra"
REQUEST_VERSION = "circular_dichroism_request_v1"
RESULT_VERSION = "ordinary_cd_result_v1"
RETURN_VERSION = "circular_dichroism_summary_v1"
VIEW_VERSION = "circular_dichroism_view_v1"
FACT_SOURCE = "circular_dichroism_summaries"
_SOURCE = re.compile(r"source_[0-9a-f]{24}\Z")
_ARTIFACT = re.compile(r"artifact_[0-9a-f]{64}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SIGNALS = ("mdeg", "delta_epsilon", "unknown")
_FEATURES = {sample: tuple(row[0] for row in rows) for sample, rows in core.SPECTRAL_FEATURES.items()}
_SIGNS = {row[0]: row[3] for rows in core.SPECTRAL_FEATURES.values() for row in rows}
_WINDOWS = {row[0]: list(row[1:3]) for rows in core.SPECTRAL_FEATURES.values() for row in rows}
_STRUCTURES = {"protein": ("predominantly alpha-helical", "predominantly beta-sheet",
    "mixed or predominantly random coil"), "nucleic_acid": ("G-quadruplex characteristics",
    "B-form characteristics", "non-standard structure")}
_COOPERATIVITY = ("highly cooperative (sharp transition)", "moderately cooperative",
    "non-cooperative (broad transition)")
ISSUE_CODES = ("expected_object", "unknown_field", "unsupported_measurement_schema", "unsupported_sample_type",
    "invalid_sample_key", "missing_spectrum", "coordinate_unit_required", "explicit_signal_unit_required",
    "missing_array", "expected_one_dimensional_list", "empty_array", "non_numeric_value", "nonfinite_value",
    "not_exactly_representable_binary64", "nonpositive_wavelength", "paired_length_mismatch",
    "nonpositive_measurement_wavelength", "zero_signal_range", "arithmetic_overflow")
_THERMAL_QUALIFICATIONS = ("signal_unit_unknown", "thermal_measurement_wavelength_unknown",
    "temperature_order_not_strictly_increasing", "binary64_temperature_steps_not_identical",
    "zero_endpoint_temperature_difference")
_METRICS = ("signal_minimum", "signal_maximum", "normalization_range", "sampled_midpoint_index",
    "sampled_midpoint_temperature", "transition_point_count", "source_endpoint_span_per_point", "source_transition_width")
_COUNT_NAMES = (*_SIGNS, "sampled_midpoint_index", "transition_point_count")
_OVERFLOW_NAMES = ("normalization_range", "source_endpoint_span_per_point", "source_transition_width")
_FORMULAS = {**{name: "count_inclusive_window_strict_sign" for name in _SIGNS},
    "signal_minimum": "minimum_supplied_signal", "signal_maximum": "maximum_supplied_signal",
    "normalization_range": "maximum_minus_minimum", "sampled_midpoint_index": "first_nearest_relative_signal_half",
    "sampled_midpoint_temperature": "temperature_at_sampled_midpoint_index",
    "transition_point_count": "count_strict_relative_window_0_2_0_8",
    "source_endpoint_span_per_point": "endpoint_temperature_difference_divided_by_N",
    "source_transition_width": "endpoint_temperature_difference_divided_by_N_times_transition_point_count",
    "relative_signal": "signal_minus_minimum_over_signal_range"}
_UNITS = {**{name: "sampled_points" for name in _SIGNS}, "sampled_midpoint_index": "zero_based_position",
    "sampled_midpoint_temperature": "degC", "transition_point_count": "sampled_points",
    "source_endpoint_span_per_point": "degC_per_sampled_point", "source_transition_width": "degC",
    "relative_signal": "dimensionless"}
_SIGNAL_METRICS = ("signal_minimum", "signal_maximum", "normalization_range")
_VIEW_KEYS = ("spectrum_ordinals", "thermal_ordinals", "issue_ordinals")
_CELL_KEYS = {"name", "value", "unit", "state", "reason", "formula_id", "input_fields", "numerator",
    "denominator", "origin", "uncertainty"}


def _fail(code):
    raise ValueError("circular_dichroism_" + code)


def _require(condition, code="contract_invalid"):
    if not condition:
        _fail(code)


def _copy(value, ancestors=()):
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        try: value.encode("utf-8")
        except UnicodeError: _fail("finite_json_required")
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if id(value) in ancestors:
        _fail("finite_json_required")
    if type(value) is list:
        return [_copy(item, (*ancestors, id(value))) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {_copy(key): _copy(item, (*ancestors, id(value))) for key, item in value.items()}
    _fail("finite_json_required")


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys))


def _integer(value, *, nullable=False):
    return value is None and nullable or type(value) is int and value >= 0


def _number(value, *, nullable=False):
    return value is None and nullable or type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def _enum_list(value, allowed):
    _require(type(value) is list and all(type(item) is str and item in allowed for item in value)
        and len(value) == len(set(value)))


def _indices(value, count):
    _require(type(value) is list and all(_integer(index) and index < count for index in value)
        and value == sorted(set(value)))


def _issue(value):
    _closed(value, ("code", "field"))
    _require(value["code"] in ISSUE_CODES and type(value["field"]) is str and value["field"].startswith("/"))


def _cell(value, *, name=None, unit=None, fields=None):
    _closed(value, _CELL_KEYS)
    actual = value["name"]
    _require(type(actual) is str and actual in _FORMULAS and (name is None or actual == name))
    expected_unit = unit if actual in _SIGNAL_METRICS else _UNITS[actual]
    _require(value["unit"] == expected_unit and expected_unit is not None
        and value["formula_id"] == _FORMULAS[actual]
        and value["origin"] == "derived_supplied_measurements"
        and _same(value["uncertainty"], {"state": "unavailable", "reason": "not_supplied_or_estimated"}))
    _require(type(value["input_fields"]) is list and all(type(item) is str and item.startswith("/")
        for item in value["input_fields"]))
    if fields is not None: _require(value["input_fields"] == fields)
    if value["state"] == "invalid_input":
        _require(actual in _OVERFLOW_NAMES and value["value"] is None and value["reason"] == "arithmetic_overflow")
    else:
        _require(value["state"] == "present" and value["reason"] is None
            and (_integer(value["value"]) if actual in _COUNT_NAMES else _number(value["value"])))
    if actual in (*_SIGNS, "transition_point_count"):
        _require(_same(value["numerator"], value["value"]) and value["denominator"] is None)
    elif actual == "source_endpoint_span_per_point":
        _require(_number(value["numerator"], nullable=True) and _integer(value["denominator"])
            and value["denominator"] > 0)
    elif actual == "relative_signal":
        _require(_number(value["numerator"]) and value["numerator"] >= 0
            and _number(value["denominator"]) and value["denominator"] > 0
            and 0 <= value["value"] <= 1)
    else:
        _require(value["numerator"] is None and value["denominator"] is None)
    if actual == "normalization_range" and value["value"] is not None:
        _require(value["value"] >= 0)


def _thermal_cells(rows, unit):
    _require(type(rows) is list)
    names = [row.get("name") if type(row) is dict else None for row in rows]
    _require(names in ([], list(_METRICS[:3]), list(_METRICS)))
    by_name = dict(zip(names, rows))
    for name, row in by_name.items():
        fields = (["/thermal/temperature_data", "/thermal/thermal_cd_data"] if name in {
            "sampled_midpoint_index", "source_transition_width"} else ["/thermal/temperature_data"]
            if name == "source_endpoint_span_per_point" else ["/thermal/thermal_cd_data"])
        if name == "sampled_midpoint_temperature":
            fields = [f'/thermal/temperature_data/{by_name["sampled_midpoint_index"]["value"]}', "/thermal/thermal_cd_data"]
        _cell(row, name=name, unit=unit, fields=fields)
    return by_name


def validate_circular_dichroism_tool_request(value):
    """Validate the selected input File capsule, without reading or admitting it."""
    value = _copy(value)
    _closed(value, ("version", "input_file"))
    _require(value["version"] == REQUEST_VERSION)
    file = value["input_file"]
    _closed(file, ("artifact_ref", "sha256", "size_bytes", "format"))
    _require(type(file["sha256"]) is str and _SHA.fullmatch(file["sha256"]) is not None
        and file["artifact_ref"] == "artifact_" + file["sha256"] and _integer(file["size_bytes"])
        and file["format"] == "json")
    return value


def _components(value, sheet):
    _closed(value, ("schema", "sheet_schema", "source_method", "sample_key", "sample_type", "array_coordinates",
        "spectrum", "thermal", "issues", "qualifications"))
    measurements = sheet["measurements"]
    supplied = core._restore(measurements["supplied"])
    raw = supplied if type(supplied) is dict else {}
    _require(value["schema"] == core.COMPONENTS_SCHEMA and value["sheet_schema"] == sheet["schema"]
        and _same(value["source_method"], sheet["source_method"])
        and _same(value["sample_key"], measurements["sample_key"])
        and _same(value["sample_type"], measurements["sample_type"])
        and value["array_coordinates"] == sheet["array_coordinates"]
        and _same(value["qualifications"], sheet["qualifications"]))
    spectrum, block = value["spectrum"], measurements["spectrum"]
    usable = measurements["method_known"] and measurements["sample_type"] is not None and block["state"] == "present"
    if not usable:
        _closed(spectrum, ("state", "features", "source_structure_label"))
        _require(spectrum["state"] == (block["state"] if block["state"] != "present" else "incompatible")
            and spectrum["features"] == [] and spectrum["source_structure_label"] is None)
    else:
        _closed(spectrum, ("state", "features", "source_structure_label", "qualifications"))
        names = _FEATURES[measurements["sample_type"]]
        _require(spectrum["state"] == "present" and type(spectrum["features"]) is list
            and [row.get("name") if type(row) is dict else None for row in spectrum["features"]] == list(names)
            and spectrum["source_structure_label"] in _STRUCTURES[measurements["sample_type"]])
        for row, name in zip(spectrum["features"], names):
            _closed(row, ("name", "window_nm", "sign", "population_indices", "selected_indices", "count",
                "population_count", "count_denominator"))
            _require(_same(row["window_nm"], _WINDOWS[name])
                and row["sign"] == _SIGNS[name] and row["count_denominator"] is None)
            _indices(row["population_indices"], block["coordinate_count"])
            _indices(row["selected_indices"], block["coordinate_count"])
            _require(set(row["selected_indices"]) <= set(row["population_indices"])
                and type(row["population_count"]) is int and row["population_count"] == len(row["population_indices"]))
            _cell(row["count"], name=name, fields=["/spectrum/wavelength_data", "/spectrum/cd_signal_data"])
            _require(row["count"]["value"] == len(row["selected_indices"]))
        _require(spectrum["qualifications"] == (["signal_unit_unknown"] if raw["spectrum"]["signal_unit"] == "unknown" else []))
    thermal, block = value["thermal"], measurements["thermal"]
    basic = {"state", "summary", "relative_signal", "source_cooperativity_label", "qualifications", "issues"}
    usable = measurements["method_known"] and block["state"] == "present"
    if not usable:
        _closed(thermal, basic)
        _require(thermal["state"] == (block["state"] if block["state"] != "present" else "incompatible")
            and thermal["summary"] == [] and thermal["relative_signal"] == []
            and thermal["source_cooperativity_label"] is None and thermal["qualifications"] == [] and thermal["issues"] == [])
    else:
        _require(type(thermal) is dict)
        _closed(thermal, basic | ({"transition_point_indices", "endpoint_temperature_difference", "width_divisor_point_count"}
            if "transition_point_indices" in thermal else set()))
        _enum_list(thermal["qualifications"], _THERMAL_QUALIFICATIONS)
        _require(type(thermal["issues"]) is list)
        for issue in thermal["issues"]: _issue(issue)
        unit, count = raw["thermal"]["signal_unit"], block["coordinate_count"]
        cells = _thermal_cells(thermal["summary"], unit)
        _require(len(cells) in (3, 8))
        full = "transition_point_indices" in thermal
        if not full:
            _closed(thermal, basic)
            _require(thermal["state"] == "partial" and len(cells) == 3 and thermal["relative_signal"] == []
                and thermal["source_cooperativity_label"] is None and len(thermal["issues"]) == 1
                and thermal["issues"][0]["field"] == "/thermal/thermal_cd_data"
                and thermal["issues"][0]["code"] in ("zero_signal_range", "arithmetic_overflow"))
            range_cell = cells["normalization_range"]
            _require(range_cell["value"] == 0 if thermal["issues"][0]["code"] == "zero_signal_range"
                else range_cell["value"] is None)
        else:
            _closed(thermal, basic | {"transition_point_indices", "endpoint_temperature_difference", "width_divisor_point_count"})
            _require(len(cells) == 8 and type(thermal["relative_signal"]) is list and len(thermal["relative_signal"]) == count
                and type(thermal["width_divisor_point_count"]) is int and thermal["width_divisor_point_count"] == count
                and _number(thermal["endpoint_temperature_difference"], nullable=True))
            _indices(thermal["transition_point_indices"], count)
            _require(cells["transition_point_count"]["value"] == len(thermal["transition_point_indices"]))
            midpoint = cells["sampled_midpoint_index"]["value"]
            _require(midpoint < count and _same(cells["sampled_midpoint_temperature"]["value"],
                float(raw["thermal"]["temperature_data"][midpoint])))
            _require(_same(cells["source_endpoint_span_per_point"]["numerator"], thermal["endpoint_temperature_difference"])
                and cells["source_endpoint_span_per_point"]["denominator"] == count)
            for index, row in enumerate(thermal["relative_signal"]):
                _closed(row, ("index", "relative_signal"))
                _require(type(row["index"]) is int and row["index"] == index)
                _cell(row["relative_signal"], name="relative_signal", fields=[f"/thermal/thermal_cd_data/{index}", "/thermal/thermal_cd_data"])
                _require(_same(row["relative_signal"]["denominator"], cells["normalization_range"]["value"]))
            complete = thermal["endpoint_temperature_difference"] is not None and cells["source_transition_width"]["value"] is not None
            _require(thermal["state"] == ("present" if complete else "partial")
                and (thermal["source_cooperativity_label"] in _COOPERATIVITY if complete else thermal["source_cooperativity_label"] is None)
                and thermal["issues"] == ([] if complete else [{"code": "arithmetic_overflow", "field": "/thermal/temperature_data"}]))
    _require(type(value["issues"]) is list and _same(value["issues"], measurements["issues"] + thermal["issues"]))
    for issue in value["issues"]: _issue(issue)


def validate_circular_dichroism_components_shape(value, *, sheet):
    """Check saved cells and array relationships, without evaluating CD arithmetic."""
    value = _copy(value)
    _components(value, core.validate_circular_dichroism_sheet(sheet))
    return value


def validate_circular_dichroism_tool_result(value):
    """Validate the literal four-field result; this confers no Source authority."""
    value = _copy(value)
    _closed(value, ("version", "request", "sheet", "components"))
    _require(value["version"] == RESULT_VERSION)
    value["request"] = validate_circular_dichroism_tool_request(value["request"])
    value["sheet"] = core.validate_circular_dichroism_sheet(value["sheet"])
    _components(value["components"], value["sheet"])
    return value


def _view_selection(value):
    if value is None: return {name: [] for name in _VIEW_KEYS}
    _closed(value, _VIEW_KEYS)
    _require(all(type(value[name]) is list and all(_integer(x) for x in value[name]) for name in _VIEW_KEYS), "view_invalid")
    return deepcopy(value)


def validate_circular_dichroism_tool_arguments(value):
    value = _copy(value)
    _require(type(value) is dict and value.get("mode") in ("calculate", "read_stored", "calculate_saved"), "arguments_invalid")
    if value["mode"] == "calculate":
        _closed(value, ("mode", "input", "view")); _closed(value["input"], ("namespace", "reference"))
        namespace, reference = value["input"]["namespace"], value["input"]["reference"]
        _require(type(reference) is str and (namespace == "source" and _SOURCE.fullmatch(reference)
            or namespace == "artifact" and _ARTIFACT.fullmatch(reference)), "arguments_invalid")
    else:
        _closed(value, ("mode", "result_ref", "view"))
        _require(type(value["result_ref"]) is str and _SOURCE.fullmatch(value["result_ref"]), "arguments_invalid")
    _view_selection(value["view"])
    return value


def _signal_unit(raw):
    value = raw.get("signal_unit") if type(raw) is dict else None
    return value if type(value) is str and value in _SIGNALS else None


def _measurement_wavelength(raw, issues):
    if type(raw) is not dict: return None
    value = raw.get("measurement_wavelength_nm")
    if value is None: return dict(state="not_supplied", value=None, unit="nm", reason="not_supplied")
    codes = [item["code"] for item in issues if item["field"] == "/thermal/measurement_wavelength_nm"]
    if codes:
        return dict(state="invalid_input", value=value if codes[0] == "nonpositive_measurement_wavelength" else None,
            unit="nm", reason=codes[0])
    return dict(state="present", value=deepcopy(value), unit="nm", reason=None)


def _summary(stored, source_ref):
    _require(type(source_ref) is str and _SOURCE.fullmatch(source_ref) is not None, "return_source_invalid")
    sheet, components = stored["sheet"], stored["components"]
    measurements = sheet["measurements"]; restored = core._restore(measurements["supplied"])
    raw = restored if type(restored) is dict else {}
    spectral, thermal = components["spectrum"], components["thermal"]
    sm, tm = measurements["spectrum"], measurements["thermal"]
    return dict(version=RETURN_VERSION, source_ref=source_ref, sample_key=components["sample_key"], sample_type=components["sample_type"],
        spectrum=dict(state=spectral["state"], wavelength_count=sm["coordinate_count"], signal_count=sm["signal_count"],
            signal_unit=_signal_unit(raw.get("spectrum")), features=[{key: deepcopy(row[key]) for key in (
                "name", "window_nm", "sign", "count", "population_count", "count_denominator")} for row in spectral["features"]],
            source_structure_label=spectral["source_structure_label"], qualifications=deepcopy(spectral.get("qualifications"))),
        thermal=dict(state=thermal["state"], temperature_count=tm["coordinate_count"], signal_count=tm["signal_count"],
            signal_unit=_signal_unit(raw.get("thermal")), measurement_wavelength=_measurement_wavelength(raw.get("thermal"), measurements["issues"]),
            summary=deepcopy(thermal["summary"]), endpoint_temperature_difference=deepcopy(thermal.get("endpoint_temperature_difference")),
            width_divisor_point_count=thermal.get("width_divisor_point_count"), source_cooperativity_label=thermal["source_cooperativity_label"],
            qualifications=deepcopy(thermal["qualifications"])),
        issue_codes=sorted({issue["code"] for issue in components["issues"]}), qualifications=deepcopy(components["qualifications"]))


def project_circular_dichroism_return(stored, *, source_ref):
    """Copy the original full-population summary, independent of every row view."""
    result = _summary(validate_circular_dichroism_tool_result(stored), source_ref)
    return validate_circular_dichroism_return(result)


def validate_circular_dichroism_return(value):
    """Validate a literal frozen summary without a sheet, File or calculator."""
    value = _copy(value)
    _closed(value, ("version", "source_ref", "sample_key", "sample_type", "spectrum", "thermal", "issue_codes", "qualifications"))
    _require(value["version"] == RETURN_VERSION and type(value["source_ref"]) is str
        and _SOURCE.fullmatch(value["source_ref"]) is not None, "return_invalid")
    _require(value["sample_key"] is None or type(value["sample_key"]) is str and bool(value["sample_key"].strip()))
    _require(value["sample_type"] in (None, "protein", "nucleic_acid") and _same(value["qualifications"], core.QUALIFICATIONS))
    _enum_list(value["issue_codes"], ISSUE_CODES)
    _require(value["issue_codes"] == sorted(value["issue_codes"]))
    spectrum = value["spectrum"]
    _closed(spectrum, ("state", "wavelength_count", "signal_count", "signal_unit", "features", "source_structure_label", "qualifications"))
    _require(spectrum["state"] in ("present", "missing_input", "invalid_input", "incompatible")
        and all(_integer(spectrum[key], nullable=True) for key in ("wavelength_count", "signal_count"))
        and spectrum["signal_unit"] in (None, *_SIGNALS) and type(spectrum["features"]) is list)
    if spectrum["state"] != "present":
        _require(spectrum["features"] == [] and spectrum["source_structure_label"] is None and spectrum["qualifications"] is None)
    else:
        sample = value["sample_type"]
        _require(sample in _FEATURES and [row.get("name") if type(row) is dict else None for row in spectrum["features"]] == list(_FEATURES[sample])
            and spectrum["source_structure_label"] in _STRUCTURES[sample] and spectrum["signal_unit"] in _SIGNALS
            and type(spectrum["wavelength_count"]) is int and spectrum["wavelength_count"] == spectrum["signal_count"] > 0
            and spectrum["qualifications"] == (["signal_unit_unknown"] if spectrum["signal_unit"] == "unknown" else []))
        for row in spectrum["features"]:
            _closed(row, ("name", "window_nm", "sign", "count", "population_count", "count_denominator"))
            _require(_same(row["window_nm"], _WINDOWS[row["name"]])
                and row["sign"] == _SIGNS[row["name"]] and row["count_denominator"] is None
                and _integer(row["population_count"]) and row["population_count"] <= spectrum["wavelength_count"])
            _cell(row["count"], name=row["name"], fields=["/spectrum/wavelength_data", "/spectrum/cd_signal_data"])
            _require(row["count"]["value"] <= row["population_count"])
    thermal = value["thermal"]
    _closed(thermal, ("state", "temperature_count", "signal_count", "signal_unit", "measurement_wavelength", "summary",
        "endpoint_temperature_difference", "width_divisor_point_count", "source_cooperativity_label", "qualifications"))
    _require(thermal["state"] in ("present", "partial", "not_supplied", "invalid_input", "incompatible")
        and all(_integer(thermal[key], nullable=True) for key in ("temperature_count", "signal_count", "width_divisor_point_count"))
        and thermal["signal_unit"] in (None, *_SIGNALS) and _number(thermal["endpoint_temperature_difference"], nullable=True))
    wavelength = thermal["measurement_wavelength"]
    if wavelength is not None:
        _closed(wavelength, ("state", "value", "unit", "reason")); _require(wavelength["unit"] == "nm")
        if wavelength["state"] == "present": _require(_number(wavelength["value"]) and wavelength["value"] > 0 and wavelength["reason"] is None)
        elif wavelength["state"] == "not_supplied": _require(wavelength["value"] is None and wavelength["reason"] == "not_supplied")
        else:
            _require(wavelength["state"] == "invalid_input" and wavelength["reason"] in (
                "non_numeric_value", "nonfinite_value", "not_exactly_representable_binary64", "nonpositive_measurement_wavelength"))
            _require(_number(wavelength["value"]) and wavelength["value"] <= 0 if wavelength["reason"] == "nonpositive_measurement_wavelength" else wavelength["value"] is None)
    _enum_list(thermal["qualifications"], _THERMAL_QUALIFICATIONS)
    cells = _thermal_cells(thermal["summary"], thermal["signal_unit"])
    if thermal["state"] in ("not_supplied", "invalid_input", "incompatible"):
        _require(not cells and thermal["endpoint_temperature_difference"] is None and thermal["width_divisor_point_count"] is None
            and thermal["source_cooperativity_label"] is None and thermal["qualifications"] == [])
    else:
        _require(len(cells) in (3, 8) and thermal["signal_unit"] in _SIGNALS
            and type(thermal["temperature_count"]) is int and thermal["temperature_count"] == thermal["signal_count"] > 0)
        if len(cells) == 3:
            _require(thermal["state"] == "partial" and thermal["endpoint_temperature_difference"] is None
                and thermal["width_divisor_point_count"] is None and thermal["source_cooperativity_label"] is None)
        else:
            count = thermal["temperature_count"]
            _require(thermal["width_divisor_point_count"] == count and cells["sampled_midpoint_index"]["value"] < count
                and cells["transition_point_count"]["value"] <= count
                and cells["source_endpoint_span_per_point"]["denominator"] == count
                and _same(cells["source_endpoint_span_per_point"]["numerator"], thermal["endpoint_temperature_difference"]))
            _require(thermal["source_cooperativity_label"] in _COOPERATIVITY if thermal["state"] == "present"
                else thermal["source_cooperativity_label"] is None)
    return value


def _raw_cell(block, key, index, issues, unit):
    rows = block.get(key) if type(block) is dict else None
    if type(rows) is not list or index >= len(rows):
        return dict(state="missing", input_kind="missing", value=None, unit=unit, issue_codes=[])
    raw = rows[index]
    kind = {type(None): "null", bool: "boolean", int: "integer", float: "number", str: "string", list: "array", dict: "object"}.get(type(raw), "unsupported")
    codes = [issue["code"] for issue in issues if issue["field"] == f"/{'spectrum' if key in ('wavelength_data', 'cd_signal_data') else 'thermal'}/{key}/{index}"]
    invalid = bool(codes) or not _number(raw)
    retained = raw if not invalid or codes == ["nonpositive_wavelength"] else None
    return dict(state="invalid_input" if invalid else "present", input_kind=kind, value=deepcopy(retained), unit=unit, issue_codes=codes)


def _availability(block, keys, index):
    counts = [len(block[key]) for key in keys if type(block) is dict and type(block.get(key)) is list]
    return "unavailable" if not counts else "present" if index < max(counts) else "out_of_range"


def project_circular_dichroism_view(stored, *, source_ref, view):
    """Select literal original ordinals; selections never change source metrics."""
    stored = validate_circular_dichroism_tool_result(stored)
    selection = _view_selection(view); result = _summary(stored, source_ref)
    measurements = stored["sheet"]["measurements"]; supplied = core._restore(measurements["supplied"])
    raw = supplied if type(supplied) is dict else {}; issues = stored["components"]["issues"]
    spectrum, thermal = raw.get("spectrum"), raw.get("thermal")
    sr, tr, ir = [], [], []
    for index in selection["spectrum_ordinals"]:
        sr.append(dict(ordinal=index, availability=_availability(spectrum, ("wavelength_data", "cd_signal_data"), index),
            wavelength=_raw_cell(spectrum, "wavelength_data", index, issues, "nm" if type(spectrum) is dict and spectrum.get("wavelength_unit") == "nm" else None),
            signal=_raw_cell(spectrum, "cd_signal_data", index, issues, _signal_unit(spectrum))))
    rows = {row["index"]: row["relative_signal"] for row in stored["components"]["thermal"]["relative_signal"]}
    selected = stored["components"]["thermal"].get("transition_point_indices")
    for index in selection["thermal_ordinals"]:
        tr.append(dict(ordinal=index, availability=_availability(thermal, ("temperature_data", "thermal_cd_data"), index),
            temperature=_raw_cell(thermal, "temperature_data", index, issues, "degC" if type(thermal) is dict and thermal.get("temperature_unit") == "degC" else None),
            signal=_raw_cell(thermal, "thermal_cd_data", index, issues, _signal_unit(thermal)),
            relative_signal=deepcopy(rows.get(index)), in_source_transition_window=index in selected if index in rows and selected is not None else None))
    for index in selection["issue_ordinals"]:
        ir.append(dict(ordinal=index, availability="present" if index < len(issues) else "out_of_range", issue=deepcopy(issues[index]) if index < len(issues) else None))
    return validate_circular_dichroism_view(dict(version=VIEW_VERSION, source_ref=source_ref, summary=result,
        selection=selection, spectrum_rows=sr, thermal_rows=tr, issues=ir))


def validate_circular_dichroism_view(value):
    value = _copy(value)
    _closed(value, ("version", "source_ref", "summary", "selection", "spectrum_rows", "thermal_rows", "issues"))
    _require(value["version"] == VIEW_VERSION)
    summary = validate_circular_dichroism_return(value["summary"])
    _require(value["source_ref"] == summary["source_ref"])
    _require(type(value["selection"]) is dict)
    selection = _view_selection(value["selection"])
    kinds = ("missing", "null", "boolean", "integer", "number", "string", "array", "object", "unsupported")
    for name, selectors, fields in (("spectrum_rows", "spectrum_ordinals", ("wavelength", "signal")),
            ("thermal_rows", "thermal_ordinals", ("temperature", "signal"))):
        rows = value[name]
        _require(type(rows) is list and len(rows) == len(selection[selectors]))
        block = summary["spectrum" if name == "spectrum_rows" else "thermal"]
        counts = (block["wavelength_count" if name == "spectrum_rows" else "temperature_count"], block["signal_count"])
        for index, row in zip(selection[selectors], rows):
            _closed(row, ("ordinal", "availability", *fields, *( ("relative_signal", "in_source_transition_window") if name == "thermal_rows" else ())))
            _require(type(row["ordinal"]) is int and row["ordinal"] == index
                and row["availability"] in ("present", "unavailable", "out_of_range"))
            known = [count for count in counts if count is not None]
            _require(row["availability"] == ("unavailable" if not known else "present" if index < max(known) else "out_of_range"))
            for field, count in zip(fields, counts):
                cell = row[field]; _closed(cell, ("state", "input_kind", "value", "unit", "issue_codes"))
                _require(cell["state"] in ("present", "missing", "invalid_input") and cell["input_kind"] in kinds
                    and _number(cell["value"], nullable=True)
                    and cell["unit"] in ((None, *_SIGNALS) if field == "signal" else (None, "nm" if field == "wavelength" else "degC")))
                _require(field != "signal" or cell["unit"] == block["signal_unit"])
                _require((cell["state"] == "missing") == (count is None or index >= count))
                _enum_list(cell["issue_codes"], ISSUE_CODES)
                if cell["state"] == "missing": _require(cell["input_kind"] == "missing" and cell["value"] is None and cell["issue_codes"] == [])
                elif cell["state"] == "present":
                    _require(cell["input_kind"] in ("integer", "number") and cell["value"] is not None
                        and type(cell["value"]) is (int if cell["input_kind"] == "integer" else float) and not cell["issue_codes"])
                elif cell["value"] is not None: _require(cell["issue_codes"] == ["nonpositive_wavelength"] and cell["value"] <= 0)
            if name == "thermal_rows":
                derived = _thermal_cells(summary["thermal"]["summary"], summary["thermal"]["signal_unit"])
                _require((row["relative_signal"] is not None) == (len(derived) == 8 and index < counts[0]))
                if row["relative_signal"] is None: _require(row["in_source_transition_window"] is None)
                else:
                    _cell(row["relative_signal"], name="relative_signal", fields=[f"/thermal/thermal_cd_data/{index}", "/thermal/thermal_cd_data"])
                    _require(type(row["in_source_transition_window"]) is bool and _same(
                        row["relative_signal"]["denominator"], derived["normalization_range"]["value"]))
    _require(type(value["issues"]) is list and len(value["issues"]) == len(selection["issue_ordinals"]))
    for index, row in zip(selection["issue_ordinals"], value["issues"]):
        _closed(row, ("ordinal", "availability", "issue")); _require(type(row["ordinal"]) is int and row["ordinal"] == index)
        if row["availability"] == "present":
            _issue(row["issue"])
            _require(row["issue"]["code"] in summary["issue_codes"])
        else: _require(row["availability"] == "out_of_range" and row["issue"] is None)
    return value


def _obj(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _nullable(node):
    return {"anyOf": [node, {"type": "null"}]}


def _array(node):
    return dict(type="array", items=node)


def _enum(values):
    return {"enum": list(values)}


def _cell_schema(name):
    integer = {"type": "integer", "minimum": 0}; number = {"type": "number"}
    value = integer if name in _COUNT_NAMES else number
    if name in _OVERFLOW_NAMES: value = _nullable(value)
    return _obj(dict(name={"const": name}, value=value,
        unit=_enum(_SIGNALS) if name in _SIGNAL_METRICS else {"const": _UNITS[name]},
        state=_enum(("present", "invalid_input") if name in _OVERFLOW_NAMES else ("present",)),
        reason=_enum((None, "arithmetic_overflow") if name in _OVERFLOW_NAMES else (None,)), formula_id={"const": _FORMULAS[name]},
        input_fields=_array({"type": "string", "pattern": "^/"}),
        numerator=_nullable(integer if name in (*_SIGNS, "transition_point_count") else number)
            if name in (*_SIGNS, "transition_point_count", "source_endpoint_span_per_point", "relative_signal") else {"type": "null"},
        denominator=integer if name == "source_endpoint_span_per_point" else number if name == "relative_signal" else {"type": "null"},
        origin={"const": "derived_supplied_measurements"},
        uncertainty=_obj(dict(state={"const": "unavailable"}, reason={"const": "not_supplied_or_estimated"}))))


def circular_dichroism_return_schema():
    count = {"type": "integer", "minimum": 0}; number = {"type": "number"}
    feature = _obj(dict(name=_enum(_SIGNS), window_nm=dict(type="array", items={"type": "integer", "minimum": 1}, minItems=2, maxItems=2,
        enum=deepcopy(list(_WINDOWS.values()))),
        sign=_enum(("positive", "negative")), count={"anyOf": [_cell_schema(name) for name in _SIGNS]},
        population_count=count, count_denominator={"type": "null"}))
    wavelength = _obj(dict(state=_enum(("present", "not_supplied", "invalid_input")), value=_nullable(number), unit={"const": "nm"},
        reason=_enum((None, "not_supplied", "non_numeric_value", "nonfinite_value", "not_exactly_representable_binary64", "nonpositive_measurement_wavelength"))))
    return _obj(dict(version={"const": RETURN_VERSION},
        source_ref={"type": "string", "format": "reference", "x-reference-namespace": "source", "pattern": "^source_[0-9a-f]{24}$"},
        sample_key=_nullable({"type": "string", "minLength": 1}), sample_type=_enum((None, "protein", "nucleic_acid")),
        spectrum=_obj(dict(state=_enum(("present", "missing_input", "invalid_input", "incompatible")), wavelength_count=_nullable(count),
            signal_count=_nullable(count), signal_unit=_enum((None, *_SIGNALS)), features=_array(feature),
            source_structure_label=_enum((None, *(label for labels in _STRUCTURES.values() for label in labels))),
            qualifications=_nullable(_array(_enum(("signal_unit_unknown",)))))),
        thermal=_obj(dict(state=_enum(("present", "partial", "not_supplied", "invalid_input", "incompatible")), temperature_count=_nullable(count),
            signal_count=_nullable(count), signal_unit=_enum((None, *_SIGNALS)), measurement_wavelength=_nullable(wavelength),
            summary=_array({"anyOf": [_cell_schema(name) for name in _METRICS]}), endpoint_temperature_difference=_nullable(number),
            width_divisor_point_count=_nullable(count), source_cooperativity_label=_enum((None, *_COOPERATIVITY)),
            qualifications=_array(_enum(_THERMAL_QUALIFICATIONS)))),
        issue_codes=_array(_enum(ISSUE_CODES)), qualifications=_array(_enum(core.QUALIFICATIONS))))


def circular_dichroism_fact_sources():
    return {FACT_SOURCE: dict(type="array", meaning=("Literal full-original-population CD summaries from a retained Source. "
        "Spectral values are signed sampled-point counts; thermal values are source-defined relative-signal/sample-midpoint/N-point-width heuristics. "
        "No calibrated structure fractions, fitted thermodynamics or function-confidence probabilities. Selected views do not change these summaries."),
        report_schema=dict(type="array", items=circular_dichroism_return_schema(), **{"x-source": FACT_SOURCE}))}


def circular_dichroism_tool_argument_schema():
    index = {"type": "integer", "minimum": 0}
    view = _nullable(_obj({name: _array(index) for name in _VIEW_KEYS}))
    source = {"type": "string", "pattern": "^source_[0-9a-f]{24}$"}
    return {"anyOf": [_obj(dict(mode={"const": "calculate"}, input={"anyOf": [
        _obj(dict(namespace={"const": "source"}, reference=source)),
        _obj(dict(namespace={"const": "artifact"}, reference={"type": "string", "pattern": "^artifact_[0-9a-f]{64}$"}))]}, view=view)),
        _obj(dict(mode=_enum(("read_stored", "calculate_saved")), result_ref=source, view=deepcopy(view)))]}


__all__ = ["CD_TOOL", "REQUEST_VERSION", "RESULT_VERSION", "RETURN_VERSION", "VIEW_VERSION", "FACT_SOURCE", "ISSUE_CODES",
    "validate_circular_dichroism_tool_arguments", "circular_dichroism_tool_argument_schema",
    "validate_circular_dichroism_tool_request", "validate_circular_dichroism_components_shape", "validate_circular_dichroism_tool_result",
    "project_circular_dichroism_return", "validate_circular_dichroism_return", "circular_dichroism_return_schema",
    "circular_dichroism_fact_sources", "project_circular_dichroism_view", "validate_circular_dichroism_view"]
