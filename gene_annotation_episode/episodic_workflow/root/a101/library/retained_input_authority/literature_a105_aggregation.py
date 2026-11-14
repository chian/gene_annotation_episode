"""The user's ordinary A105 sum/max rules over selected experiment scores.

Selection identifies existing numerical components. This module neither creates
new quality scales nor changes the selected measurements' units or meanings.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_assay_grading_storage import assay_grading_cells_schema
SCOPE = 'a105_across_experiment_aggregation'
COMPONENTS = ('reliability', 'validity', 'relevance', 'attribution', 'overall')
DIMENSIONS = {name: 'experimental_evidence' if name == 'overall' else name for name in COMPONENTS}

def _reference(namespace, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}

def _strings():
    return {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}

def aggregation_cell_schema():
    references = {'type': 'array', 'items': _reference('reference'), 'uniqueItems': True}
    contributors = deepcopy(assay_grading_cells_schema())
    contributors.pop('x-source', None)
    return obj({'component': {'enum': list(COMPONENTS)}, 'dimension': {'enum': list(DIMENSIONS.values())}, 'evaluation_scope': {'const': SCOPE}, 'assertion_ref': _reference('hypothesis'), 'comparison_ref': _reference('hypothesis', True), 'comparison_binding': {'enum': ['parent_declared', 'not_declared']}, 'reducer': {'enum': ['sum', 'max']}, 'value': {'type': ['number', 'null']}, 'available_value': {'type': ['number', 'null']}, 'status': {'enum': ['complete', 'partial', 'unavailable']}, 'unit': {'type': 'string'}, 'input_units': _strings(), 'source_component_names': _strings(), 'source_meanings': _strings(), 'selected_experiment_refs': deepcopy(references), 'available_experiment_refs': deepcopy(references), 'missing_experiment_refs': deepcopy(references), 'missing_inputs': {'type': 'array', 'items': obj({'experiment_ref': _reference('reference'), 'reason': {'type': 'string'}})}, 'selected_components': contributors, 'measurement_keys': _strings(), 'source_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'uniqueItems': True}, 'input_origins': _strings(), 'conditions': _strings(), 'formula': {'type': 'string'}, 'meaning': {'type': 'string'}, 'annotation_credit': {'type': 'null'}})
