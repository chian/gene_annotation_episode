"""Censoring and estimated uncertainty remain usable in required A105 scoring."""
from copy import deepcopy
import math
import pytest
from scipy.special import log_ndtr
from scipy.stats import norm, t as student_t
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import grade_assay, assay_grading_sheet_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_assay_grading import fixture, operand

def model_inputs(kind='fixed_predictions_estimated_normal'):
    inputs = fixture('endpoint_conversion')
    inputs['prediction_model'].update(kind=kind, variance_interpretation='estimated')
    inputs['quantities']['effect_variance']['qualifications'] = ['estimated_covariance']
    return inputs

def bounded_inputs(relation='lt', lower=None, upper=0.2, *, kind='fixed_predictions_known_normal'):
    inputs = fixture('endpoint_conversion')
    inputs['prediction_model']['kind'] = kind
    if kind != 'fixed_predictions_known_normal':
        inputs['prediction_model']['variance_interpretation'] = 'estimated'
    inputs['quantities']['effect'].update(value=None, status='bounded', reason='reported_nondetection', bound={'relation': relation, 'lower': lower, 'upper': upper})
    return inputs

def test_estimated_variance_scores_under_explicit_approximation_without_becoming_known():
    inputs = model_inputs()
    original = deepcopy(inputs)
    cells = grade_assay(inputs)['cells']
    assert cells['source_log_evidence_ratio']['value'] == pytest.approx(4)
    assert cells['source_log_evidence_ratio']['status'] == 'conditional'
    assert 'estimated_variance_plugin_normal_approximation' in cells['source_log_evidence_ratio']['conditions']
    assert 'variance_estimation_uncertainty_not_integrated' in cells['source_log_evidence_ratio']['conditions']
    assert cells['effect_variance']['value'] == 0.04
    assert inputs == original

def test_estimated_variance_is_not_automatically_reinterpreted_as_known_or_t():
    inputs = model_inputs('fixed_predictions_known_normal')
    cells = grade_assay(inputs)['cells']
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'normal_model_requires_known_variance' in cells['source_log_evidence_ratio']['reasons']
    inputs['prediction_model']['kind'] = 'fixed_predictions_student_t'
    cells = grade_assay(inputs)['cells']
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'effect_degrees_of_freedom_not_selected' in cells['source_log_evidence_ratio']['reasons']

def test_selected_t_model_uses_reported_degrees_of_freedom_and_scale():
    inputs = model_inputs('fixed_predictions_student_t')
    inputs['quantities']['effect_degrees_of_freedom'] = operand(4, 'count', 'reported_df')
    cells = grade_assay(inputs)['cells']
    expected = student_t.logpdf(-1, 4) - student_t.logpdf(3, 4)
    score = cells['source_log_evidence_ratio']
    assert score['value'] == pytest.approx(expected)
    assert score['value'] != pytest.approx(4)
    assert 'reported_df' in score['measurement_keys']
    assert 'explicit_student_t_residual_model' in score['conditions']
    assert 't_sampling_model_is_not_inferred_from_reported_sd' in score['conditions']
    assert 'effect_degrees_of_freedom' not in cells

@pytest.mark.parametrize('df,unit,reason', [(0, 'count', 'positive_degrees_of_freedom_required'), (-1, 'count', 'positive_degrees_of_freedom_required'), (4, 'mg', 'degrees_of_freedom_unit_mismatch')])
def test_t_model_requires_usable_actual_degrees_of_freedom(df, unit, reason):
    inputs = model_inputs('fixed_predictions_student_t')
    inputs['quantities']['effect_degrees_of_freedom'] = operand(df, unit, 'reported_df')
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
    assert score['value'] is None
    assert reason in score['reasons']

@pytest.mark.parametrize('relation', ['lt', 'le'])
def test_below_detection_uses_event_probability_not_zero_or_detection_limit(relation):
    inputs = bounded_inputs(relation)
    sheet = grade_assay(inputs)
    validate_schema(sheet, assay_grading_sheet_schema())
    cells = sheet['cells']
    observed = cells['measured_effect']
    assert observed['status'] == 'bounded' and observed['value'] is None
    assert observed['bound'] == {'relation': relation, 'lower': None, 'upper': 0.2}
    assert observed['reasons'] == []
    assert cells['effect_variance']['value'] == 0.04
    assert cells['effect_precision']['value'] == 25
    assert cells['assertion_prediction_error']['bound']['upper'] == pytest.approx(-0.6)
    score = cells['source_log_evidence_ratio']
    expected = math.log(norm.cdf(0.2, loc=0.8, scale=0.2) / norm.cdf(0.2, loc=0, scale=0.2))
    assert score['value'] == pytest.approx(expected)
    assert score['value'] < 0
    assert all((score['value'] != pytest.approx(imputed) for imputed in (-8, -4)))
    assert 'probability_of_reported_censoring_event_not_density_at_limit_or_zero' in score['conditions']
    assert 'bound' not in score

@pytest.mark.parametrize('relation', ['gt', 'ge'])
def test_lower_limit_uses_survival_probability(relation):
    inputs = bounded_inputs(relation, 0.7, None)
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
    expected = norm.logsf(0.7, loc=0.8, scale=0.2) - norm.logsf(0.7, loc=0, scale=0.2)
    assert score['value'] == pytest.approx(expected)
    assert score['value'] > 0

@pytest.mark.parametrize('lower,upper', [(0.1, 0.3), (2.0, 2.1), (-2.1, -2.0)])
def test_interval_observation_uses_interval_probability_with_stable_tails(lower, upper):
    inputs = bounded_inputs('interval', lower, upper)
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']

    def probability(mu):
        if lower >= mu:
            return norm.sf(lower, loc=mu, scale=0.2) - norm.sf(upper, loc=mu, scale=0.2)
        return norm.cdf(upper, loc=mu, scale=0.2) - norm.cdf(lower, loc=mu, scale=0.2)
    expected = math.log(probability(0.8)) - math.log(probability(0))
    assert score['value'] == pytest.approx(expected)

def test_far_tail_nondetection_remains_finite():
    inputs = bounded_inputs('lt', None, -8.0)
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
    assert score['value'] == pytest.approx(float(log_ndtr(-44) - log_ndtr(-40)))
    assert math.isfinite(score['value'])

@pytest.mark.parametrize('kind', ['fixed_predictions_estimated_normal', 'fixed_predictions_student_t'])
def test_bounded_result_scores_with_estimated_uncertainty_under_selected_model(kind):
    inputs = bounded_inputs(kind=kind)
    inputs['quantities']['effect_variance']['qualifications'] = ['estimated_covariance']
    inputs['quantities']['effect_degrees_of_freedom'] = operand(3, 'count', 'actual_df')
    cells = grade_assay(inputs)['cells']
    distribution = student_t(3) if kind.endswith('student_t') else norm
    expected = distribution.logcdf(-3) - distribution.logcdf(1)
    assert cells['source_log_evidence_ratio']['value'] == pytest.approx(expected)
    assert cells['measured_effect']['bound']['upper'] == 0.2

@pytest.mark.parametrize('qualification', ['variance_unknown', 'covariance_unresolved', 'source_conflicting'])
def test_approximation_cannot_erase_missing_or_conflicting_uncertainty(qualification):
    inputs = model_inputs()
    inputs['quantities']['effect_variance']['qualifications'].append(qualification)
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
    assert score['value'] is None
    assert 'effect_variance_source_qualification:' + qualification in score['reasons']

def test_nondetection_without_limit_preserves_missing_information():
    inputs = bounded_inputs()
    del inputs['quantities']['effect']['bound']
    cells = grade_assay(inputs)['cells']
    assert cells['measured_effect']['value'] is None
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'reported_nondetection' in cells['measured_effect']['reasons']

@pytest.mark.parametrize('bound', [{'relation': 'lt', 'lower': 0.0, 'upper': 0.2}, {'relation': 'gt', 'lower': None, 'upper': 0.2}, {'relation': 'interval', 'lower': 0.2, 'upper': 0.1}, {'relation': 'interval', 'lower': 0.2, 'upper': 0.2}])
def test_inconsistent_bound_metadata_is_rejected(bound):
    inputs = bounded_inputs()
    inputs['quantities']['effect']['bound'] = bound
    with pytest.raises(ContractError, match='bound_limits_inconsistent'):
        grade_assay(inputs)

def test_bound_event_does_not_relax_assay_applicability_or_prediction_identity():
    inputs = bounded_inputs()
    inputs['interpretations']['matrix_interference']['status'] = 'unknown'
    cells = grade_assay(inputs)['cells']
    assert cells['measured_effect']['status'] == 'bounded'
    assert 'matrix_interference_unknown' in cells['source_log_evidence_ratio']['reasons']
    inputs = bounded_inputs()
    inputs['quantities']['assertion_prediction']['measurement_keys'] = inputs['quantities']['effect']['measurement_keys']
    assert 'prediction_reuses_observed_measurement' in grade_assay(inputs)['cells']['source_log_evidence_ratio']['reasons']


def test_existing_native_rate_limit_reaches_censored_scoring(tmp_path):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_rate_native_storage import setup_native_store
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_storage import LiteratureRateRepository
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_grading_inputs import _component
    store, context, args = setup_native_store(tmp_path, reference='<12')
    try:
        repository = LiteratureRateRepository(store, context.run_id).source_projection()
        outcome = repository.populate_native(context, args, 'bounded_reference')
        ref = outcome['result']['sheet_ref']
        row, = repository.project_cells([ref], permitted_record_refs=[ref], components=['reference_rate'])
        observed, _ = _component({'namespace': 'literature_rate_source_cells', 'sheet_ref': ref, 'component': 'reference_rate'}, lambda *args: [row])
        assert observed['status'] == 'bounded'
        assert observed['bound'] == {'relation': 'lt', 'lower': None, 'upper': 0.012}
        inputs = fixture('activity_rate', 'rate')
        inputs['quantities']['effect'] = observed
        inputs['quantities']['effect_variance'] = operand(4e-06, observed['unit'] + '_squared', 'known_variance')
        inputs['quantities']['assertion_prediction'] = operand(0.02, observed['unit'], 'fixed_A')
        inputs['quantities']['alternative_prediction'] = operand(0.005, observed['unit'], 'fixed_B')
        score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
        assert score['value'] == pytest.approx(float(log_ndtr(-4) - log_ndtr(3.5)))
        assert 'physical_measurement_identity_unknown' in score['conditions']
    finally:
        store.close()

