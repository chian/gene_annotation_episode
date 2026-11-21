"""ITC converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import (
    C_VALUE_MAX, C_VALUE_MIN, C_VALUE_ZERO_MAX, C_VALUE_ZERO_MIN, DG_TOLERANCE_KJ_PER_MOL, DG_ZERO_KJ_PER_MOL, MIN_INJECTIONS, MIN_REPLICATE_TITRATIONS, N_OVER_EXPECTED_MAX, N_OVER_EXPECTED_MIN, N_OVER_EXPECTED_ZERO_MAX,
    N_OVER_EXPECTED_ZERO_MIN, NULL_REASONS, STOICHIOMETRY_MIN, STOICHIOMETRY_STEP, STOICHIOMETRY_STEP_TOLERANCE, STOICHIOMETRY_STEP_ZERO, STOICHIOMETRY_ZERO_MIN, TEMPERATURE_MAX_K, TEMPERATURE_MIN_K, _criterion, convert_itc)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import grade_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import sparse_record, synthetic_record


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_itc(grade_itc(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'itc'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'binding_species', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_spr_converter_and_nulls_have_reasons():
    converted = convert_itc(grade_itc(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_syringe_as_analyte_and_cell_as_immobilized():
    converted = convert_itc(grade_itc(synthetic_record(syringe_prep='syr', cell_prep='cel', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'syr', 'immobilized_preparation_ref': 'cel', 'surface_ref': None, 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_titrations_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent titrations: variance 36 / 3 = 12
    assert convert_itc(grade_itc(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['facts']['independent_titrations'] = fact('unknown')
    converted = convert_itc(grade_itc(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_missing_kd_and_confidence_interval_stay_null():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    assert convert_itc(grade_itc(r))['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_itc(grade_itc(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'kd_not_given_as_a_point_value'


def test_sparse_record_fills_only_the_effect():
    converted = convert_itc(grade_itc(sparse_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == 20.0
    assert cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_conflicting_unknown_and_not_applicable_members_combine_by_the_rule():
    r = synthetic_record()
    r['facts']['buffer_matching'] = fact('not_matched', ['s'])
    r['facts']['dilution_control_performed'] = fact('unknown')
    interpretations = convert_itc(grade_itc(r))['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting'
    r = synthetic_record()
    r['quantities']['entropy'] = {**r['quantities']['entropy'], 'status': 'unavailable', 'value': None}
    r['facts']['residuals_reported'] = fact('unknown')
    # thermodynamic_consistency is not_applicable and dropped; fit_model_appropriate is unknown
    assert convert_itc(grade_itc(r))['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'
    r['facts']['residuals_reported'] = fact('yes', ['s'])
    assert convert_itc(grade_itc(r))['extraction']['interpretations']['binding_parameter_definition']['status'] == 'supported'


def judged(record, name):
    return _criterion(grade_itc(record), name)


def degree_of(verdict):
    return verdict.get('degree')


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (N_OVER_EXPECTED_MIN, N_OVER_EXPECTED_ZERO_MIN, N_OVER_EXPECTED_MAX, N_OVER_EXPECTED_ZERO_MAX) == (0.7, 0.3, 1.3, 2.0)
    assert (C_VALUE_MIN, C_VALUE_ZERO_MIN, C_VALUE_MAX, C_VALUE_ZERO_MAX, MIN_INJECTIONS, TEMPERATURE_MIN_K, TEMPERATURE_MAX_K, MIN_REPLICATE_TITRATIONS) == (1.0, 0.1, 1000.0, 10000.0, 15, 278.15, 323.15, 3)
    assert (STOICHIOMETRY_MIN, STOICHIOMETRY_ZERO_MIN, STOICHIOMETRY_STEP, STOICHIOMETRY_STEP_TOLERANCE, STOICHIOMETRY_STEP_ZERO, DG_TOLERANCE_KJ_PER_MOL, DG_ZERO_KJ_PER_MOL) == (0.4, 0.2, 0.5, 0.15, 0.25, 2.0, 10.0)


def test_the_sheet_judges_n_over_the_expected_n_with_a_degree_and_unknown_facts():
    r = synthetic_record()                                                                     # expected n 1.0
    for n, expected, degree in ((1.0, 'supported', 1.0), (0.7, 'supported', 1.0), (1.3, 'supported', 1.0), (0.5, 'supported', 0.5), (1.65, 'supported', 0.5), (0.3, 'conflicting', None), (2.0, 'conflicting', None), (2.5, 'conflicting', None)):
        r['quantities']['stoichiometry'] = point(n, 'dimensionless', 'n', ['s'])
        verdict = judged(r, 'concentration_accuracy_and_active_fraction')
        assert verdict['status'] == expected and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), n
    r['quantities']['stoichiometry'] = point(0.5, 'dimensionless', 'n', ['s'])
    r['facts']['concentrations_determined'] = fact('unknown')
    assert judged(r, 'concentration_accuracy_and_active_fraction') == {'status': 'unknown', 'support_refs': []}
    r['quantities']['stoichiometry'] = point(0.25, 'dimensionless', 'n', ['s'])
    assert judged(r, 'concentration_accuracy_and_active_fraction')['status'] == 'conflicting'      # a ratio beyond the zero limit stays conflicting whatever the facts say


def test_the_sheet_judges_the_c_value_with_a_degree():
    r = synthetic_record()                                                                     # n 1.0, KD 20 nM: c = cell / 20
    for cell, unit, expected, degree in ((20.0, 'nM', 'supported', 1.0), (20.0, 'uM', 'supported', 1.0), (11.0, 'nM', 'supported', 0.5), (110.0, 'uM', 'supported', 0.5), (2.0, 'nM', 'conflicting', None), (200.0, 'uM', 'conflicting', None)):
        r['quantities']['cell_concentration'] = point(cell, unit, 'cell', ['s'])
        verdict = judged(r, 'c_value_window')
        assert verdict['status'] == expected and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), (cell, unit)
        assert verdict['support_refs'] == ['span_exp_synthetic_itc_1', 's']


def test_the_sheet_judges_the_injection_count_without_a_degree():
    r = synthetic_record()
    for count, expected in ((15, 'supported'), (14, 'conflicting'), (40, 'supported')):
        r['quantities']['injection_count'] = point(count, 'count', 'i', ['s'])
        verdict = judged(r, 'injections_sufficient')
        assert verdict == {'status': expected, 'support_refs': ['s']}, count


def test_the_sheet_judges_the_temperature_range_and_the_control_answer():
    r = synthetic_record()
    for kelvin, expected in ((278.15, 'supported'), (278.1, 'conflicting'), (323.15, 'supported'), (323.2, 'conflicting')):
        r['quantities']['temperature'] = point(kelvin, 'K', 't', ['s'])
        assert judged(r, 'temperature_stated_and_controlled')['status'] == expected, kelvin
        assert 'degree' not in judged(r, 'temperature_stated_and_controlled')
    r['quantities']['temperature'] = point(298.15, 'K', 't', ['s'])
    r['facts']['temperature_controlled'] = fact('unknown')
    assert judged(r, 'temperature_stated_and_controlled') == {'status': 'unknown', 'support_refs': []}
    r['facts']['temperature_controlled'] = fact('not_applicable')
    assert judged(r, 'temperature_stated_and_controlled')['status'] == 'not_applicable'


def test_the_sheet_judges_the_replicate_count_and_its_independence():
    r = synthetic_record()
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert judged(r, 'replicate_titrations_independent')['status'] == expected, (count, independent)
        assert 'degree' not in judged(r, 'replicate_titrations_independent')


def test_the_sheet_judges_the_fitted_n_and_its_distance_from_a_simple_ratio_with_a_degree():
    r = synthetic_record()
    for n, expected, degree in ((1.0, 'supported', 1.0), (0.4, 'supported', 1.0), (1.1, 'supported', 1.0), (0.3, 'supported', 0.5), (1.2, 'supported', 0.5), (1.7, 'supported', 0.5), (1.25, 'conflicting', None), (0.2, 'conflicting', None), (0.1, 'conflicting', None)):
        r['quantities']['stoichiometry'] = point(n, 'dimensionless', 'n', ['s'])
        verdict = judged(r, 'stoichiometry_consistency')
        assert verdict['status'] == expected and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), n
    r['quantities']['stoichiometry'] = point(1.0, 'dimensionless', 'n', ['s'])
    r['facts']['n_fitted_freely'] = fact('unknown')
    assert judged(r, 'stoichiometry_consistency') == {'status': 'unknown', 'support_refs': []}


def test_the_sheet_judges_the_free_energy_gap_with_a_degree():
    r = synthetic_record()
    for entropy, expected in ((-20.3, 'supported'), (-30.0, 'supported'), (0.0, 'supported'), (-60.0, 'conflicting')):
        r['quantities']['entropy'] = point(entropy, 'J/mol/K', 's', ['s'])
        graded = grade_itc(r)
        gap = graded['native']['dg_gap_kJ_per_mol']
        verdict = _criterion(graded, 'thermodynamic_consistency')
        assert verdict['status'] == expected, entropy
        if expected == 'supported':
            assert verdict['degree'] == pytest.approx(min(1.0, (10.0 - gap) / 8.0)), entropy
        else:
            assert gap > 10.0 and 'degree' not in verdict
    assert grade_itc(r)['native']['dg_gap_kJ_per_mol'] > 10.0


def test_a_member_degree_reaches_the_sheet_interpretation_as_the_smallest_one():
    r = synthetic_record()
    r['quantities']['cell_concentration'] = point(11.0, 'nM', 'cell', ['s'])                  # c 0.55: degree 0.5
    interpretation = convert_itc(grade_itc(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    assert convert_itc(grade_itc(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert 'degree' not in convert_itc(grade_itc(synthetic_record()))['extraction']['interpretations']['sampling_basis']


def interpretations_of(record):
    return convert_itc(grade_itc(record))['extraction']['interpretations']


def test_the_support_degrees_are_the_shared_constants():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORT_DEGREE
    assert SUPPORT_DEGREE == {'direct': 1.0, 'implied': 0.7, 'about_something_else': 0.3}


def test_a_criterion_resting_on_a_weakly_supported_fact_gets_the_support_degree_and_direct_changes_nothing():
    assert 'degree' not in interpretations_of(synthetic_record())['binding_controls']
    for support, degree in (('direct', None), ('implied', 0.7), ('about_something_else', 0.3)):
        r = synthetic_record()
        r['facts']['baseline_corrected'] = fact('yes', ['s'], support=support)
        got = interpretations_of(r)['binding_controls']
        assert got['status'] == 'supported'
        assert 'degree' not in got if degree is None else got['degree'] == pytest.approx(degree), support


def test_the_support_degree_multiplies_an_existing_degree_and_the_weakest_field_counts_once():
    r = synthetic_record()
    r['quantities']['cell_concentration'] = point(11.0, 'nM', 'cell', ['s'])                    # c-value degree 0.5
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.5)
    r['quantities']['cell_concentration'] = point(11.0, 'nM', 'cell', ['s'], support='implied')
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.35)
    r['quantities']['kd'] = point(20.0, 'nM', 'kd', ['s'], support='about_something_else')
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.15)             # 0.5 x 0.3, not 0.5 x 0.7 x 0.3


def test_support_never_changes_a_status_and_a_conflicting_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['baseline_corrected'] = fact('no', ['s'], support='implied')
    got = interpretations_of(r)['binding_controls']
    assert got['status'] == 'conflicting' and 'degree' not in got
    r['facts']['baseline_corrected'] = fact('unknown')
    got = interpretations_of(r)['binding_controls']
    assert got['status'] == 'unknown' and 'degree' not in got
    weak = synthetic_record()
    for name in weak['facts']:
        weak['facts'][name] = fact(weak['facts'][name]['answer'], ['s'], support='about_something_else')
    assert {k: v['status'] for k, v in interpretations_of(weak).items()} == {k: v['status'] for k, v in interpretations_of(synthetic_record()).items()}
