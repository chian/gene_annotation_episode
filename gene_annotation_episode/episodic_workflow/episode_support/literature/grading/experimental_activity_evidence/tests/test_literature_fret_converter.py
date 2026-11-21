"""FRET converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, DELAY_ZERO_AGREEMENT_US, EQUILIBRATION_REFERENCE_NM, HIGH_FACTOR, KON_FAST_PER_M_S, KON_SLOW_PER_M_S, HIGH_ZERO_AGREEMENT_FACTOR, HILL_FIT_PARAMETERS, INTEGRATION_NOISE_EXPONENT, LABELLED_MAX_OVER_KD,
    LABELLED_ZERO_AGREEMENT_OVER_KD, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MIN_CONCENTRATIONS, MIN_DELAY_US, MIN_INCUBATION_MIN, MIN_INTEGRATION_US, MIN_REPLICATES, MIN_WINDOW_FOLD, NULL_REASONS, SERIES_FIT_PARAMETERS,
    TIGHT_BINDING_FULL_OVER_KD, TIGHT_BINDING_ZERO_OVER_KD, WINDOW_ZERO_AGREEMENT_FOLD, _criterion, convert_fret)
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
    assert (MIN_WINDOW_FOLD, WINDOW_ZERO_AGREEMENT_FOLD, MIN_DELAY_US, DELAY_ZERO_AGREEMENT_US, MIN_INTEGRATION_US, INTEGRATION_NOISE_EXPONENT) == (2.0, 1.0, 50.0, 5.0, 100.0, 0.5)
    assert (MIN_CONCENTRATIONS, SERIES_FIT_PARAMETERS, HILL_FIT_PARAMETERS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (8, 3, 4, 0.2, 1.0, 10.0, 1.0)
    assert (LABELLED_MAX_OVER_KD, LABELLED_ZERO_AGREEMENT_OVER_KD, TIGHT_BINDING_FULL_OVER_KD, TIGHT_BINDING_ZERO_OVER_KD) == (1.0, 10.0, 10.0, 100.0)
    assert (MIN_INCUBATION_MIN, EQUILIBRATION_REFERENCE_NM, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (15.0, 2.0, 3, 3.0, 10.0)
    assert (KON_FAST_PER_M_S, KON_SLOW_PER_M_S) == (1.0e6, 1.0e5)


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
    check_scale(r, 'time_gating', ((gate(100.0, 400.0), 'supported', 1.0), (gate(50.0, 100.0), 'supported', 1.0), (gate(27.5, 400.0), 'supported', 0.5), (gate(100.0, 25.0), 'supported', 0.5),
                                   (gate(27.5, 25.0), 'supported', 0.5), (gate(5.0, 400.0), 'conflicting', None), (gate(0.0, 400.0), 'conflicting', None),
                                   (gate(100.0, 10.0), 'supported', math.sqrt(0.1)), (gate(100.0, 55.0), 'supported', math.sqrt(0.55)), (gate(100.0, 0.0), 'supported', 0.0)))      # a short window: precision only, never conflicting
    missing = {**r['quantities']['integration_time'], 'status': 'unavailable', 'value': None}
    r['quantities']['delay_time'] = point(27.5, 'us', 'd', ['s'])
    r['quantities']['integration_time'] = missing
    assert sheet_status_and_degree(r, 'time_gating') == ('supported', pytest.approx(0.5))      # no window given: the delay decides
    r['donor_acceptor_pair'] = 'organic_dye_pair'
    assert sheet_status_and_degree(r, 'time_gating') == ('conflicting', None)                  # a short-lived donor is the grader's own fact-based conflict


def test_the_integration_window_is_a_monotone_precision_curve_and_never_conflicts():
    r = synthetic_record()
    credit = []
    for window in (1.0, 5.0, 10.0, 25.0, 50.0, 90.0, 99.0, 100.0, 400.0):
        r['quantities']['integration_time'] = point(window, 'us', 'w', ['s'])
        status, degree = sheet_status_and_degree(r, 'time_gating')
        assert status == 'supported' and 0.0 < degree <= 1.0, window
        assert degree == pytest.approx(min(1.0, window / MIN_INTEGRATION_US) ** INTEGRATION_NOISE_EXPONENT), window
        credit.append(degree)
    assert credit == sorted(credit)                                                           # a longer window never lowers the degree
    assert 0.9 < credit[6] < 1.0                                                              # no step just below the researched 100 us


def test_the_sheet_judges_the_labelled_over_the_kd_with_a_degree_unless_tight_binding_is_handled():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['quantities']['acceptor_concentration'] = {**r['quantities']['acceptor_concentration'], 'status': 'unavailable', 'value': None}

    def donor(nm):
        return lambda record: record['quantities'].update(donor_concentration=point(nm, 'nM', 't', ['s']))
    check_scale(r, 'labelled_concentration', ((donor(5.0), 'supported', 1.0), (donor(20.0), 'supported', 1.0), (donor(110.0), 'supported', math.log(6.0 / 3.75) / math.log(4.0)), (donor(200.0), 'conflicting', None), (donor(400.0), 'conflicting', None)))
    # log of the depletion bias b = 1 + ratio / 2, ends b(1) = 1.5 and b(10) = 6: KD 20 nM, labelled 110 nM -> ratio 5.5, b = 3.75, degree ln(1.6) / ln(4) = 0.339 (was linear 0.5);
    # labelled 40 nM -> ratio 2, b = 2, ln(3) / ln(4) = 0.792; labelled 160 nM -> ratio 8, b = 5, ln(1.2) / ln(4) = 0.132
    check_scale(r, 'labelled_concentration', ((donor(40.0), 'supported', math.log(3.0) / math.log(4.0)), (donor(160.0), 'supported', math.log(1.2) / math.log(4.0))))
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])                               # handled: the bias is removed; full to 10 x KD, then the rounding 1 / sqrt(ratio) above the noise
    rounding = lambda ratio: (ratio ** -0.5 - 0.1) / (10.0 ** -0.5 - 0.1)                      # noqa: E731
    check_scale(r, 'labelled_concentration', ((donor(100.0), 'supported', None), (donor(200.0), 'supported', None), (donor(400.0), 'supported', rounding(20.0)),
                                              (donor(1000.0), 'supported', rounding(50.0)), (donor(2000.0), 'conflicting', None), (donor(4000.0), 'conflicting', None)))
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = 'quadratic'
    check_scale(r, 'labelled_concentration', ((donor(200.0), 'supported', None), (donor(400.0), 'supported', rounding(20.0))))
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
    # the ends are linear in the one-site occupancy x / (1 + x): lowest end 1.5 (1 - x) / (1 + x) between 0.2 and 1 x KD, highest end 11 (x - 1) / (9 (1 + x)) between 1 and 10 x KD
    check_scale(r, 'concentration_series', ((series(spanning), 'supported', 1.0), (series([12.0, *mid, 110.0]), 'supported', 0.375),      # lowest 0.6 x KD: 0.375; highest 5.5 x KD: 0.846
                                            (series([12.0, *mid, 400.0]), 'supported', 0.375), (series([4.0, *mid, 110.0]), 'supported', 11 * 4.5 / (9 * 6.5)),
                                            (series([4.0, 8.0, 12.0, 16.0, 20.0, 25.0, 30.0, 40.0]), 'supported', 11 / 27), (series([20.0 / 3, *mid, 400.0]), 'supported', 0.75),      # highest 2 x KD: 0.41; lowest KD / 3: 0.75
                                            (series([20.0, *mid, 400.0]), 'conflicting', None), (series([4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 20.0]), 'conflicting', None),   # lowest at 1 x KD; highest at 1 x KD
                                            (series(spanning[:7]), 'supported', 0.8)))      # seven values, one short of MIN_CONCENTRATIONS: (7 - 3) / (8 - 3), partial credit, not a conflict
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_fret_1']


def test_the_series_ends_are_monotone_in_occupancy_with_no_step_at_the_researched_factors():
    r = synthetic_record()                                                                    # KD 20 nM
    mid = [30.0, 40.0, 50.0, 60.0, 70.0, 80.0]

    def with_series(values):
        r['concentration_series']['value'] = values
        return sheet_status_and_degree(r, 'concentration_series')
    highs = [with_series([2.0, *mid, top]) for top in (25.0, 40.0, 100.0, 180.0, 199.0, 200.0, 400.0)]
    assert all(status == 'supported' for status, _ in highs) and [d for _, d in highs] == sorted(d for _, d in highs)
    assert 0.95 < highs[4][1] < 1.0 and highs[5][1] == pytest.approx(1.0)                   # just below 10 x KD: partial credit, not a step
    lows = [with_series([bottom, *mid, 400.0]) for bottom in (19.0, 12.0, 4.4, 4.0, 2.0)]
    assert all(status == 'supported' for status, _ in lows) and [d for _, d in lows] == sorted(d for _, d in lows)
    assert 0.9 < lows[2][1] < 1.0 and lows[3][1] == pytest.approx(1.0)                       # just above 0.2 x KD: partial credit


def test_a_competition_series_is_judged_against_its_own_ic50_else_its_ki():
    r = synthetic_record()                                                                    # KD 20, Ki 40, IC50 80 nM
    r['assay_format'] = 'competition'
    r['fit_model'] = 'competitive_binding'
    r['concentration_series']['value'] = [16.0, 24.0, 40.0, 60.0, 100.0, 160.0, 250.0, 400.0]
    # against the IC50 80 nM: lowest 0.2 x (full), highest 5 x: 11 * 4 / (9 * 6); the tracer's KD (the grader's constant) is not the competitor's midpoint
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(44 / 54))
    r['quantities']['ic50'] = {**r['quantities']['ic50'], 'status': 'unavailable', 'value': None}
    # against the Ki 40 nM: lowest 0.4 x: 1.5 * 0.6 / 1.4; highest 10 x (full)
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(1.5 * 0.6 / 1.4))
    r['assay_format'] = 'direct_titration'
    r['fit_model'] = '1:1'
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(1.5 * 0.2 / 1.8))      # a direct titration: against the KD 20 nM, lowest 0.8 x
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    r['quantities']['ic50'] = point(80.0, 'nM', 'ic', ['s_ic50'])
    verdict = judged(r, 'concentration_series')                                               # a Ki as the constant is a competition: against its IC50
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(44 / 54) and 's_ic50' in verdict['support_refs']


def test_a_hill_fit_consumes_one_more_point_of_the_series():
    r = synthetic_record()
    r['fit_model'] = 'hill'
    for count, degree in ((HILL_FIT_PARAMETERS, 0.0), (5, 0.25), (7, 0.75), (MIN_CONCENTRATIONS, 1.0)):
        r['concentration_series']['value'] = well_spread(count)
        assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(degree)), count


def well_spread(count):
    """``count`` titrant concentrations from 0.1 x to 20 x the KD of 20 nM (geometric): the span is fully credited, only the count varies."""
    return [2.0 * 200.0 ** (i / (count - 1)) for i in range(count)]


def test_the_concentration_count_is_a_gradual_curve_full_at_min_concentrations_with_no_step():
    r = synthetic_record()
    results = {}
    for count in range(2, 13):
        r['concentration_series']['value'] = well_spread(count)
        results[count] = sheet_status_and_degree(r, 'concentration_series')
    for count in range(2, SERIES_FIT_PARAMETERS + 1):
        assert results[count] == ('supported', 0.0), count                                  # fitted exactly by the three-parameter hyperbola: no credit, but never conflicting
    for count in range(SERIES_FIT_PARAMETERS + 1, 13):
        status, degree = results[count]
        assert status == 'supported' and 0.0 < degree <= 1.0, count
        assert degree == pytest.approx(min(1.0, (count - SERIES_FIT_PARAMETERS) / (MIN_CONCENTRATIONS - SERIES_FIT_PARAMETERS))), count
    degrees = [results[count][1] for count in range(SERIES_FIT_PARAMETERS + 1, 13)]
    assert degrees == sorted(degrees)                                                         # monotone: a longer series never lowers the degree
    assert results[MIN_CONCENTRATIONS][1] == pytest.approx(1.0) and results[MIN_CONCENTRATIONS + 4][1] == pytest.approx(1.0)
    assert 0.5 < results[MIN_CONCENTRATIONS - 1][1] < 1.0                                    # no step: just below the researched value is partial credit, not 0


def test_the_sheet_judges_the_incubation_gradually_against_the_papers_own_constant():
    r = synthetic_record()                                                                    # KD 20 nM: T_FAST = 15 x 2 / 20 = 1.5 min, T_SLOW = 10 x T_FAST = 15 min
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert KON_FAST_PER_M_S / KON_SLOW_PER_M_S == 10.0
    for minutes, expected, degree in ((1.5, 'conflicting', None), (1.4, 'conflicting', None), (0.5, 'conflicting', None), (3.0, 'supported', math.log(2.0) / math.log(10.0)),      # 0.301
                                      (10.0, 'supported', math.log(10.0 / 1.5) / math.log(10.0)), (14.9, 'supported', math.log(14.9 / 1.5) / math.log(10.0)), (15.0, 'supported', 1.0), (120.0, 'supported', 1.0)):      # 10 min 0.824
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == (expected, degree if degree is None else pytest.approx(degree)), minutes
    credit = []
    for minutes in (1.6, 2.0, 3.0, 5.0, 8.0, 12.0, 15.0):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        credit.append(sheet_status_and_degree(r, 'equilibrium')[1])
    assert credit == sorted(credit) and 0.0 < credit[0] < 0.05 and credit[-1] == pytest.approx(1.0)      # monotone, no step just above the zero end (1.6 min: log(1.6 / 1.5) / log(10) = 0.028)
    r['quantities']['incubation_time'] = point(1.0, 'min', 'i', ['s_inc'])
    assert set(judged(r, 'equilibrium')['support_refs']) == {'s_inc', 'span_exp_synthetic_fret_1'}      # the time and the constant that sets the scale
    r['quantities']['incubation_time'] = point(5.0, 'min', 'i', ['s_inc'])
    assert set(judged(r, 'equilibrium')['support_refs']) == {'s_inc', 'span_exp_synthetic_fret_1'}      # a supported answer names them too
    r['quantities']['kd'] = point(5000.0, 'nM', 'kd', ['s'])                                  # a 5 uM binder: T_FAST = 15 x 2 / 5000 = 0.006 min (0.36 s): one minute is full
    r['quantities']['incubation_time'] = point(1.0, 'min', 'i', ['s'])
    assert sheet_status_and_degree(r, 'equilibrium') == ('supported', pytest.approx(1.0))
    r['quantities']['kd'] = point(0.2, 'nM', 'kd', ['s'])                                     # a 200 pM binder: T_FAST = 15 x 2 / 0.2 = 150 min, T_SLOW = 1500 min
    for minutes, expected, degree in ((120.0, 'conflicting', None), (149.0, 'conflicting', None), (150.0, 'conflicting', None), (300.0, 'supported', math.log(2.0) / math.log(10.0)), (1500.0, 'supported', 1.0), (3000.0, 'supported', 1.0)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == (expected, degree if degree is None else pytest.approx(degree)), minutes
    r['quantities']['kd'] = point(0.01, 'nM', 'kd', ['s'])                                    # a 10 pM binder: T_FAST = 3000 min (50 h), T_SLOW = 30000 min
    for minutes, expected, degree in ((20.0, 'conflicting', None), (1440.0, 'conflicting', None), (6000.0, 'supported', math.log(2.0) / math.log(10.0)), (30000.0, 'supported', 1.0)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == (expected, degree if degree is None else pytest.approx(degree)), minutes
    r['quantities']['kd'] = point(0.2, 'nM', 'kd', ['s'])
    assert MIN_INCUBATION_MIN * EQUILIBRATION_REFERENCE_NM / 2.0 == 15.0                     # the researched 15 minutes is the time at the reference constant
    for name in ('kd', 'ki', 'ec50', 'ic50'):
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
    r['quantities']['incubation_time'] = point(0.1, 'min', 'i', ['s'])
    assert sheet_status_and_degree(r, 'equilibrium') == ('unknown', None)                     # no constant, no scale: the time alone is not a conflict
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported'                                  # the stated fact is the grader's, whatever the time


def test_the_sheet_judges_the_replicate_count_gradually_below_min_replicates():
    r = synthetic_record()
    for count, independent, expected, degree in ((3, 'yes', 'supported', None), (10, 'yes', 'supported', None), (2, 'yes', 'supported', math.sqrt(2 / 3)), (1, 'yes', 'supported', math.sqrt(1 / 3)),
                                                 (2, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None)):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert sheet_status_and_degree(r, 'replicates') == (expected, pytest.approx(degree) if degree is not None else None), (count, independent)
    r['facts']['independent_titrations'] = fact('no', ['s'])
    assert judged(r, 'replicates')['status'] == 'conflicting'                                 # stated as not independent: the paper's own fact against the standard


def test_the_replicate_curve_is_monotone_bounded_and_has_no_step_at_min_replicates():
    r = synthetic_record()
    credit = []
    for count in range(1, 8):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        status, degree = sheet_status_and_degree(r, 'replicates')
        assert status == 'supported', count
        credit.append(1.0 if degree is None else degree)
        assert 0.0 < credit[-1] <= 1.0, count
    assert credit == sorted(credit)                                                           # more independent titrations never lower the credit
    assert credit[MIN_REPLICATES - 1] == 1.0 and 0.75 < credit[MIN_REPLICATES - 2] < 1.0       # just below the researched three: partial, not 0
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert interpretation(r, 'sampling_basis') == {'status': 'supported', 'support_refs': interpretation(r, 'sampling_basis')['support_refs'], 'degree': pytest.approx(math.sqrt(2 / 3))}      # it travels into the sheet criterion


def test_the_sheet_judges_the_fold_gap_of_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM

    def ki(nm):
        return lambda record: record['quantities'].update(ki=point(nm, 'nM', 'k', ['s']))
    # on the log of the fold: a fold of sqrt(30) (the geometric middle of 3 and 10) gives 0.5; a fold of 6.5 gives log(10 / 6.5) / log(10 / 3) = 0.358
    check_scale(r, 'direct_vs_competition', ((ki(40.0), 'supported', 1.0), (ki(60.0), 'supported', 1.0), (ki(20.0 * math.sqrt(30.0)), 'supported', 0.5), (ki(130.0), 'supported', math.log(10 / 6.5) / math.log(10 / 3)),
                                             (ki(10.0), 'supported', 1.0), (ki(200.0), 'conflicting', None), (ki(2.0), 'conflicting', None)))
    credit = []
    for fold in (1.0, 2.0, 3.0, 3.1, 4.0, 6.0, 9.0, 9.9):
        r['quantities']['ki'] = point(20.0 * fold, 'nM', 'k', ['s'])
        status, degree = sheet_status_and_degree(r, 'direct_vs_competition')
        assert status == 'supported' and 0.0 < degree <= 1.0, fold
        credit.append(degree)
    assert credit == sorted(credit, reverse=True) and 0.95 < credit[3] < 1.0                # a larger gap never raises the degree; just past 3-fold is partial, not a step


def test_a_degree_of_a_member_travels_into_its_sheet_criterion_and_the_weakest_member_counts():
    r = synthetic_record()
    r['quantities']['ratio_maximum'] = point(0.6, 'ratio', 's', ['s'])                        # fold 1.5: 0.5, with time_gating at 1.0 in the same sheet criterion
    r['quantities']['ki'] = point(20.0 * math.sqrt(30.0), 'nM', 'k', ['s'])                   # fold gap sqrt(30): 0.5 on the log scale, in another sheet criterion
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


# ---- the grader gaps of the 2026-11-21 range review: Z' factor, donor lanthanide, series format, koff ----

def test_a_stated_z_prime_is_judged_in_addition_to_the_fold_gradually():
    r = synthetic_record()                                                                    # fold 4: full on its own
    def z(value):
        return lambda record: record['quantities'].update(z_prime=point(value, 'ratio', 'z', ['s_z']))
    check_scale(r, 'assay_window', ((z(0.72), 'supported', 1.0), (z(0.5), 'supported', 1.0), (z(0.25), 'supported', 0.5), (z(0.45), 'supported', 0.9), (z(0.0), 'conflicting', None)))
    r['quantities']['z_prime'] = point(0.25, 'ratio', 'z', ['s_z'])
    r['quantities']['ratio_maximum'] = point(0.6, 'ratio', 's', ['s'])                       # fold 1.5 (degree 0.5) with Z' 0.25 (degree 0.5)
    assert sheet_status_and_degree(r, 'assay_window') == ('supported', pytest.approx(0.5))
    r['quantities']['ratio_maximum'] = point(0.5, 'ratio', 's', ['s'])                       # fold 1.25: the weaker of the two
    assert sheet_status_and_degree(r, 'assay_window') == ('supported', pytest.approx(0.25))
    for name in ('ratio_minimum', 'ratio_maximum'):
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
    graded = grade_fret(r)                                                                    # a Z' with no ratio ends is judged alone
    assert graded['native']['ratio_fold'] is None and graded['native']['z_prime'] == 0.25 and graded['native']['window_refs'] == ['s_z']
    assert sheet_status_and_degree(r, 'assay_window') == ('supported', pytest.approx(0.5))
    r['quantities']['z_prime'] = {**r['quantities']['z_prime'], 'status': 'unavailable', 'value': None}
    assert grade_fret(r)['reasons']['assay_window'] == 'minimum_or_maximum_missing' and sheet_status_and_degree(r, 'assay_window') == ('unknown', None)


def test_the_integration_window_is_judged_against_the_named_lanthanides_lifetime():
    r = synthetic_record()
    r['quantities']['delay_time'] = point(100.0, 'us', 'd', ['s'])
    r['quantities']['integration_time'] = point(100.0, 'us', 'w', ['s'])
    assert sheet_status_and_degree(r, 'time_gating') == ('supported', pytest.approx(1.0))     # no lanthanide named: the reference lifetime
    r['donor_lanthanide'] = 'terbium'                                                         # lifetime 2 ms: a 100 us window collects half the photons
    assert sheet_status_and_degree(r, 'time_gating') == ('supported', pytest.approx(math.sqrt(0.5)))
    r['donor_lanthanide'] = 'europium'                                                        # lifetime 0.6 ms: the same window is enough
    assert sheet_status_and_degree(r, 'time_gating') == ('supported', pytest.approx(1.0))
    r['donor_lanthanide'] = 'other'
    assert sheet_status_and_degree(r, 'time_gating') == ('supported', pytest.approx(1.0))
    credit = []
    r['donor_lanthanide'] = 'terbium'
    for window in (10.0, 50.0, 100.0, 150.0, 199.0, 200.0, 400.0):
        r['quantities']['integration_time'] = point(window, 'us', 'w', ['s'])
        status, degree = sheet_status_and_degree(r, 'time_gating')
        assert status == 'supported' and 0.0 < degree <= 1.0
        credit.append(degree)
    assert credit == sorted(credit) and credit[-3] > 0.99 and credit[-2] == pytest.approx(1.0)      # monotone, no step at the terbium full-credit window of 200 us


def test_the_stated_series_format_picks_the_curves_midpoint_before_the_assay_format():
    r = synthetic_record()                                                                    # KD 20, Ki 40, IC50 80 nM; the experiment reports both formats, assay_format direct_titration
    r['concentration_series']['value'] = [16.0, 24.0, 40.0, 60.0, 100.0, 160.0, 250.0, 400.0]
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(1.5 * 0.2 / 1.8))      # not stated: the assay format (direct) gives the KD
    r['series_format'] = 'competition'                                                        # the listed series is the competitor series: against the IC50 80 nM
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(44 / 54))
    r['assay_format'] = 'competition'
    r['series_format'] = 'direct_titration'                                                    # stated, and the assay format says the opposite: the stated series wins (the KD)
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(1.5 * 0.2 / 1.8))
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    r['quantities']['ec50'] = point(30.0, 'nM', 'e', ['s_ec50'])                              # a direct series without a KD: against its EC50 30 nM
    verdict = judged(r, 'concentration_series')
    assert verdict['status'] == 'supported' and 's_ec50' in verdict['support_refs'] and verdict['degree'] > 0.0


def test_a_stated_koff_gives_the_equilibrium_a_degree_from_the_fraction_of_the_approach_reached():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['quantities']['koff'] = point(0.0025, 'per_s', 'k', ['s_koff'])
    half_life = math.log(2) / 0.0025 / 60                                                     # minutes
    assert not (half_life < 4.6 or half_life > 4.7)
    for half_lives, expected, degree in ((0.5, 'conflicting', None), (1.0, 'conflicting', None), (1.2, 'supported', (1 - 2 ** -1.2 - 0.5) / (1 - 2 ** -5 - 0.5)), (3.0, 'supported', 0.8), (5.0, 'supported', 1.0), (12.0, 'supported', 1.0)):
        r['quantities']['incubation_time'] = point(half_lives * half_life, 'min', 'i', ['s_inc'])
        status, got = sheet_status_and_degree(r, 'equilibrium')
        assert status == expected, half_lives
        if degree is not None:
            assert got == pytest.approx(degree), half_lives
    status, got = sheet_status_and_degree(r, 'equilibrium')
    assert set(judged(r, 'equilibrium')['support_refs']) == {'s_inc', 's_koff'}              # the time and the koff that sets the scale
    credit = []
    for half_lives in (1.0, 1.5, 2.0, 3.0, 4.0, 4.9, 5.0, 6.0):
        r['quantities']['incubation_time'] = point(half_lives * half_life, 'min', 'i', ['s'])
        credit.append(judged(r, 'equilibrium').get('degree', 0.0))
    assert credit == sorted(credit) and 0.9 < credit[5] < 1.0                                # monotone, no step just below five half-lives
    r['quantities']['kd'] = point(0.2, 'nM', 'kd', ['s'])                                     # the koff replaces the constant's scale: 120 min is enough whatever the KD
    r['quantities']['incubation_time'] = point(120.0, 'min', 'i', ['s'])
    assert sheet_status_and_degree(r, 'equilibrium') == ('supported', pytest.approx(1.0))
    r['quantities']['incubation_time'] = {**r['quantities']['incubation_time'], 'status': 'unavailable', 'value': None}
    assert sheet_status_and_degree(r, 'equilibrium') == ('unknown', None)                    # a koff without an incubation time shows nothing
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported'                                 # the stated fact stays the grader's


def test_the_equilibrium_quote_support_counts_the_koff_and_the_constants():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['quantities']['koff'] = point(0.0025, 'per_s', 'k', ['s_koff'], support='implied')
    r['quantities']['incubation_time'] = point(60.0, 'min', 'i', ['s_inc'])
    assert 'implied' in grade_fret(r)['native']['support']['equilibrium']
    assert interpretation(r, 'binding_regime')['status'] in ('supported', 'unknown')


def test_the_new_constants_have_their_researched_ends_in_order():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_fret_converter as c
    assert c.Z_PRIME_MIN == 0.5 and c.Z_PRIME_ZERO == 0.0 and c.APPROACH_FULL_HALF_LIVES == 5.0 and c.APPROACH_ZERO_HALF_LIVES == 1.0
    assert c.DONOR_LIFETIME_US['terbium'] > c.REFERENCE_LIFETIME_US > c.DONOR_LIFETIME_US['europium']
