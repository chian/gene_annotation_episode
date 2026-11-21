"""FCS converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import (
    CRITERIA_MAP, DIFFUSION_RATIO_ZERO_AGREEMENT, FRACTION_BOUND_ZERO_AGREEMENT_PERCENT, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LABELLED_MAX_OVER_KD, LABELLED_OVER_KD_ZERO_AGREEMENT, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR,
    MASS_CONSISTENCY_FACTOR, MASS_CONSISTENCY_ZERO_FACTOR, MAX_LABELLED_NM, MAX_PARTICLE_NUMBER, MIN_CONCENTRATIONS, MIN_DIFFUSION_RATIO, MIN_FRACTION_BOUND_MAXIMUM_PERCENT, MIN_INCUBATION_MIN, MIN_LABELLED_NM, MIN_PARTICLE_NUMBER,
    MIN_REPLICATES, MIN_TOTAL_ACQUISITION_S, NULL_REASONS, convert_fcs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import CRITERIA, grade_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fcs_cases import sparse_record, synthetic_record


def test_every_fcs_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) <= set(CRITERIA)
    assert set(CRITERIA) - set(mapped) == set()


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_fcs(grade_fcs(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'fcs'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert converted['extraction']['quantities']['effect']['measurement_keys'] == ['fcs_kd:exp_synthetic_fcs_1']
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_other_converters_and_nulls_have_reasons():
    converted = convert_fcs(grade_fcs(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_the_titrant_and_the_labelled_partner_and_have_no_surface():
    converted = convert_fcs(grade_fcs(synthetic_record(titrant_prep='ti', fixed_prep='la', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'ti', 'immobilized_preparation_ref': 'la', 'surface_ref': None, 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_titrations_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent titrations: variance 36 / 3 = 12
    assert convert_fcs(grade_fcs(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['facts']['independent_titrations'] = fact('unknown')
    converted = convert_fcs(grade_fcs(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_a_confidence_interval_is_not_converted_and_an_unstated_kind_gives_no_variance():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    converted = convert_fcs(grade_fcs(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None and converted['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['spread_kind'] = None
    assert convert_fcs(grade_fcs(r))['null_components']['effect_variance'] == 'spread_kind_not_stated'


def test_a_picomolar_spread_and_kd_are_converted_to_nanomolar():
    r = synthetic_record()
    r['quantities']['kd'] = point(94.0, 'pM', 'kd', ['s'])
    r['quantities']['kd_spread'] = point(10.0, 'pM', 'sp', ['s'])
    cells = convert_fcs(grade_fcs(r))['sheet']['cells']
    # KD 94 pM = 0.094 nM; standard error 10 pM = 0.01 nM -> variance 1e-4 nM^2
    assert cells['measured_effect']['value'] == pytest.approx(0.094) and cells['effect_variance']['value'] == pytest.approx(1e-4)


def test_no_kd_leaves_the_effect_null_with_a_reason_and_no_variance():
    r = synthetic_record()
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_fcs(grade_fcs(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'no_kd_given_as_a_point_value'
    assert converted['null_components']['effect_variance'] == 'no_effect_to_carry_a_variance'


def test_the_sparse_record_has_an_effect_and_no_variance_and_unknown_criteria():
    converted = convert_fcs(grade_fcs(sparse_record()))
    assert converted['sheet']['cells']['measured_effect']['value'] == 20.0 and converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_a_small_diffusion_change_and_a_mismatch_with_the_mass_make_the_calibration_criterion_conflict():
    r = synthetic_record()
    r['quantities']['mass_ratio'] = point(0.1, 'ratio', 'm', ['s'])                        # expected 0.46, reported 1.8: a factor 3.9, beyond 3
    assert convert_fcs(grade_fcs(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'
    r = synthetic_record()
    r['quantities']['bound_diffusion_time'] = point(60.0, 'us', 'b', ['s'])                # no change of the diffusion at all
    assert convert_fcs(grade_fcs(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_DIFFUSION_RATIO, DIFFUSION_RATIO_ZERO_AGREEMENT, MASS_CONSISTENCY_FACTOR, MASS_CONSISTENCY_ZERO_FACTOR, MIN_FRACTION_BOUND_MAXIMUM_PERCENT, FRACTION_BOUND_ZERO_AGREEMENT_PERCENT) == (1.3, 1.0, 1.5, 3.0, 80.0, 20.0)
    assert (MIN_PARTICLE_NUMBER, MAX_PARTICLE_NUMBER, MIN_LABELLED_NM, MAX_LABELLED_NM, LABELLED_MAX_OVER_KD, LABELLED_OVER_KD_ZERO_AGREEMENT) == (0.1, 10.0, 0.3, 30.0, 1.0, 10.0)
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, MIN_INCUBATION_MIN, MIN_TOTAL_ACQUISITION_S, MIN_REPLICATES) == (8, 0.2, 1.0, 10.0, 1.0, 5.0, 60.0, 3)


def test_a_degree_travels_with_the_sheet_criterion_and_is_the_smallest_of_its_members():
    r = synthetic_record()
    r['quantities']['bound_diffusion_time'] = point(66.0, 'us', 'b', ['s'])                # ratio 1.1: degree (1.1 - 1) / 0.3
    r['quantities']['mass_ratio'] = point(1.5, 'ratio', 'm', ['s'])                        # expected 1.1447: a factor 1.1 / 1.1447 off, inside 1.5: full degree
    converted = convert_fcs(grade_fcs(r))
    interpretation = converted['extraction']['interpretations']['calibration_applicability']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(1.0 / 3.0)
    assert converted['sheet']['interpretations']['calibration_applicability']['degree'] == interpretation['degree']
    assert 'degree' not in converted['extraction']['interpretations']['binding_controls'] and 'degree' not in converted['extraction']['interpretations']['sampling_basis']
    r['quantities']['fraction_bound_maximum'] = point(50.0, 'percent', 'f', ['s'])         # a plateau only half reached: degree 0.5
    assert convert_fcs(grade_fcs(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)


def _interpretations(record):
    return convert_fcs(grade_fcs(record))['extraction']['interpretations']


def test_a_criterion_resting_on_a_field_with_thin_support_gets_the_support_degree():
    assert 'degree' not in _interpretations(synthetic_record())['binding_controls']       # all direct: unchanged, no degree where there was none
    r = synthetic_record()
    r['facts']['triplet_state_modelled'] = fact('yes', ['s'], 'implied')
    interpretation = _interpretations(r)['binding_controls']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.7)
    r['facts']['aggregates_checked'] = fact('yes', ['s'], 'about_something_else')          # the weakest member field decides
    interpretation = _interpretations(r)['binding_controls']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.3)
    assert _interpretations(r)['sampling_basis'].get('degree') is None                    # other sheet criteria are untouched


def test_the_support_degree_multiplies_a_degree_the_sheet_already_has():
    r = synthetic_record()
    r['quantities']['bound_diffusion_time'] = point(66.0, 'us', 'b', ['s'])                # ratio 1.1: degree 1/3
    assert _interpretations(r)['calibration_applicability']['degree'] == pytest.approx(1.0 / 3.0)
    r['quantities']['free_diffusion_time'] = point(60.0, 'us', 'f', ['s'], support='implied')
    assert _interpretations(r)['calibration_applicability']['degree'] == pytest.approx(1.0 / 3.0 * 0.7)
    r['quantities']['mass_ratio'] = point(1.5, 'ratio', 'm', ['s'], support='about_something_else')
    assert _interpretations(r)['calibration_applicability']['degree'] == pytest.approx(1.0 / 3.0 * 0.3)
    direct = synthetic_record()
    direct['quantities']['fraction_bound_maximum'] = point(50.0, 'percent', 'f', ['s'], support='direct')
    assert _interpretations(direct)['binding_regime']['degree'] == pytest.approx(0.5)      # direct: unchanged


def test_a_choice_field_and_the_variance_rest_on_their_support_too():
    r = synthetic_record()
    r['choice_support']['fit_model'] = 'implied'
    assert _interpretations(r)['binding_parameter_definition']['degree'] == pytest.approx(0.7)
    r = synthetic_record()
    r['quantities']['kd_spread'] = point(2.0, 'nM', 'sp', ['s'], support='implied')
    assert _interpretations(r)['variance_correspondence']['degree'] == pytest.approx(0.7)
    r['choice_support']['spread_kind'] = 'about_something_else'
    assert _interpretations(r)['variance_correspondence']['degree'] == pytest.approx(0.3)


def test_support_never_changes_a_status_and_a_conflicting_or_unknown_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['triplet_state_modelled'] = fact('no', ['s'], 'about_something_else')
    interpretation = _interpretations(r)['binding_controls']
    assert interpretation['status'] == 'conflicting' and 'degree' not in interpretation
    r['facts']['triplet_state_modelled'] = fact('unknown')
    interpretation = _interpretations(r)['binding_controls']
    assert interpretation['status'] == 'unknown' and 'degree' not in interpretation
    assert {name: item['status'] for name, item in _interpretations(synthetic_record()).items()} == {name: 'supported' for name in _interpretations(synthetic_record())}


def test_a_one_component_fit_without_reference_values_makes_the_parameter_definition_unknown_not_conflicting():
    r = synthetic_record()
    r['diffusion_model'] = 'one_component'
    for name in ('bound_diffusion_time', 'free_diffusion_coefficient'):
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
    assert convert_fcs(grade_fcs(r))['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'
