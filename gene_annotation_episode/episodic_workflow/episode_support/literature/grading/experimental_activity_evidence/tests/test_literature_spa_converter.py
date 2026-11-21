"""SPA converter: the sheet's effect and variance, the criteria mapping and the null reasons, with the arithmetic worked by hand."""
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
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # fewer than three: not supported
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


def test_the_sheet_judges_the_excess_as_a_minimum_with_a_degree_rising_from_the_zero_agreement_limit():
    record = synthetic_record()
    for value, expected, degree in ((100.0, 'supported', 1.0), (500.0, 'supported', 1.0), (55.0, 'supported', 0.5), (10.0, 'conflicting', None), (1.0, 'conflicting', None)):
        record['quantities']['nonspecific_excess'] = point(value, 'ratio', 'e', ['s'])
        verdict = judged(record, 'nonspecific_excess')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), value


def test_the_sheet_gives_a_count_minimum_and_a_duration_no_degree():
    record = synthetic_record()
    record['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, expected in ((30.0, 'unknown'), (29.0, 'conflicting'), (5.0, 'conflicting'), (240.0, 'unknown')):
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        verdict = judged(record, 'equilibrium')
        assert verdict['status'] == expected and 'degree' not in verdict, minutes
    for count, expected in ((8, 'supported'), (7, 'conflicting')):
        record['concentration_series']['value'] = [0.5 * 2 ** step for step in range(count)]
        record['concentration_series']['value'][-1] = 100.0
        verdict = judged(record, 'radioligand_range')
        assert verdict['status'] == expected and (('degree' in verdict) == (expected == 'supported')), count


def test_the_degree_of_a_sheet_criterion_is_the_weakest_member_degree():
    record = synthetic_record()
    record['quantities']['percent_bound'] = point(20.0, 'percent', 'p', ['s'])                      # 0.5
    record['quantities']['nonspecific_fraction'] = point(65.0, 'percent', 'f', ['s'])               # 0.5
    record['quantities']['bead_only_fraction'] = point(35.0, 'percent', 'b', ['s'])                 # 0.5 (a member of binding_controls)
    record['quantities']['nonspecific_excess'] = point(32.5, 'ratio', 'e', ['s'])                   # 0.25 (binding_controls)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['degree'] == pytest.approx(0.5) and interpretations['binding_controls']['degree'] == pytest.approx(0.25)
    assert 'degree' not in interpretations['sampling_basis'] and 'degree' in interpretations['binding_parameter_definition']      # the Hill slope and the Cheng-Prusoff gap are continuous: degree 1.0
    assert interpretations['binding_parameter_definition']['degree'] == 1.0


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert 'degree' not in base['sampling_basis'] and base['binding_controls']['degree'] == 1.0
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
