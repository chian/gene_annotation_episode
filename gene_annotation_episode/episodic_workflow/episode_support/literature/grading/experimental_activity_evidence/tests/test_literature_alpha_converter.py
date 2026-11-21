"""AlphaScreen converter: the sheet's effect and variance, the criteria mapping and the null reasons, with the arithmetic worked by hand."""
import math
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, EQUILIBRATION_REFERENCE_NM, FAST_ASSOCIATION_RATE_PER_M_S, FIT_FREE_PARAMETERS, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR,
    MIN_CONCENTRATIONS, MIN_INCUBATION_MIN, MIN_REPLICATES, MIN_SIGNAL_OVER_BACKGROUND, MIN_Z_PRIME, SLOW_ASSOCIATION_RATE_PER_M_S, SIGNAL_WINDOW_ZERO_AGREEMENT, Z_PRIME_ZERO_AGREEMENT, _criterion, convert_alpha)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_grader import CRITERIA, grade_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.alpha_cases import real_record, sparse_record, synthetic_record


def convert(record):
    return convert_alpha(grade_alpha(record))


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 15


def test_the_apparent_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 20.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['alpha_kd:exp_synthetic_alpha_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == 4.0 and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 2 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(20.0) and cells['effect_variance']['value'] == pytest.approx(4.0) and cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(
        ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'), 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_titrant_a', 'immobilized_preparation_ref': 'prep_fixed_a', 'surface_ref': None, 'dataset_ref': 'dataset_alpha_1'}
    assert converted['experiment_type'] == 'alphascreen' and converted['extraction']['assay_type'] == 'ligand_binding'
    assert converted['null_components']['recovery'] == 'an_alphascreen_has_no_matrix_recovery_measurement'


def test_without_a_kd_the_ki_is_the_effect_with_its_own_spread():
    record = synthetic_record()
    missing(record, 'kd')
    converted = convert(record)
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 30.0 and effect['measurement_keys'] == ['alpha_ki:exp_synthetic_alpha_1'] and effect['native_component'] == 'ki'
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(9.0)      # 1.5 x 2 = 3 nM squared
    assert converted['extraction']['quantities']['effect_variance']['native_component'] == 'ki_spread'


def test_an_ec50_or_an_ic50_alone_is_not_a_binding_constant_and_carries_no_effect():
    record = synthetic_record()
    for name in ('kd', 'ki'):
        missing(record, name)
    converted = convert(record)                                                  # the EC50 (28 nM) and the IC50 (45 nM) are given
    assert converted['extraction']['quantities']['effect'] is None and converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'only_a_half_maximal_concentration_given_not_a_binding_constant'
    assert converted['null_components']['effect_variance'] == 'no_effect_to_carry_a_variance'
    missing(record, 'ec50')
    assert convert(record)['null_components']['effect'] == 'only_a_half_maximal_concentration_given_not_a_binding_constant'      # the IC50 alone
    missing(record, 'ic50')
    assert convert(record)['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'


def test_the_kind_of_the_spread_decides_whether_a_variance_exists():
    record = synthetic_record()
    record['spread_kind'] = 'standard_deviation'                                 # sd 2 over 3 independent experiments: 4 / 3
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4 / 3)
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # two independent experiments: supported with partial credit, so sd^2 / 2
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4 / 2)
    record['facts']['independent_experiments'] = fact('unknown')                 # the independence not stated: the replicates are unknown, no variance
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance'] is None and converted['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    record['spread_kind'] = 'confidence_interval'
    assert convert(record)['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    record['spread_kind'] = None
    assert convert(record)['null_components']['effect_variance'] == 'spread_kind_not_stated'
    record['spread_kind'] = 'standard_error'
    missing(record, 'kd_spread')
    assert convert(record)['null_components']['effect_variance'] == 'kd_spread_not_given'
    record['quantities']['kd_spread'] = point(0.002, 'uM', 's', ['s'])           # 2 nM
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4.0)


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['avidity_excluded'] = fact('no', ['s'])
    record['quantities']['signal_to_background'] = point(1.0, 'ratio', 'm', ['s'])        # no window at all
    record['facts']['hook_effect_handled'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_SIGNAL_OVER_BACKGROUND, SIGNAL_WINDOW_ZERO_AGREEMENT, MIN_Z_PRIME, Z_PRIME_ZERO_AGREEMENT, MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (10.0, 1.0, 0.5, 0.0, 8, 0.2, 1.0, 10.0, 1.0)
    assert (MIN_INCUBATION_MIN, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (30.0, 3, 3.0, 10.0)
    assert FIT_FREE_PARAMETERS == 4                                              # the zero end of the count curve: the free parameters of the four-parameter fit
    assert (FAST_ASSOCIATION_RATE_PER_M_S, SLOW_ASSOCIATION_RATE_PER_M_S) == (1e6, 1e5)      # the two ends of the incubation curve: T_SLOW = 10 x T_FAST
    assert EQUILIBRATION_REFERENCE_NM == 1.0                                     # the constant at which MIN_INCUBATION_MIN is five half-lives of the approach


def test_a_degree_travels_with_the_sheet_criterion_and_is_the_smallest_of_its_members():
    record = synthetic_record()
    record['quantities']['signal_to_background'] = point(10 ** 0.5, 'ratio', 'm', ['s'])  # halfway from 1 up to 10 on the log scale: a degree of 0.5
    record['quantities']['z_prime'] = point(0.4, 'ratio', 'z', ['s'])                      # 0.4 of 0.5: a degree of 0.8; the smaller one is kept
    converted = convert(record)
    interpretation = converted['extraction']['interpretations']['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    assert converted['sheet']['interpretations']['calibration_applicability']['degree'] == interpretation['degree']
    record['quantities']['ki'] = point(120.0, 'nM', 'k', ['s'])                            # 6 fold from the KD: log(10 / 6) / log(10 / 3) (the series spans the KD fully)
    interpretation = convert(record)['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(math.log(10 / 6) / math.log(10 / 3))
    assert 'degree' not in convert(record)['extraction']['interpretations']['binding_controls'] and 'degree' not in convert(record)['extraction']['interpretations']['sampling_basis']


def test_a_count_just_below_its_researched_value_gives_partial_credit_on_the_sheet_not_a_conflict():
    record = synthetic_record()
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                # two independent experiments of the researched three
    interpretation = convert(record)['extraction']['interpretations']['sampling_basis']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(math.sqrt(2 / 3))
    record = synthetic_record()
    record['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 200.0]   # seven points of the researched eight, the span full
    interpretation = convert(record)['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.75)
    assert convert(record)['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.75)


def _member(record, name):
    return _criterion(grade_alpha(record), name)


def _degree_of(verdict):
    """A member verdict as one ordered number: conflicting below every supported degree (-1), a supported degree as it is."""
    return -1.0 if verdict['status'] == 'conflicting' else verdict['degree']


def _with_series(lowest_over_kd, highest_over_kd, count=12):
    record = synthetic_record()                                                            # KD 20 nM
    ratio = (highest_over_kd / lowest_over_kd) ** (1 / (count - 1))
    record['concentration_series']['value'] = [20.0 * lowest_over_kd * ratio ** step for step in range(count - 1)] + [20.0 * highest_over_kd]      # the ends exact
    return record


def test_a_short_series_is_low_partial_credit_never_conflicting_and_more_points_never_lower_it():
    degrees = []
    for count in (2, 3, 4, 5, 6, 7, 8, 9, 12):
        verdict = _member(_with_series(0.2, 10.0, count), 'concentration_series')
        assert verdict['status'] == 'supported'                                            # never conflicting for a count, however short
        degrees.append(verdict['degree'])
    assert degrees == sorted(degrees) and degrees[:3] == [0.0, 0.0, 0.0] and degrees[-2:] == [1.0, 1.0]
    assert degrees[3] == pytest.approx(1 / (MIN_CONCENTRATIONS - FIT_FREE_PARAMETERS))     # one point past the free parameters: partial credit, no step
    record = _with_series(0.2, 10.0, 4)
    assert _interpretations(record)['binding_regime']['status'] == 'supported' and _interpretations(record)['binding_regime']['degree'] == 0.0


def test_the_series_ends_are_judged_on_the_occupancy_they_reach_and_are_monotone():
    high = _member(_with_series(0.05, 5.0), 'concentration_series')                        # 5x: (5/6 - 1/2) / (10/11 - 1/2)
    assert high['status'] == 'supported' and high['degree'] == pytest.approx((5 / 6 - 0.5) / (10 / 11 - 0.5))
    low = _member(_with_series(0.5, 100.0), 'concentration_series')                        # 0.5x: (1/2 - 1/3) / (1/2 - 1/6) = 0.5
    assert low['status'] == 'supported' and low['degree'] == pytest.approx(0.5)
    highs = [_degree_of(_member(_with_series(0.05, h), 'concentration_series')) for h in (0.5, 1.0, 1.5, 2.0, 5.0, 9.0, 10.0, 50.0)]
    assert highs == sorted(highs) and highs[:2] == [-1.0, -1.0] and 0 < highs[2] < highs[5] < 1.0 == highs[6]
    lows = [_degree_of(_member(_with_series(lo, 100.0), 'concentration_series')) for lo in (0.01, 0.2, 0.21, 0.5, 0.9, 1.0, 2.0)]
    assert lows == sorted(lows, reverse=True) and lows[:2] == [1.0, 1.0] and 0.9 < lows[2] < 1.0 and lows[-2:] == [-1.0, -1.0]


def test_the_signal_window_rises_with_the_log_of_the_ratio_with_no_step_at_ten():
    def window(ratio):
        record = synthetic_record()
        record['quantities']['signal_to_background'] = point(ratio, 'ratio', 'm', ['s'])
        return _member(record, 'signal_window')
    assert window(1.0)['status'] == 'conflicting' and window(0.8)['status'] == 'conflicting'
    assert window(2.0)['degree'] == pytest.approx(math.log(2) / math.log(10)) and window(10.0)['degree'] == 1.0 == window(500.0)['degree']
    assert 0.95 < window(9.0)['degree'] < 1.0                                              # just below the researched value: partial credit, no step
    degrees = [window(r)['degree'] for r in (1.1, 1.5, 2.0, 3.0, 5.0, 9.0, 10.0, 40.0)]
    assert degrees == sorted(degrees) and all(0 < d <= 1 for d in degrees)


def test_z_prime_is_linear_and_monotone_between_zero_and_its_researched_value():
    def quality(z):
        record = synthetic_record()
        record['quantities']['z_prime'] = point(z, 'ratio', 'z', ['s'])
        return _member(record, 'assay_quality')
    assert quality(0.0)['status'] == 'conflicting' and quality(0.25)['degree'] == pytest.approx(0.5) and quality(0.49)['degree'] == pytest.approx(0.98)
    degrees = [quality(z)['degree'] for z in (0.05, 0.2, 0.4, 0.5, 0.9)]
    assert degrees == sorted(degrees) and degrees[-2:] == [1.0, 1.0]


def test_the_kd_and_ki_gap_falls_with_the_log_of_the_fold():
    def agreement(ki):
        record = synthetic_record()                                                        # KD 20 nM
        record['quantities']['ki'] = point(ki, 'nM', 'k', ['s'])
        return _member(record, 'direct_vs_competition')
    assert agreement(60.0)['degree'] == pytest.approx(1.0) and agreement(200.0)['status'] == 'conflicting'
    assert agreement(80.0)['degree'] == pytest.approx(math.log(10 / 4) / math.log(10 / 3))
    assert agreement(5.0)['degree'] == agreement(80.0)['degree']                           # the fold is symmetric: a Ki 4 fold below the KD is the same gap
    degrees = [_degree_of(agreement(ki)) for ki in (20.0, 60.0, 65.0, 100.0, 150.0, 199.0, 200.0, 400.0)]
    assert degrees == sorted(degrees, reverse=True) and 0.9 < degrees[2] < 1.0


def test_the_incubation_is_a_curve_on_the_log_scale_of_the_association_rate():
    def equilibrium(minutes, kd_nm):
        record = synthetic_record()
        record['facts']['equilibrium_reached'] = fact('unknown')
        record['quantities']['incubation_time'] = point(minutes, 'min', 'inc', ['inc_span'])
        missing(record, 'bead_incubation_time')                                              # the time together is the incubation alone here
        record['quantities']['kd'] = point(kd_nm, 'nM', 'kd', ['kd_span'])
        return _member(record, 'equilibrium')
    # 1 nM: T_FAST = 30 x 1 / 1 = 30 min, T_SLOW = 300 min
    assert equilibrium(20.0, 1.0)['status'] == 'conflicting' and equilibrium(30.0, 1.0)['status'] == 'conflicting'       # at and below the fast limit: the zero end
    assert equilibrium(60.0, 1.0)['degree'] == pytest.approx(math.log(2) / math.log(10))    # 0.30103
    assert equilibrium(100.0, 1.0)['degree'] == pytest.approx(math.log(100 / 30) / math.log(10))   # 0.5229
    assert equilibrium(300.0, 1.0)['degree'] == pytest.approx(1.0) and equilibrium(900.0, 1.0)['degree'] == 1.0
    assert equilibrium(30.001, 1.0)['status'] == 'supported' and 0 < equilibrium(30.001, 1.0)['degree'] < 0.001      # no step above the fast limit
    # a micromolar binder (1000 nM): T_FAST 0.03 min, T_SLOW 0.3 min: a 5-minute read is full (was unknown)
    assert equilibrium(5.0, 1000.0)['degree'] == 1.0 and equilibrium(0.1, 1000.0)['degree'] == pytest.approx(math.log(0.1 / 0.03) / math.log(10)) and equilibrium(0.02, 1000.0)['status'] == 'conflicting'
    # a 100 pM binder: T_FAST 300 min, T_SLOW 3000 min
    assert equilibrium(60.0, 0.1)['status'] == 'conflicting' and equilibrium(3000.0, 0.1)['degree'] == pytest.approx(1.0)
    assert equilibrium(1000.0, 0.1)['degree'] == pytest.approx(math.log(1000 / 300) / math.log(10))      # 0.5229
    # a 10 pM binder: T_FAST 3000 min (50 h), T_SLOW 30000 min: an hour is conflicting, 10000 minutes 0.5229
    assert equilibrium(60.0, 0.01)['status'] == 'conflicting' and equilibrium(10000.0, 0.01)['degree'] == pytest.approx(math.log(10000 / 3000) / math.log(10))
    degrees = [_degree_of(equilibrium(minutes, 1.0)) for minutes in (5.0, 30.0, 31.0, 60.0, 120.0, 250.0, 300.0, 1000.0)]
    assert degrees == sorted(degrees) and all(d <= 1 for d in degrees)
    verdict = equilibrium(60.0, 1.0)
    assert verdict['support_refs'] == ['inc_span', 'kd_span']                              # the incubation and the constant
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    record['quantities']['incubation_time'] = point(1.0, 'min', 'inc', ['s'])
    for name in ('kd', 'ki', 'ec50', 'ic50'):
        missing(record, name)
    assert _member(record, 'equilibrium')['status'] == 'unknown'                           # no constant: no scale, and time alone is not opposition, also below any floor


def test_the_bead_step_counts_towards_the_time_the_partners_are_together():
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    record['quantities']['kd'] = point(0.5, 'nM', 'kd', ['s'])                              # T_FAST = 60 minutes together, T_SLOW = 600
    record['quantities']['incubation_time'] = point(30.0, 'min', 'inc', ['s'])
    record['quantities']['bead_incubation_time'] = point(45.0, 'min', 'bead', ['s'])       # 75 together: ln(1.25) / ln(10)
    assert _member(record, 'equilibrium')['degree'] == pytest.approx(math.log(1.25) / math.log(10))
    record['quantities']['bead_incubation_time'] = point(25.0, 'min', 'bead', ['s'])       # 55 together
    assert _member(record, 'equilibrium')['status'] == 'conflicting'


def test_a_partner_over_the_constant_is_gradual_when_the_fact_is_not_stated():
    def depletion(labelled_nm, fact_answer='unknown'):
        record = synthetic_record()                                                          # KD 20 nM, fixed-partner titration
        record['facts']['partner_concentration_below_kd'] = fact(fact_answer, ['s'] if fact_answer != 'unknown' else [])
        missing(record, 'tagged_partner_concentration')
        record['quantities']['labelled_partner_concentration'] = point(labelled_nm, 'nM', 'p', ['s'])
        return _member(record, 'partner_depletion')
    assert depletion(10.0)['degree'] == 1.0 and depletion(20.0)['degree'] == 1.0            # at and below the constant: full
    assert depletion(40.0)['degree'] == pytest.approx(math.log(6 / 2) / math.log(4))        # twice the constant: bias 1 + 2 / 2 = 2, log(6 / 2) / log(6 / 1.5) = 0.7925
    assert depletion(100.0)['degree'] == pytest.approx(math.log(6 / 3.5) / math.log(4))     # five times: bias 3.5, 0.3888
    assert depletion(100.0)['status'] == 'supported' and 0 < depletion(100.0)['degree'] < depletion(40.0)['degree']   # no step at a few times the constant
    assert depletion(200.0)['status'] == 'conflicting' and 'degree' not in depletion(200.0)     # ten times: the number reports the partner
    degrees = [depletion(nm)['degree'] for nm in (1.0, 20.0, 30.0, 60.0, 120.0, 190.0)]
    assert degrees == sorted(degrees, reverse=True) and all(0 <= d <= 1 for d in degrees)
    assert depletion(200.0, 'yes')['status'] == 'supported' and 'degree' not in depletion(200.0, 'yes')     # the stated fact decides
    assert depletion(1.0, 'no')['status'] == 'conflicting'


def _interpretations(record):
    return convert(record)['extraction']['interpretations']


def test_a_criterion_resting_on_a_field_with_thin_support_gets_the_support_degree():
    assert 'degree' not in _interpretations(synthetic_record())['binding_controls']       # all direct: unchanged, no degree where there was none
    record = synthetic_record()
    record['facts']['counter_screen_done'] = fact('yes', ['s'], 'implied')
    interpretation = _interpretations(record)['binding_controls']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.7)
    record['facts']['avidity_excluded'] = fact('yes', ['s'], 'about_something_else')       # the weakest member field decides
    assert _interpretations(record)['binding_controls']['degree'] == pytest.approx(0.3)
    assert 'degree' not in _interpretations(record)['sampling_basis']                      # other sheet criteria are untouched


def test_the_support_degree_multiplies_a_degree_the_sheet_already_has():
    record = synthetic_record()
    record['quantities']['signal_to_background'] = point(10 ** 0.5, 'ratio', 'm', ['s'])        # a degree of 0.5
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5)
    record['quantities']['signal_to_background'] = point(10 ** 0.5, 'ratio', 'm', ['s'], support='implied')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5 * 0.7)
    record['quantities']['signal_to_background'] = point(10 ** 0.5, 'ratio', 'm', ['s'], support='about_something_else')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5 * 0.3)
    record['quantities']['signal_to_background'] = point(10 ** 0.5, 'ratio', 'm', ['s'], support='direct')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5)      # direct: unchanged


def test_a_choice_field_and_the_variance_rest_on_their_support_too():
    record = synthetic_record()
    record['choice_support']['fit_model'] = 'implied'
    assert _interpretations(record)['binding_parameter_definition']['degree'] == pytest.approx(0.7)
    record = synthetic_record()
    record['quantities']['kd_spread'] = point(2.0, 'nM', 'sp', ['s'], support='implied')
    assert _interpretations(record)['variance_correspondence']['degree'] == pytest.approx(0.7)
    record['choice_support']['spread_kind'] = 'about_something_else'
    assert _interpretations(record)['variance_correspondence']['degree'] == pytest.approx(0.3)


def test_support_never_changes_a_status_and_a_conflicting_or_unknown_criterion_keeps_no_degree():
    record = synthetic_record()
    record['facts']['counter_screen_done'] = fact('no', ['s'], 'about_something_else')
    interpretation = _interpretations(record)['binding_controls']
    assert interpretation['status'] == 'conflicting' and 'degree' not in interpretation
    record['facts']['counter_screen_done'] = fact('unknown')
    interpretation = _interpretations(record)['binding_controls']
    assert interpretation['status'] == 'unknown' and 'degree' not in interpretation
    assert {item['status'] for item in _interpretations(synthetic_record()).values()} == {'supported'}


def test_a_not_applicable_member_is_dropped_and_an_all_not_applicable_sheet_criterion_is_not_selected():
    record = synthetic_record()
    record['facts']['single_estimate_method'] = fact('yes', ['s'])
    missing(record, 'ki')
    for name in ('nonspecific_binding_checked', 'capture_does_not_alter_binding', 'avidity_excluded', 'counter_screen_done', 'light_protected'):
        record['facts'][name] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert 'binding_controls' not in interpretations and interpretations['binding_regime']['status'] == 'supported'


def test_the_sparse_record_gives_only_the_effect_and_unknown_interpretations():
    converted = convert(sparse_record())
    assert converted['sheet']['cells']['measured_effect']['value'] == pytest.approx(20.0)
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {item['status'] for item in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_the_real_cross_titration_record_has_no_effect_and_the_hook_effect_is_the_only_decided_member():
    converted = convert(real_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'unknown'
    assert interpretations['binding_regime']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown'     # the hook effect is one member of the regime, the rest is unknown
    assert 'sampling_basis' in interpretations and interpretations['sampling_basis']['status'] == 'unknown'
