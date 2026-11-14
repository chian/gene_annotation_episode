"""Persist main A108 evidence counts over actually admitted subscoring cells."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_a108_aggregation import aggregation_cell_schema
NAMESPACE = 'literature_a108_aggregation_cells'

def aggregation_cells_schema():
    fields = deepcopy(aggregation_cell_schema()['properties'])
    fields['sheet_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}
