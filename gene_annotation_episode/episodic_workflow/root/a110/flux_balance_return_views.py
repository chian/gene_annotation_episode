"""Requested FBA fact declarations and selection, without custody or calculation."""
from copy import deepcopy

from .flux_balance_result_contracts import (fba_result_schema, validate_fba_projection,
    validate_fba_saved_sheet_reference, _checked)
from .flux_balance_contracts import flux_balance_schema, validate_flux_balance_record
from .flux_balance_model_tools import flux_balance_model_schema, validate_flux_balance_model_view

__all__ = ["fba_fact_sources", "requested_fba_sources", "validate_fba_fact_values", "select_fba_return_facts"]

_SOURCES = {"flux_balance_measurements": ("FBAProjection",
    "Explicitly selected FBA native and calculated molecular model measurements, with original positions, populations, units and missing-data qualifications; no annotation probability."),
    "flux_balance_saved_sheets": ("FBASavedSheetReference",
    "Explicitly requested saved numerical-sheet identities for later selected recalculation; no grant of native or prior-source artifacts."),
    "flux_balance_failures": ("FBAResultIssue",
    "Recorded located FBA selection, capture, parse, calculation and return failures; no model-composed findings."),
    "flux_balance_model_views": ("View",
    "Explicitly selected original or effective native model collections, positions, populations and missing-data qualifications; no optimization or source permission."),
    "flux_balance_edited_models": ("File",
    "Explicitly requested validated edited model Files in the caller-selected SBML or Cobra JSON format; no implicit native or private-control artifacts.")}


def _edited_file(value):
    value = validate_flux_balance_record("File", value)
    if value["format"] not in {"sbml", "cobra_json"}:
        raise ValueError("fba_projection_shape_invalid:/edited_model/format")
    return value


def fba_fact_sources() -> dict:
    result = {}
    for source, (kind, meaning) in _SOURCES.items():
        if source == "flux_balance_model_views":
            schema = flux_balance_model_schema("View")
        elif source == "flux_balance_edited_models":
            schema = flux_balance_schema("File")
            schema["properties"]["format"] = {"enum": ["sbml", "cobra_json"]}
        else:
            schema = fba_result_schema(kind)
        if source in {"flux_balance_saved_sheets", "flux_balance_edited_models"}:
            schema["properties"]["artifact_ref"].update(format="reference", **{"x-reference-namespace": "artifact"})
        result[source] = {"type": "array", "meaning": meaning,
            "report_schema": {"type": "array", "items": schema, "x-source": source}}
    return result


def requested_fba_sources(schema: dict) -> tuple[str, ...]:
    if type(schema) is not dict or type(schema.get("properties")) is not dict:
        raise ValueError("fba_projection_shape_invalid:/return_schema")
    result = []
    for node in schema["properties"].values():
        if type(node) is not dict:
            raise ValueError("fba_projection_shape_invalid:/return_schema/properties")
        source = node.get("x-source")
        if type(source) is str and source.startswith("flux_balance_"):
            if source not in _SOURCES:
                raise ValueError("fba_projection_selection_mismatch:/return_schema/x-source")
            if source not in result:
                result.append(source)
    return tuple(result)


def validate_fba_fact_values(source: str, value: list) -> list:
    if type(source) is not str or source not in _SOURCES or type(value) is not list:
        raise ValueError("fba_projection_shape_invalid:/facts")
    validator = {"flux_balance_measurements": validate_fba_projection,
        "flux_balance_saved_sheets": validate_fba_saved_sheet_reference,
        "flux_balance_model_views": validate_flux_balance_model_view,
        "flux_balance_edited_models": _edited_file,
        "flux_balance_failures": lambda row: _checked(row, fba_result_schema("FBAResultIssue"), "fba_projection_shape_invalid")}[source]
    return [validator(row) for row in value]


def select_fba_return_facts(groups: dict, *, schema: dict) -> dict:
    if type(groups) is not dict:
        raise ValueError("fba_projection_shape_invalid:/groups")
    selected = {}
    for source in requested_fba_sources(schema):
        if source not in groups:
            raise ValueError("fba_return_requested_source_unavailable:/" + source)
        selected[source] = validate_fba_fact_values(source, groups[source])
    return deepcopy(selected)
