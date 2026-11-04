"""Exact requested ATAC fact trees; access authority belongs to the receiver."""
from __future__ import annotations

from copy import deepcopy
from .atac_differential_result_contracts import (
    atac_result_schema, validate_atac_result_record, canonical, digest, SHEET_FORMAT, TABLE_FORMAT,
)

PROJECTION_SOURCE = 'atac_differential_projection'
SAVED_SOURCE = 'atac_differential_saved_sheets'
FAILURE_SOURCE = 'atac_differential_failures'
FACT_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE)
_RECORDS = {PROJECTION_SOURCE: 'RequestedProjection', SAVED_SOURCE: 'SavedSheetBundle', FAILURE_SOURCE: 'Failure'}
_MEANINGS = {
    PROJECTION_SOURCE: 'Only the requested ATAC native or derived measurements, with selected populations, numerical units and source qualifications.',
    SAVED_SOURCE: 'Explicitly returned native sheet and every referenced raw numerical table for saved calculation; no authority to unrequested native inputs.',
    FAILURE_SOURCE: 'Actual located ATAC execution, capture, calculation and delivery failures and their specific missing operands.',
}


def _array_schema(source):
    record = _RECORDS[source]
    base = atac_result_schema(record)
    # Failure is A's exact schema, including its original root declaration.
    schema = {'$schema': base.get('$schema', 'https://json-schema.org/draft/2020-12/schema'), '$defs': deepcopy(base.get('$defs', {})),
        'type': 'array', 'items': {k: deepcopy(v) for k, v in base.items() if k not in ('$schema', '$defs', '$id')}, 'x-source': source}
    if source == SAVED_SOURCE:
        definitions = schema['$defs']
        for name, format_name in (('SavedSheetIdentity', SHEET_FORMAT), ('SavedTrackIdentity', TABLE_FORMAT)):
            identity = deepcopy(definitions['NativeFileIdentity'])
            identity['properties']['format'] = {'const': format_name}
            identity['properties']['artifact_ref'].update(format='reference', **{'x-reference-namespace': 'artifact'})
            definitions[name] = identity
        bundle = definitions['SavedSheetBundle']['properties']
        bundle['sheet'] = {'$ref': '#/$defs/SavedSheetIdentity'}
        bundle['tables']['items']['properties']['file'] = {'$ref': '#/$defs/SavedTrackIdentity'}
    schema['$id'] = 'urn:gene-annotation:atac:return:' + digest(schema)
    return schema


def atac_fact_sources():
    return {source: {'type': 'array', 'meaning': _MEANINGS[source], 'report_schema': _array_schema(source)} for source in FACT_SOURCES}


def requested_atac_sources(schema):
    if type(schema) is not dict or type(schema.get('properties')) is not dict:
        raise ValueError('atac_return_form_schema_required')
    result = []
    for node in schema['properties'].values():
        if type(node) is not dict:
            raise ValueError('atac_return_form_schema_required')
        source = node.get('x-source')
        if type(source) is str and source.startswith('atac_differential_'):
            if source not in FACT_SOURCES:
                raise ValueError('atac_return_unknown_source')
            if canonical(node) != canonical(_array_schema(source)):
                raise ValueError('atac_return_unregistered_field_schema')
            if source not in result:
                result.append(source)
    return tuple(result)


def validate_atac_fact_values(source, value):
    if source not in _RECORDS:
        raise ValueError('atac_return_unknown_source')
    if type(value) is not list:
        raise ValueError('atac_return_array_required')
    return [validate_atac_result_record(_RECORDS[source], row) for row in value]


def select_atac_return_facts(groups, *, schema):
    if type(groups) is not dict:
        raise ValueError('atac_return_groups_required')
    result = {}
    for source in requested_atac_sources(schema):
        if source not in groups:
            raise ValueError('atac_return_requested_source_unavailable')
        result[source] = validate_atac_fact_values(source, groups[source])
    return result


__all__ = ['PROJECTION_SOURCE', 'SAVED_SOURCE', 'FAILURE_SOURCE', 'FACT_SOURCES', 'atac_fact_sources',
    'requested_atac_sources', 'validate_atac_fact_values', 'select_atac_return_facts']
