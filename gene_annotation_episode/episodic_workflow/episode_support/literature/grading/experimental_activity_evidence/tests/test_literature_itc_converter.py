"""ITC converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import ast
import inspect
import math
import re

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_itc_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import (
    C_VALUE_MAX, C_VALUE_MIN, C_VALUE_ZERO_MAX, C_VALUE_ZERO_MIN, C_VALUE_ZERO_MIN_SATURATED, SATURATION_FULL_OVER_KD, SATURATION_ZERO_OVER_KD, DG_TOLERANCE_KJ_PER_MOL, DG_ZERO_KJ_PER_MOL, INJECTIONS_ZERO, MIN_INJECTIONS, MIN_REPLICATE_TITRATIONS, N_OVER_EXPECTED_MAX, N_OVER_EXPECTED_MIN, N_OVER_EXPECTED_ZERO_MAX,
    N_OVER_EXPECTED_ZERO_MIN, NULL_REASONS, STOICHIOMETRY_MIN, STOICHIOMETRY_STEP, STOICHIOMETRY_STEP_TOLERANCE, STOICHIOMETRY_STEP_ZERO, STOICHIOMETRY_ZERO_MIN, TEMPERATURE_MAX_K, TEMPERATURE_MIN_K,
    TEMPERATURE_ZERO_MAX_K, TEMPERATURE_ZERO_MIN_K, _criterion, convert_itc)
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


def credit(verdict):
    """A judged verdict as a number for the monotonicity checks: conflicting 0, supported its degree."""
    return {'conflicting': 0.0, 'supported': verdict.get('degree')}[verdict['status']]


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (N_OVER_EXPECTED_MIN, N_OVER_EXPECTED_ZERO_MIN, N_OVER_EXPECTED_MAX, N_OVER_EXPECTED_ZERO_MAX) == (0.7, 0.3, 1.3, 2.0)
    assert (C_VALUE_MIN, C_VALUE_ZERO_MIN, C_VALUE_MAX, C_VALUE_ZERO_MAX, MIN_INJECTIONS, TEMPERATURE_MIN_K, TEMPERATURE_MAX_K, MIN_REPLICATE_TITRATIONS) == (1.0, 0.1, 1000.0, 10000.0, 15, 278.15, 323.15, 3)
    assert (INJECTIONS_ZERO, TEMPERATURE_ZERO_MIN_K, TEMPERATURE_ZERO_MAX_K) == (3, 275.15, 353.15)
    assert (STOICHIOMETRY_MIN, STOICHIOMETRY_ZERO_MIN, STOICHIOMETRY_STEP, STOICHIOMETRY_STEP_TOLERANCE, STOICHIOMETRY_STEP_ZERO, DG_TOLERANCE_KJ_PER_MOL, DG_ZERO_KJ_PER_MOL) == (0.4, 0.2, 0.5, 0.15, 0.25, 2.0, 10.0)


def test_every_number_the_converter_judges_with_is_a_named_expert_review_constant():
    source = inspect.getsource(literature_itc_converter)
    numeric = [line for line in source.splitlines() if re.match(r'^[A-Z_]+ = -?[0-9]', line)]
    assert numeric and all('# EXPERT_REVIEW: ' in line for line in numeric)
    for function in (literature_itc_converter._counted, literature_itc_converter._judge_injections, literature_itc_converter._judge_temperature, literature_itc_converter._judge_replicates,
                     literature_itc_converter._judge_c_value, literature_itc_converter._judge_stoichiometry, literature_itc_converter._judge_free_energies, literature_itc_converter._judge_titration_mode):
        literals = {node.value for node in ast.walk(ast.parse(inspect.getsource(function))) if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)}
        assert literals <= {0, 1.0}, function.__name__


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


HALF_DECADE = math.sqrt(10.0)
CELL_NM_FOR_C_HALF_DEGREE = 20.0 * C_VALUE_ZERO_MIN * HALF_DECADE                                # c = 0.316, half a decade below the window: degree 0.5


def test_the_sheet_judges_the_c_value_with_a_degree_linear_in_log_c():
    r = synthetic_record()                                                                     # n 1.0, KD 20 nM: c = cell / 20
    # degree linear in log10(c): c 0.55 -> log10(5.5); c 5500 -> 4 - log10(5500); half a decade outside either end -> 0.5
    for cell, unit, expected, degree in ((20.0, 'nM', 'supported', 1.0), (20.0, 'uM', 'supported', 1.0), (11.0, 'nM', 'supported', math.log10(5.5)), (110.0, 'uM', 'supported', 4.0 - math.log10(5500.0)),
                                         (CELL_NM_FOR_C_HALF_DEGREE, 'nM', 'supported', 0.5), (20.0 * C_VALUE_MAX * HALF_DECADE, 'nM', 'supported', 0.5),
                                         (2.0, 'nM', 'conflicting', None), (200.0, 'uM', 'conflicting', None)):
        r['quantities']['cell_concentration'] = point(cell, unit, 'cell', ['s'])
        verdict = judged(r, 'c_value_window')
        assert verdict['status'] == expected and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), (cell, unit)
        assert verdict['support_refs'] == ['span_exp_synthetic_itc_1', 's']


def test_the_c_value_degree_is_monotone_towards_the_window_and_each_decade_costs_the_same():
    r = synthetic_record()
    rising, falling = [], []
    for step in range(0, 41):
        r['quantities']['cell_concentration'] = point(20.0 * 10 ** (-1.2 + step * 0.03), 'nM', 'cell', ['s'])          # c from 0.063 to 1.0
        rising.append(credit(judged(r, 'c_value_window')))
        r['quantities']['cell_concentration'] = point(20.0 * 10 ** (3.0 + step * 0.03), 'nM', 'cell', ['s'])           # c from 1000 to 15800
        falling.append(credit(judged(r, 'c_value_window')))
    assert rising == sorted(rising) and falling == sorted(falling, reverse=True)
    assert all(0.0 <= c <= 1.0 for c in rising + falling)
    def degree_at(c):
        r['quantities']['cell_concentration'] = point(20.0 * c, 'nM', 'cell', ['s'])
        return judged(r, 'c_value_window')['degree']
    # a factor of 2 costs the same wherever it lies beyond an end (the old linear ramp made 1000 -> 2000 and 4000 -> 8000 unequal)
    assert degree_at(1000.0) - degree_at(2000.0) == pytest.approx(degree_at(4000.0) - degree_at(8000.0))
    assert degree_at(0.5) - degree_at(0.25) == pytest.approx(degree_at(1.0) - degree_at(0.5))
    assert 0.9 < degree_at(0.9) < 1.0 and 0.9 < degree_at(1100.0) < 1.0                                          # no step at either end of the window


def test_the_sheet_judges_the_injection_count_gradually_around_the_researched_minimum():
    r = synthetic_record()
    # degree = sqrt((count - 3) / (15 - 3)) below 15, 1.0 from 15; no credit at 3 or fewer (no residual degree of freedom), never conflicting
    for count, expected, degree in ((15, 'supported', 1.0), (40, 'supported', 1.0), (14, 'supported', math.sqrt(11 / 12)), (9, 'supported', math.sqrt(0.5)), (4, 'supported', math.sqrt(1 / 12)), (3, 'supported', 0.0), (2, 'supported', 0.0)):
        r['quantities']['injection_count'] = point(count, 'count', 'i', ['s'])
        verdict = judged(r, 'injections_sufficient')
        assert verdict['status'] == expected and verdict['support_refs'] == ['s'] and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), count
    credits = []
    for count in range(1, 41):
        r['quantities']['injection_count'] = point(count, 'count', 'i', ['s'])
        credits.append(credit(judged(r, 'injections_sufficient')))
    assert credits == sorted(credits) and all(0.0 <= c <= 1.0 for c in credits)                 # monotone and bounded
    assert 0.9 < credits[MIN_INJECTIONS - 2] < 1.0                                               # no step: just below 15 keeps most of the credit


def test_the_sheet_judges_the_temperature_gradually_and_then_the_control_answer():
    r = synthetic_record()
    for kelvin, expected, degree in ((278.15, 'supported', 1.0), (298.15, 'supported', 1.0), (323.15, 'supported', 1.0), (276.65, 'supported', 0.5), (338.15, 'supported', 0.5), (278.1, 'supported', (278.1 - 275.15) / 3.0), (323.2, 'supported', (353.15 - 323.2) / 30.0),
                                     (275.15, 'conflicting', None), (353.15, 'conflicting', None), (360.0, 'conflicting', None)):
        r['quantities']['temperature'] = point(kelvin, 'K', 't', ['s'])
        verdict = judged(r, 'temperature_stated_and_controlled')
        assert verdict['status'] == expected and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), kelvin
    rising, falling = [], []
    for step in range(0, 61):
        r['quantities']['temperature'] = point(272.15 + step * 0.1, 'K', 't', ['s'])
        rising.append(credit(judged(r, 'temperature_stated_and_controlled')))
        r['quantities']['temperature'] = point(320.15 + step * 0.6, 'K', 't', ['s'])
        falling.append(credit(judged(r, 'temperature_stated_and_controlled')))
    assert rising == sorted(rising) and falling == sorted(falling, reverse=True)               # monotone towards the usual window
    assert all(0.0 <= c <= 1.0 for c in rising + falling)
    r['quantities']['temperature'] = point(298.15, 'K', 't', ['s'])
    r['facts']['temperature_controlled'] = fact('unknown')
    assert judged(r, 'temperature_stated_and_controlled') == {'status': 'unknown', 'support_refs': []}
    r['facts']['temperature_controlled'] = fact('not_applicable')
    assert judged(r, 'temperature_stated_and_controlled')['status'] == 'not_applicable'
    r['quantities']['temperature'] = point(360.0, 'K', 't', ['s'])
    assert judged(r, 'temperature_stated_and_controlled')['status'] == 'conflicting'            # beyond the instrument limit, whatever the control answer


def test_the_sheet_judges_the_replicate_count_gradually_and_its_independence():
    r = synthetic_record()
    # degree = sqrt(count / 3) below 3, 1.0 from 3, when the titrations are independent; independence not stated is unknown
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', math.sqrt(2 / 3)), (1, 'yes', 'supported', math.sqrt(1 / 3)),
                                                 (2, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None)):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        verdict = judged(r, 'replicate_titrations_independent')
        assert verdict['status'] == expected and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), (count, independent)
    r['facts']['independent_titrations'] = fact('yes', ['s'])
    credits = []
    for count in range(1, 11):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        credits.append(credit(judged(r, 'replicate_titrations_independent')))
    assert credits == sorted(credits) and all(0.0 < c <= 1.0 for c in credits)                  # monotone, bounded, a single titration keeps partial credit


def without_expected_n(record):
    record['quantities']['expected_stoichiometry'] = {**record['quantities']['expected_stoichiometry'], 'status': 'unavailable', 'value': None}
    return record


def test_without_an_expected_n_the_sheet_judges_the_fitted_n_and_its_distance_from_a_simple_ratio_with_a_degree():
    r = without_expected_n(synthetic_record())
    # between two simple ratios (1.25, 0.75) is no credit, never conflicting; only an n at or below the size floor is conflicting
    for n, expected, degree in ((1.0, 'supported', 1.0), (0.4, 'supported', 1.0), (1.1, 'supported', 1.0), (0.3, 'supported', 0.5), (1.2, 'supported', 0.5), (1.7, 'supported', 0.5),
                                (1.25, 'supported', 0.0), (0.75, 'supported', 0.0), (0.2, 'conflicting', None), (0.1, 'conflicting', None)):
        r['quantities']['stoichiometry'] = point(n, 'dimensionless', 'n', ['s'])
        verdict = judged(r, 'stoichiometry_consistency')
        assert verdict['status'] == expected and degree_of(verdict) == (pytest.approx(degree) if degree is not None else None), n
    credits = []
    for step in range(0, 11):                                                                  # n from 1.0 to 1.25: away from a simple ratio
        r['quantities']['stoichiometry'] = point(1.0 + step * 0.025, 'dimensionless', 'n', ['s'])
        credits.append(credit(judged(r, 'stoichiometry_consistency')))
    assert credits == sorted(credits, reverse=True) and all(0.0 <= c <= 1.0 for c in credits)
    r['quantities']['stoichiometry'] = point(1.0, 'dimensionless', 'n', ['s'])
    r['facts']['n_fitted_freely'] = fact('unknown')
    assert judged(r, 'stoichiometry_consistency') == {'status': 'unknown', 'support_refs': []}
    r['quantities']['stoichiometry'] = point(1.25, 'dimensionless', 'n', ['s'])
    assert judged(r, 'stoichiometry_consistency') == {'status': 'unknown', 'support_refs': []}       # the lattice never overrides an unstated free fit


def test_with_the_expected_n_stated_the_deviation_counts_once_in_binding_species():
    r = synthetic_record()                                                                     # expected n 1.0
    for n in (1.0, 0.75, 1.25, 0.5, 0.33):
        r['quantities']['stoichiometry'] = point(n, 'dimensionless', 'n', ['s'])
        verdict = judged(r, 'stoichiometry_consistency')
        assert verdict['status'] == 'supported' and 'degree' not in verdict, n
    r['quantities']['stoichiometry'] = point(0.5, 'dimensionless', 'n', ['s'])                  # n / expected 0.5: degree 0.5 in binding_species only
    interpretations = interpretations_of(r)
    assert interpretations['binding_species']['degree'] == pytest.approx(0.5)
    assert interpretations['calibration_applicability']['status'] == 'supported' and 'degree' not in interpretations['calibration_applicability']
    r['quantities']['stoichiometry'] = point(1.0, 'dimensionless', 'n', ['s'])
    r['facts']['n_fitted_freely'] = fact('unknown')
    assert judged(r, 'stoichiometry_consistency') == {'status': 'unknown', 'support_refs': []}
    r = synthetic_record()
    r['quantities']['expected_stoichiometry'] = point(0.33, 'dimensionless', 'e', ['s'])          # one ligand per trimer: n 0.33 is the paper's own simple ratio
    r['quantities']['stoichiometry'] = point(0.33, 'dimensionless', 'n', ['s'])
    assert judged(r, 'stoichiometry_consistency')['status'] == 'supported' and 'degree' not in judged(r, 'stoichiometry_consistency')


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
    r['quantities']['cell_concentration'] = point(CELL_NM_FOR_C_HALF_DEGREE, 'nM', 'cell', ['s'])  # c 0.316: degree 0.5
    interpretation = convert_itc(grade_itc(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.5)
    assert convert_itc(grade_itc(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert convert_itc(grade_itc(synthetic_record()))['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(1.0)
    r = synthetic_record()
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                          # two independent titrations: sqrt(2/3)
    assert convert_itc(grade_itc(r))['extraction']['interpretations']['sampling_basis'] == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_itc_1'], 'degree': pytest.approx(math.sqrt(2 / 3))}
    r['quantities']['injection_count'] = point(9, 'count', 'i', ['s'])                          # nine injections: sqrt(1/2) is the weakest member of binding_regime
    assert convert_itc(grade_itc(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(math.sqrt(0.5))


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
    r['quantities']['cell_concentration'] = point(CELL_NM_FOR_C_HALF_DEGREE, 'nM', 'cell', ['s'])  # c-value degree 0.5
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.5)
    r['quantities']['cell_concentration'] = point(CELL_NM_FOR_C_HALF_DEGREE, 'nM', 'cell', ['s'], support='implied')
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


def at_c(r, c, ratio=None):
    r['quantities']['cell_concentration'] = point(20.0 * c, 'nM', 'cell', ['s'])                 # KD 20 nM, n 1.0: c = cell / 20
    r['quantities']['final_molar_ratio'] = point(ratio, 'dimensionless', 'r', ['s_r']) if ratio is not None else synthetic_record()['quantities']['final_molar_ratio']
    return judged(r, 'c_value_window')


def test_a_low_c_titration_taken_past_saturation_lowers_the_zero_end_by_one_decade_smoothly():
    r = synthetic_record()
    assert (SATURATION_ZERO_OVER_KD, SATURATION_FULL_OVER_KD, C_VALUE_ZERO_MIN_SATURATED) == (1.0, 10.0, 0.01)
    assert at_c(r, 0.05) ['status'] == 'conflicting'                                            # no ratio stated: the window is as before
    assert at_c(r, 0.05, ratio=10.0)['status'] == 'conflicting'                                 # final ligand = 0.5 KD: the plateau is not reached
    # final ligand over KD = r c; at c = 0.05 and r = 200 it is 10: the zero end is 0.01, so c = 0.05 gets log10(0.05 / 0.01) / log10(1 / 0.01)
    verdict = at_c(r, 0.05, ratio=200.0)
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(math.log10(5.0) / 2.0) and verdict['support_refs'] == ['span_exp_synthetic_itc_1', 's', 's_r']
    # monotone in the final ratio and in c, bounded, and never above the degree of c = 1
    degrees = [credit(at_c(r, 0.05, ratio=ratio)) for ratio in (20.0, 25.0, 40.0, 80.0, 160.0, 200.0, 2000.0)]
    assert degrees == sorted(degrees) and degrees[-1] == degrees[-2] and all(0.0 <= d < 1.0 for d in degrees)
    by_c = [credit(at_c(r, c, ratio=1000.0)) for c in (0.011, 0.02, 0.05, 0.1, 0.5, 1.0)]
    assert by_c == sorted(by_c) and by_c[-1] == 1.0
    # a ratio makes no difference in or above the window, and a ratio never lowers a degree
    assert credit(at_c(r, 500.0, ratio=3.0)) == credit(at_c(r, 500.0)) == 1.0
    assert credit(at_c(r, 0.5, ratio=1000.0)) >= credit(at_c(r, 0.5))


def test_a_single_injection_or_continuous_titration_does_not_apply_the_injection_count_and_an_unstated_mode_does_as_before():
    r = synthetic_record()
    r['quantities']['injection_count'] = point(1, 'count', 'inj', ['s'])
    assert judged(r, 'injections_sufficient')['status'] == 'supported' and judged(r, 'injections_sufficient')['degree'] == 0.0
    for mode in ('single_injection', 'continuous'):
        r['titration_mode'] = mode
        assert judged(r, 'injections_sufficient') == {'status': 'not_applicable', 'support_refs': []}
    interpretation = convert_itc(grade_itc(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == 1.0         # c and temperature alone
    r['titration_mode'] = 'incremental'
    assert judged(r, 'injections_sufficient')['degree'] == 0.0


def test_an_enthalpy_corrected_for_buffer_ionization_is_not_compared_with_the_free_energy_of_the_fit():
    r = synthetic_record()
    r['quantities']['entropy'] = point(50.0, 'J/mol/K', 's', ['s'])                              # a gap of about 21 kJ/mol
    for answer, expected in (('no', 'conflicting'), ('unknown', 'conflicting'), ('yes', 'not_applicable')):
        r['facts']['enthalpy_buffer_ionization_corrected'] = fact(answer, ['s'])
        assert judged(r, 'thermodynamic_consistency')['status'] == expected, answer
    r['quantities']['entropy'] = point(-20.3 + 0.0, 'J/mol/K', 's', ['s'])
    r['facts']['enthalpy_buffer_ionization_corrected'] = fact('yes', ['s'])
    interpretation = convert_itc(grade_itc(r))['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported'                                              # the fit model alone
