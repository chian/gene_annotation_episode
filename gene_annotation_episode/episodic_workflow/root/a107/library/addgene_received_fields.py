"""A107 original addgene received fields; selected retained metadata/operand declarations.

Original source qualifications and identity checks remain intact; no acquisition or dispatch is added.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.library.addgene_sequence_facts import FACT_SOURCE, ADDGENE_SEQUENCE_FACTS_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.communication import ReportBoundaryError, plain
from gene_annotation_episode.episodic_workflow.root.a107.episode_return_records import _same
OWN_BINDINGS = '_addgene_sequence_acquisition_bindings_v1'
CLOSURE_PREFIX = '_addgene_sequence_return_prefix_v1'

def _boundary(code, field=None):
    return ReportBoundaryError('addgene_sequence_return_' + code, code='addgene_sequence_return_' + code, field=field)

def addgene_sequence_fact_sources():
    return {FACT_SOURCE: {'type': 'array', 'meaning': 'Literal selected Addgene native metadata and sequence availability from the assigned original response; full/partial and verification categories are source labels, not target identity or scientific confidence. Authentication-required and unavailable records supply no sequence bases or inferred symbol counts.', 'report_schema': deepcopy(ADDGENE_SEQUENCE_FACTS_SCHEMA)}}

def requested_addgene_fields(schema):
    schema = plain(schema)
    if not isinstance(schema, dict) or not isinstance(schema.get('properties', {}), dict):
        raise _boundary('original_schema_conflict')
    fields = {}
    for name, node in schema.get('properties', {}).items():
        if not isinstance(node, dict):
            continue
        source = node.get('x-source')
        if source == FACT_SOURCE:
            if not _same(node, ADDGENE_SEQUENCE_FACTS_SCHEMA):
                raise _boundary('original_schema_conflict', name)
            fields[name] = source
        elif isinstance(source, str) and source.startswith('execution_addgene_'):
            raise _boundary('original_schema_conflict', name)
    return fields
