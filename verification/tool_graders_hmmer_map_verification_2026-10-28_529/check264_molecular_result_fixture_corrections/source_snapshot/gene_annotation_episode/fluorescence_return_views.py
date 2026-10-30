"""Exact requested fluorescence facts; no arithmetic, acquisition, or grant."""
from copy import deepcopy

from .fluorescence_execution_common import require, validate_failure
from .fluorescence_result_contracts import (FAILURE_SCHEMA, SAVED_FILE_SCHEMA, context_schema,
    projection_schema, validate_file, validate_fluorescence_context, validate_fluorescence_projection)

PROJECTION_SOURCE = "fluorescence_measurements"
CONTEXT_SOURCE = "fluorescence_contexts"
SAVED_SOURCE = "fluorescence_saved_sheets"
FAILURE_SOURCE = "fluorescence_failures"
FACT_SOURCES = (PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, FAILURE_SOURCE)


def fluorescence_fact_sources():
    meanings = (
        "Requested saved fluorescence numerical cells with their actual units, populations, denominators, and qualifications.",
        "Requested definitions associated with the selected numerical page; provenance identities do not grant source access.",
        "Explicitly returned common numerical-sheet identity for a separately selected recalculation.",
        "Recorded located input, capture, worker, and projection failures.",
    )
    schemas = (projection_schema(), context_schema(), deepcopy(SAVED_FILE_SCHEMA), deepcopy(FAILURE_SCHEMA))
    # Only the separately requested saved-sheet fact grants an artifact. All
    # nested identities in measurements/context remain factual provenance.
    schemas[2]["properties"]["artifact_ref"].update(format="reference", **{"x-reference-namespace": "artifact"})
    return {source: {"type": "array", "meaning": meaning,
        "report_schema": {"type": "array", "items": schema, "x-source": source}}
        for source, meaning, schema in zip(FACT_SOURCES, meanings, schemas)}


def requested_fluorescence_sources(schema):
    require(type(schema) is dict and type(schema.get("properties")) is dict, "fluorescence_return_form_schema_required")
    result = set()
    for node in schema["properties"].values():
        require(type(node) is dict, "fluorescence_return_form_schema_required")
        source = node.get("x-source")
        if type(source) is str and source.startswith("fluorescence_"):
            require(source in FACT_SOURCES, "fluorescence_return_unknown_source")
            result.add(source)
    return result


def validate_fluorescence_fact_values(source, values):
    require(source in FACT_SOURCES, "fluorescence_return_unknown_source")
    require(type(values) is list, "fluorescence_return_array_required")
    validator = {PROJECTION_SOURCE: validate_fluorescence_projection,
        CONTEXT_SOURCE: validate_fluorescence_context,
        SAVED_SOURCE: lambda value: validate_file(value, saved=True), FAILURE_SOURCE: validate_failure}[source]
    return [validator(value) for value in values]


def select_fluorescence_return_facts(groups, *, schema):
    require(type(groups) is dict, "fluorescence_return_groups_required")
    selected = requested_fluorescence_sources(schema)
    result = {}
    for source in FACT_SOURCES:
        if source in selected:
            require(source in groups, "fluorescence_return_requested_source_unavailable")
            result[source] = validate_fluorescence_fact_values(source, groups[source])
    return result
