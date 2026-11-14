"""Immutable A106 assessment sheets and typed delivery on existing custody."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import REF, obj
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_intervention_grading import EVALUATION_SCOPE
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_assay_grading import assay_grading_cell_schema
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_intervention_inputs import intervention_population_schema, sample_bindings_schema
NAMESPACE = 'literature_intervention_grading_cells'
SCOPE = EVALUATION_SCOPE

def intervention_cells_schema():
    fields = deepcopy(assay_grading_cell_schema()['properties'])
    inputs = intervention_population_schema()['properties']
    fields.update({key: deepcopy(inputs[key]) for key in ('assay_type', 'assertion_ref', 'comparison_ref', 'experiment_ref', 'quantity_kind', 'interpretations', 'prediction_model', 'experimental_design', 'experiment_assessment')})
    fields.update(sheet_ref={**REF, 'x-reference-namespace': 'source'}, evidence_source_ref={**REF, 'x-reference-namespace': 'source'}, evidence_measurement_keys={'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}, evaluation_scope={'const': SCOPE}, annotation_credit={'type': 'null'})
    fields['assertion_ref'] = {**REF, 'x-reference-namespace': 'hypothesis'}
    fields['sample_bindings'] = sample_bindings_schema()
    required = [*assay_grading_cell_schema()['required'], 'assay_type', 'assertion_ref', 'comparison_ref', 'experiment_ref', 'quantity_kind', 'interpretations', 'prediction_model', 'experimental_design', 'experiment_assessment', 'sheet_ref', 'evidence_source_ref', 'evidence_measurement_keys', 'evaluation_scope', 'annotation_credit', 'sample_bindings']
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields, required=required)}
