"""Finite typed facts for the unchanged shared HOMER public projection.

The source-free packet shape removes only the two outer identity fields. It
does not project, interpret or recalculate scientific values.
"""
import hashlib
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority import homer_motif_contracts as core
FACT_SOURCE = 'homer_motif_outcomes'

def validate_homer_motif_return(value):
    """Validate the exact public DTO; producer and receipt proof stay separate."""
    try:
        return core.validated('Return', value)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        raise ValueError('homer_motif_return_invalid') from error

def homer_motif_fact_sources():
    schema = core.homer_record_schema('Return')
    report = {'$schema': schema['$schema'], '$defs': schema['$defs'], 'type': 'array', 'items': {'$ref': schema['$ref']}, 'x-source': FACT_SOURCE}
    report['$id'] = 'urn:gene-annotation:homer-motif-return:' + hashlib.sha256(core.canonical(report)).hexdigest()
    return {FACT_SOURCE: dict(type='array', meaning='Retained final native HOMER motif measurements and reported-input-weight sums, preserving supplied series selection, native occurrence order, precision, populations, geometry and qualifications.', report_schema=report)}
