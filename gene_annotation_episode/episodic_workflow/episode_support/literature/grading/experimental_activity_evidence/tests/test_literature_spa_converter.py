"""SPA converter: the sheet's effect and variance, the criteria mapping and the null reasons, with the arithmetic worked by hand."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import CRITERIA_MAP, convert_spa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_grader import CRITERIA, grade_spa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spa_cases import real_record, sparse_record, synthetic_record


def convert(record):
    return convert_spa(grade_spa(record))


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 18


def test_the_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 2.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['spa_kd:exp_synthetic_spa_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == pytest.approx(0.04) and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 0.2 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(2.0) and cells['effect_variance']['value'] == pytest.approx(0.04) and cells['effect_precision']['value'] == pytest.approx(25.0)
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(
        ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'), 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_radioligand_a', 'immobilized_preparation_ref': 'prep_receptor_a', 'surface_ref': None, 'dataset_ref': 'dataset_spa_1'}
    assert converted['experiment_type'] == 'spa' and converted['extraction']['assay_type'] == 'ligand_binding'
    assert converted['null_components']['recovery'] == 'an_spa_has_no_matrix_recovery_measurement'


def test_without_a_kd_the_ki_is_the_effect_with_its_own_spread():
    record = synthetic_record()
    missing(record, 'kd')
    converted = convert(record)
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 5.0 and effect['measurement_keys'] == ['spa_ki:exp_synthetic_spa_1'] and effect['native_component'] == 'ki'
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
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(0.04 / 3)
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # two: replicates supported with partial credit, so the sd still gives 0.04 / 2
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(0.04 / 2)
    record['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])      # one experiment: replicates supported (sqrt(1/3)), but an sd of one experiment is a spread of wells: no variance
    assert convert(record)['extraction']['interpretations']['sampling_basis']['status'] == 'supported'
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance'] is None and converted['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    record['spread_kind'] = 'confidence_interval'
    assert convert(record)['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    record['spread_kind'] = None
    assert convert(record)['null_components']['effect_variance'] == 'spread_kind_not_stated'
    record['spread_kind'] = 'standard_error'
    missing(record, 'kd_spread')
    assert convert(record)['null_components']['effect_variance'] == 'kd_spread_not_given'
    record['quantities']['kd_spread'] = point(0.0002, 'uM', 's', ['s'])          # 0.2 nM
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(0.04)


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['bead_only_control_done'] = fact('no', ['s'])
    missing(record, 'bead_only_fraction')
    record['quantities']['percent_bound'] = point(40.0, 'percent', 'p', ['s'])            # above 10
    record['facts']['equilibrium_reached'] = fact('unknown')
    missing(record, 'incubation_time')                                                    # no incubation time: nothing to judge equilibrium by (unknown)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'


def test_quench_and_settling_belong_to_the_calibration_criterion_not_the_controls():
    record = synthetic_record()
    record['facts']['quench_interference_checked'] = fact('no', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and interpretations['binding_controls']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['bead_settling_controlled'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    for name in ('nonspecific_binding_determined', 'radioligand_purity_checked', 'nonproximity_signal_checked', 'bead_only_control_done'):
        record['facts'][name] = fact('not_applicable')
    missing(record, 'bead_only_fraction')
    missing(record, 'nonspecific_excess')
    missing(record, 'nonspecific_ligand_concentration')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown'            # the excess is now unknown; the four facts are dropped
    record['quantities']['nonspecific_excess'] = point(500.0, 'ratio', 'e', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['support_refs'] == ['s']     # only the excess is left


def test_the_sparse_record_gives_only_the_effect_and_unknown_interpretations():
    converted = convert(sparse_record())
    assert converted['sheet']['cells']['measured_effect']['value'] == pytest.approx(2.0)
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {item['status'] for item in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_the_real_record_converts_without_an_effect():
    converted = convert(real_record())
    assert converted['sheet']['cells']['measured_effect']['value'] is None and converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'unknown'


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_spa_converter as sheet
    assert (sheet.MAX_PERCENT_BOUND, sheet.PERCENT_BOUND_ZERO_AGREEMENT, sheet.MAX_NONSPECIFIC_FRACTION, sheet.NONSPECIFIC_FRACTION_ZERO_AGREEMENT, sheet.MAX_BEAD_ONLY_FRACTION, sheet.BEAD_ONLY_ZERO_AGREEMENT) == (10.0, 30.0, 50.0, 80.0, 20.0, 50.0)
    assert (sheet.MIN_NONSPECIFIC_EXCESS, sheet.NONSPECIFIC_EXCESS_ZERO_AGREEMENT, sheet.MIN_CONCENTRATIONS, sheet.LOW_FACTOR, sheet.LOW_ZERO_AGREEMENT_FACTOR, sheet.HIGH_FACTOR, sheet.HIGH_ZERO_AGREEMENT_FACTOR) == (100.0, 10.0, 8, 0.25, 1.0, 5.0, 1.0)
    assert (sheet.MAX_RADIOLIGAND_OVER_KD, sheet.RADIOLIGAND_OVER_KD_ZERO_AGREEMENT, sheet.MIN_INCUBATION_MIN, sheet.MIN_HILL, sheet.MAX_HILL, sheet.HILL_LOW_ZERO_AGREEMENT, sheet.HILL_HIGH_ZERO_AGREEMENT) == (1.0, 10.0, 30.0, 0.8, 1.2, 0.5, 2.0)
    assert (sheet.CHENG_PRUSOFF_FACTOR, sheet.CHENG_PRUSOFF_ZERO_AGREEMENT_FACTOR, sheet.MIN_REPLICATES) == (1.5, 5.0, 3)
    assert (sheet.SATURATION_FIT_PARAMETERS, sheet.SD_MIN_EXPERIMENTS) == (2, 2)      # KD and Bmax (was 3); the variance-only count of an sd
    assert not hasattr(sheet, 'REPLICATES_ZERO')                                       # replicates mean precision: sqrt(n / MIN_REPLICATES), no zero end


def judged(record, name):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import _criterion
    return _criterion(grade_spa(record), name)


def test_the_sheet_judges_the_percent_criteria_with_a_degree_falling_linearly_to_the_zero_agreement_limit():
    record = synthetic_record()
    cases = (('percent_bound', 'ligand_depletion', 'ligand_depletion_checked', ((10.0, 'supported', 1.0), (0.0, 'supported', 1.0), (20.0, 'supported', 0.5), (25.0, 'supported', 0.25), (30.0, 'conflicting', None), (60.0, 'conflicting', None))),
             ('nonspecific_fraction', 'nonspecific_fraction', None, ((50.0, 'supported', 1.0), (65.0, 'supported', 0.5), (80.0, 'conflicting', None), (95.0, 'conflicting', None))),
             ('bead_only_fraction', 'bead_only_control', 'bead_only_control_done', ((20.0, 'supported', 1.0), (35.0, 'supported', 0.5), (50.0, 'conflicting', None), (70.0, 'conflicting', None))))
    for quantity, criterion, _, rows in cases:
        for value, expected, degree in rows:
            record['quantities'][quantity] = point(value, 'percent', 'p', ['s'])
            verdict = judged(record, criterion)
            assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (quantity, value)
            assert verdict['support_refs'] == ['s']
    record['quantities']['percent_bound'] = point(20.0, 'percent', 'p', ['s'])                      # the degree travels into the sheet criterion that holds the member
    record['quantities']['nonspecific_fraction'] = point(25.0, 'percent', 'f', ['s'])
    interpretation = convert(record)['extraction']['interpretations']['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)


def occupancy_degree(ratio, full, zero):
    """The expected degree linear in the occupancy x / (1 + x), worked independently of the converter."""
    theta = lambda x: x / (1 + x)
    return (theta(ratio) - theta(zero)) / (theta(full) - theta(zero))


def test_the_sheet_judges_the_excess_as_a_minimum_with_a_degree_linear_in_the_occupancy():
    record = synthetic_record()
    for value, expected, degree in ((100.0, 'supported', 1.0), (500.0, 'supported', 1.0), (55.0, 'supported', occupancy_degree(55.0, 100.0, 10.0)), (20.0, 'supported', occupancy_degree(20.0, 100.0, 10.0)), (10.0, 'conflicting', None), (1.0, 'conflicting', None)):
        record['quantities']['nonspecific_excess'] = point(value, 'ratio', 'e', ['s'])
        verdict = judged(record, 'nonspecific_excess')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), value
    record['quantities']['nonspecific_excess'] = point(55.0, 'ratio', 'e', ['s'])                   # the residual specific binding moves only 1.0 -> 1.8 percent: most credit kept
    assert judged(record, 'nonspecific_excess')['degree'] == pytest.approx(0.90, abs=0.01)
    record['quantities']['nonspecific_excess'] = point(20.0, 'ratio', 'e', ['s'])                   # was 0.11 when linear in the fold
    assert judged(record, 'nonspecific_excess')['degree'] == pytest.approx(0.53, abs=0.01)
    credits = []
    for value in (5.0, 10.0, 11.0, 15.0, 20.0, 40.0, 70.0, 99.0, 100.0, 1000.0):
        record['quantities']['nonspecific_excess'] = point(value, 'ratio', 'e', ['s'])
        credits.append(credit(judged(record, 'nonspecific_excess')))
    assert all(0.0 <= value <= 1.0 for value in credits) and credits == sorted(credits) and 0.0 < credits[-3] < 1.0      # monotone, bounded, just below 100 partial


def series_of(count):
    """A saturation series of count concentrations, lowest 0.5 nM (0.25 x the KD of 2 nM) and highest 100 nM (50 x): only the count varies."""
    values = [0.5 * 2 ** step for step in range(count)]
    values[-1] = 100.0
    return values


def test_the_sheet_gives_the_concentration_count_partial_credit_and_the_incubation_a_gradual_degree_against_the_kd():
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    missing(record, 'association_half_time')                                                          # no time course stated: the incubation alone is judged
    # KD 2 nM: T_FAST = 5 ln2 / (1e8 * 2e-9) / 60 = 0.288811 min, T_SLOW 288.811 min; d_kon = ln(t / 0.288811) / ln 1000, d_floor = min(1, t / 30)
    for minutes, degree in ((300.0, 1.0), (240.0, 0.9732), (30.0, 0.67215), (29.0, 0.66726), (5.0, 1 / 6), (1.0, 1 / 30)):      # (1 min: d_kon 0.18, floor 0.0333; 240 min: d_kon ln(830.9) / ln 1000 = 0.9732; 300 min is past T_SLOW: 1)
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        verdict = judged(record, 'equilibrium')
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(degree, abs=1e-4), minutes
    degrees = []
    for minutes in (0.1, 0.2888, 0.3, 1.0, 5.0, 29.0, 30.0, 100.0, 288.0, 289.0, 960.0):      # monotone, conflicting only at or below T_FAST, never a step
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        verdict = judged(record, 'equilibrium')
        degrees.append(0.0 if verdict['status'] == 'conflicting' else verdict['degree'])
    assert degrees == sorted(degrees) and degrees[:2] == [0.0, 0.0] and degrees[2] > 0.0 and degrees[-1] == 1.0 and degrees[-2] == 1.0
    missing(record, 'kd')
    for minutes in (2.0, 120.0):                                                                  # no KD: no scale, unknown
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert judged(record, 'equilibrium') == {'status': 'unknown', 'support_refs': []}
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    missing(record, 'association_half_time')
    for count, expected, degree in ((8, 'supported', 1.0), (12, 'supported', 1.0), (7, 'supported', 5 / 6), (4, 'supported', 1 / 3), (3, 'supported', 1 / 6), (2, 'supported', 0.0)):      # max(0, (n - 2) / (8 - 2))
        record['concentration_series']['value'] = series_of(count)
        verdict = judged(record, 'radioligand_range')
        assert verdict['status'] == expected and verdict.get('degree') == pytest.approx(degree), count
        assert verdict['support_refs']                                                              # a short series is weak evidence, never conflicting


def test_the_sheet_judges_the_incubation_in_association_half_times_gradually_and_never_as_conflicting():
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    degrees = []
    for ratio in (0.5, 1.0, 2.0, 4.0, 5.0, 8.0, 30.0):
        record['quantities']['association_half_time'] = point(60.0 / ratio, 'min', 'h', ['s_half'])      # 60 min incubation
        record['quantities']['incubation_time'] = point(60.0, 'min', 'i', ['s'])
        verdict = judged(record, 'equilibrium')
        assert verdict['status'] == 'supported' and 0.0 <= verdict['degree'] <= 1.0 and 's_half' in verdict['support_refs'], ratio
        degrees.append(verdict['degree'])
    assert degrees == sorted(degrees) and degrees[-1] == 1.0 and degrees[4] == 1.0                    # monotone, full from five half-times
    assert degrees[1] == pytest.approx(0.5 / (1 - 2 ** -5)) and degrees[0] > 0.0                       # one half-time: half the plateau, over its 97 percent
    assert degrees[3] == pytest.approx((1 - 2 ** -4) / (1 - 2 ** -5))                                  # no step at the researched five: just below it is near full


def credit(verdict):
    """The weight a verdict gives a supported-or-conflicting judgement: its degree, 0 when conflicting."""
    return 0.0 if verdict['status'] == 'conflicting' else verdict['degree']


def test_the_concentration_count_is_monotone_bounded_and_has_no_step_at_its_researched_value():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import MIN_CONCENTRATIONS
    record = synthetic_record()
    credits = []
    for count in range(2, 16):
        record['concentration_series']['value'] = series_of(count)
        credits.append(credit(judged(record, 'radioligand_range')))
    assert all(0.0 <= value <= 1.0 for value in credits) and credits == sorted(credits)      # more concentrations never lower the degree
    record['concentration_series']['value'] = series_of(MIN_CONCENTRATIONS - 1)                   # just below the researched count: partial credit, not 0
    assert 0.0 < judged(record, 'radioligand_range')['degree'] < 1.0
    record['concentration_series']['value'] = series_of(MIN_CONCENTRATIONS)
    assert judged(record, 'radioligand_range')['degree'] == 1.0
    record['concentration_series'] = {**record['concentration_series'], 'status': 'unavailable', 'value': None}
    missing(record, 'radioligand_range_highest')                                                     # a count with no readable span: unknown, never 0
    assert judged(record, 'radioligand_range') == {'status': 'unknown', 'support_refs': []}


def test_the_replicates_are_monotone_bounded_and_have_no_step_at_their_researched_value():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import MIN_REPLICATES
    record = synthetic_record()
    credits = []
    for count in range(1, 11):
        record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        credits.append(credit(judged(record, 'replicates')))
    assert all(0.0 <= value <= 1.0 for value in credits) and credits == sorted(credits)      # more independent experiments never lower the degree
    assert credits[:4] == [pytest.approx(math.sqrt(1 / 3)), pytest.approx(math.sqrt(2 / 3)), 1.0, 1.0]      # sqrt(n / 3): precision of the mean constant
    record['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])                      # one independent experiment: low partial credit, never conflicting
    assert judged(record, 'replicates')['status'] == 'supported' and judged(record, 'replicates')['support_refs']
    record['quantities']['replicate_count'] = point(MIN_REPLICATES - 1, 'count', 'n', ['s'])
    verdict = judged(record, 'replicates')
    assert verdict['status'] == 'supported' and 0.0 < verdict['degree'] < 1.0 and verdict['support_refs']
    record['facts']['independent_experiments'] = fact('unknown')                                  # independence not stated: unknown, never 0
    assert judged(record, 'replicates') == {'status': 'unknown', 'support_refs': []}
    missing(record, 'replicate_count')
    assert judged(record, 'replicates')['status'] == 'unknown'


def test_the_degree_of_a_sheet_criterion_is_the_weakest_member_degree():
    record = synthetic_record()
    record['quantities']['percent_bound'] = point(20.0, 'percent', 'p', ['s'])                      # 0.5
    record['quantities']['nonspecific_fraction'] = point(65.0, 'percent', 'f', ['s'])               # 0.5
    record['quantities']['bead_only_fraction'] = point(35.0, 'percent', 'b', ['s'])                 # 0.5 (a member of binding_controls)
    record['quantities']['nonspecific_excess'] = point(12.5, 'ratio', 'e', ['s'])                   # about 0.21, in the occupancy (binding_controls)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['degree'] == pytest.approx(0.5) and interpretations['binding_controls']['degree'] == pytest.approx(occupancy_degree(12.5, 100.0, 10.0))
    assert interpretations['sampling_basis']['degree'] == 1.0 and 'degree' in interpretations['binding_parameter_definition']      # three independent experiments: full credit; the Hill slope and the Cheng-Prusoff gap are continuous: degree 1.0
    assert interpretations['binding_parameter_definition']['degree'] == 1.0
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                         # two: the replicate degree travels into sampling_basis
    assert convert(record)['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(math.sqrt(2 / 3))


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert base['sampling_basis']['degree'] == 1.0 and base['binding_controls']['degree'] == 1.0
    implied = synthetic_record()
    implied['facts']['nonspecific_binding_determined']['support'] = 'implied'              # a fact: supported with no degree before
    implied['quantities']['replicate_count']['support'] = 'about_something_else'
    interpretations = convert(implied)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['degree'] == pytest.approx(0.7)
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx(0.3)
    assert interpretations['binding_regime'] == base['binding_regime'] and interpretations['calibration_applicability'] == base['calibration_applicability']


def test_the_support_degree_multiplies_a_degree_the_sheet_already_gave_and_never_changes_a_status():
    record = synthetic_record()
    record['quantities']['percent_bound'] = point(20.0, 'percent', 'p', ['s'], support='implied')      # 0.5 from the comparison, times 0.7
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['degree'] == pytest.approx(0.35)
    record['quantities']['percent_bound'] = point(40.0, 'percent', 'p', ['s'], support='about_something_else')      # conflicting: no degree
    verdict = convert(record)['extraction']['interpretations']['calibration_applicability']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = synthetic_record()
    record['fit_model'], record['choice_support']['fit_model'] = 'one_site', 'implied'
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.7)
    record['quantities']['kd_spread']['support'] = 'implied'
    assert convert(record)['extraction']['interpretations']['variance_correspondence']['degree'] == pytest.approx(0.7)
    record = synthetic_record()
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'], support='implied')        # sqrt(2/3) from the count, times 0.7
    assert convert(record)['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(math.sqrt(2 / 3) * 0.7)


def test_the_span_ends_are_linear_in_the_occupancy_and_symmetric_about_the_kd():
    record = synthetic_record()                                                                     # KD 2 nM, ten concentrations
    cases = (([1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 15.0, 20.0], 'low', 0.5), ([0.2, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0], 'high', 2.0), ([0.2, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0], 'high', 2.5))
    for values, end, ratio in cases:
        record['concentration_series']['value'] = values
        verdict = judged(record, 'radioligand_range')
        full, zero = (0.25, 1.0) if end == 'low' else (5.0, 1.0)
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(occupancy_degree(ratio, full, zero)), (end, ratio)
    record['concentration_series']['value'] = [1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 15.0, 20.0]
    low_half = judged(record, 'radioligand_range')['degree']                                       # lowest 0.5 x KD
    record['concentration_series']['value'] = [0.2, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
    high_double = judged(record, 'radioligand_range')['degree']                                    # highest 2 x KD
    assert low_half == pytest.approx(5 / 9) and high_double == pytest.approx(0.5)                  # one fold from the KD on either side: near-equal credit (was 0.67 against 0.25)
    credits = []
    for highest in (1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 4.9, 5.0, 20.0):
        record['concentration_series']['value'] = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, highest * 2.0]
        credits.append(credit(judged(record, 'radioligand_range')))
    assert all(0.0 <= value <= 1.0 for value in credits) and credits == sorted(credits) and 0.0 < credits[-3] < 1.0      # monotone, bounded, no step at HIGH_FACTOR
    record['concentration_series']['value'] = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 2.0]               # the plateau not reached at all: the span conflicts
    assert judged(record, 'radioligand_range')['status'] == 'conflicting'


def test_the_competition_radioligand_level_is_linear_in_the_radioligand_occupancy():
    record = synthetic_record()                                                                     # KD 2 nM
    for nanomolar, expected, degree in ((1.0, 'supported', 1.0), (2.0, 'supported', 1.0), (4.0, 'supported', occupancy_degree(2.0, 1.0, 10.0)), (6.0, 'supported', occupancy_degree(3.0, 1.0, 10.0)), (10.0, 'supported', occupancy_degree(5.0, 1.0, 10.0)), (20.0, 'conflicting', None), (40.0, 'conflicting', None)):
        record['quantities']['radioligand_concentration'] = point(nanomolar, 'nM', 'r', ['s'])
        verdict = judged(record, 'competition_radioligand_level')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), nanomolar
    record['quantities']['radioligand_concentration'] = point(6.0, 'nM', 'r', ['s'])               # 3 x KD: the Ki takes 75 of every 100 percent of KD error (was 0.78 when linear in r)
    assert judged(record, 'competition_radioligand_level')['degree'] == pytest.approx(0.39, abs=0.01)
    credits = []
    for ratio in (0.5, 1.0, 1.1, 2.0, 3.0, 5.0, 9.9, 10.0, 30.0):
        record['quantities']['radioligand_concentration'] = point(ratio * 2.0, 'nM', 'r', ['s'])
        credits.append(credit(judged(record, 'competition_radioligand_level')))
    assert all(0.0 <= value <= 1.0 for value in credits) and credits == sorted(credits, reverse=True) and 0.0 < credits[2] < 1.0      # more radioligand never raises the degree; just above the KD partial
