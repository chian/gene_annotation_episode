"""Exact parent-selected projections of retained RNA comparison components.

This module selects supplied facts. It does not calculate scientific components,
authenticate publication identities, access Store, or invoke native operations.
Publication must independently compare components to deterministic recalculation.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.rna_structure_contracts import COORDINATE_SYSTEM
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.rna_structure_comparison_contracts import COMPARISON_ISSUE_SCHEMA, COMPARISON_REASONS, COUNT, ENERGY_COMPARISON_SCHEMA, ENERGY_STATES, ID, NUMERIC_CELL_SCHEMA, PAIR, PAIR_CHANGE_SCHEMA, PAIRING_STATES, RANK_CLASSES, RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA, SITE_CHANGE_SCHEMA, array, enum, nullable, obj
PROJECTION_VERSION = 'rna_comparison_projection_v1'
PROJECTION_SOURCE = 'execution_rna_structure_comparison_projections'
IDENTIFIER_NAMESPACES = ('rna_comparison_receipt', 'rna_comparison_calculation')
SITE_POPULATION_FIELDS = ('requested_site_count', 'decidable_site_count', 'deleted_site_count', 'inserted_site_count', 'unmapped_site_count', 'unavailable_topology_site_count', 'unresolved_partner_site_count')
PAIR_POPULATION_FIELDS = ('baseline_pair_count', 'variant_pair_count', 'baseline_mapped_pair_count', 'variant_mapped_pair_count', 'baseline_unresolved_pair_count', 'variant_unresolved_pair_count')
SCAN_POPULATION_FIELDS = ('declared_variant_count', 'alias_entry_count', 'native_energy_available_variant_count', 'comparable_variant_count', 'received_failure_variant_count', 'not_supplied_variant_count', 'not_tested_variant_count', 'sheet_energy_unavailable_variant_count', 'model_incompatible_variant_count', 'model_unknown_variant_count', 'rank_population_count')
_NULLABLE_SCAN_COUNTS = frozenset(('comparable_variant_count', 'model_incompatible_variant_count', 'model_unknown_variant_count', 'rank_population_count'))
_MEMBER_CELL_FIELDS = {'energy': 'energy', 'delta': 'delta', 'rank_start': 'exact_rank_start', 'rank_end': 'exact_rank_end'}
_REQUESTS = {branch['properties']['family']['const']: branch for branch in RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA['oneOf']}

def _publication_identifier(namespace):
    return {'type': 'string', 'pattern': '^' + namespace + ':[0-9a-f]{64}$', 'format': 'identifier', 'x-reference-namespace': namespace}
_REASON = nullable(enum(sorted(COMPARISON_REASONS)))
_STRING_VALUE = nullable({'type': 'string'})
RETURNED_NUMERIC_CELL_SCHEMA = obj({key: deepcopy(value) for key, value in NUMERIC_CELL_SCHEMA['properties'].items() if key != 'input_paths'})
RETURNED_SITE_CHANGE_SCHEMA = obj({key: deepcopy(RETURNED_NUMERIC_CELL_SCHEMA if key == 'change_indicator' else value) for key, value in SITE_CHANGE_SCHEMA['properties'].items()})
STRUCTURE_VALUE_SCHEMA = {'oneOf': [obj({'field': {'const': name}, 'state': enum(('present', 'missing_input', 'invalid_input')), 'value': nullable(array(PAIR)) if name == 'pairs' else _STRING_VALUE, 'reason': _REASON}) for name in _REQUESTS['structures']['properties']['fields']['items']['enum']]}
SELECTED_MEMBER_VALUE_SCHEMA = {'oneOf': [obj({'field': enum(_MEMBER_CELL_FIELDS), 'cell': RETURNED_NUMERIC_CELL_SCHEMA}), obj({'field': {'const': 'eligibility'}, 'state': enum(ENERGY_STATES)})]}
PROJECTION_QUALIFICATION_SCHEMA = obj({'codes': array(enum(sorted(COMPARISON_REASONS)), unique=True), 'domain': enum(('pairwise', 'selected_sites', 'declared_scan')), 'baseline_member_id': ID, 'member_ids': array(ID, unique=True), 'site_populations': array(obj({'comparison_id': ID, 'selection_id': ID, **{field: nullable(COUNT) for field in SITE_POPULATION_FIELDS}})), 'pair_populations': array(obj({'comparison_id': ID, **{field: nullable(COUNT) for field in PAIR_POPULATION_FIELDS}})), 'population': nullable(obj({field: nullable(COUNT) if field in _NULLABLE_SCAN_COUNTS else COUNT for field in SCAN_POPULATION_FIELDS})), 'issues': array(COMPARISON_ISSUE_SCHEMA)})
_ENERGY_PROPERTIES = ENERGY_COMPARISON_SCHEMA['properties']
_PAYLOADS = {'energy_comparison': obj({'rows': array(obj({'comparison_id': ID, 'baseline_member_id': ID, 'variant_member_id': ID, 'energy_kind': _ENERGY_PROPERTIES['request']['properties']['quantity'], 'normalization': _ENERGY_PROPERTIES['request']['properties']['normalization'], 'measurements': array(RETURNED_NUMERIC_CELL_SCHEMA), 'order': nullable(_ENERGY_PROPERTIES['order']), 'tolerance_band': nullable(_ENERGY_PROPERTIES['baseline_tolerance_band']), 'compatibility_state': _ENERGY_PROPERTIES['compatibility']['properties']['state']}))}), 'structures': obj({'rows': array(obj({'member_id': ID, 'coordinate_system': {'const': COORDINATE_SYSTEM}, 'structure_origin': nullable(enum(('native_prediction', 'supplied_unknown', 'supplied_prediction', 'supplied_observation'))), 'values': array(STRUCTURE_VALUE_SCHEMA), 'issues': array(COMPARISON_ISSUE_SCHEMA)}))}), 'position_changes': obj({'comparison_id': ID, 'selection_id': ID, 'rows': array(RETURNED_SITE_CHANGE_SCHEMA)}), 'pair_changes': obj({'rows': array(obj({'comparison_id': ID, 'change': PAIR_CHANGE_SCHEMA}))}), 'comparison_counts': obj({'rows': array(obj({'comparison_id': ID, 'selection_id': nullable(ID), 'measurements': array(RETURNED_NUMERIC_CELL_SCHEMA), 'pairing_change_state': nullable(enum(PAIRING_STATES))}))}), 'scan_energy': obj({'scan_id': ID, 'measurements': array(RETURNED_NUMERIC_CELL_SCHEMA), 'rank_class': nullable(enum(RANK_CLASSES))}), 'scan_sites': obj({'scan_id': ID, 'rows': array(obj({'selection_id': ID, 'baseline_index': COUNT, 'measurements': array(RETURNED_NUMERIC_CELL_SCHEMA)}))}), 'scan_members': obj({'scan_id': ID, 'matched_count': COUNT, 'returned_count': COUNT, 'omitted_count': COUNT, 'rows': array(obj({'member_id': ID, 'canonical_member_id': ID, 'values': array(SELECTED_MEMBER_VALUE_SCHEMA)}))})}
RNA_COMPARISON_PROJECTION_RESULT_SCHEMA = {'oneOf': [obj({'schema': {'const': PROJECTION_VERSION}, 'projection_id': ID, 'family': {'const': family}, 'result_receipt_key': _publication_identifier(IDENTIFIER_NAMESPACES[0]), 'calculation_key': _publication_identifier(IDENTIFIER_NAMESPACES[1]), 'population_id': nullable(ID), 'selection': _REQUESTS[family], 'delivery': enum(('values', 'qualified_unavailability', 'empty_selected_set')), 'payload': payload, 'qualification': PROJECTION_QUALIFICATION_SCHEMA}) for family, payload in _PAYLOADS.items()]}

def rna_comparison_fact_sources() -> dict:
    """Return the one exact source schema; registration is a host responsibility."""
    return deepcopy({PROJECTION_SOURCE: {'type': 'array', 'meaning': 'Exactly selected retained RNA comparison facts and required population qualifications; no implied native acquisition or annotation confidence.', 'report_schema': {'type': 'array', 'items': RNA_COMPARISON_PROJECTION_RESULT_SCHEMA, 'x-source': PROJECTION_SOURCE}}})
