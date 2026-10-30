"""Censoring and estimated uncertainty remain usable in required A105 scoring."""
from copy import deepcopy
import math

import pytest
from scipy.special import log_ndtr
from scipy.stats import norm, t as student_t

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_assay_grading import grade_assay, assay_grading_sheet_schema
from test_literature_assay_grading import fixture, operand


def model_inputs(kind='fixed_predictions_estimated_normal'):
    inputs = fixture('endpoint_conversion')
    inputs['prediction_model'].update(kind=kind, variance_interpretation='estimated')
    inputs['quantities']['effect_variance']['qualifications'] = ['estimated_covariance']
    return inputs


def bounded_inputs(relation='lt', lower=None, upper=.2, *, kind='fixed_predictions_known_normal'):
    inputs = fixture('endpoint_conversion')
    inputs['prediction_model']['kind'] = kind
    if kind != 'fixed_predictions_known_normal':
        inputs['prediction_model']['variance_interpretation'] = 'estimated'
    inputs['quantities']['effect'].update(value=None, status='bounded', reason='reported_nondetection',
        bound={'relation': relation, 'lower': lower, 'upper': upper})
    return inputs


def test_estimated_variance_scores_under_explicit_approximation_without_becoming_known():
    inputs = model_inputs()
    original = deepcopy(inputs)
    cells = grade_assay(inputs)['cells']
    # y=.6, assertion=.8, alternative=0, estimated variance=.04.
    assert cells['source_log_evidence_ratio']['value'] == pytest.approx(4)
    assert cells['source_log_evidence_ratio']['status'] == 'conditional'
    assert 'estimated_variance_plugin_normal_approximation' in cells['source_log_evidence_ratio']['conditions']
    assert 'variance_estimation_uncertainty_not_integrated' in cells['source_log_evidence_ratio']['conditions']
    assert cells['effect_variance']['value'] == .04
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


@pytest.mark.parametrize('df,unit,reason', [(0, 'count', 'positive_degrees_of_freedom_required'),
    (-1, 'count', 'positive_degrees_of_freedom_required'), (4, 'mg', 'degrees_of_freedom_unit_mismatch')])
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
    assert observed['bound'] == {'relation': relation, 'lower': None, 'upper': .2}
    assert observed['reasons'] == []
    assert cells['effect_variance']['value'] == .04
    assert cells['effect_precision']['value'] == 25
    assert cells['assertion_prediction_error']['bound']['upper'] == pytest.approx(-.6)
    score = cells['source_log_evidence_ratio']
    expected = math.log(norm.cdf(.2, loc=.8, scale=.2) / norm.cdf(.2, loc=0, scale=.2))
    assert score['value'] == pytest.approx(expected)
    assert score['value'] < 0
    assert all(score['value'] != pytest.approx(imputed) for imputed in (-8, -4))
    assert 'probability_of_reported_censoring_event_not_density_at_limit_or_zero' in score['conditions']
    assert 'bound' not in score  # Numeric measurements remain separately requested cells.


@pytest.mark.parametrize('relation', ['gt', 'ge'])
def test_lower_limit_uses_survival_probability(relation):
    inputs = bounded_inputs(relation, .7, None)
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
    expected = norm.logsf(.7, loc=.8, scale=.2) - norm.logsf(.7, loc=0, scale=.2)
    assert score['value'] == pytest.approx(expected)
    assert score['value'] > 0


@pytest.mark.parametrize('lower,upper', [(.1, .3), (2., 2.1), (-2.1, -2.)])
def test_interval_observation_uses_interval_probability_with_stable_tails(lower, upper):
    inputs = bounded_inputs('interval', lower, upper)
    score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
    def probability(mu):
        if lower >= mu:
            return norm.sf(lower, loc=mu, scale=.2) - norm.sf(upper, loc=mu, scale=.2)
        return norm.cdf(upper, loc=mu, scale=.2) - norm.cdf(lower, loc=mu, scale=.2)
    expected = math.log(probability(.8)) - math.log(probability(0))
    assert score['value'] == pytest.approx(expected)


def test_far_tail_nondetection_remains_finite():
    inputs = bounded_inputs('lt', None, -8.)
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
    assert cells['measured_effect']['bound']['upper'] == .2


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


@pytest.mark.parametrize('bound', [
    {'relation': 'lt', 'lower': 0., 'upper': .2},
    {'relation': 'gt', 'lower': None, 'upper': .2},
    {'relation': 'interval', 'lower': .2, 'upper': .1},
    {'relation': 'interval', 'lower': .2, 'upper': .2},
])
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


def test_existing_summary_sd_variance_and_df_reach_t_scoring_without_reextraction(tmp_path):
    from test_literature_kinetic_summary_precision_binding_251 import setup, selected
    from gene_annotation_episode.literature_assay_grading_inputs import _component
    components = ['source_reported_parameter', 'source_mean_variance', 'source_mean_interval_df']
    store, context, args, binding, _ = setup(tmp_path, components=components)
    try:
        args['selection']['interval_request'] = 'student_t_95'
        _, _, rows = selected(store, context, args, binding)
        inputs = fixture('activity_rate', 'turnover')
        inputs['prediction_model'].update(kind='fixed_predictions_student_t', variance_interpretation='estimated')
        for role, component in zip(('effect', 'effect_variance', 'effect_degrees_of_freedom'), components):
            row = next(r for r in rows if r['component'] == component)
            selection = {'namespace': 'literature_kinetic_summary_precision_cells',
                'sheet_ref': row['sheet_ref'], 'component': component}
            inputs['quantities'][role], _ = _component(selection, lambda *args, row=row: [row])
        inputs['quantities']['assertion_prediction'] = operand(590., 'per_min', 'independent_prediction_A')
        inputs['quantities']['alternative_prediction'] = operand(620., 'per_min', 'independent_prediction_B')
        assert inputs['quantities']['effect']['value'] == 600.
        assert inputs['quantities']['effect_variance']['value'] == 36.
        assert 'estimated_covariance' in inputs['quantities']['effect_variance']['qualifications']
        assert inputs['quantities']['effect_degrees_of_freedom']['value'] == 3
        score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
        assert score['value'] == pytest.approx(student_t.logpdf(10/6, 3) - student_t.logpdf(-20/6, 3))
        assert score['status'] == 'conditional'
    finally:
        store.close()


def test_existing_native_rate_limit_reaches_censored_scoring(tmp_path):
    from test_literature_rate_native_storage import setup_native_store
    from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
    from gene_annotation_episode.literature_assay_grading_inputs import _component
    store, context, args = setup_native_store(tmp_path, reference='<12')
    try:
        repository = LiteratureRateRepository(store, context.run_id).source_projection()
        outcome = repository.populate_native(context, args, 'bounded_reference')
        ref = outcome['result']['sheet_ref']
        row, = repository.project_cells([ref], permitted_record_refs=[ref], components=['reference_rate'])
        observed, _ = _component({'namespace': 'literature_rate_source_cells',
            'sheet_ref': ref, 'component': 'reference_rate'}, lambda *args: [row])
        assert observed['status'] == 'bounded'
        assert observed['bound'] == {'relation': 'lt', 'lower': None, 'upper': .012}
        inputs = fixture('activity_rate', 'rate')
        inputs['quantities']['effect'] = observed
        inputs['quantities']['effect_variance'] = operand(.000004, observed['unit'] + '_squared', 'known_variance')
        inputs['quantities']['assertion_prediction'] = operand(.020, observed['unit'], 'fixed_A')
        inputs['quantities']['alternative_prediction'] = operand(.005, observed['unit'], 'fixed_B')
        score = grade_assay(inputs)['cells']['source_log_evidence_ratio']
        assert score['value'] == pytest.approx(float(log_ndtr(-4) - log_ndtr(3.5)))
        assert 'physical_measurement_identity_unknown' in score['conditions']
    finally:
        store.close()


def test_censored_estimated_score_and_bound_survive_parent_receipt_and_cold_read(tmp_path, monkeypatch):
    from dataclasses import replace
    from test_literature_a105_assay_type_binding_322 import grading_fixture
    from gene_annotation_episode.literature_assay_grading import COMPONENTS
    from gene_annotation_episode.literature_assay_grading_storage import LiteratureAssayGradingRepository
    from gene_annotation_episode.state import Store
    path = tmp_path / 'state'
    with Store(path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, original_artifact = grading_fixture(store)
        primary = args['source_ref']
        declaration = ('Synthetic supplemental readout for Experiment A. '
            'The fixed-prediction estimated-variance normal approximation is explicitly stipulated.')
        raw = declaration + '\nBelow detection: <0.2 fraction.\n'
        artifact = store.artifact(raw, 'text/plain')
        source = store.put('source', {'provider': 'synthetic_censored_assay_324',
            'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact,
            'request_ref': None, 'version': None, 'retrieved_at': None,
            'parent_source_refs': [primary]}, origin='caller')['id']
        support = store.put('reference', {'reference_type': 'assay', 'source_ref': source,
            'accession': 'synthetic_event_model324', 'label': 'Synthetic supplemental readout',
            'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [],
            'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0,
                'end': len(declaration), 'quote': declaration}}, origin='caller')['id']
        token_start = raw.index('0.2')
        unit_start = raw.index('fraction')
        args['quantities']['effect'] = {'kind': 'source_number',
            'number': {'witness': {'source_ref': source, 'representation': 'original',
                'start': token_start, 'end': token_start + 3, 'quote': '0.2'},
                'number_start': 0, 'number_end': 3},
            'unit': {'source_ref': source, 'representation': 'original',
                'start': unit_start, 'end': unit_start + 8, 'quote': 'fraction'}, 'origin': 'synthetic'}
        args['source_ref'] = source
        args['prediction_model'] = {'kind': 'fixed_predictions_estimated_normal',
            'variance_interpretation': 'estimated', 'support_refs': [support]}
        context = replace(context, received_record_refs=[*context.received_record_refs, source, support],
            assignment={**dict(context.assignment), 'source_refs': [primary, source]})
        repository = LiteratureAssayGradingRepository(store, context.run_id)
        outcome = repository.populate(context, args, 'censored-estimated-score')
        ref = outcome['result']['sheet_ref']
        delivered = repository.project_cells([ref], permitted_record_refs=[ref],
            components=['measured_effect', 'effect_variance', 'source_log_evidence_ratio'])
        assert delivered[0]['bound'] == {'relation': 'lt', 'lower': None, 'upper': .2}
        assert delivered[0]['status'] == 'bounded'
        assert delivered[1]['value'] == .04
        assert delivered[2]['value'] == pytest.approx(float(log_ndtr(-4) - log_ndtr(1)))
        assert delivered[0]['experiment_ref'] == args['experiment_ref']
        parent = replace(context, episode_id='parent', role='annotation',
            path=(('annotation', 'parent'),), assignment={},
            received_record_refs=repository.cell_record_refs(delivered))
        repository.receive_cells(parent, delivered, 'trusted_censoring_delivery')
    def forbidden(*args, **kwargs):
        raise AssertionError('saved grading must not repeat scientific reading or scoring')
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.read_assay_grading_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.grade_assay', forbidden)
    with Store(path) as cold:
        raw_reader = cold.get_artifact
        def artifact_reader(reference):
            assert reference not in (original_artifact, artifact)
            return raw_reader(reference)
        monkeypatch.setattr(cold, 'get_artifact', artifact_reader)
        cold.db.execute('PRAGMA query_only=ON')
        changes = cold.db.total_changes
        repository = LiteratureAssayGradingRepository(cold, context.run_id)
        assert repository.fact_cells(parent, [ref], components=list(COMPONENTS)) == delivered
        assert repository.read(ref)['extraction']['quantities']['effect']['bound']['upper'] == .2
        assert cold.db.total_changes == changes
        changed = deepcopy(delivered)
        changed[0]['bound']['upper'] = .3
        with pytest.raises(ContractError, match='differs_from_saved'):
            repository.validate_fact_values(parent, changed)
