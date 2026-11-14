"""Claim-bound A106 log evidence ratios with explicit experiment dependence."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import REF, obj
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_assay_inputs import _witness_schema
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_intervention_storage import intervention_cells_schema
NAMESPACE = 'literature_a106_subscore_cells'
COMPONENTS = ('experimental_subscore',)
SCOPE = 'a106_intervention_experimental_evidence'

def population_schema():
    text = {'type': 'string', 'minLength': 1}
    source = {**REF, 'x-reference-namespace': 'source'}
    return obj({'subject_ref': deepcopy(REF), 'assertion_ref': {**REF, 'x-reference-namespace': 'hypothesis'}, 'comparison_ref': {**REF, 'x-reference-namespace': 'hypothesis'}, 'scope_statement': text, 'experiments': {'type': 'array', 'items': obj({'experiment_ref': {**REF, 'x-reference-namespace': 'reference'}, 'sheet_ref': {**source, 'type': ['string', 'null'], 'description': 'Current assessment sheet, including an unavailable score. Null only when no applicable assessment sheet exists.'}, 'missing_reason': {'type': ['string', 'null'], 'minLength': 1, 'description': 'Null whenever sheet_ref is supplied, including an unavailable score. Explain a missing assessment only when sheet_ref is null; numerical limitations remain in the selected assessment and final limitations.'}})}, 'dependence': obj({'status': {'enum': ['independent', 'shared', 'unknown']}, 'rationale': text, 'witnesses': {'type': 'array', 'items': _witness_schema()}}), 'conclusion': text, 'limitations': {'type': 'array', 'items': text}, 'revises_subscore_ref': {**source, 'type': ['string', 'null']}, 'revision_reason': {'type': ['string', 'null'], 'minLength': 1}})

def cell_schema():
    fields = population_schema()['properties']
    contributors = deepcopy(intervention_cells_schema())
    contributors.pop('x-source')
    strings = {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}
    return obj({**fields, 'component': {'enum': list(COMPONENTS)}, 'axis': {'const': 'A106'}, 'evaluation_scope': {'const': SCOPE}, 'score_meaning': {'const': 'conditional_signed_log_evidence_ratio'}, 'value': {'type': ['number', 'null']}, 'available_value': {'type': ['number', 'null']}, 'status': {'enum': ['complete', 'partial', 'unavailable']}, 'unit': {'const': 'natural_log_ratio'}, 'unavailable_reasons': strings, 'conditions': strings, 'selected_components': contributors, 'source_refs': {'type': 'array', 'items': {**REF, 'x-reference-namespace': 'source'}, 'uniqueItems': True}, 'evidence_measurement_keys': strings, 'input_origins': strings, 'annotation_credit': {'type': 'null'}})

def cells_schema():
    fields = deepcopy(cell_schema()['properties'])
    fields['sheet_ref'] = {**REF, 'x-reference-namespace': 'source'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}
