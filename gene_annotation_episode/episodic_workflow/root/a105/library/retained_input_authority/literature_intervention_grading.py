"""A106 intervention assessment using the existing evidence-ratio calculation."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a105.domain import obj
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading import ROLES, REQUIRED_ROLES, COMMON_CRITERIA, operand_schema, interpretation_schema, prediction_model_schema
INPUT_VERSION = 'a106_intervention_grading_inputs_v1'
EVALUATION_SCOPE = 'intervention_experimental_evidence'
QUANTITY_KINDS = ('native_endpoint', 'endpoint_difference', 'endpoint_ratio', 'log2_fold_change', 'fitness_difference')
CRITERIA = (*COMMON_CRITERIA, 'intervention_identity', 'subject_correspondence', 'contrast_definition', 'prediction_independence')

def intervention_grading_input_schema():
    interpretation = interpretation_schema()
    interpretation['properties']['status'] = {'enum': ['supported', 'unknown', 'conflicting']}
    interpretation['properties']['support_refs']['description'] = 'Received reference records with exact source anchors, such as experiment_ref. A document source_ref alone does not provide an anchored interpretation witness.'
    return obj({'version': {'const': INPUT_VERSION}, 'assay_type': {'const': 'intervention_response'}, 'assertion_ref': {'type': 'string', 'minLength': 1}, 'quantity_kind': {'enum': list(QUANTITY_KINDS)}, 'quantities': obj({role: {'anyOf': [operand_schema(), {'type': 'null'}]} for role in ROLES}, required=list(REQUIRED_ROLES)), 'interpretations': obj({key: deepcopy(interpretation) for key in CRITERIA}, required=[]), 'prediction_model': {'anyOf': [prediction_model_schema(), {'type': 'null'}]}})
