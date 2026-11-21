"""Radioligand converter: the sheet's effect and variance, the criteria mapping and the null reasons, with the arithmetic worked by hand."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_radioligand_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import (
    CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_FACTOR, CRITERIA_MAP, HALF_LIVES_AT_MIN_INCUBATION, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MAX_HILL, MAX_HILL_ZERO_AGREEMENT,
    MAX_NONSPECIFIC_FRACTION, MAX_PERCENT_BOUND, MAX_RADIOLIGAND_OVER_KD, MIN_CONCENTRATIONS, MIN_HILL, MIN_HILL_ZERO_AGREEMENT, MIN_INCUBATION_MIN, MIN_NONSPECIFIC_EXCESS, MIN_REPLICATES,
    NONSPECIFIC_EXCESS_ZERO_AGREEMENT, NONSPECIFIC_FRACTION_ZERO_AGREEMENT, PERCENT_BOUND_ZERO_AGREEMENT, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT, SATURATION_FIT_PARAMETERS, SINGLE_EXPERIMENT, _criterion,
    convert_radioligand)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import CRITERIA, grade_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import WEIGHT_UNKNOWN_BY_CRITERION, WEIGHT_UNKNOWN_BY_TYPE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.radioligand_cases import real_record, sparse_record, synthetic_record


def convert(record):
    return convert_radioligand(grade_radioligand(record))


def _bias(percent):
    """The apparent over the true KD when the added radioligand is taken as free with this percent bound: 1 + f / (2 (1 - f)), worked by hand."""
    f = percent / 100.0
    return 1 + f / (2 * (1 - f))


DEPLETION_AT_30 = math.log(_bias(50) / _bias(30)) / math.log(_bias(50) / _bias(10))      # ln(1.5 / 1.2143) / ln(1.5 / 1.0556) = 0.601


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 15


def test_the_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 2.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['radioligand_kd:exp_synthetic_radioligand_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == pytest.approx(0.04) and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 0.2 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(2.0) and cells['effect_variance']['value'] == pytest.approx(0.04) and cells['effect_precision']['value'] == pytest.approx(25.0)
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(
        ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'), 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_radioligand_a', 'immobilized_preparation_ref': 'prep_receptor_a', 'surface_ref': None, 'dataset_ref': 'dataset_radioligand_1'}
    assert converted['experiment_type'] == 'radioligand' and converted['extraction']['assay_type'] == 'ligand_binding'
    assert converted['null_components']['recovery'] == 'a_radioligand_assay_has_no_matrix_recovery_measurement'


def test_without_a_kd_the_ki_is_the_effect_with_its_own_spread():
    record = synthetic_record()
    missing(record, 'kd')
    converted = convert(record)
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 5.0 and effect['measurement_keys'] == ['radioligand_ki:exp_synthetic_radioligand_1'] and effect['native_component'] == 'ki'
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(0.09)      # 1.5 x 0.2 = 0.3 nM squared
    assert converted['extraction']['quantities']['effect_variance']['native_component'] == 'ki_spread'


def test_an_ic50_alone_is_not_a_binding_constant_and_carries_no_effect():
    record = synthetic_record()
    for name in ('kd', 'ki'):
        missing(record, name)
    converted = convert(record)                                                  # the IC50 (7.5 nM) is given
    assert converted['extraction']['quantities']['effect'] is None and converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'only_a_half_maximal_concentration_given_not_a_binding_constant'
    assert converted['null_components']['effect_variance'] == 'no_effect_to_carry_a_variance'
    missing(record, 'ic50')
    assert convert(record)['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'


def test_the_kind_of_the_spread_decides_whether_a_variance_exists():
    record = synthetic_record()
    record['spread_kind'] = 'standard_deviation'                                 # sd 0.2 over 3 independent experiments: 0.04 / 3
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(0.04 / 3)
    assert converted['extraction']['interpretations']['variance_correspondence']['degree'] == 1.0      # the researched three: the full degree
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # two independent experiments: supported with sqrt(2 / 3), 0.04 / 2
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(0.02)
    assert converted['extraction']['interpretations']['variance_correspondence'] == {'status': 'supported', 'support_refs': ['span_exp_synthetic_radioligand_1', 's'], 'degree': pytest.approx(math.sqrt(2 / 3))}
    record['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])      # one experiment: the replicates are supported (sqrt(1 / 3)), but its sd is no spread between experiments: no variance
    converted = convert(record)
    assert converted['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(math.sqrt(1 / 3))
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance'] is None and converted['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    assert 'variance_correspondence' not in converted['extraction']['interpretations']
    record['spread_kind'] = 'confidence_interval'
    assert convert(record)['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    record['spread_kind'] = None
    assert convert(record)['null_components']['effect_variance'] == 'spread_kind_not_stated'
    record['spread_kind'] = 'standard_error'
    missing(record, 'kd_spread')
    assert convert(record)['null_components']['effect_variance'] == 'kd_spread_not_given'
    record['quantities']['kd_spread'] = point(0.0002, 'uM', 's', ['s'])          # 0.2 nM
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(0.04)
    assert 'degree' not in converted['extraction']['interpretations']['variance_correspondence']      # a standard error does not rest on the replicate count


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['filter_binding_checked'] = fact('no', ['s'])
    record['quantities']['percent_bound'] = point(60.0, 'percent', 'p', ['s'])            # beyond the zero-agreement limit of 50
    record['facts']['equilibrium_reached'] = fact('unknown')
    missing(record, 'incubation_time')                                                    # no time to judge either: unknown (a stated time would be judged)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MAX_PERCENT_BOUND, PERCENT_BOUND_ZERO_AGREEMENT, MAX_NONSPECIFIC_FRACTION, NONSPECIFIC_FRACTION_ZERO_AGREEMENT, MIN_NONSPECIFIC_EXCESS, NONSPECIFIC_EXCESS_ZERO_AGREEMENT) == (10.0, 50.0, 50.0, 90.0, 100.0, 1.0)
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, MAX_RADIOLIGAND_OVER_KD, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT) == (8, 0.25, 1.0, 5.0, 1.0, 1.0, 10.0)
    assert (MIN_INCUBATION_MIN, MIN_HILL, MIN_HILL_ZERO_AGREEMENT, MAX_HILL, MAX_HILL_ZERO_AGREEMENT, CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_FACTOR, MIN_REPLICATES) == (30.0, 0.8, 0.5, 1.2, 1.5, 1.5, 5.0, 3)
    assert (SATURATION_FIT_PARAMETERS, HALF_LIVES_AT_MIN_INCUBATION, SINGLE_EXPERIMENT) == (2, 5.0, 1)      # the ends of the curves of the three lone minimums


def test_a_degree_travels_with_the_sheet_criterion_and_is_the_smallest_of_its_members():
    record = synthetic_record()
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'])            # log-bias degree 0.601
    record['quantities']['nonspecific_fraction'] = point(58.0, 'percent', 'f', ['s'])      # ln(9 / (58 / 42)) / ln 9 = 0.853; the smaller one is kept
    converted = convert(record)
    interpretation = converted['extraction']['interpretations']['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(DEPLETION_AT_30)
    assert converted['sheet']['interpretations']['calibration_applicability']['degree'] == interpretation['degree']
    record['quantities']['hill_slope'] = point(0.65, 'ratio', 'h', ['s'])                 # a degree of 0.5 below one
    interpretation = convert(record)['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    assert convert(record)['extraction']['interpretations']['binding_controls']['degree'] == 1.0      # its one continuous member (the non-specific excess) is at full agreement
    assert convert(record)['extraction']['interpretations']['sampling_basis']['degree'] == 1.0        # three independent experiments: the full degree of the replicate curve


def _interpretations(record):
    return convert(record)['extraction']['interpretations']


def test_a_criterion_resting_on_a_field_with_thin_support_gets_the_support_degree():
    assert _interpretations(synthetic_record())['sampling_basis']['degree'] == 1.0         # all direct: unchanged
    record = synthetic_record()
    record['facts']['independent_experiments'] = fact('yes', ['s'], 'implied')
    interpretation = _interpretations(record)['sampling_basis']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.7)
    record['quantities']['replicate_count'] = point(3, 'count', 'r', ['s'], support='about_something_else')      # the weakest member field decides
    assert _interpretations(record)['sampling_basis']['degree'] == pytest.approx(0.3)
    assert _interpretations(synthetic_record())['sampling_basis']['degree'] == 1.0         # another record is untouched


def test_the_support_degree_multiplies_a_degree_the_sheet_already_has():
    record = synthetic_record()
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'])            # a degree of 0.601
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(DEPLETION_AT_30)
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'], support='implied')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(DEPLETION_AT_30 * 0.7)
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'], support='about_something_else')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(DEPLETION_AT_30 * 0.3)
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'], support='direct')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(DEPLETION_AT_30)      # direct: unchanged
    record = synthetic_record()
    record['quantities']['replicate_count'] = point(2, 'count', 'r', ['s'], support='implied')         # sqrt(2 / 3), then the support
    assert _interpretations(record)['sampling_basis']['degree'] == pytest.approx(math.sqrt(2 / 3) * 0.7)


def test_a_choice_field_and_the_variance_rest_on_their_support_too():
    record = synthetic_record()
    base = _interpretations(record)['binding_parameter_definition'].get('degree', 1.0)
    record['choice_support']['fit_model'] = 'implied'
    assert _interpretations(record)['binding_parameter_definition']['degree'] == pytest.approx(base * 0.7)
    record = synthetic_record()
    record['quantities']['kd_spread'] = point(0.2, 'nM', 'sp', ['s'], support='implied')
    assert _interpretations(record)['variance_correspondence']['degree'] == pytest.approx(0.7)
    record['choice_support']['spread_kind'] = 'about_something_else'
    assert _interpretations(record)['variance_correspondence']['degree'] == pytest.approx(0.3)


def test_support_never_changes_a_status_and_a_conflicting_or_unknown_criterion_keeps_no_degree():
    record = synthetic_record()
    record['facts']['independent_experiments'] = fact('no', ['s'], 'about_something_else')
    interpretation = _interpretations(record)['sampling_basis']
    assert interpretation['status'] == 'conflicting' and 'degree' not in interpretation
    record['facts']['independent_experiments'] = fact('unknown')
    interpretation = _interpretations(record)['sampling_basis']
    assert interpretation['status'] == 'unknown' and 'degree' not in interpretation
    assert {item['status'] for item in _interpretations(synthetic_record()).values()} == {'supported'}


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    for name in ('nonspecific_binding_determined', 'radioligand_purity_checked', 'filter_binding_checked'):
        record['facts'][name] = fact('not_applicable')
    missing(record, 'nonspecific_excess')
    missing(record, 'nonspecific_ligand_concentration')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown'            # the excess is now unknown; the three facts are dropped
    record['quantities']['nonspecific_excess'] = point(500.0, 'ratio', 'e', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['support_refs'] == ['s']     # only the excess is left


def test_the_sparse_record_gives_only_the_effect_and_unknown_interpretations():
    converted = convert(sparse_record())
    assert converted['sheet']['cells']['measured_effect']['value'] == pytest.approx(2.0)
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {item['status'] for item in converted['extraction']['interpretations'].values()} == {'unknown'}


# The three lone minimums (MIN_CONCENTRATIONS, MIN_REPLICATES, MIN_INCUBATION_MIN) are curves, not steps: full at the researched value,
# partial credit just below it, never conflicting for a stated value, monotone, in [0, 1], and unknown when the value is not stated.

def _weight(verdict, sheet_criterion):
    """The row weight a verdict gives (OWNER_DECISION 4): a supported degree, 1.0 without one, 0 conflicting, the radioligand unknown weight of its sheet criterion unknown."""
    unknown = WEIGHT_UNKNOWN_BY_CRITERION['radioligand'].get(sheet_criterion, WEIGHT_UNKNOWN_BY_TYPE['radioligand'])
    return {'supported': verdict.get('degree', 1.0), 'conflicting': 0.0, 'unknown': unknown}[verdict['status']]


def test_no_unknown_weight_is_used_inside_a_degree():
    assert not hasattr(literature_radioligand_converter, 'WEIGHT_UNKNOWN') and not hasattr(literature_radioligand_converter, 'WEIGHT_UNKNOWN_BY_TYPE')


def _range_verdict(count):
    record = synthetic_record()                                                            # a span from 0.05 x to 25.6 x the KD: the span is at full agreement
    record['concentration_series'] = {**record['concentration_series'], 'status': 'unavailable', 'value': None}
    record['quantities']['titration_point_count'] = point(count, 'count', 'n', ['n'])
    return _criterion(grade_radioligand(record), 'radioligand_range')


def test_a_saturation_series_just_short_of_the_researched_count_gets_partial_credit():
    assert _range_verdict(MIN_CONCENTRATIONS)['degree'] == 1.0 and _range_verdict(12)['degree'] == 1.0
    just_below = _range_verdict(MIN_CONCENTRATIONS - 1)                                    # 7 points: (7 - 2) / (8 - 2) = 5 / 6, not a conflict
    assert just_below['status'] == 'supported' and just_below['degree'] == pytest.approx(5.0 / 6.0)
    assert set(just_below['support_refs']) == {'span_exp_synthetic_radioligand_1', 'n'}     # the lowered degree rests on the count too
    assert _range_verdict(4)['degree'] == pytest.approx(2.0 / 6.0)
    assert _range_verdict(3)['degree'] == pytest.approx(1.0 / 6.0)
    for count in (SATURATION_FIT_PARAMETERS, 1):                                           # the hyperbola passes through every point: no credit, but a short series is not evidence against
        assert _range_verdict(count) == {'status': 'supported', 'support_refs': ['span_exp_synthetic_radioligand_1', 'n'], 'degree': 0.0}
    weights = [_weight(_range_verdict(count), 'binding_regime') for count in range(1, 13)]
    assert weights == sorted(weights) and all(0.0 <= w <= 1.0 for w in weights)           # more concentrations never lower the degree


def _span_verdict(lowest_over_kd, highest_over_kd):
    record = synthetic_record()                                                            # KD 2 nM, ten concentrations: the count is at full agreement
    record['concentration_series'] = {**record['concentration_series'], 'status': 'unavailable', 'value': None}
    record['quantities']['radioligand_range_lowest'] = point(2.0 * lowest_over_kd, 'nM', 'l', ['s'])
    record['quantities']['radioligand_range_highest'] = point(2.0 * highest_over_kd, 'nM', 'h', ['s'])
    return _criterion(grade_radioligand(record), 'radioligand_range')


def test_the_span_of_the_series_is_judged_on_the_occupancy_its_ends_reach():
    assert _span_verdict(LOW_FACTOR, HIGH_FACTOR)['degree'] == 1.0 and _span_verdict(0.05, 25.6)['degree'] == 1.0
    assert _span_verdict(0.05, 3.0)['degree'] == pytest.approx((0.75 - 0.5) / (5 / 6 - 0.5))        # occupancy 3 / 4: 0.75, not the linear 0.5
    assert _span_verdict(0.05, 4.5)['degree'] == pytest.approx((4.5 / 5.5 - 0.5) / (5 / 6 - 0.5))    # 0.955: 4.5 x the KD covers nearly as much of the curve as 5 x
    assert _span_verdict(0.5, 25.6)['degree'] == pytest.approx((1 / 3 - 0.5) / (0.2 - 0.5))           # occupancy 1 / 3 at the foot: 0.556
    just_past = _span_verdict(0.05, HIGH_FACTOR - 0.1)
    assert just_past['status'] == 'supported' and 0.95 < just_past['degree'] < 1.0                     # no step at the researched end
    for low, high in ((LOW_ZERO_AGREEMENT_FACTOR, 25.6), (0.05, HIGH_ZERO_AGREEMENT_FACTOR)):          # half occupancy at an end: conflicting, as before
        assert _span_verdict(low, high)['status'] == 'conflicting'
    highs = [_weight(_span_verdict(0.05, high), 'binding_regime') for high in (1.0, 1.5, 2.0, 3.0, 4.0, 4.9, 5.0, 10.0)]
    lows = [_weight(_span_verdict(low, 25.6), 'binding_regime') for low in (1.0, 0.8, 0.5, 0.3, 0.25, 0.1)]
    assert highs == sorted(highs) and lows == sorted(lows) and all(0.0 <= w <= 1.0 for w in highs + lows)
    # the shape: a step of the high end near the researched value costs less than the same step near the KD
    assert _span_verdict(0.05, 5.0)['degree'] - _span_verdict(0.05, 4.0)['degree'] < _span_verdict(0.05, 2.0)['degree'] - _span_verdict(0.05, 1.01)['degree']


def test_the_count_and_the_span_of_the_series_combine_as_the_weakest():
    record = synthetic_record()
    record['concentration_series'] = {**record['concentration_series'], 'status': 'unavailable', 'value': None}
    record['quantities']['titration_point_count'] = point(5, 'count', 'n', ['s'])          # (5 - 2) / 6 = 0.5
    record['quantities']['radioligand_range_highest'] = point(9.0, 'nM', 'h', ['s'])       # 4.5 x the KD: occupancy degree 0.955
    assert _criterion(grade_radioligand(record), 'radioligand_range')['degree'] == pytest.approx(0.5)
    missing(record, 'radioligand_range_highest')                                           # the count is short but the span is not known: unknown, not 0
    assert _criterion(grade_radioligand(record), 'radioligand_range') == {'status': 'unknown', 'support_refs': []}


def _replicate_verdict(count, independent='yes'):
    record = synthetic_record()
    record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
    if independent != 'yes':                                                               # the synthetic record states yes on its own span
        record['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
    return _criterion(grade_radioligand(record), 'replicates')


def test_fewer_independent_experiments_get_the_precision_of_their_mean_and_never_conflict():
    assert _replicate_verdict(MIN_REPLICATES) == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_radioligand_1'], 'degree': 1.0}
    assert _replicate_verdict(6)['degree'] == 1.0
    assert _replicate_verdict(MIN_REPLICATES - 1) == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_radioligand_1'], 'degree': pytest.approx(math.sqrt(2 / 3))}   # 0.816
    assert _replicate_verdict(SINGLE_EXPERIMENT) == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_radioligand_1'], 'degree': pytest.approx(math.sqrt(1 / 3))}  # 0.577, not a conflict
    assert _replicate_verdict(2, 'unknown') == {'status': 'unknown', 'support_refs': []}   # the independence not stated: unknown, not 0
    assert _replicate_verdict(2, 'no')['status'] == 'conflicting'                          # the paper says the repeats were not independent: the grader's conflict
    weights = [_weight(_replicate_verdict(count), 'sampling_basis') for count in range(1, 7)]
    assert weights == sorted(weights) and all(0.0 <= w <= 1.0 for w in weights)
    record = synthetic_record()
    missing(record, 'replicate_count')                                                     # the count not stated: unknown
    assert _criterion(grade_radioligand(record), 'replicates')['status'] == 'unknown'
    assert _interpretations(record)['sampling_basis']['status'] == 'unknown'


def _incubation_verdict(minutes):
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['i'])
    return _criterion(grade_radioligand(record), 'equilibrium')


def test_an_incubation_follows_the_approach_to_equilibrium_full_from_the_researched_time():
    assert _incubation_verdict(MIN_INCUBATION_MIN) == {'status': 'supported', 'support_refs': ['i'], 'degree': 1.0}      # the researched time: full agreement
    assert _incubation_verdict(120.0) == {'status': 'supported', 'support_refs': ['i'], 'degree': 1.0}
    # 30 min stands for five half-lives (6 min each); one half-life reaches 1/2 of the equilibrium binding, four reach 15/16, five 31/32
    assert _incubation_verdict(6.0) == {'status': 'supported', 'support_refs': ['i'], 'degree': pytest.approx((1 / 2) / (31 / 32))}
    assert _incubation_verdict(24.0)['degree'] == pytest.approx((15 / 16) / (31 / 32))     # a little short loses little (0.968)
    just_below = _incubation_verdict(MIN_INCUBATION_MIN - 0.1)
    assert just_below['status'] == 'supported' and 0.99 < just_below['degree'] < 1.0       # no step at the researched value
    assert 0.0 < _incubation_verdict(0.5)['degree'] < 0.1                                  # very short: little weight, but not a conflict (the paper did not state 'no')
    weights = [_weight(_incubation_verdict(minutes), 'binding_regime') for minutes in (0.5, 1.0, 3.0, 6.0, 12.0, 20.0, 29.0, 29.9, 30.0, 60.0)]
    assert weights == sorted(weights) and all(0.0 <= w <= 1.0 for w in weights)
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    missing(record, 'incubation_time')                                                     # no time stated: unknown
    assert _criterion(grade_radioligand(record), 'equilibrium')['status'] == 'unknown'
    record['facts']['equilibrium_reached'] = fact('no', ['s'])                             # the paper itself says no: conflicting
    assert _criterion(grade_radioligand(record), 'equilibrium')['status'] == 'conflicting'


def _kd_incubation_verdict(kd, minutes):
    record = synthetic_record(kd=kd)
    record['facts']['equilibrium_reached'] = fact('unknown')
    record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['i'])
    return _criterion(grade_radioligand(record), 'equilibrium')


def test_the_no_koff_incubation_is_scaled_by_the_paper_own_kd_never_asking_less_than_30_min():
    # kd 0.1 nM: 10 times the 30 min = 300 min; 60 min is 5 x 60 / 300 = 1 half-life: 1/2 of the way, against 31/32 at five
    assert _kd_incubation_verdict(0.1, 60.0)['degree'] == pytest.approx(0.5 / (31 / 32))
    assert _kd_incubation_verdict(0.1, 60.0)['support_refs'] == ['i', 'span_exp_synthetic_radioligand_1']      # the degree rests on the KD: its refs join
    assert _kd_incubation_verdict(0.1, 300.0)['degree'] == pytest.approx(1.0)
    # kd 0.5 nM: 60 min needed; 30 min is 2.5 half-lives
    assert _kd_incubation_verdict(0.5, 30.0)['degree'] == pytest.approx((1 - 0.5 ** 2.5) / (31 / 32))
    # kd 1 nM and weaker: the 30 min as before, never less for a weaker constant
    for kd in (1.0, 2.0, 50.0):
        assert _kd_incubation_verdict(kd, 30.0)['degree'] == 1.0 and _kd_incubation_verdict(kd, 6.0)['degree'] == pytest.approx((1 / 2) / (31 / 32))
    assert _kd_incubation_verdict(50.0, 6.0)['support_refs'] == ['i']
    # monotone in the KD (a tighter constant never raises the degree) and gradual at the reference: no step
    degrees = [_kd_incubation_verdict(kd, 60.0)['degree'] for kd in (0.01, 0.1, 0.5, 0.9, 0.99, 1.0, 5.0)]
    assert degrees == sorted(degrees) and all(0.0 < d <= 1.0 for d in degrees)
    assert abs(_kd_incubation_verdict(0.99, 20.0)['degree'] - _kd_incubation_verdict(1.0, 20.0)['degree']) < 0.01
    # a stated koff keeps its own route (the KD is not used)
    record = synthetic_record(kd=0.1)
    record['facts']['equilibrium_reached'] = fact('unknown')
    record['quantities']['incubation_time'] = point(60.0, 'min', 'i', ['i'])
    record['quantities']['dissociation_rate'] = point(math.log(2) / 30, '1/min', 'k', ['k'])
    assert _criterion(grade_radioligand(record), 'equilibrium')['degree'] == pytest.approx(0.75 / (31 / 32))
    # no KD in the record (a Ki alone): the 30 min stands
    record = synthetic_record(kd=0.1)
    record['facts']['equilibrium_reached'] = fact('unknown')
    record['quantities']['incubation_time'] = point(30.0, 'min', 'i', ['i'])
    missing(record, 'kd')
    assert _criterion(grade_radioligand(record), 'equilibrium')['degree'] == 1.0


# The continuous comparisons: each falls on the scale its own error grows on. For every one: full at the researched value, partial just past it,
# conflicting at the zero-agreement end (a stated value against the standard), monotone and in [0, 1].

def _judged(name, criterion, value, unit='ratio'):
    record = synthetic_record()
    record['quantities'][name] = point(value, unit, 'x', ['s'])
    return _criterion(grade_radioligand(record), criterion)


def _check_curve(values, verdicts, full_at, sheet_criterion):
    """values ordered from best to worst; verdicts the matching verdicts; full_at the index of the researched value."""
    weights = [_weight(verdict, sheet_criterion) for verdict in verdicts]
    assert weights == sorted(weights, reverse=True) and all(0.0 <= w <= 1.0 for w in weights), (values, weights)      # worse never raises the degree
    assert all(w == 1.0 for w in weights[:full_at + 1]) and verdicts[-1]['status'] == 'conflicting'


def test_ligand_depletion_falls_with_the_log_of_the_kd_bias():
    percents = (5.0, 10.0, 10.5, 20.0, 30.0, 40.0, 49.0, 50.0)
    verdicts = [_judged('percent_bound', 'ligand_depletion', p, 'percent') for p in percents]
    _check_curve(percents, verdicts, 1, 'calibration_applicability')
    assert verdicts[2]['degree'] == pytest.approx(math.log(1.5 / _bias(10.5)) / math.log(1.5 / _bias(10)))    # just past 10 percent: 0.992, not a step
    assert verdicts[3]['degree'] == pytest.approx(math.log(1.5 / 1.125) / math.log(1.5 / _bias(10)))         # 20 percent: KD 1.125-fold, degree 0.82 (linear gave 0.75)
    assert verdicts[4]['degree'] == pytest.approx(DEPLETION_AT_30)


def test_nonspecific_fraction_falls_with_the_log_of_nonspecific_over_specific():
    percents = (25.0, 50.0, 52.0, 58.0, 70.0, 80.0, 89.0, 90.0)
    verdicts = [_judged('nonspecific_fraction', 'nonspecific_fraction', p, 'percent') for p in percents]
    _check_curve(percents, verdicts, 1, 'calibration_applicability')
    assert verdicts[3]['degree'] == pytest.approx(math.log(9 / (58 / 42)) / math.log(9))                     # 0.853
    assert verdicts[4]['degree'] == pytest.approx(math.log(9 / (70 / 30)) / math.log(9))                     # 0.614 (linear gave 0.5)
    assert verdicts[2]['degree'] > 0.95                                                                       # just past half: partial, not a step


def test_nonspecific_excess_falls_with_the_log_of_the_excess():
    excesses = (1000.0, 100.0, 90.0, 30.0, 10.0, 3.0, 1.5, 1.0)
    verdicts = [_judged('nonspecific_excess', 'nonspecific_excess', x) for x in excesses]
    _check_curve(excesses, verdicts, 1, 'binding_controls')
    assert verdicts[4]['degree'] == pytest.approx(0.5)                                                       # tenfold: half-way in log (the linear ramp gave 0.09)
    assert verdicts[3]['degree'] == pytest.approx(math.log(30) / math.log(100))
    assert verdicts[2]['degree'] > 0.97


def test_competition_radioligand_level_falls_with_the_radioligand_occupancy():
    levels = (0.25, 1.0, 1.1, 2.0, 5.0, 9.0, 10.0)
    verdicts = []
    for level in levels:
        record = synthetic_record()                                                       # KD 2 nM
        record['quantities']['radioligand_concentration'] = point(2.0 * level, 'nM', 'x', ['s'])
        verdicts.append(_criterion(grade_radioligand(record), 'competition_radioligand_level'))
    _check_curve(levels, verdicts, 1, 'binding_regime')
    assert verdicts[3]['degree'] == pytest.approx((2 / 3 - 10 / 11) / (0.5 - 10 / 11))                     # twice the KD: 0.59 (the Ki takes two thirds of a KD error)
    assert verdicts[4]['degree'] == pytest.approx((5 / 6 - 10 / 11) / (0.5 - 10 / 11))                     # five times: 0.19
    assert verdicts[2]['degree'] > 0.85


def test_cheng_prusoff_falls_with_the_log_of_the_fold_gap():
    folds = []
    verdicts = []
    for ki in (5.0, 7.5, 7.6, 10.0, 15.0, 20.0, 24.0, 25.0):                             # the calculated Ki is 5 nM (7.5 / (1 + 1 / 2))
        folds.append(ki / 5.0)
        verdicts.append(_judged('ki', 'cheng_prusoff', ki, 'nM'))
    _check_curve(folds, verdicts, 1, 'binding_parameter_definition')
    assert verdicts[3]['degree'] == pytest.approx(math.log(5 / 2) / math.log(5 / 1.5))                     # twofold: 0.76
    assert verdicts[2]['degree'] > 0.95


def test_the_hill_slope_keeps_its_linear_window_on_both_sides():
    slopes_low = (1.0, MIN_HILL, 0.75, 0.65, 0.55, MIN_HILL_ZERO_AGREEMENT)
    slopes_high = (1.0, MAX_HILL, 1.25, 1.35, 1.45, MAX_HILL_ZERO_AGREEMENT)
    for slopes in (slopes_low, slopes_high):
        verdicts = [_judged('hill_slope', 'hill_slope', s) for s in slopes]
        _check_curve(slopes, verdicts, 1, 'binding_parameter_definition')
    assert _judged('hill_slope', 'hill_slope', 0.65)['degree'] == pytest.approx(0.5) and _judged('hill_slope', 'hill_slope', 1.35)['degree'] == pytest.approx(0.5)
