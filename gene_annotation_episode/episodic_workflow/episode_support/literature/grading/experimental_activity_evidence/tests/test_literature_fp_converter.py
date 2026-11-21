"""FP converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fp_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, FIT_PARAMETERS, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, INTENSITY_CHANGE_MAX_PERCENT, INTENSITY_ZERO_AGREEMENT_PERCENT, LOW_FACTOR,
    LOW_ZERO_AGREEMENT_FACTOR, MIN_CONCENTRATIONS, MIN_INCUBATION_MIN, MIN_REPLICATES, MIN_WINDOW_MP, NULL_REASONS, TRACER_MAX_OVER_KD, TRACER_ZERO_AGREEMENT_OVER_KD, WINDOW_ZERO_AGREEMENT_MP,
    EQUILIBRATION_HALF_LIVES, FAST_KON_PER_M_PER_S, SLOW_KON_PER_M_PER_S, WINDOW_OVER_NOISE_FULL, WINDOW_OVER_NOISE_ZERO, TRACER_BOUND_AT_MIDPOINT, _criterion, convert_fp)
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
    assert (MIN_WINDOW_MP, WINDOW_ZERO_AGREEMENT_MP, MIN_CONCENTRATIONS, FIT_PARAMETERS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (70.0, 20.0, 8, 3, 0.2, 1.0, 10.0, 1.0)
    assert (TRACER_MAX_OVER_KD, TRACER_ZERO_AGREEMENT_OVER_KD, INTENSITY_CHANGE_MAX_PERCENT, INTENSITY_ZERO_AGREEMENT_PERCENT, MIN_INCUBATION_MIN, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.0, 10.0, 30.0, 100.0, 5.0, 3, 3.0, 10.0)
    assert (TRACER_BOUND_AT_MIDPOINT, EQUILIBRATION_HALF_LIVES, FAST_KON_PER_M_PER_S) == (0.5, 5.0, 1.0e7)


def test_the_sheet_judges_the_window_with_a_degree():
    r = synthetic_record()                                                                    # minimum 50 mP

    def window(width):
        return lambda record: record['quantities'].update(signal_maximum=point(50.0 + width, 'mP', 's', ['s']))
    # linear in 1 / window: 45 mP -> (1/20 - 1/45) / (1/20 - 1/70) = 7/9; 25 mP -> 0.28; 21 mP -> 1/15
    check_scale(r, 'assay_window', ((window(200.0), 'supported', 1.0), (window(70.0), 'supported', 1.0), (window(45.0), 'supported', 7 / 9), (window(25.0), 'supported', 0.28), (window(21.0), 'supported', 1 / 15),
                                    (window(20.0), 'conflicting', None), (window(0.0), 'conflicting', None), (window(-10.0), 'conflicting', None)))
    assert judged(r, 'assay_window')['support_refs'] == ['span_exp_synthetic_fp_1', 's']


def test_the_sheet_judges_the_tracer_over_the_kd_with_a_degree_unless_tight_binding_is_handled():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')

    def tracer(nm):
        return lambda record: record['quantities'].update(tracer_concentration=point(nm, 'nM', 't', ['s']))
    # linear in the log of the depletion bias 1 + tracer / (2 KD): full at 1.5-fold (tracer = KD), none at 6-fold (10 x KD);
    # 80 nM (4 x KD): bias 3, the geometric middle -> 0.5; 40 nM (2 x KD): bias 2 -> 1 - log(2 / 1.5) / log(4)
    check_scale(r, 'tracer_concentration', ((tracer(5.0), 'supported', 1.0), (tracer(20.0), 'supported', 1.0), (tracer(40.0), 'supported', 1 - math.log(2 / 1.5) / math.log(4)),
                                            (tracer(80.0), 'supported', 0.5), (tracer(200.0), 'conflicting', None), (tracer(400.0), 'conflicting', None)))
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
    # the ends are linear in the occupancy x / (1 + x): lowest 0.5 x KD (1/3 occupied, halfway from 1/6 to 1/2) -> 0.5;
    # highest 3 x KD (3/4 occupied, from 1/2 to 10/11) -> 11/18; highest 5.5 x KD -> 11/13
    check_scale(r, 'concentration_series', ((series(spanning), 'supported', 1.0), (series([10.0, 12.0, 14.0, 16.0, 18.0, 22.0, 30.0, 400.0]), 'supported', 0.5),
                                            (series([4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 60.0]), 'supported', 11 / 18), (series([4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 110.0]), 'supported', 11 / 13),
                                            (series([10.0, 12.0, 14.0, 16.0, 18.0, 22.0, 30.0, 60.0]), 'supported', 0.5),      # the weakest end counts
                                            (series([20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 400.0]), 'conflicting', None), (series([4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 20.0]), 'conflicting', None),   # lowest at 1 x KD; highest at 1 x KD
                                            (series(spanning[:7]), 'supported', 0.8)))      # seven values, one below MIN_CONCENTRATIONS: (7 - 3) / (8 - 3), partial credit, not a fail
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_fp_1']
    r['concentration_series']['value'] = spanning
    assert judged(r, 'concentration_series')['status'] == 'supported'


def a_spanning_series(count):
    """count concentrations spread evenly on the log scale from 0.1 x KD to 100 x KD (KD 20 nM), so only the count limits the degree."""
    return [2.0 * 1000.0 ** (i / (count - 1)) for i in range(count)]


def test_the_concentration_count_is_gradual_around_min_concentrations_monotone_and_bounded():
    r = synthetic_record()
    degrees = []
    for count in range(2, 16):
        r['concentration_series']['value'] = a_spanning_series(count)
        status, degree = sheet_status_and_degree(r, 'concentration_series')
        degrees.append(degree)
        assert status == 'supported', count                                                     # a short count is never conflicting; at or below the fitted parameters it gets no credit
        expected = min(1.0, (count - FIT_PARAMETERS) / (MIN_CONCENTRATIONS - FIT_PARAMETERS)) if count > FIT_PARAMETERS else 0.0
        assert degrees[-1] == pytest.approx(expected) and 0.0 <= degrees[-1] <= 1.0, count
    assert degrees == sorted(degrees)                                                         # more concentrations never lower the degree
    r['concentration_series']['value'] = a_spanning_series(MIN_CONCENTRATIONS - 1)
    just_below = judged(r, 'concentration_series')
    assert just_below['status'] == 'supported' and 0.5 < just_below['degree'] < 1.0         # no step: one below the researched count keeps most of the credit
    r['concentration_series']['value'] = a_spanning_series(MIN_CONCENTRATIONS)
    assert judged(r, 'concentration_series')['degree'] == pytest.approx(1.0)                # full credit at the researched count
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert judged(r, 'concentration_series')['status'] == 'unknown'                         # not stated: unknown, not 0


def test_the_sheet_judges_the_incubation_as_a_curve():
    # KD 20 nM: koff at the fast kon 1e7 x 2e-8 = 0.2 per s, T_FAST = 5 ln 2 / 0.2 s = 0.2888 min; at the slow kon 1e5 T_SLOW = 28.88 min (100 x T_FAST)
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    # (minutes, status, degree): 0.2 is below T_FAST (conflicting); 0.5 and 1 are held by the floor t / 5 (0.1, 0.2) since log(t / T_FAST) / ln 100 is 0.119 and 0.270;
    # 4 min: floor 0.8, log(4 / 0.2888) / ln 100 = 0.571; 10 min: 0.770; 30 min is past T_SLOW (full)
    for minutes, expected, degree in ((0.2, 'conflicting', None), (0.5, 'supported', 0.1), (1.0, 'supported', 0.2), (4.0, 'supported', 0.571), (10.0, 'supported', 0.770), (30.0, 'supported', 1.0), (60.0, 'supported', 1.0)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        got_status, got_degree = sheet_status_and_degree(r, 'equilibrium')
        assert got_status == expected and (got_degree is None if degree is None else got_degree == pytest.approx(degree, abs=2e-3)), minutes
    assert SLOW_KON_PER_M_PER_S == 1.0e5
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported'                                  # the stated fact is the grader's, whatever the time


def test_no_constant_means_unknown_even_below_the_floor():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    r['quantities']['ki'] = {**r['quantities']['ki'], 'status': 'unavailable', 'value': None}
    for minutes in (0.5, 4.0, 60.0):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == ('unknown', None), minutes


def test_the_two_ends_for_a_weak_and_a_tight_binder():
    # KD 1000 nM (micromolar): T_FAST 0.005776 min, T_SLOW 0.5776 min: 5 min is full, 1 min is held by the floor (0.2)
    r = synthetic_record(kd=1000.0)
    r['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, degree in ((5.0, 1.0), (1.0, 0.2)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == ('supported', pytest.approx(degree)), minutes
    # KD 0.01 nM (picomolar): T_FAST 577.6 min, T_SLOW 57762 min: 1 h conflicting, 24 h log(1440 / 577.6) / ln 100 = 0.198, 10 days 0.698
    r = synthetic_record(kd=0.01)
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['quantities']['incubation_time'] = point(60.0, 'min', 'i', ['s'])
    assert sheet_status_and_degree(r, 'equilibrium') == ('conflicting', None)
    for minutes, degree in ((1440.0, 0.198), (14400.0, 0.698), (57762.0, 1.0)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        got_status, got_degree = sheet_status_and_degree(r, 'equilibrium')
        assert got_status == 'supported' and got_degree == pytest.approx(degree, abs=2e-3), minutes


def test_a_tight_binder_needs_the_incubation_its_own_constant_sets():
    # KD 0.1 nM: koff at the fast kon is 1e7 x 1e-10 = 1e-3 per s; five half-lives are 5 x ln 2 / 1e-3 s = 57.8 min (T_FAST); T_SLOW = 5776 min
    r = synthetic_record(kd=0.1)
    r['facts']['equilibrium_reached'] = fact('unknown')
    needed = EQUILIBRATION_HALF_LIVES * math.log(2) / (FAST_KON_PER_M_PER_S * 0.1e-9) / 60
    assert needed == pytest.approx(57.76, abs=0.01)
    # 58 min is just past T_FAST: log(58 / 57.76) / ln 100 = 0.0009 (no step); 120 min 0.159; 1000 min 0.619
    for minutes, expected, degree in ((30.0, 'conflicting', None), (57.0, 'conflicting', None), (58.0, 'supported', 0.0009), (120.0, 'supported', 0.159), (1000.0, 'supported', 0.619)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        got_status, got_degree = sheet_status_and_degree(r, 'equilibrium')
        assert got_status == expected and (got_degree is None if degree is None else got_degree == pytest.approx(degree, abs=5e-4)), minutes
    r['quantities']['incubation_time'] = point(30.0, 'min', 'i', ['s'])
    assert judged(r, 'equilibrium')['support_refs'] == ['s', 'span_exp_synthetic_fp_1']      # the constant set the scale, so its quote is cited too
    # KD 2 nM: T_FAST 2.888 min; 4.9 min: floor 0.98, log(4.9 / 2.888) / ln 100 = 0.115
    r = synthetic_record(kd=2.0)
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['quantities']['incubation_time'] = point(4.9, 'min', 'i', ['s'])
    got = judged(r, 'equilibrium')
    assert got['status'] == 'supported' and got['degree'] == pytest.approx(0.115, abs=2e-3) and got['support_refs'] == ['s', 'span_exp_synthetic_fp_1']
    # monotone: a tighter constant never raises the degree, a longer incubation never lowers it (conflicting counts as 0)
    def degree_of(kd, minutes):
        r = synthetic_record(kd=kd)
        r['facts']['equilibrium_reached'] = fact('unknown')
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        got = judged(r, 'equilibrium')
        return got['degree'] if got['status'] == 'supported' else 0.0
    for minutes in (10.0, 30.0, 90.0):
        degrees = [degree_of(kd, minutes) for kd in (100.0, 10.0, 1.0, 0.3, 0.1, 0.03)]
        assert degrees == sorted(degrees, reverse=True) and all(0.0 <= d <= 1.0 for d in degrees), (minutes, degrees)
    for kd in (100.0, 1.0, 0.1):
        degrees = [degree_of(kd, minutes) for minutes in (0.1, 0.5, 2.0, 10.0, 60.0, 600.0, 6000.0)]
        assert degrees == sorted(degrees), (kd, degrees)


def sweep(record, name, setter, values):
    """Degrees (0 for conflicting) of criterion name as setter(record, value) runs through values."""
    degrees = []
    for value in values:
        setter(record, value)
        verdict = judged(record, name)
        assert verdict['status'] in ('supported', 'conflicting'), (name, value)
        degree = verdict['degree'] if verdict['status'] == 'supported' else 0.0
        assert 0.0 <= degree <= 1.0, (name, value)
        degrees.append(degree)
    return degrees


def test_every_reshaped_curve_is_monotone_bounded_and_has_no_step_at_its_researched_value():
    r = synthetic_record()                                                                    # KD 20 nM, free tracer 50 mP
    r['facts']['tight_binding_considered'] = fact('unknown')
    better_to_worse = {
        'assay_window': (lambda rec, w: rec['quantities'].update(signal_maximum=point(50.0 + w, 'mP', 's', ['s'])), [300.0, 100.0, 70.0, 69.0, 50.0, 30.0, 21.0, 20.0, 5.0]),
        'tracer_concentration': (lambda rec, x: rec['quantities'].update(tracer_concentration=point(20.0 * x, 'nM', 't', ['s'])), [0.1, 1.0, 1.05, 2.0, 4.0, 8.0, 9.9, 10.0, 30.0]),
        'direct_vs_competition': (lambda rec, f: rec['quantities'].update(ki=point(20.0 * f, 'nM', 'k', ['s'])), [1.0, 3.0, 3.1, 5.0, 8.0, 9.9, 10.0, 40.0]),
        'concentration_series': (lambda rec, top: rec['concentration_series'].update(value=[2.0, 4.0, 8.0, 12.0, 16.0, 18.0, 19.0, 20.0 * top]), [50.0, 10.0, 9.5, 5.0, 3.0, 1.5, 1.05, 1.0]),
    }
    for name, (setter, values) in better_to_worse.items():
        degrees = sweep(r, name, setter, values)
        assert degrees == sorted(degrees, reverse=True), (name, degrees)                       # worse never raises the degree
        just_past = next(d for d in degrees if 0.0 < d < 1.0)
        assert 0.9 < just_past < 1.0, (name, degrees)                                          # no step: just past the researched value keeps most of the credit
    lows = sweep(r, 'concentration_series', lambda rec, low: rec['concentration_series'].update(value=[20.0 * low, 30.0, 40.0, 60.0, 80.0, 120.0, 200.0, 400.0]), [0.05, 0.2, 0.21, 0.4, 0.6, 0.9, 0.99, 1.0])
    assert lows == sorted(lows, reverse=True) and lows[0] == lows[1] == 1.0 and 0.9 < lows[2] < 1.0 and lows[-1] == 0.0


def test_the_new_shapes_are_gentle_near_the_researched_value_where_the_error_grows_slowly():
    r = synthetic_record()
    # window: losing 20 mP near the full end costs less than losing 5 mP near the zero end (error goes as 1 / window)
    r['quantities']['signal_maximum'] = point(50.0 + 50.0, 'mP', 's', ['s'])
    near_full = 1.0 - judged(r, 'assay_window')['degree']
    r['quantities']['signal_maximum'] = point(50.0 + 25.0, 'mP', 's', ['s'])
    near_zero = judged(r, 'assay_window')['degree']                                           # what is left to lose between 25 and 20 mP
    assert near_full < 0.25 < near_zero < 0.3
    # top of the series: 5.5 x KD already sees 85 percent of the plateau and keeps most of the credit
    r['concentration_series']['value'] = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 110.0]
    assert judged(r, 'concentration_series')['degree'] == pytest.approx(11 / 13)


def test_the_sheet_judges_the_intensity_change_with_a_degree():
    r = synthetic_record()
    r['facts']['intensity_change_checked'] = fact('unknown')

    def change(percent):
        return lambda record: record['quantities'].update(total_intensity_change=point(percent, 'percent', 'c', ['s']))
    check_scale(r, 'intensity_change', ((change(0.0), 'supported', 1.0), (change(30.0), 'supported', 1.0), (change(65.0), 'supported', 0.5), (change(99.0), 'supported', 1 / 70),
                                        (change(100.0), 'conflicting', None), (change(250.0), 'conflicting', None)))
    r['facts']['intensity_change_checked'] = fact('no', ['s'])
    assert judged(r, 'intensity_change')['status'] == 'conflicting'                           # the fact is the grader's, whatever the number


def test_the_sheet_judges_the_replicate_count_with_a_degree_when_the_titrations_are_independent():
    r = synthetic_record()
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', math.sqrt(2 / 3)), (1, 'yes', 'supported', math.sqrt(1 / 3)),
                                                 (2, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None)):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        status, got = sheet_status_and_degree(r, 'replicates')
        assert status == expected and got == (pytest.approx(degree) if degree is not None else None), (count, independent)
    r['facts']['independent_titrations'] = fact('no', ['s'])
    assert judged(r, 'replicates')['status'] == 'conflicting'                                 # a stated no is the paper's own fact, the grader's


def test_the_replicate_count_is_gradual_around_min_replicates_monotone_and_bounded():
    r = synthetic_record()
    degrees = []
    for count in range(1, 12):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        verdict = judged(r, 'replicates')
        assert verdict['status'] == 'supported' and 0.0 < verdict['degree'] <= 1.0, count
        degrees.append(verdict['degree'])
    assert degrees == sorted(degrees)                                                         # more independent titrations never lower the degree
    assert degrees[MIN_REPLICATES - 1] == pytest.approx(1.0) and 0.5 < degrees[MIN_REPLICATES - 2] < 1.0      # full at the researched count; no step just below it
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    r['spread_kind'] = 'standard_deviation'
    assert convert_fp(grade_fp(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(2.0 * 2.0 / 2)      # two independent titrations: sd^2 / n
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(math.sqrt(2 / 3))


def test_the_sheet_judges_the_fold_gap_of_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM

    def ki(nm):
        return lambda record: record['quantities'].update(ki=point(nm, 'nM', 'k', ['s']))
    # linear in log(fold) from 3 to 10: fold 6.5 -> 1 - log(6.5 / 3) / log(10 / 3)
    check_scale(r, 'direct_vs_competition', ((ki(40.0), 'supported', 1.0), (ki(60.0), 'supported', 1.0), (ki(130.0), 'supported', 1 - math.log(6.5 / 3) / math.log(10 / 3)), (ki(10.0), 'supported', 1.0),
                                             (ki(200.0), 'conflicting', None), (ki(2.0), 'conflicting', None)))


def test_a_degree_of_a_member_travels_into_its_sheet_criterion_and_the_weakest_member_counts():
    r = synthetic_record()
    r['quantities']['signal_maximum'] = point(95.0, 'mP', 's', ['s'])                         # window 45 mP: 7/9
    r['quantities']['ki'] = point(110.0, 'nM', 'k', ['s'])                                    # fold gap 5.5, in another sheet criterion
    fold_degree = 1 - math.log(5.5 / 3) / math.log(10 / 3)
    interpretations = convert_fp(grade_fp(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability'] == {'status': 'supported', 'support_refs': ['span_exp_synthetic_fp_1', 's'], 'degree': pytest.approx(7 / 9)}
    assert interpretations['binding_regime']['degree'] == pytest.approx(fold_degree) and interpretations['binding_controls'].get('degree') is None
    r['quantities']['total_intensity_change'] = point(65.0, 'percent', 'c', ['s'])
    r['facts']['intensity_change_checked'] = fact('unknown')
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.5)
    r['quantities']['ki'] = point(40.0, 'nM', 'k', ['s'])
    assert convert_fp(grade_fp(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(1.0)
    assert convert_fp(grade_fp(r))['sheet']['interpretations']['calibration_applicability']['degree'] == pytest.approx(7 / 9)      # it travels into the sheet


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
    r['quantities']['signal_maximum'] = point(95.0, 'mP', 's', ['s'])                                 # window 45 mP: degree 7/9
    r['quantities']['signal_minimum'] = point(50.0, 'mP', 's', ['s'], support='implied')
    assert interpretation(r, 'calibration_applicability')['degree'] == pytest.approx(7 / 9 * 0.7)


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


def test_the_window_is_also_judged_over_the_papers_own_noise_and_the_weaker_degree_counts():
    r = synthetic_record()                                                                    # minimum 50 mP, no noise stated: the absolute curve alone
    r['quantities']['signal_maximum'] = point(150.0, 'mP', 's', ['s'])                       # window 100
    assert sheet_status_and_degree(r, 'assay_window') == ('supported', 1.0)

    def noise(window, sd):
        def setter(record):
            record['quantities'].update(signal_maximum=point(50.0 + window, 'mP', 's', ['s']), signal_noise=point(sd, 'mP', 'n', ['n']))
        return setter
    low, zero = 1 / WINDOW_OVER_NOISE_FULL, 1 / WINDOW_OVER_NOISE_ZERO
    relative = lambda window, sd: (zero - sd / window) / (zero - low)
    # linear in noise / window between 1/12 and 1/3; the absolute curve (70 / 20 mP) counts too, the weaker of the two
    check_scale(r, 'assay_window', ((noise(200.0, 10.0), 'supported', 1.0), (noise(100.0, 10.0), 'supported', relative(100.0, 10.0)), (noise(100.0, 33.0), 'supported', relative(100.0, 33.0)),
                                    (noise(30.0, 5.0), 'supported', min(relative(30.0, 5.0), (1 / 20 - 1 / 30) / (1 / 20 - 1 / 70))), (noise(100.0, 100.0 / 3.0), 'conflicting', None), (noise(100.0, 50.0), 'conflicting', None),
                                    (noise(15.0, 0.5), 'conflicting', None)))                 # the last: the absolute window is already below 20 mP
    noise(100.0, 10.0)(r)
    assert grade_fp(r)['native']['window_noise_refs'] == ['n'] and judged(r, 'assay_window') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_fp_1', 's', 'n'], 'degree': pytest.approx(relative(100.0, 10.0))}
    assert (WINDOW_OVER_NOISE_FULL, WINDOW_OVER_NOISE_ZERO) == (12.0, 3.0)
    degrees = [sheet_status_and_degree(r, 'assay_window')[1] for sd in (1.0, 5.0, 8.0, 12.0, 20.0, 30.0) if noise(100.0, sd)(r) is None]
    assert degrees == sorted(degrees, reverse=True) and all(0.0 <= d <= 1.0 for d in degrees)       # more noise never raises the degree


def test_the_intensity_change_is_judged_on_the_bias_of_the_apparent_kd_when_its_direction_is_stated():
    r = synthetic_record()
    r['facts']['intensity_change_checked'] = fact('unknown')

    def change(percent, direction):
        def setter(record):
            record['quantities'].update(total_intensity_change=point(percent, 'percent', 'c', ['s']))
            record['intensity_change_direction'] = direction
        return setter
    bias_degree = lambda bias: (math.log(2.0) - math.log(bias)) / (math.log(2.0) - math.log(1.3))
    check_scale(r, 'intensity_change', ((change(65.0, None), 'supported', 0.5),                                   # sign not stated: the percent curve as before
                                        (change(30.0, 'increase'), 'supported', 1.0), (change(65.0, 'increase'), 'supported', bias_degree(1.65)), (change(100.0, 'increase'), 'conflicting', None),
                                        (change(20.0, 'decrease'), 'supported', 1.0), (change(40.0, 'decrease'), 'supported', bias_degree(1 / 0.6)),      # a fall of 40 percent is a 1.67-fold bias
                                        (change(60.0, 'decrease'), 'conflicting', None), (change(100.0, 'decrease'), 'conflicting', None)))
    # a fall is never judged better than a rise of the same size, and a larger fall never scores higher
    falls = [sheet_status_and_degree(r, 'intensity_change') for p in (10.0, 23.0, 30.0, 40.0, 45.0, 49.0) if change(p, 'decrease')(r) is None]
    assert [d for _, d in falls] == sorted((d for _, d in falls), reverse=True) and all(s == 'supported' for s, _ in falls)
    change(40.0, 'decrease')(r)
    degree_fall = judged(r, 'intensity_change')['degree']
    change(40.0, 'increase')(r)
    assert degree_fall < judged(r, 'intensity_change')['degree']


def test_a_competitor_series_is_judged_against_the_ic50_when_it_is_given():
    r = synthetic_record()                                                                    # KD 20 nM; the series 2 to 2000 nM brackets it
    assert grade_fp(r)['native']['series_reference'] == 'kd' and judged(r, 'concentration_series')['status'] == 'supported'
    r['quantities']['ic50'] = point(2000.0, 'nM', 'i', ['i'])
    assert grade_fp(r)['native']['series_reference'] == 'kd'                                  # series_kind not stated: against the constant, as before
    r['series_kind'] = 'titrant'
    assert grade_fp(r)['native']['series_reference'] == 'kd' and judged(r, 'concentration_series')['status'] == 'supported'
    r['series_kind'] = 'competitor'                                                           # the IC50 is at the top of the series: the plateau is not seen
    graded = grade_fp(r)
    assert graded['native']['series_reference'] == 'ic50' and graded['native']['concentration_high_over_constant'] == pytest.approx(1.0)
    verdict = _criterion(graded, 'concentration_series')
    assert verdict['status'] == 'conflicting' and verdict['support_refs'][-1] == 'i'
    r['quantities']['ic50'] = point(20.0, 'nM', 'i', ['i'])                                   # a competitor series bracketing the IC50
    assert judged(r, 'concentration_series')['status'] == 'supported'
    r['quantities']['ic50'] = {**r['quantities']['ic50'], 'status': 'unavailable', 'value': None}
    graded = grade_fp(r)
    assert graded['native']['series_reference'] == 'kd' and judged(r, 'concentration_series')['status'] == 'supported'      # no IC50: the constant
