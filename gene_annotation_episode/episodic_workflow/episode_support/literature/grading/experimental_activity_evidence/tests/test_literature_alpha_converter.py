"""AlphaScreen converter: the sheet's effect and variance, the criteria mapping and the null reasons, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MIN_CONCENTRATIONS, MIN_INCUBATION_MIN, MIN_REPLICATES, MIN_SIGNAL_OVER_BACKGROUND,
    MIN_Z_PRIME, SIGNAL_WINDOW_ZERO_AGREEMENT, Z_PRIME_ZERO_AGREEMENT, convert_alpha)
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


def test_a_degree_travels_with_the_sheet_criterion_and_is_the_smallest_of_its_members():
    record = synthetic_record()
    record['quantities']['signal_to_background'] = point(5.5, 'ratio', 'm', ['s'])        # halfway from 1 up to 10: a degree of 0.5
    record['quantities']['z_prime'] = point(0.4, 'ratio', 'z', ['s'])                      # 0.4 of 0.5: a degree of 0.8; the smaller one is kept
    converted = convert(record)
    interpretation = converted['extraction']['interpretations']['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    assert converted['sheet']['interpretations']['calibration_applicability']['degree'] == interpretation['degree']
    record['quantities']['ki'] = point(120.0, 'nM', 'k', ['s'])                            # 6 fold from the KD: a degree of 4 / 7 (the series spans the KD fully)
    interpretation = convert(record)['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(4.0 / 7.0)
    assert 'degree' not in convert(record)['extraction']['interpretations']['binding_controls'] and 'degree' not in convert(record)['extraction']['interpretations']['sampling_basis']


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
    record['quantities']['signal_to_background'] = point(5.5, 'ratio', 'm', ['s'])        # a degree of 0.5
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5)
    record['quantities']['signal_to_background'] = point(5.5, 'ratio', 'm', ['s'], support='implied')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5 * 0.7)
    record['quantities']['signal_to_background'] = point(5.5, 'ratio', 'm', ['s'], support='about_something_else')
    assert _interpretations(record)['calibration_applicability']['degree'] == pytest.approx(0.5 * 0.3)
    record['quantities']['signal_to_background'] = point(5.5, 'ratio', 'm', ['s'], support='direct')
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
