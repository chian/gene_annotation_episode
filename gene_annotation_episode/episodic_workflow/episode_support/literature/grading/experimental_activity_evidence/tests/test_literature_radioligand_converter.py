"""Radioligand converter: the sheet's effect and variance, the criteria mapping and the null reasons, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import (
    CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_FACTOR, CRITERIA_MAP, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MAX_HILL, MAX_HILL_ZERO_AGREEMENT, MAX_NONSPECIFIC_FRACTION,
    MAX_PERCENT_BOUND, MAX_RADIOLIGAND_OVER_KD, MIN_CONCENTRATIONS, MIN_HILL, MIN_HILL_ZERO_AGREEMENT, MIN_INCUBATION_MIN, MIN_NONSPECIFIC_EXCESS, MIN_REPLICATES, NONSPECIFIC_EXCESS_ZERO_AGREEMENT,
    NONSPECIFIC_FRACTION_ZERO_AGREEMENT, PERCENT_BOUND_ZERO_AGREEMENT, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT, convert_radioligand)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import CRITERIA, grade_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.radioligand_cases import real_record, sparse_record, synthetic_record


def convert(record):
    return convert_radioligand(grade_radioligand(record))


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
    record['facts']['filter_binding_checked'] = fact('no', ['s'])
    record['quantities']['percent_bound'] = point(60.0, 'percent', 'p', ['s'])            # beyond the zero-agreement limit of 50
    record['facts']['equilibrium_reached'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MAX_PERCENT_BOUND, PERCENT_BOUND_ZERO_AGREEMENT, MAX_NONSPECIFIC_FRACTION, NONSPECIFIC_FRACTION_ZERO_AGREEMENT, MIN_NONSPECIFIC_EXCESS, NONSPECIFIC_EXCESS_ZERO_AGREEMENT) == (10.0, 50.0, 50.0, 90.0, 100.0, 1.0)
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, MAX_RADIOLIGAND_OVER_KD, RADIOLIGAND_OVER_KD_ZERO_AGREEMENT) == (8, 0.25, 1.0, 5.0, 1.0, 1.0, 10.0)
    assert (MIN_INCUBATION_MIN, MIN_HILL, MIN_HILL_ZERO_AGREEMENT, MAX_HILL, MAX_HILL_ZERO_AGREEMENT, CHENG_PRUSOFF_FACTOR, CHENG_PRUSOFF_ZERO_FACTOR, MIN_REPLICATES) == (30.0, 0.8, 0.5, 1.2, 1.5, 1.5, 5.0, 3)


def test_a_degree_travels_with_the_sheet_criterion_and_is_the_smallest_of_its_members():
    record = synthetic_record()
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'])            # halfway from 10 to 50: a degree of 0.5
    record['quantities']['nonspecific_fraction'] = point(58.0, 'percent', 'f', ['s'])      # (90 - 58) / 40 = 0.8; the smaller one is kept
    converted = convert(record)
    interpretation = converted['extraction']['interpretations']['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    assert converted['sheet']['interpretations']['calibration_applicability']['degree'] == interpretation['degree']
    record['quantities']['hill_slope'] = point(0.65, 'ratio', 'h', ['s'])                 # a degree of 0.5 below one
    interpretation = convert(record)['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    assert convert(record)['extraction']['interpretations']['binding_controls']['degree'] == 1.0      # its one continuous member (the non-specific excess) is at full agreement
    assert 'degree' not in convert(record)['extraction']['interpretations']['sampling_basis']        # a count minimum carries none


def _interpretations(record):
    return convert(record)['extraction']['interpretations']


def test_a_criterion_resting_on_a_field_with_thin_support_gets_the_support_degree():
    assert 'degree' not in _interpretations(synthetic_record())['sampling_basis']         # all direct: unchanged, no degree where there was none
    record = synthetic_record()
    record['facts']['independent_experiments'] = fact('yes', ['s'], 'implied')
    interpretation = _interpretations(record)['sampling_basis']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.7)
    record['quantities']['replicate_count'] = point(3, 'count', 'r', ['s'], support='about_something_else')      # the weakest member field decides
    assert _interpretations(record)['sampling_basis']['degree'] == pytest.approx(0.3)
    assert 'degree' not in _interpretations(synthetic_record())['sampling_basis']         # another record is untouched


def test_the_support_degree_multiplies_a_degree_the_sheet_already_has():
    record = synthetic_record()
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'])            # a degree of 0.5
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5)
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'], support='implied')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5 * 0.7)
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'], support='about_something_else')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5 * 0.3)
    record['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'], support='direct')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5)      # direct: unchanged


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
