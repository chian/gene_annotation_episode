"""Pure supplied-measurement CD sheets and inspectable source heuristics.

Inputs are JSON records with ``schema``, optional ``sample_key``, ``sample_type``
(``protein`` or ``nucleic_acid``), ``spectrum`` and optional ``thermal``. Spectrum
records contain ordered ``wavelength_data``/``cd_signal_data`` arrays,
``wavelength_unit='nm'`` and an explicit ``signal_unit``. Thermal records contain
ordered ``temperature_data``/``thermal_cd_data`` arrays, ``temperature_unit='degC'``,
``signal_unit`` and optional nullable ``measurement_wavelength_nm``. Signal units
are ``mdeg``, ``delta_epsilon`` or explicitly ``unknown``; no conversion occurs.
Numeric operands have an explicit binary64 interpretation. Integers that cannot
be represented exactly in binary64 are retained but unavailable to calculation.

This is componentwise calculation of the Biomni source's descriptive arithmetic,
not execution of that function. Counts are sampled-point counts, not structure
fractions. Min/max normalization is relative signal, not an unfolding fraction.
The sampled midpoint and source width/labels are not fitted melting parameters.
No calibration, baseline, concentration, uncertainty or confidence is invented.
There is no acquisition, file access, fitting, native call or episode behavior.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math


INPUT_SCHEMA = "circular_dichroism_measurements_v1"
SHEET_SCHEMA = "circular_dichroism_sheet_v1"
COMPONENTS_SCHEMA = "circular_dichroism_components_v1"
_TAG = "$cd_retained_invalid_value"
_OBJECT_TAG = "$cd_retained_object"
_SIGNAL_UNITS = {"mdeg", "delta_epsilon", "unknown"}
SOURCE_METHOD = {
    "callable": "biomni.tool.biochemistry.analyze_circular_dichroism_spectra",
    "source_function_sha256": "1e4d9fd3ae96b71c6c124b530aa4c5d8364ec641edc75bd8d20fae86ee65ab1d",
    "calculation": "source_heuristics_from_supplied_binary64_measurements",
    "native_execution": False,
}
QUALIFICATIONS = [
    "source_labels_are_heuristics_not_calibrated_secondary_structure",
    "sign_counts_depend_on_supplied_baseline_sampling_density_and_duplicates",
    "no_baseline_or_calibration_correction_performed",
    "relative_signal_is_not_a_measured_unfolded_fraction",
    "sampled_midpoint_is_not_a_fitted_melting_temperature",
    "source_width_uses_endpoint_difference_and_N_points_not_N_minus_1_intervals",
    "no_replicate_uncertainty_or_gene_function_probability",
]


class CircularDichroismContractError(ValueError):
    def __init__(self, code, field):
        self.issue = {"code": code, "field": field}
        super().__init__(f"{code}:{field}")


class _Unsupported:
    def __init__(self, kind):
        self.kind = kind


def _retain(value, ancestors=()):
    """Keep valid JSON values exact and locate invalid native values safely."""
    if type(value) is float and not math.isfinite(value):
        return {_TAG: {"kind": "nonfinite_float", "token": value.hex()}}
    if type(value) is int and value.bit_length() > 1024:
        return {_TAG: {"kind": "large_integer", "token": hex(value)}}
    if value is None or type(value) in (str, bool, int, float):
        return value
    if isinstance(value, _Unsupported):
        return {_TAG: {"kind": "unsupported_type", "token": value.kind}}
    if id(value) in ancestors:
        return {_TAG: {"kind": "unsupported_type", "token": "cyclic_value"}}
    if type(value) is list:
        return [_retain(item, (*ancestors, id(value))) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        result = {key: _retain(item, (*ancestors, id(value))) for key, item in value.items()}
        return {_OBJECT_TAG: result} if _TAG in value or _OBJECT_TAG in value else result
    return {_TAG: {"kind": "unsupported_type", "token": type(value).__name__}}


def _restore(value):
    if type(value) is dict and set(value) == {_OBJECT_TAG}:
        if type(value[_OBJECT_TAG]) is not dict:
            raise CircularDichroismContractError("invalid_retained_value", "/measurements/supplied")
        return {key: _restore(item) for key, item in value[_OBJECT_TAG].items()}
    if type(value) is dict and set(value) == {_TAG}:
        row = value[_TAG]
        if type(row) is not dict or set(row) != {"kind", "token"} or type(row["token"]) is not str:
            raise CircularDichroismContractError("invalid_retained_value", "/measurements/supplied")
        if row["kind"] == "nonfinite_float" and row["token"] in {"nan", "inf", "-inf"}:
            return float.fromhex(row["token"])
        if row["kind"] == "large_integer":
            return int(row["token"], 16)
        if row["kind"] == "unsupported_type":
            return _Unsupported(row["token"])
        raise CircularDichroismContractError("invalid_retained_value", "/measurements/supplied")
    if type(value) is dict:
        return {key: _restore(item) for key, item in value.items()}
    if type(value) is list:
        return [_restore(item) for item in value]
    return value


def _issue(code, field):
    return {"code": code, "field": field}


def _number_reason(value):
    if type(value) not in (int, float):
        return "non_numeric_value"
    try:
        number = float(value)
    except OverflowError:
        return "not_exactly_representable_binary64"
    if not math.isfinite(number):
        return "nonfinite_value"
    if type(value) is int and number != value:
        return "not_exactly_representable_binary64"
    return None


def _array(value, field, issues):
    if value is None:
        issues.append(_issue("missing_array", field))
        return None
    if type(value) is not list:
        issues.append(_issue("expected_one_dimensional_list", field))
        return None
    if not value:
        issues.append(_issue("empty_array", field))
    for index, item in enumerate(value):
        reason = _number_reason(item)
        if reason is not None:
            issues.append(_issue(reason, f"{field}/{index}"))
    return len(value)


def _block(value, *, thermal):
    name = "thermal" if thermal else "spectrum"
    field = "/" + name
    if value is None:
        return {"state": "not_supplied" if thermal else "missing_input", "coordinate_count": None,
            "signal_count": None, "issues": [] if thermal else [_issue("missing_spectrum", field)]}
    if type(value) is not dict or any(type(key) is not str for key in value):
        return {"state": "invalid_input", "coordinate_count": None, "signal_count": None,
            "issues": [_issue("expected_object", field)]}
    coordinate, signal, unit, expected_unit = (("temperature_data", "thermal_cd_data", "temperature_unit", "degC")
        if thermal else ("wavelength_data", "cd_signal_data", "wavelength_unit", "nm"))
    allowed = {coordinate, signal, unit, "signal_unit"} | ({"measurement_wavelength_nm"} if thermal else set())
    issues = [_issue("unknown_field", field + "/" + key) for key in value if key not in allowed]
    if value.get(unit) != expected_unit:
        issues.append(_issue("coordinate_unit_required", field + "/" + unit))
    if type(value.get("signal_unit")) is not str or value["signal_unit"] not in _SIGNAL_UNITS:
        issues.append(_issue("explicit_signal_unit_required", field + "/signal_unit"))
    nc = _array(value.get(coordinate), field + "/" + coordinate, issues)
    ns = _array(value.get(signal), field + "/" + signal, issues)
    if not thermal and nc is not None:
        for index, wavelength in enumerate(value[coordinate]):
            if _number_reason(wavelength) is None and wavelength <= 0:
                issues.append(_issue("nonpositive_wavelength", field + "/" + coordinate + "/" + str(index)))
    if nc is not None and ns is not None and nc != ns:
        issues.append(_issue("paired_length_mismatch", field))
    if thermal and value.get("measurement_wavelength_nm") is not None:
        wavelength = value["measurement_wavelength_nm"]
        reason = _number_reason(wavelength)
        if reason is not None or wavelength <= 0:
            issues.append(_issue(reason or "nonpositive_measurement_wavelength", field + "/measurement_wavelength_nm"))
    return {"state": "invalid_input" if issues else "present", "coordinate_count": nc,
        "signal_count": ns, "issues": issues}


def validate_circular_dichroism_measurements(measurements):
    """Return retained data and located failures; retain independent valid parts.

    The contract accepts parsed JSON lists, not ndarray broadcasting semantics.
    Nonfinite values are retained as explicit tokens so the sheet stays JSON-safe.
    Unsupported Python objects retain their type, not an invented measurement.
    """
    supplied = _retain(measurements)
    valid_object = type(measurements) is dict and all(type(key) is str for key in measurements)
    value = measurements if valid_object else {}
    issues = [] if valid_object else [_issue("expected_object", "/")]
    allowed = {"schema", "sample_key", "sample_type", "spectrum", "thermal"}
    issues.extend(_issue("unknown_field", "/" + key) for key in value if key not in allowed)
    method_known = value.get("schema") == INPUT_SCHEMA
    if not method_known:
        issues.append(_issue("unsupported_measurement_schema", "/schema"))
    sample_type = value.get("sample_type")
    if type(sample_type) is not str or sample_type not in {"protein", "nucleic_acid"}:
        issues.append(_issue("unsupported_sample_type", "/sample_type"))
        sample_type = None
    sample_key = value.get("sample_key")
    if sample_key is not None and (type(sample_key) is not str or not sample_key.strip()):
        issues.append(_issue("invalid_sample_key", "/sample_key"))
        sample_key = None
    spectrum, thermal = (_block(value.get("spectrum"), thermal=False), _block(value.get("thermal"), thermal=True))
    return {"supplied": supplied, "method_known": method_known, "sample_key": sample_key,
        "sample_type": sample_type, "spectrum": spectrum, "thermal": thermal,
        "issues": issues + spectrum["issues"] + thermal["issues"]}


def populate_circular_dichroism_sheet(*, measurements):
    """Populate the retained measurement sheet without calculating CD results."""
    return {"schema": SHEET_SCHEMA, "source_method": deepcopy(SOURCE_METHOD),
        "numeric_interpretation": "binary64", "array_coordinates": "original_zero_based_position",
        "measurements": validate_circular_dichroism_measurements(measurements),
        "qualifications": list(QUALIFICATIONS)}


def validate_circular_dichroism_sheet(sheet):
    """Revalidate saved relationships; this does not authenticate source custody."""
    try:
        supplied = _restore(sheet["measurements"]["supplied"])
        expected = populate_circular_dichroism_sheet(measurements=supplied)
        same = json.dumps(sheet, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError) as error:
        raise CircularDichroismContractError("invalid_sheet", "/") from error
    if not same:
        raise CircularDichroismContractError("inconsistent_sheet", "/")
    return deepcopy(expected)


def _cell(name, value, *, unit, formula, fields, numerator=None, denominator=None,
          state="present", reason=None):
    return {"name": name, "value": value, "unit": unit, "state": state, "reason": reason,
        "formula_id": formula, "input_fields": fields, "numerator": numerator, "denominator": denominator,
        "origin": "derived_supplied_measurements", "uncertainty": {"state": "unavailable", "reason": "not_supplied_or_estimated"}}


def _spectrum(measurements, supplied):
    block = measurements["spectrum"]
    if not measurements["method_known"] or measurements["sample_type"] is None or block["state"] != "present":
        return {"state": block["state"] if block["state"] != "present" else "incompatible",
            "features": [], "source_structure_label": None}
    raw = supplied["spectrum"]
    wavelengths = [float(value) for value in raw["wavelength_data"]]
    signals = [float(value) for value in raw["cd_signal_data"]]
    windows = (("alpha_helix_sign_count", 190, 195, "positive"), ("beta_sheet_sign_count", 215, 220, "negative"),
        ("random_coil_sign_count", 195, 200, "negative")) if measurements["sample_type"] == "protein" else (
        ("g_quadruplex_sign_count", 290, 300, "positive"), ("b_form_sign_count", 270, 280, "positive"))
    features = []
    for name, lower, upper, sign in windows:
        population = [index for index, value in enumerate(wavelengths) if lower <= value <= upper]
        selected = [index for index in population if (signals[index] > 0 if sign == "positive" else signals[index] < 0)]
        features.append({"name": name, "window_nm": [lower, upper], "sign": sign,
            "population_indices": population, "selected_indices": selected,
            "count": _cell(name, len(selected), unit="sampled_points", formula="count_inclusive_window_strict_sign",
                fields=["/spectrum/wavelength_data", "/spectrum/cd_signal_data"], numerator=len(selected)),
            "population_count": len(population), "count_denominator": None})
    counts = [row["count"]["value"] for row in features]
    if measurements["sample_type"] == "protein":
        label = ("predominantly alpha-helical" if counts[0] > counts[1] and counts[0] > counts[2] else
            "predominantly beta-sheet" if counts[1] > counts[0] and counts[1] > counts[2] else
            "mixed or predominantly random coil")
    else:
        label = "G-quadruplex characteristics" if counts[0] > 0 else "B-form characteristics" if counts[1] > 0 else "non-standard structure"
    return {"state": "present", "features": features, "source_structure_label": label,
        "qualifications": ["signal_unit_unknown"] if raw["signal_unit"] == "unknown" else []}


def _thermal(measurements, supplied):
    block = measurements["thermal"]
    if not measurements["method_known"] or block["state"] != "present":
        return {"state": block["state"] if block["state"] != "present" else "incompatible",
            "summary": [], "relative_signal": [], "source_cooperativity_label": None, "qualifications": [], "issues": []}
    raw = supplied["thermal"]
    temperatures = [float(value) for value in raw["temperature_data"]]
    signals = [float(value) for value in raw["thermal_cd_data"]]
    fields = ["/thermal/thermal_cd_data"]
    minimum, maximum, n = min(signals), max(signals), len(signals)
    denominator = maximum - minimum
    cells = [_cell("signal_minimum", minimum, unit=raw["signal_unit"], formula="minimum_supplied_signal", fields=fields),
        _cell("signal_maximum", maximum, unit=raw["signal_unit"], formula="maximum_supplied_signal", fields=fields),
        _cell("normalization_range", denominator if math.isfinite(denominator) else None,
            unit=raw["signal_unit"], formula="maximum_minus_minimum", fields=fields,
            state="present" if math.isfinite(denominator) else "invalid_input",
            reason=None if math.isfinite(denominator) else "arithmetic_overflow")]
    qualifications = []
    if raw["signal_unit"] == "unknown": qualifications.append("signal_unit_unknown")
    if raw.get("measurement_wavelength_nm") is None: qualifications.append("thermal_measurement_wavelength_unknown")
    if any(right <= left for left, right in zip(temperatures, temperatures[1:])):
        qualifications.append("temperature_order_not_strictly_increasing")
    steps = [right - left for left, right in zip(temperatures, temperatures[1:])]
    if steps and any(step != steps[0] for step in steps[1:]): qualifications.append("binary64_temperature_steps_not_identical")
    if not math.isfinite(denominator) or denominator == 0:
        reason = "arithmetic_overflow" if not math.isfinite(denominator) else "zero_signal_range"
        return {"state": "partial", "summary": cells, "relative_signal": [], "source_cooperativity_label": None,
            "qualifications": qualifications, "issues": [_issue(reason, "/thermal/thermal_cd_data")]}
    relative = [(value - minimum) / denominator for value in signals]
    rows = [{"index": index, "relative_signal": _cell("relative_signal", value, unit="dimensionless",
        formula="signal_minus_minimum_over_signal_range", fields=[f"/thermal/thermal_cd_data/{index}", *fields],
        numerator=signals[index] - minimum, denominator=denominator)} for index, value in enumerate(relative)]
    midpoint = min(range(n), key=lambda index: abs(relative[index] - 0.5))
    selected = [index for index, value in enumerate(relative) if 0.2 < value < 0.8]
    span = temperatures[-1] - temperatures[0]
    span_per_point = span / n
    width = span_per_point * len(selected)
    cells.extend([
        _cell("sampled_midpoint_index", midpoint, unit="zero_based_position", formula="first_nearest_relative_signal_half",
            fields=["/thermal/temperature_data", *fields]),
        _cell("sampled_midpoint_temperature", temperatures[midpoint], unit="degC", formula="temperature_at_sampled_midpoint_index",
            fields=[f"/thermal/temperature_data/{midpoint}", *fields]),
        _cell("transition_point_count", len(selected), unit="sampled_points", formula="count_strict_relative_window_0_2_0_8",
            fields=fields, numerator=len(selected)),
        _cell("source_endpoint_span_per_point", span_per_point if math.isfinite(span_per_point) else None,
            unit="degC_per_sampled_point", formula="endpoint_temperature_difference_divided_by_N",
            fields=["/thermal/temperature_data"], numerator=span if math.isfinite(span) else None,
            denominator=n, state="present" if math.isfinite(span_per_point) else "invalid_input",
            reason=None if math.isfinite(span_per_point) else "arithmetic_overflow"),
        _cell("source_transition_width", width if math.isfinite(width) else None, unit="degC",
            formula="endpoint_temperature_difference_divided_by_N_times_transition_point_count",
            fields=["/thermal/temperature_data", *fields], state="present" if math.isfinite(width) else "invalid_input",
            reason=None if math.isfinite(width) else "arithmetic_overflow"),
    ])
    if span == 0: qualifications.append("zero_endpoint_temperature_difference")
    finite_width = math.isfinite(span) and math.isfinite(width)
    label = ("highly cooperative (sharp transition)" if width < 0.2 * span else
        "moderately cooperative" if width < 0.4 * span else "non-cooperative (broad transition)") if finite_width else None
    return {"state": "present" if finite_width else "partial", "summary": cells, "relative_signal": rows,
        "transition_point_indices": selected, "endpoint_temperature_difference": span if math.isfinite(span) else None,
        "width_divisor_point_count": n,
        "source_cooperativity_label": label, "qualifications": qualifications,
        "issues": [] if finite_width else [_issue("arithmetic_overflow", "/thermal/temperature_data")]}


def calculate_circular_dichroism_components(sheet):
    """Calculate only the declared source arithmetic from a validated saved sheet."""
    value = validate_circular_dichroism_sheet(sheet)
    measurements = value["measurements"]
    supplied = _restore(measurements["supplied"])
    spectrum, thermal = _spectrum(measurements, supplied), _thermal(measurements, supplied)
    return {"schema": COMPONENTS_SCHEMA, "sheet_schema": SHEET_SCHEMA, "source_method": deepcopy(SOURCE_METHOD),
        "sample_key": measurements["sample_key"], "sample_type": measurements["sample_type"],
        "array_coordinates": value["array_coordinates"], "spectrum": spectrum, "thermal": thermal,
        "issues": deepcopy(measurements["issues"]) + thermal["issues"], "qualifications": list(QUALIFICATIONS)}


__all__ = ["INPUT_SCHEMA", "SHEET_SCHEMA", "COMPONENTS_SCHEMA", "CircularDichroismContractError",
    "validate_circular_dichroism_measurements", "populate_circular_dichroism_sheet",
    "validate_circular_dichroism_sheet", "calculate_circular_dichroism_components"]
