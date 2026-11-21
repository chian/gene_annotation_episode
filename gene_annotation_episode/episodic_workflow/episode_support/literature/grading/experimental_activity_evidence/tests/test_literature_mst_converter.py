"""MST converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, FHOT_ZERO_AGREEMENT_S, FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LABELLED_MAX_OVER_KD, LABELLED_ZERO_AGREEMENT_OVER_KD,
    LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MIN_CONCENTRATIONS, MIN_FHOT_S, MIN_FNORM_AMPLITUDE_PERMILLE, MIN_INCUBATION_MIN, MIN_REPLICATES, MIN_SIGNAL_TO_NOISE, NULL_REASONS, SIGNAL_TO_NOISE_ZERO_AGREEMENT, _criterion, convert_mst)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_grader import CRITERIA, grade_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import sparse_record, synthetic_record


def test_every_mst_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) <= set(CRITERIA)
    assert set(CRITERIA) - set(mapped) == set()


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_mst(grade_mst(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'mst'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_other_converters_and_nulls_have_reasons():
    converted = convert_mst(grade_mst(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_the_titrant_and_the_fixed_partner_and_have_no_surface():
    converted = convert_mst(grade_mst(synthetic_record(titrant_prep='ti', fixed_prep='fi', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'ti', 'immobilized_preparation_ref': 'fi', 'surface_ref': None, 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_titrations_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent titrations: variance 36 / 3 = 12
    assert convert_mst(grade_mst(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['facts']['independent_titrations'] = fact('unknown')
    converted = convert_mst(grade_mst(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_a_confidence_interval_is_not_converted_and_an_unstated_kind_gives_no_variance():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    converted = convert_mst(grade_mst(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None and converted['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['spread_kind'] = None
    assert convert_mst(grade_mst(r))['null_components']['effect_variance'] == 'spread_kind_not_stated'


def test_a_picomolar_spread_and_kd_are_converted_to_nanomolar():
    r = synthetic_record()
    r['quantities']['kd'] = point(94.0, 'pM', 'kd', ['s'])
    r['quantities']['kd_spread'] = point(10.0, 'pM', 'sp', ['s'])
    cells = convert_mst(grade_mst(r))['sheet']['cells']
    # KD 94 pM = 0.094 nM; standard error 10 pM = 0.01 nM -> variance 1e-4 nM^2
    assert cells['measured_effect']['value'] == pytest.approx(0.094) and cells['effect_variance']['value'] == pytest.approx(1e-4)


def test_a_ki_is_the_effect_when_there_is_no_kd_with_the_ki_spread():
    r = synthetic_record()
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_mst(grade_mst(r))
    cells = converted['sheet']['cells']
    # Ki 40 nM with standard error 4 nM -> variance 16 nM^2
    assert cells['measured_effect']['value'] == 40.0 and cells['effect_variance']['value'] == pytest.approx(16.0)
    assert converted['extraction']['quantities']['effect']['measurement_keys'] == ['mst_ki:' + r['experiment_ref']]


def test_an_ec50_alone_is_not_a_binding_constant():
    r = synthetic_record()
    for name in ('kd', 'ki'):
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
    converted = convert_mst(grade_mst(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'only_a_half_maximal_concentration_given_not_a_binding_constant'
    assert converted['null_components']['effect_variance'] == 'no_effect_to_carry_a_variance'      # the spreads belong to the KD and the Ki, which are not given
    r['quantities']['ec50'] = {**r['quantities']['ec50'], 'status': 'unavailable', 'value': None}
    assert convert_mst(grade_mst(r))['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'


def test_the_sparse_record_has_an_effect_and_no_variance_and_unknown_criteria():
    converted = convert_mst(grade_mst(sparse_record()))
    assert converted['sheet']['cells']['measured_effect']['value'] == 20.0 and converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_a_readout_that_does_not_apply_is_dropped_from_its_sheet_criterion():
    r = synthetic_record()
    r['readout_signal'] = 'initial_fluorescence'
    r['fit_model'] = 'competitive_binding'            # the fit model clashes with the direct titration: the sheet criterion conflicts
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['binding_parameter_definition']['status'] == 'conflicting'
    r['fit_model'] = '1:1'
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['binding_parameter_definition']['status'] == 'supported'
    r['quantities']['signal_to_noise'] = point(1.0, 'ratio', 's', ['s'])        # the sheet's calibration criterion is the signal: at the noise
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'


def judged(record, name):
    return _criterion(grade_mst(record), name)


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
    assert (MIN_SIGNAL_TO_NOISE, SIGNAL_TO_NOISE_ZERO_AGREEMENT, MIN_FNORM_AMPLITUDE_PERMILLE, FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE, MIN_FHOT_S, FHOT_ZERO_AGREEMENT_S) == (5.0, 1.0, 5.0, 1.0, 1.0, 0.0)
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (10, 0.2, 1.0, 10.0, 1.0)
    assert (LABELLED_MAX_OVER_KD, LABELLED_ZERO_AGREEMENT_OVER_KD, MIN_INCUBATION_MIN, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.0, 10.0, 10.0, 3, 3.0, 10.0)


def test_the_sheet_judges_the_signal_to_noise_and_the_fnorm_change_with_a_degree():
    r = synthetic_record()

    def signal(noise, amplitude):
        def put(record):
            for name, value, unit in (('signal_to_noise', noise, 'ratio'), ('fnorm_amplitude', amplitude, 'permille')):
                record['quantities'][name] = point(value, unit, name, ['s']) if value is not None else {**record['quantities'][name], 'status': 'unavailable', 'value': None}
        return put
    check_scale(r, 'signal_amplitude', ((signal(18.0, 12.0), 'supported', 1.0), (signal(5.0, 5.0), 'supported', 1.0), (signal(3.0, 12.0), 'supported', 0.5), (signal(18.0, 3.0), 'supported', 0.5),
                                        (signal(3.0, 2.0), 'supported', 0.25), (signal(1.0, 12.0), 'conflicting', None), (signal(18.0, 1.0), 'conflicting', None), (signal(18.0, 0.5), 'conflicting', None),
                                        (signal(None, 3.0), 'supported', 0.5), (signal(3.0, None), 'supported', 0.5)))             # one given number is judged alone
    assert 's' in judged(r, 'signal_amplitude')['support_refs']


def test_the_sheet_judges_the_fhot_time_with_a_degree():
    r = synthetic_record()

    def fhot(seconds):
        return lambda record: record['quantities'].update(fhot_time=point(seconds, 's', 'f', ['s']))
    check_scale(r, 'readout_window', ((fhot(1.5), 'supported', 1.0), (fhot(1.0), 'supported', 1.0), (fhot(0.5), 'supported', 0.5), (fhot(0.0), 'conflicting', None), (fhot(-0.5), 'conflicting', None)))
    r['readout_signal'] = 't_jump'
    assert sheet_status_and_degree(r, 'readout_window') == ('unknown', None)               # a temperature-jump readout stated has no F-hot time to judge, and holds no span to support a decision


def test_the_sheet_judges_the_labelled_over_the_kd_with_a_degree_unless_tight_binding_is_handled():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')

    def labelled(nm):
        return lambda record: record['quantities'].update(labelled_concentration=point(nm, 'nM', 't', ['s']))
    check_scale(r, 'labelled_concentration', ((labelled(5.0), 'supported', 1.0), (labelled(20.0), 'supported', 1.0), (labelled(110.0), 'supported', 0.5), (labelled(200.0), 'conflicting', None), (labelled(400.0), 'conflicting', None)))
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])                               # handled: the ratio no longer matters
    check_scale(r, 'labelled_concentration', ((labelled(400.0), 'supported', None),))
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = 'quadratic'
    check_scale(r, 'labelled_concentration', ((labelled(400.0), 'supported', None),))
    r['fit_model'] = '1:1'
    r['quantities']['labelled_concentration'] = {**r['quantities']['labelled_concentration'], 'status': 'unavailable', 'value': None}      # without a number the grader's fact decides, as before
    r['facts']['labelled_partner_at_or_below_kd'] = fact('no', ['s'])
    assert judged(r, 'labelled_concentration')['status'] == 'conflicting'


def test_the_sheet_judges_the_count_and_the_span_of_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM

    def series(values):
        return lambda record: record['concentration_series'].update(value=values)
    spanning = [4.0, 8.0, 16.0, 32.0, 64.0, 100.0, 150.0, 180.0, 190.0, 400.0]               # ten values, 0.2 x KD to 20 x KD
    mid = [30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0]
    check_scale(r, 'concentration_series', ((series(spanning), 'supported', 1.0), (series([12.0, *mid, 110.0]), 'supported', 0.5),      # lowest 0.6 x KD: 0.5; highest 5.5 x KD: 0.5
                                            (series([12.0, *mid, 400.0]), 'supported', 0.5), (series([4.0, *mid, 110.0]), 'supported', 0.5),
                                            (series([20.0, *mid, 400.0]), 'conflicting', None), (series([4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0]), 'conflicting', None),             # lowest at 1 x KD; highest at 1 x KD
                                            (series(spanning[:9]), 'conflicting', None)))                                                                      # nine values: fewer than MIN_CONCENTRATIONS
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_mst_1']
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}      # a count without a list: below the minimum conflicts, otherwise the span is not known
    for count, expected in ((9, 'conflicting'), (10, 'unknown'), (12, 'unknown')):
        r['quantities']['titration_point_count'] = point(count, 'count', 'n', ['s'])
        assert sheet_status_and_degree(r, 'concentration_series') == (expected, None), count
    assert judged(r, 'concentration_series')['support_refs'] == []


def test_the_sheet_judges_the_incubation_without_a_degree():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, expected in ((10.0, 'unknown'), (9.9, 'conflicting'), (1.0, 'conflicting'), (120.0, 'unknown')):
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
    r['quantities']['signal_to_noise'] = point(3.0, 'ratio', 's', ['s'])                      # 0.5, in calibration_applicability
    r['quantities']['ki'] = point(130.0, 'nM', 'k', ['s'])                                    # fold gap 6.5: 0.5, in binding_regime
    interpretations = convert_mst(grade_mst(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['degree'] == pytest.approx(0.5)
    assert interpretations['binding_regime']['degree'] == pytest.approx(0.5) and interpretations['binding_controls'].get('degree') is None
    r['quantities']['fhot_time'] = point(0.75, 's', 'f', ['s'])                               # 0.75, in binding_parameter_definition
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.75)
    r['quantities']['fnorm_amplitude'] = point(2.0, 'permille', 'a', ['s'])                   # 0.25: the weakest of the two numbers
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.25)
    r['quantities']['ki'] = point(40.0, 'nM', 'k', ['s'])
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(1.0)
    assert convert_mst(grade_mst(r))['sheet']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.25)      # it travels into the sheet


def interpretation(record, name):
    return convert_mst(grade_mst(record))['extraction']['interpretations'][name]


def test_support_implied_or_about_something_else_gives_the_support_degree_and_direct_leaves_it():
    r = synthetic_record()
    assert interpretation(r, 'binding_parameter_definition').get('degree', 1.0) == 1.0 and interpretation(r, 'binding_controls').get('degree', 1.0) == 1.0      # all direct: unchanged
    r['facts']['labelling_does_not_alter_binding'] = fact('yes', ['s'], 'implied')
    assert interpretation(r, 'binding_parameter_definition')['degree'] == pytest.approx(0.7)
    r['facts']['aggregation_or_adsorption_checked'] = fact('yes', ['s'], 'about_something_else')
    assert interpretation(r, 'binding_controls')['degree'] == pytest.approx(0.3)


def test_the_support_degree_multiplies_a_degree_the_criterion_already_has():
    r = synthetic_record()
    r['quantities']['signal_to_noise'] = point(3.0, 'ratio', 's', ['s'], support='implied')        # degree 0.5
    assert interpretation(r, 'calibration_applicability')['degree'] == pytest.approx(0.5 * 0.7)


def test_support_never_changes_a_status_and_a_conflicting_or_unknown_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['aggregation_or_adsorption_checked'] = fact('no', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_controls')
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    r = synthetic_record()
    r['facts']['aggregation_or_adsorption_checked'] = fact('unknown')
    r['facts']['nonspecific_binding_checked'] = fact('yes', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_controls')
    assert verdict['status'] == 'unknown' and 'degree' not in verdict
