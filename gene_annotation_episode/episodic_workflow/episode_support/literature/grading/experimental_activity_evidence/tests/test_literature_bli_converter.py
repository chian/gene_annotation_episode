"""BLI converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, DISSOCIATION_DECAY_MIN, DISSOCIATION_DECAY_ZERO, FIT_R_SQUARED_MIN, FIT_R_SQUARED_ZERO, HIGH_FACTOR, HIGH_ZERO_FACTOR, KINETIC_TOLERANCE, KINETIC_ZERO_TOLERANCE,
    LOADING_MAX_NM, LOADING_ZERO_NM, LOW_FACTOR, LOW_ZERO_FACTOR, MIN_CONCENTRATIONS, MIN_REPLICATES, NULL_REASONS, RESPONSE_MIN_NM, RESPONSE_ZERO_NM, _criterion, convert_bli)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import CRITERIA, grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import sparse_record, synthetic_record


def test_every_bli_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) <= set(CRITERIA)
    # kept out of the sheet on purpose: none (every criterion has a sheet counterpart)
    assert set(CRITERIA) - set(mapped) == set()


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_bli(grade_bli(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'bli'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'binding_species', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_spr_and_itc_converters_and_nulls_have_reasons():
    converted = convert_bli(grade_bli(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_the_sensor_as_the_surface():
    converted = convert_bli(grade_bli(synthetic_record(analyte_prep='ana', immobilized_prep='lig', sensor='tip_lot', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'ana', 'immobilized_preparation_ref': 'lig', 'surface_ref': 'tip_lot', 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_sensors_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent sensors: variance 36 / 3 = 12
    assert convert_bli(grade_bli(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['facts']['independent_sensors'] = fact('unknown')
    converted = convert_bli(grade_bli(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_missing_kd_and_confidence_interval_stay_null():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    assert convert_bli(grade_bli(r))['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_bli(grade_bli(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'kd_not_given_as_a_point_value'


def test_sparse_record_fills_only_the_effect():
    converted = convert_bli(grade_bli(sparse_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == 20.0
    assert cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_conflicting_unknown_and_not_applicable_members_combine_by_the_rule():
    r = synthetic_record()
    r['facts']['nonspecific_binding_checked'] = fact('no', ['s'])
    r['facts']['baseline_stable'] = fact('unknown')
    assert convert_bli(grade_bli(r))['extraction']['interpretations']['binding_controls']['status'] == 'conflicting'
    r = synthetic_record()
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    r['quantities']['kd_steady_state'] = {**r['quantities']['kd_steady_state'], 'status': 'unavailable', 'value': None}
    # steady_state_vs_kinetic is not_applicable and dropped; the other binding_regime members are supported
    assert convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']['status'] == 'supported'
    r['facts']['mass_transport_considered'] = fact('unknown')
    r['facts']['avidity_rebinding_considered'] = fact('unknown')
    assert convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']['status'] == 'unknown'
    r = synthetic_record()
    r['facts']['loading_step_documented'] = fact('no', ['s'])
    assert convert_bli(grade_bli(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'


def judged(record, name):
    return _criterion(grade_bli(record), name)


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_FACTOR, HIGH_FACTOR, HIGH_ZERO_FACTOR, MIN_REPLICATES) == (5, 0.2, 1.0, 5.0, 1.0, 3)
    assert (FIT_R_SQUARED_MIN, FIT_R_SQUARED_ZERO, LOADING_MAX_NM, LOADING_ZERO_NM, RESPONSE_MIN_NM, RESPONSE_ZERO_NM, DISSOCIATION_DECAY_MIN, DISSOCIATION_DECAY_ZERO) == (0.95, 0.80, 2.0, 4.0, 0.05, 0.01, 0.05, 0.01)
    assert (KINETIC_TOLERANCE, KINETIC_ZERO_TOLERANCE, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (0.20, 0.8, 2.0, 10.0)


def test_the_sheet_judges_the_loading_and_the_response_with_a_degree():
    r = synthetic_record()                                                                     # loading 1.0 nm, response 0.8 nm, loading step documented
    for loading, response, expected, degree in ((2.0, 0.05, 'supported', 1.0), (3.0, 0.8, 'supported', 0.5), (1.0, 0.03, 'supported', 0.5), (3.0, 0.03, 'supported', 0.5), (3.5, 0.02, 'supported', 0.25),
                                                (4.0, 0.8, 'conflicting', None), (5.0, 0.8, 'conflicting', None), (1.0, 0.01, 'conflicting', None), (1.0, 0.0, 'conflicting', None)):
        r['quantities']['loading_level'] = point(loading, 'nm', 'l', ['s'])
        r['quantities']['response_max'] = point(response, 'nm', 'r', ['s'])
        verdict = judged(r, 'loading_and_response')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (loading, response)
        interpretation = convert_bli(grade_bli(r))['extraction']['interpretations']['calibration_applicability']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), (loading, response)
    r = synthetic_record()
    r['facts']['loading_step_documented'] = fact('unknown')
    assert judged(r, 'loading_and_response') == {'status': 'unknown', 'support_refs': []}
    r['quantities']['loading_level'] = point(5.0, 'nm', 'l', ['s'])
    assert judged(r, 'loading_and_response')['status'] == 'conflicting'                        # beyond the zero limit stays conflicting whatever the documentation says
    r = synthetic_record()
    r['quantities']['loading_level'] = {**r['quantities']['loading_level'], 'status': 'unavailable', 'value': None}
    assert judged(r, 'loading_and_response')['status'] == 'unknown'                            # the response alone cannot make it supported
    r['quantities']['response_max'] = point(0.005, 'nm', 'r', ['s'])
    assert judged(r, 'loading_and_response')['status'] == 'conflicting'                        # but it can make it conflicting


def test_the_sheet_judges_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM
    for series, expected, degree in (([2.0, 4.0, 20.0, 100.0, 200.0], 'supported', 1.0), ([12.0, 20.0, 40.0, 100.0, 200.0], 'supported', 0.5), ([4.0, 6.0, 20.0, 40.0, 60.0], 'supported', 0.5),
                                     ([20.0, 40.0, 60.0, 100.0, 200.0], 'conflicting', None), ([2.0, 4.0, 6.0, 10.0, 20.0], 'conflicting', None), ([2.0, 20.0, 200.0, 600.0], 'conflicting', None)):
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
        interpretation = convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), series


def test_the_sheet_judges_the_fit_r_squared_with_a_degree_and_keeps_the_one_to_one_bivalence_question():
    r = synthetic_record()
    for r_squared, expected, degree in ((0.99, 'supported', 1.0), (0.95, 'supported', 1.0), (0.875, 'supported', 0.5), (0.81, 'supported', 0.0667), (0.80, 'conflicting', None), (0.5, 'conflicting', None)):
        r['quantities']['fit_r_squared'] = point(r_squared, 'dimensionless', 'r2', ['s'])
        verdict = judged(r, 'fit_model')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree, abs=1e-3) if degree is not None else None), r_squared
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('unknown')
    r['quantities']['fit_r_squared'] = point(0.5, 'dimensionless', 'r2', ['s'])
    assert judged(r, 'fit_model')['status'] == 'conflicting'
    r['quantities']['fit_r_squared'] = point(0.99, 'dimensionless', 'r2', ['s'])
    assert judged(r, 'fit_model') == {'status': 'unknown', 'support_refs': []}
    r['fit_model'] = '2:1_bivalent_analyte'
    assert judged(r, 'fit_model')['status'] == 'supported'


def test_the_sheet_judges_the_decayed_fraction_in_the_dissociation_window_with_a_degree():
    r = synthetic_record()                                                                     # koff 2.0e-3 s^-1
    for seconds, expected in ((600.0, 'supported'), (30.0, 'supported'), (10.0, 'supported'), (2.0, 'conflicting')):
        r['quantities']['dissociation_time'] = point(seconds, 's', 't', ['s'])
        graded = grade_bli(r)
        decay = graded['native']['dissociation_decay']
        verdict = _criterion(graded, 'dissociation_window')
        assert verdict['status'] == expected, seconds
        if expected == 'supported':
            assert verdict['degree'] == pytest.approx(min(1.0, (decay - 0.01) / 0.04)), seconds
        else:
            assert decay < 0.01 and 'degree' not in verdict
    assert judged(r, 'dissociation_window')['status'] == 'conflicting'


def test_the_sheet_judges_the_replicate_count_without_a_degree():
    r = synthetic_record()
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_sensors'] = fact(independent, ['s'] if independent != 'unknown' else [])
        verdict = judged(r, 'replicates')
        assert verdict['status'] == expected and 'degree' not in verdict, (count, independent)


def test_the_sheet_judges_the_kd_from_the_rates_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM, kon 1e5: koff 2e-3 gives 20 nM
    for koff, expected, degree in ((2.0e-3, 'supported', 1.0), (2.3e-3, 'supported', 1.0), (2.8e-3, 'supported', 2 / 3), (3.4e-3, 'supported', 1 / 6), (3.8e-3, 'conflicting', None),
                                   (1.0e-3, 'supported', 0.5), (0.6e-3, 'supported', 1 / 6), (0.3e-3, 'conflicting', None)):
        r['quantities']['koff'] = point(koff, 's^-1', 'koff', ['s'])
        verdict = judged(r, 'kinetic_consistency')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), koff


def test_the_sheet_judges_the_fold_between_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                     # kinetic KD 20 nM
    for steady, expected, degree in ((20.0, 'supported', 1.0), (40.0, 'supported', 1.0), (60.0, 'supported', 0.875), (5.0, 'supported', 0.75), (120.0, 'supported', 0.5), (180.0, 'supported', 0.125),
                                     (400.0, 'conflicting', None), (1.0, 'conflicting', None)):
        r['quantities']['kd_steady_state'] = point(steady, 'nM', 'ss', ['s'])
        verdict = judged(r, 'steady_state_vs_kinetic')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), steady


def test_a_member_degree_reaches_the_sheet_interpretation_as_the_smallest_one():
    r = synthetic_record()
    r['quantities']['kd_steady_state'] = point(60.0, 'nM', 'ss', ['s'])                       # threefold: degree 0.875
    interpretation = convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.875)
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]                    # lowest 0.6 x KD: degree 0.5
    assert convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert convert_bli(grade_bli(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert 'degree' not in convert_bli(grade_bli(synthetic_record()))['extraction']['interpretations']['sampling_basis']


def interpretations_of(record):
    return convert_bli(grade_bli(record))['extraction']['interpretations']


def test_the_support_degrees_are_the_shared_constants():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORT_DEGREE
    assert SUPPORT_DEGREE == {'direct': 1.0, 'implied': 0.7, 'about_something_else': 0.3}


def test_a_criterion_resting_on_a_weakly_supported_fact_gets_the_support_degree_and_direct_changes_nothing():
    assert 'degree' not in interpretations_of(synthetic_record())['binding_species']
    for support, degree in (('direct', None), ('implied', 0.7), ('about_something_else', 0.3)):
        r = synthetic_record()
        r['facts']['immobilized_partner_active'] = fact('yes', ['s'], support=support)
        got = interpretations_of(r)['binding_species']
        assert got['status'] == 'supported'
        assert 'degree' not in got if degree is None else got['degree'] == pytest.approx(degree), support


def test_the_support_degree_multiplies_an_existing_degree_and_the_weakest_field_counts_once():
    r = synthetic_record()
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]                    # lowest 0.6 x KD: degree 0.5
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.5)
    r['concentration_series']['support'] = 'implied'
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.35)
    r['quantities']['kd'] = point(20.0, 'nM', 'kd', ['s'], support='about_something_else')
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.15)             # 0.5 x 0.3, not 0.5 x 0.7 x 0.3


def test_support_never_changes_a_status_and_a_conflicting_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['immobilized_partner_active'] = fact('no', ['s'], support='implied')
    got = interpretations_of(r)['binding_species']
    assert got['status'] == 'conflicting' and 'degree' not in got
    r['facts']['immobilized_partner_active'] = fact('unknown')
    got = interpretations_of(r)['binding_species']
    assert got['status'] == 'unknown' and 'degree' not in got
    weak = synthetic_record()
    for name in weak['facts']:
        weak['facts'][name] = fact(weak['facts'][name]['answer'], ['s'], support='about_something_else')
    assert {k: v['status'] for k, v in interpretations_of(weak).items()} == {k: v['status'] for k, v in interpretations_of(synthetic_record()).items()}
