"""Requested chromatin facts, separate from calculations and return authority.

These pure ports constrain existing records. They neither acquire measurements
nor establish that a receiving episode was given an artifact by its child.
"""
from __future__ import annotations

from copy import deepcopy
from jsonschema import Draft202012Validator

from .chromatin_interaction_contracts import (
    canonical_chromatin_record, chromatin_record_schema, validate_chromatin_record,
)
from .execution_contracts import digest


PROJECTION_SOURCE = "chromatin_interaction_projection"
SAVED_SOURCE = "chromatin_interaction_saved_sheets"
FAILURE_SOURCE = "chromatin_interaction_failures"
FACT_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE)
_RECORDS = {PROJECTION_SOURCE: "RequestedProjection", SAVED_SOURCE: "SavedSheetBundle",
            FAILURE_SOURCE: "Failure"}
_SHEET_FORMAT = "chromatin_interaction_sheet_v1"
_TABLE_FORMATS = tuple("chromatin_contact_tables_v1:" + role for role in
    ("bins", "contacts", "weights", "cell_states", "dense_values"))
_MEANINGS = {
    PROJECTION_SOURCE: "Exactly requested chromatin measurements, populations, denominators and qualifications; heuristic values retain their meaning.",
    SAVED_SOURCE: "Explicitly returned numerical sheet and complete table identities for later selected recalculation; no access to unrequested child outputs.",
    FAILURE_SOURCE: "Actual located chromatin input, capture, calculation or delivery failures, with their specific missing requirements.",
}


def _array_schema(source: str) -> dict:
    record = _RECORDS[source]
    base = chromatin_record_schema(record)
    schema = {"$schema": base["$schema"], "$defs": base["$defs"],
        "type": "array", "items": {"$ref": "#/$defs/" + record}, "x-source": source}
    if source == SAVED_SOURCE:
        definitions = schema["$defs"]
        identity = definitions["NativeFileIdentity"]
        identity["properties"]["artifact_ref"].update(
            format="reference", **{"x-reference-namespace": "artifact"})
        sheet_identity = deepcopy(identity)
        sheet_identity["properties"]["format"] = {"const": _SHEET_FORMAT}
        definitions["ChromatinSavedSheetIdentity"] = sheet_identity
        definitions[record]["properties"]["sheet"] = {
            "$ref": "#/$defs/ChromatinSavedSheetIdentity"}
        identity["properties"]["format"] = {"enum": list(_TABLE_FORMATS)}
    schema["$id"] = "urn:gene-annotation:chromatin:return:" + digest(schema)
    return schema


def chromatin_fact_sources() -> dict:
    return {source: {"type": "array", "meaning": _MEANINGS[source],
        "report_schema": _array_schema(source)} for source in FACT_SOURCES}


def chromatin_fact_schema_alternatives(source: str) -> tuple[dict, ...]:
    """Current tree and the single exact supported historical field tree."""
    if type(source) is not str or source not in FACT_SOURCES:
        raise ValueError("chromatin_return_unknown_source")
    current = _array_schema(source)
    if source == SAVED_SOURCE:
        return (current,)
    from .chromatin_interaction_legacy_return_schemas import legacy_chromatin_fact_schema
    legacy = legacy_chromatin_fact_schema(source)
    return (current,) if current == legacy else (current, legacy)


def requested_chromatin_sources(schema: dict) -> tuple[str, ...]:
    if type(schema) is not dict or type(schema.get("properties")) is not dict:
        raise ValueError("chromatin_return_form_schema_required")
    result = []
    for node in schema["properties"].values():
        if type(node) is not dict:
            raise ValueError("chromatin_return_form_schema_required")
        source = node.get("x-source")
        if type(source) is str and source.startswith("chromatin_interaction_"):
            if source not in FACT_SOURCES:
                raise ValueError("chromatin_return_unknown_source")
            if source not in result:
                result.append(source)
    return tuple(result)


def _validate_identity(file: dict, *, allowed_formats: tuple[str, ...]) -> None:
    validate_chromatin_record("NativeFileIdentity", file)
    if file["artifact_ref"] != "artifact_" + file["sha256"] or file["format"] not in allowed_formats:
        raise ValueError("chromatin_return_saved_identity")


def validate_chromatin_fact_values(source: str, value: object) -> list:
    if type(source) is not str or source not in _RECORDS:
        raise ValueError("chromatin_return_unknown_source")
    if type(value) is not list:
        raise ValueError("chromatin_return_array_required")
    result = [validate_chromatin_record(_RECORDS[source], row) for row in value]
    if source == SAVED_SOURCE:
        for bundle in result:
            _validate_identity(bundle["sheet"], allowed_formats=(_SHEET_FORMAT,))
            for table in bundle["tables"]:
                _validate_identity(table, allowed_formats=_TABLE_FORMATS)
    return result


def select_chromatin_return_facts(groups: dict, *, schema: dict) -> dict:
    if type(groups) is not dict:
        raise ValueError("chromatin_return_groups_required")
    result = {}
    requested_chromatin_sources(schema)
    for node in schema['properties'].values():
        source = node.get('x-source')
        if source not in FACT_SOURCES:
            continue
        accepted = chromatin_fact_schema_alternatives(source)
        if canonical_chromatin_record(node) not in {canonical_chromatin_record(tree) for tree in accepted}:
            raise ValueError('chromatin_return_unregistered_field_schema')
        if source not in groups:
            raise ValueError("chromatin_return_requested_source_unavailable")
        rows = validate_chromatin_fact_values(source, groups[source])
        # Repeated source fields can have different historical/current trees.
        # Every requested field keeps its own original restrictions.
        try:
            Draft202012Validator(node).validate(rows)
        except Exception as error:
            raise ValueError('chromatin_return_field_value_incompatible') from error
        result[source] = rows
    return result


__all__ = ["PROJECTION_SOURCE", "SAVED_SOURCE", "FAILURE_SOURCE", "FACT_SOURCES",
    "chromatin_fact_sources", "requested_chromatin_sources",
    "chromatin_fact_schema_alternatives",
    "validate_chromatin_fact_values", "select_chromatin_return_facts"]
