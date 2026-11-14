"""Authenticate native database cells for the existing A105 assay grader.

The selector contains locations, never a model-authored measurement. Native
units, censoring, missingness and score definitions remain explicit. This is a
source reader; it supplies no assay validity, variance or prediction defaults.
"""
from gene_annotation_episode.episodic_workflow.root.a108.domain import REF, obj

def measurement_schema():
    return obj({'kind': {'const': 'database_measurement'}, 'source_ref': REF, 'record_index': {'type': 'integer', 'minimum': 0}, 'field': {'type': 'string', 'minLength': 1, 'maxLength': 200}, 'metadata_source_ref': {'anyOf': [REF, {'type': 'null'}]}})
