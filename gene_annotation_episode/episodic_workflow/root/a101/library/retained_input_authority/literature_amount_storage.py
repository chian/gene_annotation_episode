"""Selected source-amount persistence and exact typed subsets; no credit policy."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_amount_inputs import COMPARISON_KINDS, AMOUNT_ROLES, AMOUNT_KINDS, QUALIFICATIONS, RELATIONSHIPS, STOCK_RELATIONSHIPS, UNCERTAINTY_KINDS
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_amount_calculations import COMPONENTS, REASONS
CONDITIONS = ('source_role_and_pair_interpretations', 'linear_covariance_propagation', 'first_order_covariance_propagation', 'same_stock_rate_with_total_mass_denominator_required_before_application')
_QUANTITY_REF_FIELDS = ('subject_ref', 'construct_ref', 'preparation_ref', 'stock_ref', 'method_ref', 'reported_basis_ref', 'condition_ref', 'measurement_ref', 'physical_observation_ref', 'reported_uncertainty_ref')

def amount_cells_schema():

    def reference(namespace, nullable=True):
        return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}
    quantity = obj({**{name: reference('context' if name == 'condition_ref' else 'reference') for name in _QUANTITY_REF_FIELDS}, 'amount_role': {'enum': list(AMOUNT_ROLES)}, 'amount_kind': {'enum': list(AMOUNT_KINDS)}, 'basis_status': {'enum': list(RELATIONSHIPS)}, 'qualification': {'enum': list(QUALIFICATIONS)}, 'approximate': {'type': 'boolean'}, 'reported_uncertainty_kind': {'enum': list(UNCERTAINTY_KINDS)}})
    schema = {'type': 'array', 'items': obj({'sheet_ref': reference('source', False), 'evidence_source_ref': reference('source', False), 'experiment_ref': reference('reference'), 'intended_change_ref': reference('reference'), 'covariance_source_ref': reference('source'), 'component': {'enum': list(COMPONENTS)}, 'value': {'type': ['number', 'null']}, 'threshold': {'type': ['number', 'null']}, 'bound': {'enum': ['none', 'lt', 'le', 'gt', 'ge']}, 'unit': {'enum': ['mg/ml', 'uM', 'mg2/ml2', 'uM2', 'dimensionless', None]}, 'status': {'enum': ['populated', 'unavailable']}, 'origin': {'enum': ['reported', 'derived', 'synthetic']}, 'unavailable_reason': {'enum': [*REASONS, None]}, 'conditional_on': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(CONDITIONS)}}, 'approximate': {'type': 'boolean'}, 'evaluation_scope': {'const': 'source_amount_comparison'}, 'comparison_kind': {'enum': list(COMPARISON_KINDS)}, 'pair_relationship': {'enum': list(RELATIONSHIPS)}, 'stock_relationship': {'enum': list(STOCK_RELATIONSHIPS)}, 'variance_status': {'enum': ['known', 'estimated', 'unknown']}, 'covariance_origin': {'enum': ['reported', 'derived', 'synthetic', None]}, 'numerator': quantity, 'denominator': json.loads(json.dumps(quantity)), 'input_measurement_refs': {'type': 'array', 'uniqueItems': True, 'items': reference('reference', False)}, 'mass_factor_applied_to_rate': {'const': False}}), 'x-source': 'literature_amount_cells'}

    def typed(node):
        if not isinstance(node, dict):
            return
        if 'enum' in node and 'type' not in node:
            node['type'] = ['string', 'null'] if None in node['enum'] else 'string'
        if 'const' in node and 'type' not in node:
            node['type'] = 'boolean' if type(node['const']) is bool else 'string'
        for child in node.get('properties', {}).values():
            typed(child)
        if 'items' in node:
            typed(node['items'])
    typed(schema)
    return schema
