"""Literal grouped views of the existing ordinary ITC public results.

These functions neither authenticate custody nor read or calculate measurements.
Unknown or malformed packets remain outside this finite presentation profile.
"""
from collections.abc import Mapping
import json
import re

from .communication import plain
from .itc_binding_contracts import (
    PARAMETERS, PARAMETER_UNITS, REASONS, closed, copy_json, number,
    observed_number, require,
)
from .molecular_measurement_tools import (
    ROW_FIELDS, UNIT_CODES, validate_itc_parameter_return,
)


_FULL = "ordinary_itc_values_v1"
_PARTIAL = "ordinary_itc_partial_values_v1"
_RICH = "itc_parameter_return_v1"
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z")
_ARTIFACT = re.compile(r"artifact_[a-f0-9]{64}\Z")
_FIT_SCOPE = "retained_original_fit_vector_and_residual_population"
_ROW_UNITS = {
    "injection_volume": "litre", "syringe_ligand_concentration": "mol_per_litre",
    "retained_cell_fraction": "fraction", "macromolecule_concentration": "mol_per_litre",
    "ligand_concentration": "mol_per_litre", "bound_complex_concentration": "mol_per_litre",
    "predicted_heat": "joule", "corrected_heat": "joule", "residual": "joule",
}
_FULL_FIELDS = (
    "version", "mode", "source_ref", "native_file", "grading_ref", "parameters", "rows",
    "fit_call_state", "fit_call_count", "fit_call_scope", "this_operation_fit", "parameter_source",
    "residual_population_count", "residual_degrees_of_freedom", "sse", "selected_objective",
    "covariance_estimate", "fit_diagnostics_scope", "covariance_scope", "covariance_parameter_order",
    "covariance_parameter_units", "covariance_validity", "identifiability", "weighting",
    "independent_error_assumption", "absolute_sigma", "warning_locations", "failure_location",
)


def _reference(value, pattern):
    require(type(value) is str and pattern.fullmatch(value) is not None)


def _native_file(value):
    closed(value, ("artifact_ref", "format"))
    _reference(value["artifact_ref"], _ARTIFACT)
    require(value["format"] == "json")


def _cell(value, unit):
    closed(value, ("state", "value", "unit", "reason"))
    require(value["unit"] == unit)
    require((value["state"] == "present" and number(value["value"]) and value["reason"] is None)
        or (value["state"] == "unavailable" and value["value"] is None and value["reason"] in REASONS))


def _call(value, *, nullable=False):
    require(value["fit_call_scope"] == "retained_fit_observation")
    count = value["fit_call_count"]
    require(count is None or type(count) is int)
    pairs = (("not_started", 0), ("returned", 1), ("raised", 1), ("uncertain", None))
    require((value["fit_call_state"], count) in (pairs + ((None, None),) if nullable else pairs))


def _locations(value):
    warnings = value["warning_locations"]
    require(type(warnings) is list)
    for index, location in enumerate(warnings):
        closed(location, ("source_ref", "location", "occurrence"))
        require(location["source_ref"] == value["source_ref"] and location["location"] == "fit_warning"
            and type(location["occurrence"]) is int and location["occurrence"] == index)
    failure = value["failure_location"]
    if failure is not None:
        closed(failure, ("source_ref", "location", "occurrence"))
        require(failure["source_ref"] == value["source_ref"] and failure["location"] == "fit_failure"
            and type(failure["occurrence"]) is int and failure["occurrence"] == 0)


def _full(value):
    closed(value, _FULL_FIELDS)
    require(value["version"] == _FULL and value["mode"] in ("fit", "calculate_saved", "read_stored"))
    _reference(value["source_ref"], _SOURCE)
    _reference(value["grading_ref"], _ARTIFACT)
    _native_file(value["native_file"])
    closed(value["parameters"], PARAMETERS)
    for name in PARAMETERS:
        _cell(value["parameters"][name], UNIT_CODES[PARAMETER_UNITS[name]])
    require(value["parameter_source"] in ("fit_observation", "selected_parameters"))
    require(value["mode"] != "fit" or value["parameter_source"] == "fit_observation")
    _call(value)
    require(type(value["this_operation_fit"]) is bool
        and value["this_operation_fit"] == (value["mode"] == "fit"))
    require(type(value["rows"]) is list)
    ordinals, fields = [], None
    for row in value["rows"]:
        require(type(row) is dict and "injection_ordinal" in row
            and set(row) <= {"injection_ordinal", *ROW_FIELDS})
        ordinal = row["injection_ordinal"]
        require(type(ordinal) is int and ordinal >= 0)
        ordinals.append(ordinal)
        selected = set(row) - {"injection_ordinal"}
        require(fields is None or fields == selected)
        fields = selected
        for field in selected:
            _cell(row[field], _ROW_UNITS[field])
    require(len(ordinals) == len(set(ordinals)))
    weighting = value["weighting"]
    require(weighting in (None, "unweighted", "diagonal_sigma"))
    if weighting is None:
        require(value["absolute_sigma"] is None and value["independent_error_assumption"] is None)
    else:
        require(type(value["absolute_sigma"]) is bool)
        require(value["independent_error_assumption"] is (True if weighting == "diagonal_sigma" else None))
    count, degrees = value["residual_population_count"], value["residual_degrees_of_freedom"]
    if count is None:
        require(degrees is None and value["sse"] is None and value["selected_objective"] is None
            and value["fit_diagnostics_scope"] is None)
    else:
        require(type(count) is int and count >= 0 and type(degrees) is int and degrees == count - 3
            and weighting is not None and value["fit_diagnostics_scope"] == _FIT_SCOPE)
        _cell(value["sse"], "joule_squared")
        _cell(value["selected_objective"], "dimensionless" if weighting == "diagonal_sigma" else "joule_squared")
    require(value["covariance_parameter_order"] == list(PARAMETERS))
    require(value["covariance_parameter_units"] == [UNIT_CODES[PARAMETER_UNITS[name]] for name in PARAMETERS])
    covariance = value["covariance_estimate"]
    if covariance is None:
        require(value["covariance_scope"] is None)
    else:
        require(type(covariance) is list and value["covariance_scope"] == _FIT_SCOPE)
        for row in covariance:
            require(type(row) is list)
            for cell in row:
                observed_number(cell)
    require(value["covariance_validity"] == value["identifiability"] == "not_assessed")
    _locations(value)
    return value


def _partial(value):
    closed(value, ("version", "mode", "projection_state", "retained_sources"))
    require(value["version"] == _PARTIAL and value["mode"] in ("fit", "calculate_saved")
        and value["projection_state"] == "unavailable")
    require(type(value["retained_sources"]) is list and bool(value["retained_sources"]))
    for row in value["retained_sources"]:
        closed(row, ("source_ref", "native_file", "grading_ref", "fit_call_state", "fit_call_count", "fit_call_scope"))
        _reference(row["source_ref"], _SOURCE)
        _reference(row["grading_ref"], _ARTIFACT)
        _native_file(row["native_file"])
        _call(row, nullable=True)
    return value


def select_itc_binding_result(value):
    """Detach one exact public packet, without reading its Source or Files."""
    if not isinstance(value, Mapping) or value.get("version") not in (_FULL, _PARTIAL, _RICH):
        return None
    try:
        value = copy_json(plain(value))
        if value["version"] == _RICH:
            return validate_itc_parameter_return(value)
        return _full(value) if value["version"] == _FULL else _partial(value)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        return None


def _literal(value):
    return value if type(value) is str else json.dumps(value, ensure_ascii=False, allow_nan=False)


def _table(headers, rows):
    def escape(value):
        return _literal(value).replace("|", "\\|").replace("\n", "<br>")
    rows = list(rows)
    if not rows:
        return "[]"
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(escape(cell) for cell in row) + " |" for row in rows)])


def _section(parts, title, body):
    parts.extend(["", title, "", body])


def _cell_text(cell):
    if cell["state"] == "present":
        return _literal(cell["value"]) + " " + cell["unit"]
    return "unavailable; value=null; unit=" + cell["unit"] + "; reason=" + cell["reason"]


def _parameters(parts, parameters):
    _section(parts, "Retained parameter vector", _table(("Parameter", "Value", "Unit", "State", "Reason"),
        ((name, parameters[name]["value"], parameters[name]["unit"], parameters[name]["state"], parameters[name]["reason"])
            for name in PARAMETERS)))
    parts.extend(["", "Contract meaning: n is effective sites per declared macromolecule and participates in the physical binding balance."])


def _injections(parts, rows):
    parts.extend(["", "Present injection-cell entries show the exact value and unit; their state is present and reason is null. Unavailable entries retain their literal reason."])
    for title, fields in (("Selected heats and residuals", ("corrected_heat", "predicted_heat", "residual")),
            ("Selected injection and physical-state cells", tuple(name for name in ROW_FIELDS
                if name not in ("corrected_heat", "predicted_heat", "residual")))):
        selected = [name for name in fields if rows and name in rows[0]]
        if selected:
            _section(parts, title, _table(("Delivered injection ordinal", *selected),
                ((row["injection_ordinal"], *(_cell_text(row[field]) for field in selected)) for row in rows)))
    if not rows or not any(len(row) > 1 for row in rows):
        _section(parts, "Selected injection rows", _table(("Delivered injection ordinal",),
            ((row["injection_ordinal"],) for row in rows)))


def _covariance(parts, value):
    _section(parts, "Retained native covariance estimate", _table(("Property", "Literal value"), (
        ("Scope", value["covariance_scope"]), ("Declared parameter order", value["covariance_parameter_order"]),
        ("Declared parameter units", value["covariance_parameter_units"]),
        ("Statistical covariance validity", value["covariance_validity"]), ("Identifiability", value["identifiability"]))))
    parts.extend(["", "Contract meaning: these are the native local covariance-estimate cells. Row and column units form the entry's unit product; they are not standard errors, confidence intervals or established experimental covariance."])
    matrix = value["covariance_estimate"]
    if matrix is None or matrix == []:
        parts.extend(["", _literal(matrix)])
        return
    order, units, cells = value["covariance_parameter_order"], value["covariance_parameter_units"], []
    empty_rows = []
    for i, row in enumerate(matrix):
        row_name, row_unit = (order[i], units[i]) if i < len(order) else ("undeclared axis", "unknown")
        if not row:
            empty_rows.append(i)
        for j, cell in enumerate(row):
            column_name, column_unit = (order[j], units[j]) if j < len(order) else ("undeclared axis", "unknown")
            cells.append((i, row_name, j, column_name, cell["state"], cell["value"], row_unit, column_unit))
    parts.extend(["", _table(("Native row ordinal", "Declared row parameter", "Native column ordinal",
        "Declared column parameter", "State", "Value", "Row unit", "Column unit"), cells)])
    if empty_rows:
        parts.extend(["", "Recorded empty native row ordinals: " + _literal(empty_rows)])


def render_itc_binding_result(value, number):
    """Render supplied cells and qualifications; never fit or calculate them."""
    value = select_itc_binding_result(value)
    if value is None:
        raise ValueError("itc_binding_presentation_invalid")
    parts = ["Selected molecular result " + str(number), "", "ITC retained values"]
    version = value["version"]
    if version == _PARTIAL:
        _section(parts, "Projection availability", _table(("Property", "Literal value"),
            (("Mode", value["mode"]), ("Projection state", value["projection_state"]))))
        _section(parts, "Retained scientific outputs", _table(("Callable Source", "Native File", "Grading File",
            "Retained fit call state", "Retained fit call count", "Call scope"),
            ((row["source_ref"], row["native_file"], row["grading_ref"], row["fit_call_state"],
                row["fit_call_count"], row["fit_call_scope"]) for row in value["retained_sources"])))
        parts.extend(["", "The selected projection is unavailable. Retained fit observations do not supply missing parameter or injection cells in this packet."])
        return "\n".join(parts)
    association = [("Callable result Source", value["source_ref"]), ("Parameter source", value["parameter_source"])]
    if version == _FULL:
        association.extend((key, value[key]) for key in ("mode", "native_file", "grading_ref", "this_operation_fit", "fit_call_scope"))
    else:
        association.append(("Cell scope", value["cell_scope"]))
    _section(parts, "Result association and selection", _table(("Property", "Literal value"), association))
    _parameters(parts, value["parameters"] if version == _FULL else {name: value[name] for name in PARAMETERS})
    _section(parts, "Retained fit observation and error assumption", _table(("Property", "Literal value"),
        ((key, value[key]) for key in ("fit_call_state", "fit_call_count", "fit_diagnostics_scope", "weighting",
            "independent_error_assumption", "absolute_sigma"))))
    parts.extend(["", "The call state and count describe the retained fit observation. Saved calculation and literal read do not imply another fit."])
    if version == _FULL:
        _injections(parts, value["rows"])
        _section(parts, "Diagnostics for the retained original fitted vector and residual population", _table(
            ("Property", "Literal value"), (("Residual population count", value["residual_population_count"]),
                ("Residual degrees of freedom", value["residual_degrees_of_freedom"]),
                ("SSE", None if value["sse"] is None else value["sse"]),
                ("Selected objective", None if value["selected_objective"] is None else value["selected_objective"]))))
        _covariance(parts, value)
    else:
        _section(parts, "Retained qualifications", _table(("Property", "Literal value"),
            ((key, value[key]) for key in ("fit_qualification_codes", "prediction_qualification_codes",
                "calibration_authority", "n_meaning", "identifiability", "statistical_covariance_validity"))))
    _section(parts, "Retained warning locations", _literal(value["warning_locations"]))
    _section(parts, "Retained failure location", _literal(value["failure_location"]))
    return "\n".join(parts)


__all__ = ["select_itc_binding_result", "render_itc_binding_result"]
