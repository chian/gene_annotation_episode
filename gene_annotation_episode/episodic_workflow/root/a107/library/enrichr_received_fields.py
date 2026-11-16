"""A107 enrichr received fields."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.communication import ReportBoundaryError, plain
from gene_annotation_episode.episodic_workflow.root.a107.library.enrichr_received_contracts import TABLE_SOURCE, ROW_SOURCE, enrichr_fact_sources
from gene_annotation_episode.episodic_workflow.root.a107.episode_return_records import _same
SOURCES = (TABLE_SOURCE, ROW_SOURCE)
OWN_WITNESSES = 'enrichr_original_publication_witnesses_v1'

def _boundary(code, field=None):
    return ReportBoundaryError('enrichr_' + code, code='enrichr_' + code, field=field)

def requested_enrichr_fields(schema):
    """Recognize exact source-owned contracts; this does not authenticate values."""
    schema = plain(schema)
    if not isinstance(schema, dict) or not isinstance(schema.get('properties', {}), dict):
        raise _boundary('original_schema_conflict')
    available, result = (enrichr_fact_sources(), {})
    for name, node in schema.get('properties', {}).items():
        if not isinstance(node, dict):
            continue
        source = node.get('x-source')
        if source in SOURCES:
            if not _same(node, available[source]['report_schema']):
                raise _boundary('original_schema_conflict', name)
            result[name] = source
        elif isinstance(source, str) and source.startswith('execution_enrichr_'):
            raise _boundary('original_schema_conflict', name)
    return result
