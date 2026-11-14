"""Source-bound assay interpretation and numerical correction, without credit policy.

The episode assigns scientific meanings to exact source operands. This adapter
validates their custody and performs arithmetic; source quotation validation is
not a semantic proof of the episode's interpretation.
"""
from __future__ import annotations
PRIMITIVE_CELLS = {'q': ('net_rate', 'uM/min'), 'g': ('contaminant_rate', 'uM/min'), 'k': ('recovery', 'dimensionless'), 'E': ('protein_amount', 'uM'), 'u': ('condition_test_rate', 'uM/min'), 'v': ('condition_reference_rate', 'uM/min')}
COMPONENTS = (*[row[0] for row in PRIMITIVE_CELLS.values()], 'attributed_rate', 'condition_response', 'corrected_activity', 'effect_variance', 'effect_standard_uncertainty', 'effect_precision', 'source_profile_log_ratio', 'source_presence_index')
BINDINGS = {'assay_ref': 'reference', 'assayed_subject_ref': 'reference', 'organism_ref': 'reference', 'genotype_ref': 'reference', 'construct_ref': 'reference', 'preparation_ref': 'reference', 'condition_ref': 'context', 'intended_variable_ref': 'reference', 'endpoint_ref': 'term', 'arrangement_ref': 'term', 'covariance_source_ref': 'source', 'experimental_system_ref': 'reference', 'expression_host_ref': 'reference', 'measured_entity_ref': 'reference', 'asserted_input_ref': 'reference', 'asserted_output_ref': 'reference'}
REASONS = ('endpoint_requires_different_model', 'assayed_molecule_unresolved', 'source_endpoint_unresolved', 'source_endpoint_conflicting', 'source_measurement_unavailable', 'correction_inputs_unreported', 'numerical_model_range', 'primitive_covariance_unreported', 'distinct_residual_variance_unreported', 'invalid_propagated_variance', 'positive_effect_variance_required', 'known_variance_required', 'observation_model_unspecified')
REASONS += ('correction_inputs_not_supplied', 'primitive_covariance_not_supplied',
            'distinct_residual_variance_not_supplied')
CONDITIONS = ('source_role_assignments', 'first_order_covariance_propagation', 'known_variance', 'known_normal_nonnegative_presence')

def assay_cells_schema():
    from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_assay_inputs import ENDPOINTS, ARRANGEMENTS, SOURCE_KINDS
    reference = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    properties = {'sheet_ref': dict(reference), 'evidence_source_ref': dict(reference), 'component': {'type': 'string', 'enum': list(COMPONENTS)}, 'value': {'type': ['number', 'null']}, 'input_measurement_refs': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'reference'}}, 'unit': {'type': 'string', 'enum': ['uM/min', 'uM', 'dimensionless', 'per_min', 'per_min_squared', 'min_squared']}, 'status': {'type': 'string', 'enum': ['populated', 'unavailable']}, 'origin': {'type': 'string', 'enum': ['reported', 'graph_derived', 'synthetic', 'derived', 'proposed']}, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *REASONS]}, 'conditional_on': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': list(CONDITIONS)}}, 'interpretation_kind': {'type': 'string', 'enum': ['episode_source_interpretation']}, 'evaluated_scope': {'type': 'string', 'enum': ['interpreted_source_endpoint']}, 'endpoint_kind': {'type': 'string', 'enum': list(ENDPOINTS)}, 'arrangement_kind': {'type': 'string', 'enum': list(ARRANGEMENTS)}, 'operand_source_kind': {'type': 'string', 'enum': list(SOURCE_KINDS)}, 'covariance_origin': {'type': ['string', 'null'], 'enum': [None, 'reported', 'derived', 'synthetic']}}
    for name, namespace in BINDINGS.items():
        properties[name] = {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': namespace}
    return {'type': 'array', 'items': obj(properties), 'x-source': 'literature_assay_cells'}
