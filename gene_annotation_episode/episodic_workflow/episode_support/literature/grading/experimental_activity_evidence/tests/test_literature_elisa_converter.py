"""ELISA converter: the sheet's effect and variance, the criteria mapping and the null reasons, with the arithmetic worked by hand."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_converter import (
    ABSORBANCE_BASE, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CONCENTRATIONS_ZERO_AGREEMENT, CRITERIA_MAP, EQUILIBRATION_REFERENCE_MIN, EQUILIBRATION_REFERENCE_NM, FIT_FREE_PARAMETERS_BY_MODEL, HIGH_FACTOR,
    HIGH_ZERO_AGREEMENT_FACTOR, KON_FAST_PER_M_S, KON_SLOW_PER_M_S, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MAX_LINEAR_OD, MAX_READABLE_OD, MIN_CONCENTRATIONS, MIN_INCUBATION_MIN, MIN_REPLICATES, MIN_SIGNAL_OVER_BACKGROUND,
    SIGNAL_WINDOW_ZERO_AGREEMENT, WASH_RETAINED_FULL, WASH_RETAINED_ZERO, _judge_concentration_series, _judge_equilibrium, _judge_estimates, _judge_plateau, _judge_replicates,
    _judge_signal_window, _judge_wash_loss, convert_elisa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_grader import CRITERIA, grade_elisa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.elisa_cases import real_record, sparse_record, synthetic_record


def convert(record):
    return convert_elisa(grade_elisa(record))


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 14


def test_the_apparent_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 20.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['elisa_kd:exp_synthetic_elisa_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == 4.0 and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 2 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(20.0) and cells['effect_variance']['value'] == pytest.approx(4.0) and cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(
        ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'), 'supported')
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_titrant_a', 'immobilized_preparation_ref': 'prep_coated_a', 'surface_ref': None, 'dataset_ref': 'dataset_elisa_1'}
    assert converted['experiment_type'] == 'elisa' and converted['extraction']['assay_type'] == 'ligand_binding'
    assert converted['null_components']['recovery'] == 'an_elisa_has_no_matrix_recovery_measurement'


def test_without_a_kd_the_ki_is_the_effect_with_its_own_spread():
    record = synthetic_record()
    missing(record, 'kd')
    converted = convert(record)
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 30.0 and effect['measurement_keys'] == ['elisa_ki:exp_synthetic_elisa_1'] and effect['native_component'] == 'ki'
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
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # two: replicates supported with partial credit, sd 2 over 2: 4 / 2
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(2.0)
    record['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])      # one independent experiment: supported with partial credit sqrt(1 / 3), sd 2 over 1: 4
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4.0)
    record['facts']['independent_experiments'] = fact('unknown')                # independence not stated: replicates unknown, so no variance
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance'] is None and converted['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    record = synthetic_record()
    record['spread_kind'] = 'standard_deviation'
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
    record['quantities']['signal_maximum'] = point(0.06, 'OD', 'm', ['s'])       # 0.06 / 0.06 = 1: the plateau is the background
    record['facts']['saturation_reached'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_SIGNAL_OVER_BACKGROUND, SIGNAL_WINDOW_ZERO_AGREEMENT, MAX_LINEAR_OD, MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (5.0, 1.0, 2.0, 8, 0.2, 1.0, 10.0, 1.0)
    assert (MIN_INCUBATION_MIN, MIN_REPLICATES, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (30.0, 3, 3.0, 10.0)
    assert (MAX_READABLE_OD, ABSORBANCE_BASE, CONCENTRATIONS_ZERO_AGREEMENT) == (4.0, 10.0, 4)      # the zero ends of the softened plateau and count
    assert (EQUILIBRATION_REFERENCE_NM, EQUILIBRATION_REFERENCE_MIN, KON_FAST_PER_M_S, KON_SLOW_PER_M_S) == (1.0, 30.0, 1e6, 1e4) and FIT_FREE_PARAMETERS_BY_MODEL == {'1:1': 2, 'hill': 3, 'four_parameter_logistic': 4, 'competitive_binding': 3}      # range review


WINDOW_AT_3 = math.log(3) / math.log(5)          # S/B 3 on the log scale from 1 (none) to 5 (full): about 0.68
FOLD_6 = math.log(10 / 6) / math.log(10 / 3)     # a 6-fold KD/Ki gap on the log scale from 3 (full) to 10 (none): about 0.42


def test_a_degree_travels_with_the_sheet_criterion_and_is_the_smallest_of_its_members():
    record = synthetic_record()
    record['quantities']['signal_maximum'] = point(0.18, 'OD', 'm', ['s'])       # 3 x the background: log 3 / log 5; the plateau is within the reader's range
    converted = convert(record)
    interpretation = converted['extraction']['interpretations']['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(WINDOW_AT_3)
    assert converted['sheet']['interpretations']['calibration_applicability']['degree'] == interpretation['degree']
    record['quantities']['ki'] = point(120.0, 'nM', 'k', ['s'])                  # 6 fold from the KD: log(10 / 6) / log(10 / 3) (the series spans the KD fully)
    interpretation = convert(record)['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(FOLD_6)
    assert 'degree' not in convert(record)['extraction']['interpretations']['binding_controls'] and 'degree' not in convert(record)['extraction']['interpretations']['sampling_basis']


def test_a_softened_count_below_its_researched_value_gives_its_sheet_criterion_a_partial_degree():
    record = synthetic_record()
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # two of the researched three independent experiments: sqrt(2 / 3)
    interpretation = _interpretations(record)['sampling_basis']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx((2 / 3) ** 0.5)
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'], support='implied')      # quote support multiplies it
    assert _interpretations(record)['sampling_basis']['degree'] == pytest.approx((2 / 3) ** 0.5 * 0.7)
    record = synthetic_record()
    record['concentration_series']['value'] = [1.0, 4.0, 16.0, 64.0, 256.0, 1024.0]      # six points, 0.05 x to 51.2 x the KD: two of the four residual degrees of freedom
    interpretation = _interpretations(record)['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    record = synthetic_record()
    record['facts']['signal_in_linear_range'] = fact('unknown')
    record['quantities']['signal_maximum'] = point(3.0, 'OD', 'm', ['s'])        # 3 OD: (10^4 - 10^3) / (10^4 - 10^2); the signal window (50 x) is full
    interpretation = _interpretations(record)['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(9000 / 9900)


def plateau(od, readout='absorbance', limit=None):
    return _judge_plateau({'plateau_absorbance': od, 'plateau_refs': ['s'], 'readout_signal': readout, 'detector_linear_limit': limit, 'linear_limit_refs': [] if limit is None else ['l']})


def series(count, low=0.1, high=20.0, model='four_parameter_logistic'):
    return _judge_concentration_series({'concentration_count': count, 'concentration_count_refs': ['c'], 'concentration_low_over_constant': low, 'concentration_high_over_constant': high, 'concentration_span_refs': ['sp'], 'fit_model': model})


def replicates(count, independent='yes'):
    return _judge_replicates({'replicate_count': count, 'replicate_independent': independent, 'replicate_refs': ['r']})


def window(ratio):
    return _judge_signal_window({'signal_over_background': ratio, 'signal_window_refs': ['w']})


def estimates(fold, conversion=None):
    return _judge_estimates({'estimate_fold': fold, 'estimate_refs': ['e'] if fold is not None else [], 'conversion_fold': conversion, 'conversion_refs': ['v'] if conversion is not None else []})


def wash(koff, minutes):
    return _judge_wash_loss({'koff_per_s': koff, 'wash_min': minutes, 'wash_loss_refs': ['w']})


def equilibrium(minutes, constant):
    return _judge_equilibrium({'incubation_min': minutes, 'incubation_refs': ['i'], 'constant_refs': ['c'], 'constant_nM': constant})


def credit(verdict):
    """The credit a verdict gives: 0 for conflicting, the degree (1.0 when none is attached) for supported."""
    return 0.0 if verdict['status'] == 'conflicting' else verdict.get('degree', 1.0)


@pytest.mark.parametrize('judge, values, researched, step', [
    (plateau, [1.0, 1.5, 2.0, 2.2, 2.5, 2.8, 3.0, 3.3, 3.6, 3.9, 4.0, 4.5, 400.0], MAX_LINEAR_OD, 0.01),      # worse as the absorbance rises
    (series, [12, 10, 8, 7.9, 7, 6, 5, 4.1, 4, 3, 2], MIN_CONCENTRATIONS, -0.01),                            # worse as the points fall
    (replicates, [6, 4, 3, 2.9, 2.5, 2, 1.5, 1.1, 1, 0], MIN_REPLICATES, -0.01),                             # worse as the experiments fall
    (window, [50, 10, 5, 4.99, 4, 3, 2, 1.5, 1.01, 1, 0.5, 0], MIN_SIGNAL_OVER_BACKGROUND, -0.01),           # worse as the window shrinks
    (estimates, [1, 2, 3, 3.01, 4, 6, 9.9, 10, 20], AGREEMENT_FACTOR, 0.01),                                 # worse as the KD and the Ki drift apart
])
def test_each_softened_judge_is_monotone_bounded_and_has_no_step_at_its_researched_value(judge, values, researched, step):
    credits = [credit(judge(value)) for value in values]                                  # values from better to worse
    assert all(0.0 <= c <= 1.0 for c in credits)
    assert credits == sorted(credits, reverse=True)                                       # worse never raises the degree
    assert judge(researched)['status'] == 'supported' and credit(judge(researched)) == 1.0                # full credit at the researched value
    just_past = judge(researched + step)
    assert just_past['status'] == 'supported' and 0.97 < just_past['degree'] < 1.0                       # just past it: partial credit, not a step to 0


def test_the_signal_window_and_the_kd_ki_gap_fall_with_the_log_of_their_fold():
    # range review: a window and a gap are folds, so each doubling costs the same; the old linear ramps gave S/B 3 0.5 and a 6-fold gap 4 / 7
    assert window(3)['degree'] == pytest.approx(WINDOW_AT_3) and window(2)['degree'] == pytest.approx(math.log(2) / math.log(5))
    assert window(SIGNAL_WINDOW_ZERO_AGREEMENT) == {'status': 'conflicting', 'support_refs': ['w']}
    assert estimates(6)['degree'] == pytest.approx(FOLD_6) and estimates(5)['degree'] == pytest.approx(math.log(2) / math.log(10 / 3))
    assert estimates(AGREEMENT_ZERO_FACTOR) == {'status': 'conflicting', 'support_refs': ['e']}
    assert window(3)['degree'] - window(2)['degree'] < window(2)['degree'] - window(1.01)['degree']      # the first doubling of the window matters most


def test_the_span_is_judged_on_the_occupancy_reached_at_each_end():
    occupancy = lambda x: x / (1 + x)
    high_5 = (occupancy(5) - occupancy(1)) / (occupancy(HIGH_FACTOR) - occupancy(1))          # 5 x the constant already shows 83 percent of the curve: about 0.81 (was 0.44)
    assert series(MIN_CONCENTRATIONS, high=5.0)['degree'] == pytest.approx(high_5) and 0.8 < high_5 < 0.82
    low_06 = (occupancy(0.6) - occupancy(1)) / (occupancy(LOW_FACTOR) - occupancy(1))         # 0.6 x leaves 37.5 percent of the curve unseen: 0.375 (was 0.5)
    assert series(MIN_CONCENTRATIONS, low=0.6)['degree'] == pytest.approx(low_06) == pytest.approx(0.375)
    assert series(MIN_CONCENTRATIONS, low=LOW_ZERO_AGREEMENT_FACTOR)['status'] == 'conflicting' and series(MIN_CONCENTRATIONS, high=HIGH_ZERO_AGREEMENT_FACTOR)['status'] == 'conflicting'
    highs = [credit(series(MIN_CONCENTRATIONS, high=h)) for h in (20, 10, 8, 5, 3, 2, 1.5, 1.1, 1.0)]
    lows = [credit(series(MIN_CONCENTRATIONS, low=x)) for x in (0.01, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0)]
    assert highs == sorted(highs, reverse=True) and lows == sorted(lows, reverse=True)       # monotone at both ends


def test_the_count_starts_its_credit_at_the_parameters_of_the_papers_stated_model():
    # range review: the points a fit uses up are its free parameters; a one-site fit to 5 points has 3 residual degrees of freedom
    assert series(5, model='1:1')['degree'] == pytest.approx(3 / 6) and series(2, model='1:1')['degree'] == 0.0
    assert series(5, model='hill')['degree'] == pytest.approx(2 / 5) and series(5, model='competitive_binding')['degree'] == pytest.approx(2 / 5)
    for model in ('four_parameter_logistic', 'other', None):                                  # four-parameter, other or unstated: the stricter four
        assert series(5, model=model)['degree'] == pytest.approx(1 / 4) and series(4, model=model) == {'status': 'supported', 'support_refs': ['sp'], 'degree': 0.0}
    for model in ('1:1', 'hill', 'competitive_binding', 'four_parameter_logistic', None):     # full at the researched count whatever the model; never conflicting when short
        assert series(MIN_CONCENTRATIONS, model=model)['degree'] == 1.0 and series(1, model=model)['status'] == 'supported'
    assert series(6, model='1:1')['degree'] > series(6, model='hill')['degree'] > series(6)['degree']      # fewer parameters, more credit for the same points
    record = synthetic_record()
    record['fit_model'] = '1:1'
    record['concentration_series']['value'] = [1.0, 4.0, 16.0, 64.0, 256.0]                 # five points, 0.05 x to 12.8 x the KD, a one-site fit
    assert _interpretations(record)['binding_regime']['degree'] == pytest.approx(0.5)


def test_the_equilibrium_is_a_curve_on_the_log_of_the_association_rate():
    # decision A: T_FAST = 30 min x 1 nM / constant (kon 1e6), T_SLOW = 100 x T_FAST (kon 1e4); d_kon = log(t / T_FAST) / log(100); d_floor = min(1, t / 30)
    span = math.log(100)
    one_nm = lambda minutes: equilibrium(minutes, 1.0)
    assert one_nm(30) == {'status': 'conflicting', 'support_refs': ['i', 'c']} and 'degree' not in one_nm(30)      # t <= T_FAST: the zero end
    assert one_nm(29)['status'] == 'conflicting'
    assert one_nm(60)['degree'] == pytest.approx(math.log(2) / span) and one_nm(60)['degree'] == pytest.approx(0.1505, abs=1e-4)
    assert one_nm(120)['degree'] == pytest.approx(math.log(4) / span) and one_nm(1440)['degree'] == pytest.approx(math.log(48) / span)      # 0.30, 0.84
    assert one_nm(3000) == {'status': 'supported', 'support_refs': ['i', 'c']} and 'degree' not in one_nm(3000)      # T_SLOW: full
    assert 'degree' not in one_nm(5000)
    # 20 nM: T_FAST 1.5 minutes, T_SLOW 150; the floor is the smaller of the two at 15 minutes
    assert equilibrium(1.5, 20.0)['status'] == 'conflicting'
    assert equilibrium(15, 20.0)['degree'] == pytest.approx(math.log(10) / span)      # d_kon 0.5, d_floor 0.5
    assert equilibrium(29, 20.0)['degree'] == pytest.approx(math.log(29 / 1.5) / span) and equilibrium(29, 20.0)['status'] == 'supported'      # 0.643 (d_floor 0.967)
    assert equilibrium(90, 20.0)['degree'] == pytest.approx(math.log(60) / span)      # 0.889
    assert 'degree' not in equilibrium(150, 20.0)
    # a weak, micromolar binder (1 uM: T_FAST 0.03, T_SLOW 3 minutes): only the floor lowers it, proportionally, never conflicting by itself
    assert 'degree' not in equilibrium(30, 1000.0) and equilibrium(15, 1000.0)['degree'] == pytest.approx(0.5)
    assert equilibrium(1, 1000.0)['degree'] == pytest.approx(1 / 30) and equilibrium(0.03, 1000.0)['status'] == 'conflicting'
    assert equilibrium(15, 1e4)['degree'] == pytest.approx(0.5)      # 10 uM
    # a tight, picomolar binder (10 pM: T_FAST 3000, T_SLOW 300000 minutes): the old needed time is now the zero end
    assert equilibrium(120, 0.01)['status'] == 'conflicting' and equilibrium(1440, 0.01)['status'] == 'conflicting' and equilibrium(3000, 0.01)['status'] == 'conflicting'
    assert equilibrium(6000, 0.01)['degree'] == pytest.approx(math.log(2) / span) and equilibrium(300000, 0.01)['status'] == 'supported'
    # no constant: unknown, also below the floor (a time alone is not the paper against equilibrium)
    assert equilibrium(29, None) == {'status': 'unknown', 'support_refs': []} and equilibrium(120, None) == {'status': 'unknown', 'support_refs': []}
    degrees = [equilibrium(120, k).get('degree', 1.0) if equilibrium(120, k)['status'] == 'supported' else 0.0 for k in (1000.0, 100.0, 20.0, 1.0, 0.25, 0.1, 0.01)]
    assert degrees == sorted(degrees, reverse=True) and degrees[0] == 1.0 and degrees[-1] == 0.0      # tighter constants never make the same time look better
    times = [equilibrium(t, 1.0).get('degree', 1.0) if equilibrium(t, 1.0)['status'] == 'supported' else 0.0 for t in (10, 30, 31, 60, 600, 3000, 6000)]
    assert times == sorted(times)      # a longer step never looks worse
    record = synthetic_record(kd=0.01)                                                      # a 10 pM apparent KD from a 90-minute step: conflicting through the sheet
    record['facts']['equilibrium_reached'] = fact('unknown')
    record['concentration_series']['value'] = [0.0005 * 2 ** step for step in range(12)]
    assert _interpretations(record)['binding_regime']['status'] == 'conflicting'
    record = synthetic_record(kd=20.0)                                                      # 20 nM from a 90-minute step: the sheet carries the equilibrium degree 0.889
    record['facts']['equilibrium_reached'] = fact('unknown')
    assert _interpretations(record)['binding_regime']['degree'] == pytest.approx(math.log(60) / span)
    record = synthetic_record(kd=20.0)                                                      # the same step with no constant at all is unknown
    record['facts']['equilibrium_reached'] = fact('unknown')
    for name in ('kd', 'ki', 'ec50', 'ic50'):
        record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}
    assert _interpretations(record)['binding_regime']['status'] == 'unknown'


def test_the_plateau_is_judged_only_for_an_absorbance_and_never_overflows():
    assert plateau(400.0) == {'status': 'conflicting', 'support_refs': ['s']} and plateau(1e6)['status'] == 'conflicting'      # was an OverflowError
    assert plateau(3.0, readout=None)['degree'] == pytest.approx(9000 / 9900)                # not stated: the OD unit says absorbance
    for readout in ('chemiluminescence', 'fluorescence'):
        assert plateau(3.0, readout=readout) == {'status': 'unknown', 'support_refs': []} and plateau(5.0, readout=readout)['status'] == 'unknown'
    record = synthetic_record()
    record['facts']['signal_in_linear_range'] = fact('unknown')
    record['readout_signal'] = 'chemiluminescence'
    assert _interpretations(record)['calibration_applicability']['status'] == 'unknown'


def test_a_stated_reader_linear_limit_replaces_the_researched_one_and_is_capped_at_the_photometric_range():
    assert plateau(1.8, limit=1.5)['degree'] == pytest.approx((10 ** 1.8 - 10 ** 4) / (10 ** 1.5 - 10 ** 4)) and plateau(1.8, limit=1.5)['support_refs'] == ['s', 'l']
    assert plateau(2.5, limit=3.0) == {'status': 'supported', 'support_refs': ['s', 'l']}                 # inside the paper's own stated limit: full credit (the researched 2.0 would give partial)
    assert plateau(2.5)['degree'] < 1.0 and plateau(2.5, limit=2.0)['degree'] == plateau(2.5)['degree']  # no limit stated: the researched MAX_LINEAR_OD
    assert plateau(3.5, limit=9.0) == {'status': 'supported', 'support_refs': ['s', 'l']}                # a limit past the reader's range is cut to MAX_READABLE_OD: full up to it
    assert plateau(MAX_READABLE_OD, limit=9.0)['status'] == 'conflicting'
    degrees = [credit(plateau(od, limit=1.5)) for od in (1.0, 1.5, 1.7, 2.0, 3.0, 3.9)]
    assert degrees == sorted(degrees, reverse=True) and degrees[1] == 1.0 and 0.97 < credit(plateau(1.5 + 0.01, limit=1.5)) < 1.0      # monotone, no step


def test_the_wash_loss_is_judged_on_the_share_of_the_complex_that_survives():
    # first-order loss: retained = exp(-koff * t); full at WASH_RETAINED_FULL, conflicting at WASH_RETAINED_ZERO, linear in koff * t between
    full, zero = -math.log(WASH_RETAINED_FULL), -math.log(WASH_RETAINED_ZERO)
    assert wash(full / 600.0, 10) == {'status': 'supported', 'support_refs': ['w'], 'degree': pytest.approx(1.0)}
    assert wash(zero / 600.0, 10) == {'status': 'conflicting', 'support_refs': ['w']}
    middle = wash((full + zero) / 2 / 600.0, 10)
    assert middle['status'] == 'supported' and middle['degree'] == pytest.approx(0.5)
    assert wash(1e-5, 10)['degree'] == 1.0                                                              # a slow koff: complex kept (exp(-0.006) = 0.994)
    assert wash(1e-3, 5)['degree'] == pytest.approx((0.3 - zero) / (full - zero))                         # 5 min at 1e-3 per s: exp(-0.3) = 0.74 kept, about 0.91
    times = [credit(wash(2e-3, minutes)) for minutes in (0.1, 1, 2, 5, 10, 20)]
    assert times == sorted(times, reverse=True) and all(0.0 <= c <= 1.0 for c in times)                 # a longer wash never raises it
    rates = [credit(wash(rate, 5)) for rate in (1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2)]
    assert rates == sorted(rates, reverse=True)                                                         # a faster koff never raises it


def test_the_wash_loss_and_the_reader_limit_and_the_cheng_prusoff_ki_reach_the_sheet():
    record = synthetic_record()
    record['facts']['wash_dissociation_considered'] = fact('unknown')
    record['quantities']['koff'] = point(0.0005, 's^-1', 'koff', ['s'])
    record['quantities']['wash_duration'] = point(10, 'min', 'wash', ['s'])                              # exp(-0.3) = 0.74 kept
    graded = grade_elisa(record)
    assert graded['reasons']['wash_dissociation'] == 'wash_loss_recorded_for_the_sheet' and graded['native']['wash_min'] == 10
    assert _interpretations(record)['binding_regime']['degree'] < 1.0
    unstated = synthetic_record()
    unstated['facts']['wash_dissociation_considered'] = fact('unknown')                                    # koff and the wash duration not given: unknown, as before
    assert grade_elisa(unstated)['reasons']['wash_dissociation'] == 'fact_unknown'
    record = synthetic_record()
    record['facts']['signal_in_linear_range'] = fact('unknown')
    record['quantities']['signal_maximum'] = point(1.8, 'OD', 'm', ['s'])
    assert _interpretations(record)['calibration_applicability']['degree'] == 1.0                         # 1.8 OD is inside the researched 2 OD
    record['quantities']['detector_linear_limit'] = point(1.5, 'OD', 'lim', ['s'])
    assert _interpretations(record)['calibration_applicability']['degree'] < 1.0                          # but not inside the reader limit the paper states
    record = synthetic_record()                                                                           # tracer 10 nM, tracer KD 15 nM: Ki = 45 / (1 + 10 / 15) = 27 nM
    record['quantities']['tracer_concentration'] = point(10.0, 'nM', 'tr', ['s'])
    record['quantities']['tracer_kd'] = point(15.0, 'nM', 'trkd', ['s'])
    native = grade_elisa(record)['native']
    assert native['ki_cheng_prusoff_nM'] == pytest.approx(27.0) and native['conversion_fold'] == pytest.approx(30 / 27)
    record['quantities']['tracer_concentration'] = point(1000.0, 'nM', 'tr', ['s'])                       # a tracer far above its KD: the Ki would be 45 / 67.7 = 0.66 nM, 45-fold from the reported 30
    assert _interpretations(record)['binding_regime']['status'] == 'conflicting'
    missing(record, 'ki')                                                                                 # no reported Ki: the KD (20 nM) is compared with the derived Ki
    graded = grade_elisa(record)
    assert graded['native']['conversion_fold'] is None and graded['native']['estimate_fold'] == pytest.approx(20 / (45 / (1 + 1000 / 15)))


def test_the_softened_judges_reach_zero_only_at_their_researched_zero_ends():
    assert plateau(MAX_READABLE_OD) == {'status': 'conflicting', 'support_refs': ['s']} and plateau(MAX_READABLE_OD - 0.01)['status'] == 'supported'
    # a short count is never conflicting: at the zero end of the count it is supported with no credit
    assert series(CONCENTRATIONS_ZERO_AGREEMENT) == {'status': 'supported', 'support_refs': ['sp'], 'degree': 0.0} and series(2)['degree'] == 0.0
    assert series(CONCENTRATIONS_ZERO_AGREEMENT + 1)['degree'] == pytest.approx(0.25)
    assert replicates(1) == {'status': 'supported', 'support_refs': ['r'], 'degree': pytest.approx((1 / 3) ** 0.5)} and replicates(2)['degree'] == pytest.approx((2 / 3) ** 0.5)
    assert series(MIN_CONCENTRATIONS)['degree'] == 1.0 and series(7, low=0.6)['degree'] == pytest.approx(0.375)      # the smallest of the count (0.75) and the span (0.375 on the occupancy scale)


def test_a_softened_count_with_nothing_else_to_judge_is_unknown_not_zero():
    assert _judge_concentration_series({'concentration_count': 6, 'concentration_count_refs': ['c'], 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'concentration_span_refs': [], 'fit_model': None}) == {'status': 'unknown', 'support_refs': []}
    assert replicates(2, independent='unknown') == {'status': 'unknown', 'support_refs': []}
    record = synthetic_record()
    record['facts']['signal_in_linear_range'] = fact('unknown')
    missing(record, 'signal_maximum')                                             # no plateau absorbance stated: unknown
    assert _interpretations(record)['calibration_applicability']['status'] == 'unknown'


def _interpretations(record):
    return convert(record)['extraction']['interpretations']


def test_a_criterion_resting_on_a_field_with_thin_support_gets_the_support_degree():
    assert 'degree' not in _interpretations(synthetic_record())['binding_controls']       # all direct: unchanged, no degree where there was none
    record = synthetic_record()
    record['facts']['blank_subtracted'] = fact('yes', ['s'], 'implied')
    interpretation = _interpretations(record)['binding_controls']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.7)
    record['facts']['avidity_excluded'] = fact('yes', ['s'], 'about_something_else')       # the weakest member field decides
    assert _interpretations(record)['binding_controls']['degree'] == pytest.approx(0.3)
    assert 'degree' not in _interpretations(record)['sampling_basis']                      # other sheet criteria are untouched


def test_the_support_degree_multiplies_a_degree_the_sheet_already_has():
    record = synthetic_record()
    record['quantities']['signal_maximum'] = point(0.18, 'OD', 'm', ['s'])                 # S/B 3: a degree of log 3 / log 5
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(WINDOW_AT_3)
    record['quantities']['signal_maximum'] = point(0.18, 'OD', 'm', ['s'], support='implied')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(WINDOW_AT_3 * 0.7)
    record['quantities']['signal_maximum'] = point(0.18, 'OD', 'm', ['s'], support='about_something_else')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(WINDOW_AT_3 * 0.3)
    record['quantities']['signal_maximum'] = point(0.18, 'OD', 'm', ['s'], support='direct')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(WINDOW_AT_3)      # direct: unchanged


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
    record['facts']['blank_subtracted'] = fact('no', ['s'], 'about_something_else')
    interpretation = _interpretations(record)['binding_controls']
    assert interpretation['status'] == 'conflicting' and 'degree' not in interpretation
    record['facts']['blank_subtracted'] = fact('unknown')
    interpretation = _interpretations(record)['binding_controls']
    assert interpretation['status'] == 'unknown' and 'degree' not in interpretation
    assert {item['status'] for item in _interpretations(synthetic_record()).values()} == {'supported'}


def test_a_not_applicable_member_is_dropped_and_an_all_not_applicable_sheet_criterion_is_not_selected():
    record = synthetic_record()
    record['facts']['single_estimate_method'] = fact('yes', ['s'])
    missing(record, 'ki')
    for name in ('blank_subtracted', 'nonspecific_binding_checked', 'avidity_excluded', 'coated_protein_active', 'detection_does_not_interfere'):
        record['facts'][name] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert 'binding_controls' not in interpretations and interpretations['binding_regime']['status'] == 'supported'


def test_the_sparse_record_gives_only_the_effect_and_unknown_interpretations():
    converted = convert(sparse_record())
    assert converted['sheet']['cells']['measured_effect']['value'] == pytest.approx(20.0)
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {item['status'] for item in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_the_real_paragraph_record_has_no_effect_and_only_unknown_interpretations():
    converted = convert(real_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'unknown'
    assert interpretations['binding_regime']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown'
    assert 'sampling_basis' in interpretations and interpretations['sampling_basis']['status'] == 'unknown'
