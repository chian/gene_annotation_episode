"""Source-bound product/cofactor operands and explicit scientific relationships.

Callbacks authorize actually received sources. Scientific role/model selections
are witnessed interpretations, not facts inferred from matching names or units.
This pure reader performs no acquisition, persistence, model call or credit work.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import REF, obj
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_assay_inputs import _witness_schema
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_measurement_validation_inputs import _number_schema, _retained_witness_schema, _nullable, _array, _exact_schema, NUMBER_REASONS, RELATIONS
VERSION = 'a105_product_coupling_inputs_v1'
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'synthetic_fixture')
ORIGINS = dict(primary_source='reported', retained_extraction='derived', synthetic_fixture='synthetic')
ROLES = ('product', 'cofactor', 'reported_coupling')
CONTEXT_FIELDS = ('experiment', 'organism', 'expression_host', 'molecule', 'construct', 'preparation', 'partners', 'intended_change', 'substrate', 'product', 'product_identity_method', 'product_conditions', 'cofactor_conditions', 'blank', 'calibration', 'normalization', 'repetition', 'uncertainty', 'source_conflict')
QUANTITY_MEANINGS = {'endpoint_role': ('product_formation', 'cofactor_consumption', 'coupling_fraction', 'other_endpoint', 'unknown', 'conflicting'), 'measurement_semantics': ('reported_point', 'reported_nondetection', 'reported_negligible', 'unknown', 'conflicting'), 'normalization': ('per_assayed_molecule', 'per_active_molecule', 'other_basis', 'unknown', 'conflicting')}
RELATIONSHIPS = {'source_pairing': ('author_assigned', 'not_assigned', 'unknown', 'conflicting'), 'same_molecule': ('same', 'different', 'unknown', 'conflicting'), 'same_preparation': ('same', 'different', 'unknown', 'conflicting'), 'normalization': ('compatible', 'incompatible', 'unknown', 'conflicting'), 'conditions': ('matched', 'different', 'unknown', 'conflicting'), 'product_identity': ('chemically_identified', 'other_product', 'reporter_only', 'unknown', 'conflicting'), 'molecular_attribution': ('controlled', 'mixed_or_unresolved', 'unknown', 'conflicting')}
NU_STATUSES = ('fixed_model', 'uncertain_model', 'unknown', 'conflicting')
EXTRA_NUMBER_REASONS = ('nondetection_source_text',)
UNIT_REASONS = ('source_unit_not_supplied', 'unsupported_source_rate_unit', 'unsupported_coupling_unit')
COVARIANCE_REASONS = ('covariance_not_supplied', 'covariance_json_invalid', 'covariance_contract_mismatch', 'covariance_owner_mismatch', 'covariance_units_mismatch', 'covariance_basis_mismatch', 'covariance_status_unknown', 'covariance_nonfinite_or_non_numeric', 'covariance_shape_invalid', 'covariance_not_symmetric', 'covariance_not_positive_semidefinite', 'covariance_rate_inputs_unavailable')

def _interpreted_schema(values, enriched=False):
    return obj({**({'kind': {'const': 'source_interpretation'}} if enriched else {}), 'value': {'enum': list(values)}, 'witnesses': _array(_retained_witness_schema() if enriched else _witness_schema())})

def _nu_schema(enriched=False):
    return obj({'kind': {'const': 'interpreted_reaction_account'}, 'direction': {'const': 'cofactor_per_product'}, 'status': {'enum': list(NU_STATUSES)}, 'exact_value': _nullable(_exact_schema()), 'witnesses': _array(_retained_witness_schema() if enriched else _witness_schema()), **({'model_key': _nullable(deepcopy(REF))} if enriched else {})})

def _coupling_number_schema():
    result = _number_schema()
    result['properties']['capability_reason'] = {'enum': [*NUMBER_REASONS, *EXTRA_NUMBER_REASONS, None]}
    return result

def _unit_schema():
    return obj({'witness': _retained_witness_schema(), 'raw_unit': {'type': 'string', 'minLength': 1}, 'canonical_unit': {'type': ['string', 'null']}, 'multiplier_exact': _nullable(_exact_schema()), 'unavailable_reason': {'enum': [*UNIT_REASONS, None]}})

def _covariance_schema():
    return obj({'source_ref': _nullable(deepcopy(REF)), 'artifact_ref': _nullable(deepcopy(REF)), 'status': {'enum': ['not_supplied', 'valid_known', 'valid_estimated', 'unavailable']}, 'unavailable_reason': {'enum': [*COVARIANCE_REASONS, None]}, 'origin': {'enum': ['reported', 'derived', 'synthetic', None]}, 'measurement_keys': _array(REF), 'units': _array({'type': 'string'}), 'basis': {'type': ['string', 'null']}, 'variance_status': {'enum': ['known', 'estimated', 'unknown', None]}, 'matrix_exact': _nullable(_array(_array(_exact_schema())))})

def product_coupling_extraction_schema():
    quantity = obj({'number': _nullable(_coupling_number_schema()), 'quantity_label': _nullable(_retained_witness_schema()), 'unit': _nullable(_unit_schema()), **{name: _interpreted_schema(values, True) for name, values in QUANTITY_MEANINGS.items()}, 'physical_identity': _nullable(_retained_witness_schema()), 'dependency_witnesses': _array(_retained_witness_schema()), 'canonical_value': {'type': ['number', 'null']}, 'canonical_exact_value': _nullable(_exact_schema()), 'canonical_unit': {'type': ['string', 'null']}, 'dependency_keys': _array(REF, True), 'physical_identity_key': _nullable(deepcopy(REF))})
    return obj({'version': {'const': VERSION}, 'source_ref': deepcopy(REF), 'artifact_ref': deepcopy(REF), 'source_kind': {'enum': list(SOURCE_KINDS)}, 'context': obj({name: _nullable(obj({'value': {'type': 'string', 'minLength': 1}, 'witness': _retained_witness_schema()})) for name in CONTEXT_FIELDS}), 'quantities': obj({role: _nullable(quantity) for role in ROLES}), 'relationships': obj({name: _interpreted_schema(values, True) for name, values in RELATIONSHIPS.items()}), 'nu_cofactor_per_product': _nu_schema(True), 'covariance': _covariance_schema(), 'source_refs': _array(REF, True), 'input_origins': _array({'enum': list(ORIGINS.values())}, True)})
