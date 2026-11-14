"""Original calibration_recovery return declarations and schema; no service execution."""
from copy import deepcopy
import json
from gene_annotation_episode.domain import obj

SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")

LITERAL_FIELDS = ("experiment", "analyte", "matrix", "endpoint", "blank_treatment",
                  "expected_quantity_basis")

CONTROL_KINDS = ("reporter_standard", "enzyme_activity_spike", "unknown", "conflicting")

APPLICABILITIES = ("same_matrix_same_endpoint_supported", "different_matrix_or_endpoint",
                   "unknown", "conflicting")

SPREAD_KINDS = ("SD", "SEM", "unspecified", "unknown")

COMPONENTS = ("nominal", "measured", "signed_difference", "recovery", "relative_bias",
              "percent_bias", "inverse_recovery", "reported_measured_spread", "measured_sd",
              "measured_cv", "reported_recovery", "displayed_minus_reported_recovery",
              "correction_for_other_measurement", "recovery_variance")

FORMULAS = {"nominal": "source_expected_quantity", "measured": "source_measured_quantity",
    "signed_difference": "measured-nominal", "recovery": "measured/nominal",
    "relative_bias": "measured/nominal-1", "percent_bias": "100*(measured/nominal-1)",
    "inverse_recovery": "nominal/measured", "reported_measured_spread": "source_measured_spread",
    "measured_sd": "source_measured_spread_when_explicitly_SD", "measured_cv": "measured_SD/measured",
    "reported_recovery": "source_reported_recovery_as_fraction",
    "displayed_minus_reported_recovery": "measured/nominal-reported_recovery",
    "correction_for_other_measurement": "requires_linked_target_measurement_and_applicable_recovery",
    "recovery_variance": "requires_measured_and_nominal_uncertainty_and_covariance"}

REASONS = ("nominal_not_supplied", "measured_not_supplied", "shared_unit_not_supplied",
    "nonpositive_nominal", "nonpositive_measured", "measured_spread_not_supplied",
    "spread_kind_not_SD", "reported_recovery_not_supplied", "reported_recovery_unit_not_supplied",
    "control_dimension_mismatch", "no_target_measurement_supplied",
    "denominator_uncertainty_and_covariance_not_supplied", "numerical_model_range")



NAMESPACE = 'literature_calibration_recovery_cells'

TEXT = {'type': 'string', 'minLength': 1}

SECTIONS = ('calibration_validity', 'matrix_activity_response', 'recovery_control_role_unresolved')

SCOPE_REASONS = ('control_dimension_mismatch', 'control_kind_unknown', 'control_kind_conflicting', None)

QUALIFICATIONS = ('source_quotes_do_not_prove_scientific_roles', 'shared_units_do_not_establish_comparison_linkage',
    'no_target_measurement_supplied', 'replicate_independence_not_established',
    'denominator_uncertainty_and_covariance_not_supplied', 'recovery_bias_and_inverse_share_original_operands',
    'no_overall_reliability_grade', 'no_annotation_credit')

def _array(schema, *, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}



def _exact():
    return {'anyOf': [obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
        'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}}), {'type': 'null'}]}



def _cell(component=None):
    return obj({'value': {'type': ['number', 'null']},
        'unit': {'enum': ['nmol', 'nmol/min', 'fraction', 'percent', 'fraction_squared', None]},
        'status': {'enum': ['populated', 'unavailable']},
        'origin': {'enum': ['reported', 'derived', 'synthetic']},
        'input_origins': _array({'enum': ['reported', 'derived', 'synthetic']}, unique=True),
        'unavailable_reason': {'enum': [*REASONS, None]},
        'formula': {'const': FORMULAS[component]} if component else {'enum': list(FORMULAS.values())},
        'exact_value': _exact(), 'input_measurement_keys': _array(TEXT, unique=True),
        'conditional_on': {'const': ['source_role_assignments']}})



def calibration_recovery_cells_schema():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    row = obj({'sheet_ref': deepcopy(ref), 'evidence_source_ref': deepcopy(ref),
        'evaluation_scope': {'const': 'source_calibration_recovery'},
        'component': {'enum': list(COMPONENTS)}, **_cell()['properties'],
        'source_kind': {'enum': list(SOURCE_KINDS)}, 'section': {'enum': list(SECTIONS)},
        'control_kind': {'enum': list(CONTROL_KINDS)}, 'applicability': {'enum': list(APPLICABILITIES)},
        'spread_kind': {'enum': list(SPREAD_KINDS)},
        'source_meanings': obj({name: {'type': ['string', 'null'], 'minLength': 1} for name in LITERAL_FIELDS}),
        'interpretation_scope_unavailable_reason': {'enum': list(SCOPE_REASONS)},
        'qualifications': {'const': list(QUALIFICATIONS)}})
    return {**_array(row), 'x-source': NAMESPACE}



