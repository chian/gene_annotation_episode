"""Source-bound precision/Z-prime and possessed recovery operands.

Scientific relationships are explicit caller interpretations. Callbacks authorize
received facts; this module performs no acquisition, private-sheet lookup or IO.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import REF, obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_assay_inputs import _witness_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_partner_source_fields import number_selector_schema
ORIGINS = {'primary_source': 'reported', 'retained_extraction': 'derived', 'synthetic_fixture': 'synthetic'}
CONTEXT_FIELDS = ('experiment', 'analyte', 'matrix', 'method', 'endpoint', 'repetition', 'mean_definition', 'nominal_uncertainty')
RELATIONSHIPS = {'basis': ('within_run', 'between_run', 'between_preparation', 'unspecified', 'unknown', 'conflicting'), 'mean_precision_population': ('same', 'different', 'unknown', 'conflicting'), 'cv_denominator': ('displayed_measured_mean', 'other_reported_mean', 'unknown', 'conflicting'), 'recovery_context': ('same', 'different', 'unknown', 'conflicting'), 'validation_relation': ('held_out_observations_and_stock_supported', 'shared_fit_or_stock', 'unknown', 'conflicting')}
FORMULA_RELATIONS = ('conventional_zprime', 'different', 'unknown', 'conflicting')
PAIR_REASONS = ('recovery_pair_not_supplied', 'recovery_pair_incomplete', 'recovery_pair_identity_mismatch', 'recovery_pair_dependencies_mismatch', 'recovery_pair_exact_identity_mismatch', 'recovery_pair_unavailable', 'recovery_pair_units_mismatch', 'recovery_pair_scope_mismatch', 'recovery_pair_control_unknown', 'recovery_pair_control_conflicting', 'enzyme_activity_spike_is_not_reporter_standard', 'recovery_pair_source_meanings_mismatch')
NUMBER_REASONS = ('source_approximation_unimplemented', 'source_range_unimplemented', 'nonfinite_source_statistic_unavailable', 'source_negated_comparison_unimplemented')
RELATIONS = ('point', 'lt', 'le', 'gt', 'ge', 'approximate', 'range', 'unresolved')

def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}

def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})

def _retained_witness_schema():
    return obj({**deepcopy(_witness_schema()['properties']), 'artifact_ref': deepcopy(REF)})

def _number_schema():
    selector = obj({**number_selector_schema()['properties'], 'witness': _retained_witness_schema()})
    return obj({'selector': selector, 'raw_number': {'type': 'string', 'minLength': 1}, 'native_value': {'type': ['number', 'null']}, 'native_exact_value': _nullable(_exact_schema()), 'relation': {'enum': list(RELATIONS)}, 'capability_reason': {'enum': [*NUMBER_REASONS, None]}, 'representation_witness': _retained_witness_schema(), 'measurement_key': deepcopy(REF), 'number_start_bytes': {'type': 'integer', 'minimum': 0}, 'number_end_bytes': {'type': 'integer', 'minimum': 1}, 'origin': {'enum': list(ORIGINS.values())}})
