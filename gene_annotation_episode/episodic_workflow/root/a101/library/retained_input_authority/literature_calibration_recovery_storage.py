"""Selected recovery controls, saved numerical sections and exact typed custody.

The operation assigns no experimental meaning itself. It executes the caller's
source selection and saves the reader/calculator result once. Returning or
reconstructing that result validates custody without scientific source IO.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_calibration_recovery_inputs import SOURCE_KINDS, LITERAL_FIELDS, CONTROL_KINDS, APPLICABILITIES, SPREAD_KINDS
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_calibration_recovery_calculations import COMPONENTS, FORMULAS, REASONS
NAMESPACE = 'literature_calibration_recovery_cells'
TEXT = {'type': 'string', 'minLength': 1}
SECTIONS = ('calibration_validity', 'matrix_activity_response', 'recovery_control_role_unresolved')
SCOPE_REASONS = ('control_dimension_mismatch', 'control_kind_unknown', 'control_kind_conflicting', None)
QUALIFICATIONS = ('source_quotes_do_not_prove_scientific_roles', 'shared_units_do_not_establish_comparison_linkage', 'no_target_measurement_supplied', 'replicate_independence_not_established', 'denominator_uncertainty_and_covariance_not_supplied', 'recovery_bias_and_inverse_share_original_operands', 'no_overall_reliability_grade', 'no_annotation_credit')

def _array(schema, *, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _exact():
    return {'anyOf': [obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}}), {'type': 'null'}]}

def _cell(component=None):
    return obj({'value': {'type': ['number', 'null']}, 'unit': {'enum': ['nmol', 'nmol/min', 'fraction', 'percent', 'fraction_squared', None]}, 'status': {'enum': ['populated', 'unavailable']}, 'origin': {'enum': ['reported', 'derived', 'synthetic']}, 'input_origins': _array({'enum': ['reported', 'derived', 'synthetic']}, unique=True), 'unavailable_reason': {'enum': [*REASONS, None]}, 'formula': {'const': FORMULAS[component]} if component else {'enum': list(FORMULAS.values())}, 'exact_value': _exact(), 'input_measurement_keys': _array(TEXT, unique=True), 'conditional_on': {'const': ['source_role_assignments']}})

def calibration_recovery_cells_schema():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    row = obj({'sheet_ref': deepcopy(ref), 'evidence_source_ref': deepcopy(ref), 'evaluation_scope': {'const': 'source_calibration_recovery'}, 'component': {'enum': list(COMPONENTS)}, **_cell()['properties'], 'source_kind': {'enum': list(SOURCE_KINDS)}, 'section': {'enum': list(SECTIONS)}, 'control_kind': {'enum': list(CONTROL_KINDS)}, 'applicability': {'enum': list(APPLICABILITIES)}, 'spread_kind': {'enum': list(SPREAD_KINDS)}, 'source_meanings': obj({name: {'type': ['string', 'null'], 'minLength': 1} for name in LITERAL_FIELDS}), 'interpretation_scope_unavailable_reason': {'enum': list(SCOPE_REASONS)}, 'qualifications': {'const': list(QUALIFICATIONS)}})
    return {**_array(row), 'x-source': NAMESPACE}
