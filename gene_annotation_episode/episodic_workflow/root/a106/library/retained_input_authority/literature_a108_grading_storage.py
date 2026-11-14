"""Persist A108's purpose-specific contextual subscoring sheets and returns."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a106.domain import obj
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.literature_a108_grading import GRADER_TYPES, grading_cell_schema
NAMESPACE = 'literature_a108_grading_cells'

def grading_cells_schema():
    fields = deepcopy(grading_cell_schema()['properties'])
    fields.update({'sheet_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}, 'assertion_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis'}, 'target_context_ref': {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': 'context'}, 'grader_type': {'enum': list(GRADER_TYPES)}})
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}
