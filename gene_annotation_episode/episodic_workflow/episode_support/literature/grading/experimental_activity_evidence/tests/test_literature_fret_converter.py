"""FRET converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, DELAY_ZERO_AGREEMENT_US, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, INTEGRATION_ZERO_AGREEMENT_US, LABELLED_MAX_OVER_KD, LABELLED_ZERO_AGREEMENT_OVER_KD, LOW_FACTOR,
    LOW_ZERO_AGREEMENT_FACTOR, MIN_CONCENTRATIONS, MIN_DELAY_US, MIN_INCUBATION_MIN, MIN_INTEGRATION_US, MIN_REPLICATES, MIN_WINDOW_FOLD, NULL_REASONS, WINDOW_ZERO_AGREEMENT_FOLD, _criterion, convert_fret)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_grader import CRITERIA, grade_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import sparse_record, synthetic_record


def test_every_fret_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) <= set(CRITERIA)
    assert set(CRITERIA) - set(mapped) == set()


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_fret(grade_fret(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'fret'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_other_converters_and_nulls_have_reasons():
    converted = convert_fret(grade_fret(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_the_titrant_and_the_fixed_partner_and_have_no_surface():
    converted = convert_fret(grade_fret(synthetic_record(titrant_prep='ti', fixed_prep='fi', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'ti', 'immobilized_preparation_ref': 'fi', 'surface_ref': None, 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_titrations_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent titrations: variance 36 / 3 = 12
    assert convert_fret(grade_fret(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['facts']['independent_titrations'] = fact('unknown')
    converted = convert_fret(grade_fret(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_a_confidence_interval_is_not_converted():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    converted = convert_fret(grade_fret(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None and converted['null_components']['effect_variance'] == 'confidence_interval_not_converted'


def test_a_picomolar_spread_and_kd_are_converted_to_nanomolar():
    r = synthetic_record()
    r['quantities']['kd'] = point(94.0, 'pM', 'kd', ['s'])
    r['quantities']['kd_spread'] = point(10.0, 'pM', 'sp', ['s'])
    cells = convert_fret(grade_fret(r))['sheet']['cells']
    # KD 94 pM = 0.094 nM; standard error 10 pM = 0.01 nM -> variance 1e-4 nM^2
    assert cells['measured_effect']['value'] == pytest.approx(0.094) and cells['effect_variance']['value'] == pytest.approx(1e-4)


def test_a_ki_is_the_effect_when_there_is_no_kd_with_the_ki_spread():
    r = synthetic_record()
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_fret(grade_fret(r))
    cells = converted['sheet']['cells']
    # Ki 40 nM with standard error 4 nM -> variance 16 nM^2
    assert cells['measured_effect']['value'] == 40.0 and cells['effect_variance']['value'] == pytest.approx(16.0)
    assert converted['extraction']['quantities']['effect']['measurement_keys'] == ['fret_ki:' + r['experiment_ref']]


def test_an_ec50_or_an_ic50_alone_is_not_a_binding_constant():
    r = synthetic_record()
    for name in ('kd', 'ki'):
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
    converted = convert_fret(grade_fret(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'only_a_half_maximal_concentration_given_not_a_binding_constant'
    assert converted['null_components']['effect_variance'] == 'no_effect_to_carry_a_variance'      # the spreads belong to the KD and the Ki, which are not given
    for name in ('ec50', 'ic50'):
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
    assert convert_fret(grade_fret(r))['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'


def test_the_sparse_record_has_an_effect_and_no_variance_and_unknown_criteria():
    converted = convert_fret(grade_fret(sparse_record()))
    assert converted['sheet']['cells']['measured_effect']['value'] == 20.0 and converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_a_gating_that_does_not_apply_is_dropped_from_its_sheet_criterion():
    r = synthetic_record()
    r['facts']['time_resolved_read'] = fact('no', ['s'])
    r['quantities']['ratio_maximum'] = point(0.4, 'ratio', 's', ['s'])        # fold 1.0: no window, the window conflicts
    interpretations = convert_fret(grade_fret(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'conflicting'
    r['quantities']['ratio_maximum'] = point(1.6, 'ratio', 's', ['s'])
    assert convert_fret(grade_fret(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'supported'


def judged(record, name):
    return _criterion(grade_fret(record), name)


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
    assert (MIN_WINDOW_FOLD, WINDOW_ZERO_AGREEMENT_FOLD, MIN_DELAY_US, DELAY_ZERO_AGREEMENT_US, MIN_INTEGRATION_US, INTEGRATION_ZERO_AGREEMENT_US) == (2.0, 1.0, 50.0, 5.0, 100.0, 10.0)
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (8, 0.2, 1.0, 10.0, 1.0)
    assert (LABELLED_MAX_OVER_KD, LABELLED_ZERO_AGREEMENT_OVER_KD, MIN_INCUBATION_MIN, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.0, 10.0, 15.0, 3, 3.0, 10.0)


def test_the_sheet_judges_the_window_fold_with_a_degree():
    r = synthetic_record()                                                                    # minimum ratio 0.4

    def top(value):
        return lambda record: record['quantities'].update(ratio_maximum=point(value, 'ratio', 's', ['s']))
    check_scale(r, 'assay_window', ((top(1.6), 'supported', 1.0), (top(0.8), 'supported', 1.0), (top(0.6), 'supported', 0.5), (top(0.4), 'conflicting', None), (top(0.2), 'conflicting', None)))
    assert judged(r, 'assay_window')['support_refs'] == ['span_exp_synthetic_fret_1', 's']


def test_the_sheet_judges_the_gating_delay_and_window_with_a_degree():
    r = synthetic_record()                                                                    # delay 100 us, window 400 us

    def gate(delay, window):
        return lambda record: record['quantities'].update(delay_time=point(delay, 'us', 'd', ['s']), integration_time=point(window, 'us', 'w', ['s']))
    check_scale(r, 'time_gating', ((gate(100.0, 400.0), 'supported', 1.0), (gate(50.0, 100.0), 'supported', 1.0), (gate(27.5, 400.0), 'supported', 0.5), (gate(100.0, 55.0), 'supported', 0.5),
                                   (gate(27.5, 55.0), 'supported', 0.5), (gate(5.0, 400.0), 'conflicting', None), (gate(100.0, 10.0), 'conflicting', None), (gate(0.0, 400.0), 'conflicting', None)))
    missing = {**r['quantities']['integration_time'], 'status': 'unavailable', 'value': None}
    r['quantities']['delay_time'] = point(27.5, 'us', 'd', ['s'])
    r['quantities']['integration_time'] = missing
    assert sheet_status_and_degree(r, 'time_gating') == ('supported', pytest.approx(0.5))      # no window given: the delay decides
    r['donor_acceptor_pair'] = 'organic_dye_pair'
    assert sheet_status_and_degree(r, 'time_gating') == ('conflicting', None)                  # a short-lived donor is the grader's own fact-based conflict


def test_the_sheet_judges_the_labelled_over_the_kd_with_a_degree_unless_tight_binding_is_handled():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['quantities']['acceptor_concentration'] = {**r['quantities']['acceptor_concentration'], 'status': 'unavailable', 'value': None}

    def donor(nm):
        return lambda record: record['quantities'].update(donor_concentration=point(nm, 'nM', 't', ['s']))
    check_scale(r, 'labelled_concentration', ((donor(5.0), 'supported', 1.0), (donor(20.0), 'supported', 1.0), (donor(110.0), 'supported', 0.5), (donor(200.0), 'conflicting', None), (donor(400.0), 'conflicting', None)))
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])                               # handled: the ratio no longer matters
    check_scale(r, 'labelled_concentration', ((donor(400.0), 'supported', None),))
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = 'quadratic'
    check_scale(r, 'labelled_concentration', ((donor(400.0), 'supported', None),))
    r['fit_model'] = '1:1'
    r['quantities']['donor_concentration'] = {**r['quantities']['donor_concentration'], 'status': 'unavailable', 'value': None}      # without a number the grader's fact decides, as before
    r['facts']['labelled_partner_at_or_below_kd'] = fact('no', ['s'])
    assert judged(r, 'labelled_concentration')['status'] == 'conflicting'


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
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_fret_1']


def test_the_sheet_judges_the_incubation_without_a_degree():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, expected in ((15.0, 'unknown'), (14.9, 'conflicting'), (1.0, 'conflicting'), (120.0, 'unknown')):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == (expected, None), minutes
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported'                                  # the stated fact is the grader's, whatever the time


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
    r['quantities']['ratio_maximum'] = point(0.6, 'ratio', 's', ['s'])                        # fold 1.5: 0.5, with time_gating at 1.0 in the same sheet criterion
    r['quantities']['ki'] = point(130.0, 'nM', 'k', ['s'])                                    # fold gap 6.5: 0.5, in another sheet criterion
    interpretations = convert_fret(grade_fret(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability'] == {'status': 'supported', 'support_refs': interpretations['calibration_applicability']['support_refs'], 'degree': pytest.approx(0.5)}
    assert interpretations['calibration_applicability']['support_refs'] and interpretations['binding_regime']['degree'] == pytest.approx(0.5) and interpretations['binding_controls'].get('degree') is None
    r['quantities']['delay_time'] = point(27.5, 'us', 'd', ['s'])                             # 0.5, the same as the window: the weakest counts
    r['quantities']['ratio_maximum'] = point(1.6, 'ratio', 's', ['s'])
    assert convert_fret(grade_fret(r))['extraction']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)
    r['quantities']['ki'] = point(40.0, 'nM', 'k', ['s'])
    assert convert_fret(grade_fret(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(1.0)
    assert convert_fret(grade_fret(r))['sheet']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)      # it travels into the sheet


def interpretation(record, name):
    return convert_fret(grade_fret(record))['extraction']['interpretations'][name]


def test_support_implied_or_about_something_else_gives_the_support_degree_and_direct_leaves_it():
    r = synthetic_record()
    assert 'degree' not in interpretation(r, 'binding_parameter_definition') and 'degree' not in interpretation(r, 'binding_controls')      # all direct: unchanged
    r['facts']['ratiometric_readout_used'] = fact('yes', ['s'], 'implied')
    assert interpretation(r, 'binding_parameter_definition')['degree'] == pytest.approx(0.7)
    r['facts']['labelling_does_not_alter_binding'] = fact('yes', ['s'], 'about_something_else')      # the weakest member field counts
    assert interpretation(r, 'binding_parameter_definition')['degree'] == pytest.approx(0.3)
    r['facts']['crosstalk_corrected'] = fact('yes', ['s'], 'implied')
    assert interpretation(r, 'binding_controls')['degree'] == pytest.approx(0.7)


def test_the_support_degree_multiplies_a_degree_the_criterion_already_has():
    r = synthetic_record()
    r['quantities']['ratio_maximum'] = point(0.6, 'ratio', 's', ['s'], support='implied')        # fold 1.5: degree 0.5
    assert interpretation(r, 'calibration_applicability')['degree'] == pytest.approx(0.5 * 0.7)


def test_support_never_changes_a_status_and_a_conflicting_or_unknown_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['crosstalk_corrected'] = fact('no', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_controls')
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    r = synthetic_record()
    r['facts']['ratiometric_readout_used'] = fact('unknown')
    r['facts']['labelling_does_not_alter_binding'] = fact('yes', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_parameter_definition')
    assert verdict['status'] == 'unknown' and 'degree' not in verdict
