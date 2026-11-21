"""MST converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CONCENTRATIONS_ZERO_AGREEMENT, CRITERIA_MAP, EQUILIBRATION_REFERENCE_NM, KON_FAST_PER_M_S, KON_SLOW_PER_M_S, FHOT_ZERO_AGREEMENT_S, FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LABELLED_MAX_OVER_KD,
    LABELLED_ZERO_AGREEMENT_OVER_KD, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MIN_CONCENTRATIONS, MIN_FHOT_S, MIN_FNORM_AMPLITUDE_PERMILLE, MIN_INCUBATION_MIN, MIN_REPLICATES, MIN_SIGNAL_TO_NOISE, NULL_REASONS,
    SIGNAL_TO_NOISE_ZERO_AGREEMENT, _criterion, convert_mst)
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
    assert (MIN_CONCENTRATIONS, CONCENTRATIONS_ZERO_AGREEMENT, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (10, 3, 0.2, 1.0, 10.0, 1.0)
    assert (LABELLED_MAX_OVER_KD, LABELLED_ZERO_AGREEMENT_OVER_KD, MIN_INCUBATION_MIN, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.0, 10.0, 10.0, 3, 3.0, 10.0)
    assert (EQUILIBRATION_REFERENCE_NM, KON_FAST_PER_M_S, KON_SLOW_PER_M_S) == (10.0, 1.0e6, 1.0e5)
    assert KON_FAST_PER_M_S * EQUILIBRATION_REFERENCE_NM * 1e-9 == pytest.approx(0.01)       # the off rate (per s) of the researched 10 minutes: kon x KD


def test_the_sheet_judges_the_signal_to_noise_and_the_fnorm_change_with_a_degree():
    r = synthetic_record()

    def signal(noise, amplitude):
        def put(record):
            for name, value, unit in (('signal_to_noise', noise, 'ratio'), ('fnorm_amplitude', amplitude, 'permille')):
                record['quantities'][name] = point(value, unit, name, ['s']) if value is not None else {**record['quantities'][name], 'status': 'unavailable', 'value': None}
        return put
    # the signal-to-noise (the paper's own relative scale) governs when stated; the absolute Fnorm change is judged only without it (range review)
    check_scale(r, 'signal_amplitude', ((signal(18.0, 12.0), 'supported', 1.0), (signal(5.0, 5.0), 'supported', 1.0), (signal(3.0, 12.0), 'supported', 0.5), (signal(18.0, 3.0), 'supported', 1.0),
                                        (signal(3.0, 2.0), 'supported', 0.5), (signal(1.0, 12.0), 'conflicting', None), (signal(18.0, 1.0), 'supported', 1.0), (signal(18.0, 0.5), 'supported', 1.0),
                                        (signal(None, 3.0), 'supported', 0.5), (signal(None, 2.0), 'supported', 0.25), (signal(None, 1.0), 'conflicting', None), (signal(3.0, None), 'supported', 0.5)))
    assert 's' in judged(r, 'signal_amplitude')['support_refs']


def test_a_quiet_instrument_with_a_small_fnorm_change_and_a_high_signal_to_noise_is_not_marked_down():
    r = synthetic_record()
    r['quantities']['fnorm_amplitude'] = point(3.0, 'permille', 'a', ['s'])      # 3 per mille at S/N 18: the noise is about 0.17 per mille, the curve is clear
    assert sheet_status_and_degree(r, 'signal_amplitude') == ('supported', 1.0)
    degrees = []
    for noise in (1.5, 2.0, 3.0, 4.0, 4.9, 5.0, 8.0):                             # monotone in the signal-to-noise, no step at MIN_SIGNAL_TO_NOISE
        r['quantities']['signal_to_noise'] = point(noise, 'ratio', 's', ['s'])
        degrees.append(sheet_status_and_degree(r, 'signal_amplitude')[1])
    assert degrees == sorted(degrees) and 0.9 < degrees[4] < 1.0 and degrees[5] == 1.0


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
    # linear in the log of the depletion error 1 + r / 2: 1.5-fold at r = 1 (full), 6-fold at r = 10 (zero)
    def log_degree(ratio):
        return math.log(6.0 / (1 + ratio / 2)) / math.log(6.0 / 1.5)
    check_scale(r, 'labelled_concentration', ((labelled(5.0), 'supported', 1.0), (labelled(20.0), 'supported', 1.0), (labelled(40.0), 'supported', log_degree(2.0)), (labelled(110.0), 'supported', log_degree(5.5)),
                                              (labelled(200.0), 'conflicting', None), (labelled(400.0), 'conflicting', None)))
    assert log_degree(2.0) == pytest.approx(0.792, abs=1e-3) and log_degree(5.5) == pytest.approx(0.339, abs=1e-3)
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])                               # handled: the ratio no longer matters
    check_scale(r, 'labelled_concentration', ((labelled(400.0), 'supported', None),))
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = 'quadratic'
    check_scale(r, 'labelled_concentration', ((labelled(400.0), 'supported', None),))
    r['fit_model'] = '1:1'
    r['quantities']['labelled_concentration'] = {**r['quantities']['labelled_concentration'], 'status': 'unavailable', 'value': None}      # without a number the grader's fact decides, as before
    r['facts']['labelled_partner_at_or_below_kd'] = fact('no', ['s'])
    assert judged(r, 'labelled_concentration')['status'] == 'conflicting'


def occupancy(ratio):
    return ratio / (1 + ratio)


def low_degree(ratio):
    """The lowest concentration's degree, linear in the occupancy from LOW_FACTOR (1/6, full) to LOW_ZERO_AGREEMENT_FACTOR (1/2, zero)."""
    return (occupancy(LOW_ZERO_AGREEMENT_FACTOR) - occupancy(ratio)) / (occupancy(LOW_ZERO_AGREEMENT_FACTOR) - occupancy(LOW_FACTOR))


def high_degree(ratio):
    """The highest concentration's degree, linear in the occupancy from HIGH_ZERO_AGREEMENT_FACTOR (1/2, zero) to HIGH_FACTOR (10/11, full)."""
    return (occupancy(ratio) - occupancy(HIGH_ZERO_AGREEMENT_FACTOR)) / (occupancy(HIGH_FACTOR) - occupancy(HIGH_ZERO_AGREEMENT_FACTOR))


def test_the_occupancy_degrees_of_the_span_worked_by_hand():
    assert low_degree(0.6) == pytest.approx(0.375) and high_degree(5.5) == pytest.approx(11 / 13)
    assert high_degree(2.0) == pytest.approx((2 / 3 - 1 / 2) / (10 / 11 - 1 / 2))


def test_the_span_is_gradual_and_monotone_on_the_occupancy_scale():
    r = synthetic_record()
    r['facts']['tight_binding_considered'] = fact('unknown')                                  # KD 20 nM is the midpoint
    lows, highs = [], []
    for factor in (0.05, 0.1, 0.19, 0.2, 0.21, 0.3, 0.5, 0.8, 0.99):                          # a worse (higher) lowest never raises the degree
        r['concentration_series']['value'] = [20.0 * factor, *[20.0 * 2 ** (k / 2) for k in range(10)], 400.0]      # twelve values, the highest above 20 x KD
        lows.append(sheet_status_and_degree(r, 'concentration_series')[1])
    assert lows == sorted(lows, reverse=True) and lows[3] == pytest.approx(1.0) and 0.9 < lows[4] < 1.0 and lows[-1] > 0      # just above LOW_FACTOR: partial credit, no step
    for factor in (1.01, 1.5, 2.0, 5.0, 9.9, 10.0, 20.0):                                     # a better (higher) highest never lowers it
        r['concentration_series']['value'] = [2.0, *[20.0 * 2 ** (-k / 2) for k in range(1, 9)], 20.0 * factor]      # ten values, the lowest below 0.1 x KD
        highs.append(sheet_status_and_degree(r, 'concentration_series')[1])
    assert highs == sorted(highs) and highs[0] > 0 and 0.95 < highs[4] < 1.0 and highs[5] == pytest.approx(1.0)      # just below HIGH_FACTOR: most of the credit, no step


def test_the_span_is_judged_against_the_midpoint_of_the_curve():
    r = synthetic_record()                                                                    # KD 20 nM, tight binding handled
    r['quantities']['labelled_concentration'] = point(40.0, 'nM', 't', ['span_labelled'])     # the curve's middle is at KD + 40 / 2 = 40 nM
    r['concentration_series']['value'] = [8.0, 16.0, 24.0, 32.0, 48.0, 64.0, 96.0, 128.0, 256.0, 400.0]      # 0.4 x KD (0.2 x midpoint) to 20 x KD (10 x midpoint)
    verdict = judged(r, 'concentration_series')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(1.0) and 'span_labelled' in verdict['support_refs']
    r['facts']['tight_binding_considered'] = fact('unknown')                                  # a hyperbola fit: its KD is the apparent midpoint, judged against itself
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(low_degree(0.4)))
    r = synthetic_record()                                                                    # a competition Ki with its EC50: the EC50 is the midpoint
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    r['quantities']['ki'] = point(10.0, 'nM', 'k', ['s'])
    r['quantities']['ec50'] = point(30.0, 'nM', 'e', ['span_ec50'])
    r['concentration_series']['value'] = [6.0, 12.0, 24.0, 48.0, 60.0, 90.0, 120.0, 180.0, 240.0, 300.0]     # 0.6 x Ki, 0.2 x EC50; 30 x Ki, 10 x EC50
    verdict = judged(r, 'concentration_series')
    assert verdict['degree'] == pytest.approx(1.0) and 'span_ec50' in verdict['support_refs']
    r['quantities']['ec50'] = {**r['quantities']['ec50'], 'status': 'unavailable', 'value': None}         # no EC50: the Ki is used (a grader gap)
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(low_degree(0.6)))


def test_one_concentration_is_a_short_series_never_a_conflict():
    r = synthetic_record()
    r['concentration_series']['value'] = [400.0]                                              # 20 x KD: the plateau end is placed well; one point carries no credit
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', 0.0)


def test_the_sheet_judges_the_count_and_the_span_of_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')                                  # a 1:1 hyperbola fit: the reported KD is the curve's midpoint

    def series(values):
        return lambda record: record['concentration_series'].update(value=values)
    spanning = [4.0, 8.0, 16.0, 32.0, 64.0, 100.0, 150.0, 180.0, 190.0, 400.0]               # ten values, 0.2 x KD to 20 x KD
    mid = [30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0]
    check_scale(r, 'concentration_series', ((series(spanning), 'supported', 1.0), (series([12.0, *mid, 110.0]), 'supported', low_degree(0.6)),      # lowest 0.6 x KD: 0.375; highest 5.5 x KD: 0.846
                                            (series([12.0, *mid, 400.0]), 'supported', low_degree(0.6)), (series([4.0, *mid, 110.0]), 'supported', high_degree(5.5)),
                                            (series([4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 25.0, 30.0, 40.0]), 'supported', high_degree(2.0)),                                                         # a top at 2 x KD is 2/3 bound: 0.41 (linear in the ratio gave 0.11)
                                            (series([20.0, *mid, 400.0]), 'conflicting', None), (series([4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0]), 'conflicting', None),             # lowest at 1 x KD; highest at 1 x KD
                                            (series([*spanning[:8], 400.0]), 'supported', 6 / 7),                     # nine values, the same span: just below MIN_CONCENTRATIONS, (9 - 3) / (10 - 3)
                                            (series([4.0, 16.0, 64.0, 400.0]), 'supported', 1 / 7),                   # four values spanning 0.2 x KD to 20 x KD: one point beyond the three fitted parameters
                                            (series([4.0, 64.0, 400.0]), 'supported', 0.0)))                          # three values: no more points than the fit has parameters: no credit, never conflicting
    r['concentration_series']['value'] = spanning
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_mst_1']
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}      # a count without a list: the span is not known, whatever the count (a short count is never a conflict)
    for count, expected in ((2, 'unknown'), (3, 'unknown'), (4, 'unknown'), (9, 'unknown'), (10, 'unknown'), (12, 'unknown')):
        r['quantities']['titration_point_count'] = point(count, 'count', 'n', ['s'])
        assert sheet_status_and_degree(r, 'concentration_series') == (expected, None), count
    assert judged(r, 'concentration_series')['support_refs'] == []


def test_the_concentration_count_is_gradual_monotone_and_has_no_step_at_the_researched_count():
    r = synthetic_record()                                                                    # KD 20 nM; every series spans 0.05 x KD to 20 x KD, so only the count limits the degree
    degrees = []
    for count in range(CONCENTRATIONS_ZERO_AGREEMENT + 1, MIN_CONCENTRATIONS + 6):
        r['concentration_series']['value'] = [1.0 * 2 ** (step * 3 / (count - 1)) for step in range(count - 1)] + [400.0]
        status, degree = sheet_status_and_degree(r, 'concentration_series')
        assert status == 'supported' and 0 < degree <= 1, count
        degrees.append(degree)
    assert degrees == sorted(degrees)                                                         # more concentrations never lower the degree
    assert degrees[MIN_CONCENTRATIONS - CONCENTRATIONS_ZERO_AGREEMENT - 1] == pytest.approx(1.0) and set(degrees[MIN_CONCENTRATIONS - CONCENTRATIONS_ZERO_AGREEMENT - 1:]) == {1.0}      # full credit at the researched count and above
    just_below = degrees[MIN_CONCENTRATIONS - CONCENTRATIONS_ZERO_AGREEMENT - 2]
    assert 0.5 < just_below < 1.0                                                             # one point short of the researched count keeps most of the credit: no step


def test_the_sheet_judges_the_incubation_as_a_curve_on_the_papers_own_constant():
    # T_FAST = 10 min x 10 nM / KD, T_SLOW = ten times T_FAST; degree = log(t / T_FAST) / log(10), clipped to 1; t <= T_FAST conflicting.
    r = synthetic_record()                                                                    # KD 20 nM: T_FAST 5 min, T_SLOW 50 min
    r['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, expected, degree in ((1.0, 'conflicting', None), (4.0, 'conflicting', None), (5.0, 'conflicting', None), (10.0, 'supported', math.log10(2)),
                                      (15.0, 'supported', math.log10(3)), (25.0, 'supported', math.log10(5)), (50.0, 'supported', 1.0), (120.0, 'supported', 1.0)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        got_status, got_degree = sheet_status_and_degree(r, 'equilibrium')
        assert got_status == expected, minutes
        assert got_degree == (pytest.approx(degree) if degree is not None else None), minutes
    assert math.log10(2) == pytest.approx(0.30103, abs=1e-5) and math.log10(3) == pytest.approx(0.47712, abs=1e-5)
    assert judged(r, 'equilibrium')['support_refs'] == ['s']
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported' and 'degree' not in judged(r, 'equilibrium')      # the stated fact is the grader's, whatever the time


def test_the_incubation_curve_for_a_weak_and_a_tight_binder_and_the_reference():
    for kd, cases in ((1000.0, ((0.05, 'conflicting', None), (0.1, 'conflicting', None), (0.2, 'supported', math.log10(2)), (1.0, 'supported', 1.0), (5.0, 'supported', 1.0))),      # 1 uM: T_FAST 0.1 min (6 s), T_SLOW 1 min
                      (10.0, ((10.0, 'conflicting', None), (30.0, 'supported', math.log10(3)), (100.0, 'supported', 1.0))),                                                       # the reference KD: 10 min and 100 min
                      (0.01, ((30.0, 'conflicting', None), (6000.0, 'conflicting', None), (10000.0, 'conflicting', None), (20000.0, 'supported', math.log10(2)), (100000.0, 'supported', 1.0)))):      # 10 pM: T_FAST 10000 min, T_SLOW 100000 min
        r = synthetic_record(kd=kd)
        r['facts']['equilibrium_reached'] = fact('unknown')
        for minutes, expected, degree in cases:
            r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
            got_status, got_degree = sheet_status_and_degree(r, 'equilibrium')
            assert got_status == expected, (kd, minutes)
            assert got_degree == (pytest.approx(degree) if degree is not None else None), (kd, minutes)


def test_the_incubation_curve_never_falls_with_a_longer_time_and_never_rises_with_a_tighter_binder():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    last = 0.0
    for minutes in (6.0, 8.0, 12.0, 20.0, 35.0, 49.0, 60.0):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        degree = judged(r, 'equilibrium')['degree']
        assert degree >= last and 0 < degree <= 1
        last = degree
    tighter = synthetic_record(kd=2.0)                                                        # T_FAST 50 min: 15 min is conflicting, where 20 nM gave 0.477
    tighter['facts']['equilibrium_reached'] = fact('unknown')
    assert sheet_status_and_degree(tighter, 'equilibrium') == ('conflicting', None)


def test_the_incubation_uses_the_ki_without_a_kd_and_is_unknown_without_a_binding_constant():
    r = synthetic_record()                                                                    # KD 20, Ki 40 nM, EC50 30 nM, incubation 15 min
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    assert sheet_status_and_degree(r, 'equilibrium') == ('supported', pytest.approx(math.log10(6)))      # Ki 40 nM: T_FAST 2.5 min, 15 / 2.5 = 6
    r['quantities']['ki'] = {**r['quantities']['ki'], 'status': 'unavailable', 'value': None}
    assert sheet_status_and_degree(r, 'equilibrium') == ('unknown', None)                     # an EC50 alone is no association scale
    r['quantities']['ec50'] = {**r['quantities']['ec50'], 'status': 'unavailable', 'value': None}
    assert sheet_status_and_degree(r, 'equilibrium') == ('unknown', None)                     # no constant at all
    r['quantities']['incubation_time'] = point(0.5, 'min', 'i', ['s'])
    assert sheet_status_and_degree(r, 'equilibrium') == ('unknown', None)                     # also for a very short time: a time alone is not the paper against equilibrium


def test_the_sheet_judges_the_replicate_count_with_a_degree_and_its_independence():
    r = synthetic_record()
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', (2 / 3) ** 0.5), (1, 'yes', 'supported', (1 / 3) ** 0.5),
                                                 (2, 'unknown', 'unknown', None), (1, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None)):      # sqrt(n / 3); a stated count is never conflicting
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        got = sheet_status_and_degree(r, 'replicates')
        assert got == (expected, pytest.approx(degree) if degree is not None else None), (count, independent, got)
    r['facts']['independent_titrations'] = fact('no', ['s'])
    assert judged(r, 'replicates')['status'] == 'conflicting'


def test_the_replicate_count_is_gradual_monotone_and_has_no_step_at_the_researched_count():
    r = synthetic_record()
    degrees = []
    for count in range(1, MIN_REPLICATES + 4):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        status, degree = sheet_status_and_degree(r, 'replicates')
        assert status == 'supported' and 0 < degree <= 1, count
        degrees.append(degree)
    assert degrees == sorted(degrees) and degrees[MIN_REPLICATES - 1] == pytest.approx(1.0)
    assert 0 < degrees[0] < degrees[MIN_REPLICATES - 2] < 1.0                                 # one and two independent titrations: partial credit, not a fail


def test_two_independent_titrations_now_give_a_variance_from_a_standard_deviation():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    converted = convert_mst(grade_mst(r))
    # sd 6 nM, 2 independent titrations: variance 36 / 2 = 18; the sampling basis is supported with the partial degree sqrt(2 / 3)
    assert converted['sheet']['cells']['effect_variance']['value'] == pytest.approx(18.0)
    sampling = converted['extraction']['interpretations']['sampling_basis']
    assert sampling['status'] == 'supported' and sampling['support_refs'] and sampling['degree'] == pytest.approx((2 / 3) ** 0.5)


def test_the_sheet_judges_the_fold_gap_of_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM

    def ki(nm):
        return lambda record: record['quantities'].update(ki=point(nm, 'nM', 'k', ['s']))
    def log_fold(fold):                                                                       # linear in log fold from AGREEMENT_FACTOR (full) to AGREEMENT_ZERO_FACTOR (zero)
        return math.log(AGREEMENT_ZERO_FACTOR / fold) / math.log(AGREEMENT_ZERO_FACTOR / AGREEMENT_FACTOR)
    check_scale(r, 'direct_vs_competition', ((ki(40.0), 'supported', 1.0), (ki(60.0), 'supported', 1.0), (ki(100.0), 'supported', log_fold(5.0)), (ki(130.0), 'supported', log_fold(6.5)), (ki(10.0), 'supported', 1.0),
                                             (ki(4.0), 'supported', log_fold(5.0)), (ki(200.0), 'conflicting', None), (ki(2.0), 'conflicting', None)))      # a gap either way counts the same
    assert log_fold(5.0) == pytest.approx(0.576, abs=1e-3) and log_fold(6.5) == pytest.approx(0.358, abs=1e-3)
    degrees = []
    for fold in (1.0, 2.9, 3.0, 3.1, 5.0, 9.0, 9.9):                                         # a larger gap never raises the degree; just past AGREEMENT_FACTOR keeps most of it
        ki(20.0 * fold)(r)
        degrees.append(sheet_status_and_degree(r, 'direct_vs_competition')[1])
    assert degrees == sorted(degrees, reverse=True) and degrees[2] == pytest.approx(1.0) and 0.95 < degrees[3] < 1.0 and degrees[-1] > 0


def test_a_degree_of_a_member_travels_into_its_sheet_criterion_and_the_weakest_member_counts():
    r = synthetic_record()
    r['quantities']['signal_to_noise'] = point(3.0, 'ratio', 's', ['s'])                      # 0.5, in calibration_applicability
    r['quantities']['ki'] = point(130.0, 'nM', 'k', ['s'])                                    # fold gap 6.5: log(10 / 6.5) / log(10 / 3), in binding_regime
    interpretations = convert_mst(grade_mst(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['degree'] == pytest.approx(0.5)
    assert interpretations['binding_regime']['degree'] == pytest.approx(math.log(10 / 6.5) / math.log(10 / 3)) and interpretations['binding_controls'].get('degree') is None
    r['quantities']['fhot_time'] = point(0.75, 's', 'f', ['s'])                               # 0.75, in binding_parameter_definition
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.75)
    r['quantities']['fnorm_amplitude'] = point(2.0, 'permille', 'a', ['s'])                   # with a signal-to-noise stated the Fnorm change does not count: still 0.5
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)
    r['quantities']['signal_to_noise'] = {**r['quantities']['signal_to_noise'], 'status': 'unavailable', 'value': None}      # without it the Fnorm change is judged: 0.25
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


def test_the_papers_own_fnorm_noise_turns_the_amplitude_into_a_signal_to_noise_when_none_is_stated():
    r = synthetic_record()
    r['quantities']['signal_to_noise'] = {**r['quantities']['signal_to_noise'], 'status': 'unavailable', 'value': None}
    r['quantities']['fnorm_amplitude'] = point(3.0, 'permille', 'a', ['s'])
    degrees = []
    for noise in (0.1, 0.5, 0.6, 1.0, 3.0):        # S/N 30, 6, 5, 3, 1
        r['quantities']['fnorm_noise'] = point(noise, 'permille', 'n', ['s'])
        verdict = convert_mst(grade_mst(r))['extraction']['interpretations']['calibration_applicability']
        degrees.append(verdict.get('degree') if verdict['status'] == 'supported' else None)
    assert degrees[:3] == [1.0, 1.0, 1.0] and degrees[3] == pytest.approx(0.5) and degrees[4] is None      # 1 is the noise end: conflicting
    r['quantities']['fnorm_noise'] = {**r['quantities']['fnorm_noise'], 'status': 'unavailable', 'value': None}      # no noise: the 1 per mille proxy, 3 per mille -> 0.5
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)
    r['quantities']['fnorm_noise'] = point(0.1, 'permille', 'n', ['s'])
    r['quantities']['signal_to_noise'] = point(3.0, 'ratio', 's', ['s'])      # a stated signal-to-noise still governs
    assert convert_mst(grade_mst(r))['extraction']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)
