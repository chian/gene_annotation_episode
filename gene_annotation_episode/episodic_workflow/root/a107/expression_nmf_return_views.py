"""Receiver-requested NMF facts; no calculation, acquisition or custody grant."""
from copy import deepcopy

from .expression_nmf_result_contracts import (ISSUE_SCHEMA, SAVED_FILE_SCHEMA,
    projection_schema, require, validate_file, validate_issue, validate_projection)

PROJECTION_SOURCE = 'expression_nmf_measurements'
SAVED_SOURCE = 'expression_nmf_saved_sheets'
FAILURE_SOURCE = 'expression_nmf_failures'
FACT_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE)


def expression_nmf_fact_sources():
    meanings = (
        'Requested native NMF diagnostics or calculated loading, contribution or residual quantities with exact populations and denominators; no annotation probability.',
        'Explicitly returned retained numerical-sheet identities for later selected calculation; no grant of other child files.',
        'Recorded located NMF input, capture, calculation and delivery failures; no model-composed findings.',
    )
    schemas = (projection_schema(), deepcopy(SAVED_FILE_SCHEMA), deepcopy(ISSUE_SCHEMA))
    schemas[1]['properties']['artifact_ref'].update(format='reference', **{'x-reference-namespace': 'artifact'})
    return {source: {'type': 'array', 'meaning': meaning,
        'report_schema': {'type': 'array', 'items': schema, 'x-source': source}}
        for source, meaning, schema in zip(FACT_SOURCES, meanings, schemas)}


def requested_expression_nmf_sources(schema):
    require(type(schema) is dict and type(schema.get('properties')) is dict, 'expression_nmf_return_form_schema_required')
    result = []
    for node in schema['properties'].values():
        require(type(node) is dict, 'expression_nmf_return_form_schema_required')
        source = node.get('x-source')
        if type(source) is str and source.startswith('expression_nmf_'):
            require(source in FACT_SOURCES, 'expression_nmf_return_unknown_source')
            if source not in result:
                result.append(source)
    return tuple(result)


def validate_expression_nmf_fact_values(source, value):
    require(source in FACT_SOURCES, 'expression_nmf_return_unknown_source')
    require(type(value) is list, 'expression_nmf_return_array_required')
    validator = {PROJECTION_SOURCE: validate_projection, SAVED_SOURCE: lambda v: validate_file(v, saved=True),
        FAILURE_SOURCE: validate_issue}[source]
    return [validator(row) for row in value]


def select_expression_nmf_return_facts(groups, *, schema):
    require(type(groups) is dict, 'expression_nmf_return_groups_required')
    result = {}
    for source in requested_expression_nmf_sources(schema):
        require(source in groups, 'expression_nmf_return_requested_source_unavailable')
        result[source] = validate_expression_nmf_fact_values(source, groups[source])
    return result
