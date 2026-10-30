"""Scientific conversion tests on explicitly synthetic assay/model operands."""
from copy import deepcopy
import math

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_assay_grading import (
    ASSAY_TYPES, COMPONENTS, CRITERIA_BY_TYPE, INPUT_VERSION, ROLES,
    assay_grading_input_schema, assay_grading_sheet_schema, grade_assay,
)


def operand(value, unit, key):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None,
        'measurement_keys': [key], 'source_refs': ['source_synthetic_' + key],
        'origin': 'synthetic', 'native_component': key}


def fixture(assay_type='activity_rate', quantity_kind=None):
    kind, unit, effect, variance, predicted, alternative = {
        'activity_rate': ('rate', 'per_min', .68, .11124225, 1., 0.),
        'endpoint_conversion': ('conversion_difference', 'fraction', .6, .04, .8, 0.),
        'product_distribution': ('equilibrium_fraction', 'fraction', .6, .01, .6, .2),
        'reaction_coupling': ('productive_fraction', 'fraction', .8, .01, 1., .2),
        'ligand_binding': ('binding_parameter', 'nM', 25., 4., 20., 40.),
        'transport_response': ('electrical_conductance', 'pS', 12., 1., 14., 5.),
        'protein_signal': ('signal_ratio', 'dimensionless', .8, .01, 1., .2),
        'protein_amount': ('protein_amount_ratio', 'dimensionless', .8, .01, 1., .2),
    }[assay_type]
    quantities = dict.fromkeys(ROLES)
    quantities.update(effect=operand(effect, unit, 'observed_effect'),
        effect_variance=operand(variance, unit + '_squared', 'estimate_variance'),
        assertion_prediction=operand(predicted, unit, 'fixed_assertion_prediction'),
        alternative_prediction=operand(alternative, unit, 'fixed_alternative_prediction'),
        recovery=operand(.95, 'fraction', 'matrix_recovery'),
        attributed_signal=operand(.85, 'uM/min', 'assigned_rate'),
        total_signal=operand(1., 'uM/min', 'net_preparation_rate'),
        condition_test=operand(2., 'uM/min', 'nuisance_test'),
        condition_reference=operand(1.6, 'uM/min', 'nuisance_reference'))
    return {'version': INPUT_VERSION, 'assay_type': assay_type,
        'assertion_ref': 'hypothesis_synthetic_selected_reference_function',
        'quantity_kind': quantity_kind or kind, 'quantities': quantities,
        'interpretations': {criterion: {'status': 'supported',
            'support_refs': ['source_synthetic_design_' + criterion]}
            for criterion in CRITERIA_BY_TYPE[assay_type]},
        'prediction_model': {'kind': 'fixed_predictions_known_normal',
            'variance_interpretation': 'known', 'support_refs': ['source_synthetic_known_normal_model']}}


@pytest.mark.parametrize('assay_type', ASSAY_TYPES)
def test_reusable_protocols_fill_same_dimensions_and_conditional_evidence(assay_type):
    inputs = fixture(assay_type)
    original = deepcopy(inputs)
    sheet = grade_assay(inputs)
    validate_schema(sheet, assay_grading_sheet_schema())
    assert inputs == original
    assert tuple(sheet['cells']) == COMPONENTS
    cells = sheet['cells']
    y = inputs['quantities']['effect']['value']
    variance = inputs['quantities']['effect_variance']['value']
    predicted = inputs['quantities']['assertion_prediction']['value']
    alternative = inputs['quantities']['alternative_prediction']['value']
    expected = ((y - alternative)**2 - (y - predicted)**2) / (2 * variance)
    assert cells['source_log_evidence_ratio']['value'] == pytest.approx(expected)
    assert cells['source_log_evidence_ratio']['status'] == 'conditional'
    assert cells['effect_precision']['value'] == pytest.approx(1 / variance)
    assert cells['recovery_deviation']['value'] == pytest.approx(-.05)
    assert cells['attributed_fraction']['value'] == pytest.approx(.85)
    assert cells['condition_response']['value'] == pytest.approx(1.25)
    assert sheet['annotation_credit'] is None
    assert {'measurement', 'reliability', 'validity', 'attribution', 'comparability',
            'relevance', 'experimental_evidence'} == {c['dimension'] for c in cells.values()}


def test_actual_synthetic_proposal_arithmetic_and_no_double_corrections():
    inputs = fixture()
    sheet = grade_assay(inputs)
    assert sheet['cells']['measured_effect']['value'] == .68
    assert sheet['cells']['source_log_evidence_ratio']['value'] == pytest.approx(1.618090249)
    inputs['quantities']['recovery']['value'] = .5
    inputs['quantities']['attributed_signal']['value'] = .2
    inputs['quantities']['condition_test']['value'] = 10.
    changed = grade_assay(inputs)
    assert changed['cells']['recovery_deviation']['value'] == -.5
    assert changed['cells']['source_log_evidence_ratio']['value'] == sheet['cells']['source_log_evidence_ratio']['value']
    assert changed['cells']['measured_effect']['value'] == .68


def test_binding_display_assay_requires_binding_controls_without_fitted_parameter_claim():
    inputs = fixture('ligand_binding', 'band_display_fraction')
    for role in ('effect', 'assertion_prediction', 'alternative_prediction'):
        inputs['quantities'][role]['unit'] = 'display_fraction'
    inputs['quantities']['effect']['value'] = .5
    inputs['quantities']['assertion_prediction']['value'] = .6
    inputs['quantities']['alternative_prediction']['value'] = .1
    inputs['quantities']['effect_variance']['value'] = .01
    inputs['quantities']['effect_variance']['unit'] = 'display_fraction_squared'
    inputs['interpretations'].pop('binding_parameter_definition')
    assert grade_assay(inputs)['cells']['source_log_evidence_ratio']['value'] is not None
    inputs['interpretations']['binding_controls']['status'] = 'unknown'
    cells = grade_assay(inputs)['cells']
    assert cells['measured_effect']['value'] == .5
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'binding_controls_unknown' in cells['source_log_evidence_ratio']['reasons']


def test_contradictory_experiment_produces_negative_evidence():
    inputs = fixture()
    inputs['quantities']['effect']['value'] = .1
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
    assert score['value'] < 0
    assert score['value'] == pytest.approx(-.4 / .11124225)


@pytest.mark.parametrize('assay_type,criterion', [
    ('activity_rate', 'rate_regime'), ('endpoint_conversion', 'endpoint_alignment'),
    ('product_distribution', 'equilibrium_state'), ('reaction_coupling', 'matched_windows'),
    ('ligand_binding', 'binding_parameter_definition'), ('transport_response', 'transport_endpoint'),
    ('protein_signal', 'signal_normalization'), ('protein_amount', 'amount_basis')])
def test_specific_protocol_failure_prevents_claim_score_but_keeps_measurement(assay_type, criterion):
    inputs = fixture(assay_type)
    inputs['interpretations'][criterion]['status'] = 'unknown'
    sheet = grade_assay(inputs)
    assert sheet['cells']['measured_effect']['status'] == 'populated'
    assert sheet['cells']['source_log_evidence_ratio']['value'] is None
    assert criterion + '_unknown' in sheet['cells']['source_log_evidence_ratio']['reasons']


@pytest.mark.parametrize('criterion', ['matrix_interference', 'background_alternatives',
    'attribution_supported', 'condition_scope', 'assertion_relevance', 'sampling_basis'])
def test_shared_scientific_considerations_are_not_metadata_only(criterion):
    inputs = fixture()
    inputs['interpretations'][criterion]['status'] = 'conflicting'
    cells = grade_assay(inputs)['cells']
    assert cells['source_log_evidence_ratio']['value'] is None
    assert criterion + '_conflicting' in cells['source_log_evidence_ratio']['reasons']


def test_missing_variance_is_not_zero_and_estimated_is_not_known():
    inputs = fixture()
    inputs['quantities']['effect_variance'] = None
    cells = grade_assay(inputs)['cells']
    assert cells['measured_effect']['value'] == .68
    assert cells['effect_precision']['value'] is None
    assert 'effect_variance_not_selected' in cells['source_log_evidence_ratio']['reasons']
    inputs = fixture()
    inputs['prediction_model']['variance_interpretation'] = 'estimated'
    cells = grade_assay(inputs)['cells']
    assert cells['effect_precision']['value'] == pytest.approx(1 / .11124225)
    assert cells['effect_precision']['status'] == 'conditional'
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'normal_model_requires_known_variance' in cells['source_log_evidence_ratio']['reasons']


def test_variance_must_belong_to_the_selected_estimate_and_scale():
    inputs = fixture()
    inputs['quantities']['effect_variance']['unit'] = 'fraction_squared'
    cells = grade_assay(inputs)['cells']
    assert 'variance_unit_mismatch' in cells['effect_precision']['reasons']
    assert cells['source_log_evidence_ratio']['value'] is None
    inputs = fixture()
    inputs['interpretations']['variance_correspondence']['status'] = 'unknown'
    cells = grade_assay(inputs)['cells']
    assert cells['effect_variance']['value'] is None
    assert 'variance_correspondence_unknown' in cells['effect_precision']['reasons']


@pytest.mark.parametrize('value,reason', [(0., 'positive_variance_required'), (-.1, 'negative_variance')])
def test_invalid_variance_cannot_produce_infinite_or_negative_precision(value, reason):
    inputs = fixture()
    inputs['quantities']['effect_variance']['value'] = value
    cells = grade_assay(inputs)['cells']
    assert cells['effect_precision']['value'] is None
    assert reason in cells['effect_precision']['reasons']
    assert cells['source_log_evidence_ratio']['value'] is None


def test_bounded_completion_time_stays_bounded_not_point_activity():
    inputs = fixture('endpoint_conversion', 'completion_time')
    inputs['quantities']['effect'] = {**operand(None, 'min', 'bounded_time'),
        'status': 'bounded', 'reason': 'reported_lower_bound'}
    cells = grade_assay(inputs)['cells']
    assert cells['measured_effect']['value'] is None
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'effect_bounded' in cells['measured_effect']['reasons']
    assert 'reported_lower_bound' in cells['measured_effect']['reasons']


def test_reported_fraction_is_not_a_rate_or_a_time():
    for kind in ('rate',):
        inputs = fixture('activity_rate', kind)
        for role in ('effect', 'assertion_prediction', 'alternative_prediction'):
            inputs['quantities'][role]['unit'] = 'fraction'
        inputs['quantities']['effect_variance']['unit'] = 'fraction_squared'
        cells = grade_assay(inputs)['cells']
        assert cells['measured_effect']['value'] == .68
        assert 'quantity_kind_unit_unsupported' in cells['source_log_evidence_ratio']['reasons']


def test_fixed_prediction_cannot_reuse_the_observation_it_claims_to_predict():
    inputs = fixture()
    inputs['quantities']['assertion_prediction'] = deepcopy(inputs['quantities']['effect'])
    cells = grade_assay(inputs)['cells']
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'prediction_reuses_observed_measurement' in cells['source_log_evidence_ratio']['reasons']


def test_known_shared_input_keys_are_deduplicated_without_independence_claim():
    inputs = fixture()
    inputs['quantities']['attributed_signal']['measurement_keys'].append('shared_blank')
    inputs['quantities']['total_signal']['measurement_keys'].append('shared_blank')
    cell = grade_assay(inputs)['cells']['attributed_fraction']
    assert cell['value'] == .85
    assert cell['measurement_keys'].count('shared_blank') == 1
    assert not any('independent' in c for c in cell['conditions'])


def test_attribution_requires_real_same_endpoint_units_and_positive_total():
    inputs = fixture()
    inputs['quantities']['total_signal']['unit'] = 'mg'
    cells = grade_assay(inputs)['cells']
    assert 'attribution_unit_mismatch' in cells['attributed_fraction']['reasons']
    inputs = fixture()
    inputs['quantities']['total_signal']['value'] = 0
    assert 'positive_total_signal_required' in grade_assay(inputs)['cells']['attributed_fraction']['reasons']


def test_no_clamping_a_noisy_attribution_estimate():
    inputs = fixture()
    inputs['quantities']['attributed_signal']['value'] = 1.1
    cell = grade_assay(inputs)['cells']['attributed_fraction']
    assert cell['value'] == 1.1
    assert 'outside_physical_fraction_range_not_clamped' in cell['conditions']


def test_inapplicable_checks_do_not_impose_different_experiments():
    inputs = fixture('activity_rate', 'rate')
    inputs['interpretations']['kinetic_model']['status'] = 'not_applicable'
    assert grade_assay(inputs)['cells']['source_log_evidence_ratio']['value'] is not None
    inputs = fixture('product_distribution', 'product_fraction')
    inputs['interpretations']['equilibrium_state']['status'] = 'unknown'
    assert grade_assay(inputs)['cells']['source_log_evidence_ratio']['value'] is not None
    inputs = fixture('endpoint_conversion', 'conversion_difference')
    inputs['interpretations']['product_identity']['status'] = 'unknown'
    assert grade_assay(inputs)['cells']['source_log_evidence_ratio']['value'] is not None


@pytest.mark.parametrize('assay_type,criterion', [('activity_rate', 'rate_regime'),
    ('product_distribution', 'species_identity'), ('reaction_coupling', 'stoichiometry')])
def test_required_protocol_condition_cannot_be_called_inapplicable(assay_type, criterion):
    inputs = fixture(assay_type)
    inputs['interpretations'][criterion]['status'] = 'not_applicable'
    with pytest.raises(ContractError, match='required_criterion_not_applicable'):
        grade_assay(inputs)


@pytest.mark.parametrize('mutation', ['support', 'identity', 'nonfinite', 'point_null', 'wrong_type'])
def test_malformed_or_unsupported_normalized_inputs_are_rejected(mutation):
    inputs = fixture()
    if mutation == 'support':
        inputs['interpretations']['condition_scope']['support_refs'] = []
    elif mutation == 'identity':
        inputs['quantities']['effect']['measurement_keys'] = []
    elif mutation == 'nonfinite':
        inputs['quantities']['effect']['value'] = math.inf
    elif mutation == 'point_null':
        inputs['quantities']['effect']['value'] = None
    else:
        inputs['quantity_kind'] = 'completion_time'
    with pytest.raises(ContractError):
        grade_assay(inputs)


def test_missing_source_inputs_remain_distinct_from_missing_interpretations():
    inputs = fixture()
    inputs['quantities']['effect_variance'] = None
    del inputs['interpretations']['rate_regime']
    reasons = grade_assay(inputs)['cells']['source_log_evidence_ratio']['reasons']
    assert 'effect_variance_not_selected' in reasons
    assert 'rate_regime_not_selected' in reasons


@pytest.mark.parametrize('qualification', ['nonintended_conditions_unknown',
    'estimated_covariance', 'variance_status:estimated', 'normalization_unresolved', 'source_conflicting'])
def test_original_conditional_qualifications_survive_and_cannot_be_upgraded(qualification):
    inputs = fixture()
    inputs['quantities']['effect']['qualifications'] = [qualification]
    cells = grade_assay(inputs)['cells']
    assert cells['measured_effect']['value'] == .68
    assert qualification in cells['measured_effect']['conditions']
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'effect_source_qualification:' + qualification in cells['source_log_evidence_ratio']['reasons']
    assert cells['effect_precision']['status'] == 'conditional'


def test_unrelated_diagnostic_qualification_does_not_change_an_already_corrected_effect():
    inputs = fixture()
    inputs['quantities']['recovery']['qualifications'] = ['diagnostic_variance_unknown']
    cells = grade_assay(inputs)['cells']
    assert cells['source_log_evidence_ratio']['value'] == pytest.approx(1.618090249)
    assert 'diagnostic_variance_unknown' in cells['recovery_deviation']['conditions']


def test_huge_integer_operand_fails_with_typed_error_instead_of_overflow():
    inputs = fixture()
    inputs['quantities']['effect']['value'] = 10**400
    with pytest.raises(ContractError, match='finite_number_required'):
        grade_assay(inputs)


def test_existing_native_mass_normalized_rate_unit_is_supported():
    inputs = fixture()
    for role in ('effect', 'assertion_prediction', 'alternative_prediction'):
        inputs['quantities'][role]['unit'] = 'umol/min/mg'
    inputs['quantities']['effect_variance']['unit'] = 'umol/min/mg_squared'
    assert grade_assay(inputs)['cells']['source_log_evidence_ratio']['value'] == pytest.approx(1.618090249)


def test_endpoint_amount_requires_product_identity_or_witnessed_disappearance_scope():
    inputs = fixture('endpoint_conversion', 'endpoint_amount')
    for role in ('effect', 'assertion_prediction', 'alternative_prediction'):
        inputs['quantities'][role]['unit'] = 'uM'
    inputs['quantities']['effect_variance']['unit'] = 'uM_squared'
    inputs['interpretations']['product_identity']['status'] = 'unknown'
    cells = grade_assay(inputs)['cells']
    assert cells['measured_effect']['value'] == .6
    assert 'product_identity_unknown' in cells['source_log_evidence_ratio']['reasons']
    inputs['interpretations']['product_identity']['status'] = 'not_applicable'
    assert grade_assay(inputs)['cells']['source_log_evidence_ratio']['value'] is not None
    inputs['interpretations']['product_identity']['support_refs'] = []
    with pytest.raises(ContractError, match='interpretation_support_required'):
        grade_assay(inputs)


def test_all_schemas_validate_and_form_does_not_count_additional_assays():
    for assay_type in ASSAY_TYPES:
        inputs = fixture(assay_type)
        validate_schema(inputs, assay_grading_input_schema())
        output = grade_assay(inputs)
        assert len(output['cells']) == 9
        assert output['assay_type'] == assay_type
        assert 'assay_count' not in output
