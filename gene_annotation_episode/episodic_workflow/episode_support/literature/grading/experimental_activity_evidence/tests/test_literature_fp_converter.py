"""FP converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fp_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, INTENSITY_CHANGE_MAX_PERCENT, INTENSITY_ZERO_AGREEMENT_PERCENT, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR,
    MIN_CONCENTRATIONS, MIN_INCUBATION_MIN, MIN_REPLICATES, MIN_WINDOW_MP, NULL_REASONS, TRACER_MAX_OVER_KD, TRACER_ZERO_AGREEMENT_OVER_KD, WINDOW_ZERO_AGREEMENT_MP, _criterion, convert_fp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_grader import CRITERIA, grade_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import sparse_record, synthetic_record


def test_every_fp_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) <= set(CRITERIA)
    assert set(CRITERIA) - set(mapped) == set()


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_fp(grade_fp(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'fp'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_other_converters_and_nulls_have_reasons():
    converted = convert_fp(grade_fp(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_the_titrant_and_tracer_and_have_no_surface():
    converted = convert_fp(grade_fp(synthetic_record(titrant_prep='ti', tracer_prep='tr', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'ti', 'immobilized_preparation_ref': 'tr', 'surface_ref': None, 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_titrations_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent titrations: variance 36 / 3 = 12
    assert convert_fp(grade_fp(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['facts']['independent_titrations'] = fact('unknown')
    converted = convert_fp(grade_fp(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_a_picomolar_spread_and_kd_are_converted_to_nanomolar():
    r = synthetic_record()
    r['quantities']['kd'] = point(94.0, 'pM', 'kd', ['s'])
    r['quantities']['kd_spread'] = point(10.0, 'pM', 'sp', ['s'])
    cells = convert_fp(grade_fp(r))['sheet']['cells']
    # KD 94 pM = 0.094 nM; standard error 10 pM = 0.01 nM -> variance 1e-4 nM^2
    assert cells['measured_effect']['value'] == pytest.approx(0.094) and cells['effect_variance']['value'] == pytest.approx(1e-4)


def test_a_ki_is_the_effect_when_there_is_no_kd_and_its_own_spread_is_used():
    r = synthetic_record()
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_fp(grade_fp(r))
    cells = converted['sheet']['cells']
    # Ki 40 nM with a standard error of 4 nM -> variance 16 nM^2
    assert cells['measured_effect']['value'] == 40.0 and cells['effect_variance']['value'] == pytest.approx(16.0)
    assert converted['extraction']['quantities']['effect']['measurement_keys'] == ['fp_ki:exp_synthetic_fp_1']


def test_missing_constant_and_confidence_interval_stay_null():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    assert convert_fp(grade_fp(r))['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    for name in ('kd', 'ki'):
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
    converted = convert_fp(grade_fp(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'


def test_sparse_record_fills_only_the_effect():
    converted = convert_fp(grade_fp(sparse_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == 20.0
    assert cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_conflicting_unknown_and_not_applicable_members_combine_by_the_rule():
    r = synthetic_record()
    r['facts']['nonspecific_binding_checked'] = fact('no', ['s'])
    r['facts']['unlabelled_competitor_displaces'] = fact('unknown')
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_controls']['status'] == 'conflicting'
    r = synthetic_record()
    r['facts']['surface_adsorption_prevented'] = fact('not_applicable')     # dropped: the other binding_controls members are supported
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_controls']['status'] == 'supported'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    r['quantities']['ki'] = {**r['quantities']['ki'], 'status': 'unavailable', 'value': None}
    # direct_vs_competition is not_applicable and dropped; the other binding_regime members are supported
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_regime']['status'] == 'supported'
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['quantities']['incubation_time'] = {**r['quantities']['incubation_time'], 'status': 'unavailable', 'value': None}
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_regime']['status'] == 'unknown'
    r = synthetic_record()
    r['quantities']['signal_maximum'] = point(70.0, 'mP', 's', ['s'])            # a window of 20 mP: the zero-agreement limit
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'


def judged(record, name):
    return _criterion(grade_fp(record), name)


def sheet_status_and_degree(record, name):
    verdict = judged(record, name)
    return verdict['status'], verdict.get('degree')


def check_scale(record, name, cases):
    for value_setter, expected, degree in cases:
        value_setter(record)
        status, got = sheet_status_and_degree(record, name)
        assert status == expected, (name, status, expected)
        assert got == (pytest.approx(degree) if degree is not None else None), (name, got, degree)


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_WINDOW_MP, WINDOW_ZERO_AGREEMENT_MP, MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (70.0, 20.0, 8, 0.2, 1.0, 10.0, 1.0)
    assert (TRACER_MAX_OVER_KD, TRACER_ZERO_AGREEMENT_OVER_KD, INTENSITY_CHANGE_MAX_PERCENT, INTENSITY_ZERO_AGREEMENT_PERCENT, MIN_INCUBATION_MIN, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.0, 10.0, 30.0, 100.0, 5.0, 3, 3.0, 10.0)


def test_the_sheet_judges_the_window_with_a_degree():
    r = synthetic_record()                                                                    # minimum 50 mP

    def window(width):
        return lambda record: record['quantities'].update(signal_maximum=point(50.0 + width, 'mP', 's', ['s']))
    check_scale(r, 'assay_window', ((window(200.0), 'supported', 1.0), (window(70.0), 'supported', 1.0), (window(45.0), 'supported', 0.5), (window(21.0), 'supported', 0.02),
                                    (window(20.0), 'conflicting', None), (window(0.0), 'conflicting', None), (window(-10.0), 'conflicting', None)))
    assert judged(r, 'assay_window')['support_refs'] == ['span_exp_synthetic_fp_1', 's']


def test_the_sheet_judges_the_tracer_over_the_kd_with_a_degree_unless_tight_binding_is_handled():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')

    def tracer(nm):
        return lambda record: record['quantities'].update(tracer_concentration=point(nm, 'nM', 't', ['s']))
    check_scale(r, 'tracer_concentration', ((tracer(5.0), 'supported', 1.0), (tracer(20.0), 'supported', 1.0), (tracer(110.0), 'supported', 0.5), (tracer(200.0), 'conflicting', None), (tracer(400.0), 'conflicting', None)))
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])                               # handled: the ratio no longer matters
    check_scale(r, 'tracer_concentration', ((tracer(400.0), 'supported', None),))
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = 'quadratic'
    check_scale(r, 'tracer_concentration', ((tracer(400.0), 'supported', None),))
    # without the two numbers the grader's fact decides, as before
    r['fit_model'] = '1:1'
    r['quantities']['tracer_concentration'] = {**r['quantities']['tracer_concentration'], 'status': 'unavailable', 'value': None}
    r['facts']['tracer_at_or_below_kd'] = fact('no', ['s'])
    assert judged(r, 'tracer_concentration')['status'] == 'conflicting'


def test_the_sheet_judges_the_count_and_the_span_of_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM

    def series(values):
        return lambda record: record['concentration_series'].update(value=values)
    spanning = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 200.0, 400.0]                             # 0.2 x KD to 20 x KD
    mid = [30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    check_scale(r, 'concentration_series', ((series(spanning), 'supported', 1.0), (series([12.0, *mid, 110.0]), 'supported', 0.5),      # lowest 0.6 x KD: 0.5; highest 5.5 x KD: 0.5
                                            (series([12.0, *mid, 400.0]), 'supported', 0.5), (series([4.0, *mid, 110.0]), 'supported', 0.5),
                                            (series([20.0, *mid, 400.0]), 'conflicting', None), (series([4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 20.0]), 'conflicting', None),   # lowest at 1 x KD; highest at 1 x KD
                                            (series(spanning[:7]), 'conflicting', None)))                                                                                      # seven values: fewer than MIN_CONCENTRATIONS
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_fp_1']
    r['concentration_series']['value'] = spanning
    assert judged(r, 'concentration_series')['status'] == 'supported'


def test_the_sheet_judges_the_incubation_without_a_degree():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, expected in ((5.0, 'unknown'), (4.9, 'conflicting'), (0.5, 'conflicting'), (60.0, 'unknown')):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == (expected, None), minutes
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported'                                  # the stated fact is the grader's, whatever the time


def test_the_sheet_judges_the_intensity_change_with_a_degree():
    r = synthetic_record()
    r['facts']['intensity_change_checked'] = fact('unknown')

    def change(percent):
        return lambda record: record['quantities'].update(total_intensity_change=point(percent, 'percent', 'c', ['s']))
    check_scale(r, 'intensity_change', ((change(0.0), 'supported', 1.0), (change(30.0), 'supported', 1.0), (change(65.0), 'supported', 0.5), (change(99.0), 'supported', 1 / 70),
                                        (change(100.0), 'conflicting', None), (change(250.0), 'conflicting', None)))
    r['facts']['intensity_change_checked'] = fact('no', ['s'])
    assert judged(r, 'intensity_change')['status'] == 'conflicting'                           # the fact is the grader's, whatever the number


def test_the_sheet_judges_the_replicate_count_and_its_independence_without_a_degree():
    r = synthetic_record()
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert sheet_status_and_degree(r, 'replicates') == (expected, None), (count, independent)
    r['facts']['independent_titrations'] = fact('no', ['s'])
    assert judged(r, 'replicates')['status'] == 'conflicting'


def test_the_sheet_judges_the_fold_gap_of_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM

    def ki(nm):
        return lambda record: record['quantities'].update(ki=point(nm, 'nM', 'k', ['s']))
    check_scale(r, 'direct_vs_competition', ((ki(40.0), 'supported', 1.0), (ki(60.0), 'supported', 1.0), (ki(130.0), 'supported', 0.5), (ki(10.0), 'supported', 1.0), (ki(200.0), 'conflicting', None), (ki(2.0), 'conflicting', None)))


def test_a_degree_of_a_member_travels_into_its_sheet_criterion_and_the_weakest_member_counts():
    r = synthetic_record()
    r['quantities']['signal_maximum'] = point(95.0, 'mP', 's', ['s'])                         # window 45 mP: 0.5
    r['quantities']['ki'] = point(130.0, 'nM', 'k', ['s'])                                    # fold gap 6.5: 0.5, in another sheet criterion
    interpretations = convert_fp(grade_fp(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability'] == {'status': 'supported', 'support_refs': ['span_exp_synthetic_fp_1', 's'], 'degree': pytest.approx(0.5)}
    assert interpretations['binding_regime']['degree'] == pytest.approx(0.5) and interpretations['binding_controls'].get('degree') is None
    r['quantities']['total_intensity_change'] = point(65.0, 'percent', 'c', ['s'])
    r['facts']['intensity_change_checked'] = fact('unknown')
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.5)
    r['quantities']['ki'] = point(40.0, 'nM', 'k', ['s'])
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(1.0)
    assert convert_fp(grade_fp(r))['sheet']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)      # it travels into the sheet


def interpretation(record, name):
    return convert_fp(grade_fp(record))['extraction']['interpretations'][name]


def test_support_implied_or_about_something_else_gives_the_support_degree_and_direct_leaves_it():
    r = synthetic_record()
    assert 'degree' not in interpretation(r, 'binding_controls')                                      # all direct: unchanged
    r['facts']['free_probe_baseline_measured'] = fact('yes', ['s'], 'implied')
    assert interpretation(r, 'binding_controls') == {'status': 'supported', 'support_refs': interpretation(r, 'binding_controls')['support_refs'], 'degree': pytest.approx(0.7)}
    r['facts']['surface_adsorption_prevented'] = fact('yes', ['s'], 'about_something_else')          # the weakest member field counts
    assert interpretation(r, 'binding_controls')['degree'] == pytest.approx(0.3)
    r = synthetic_record()
    r['quantities']['tracer_concentration'] = point(5.0, 'nM', 't', ['s'], support='about_something_else')
    assert interpretation(r, 'binding_regime')['degree'] == pytest.approx(0.3)


def test_the_support_degree_multiplies_a_degree_the_criterion_already_has():
    r = synthetic_record()
    r['quantities']['signal_maximum'] = point(95.0, 'mP', 's', ['s'])                                 # window 45 mP: degree 0.5
    r['quantities']['signal_minimum'] = point(50.0, 'mP', 's', ['s'], support='implied')
    assert interpretation(r, 'calibration_applicability')['degree'] == pytest.approx(0.5 * 0.7)


def test_support_never_changes_a_status_and_a_conflicting_or_unknown_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['free_probe_baseline_measured'] = fact('no', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_controls')
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    r = synthetic_record()
    r['facts']['free_probe_baseline_measured'] = fact('unknown')
    r['facts']['nonspecific_binding_checked'] = fact('yes', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_controls')
    assert verdict['status'] == 'unknown' and 'degree' not in verdict
