"""Reusable assay-type assessments feeding the same A105 dimensions.

Readers/calculators supply native estimates, corrections and uncertainty. This
module assesses their scientific applicability and calculates the requested
evidence comparison. It never parses a paper or repeats a source correction.
"""
from gene_annotation_episode.episodic_workflow.root.a108.domain import obj
INPUT_VERSION = 'a105_assay_grading_inputs_v1'
VERSION = 'a105_assay_grading_sheet_v1'
EVALUATION_SCOPE = 'assay_type_experimental_evidence'
ASSAY_TYPES = ('activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling', 'ligand_binding', 'transport_response', 'protein_signal', 'protein_amount')
QUANTITY_KINDS = {'activity_rate': ('rate', 'rate_difference', 'rate_ratio', 'turnover', 'catalytic_efficiency', 'kinetic_parameter', 'kinetic_parameter_difference', 'kinetic_parameter_ratio', 'log_kinetic_parameter_ratio', 'partner_rate_difference', 'partner_response_fraction'), 'endpoint_conversion': ('conversion_fraction', 'conversion_difference', 'endpoint_amount', 'completion_time', 'completion_time_ratio'), 'product_distribution': ('product_fraction', 'product_fraction_ratio', 'equilibrium_fraction', 'equilibrium_ratio'), 'reaction_coupling': ('productive_fraction', 'stoichiometric_ratio', 'balance_residual'), 'ligand_binding': ('binding_parameter', 'binding_parameter_ratio', 'log_binding_parameter_ratio', 'binding_discrimination_ratio', 'log_binding_discrimination', 'band_display_fraction', 'relative_binding_response', 'log_relative_binding_response'), 'transport_response': ('transport_rate', 'transport_rate_ratio', 'log_transport_rate_ratio', 'accumulated_amount', 'transport_parameter', 'substrate_saturation', 'substrate_response_ratio', 'log_substrate_response', 'electrical_current', 'electrical_conductance', 'charge_equivalent_rate'), 'protein_signal': ('signal_ratio', 'signal_difference', 'log_signal_ratio', 'band_display_fraction', 'band_display_darkness'), 'protein_amount': ('protein_amount', 'protein_amount_difference', 'protein_amount_ratio', 'sites_per_monomer', 'active_fraction')}
REQUIRED_ROLES = ('effect', 'effect_variance', 'recovery', 'attributed_signal', 'total_signal', 'condition_test', 'condition_reference', 'assertion_prediction', 'alternative_prediction')
ROLES = (*REQUIRED_ROLES, 'effect_degrees_of_freedom')
COMPONENTS = ('measured_effect', 'effect_variance', 'effect_precision', 'recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio')
COMMON_CRITERIA = ('measurement_identity', 'calibration_applicability', 'matrix_interference', 'background_alternatives', 'attribution_supported', 'assertion_relevance', 'condition_scope', 'variance_correspondence', 'sampling_basis')
CRITERIA_BY_TYPE = {'activity_rate': (*COMMON_CRITERIA, 'rate_regime', 'normalization_basis', 'kinetic_model', 'partner_perturbation'), 'endpoint_conversion': (*COMMON_CRITERIA, 'endpoint_alignment', 'conversion_denominator', 'product_identity'), 'product_distribution': (*COMMON_CRITERIA, 'species_identity', 'response_factors', 'common_denominator', 'equilibrium_state'), 'reaction_coupling': (*COMMON_CRITERIA, 'product_identity', 'stoichiometry', 'matched_windows', 'reporter_specificity'), 'ligand_binding': (*COMMON_CRITERIA, 'binding_parameter_definition', 'binding_species', 'binding_controls', 'binding_regime', 'binding_comparison'), 'transport_response': (*COMMON_CRITERIA, 'membrane_system', 'transport_endpoint', 'transport_driving_force', 'transport_specificity', 'transport_response_model'), 'protein_signal': (*COMMON_CRITERIA, 'signal_assignment', 'signal_response_range', 'signal_normalization', 'signal_representation'), 'protein_amount': (*COMMON_CRITERIA, 'amount_basis', 'preparation_relationship', 'amount_calibration', 'active_site_stoichiometry')}
CRITERIA = tuple(dict.fromkeys((c for cs in CRITERIA_BY_TYPE.values() for c in cs)))
ORIGINS = ('reported', 'derived', 'graph_derived', 'synthetic', 'proposed')

def _strings():
    return {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}

def interpretation_schema():
    return obj({'status': {'enum': ['supported', 'unknown', 'conflicting', 'not_applicable']}, 'support_refs': _strings()})

def operand_schema():
    result = obj({'value': {'type': ['number', 'null']}, 'unit': {'type': 'string', 'minLength': 1}, 'status': {'enum': ['point', 'bounded', 'unavailable']}, 'reason': {'type': ['string', 'null']}, 'measurement_keys': _strings(), 'source_refs': _strings(), 'origin': {'enum': list(ORIGINS)}, 'native_component': {'type': 'string', 'minLength': 1}})
    result['properties']['qualifications'] = _strings()
    result['properties']['bound'] = {'anyOf': [bound_schema(), {'type': 'null'}]}
    return result

def bound_schema():
    return obj({'relation': {'enum': ['lt', 'le', 'gt', 'ge', 'interval']}, 'lower': {'type': ['number', 'null']}, 'upper': {'type': ['number', 'null']}})

def prediction_model_schema():
    return obj({'kind': {'enum': ['fixed_predictions_known_normal', 'fixed_predictions_estimated_normal', 'fixed_predictions_student_t']}, 'variance_interpretation': {'enum': ['known', 'estimated', 'unknown']}, 'support_refs': _strings()})

def assay_grading_input_schema():
    result = obj({'version': {'const': INPUT_VERSION}, 'assay_type': {'enum': list(ASSAY_TYPES)}, 'assertion_ref': {'type': 'string', 'minLength': 1}, 'quantity_kind': {'enum': list(dict.fromkeys((k for ks in QUANTITY_KINDS.values() for k in ks)))}, 'quantities': obj({role: {'anyOf': [operand_schema(), {'type': 'null'}]} for role in ROLES}, required=list(REQUIRED_ROLES)), 'interpretations': {'type': 'object', 'properties': {c: interpretation_schema() for c in CRITERIA}, 'additionalProperties': False}, 'prediction_model': {'anyOf': [prediction_model_schema(), {'type': 'null'}]}})
    result['allOf'] = [{'if': {'properties': {'assay_type': {'const': kind}}}, 'then': {'properties': {'quantity_kind': {'enum': list(quantities)}, 'interpretations': {'propertyNames': {'enum': list(CRITERIA_BY_TYPE[kind])}}}}} for kind, quantities in QUANTITY_KINDS.items()]
    return result

def assay_grading_cell_schema():
    result = obj({'component': {'enum': list(COMPONENTS)}, 'dimension': {'enum': ['measurement', 'reliability', 'validity', 'attribution', 'comparability', 'relevance', 'experimental_evidence']}, 'value': {'type': ['number', 'null']}, 'unit': {'type': 'string'}, 'status': {'enum': ['populated', 'conditional', 'bounded', 'unavailable']}, 'reasons': _strings(), 'formula': {'type': 'string'}, 'meaning': {'type': 'string'}, 'measurement_keys': _strings(), 'source_refs': _strings(), 'input_origins': {'type': 'array', 'items': {'enum': list(ORIGINS)}, 'uniqueItems': True}, 'conditions': _strings()})
    result['properties']['bound'] = bound_schema()
    return result

def assay_grading_sheet_schema():
    return obj({'version': {'const': VERSION}, 'axis': {'const': 'A105'}, 'evaluation_scope': {'const': EVALUATION_SCOPE}, 'assay_type': {'enum': list(ASSAY_TYPES)}, 'assertion_ref': {'type': 'string', 'minLength': 1}, 'quantity_kind': {'enum': list(dict.fromkeys((k for ks in QUANTITY_KINDS.values() for k in ks)))}, 'cells': obj({name: assay_grading_cell_schema() for name in COMPONENTS}), 'interpretations': assay_grading_input_schema()['properties']['interpretations'], 'prediction_model': {'anyOf': [prediction_model_schema(), {'type': 'null'}]}, 'annotation_credit': {'type': 'null'}})
