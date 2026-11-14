"""Requested typed overlap facts, separate from calculation and authority.

The result host supplies original qualified values. These ports define their
closed runtime shapes and select requested sources. They neither open artifacts
nor establish that a receiver was given a result by its child.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.genomic_overlap_contracts import genomic_overlap_schema, validate_genomic_overlap_record
PROJECTION_SOURCE = 'genomic_overlap_pair_metrics'
SAVED_SOURCE = 'genomic_overlap_saved_sheets'
FAILURE_SOURCE = 'genomic_overlap_failures'
FACT_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE)
_RECORDS = {PROJECTION_SOURCE: 'Projection', SAVED_SOURCE: 'NativeFileIdentity', FAILURE_SOURCE: 'Failure'}
_MEANINGS = {PROJECTION_SOURCE: 'Exactly requested overlap measurements and their original denominators, extents and reference qualifications; no annotation confidence.', SAVED_SOURCE: 'Explicitly returned saved numerical-sheet identities for later selected recalculation; no access to unrequested child outputs.', FAILURE_SOURCE: 'Actual located overlap input, capture, calculation or delivery failures; no model-authored finding.'}

def _array_schema(source):
    """Keep only definitions reachable from this one recorded fact shape."""
    record = _RECORDS[source]
    definitions = genomic_overlap_schema(record)['$defs']
    wanted = set()

    def visit(value):
        if isinstance(value, dict):
            reference = value.get('$ref')
            if reference is not None:
                if not reference.startswith('#/$defs/'):
                    raise ValueError('genomic_overlap_return_external_schema_reference')
                name = reference.removeprefix('#/$defs/')
                if name not in wanted:
                    wanted.add(name)
                    visit(definitions[name])
            for key, child in value.items():
                if key != '$ref':
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    items = {'$ref': '#/$defs/' + record}
    visit(items)
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$defs': {name: deepcopy(definitions[name]) for name in sorted(wanted)}, 'type': 'array', 'items': items, 'x-source': source}
    if source == SAVED_SOURCE:
        schema['$defs'][record]['properties']['format'] = {'const': 'genomic_region_overlap_sheet_v1'}
        schema['$defs'][record]['properties']['artifact_ref'].update(format='reference', **{'x-reference-namespace': 'artifact'})
    schema['$id'] = 'urn:gene-annotation:genomic-overlap:return:' + digest(schema)
    return schema

def genomic_overlap_fact_sources() -> dict:
    return {source: {'type': 'array', 'meaning': _MEANINGS[source], 'report_schema': _array_schema(source)} for source in FACT_SOURCES}

def validate_genomic_overlap_fact_values(source: str, value: object) -> list:
    if type(source) is not str or source not in _RECORDS:
        raise ValueError('genomic_overlap_return_unknown_source')
    if type(value) is not list:
        raise ValueError('genomic_overlap_return_array_required')
    result = [validate_genomic_overlap_record(_RECORDS[source], row) for row in value]
    if source == SAVED_SOURCE:
        for row in result:
            if row['format'] != 'genomic_region_overlap_sheet_v1' or row['artifact_ref'] != 'artifact_' + row['sha256']:
                raise ValueError('genomic_overlap_return_saved_sheet_identity')
    return result
