"""Persist selected A105 aggregation over the parent's possessed grade rows."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import obj
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_a105_aggregation import aggregation_cell_schema
NAMESPACE = 'literature_a105_aggregation_cells'

def aggregation_cells_schema():
    fields = deepcopy(aggregation_cell_schema()['properties'])
    fields['sheet_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}
