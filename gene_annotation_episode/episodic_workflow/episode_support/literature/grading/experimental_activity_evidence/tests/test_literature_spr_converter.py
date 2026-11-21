"""SPR converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CHI2_OVER_RMAX_MAX, CHI2_OVER_RMAX_ZERO, HIGH_FACTOR, HIGH_ZERO_FACTOR, KINETIC_TOLERANCE, KINETIC_ZERO_TOLERANCE, LOW_FACTOR, LOW_ZERO_FACTOR, MIN_CONCENTRATIONS,
    MIN_REPLICATES, NULL_REASONS, RMAX_RATIO_MAX, RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MAX, RMAX_RATIO_ZERO_MIN, _criterion, convert_spr)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_spr(grade_spr(synthetic_record()))
    cells = converted['sheet']['cells']
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_variance']['unit'] == 'nM_squared'
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'binding_species', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_components_a_kd_cannot_fill_stay_null_with_a_reason():
    converted = convert_spr(grade_spr(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_standard_deviation_needs_independent_replicates_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    converted = convert_spr(grade_spr(r))
    assert converted['sheet']['cells']['effect_variance']['value'] == pytest.approx(36.0 / 3)
    r['facts']['independent_surfaces'] = fact('unknown')
    converted = convert_spr(grade_spr(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_missing_kd_and_confidence_interval_stay_null():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    converted = convert_spr(grade_spr(r))
    assert converted['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_spr(grade_spr(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'kd_not_given_as_a_point_value'


def test_conflicting_and_unknown_members_combine_by_the_rule():
    r = synthetic_record()
    r['facts']['mass_transport'] = fact('not_checked')
    r['facts']['reference_surface'] = fact('no')
    r['facts']['double_referencing'] = fact('no')
    interpretations = convert_spr(grade_spr(r))['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_controls']['status'] == 'conflicting'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    r['quantities']['kd_steady_state'] = {**r['quantities']['kd_steady_state'], 'status': 'unavailable', 'value': None}
    r['facts']['mass_transport'] = fact('checked_not_limited', ['s'])
    assert convert_spr(grade_spr(r))['extraction']['interpretations']['binding_regime']['status'] == 'supported'


def judged(record, name):
    return _criterion(grade_spr(record), name)


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_FACTOR, HIGH_FACTOR, HIGH_ZERO_FACTOR, MIN_REPLICATES) == (5, 0.2, 1.0, 5.0, 1.0, 3)
    assert (CHI2_OVER_RMAX_MAX, CHI2_OVER_RMAX_ZERO, RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MIN, RMAX_RATIO_MAX, RMAX_RATIO_ZERO_MAX) == (0.10, 0.30, 0.3, 0.1, 1.2, 2.0)
    assert (KINETIC_TOLERANCE, KINETIC_ZERO_TOLERANCE, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (0.20, 0.8, 2.0, 10.0)


def test_the_sheet_judges_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM
    for series, expected, degree in (([2.0, 4.0, 20.0, 100.0, 200.0], 'supported', 1.0), ([4.0, 6.0, 20.0, 100.0, 200.0], 'supported', 1.0),                # lowest 0.2 x KD, highest 10 x KD
                                     ([12.0, 20.0, 40.0, 100.0, 200.0], 'supported', 0.5), ([4.0, 6.0, 20.0, 60.0, 100.0], 'supported', 1.0),         # lowest 0.6 x KD: half way to the zero limit; highest exactly 5 x KD
                                     ([4.0, 6.0, 20.0, 40.0, 60.0], 'supported', 0.5), ([20.0, 40.0, 60.0, 100.0, 200.0], 'conflicting', None),      # highest 3 x KD: half; lowest at the KD: zero
                                     ([2.0, 4.0, 6.0, 10.0, 20.0], 'conflicting', None), ([2.0, 20.0, 200.0, 600.0], 'conflicting', None)):           # highest at the KD; four concentrations
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
        assert verdict['support_refs'] == ['span_exp_synthetic_spr_1']
        interpretation = convert_spr(grade_spr(r))['extraction']['interpretations']['binding_regime']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), series


def test_the_sheet_judges_the_fit_with_a_degree_and_keeps_the_one_to_one_bivalence_question():
    r = synthetic_record()                                                                     # Rmax 200
    for chi2, expected, degree in ((20.0, 'supported', 1.0), (30.0, 'supported', 0.75), (40.0, 'supported', 0.5), (59.0, 'supported', 0.025), (60.0, 'conflicting', None), (100.0, 'conflicting', None)):
        r['quantities']['chi_squared'] = point(chi2, 'RU^2', 'chi', ['s'])
        verdict = judged(r, 'fit_model')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), chi2
    r['quantities']['chi_squared'] = point(100.0, 'RU^2', 'chi', ['s'])
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('unknown')
    assert judged(r, 'fit_model')['status'] == 'conflicting'                                   # a poor fit stays conflicting whatever the bivalence answer
    r['quantities']['chi_squared'] = point(20.0, 'RU^2', 'chi', ['s'])
    assert judged(r, 'fit_model') == {'status': 'unknown', 'support_refs': []}


def test_the_sheet_judges_the_rmax_ratio_on_both_sides_with_a_degree():
    r = synthetic_record()                                                                     # theoretical Rmax 400
    for rmax, expected, degree in ((120.0, 'supported', 1.0), (480.0, 'supported', 1.0), (80.0, 'supported', 0.5), (60.0, 'supported', 0.25), (40.0, 'conflicting', None), (20.0, 'conflicting', None),
                                   (560.0, 'supported', 0.75), (640.0, 'supported', 0.5), (800.0, 'conflicting', None), (900.0, 'conflicting', None)):
        r['quantities']['rmax'] = point(rmax, 'RU', 'rmax', ['s'])
        verdict = judged(r, 'rmax_consistency')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), rmax


def test_the_sheet_judges_the_replicate_count_without_a_degree():
    r = synthetic_record()
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_surfaces'] = fact(independent, ['s'] if independent != 'unknown' else [])
        verdict = judged(r, 'replicates')
        assert verdict['status'] == expected and 'degree' not in verdict, (count, independent)


def test_the_sheet_judges_the_kd_from_the_rates_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM, kon 1e5: koff 2e-3 gives 20 nM
    for koff, expected, degree in ((2.0e-3, 'supported', 1.0), (2.3e-3, 'supported', 1.0), (2.8e-3, 'supported', 2 / 3), (3.4e-3, 'supported', 1 / 6), (3.8e-3, 'conflicting', None),
                                   (1.0e-3, 'supported', 0.5), (0.6e-3, 'supported', 1 / 6), (0.3e-3, 'conflicting', None)):      # relative gaps 0 / 0.15 / 0.4 / 0.7 / 0.9 / 0.5 / 0.7 / 0.85 (the last three are below the KD)
        r['quantities']['koff'] = point(koff, 's^-1', 'koff', ['s'])
        verdict = judged(r, 'kinetic_consistency')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), koff
        assert verdict['support_refs'] == ['span_exp_synthetic_spr_1', 's']                  # the KD's span and the replaced koff's


def test_the_sheet_judges_the_fold_between_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                     # kinetic KD 20 nM
    for steady, expected, degree in ((20.0, 'supported', 1.0), (40.0, 'supported', 1.0), (10.0, 'supported', 1.0), (60.0, 'supported', 0.875), (5.0, 'supported', 0.75), (120.0, 'supported', 0.5),
                                     (180.0, 'supported', 0.125), (200.0, 'conflicting', None), (2.0, 'conflicting', None)):
        r['quantities']['kd_steady_state'] = point(steady, 'nM', 'ss', ['s'])
        verdict = judged(r, 'steady_state_vs_kinetic')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), steady


def test_a_member_degree_reaches_the_sheet_interpretation_as_the_smallest_one():
    r = synthetic_record()
    r['quantities']['kd_steady_state'] = point(60.0, 'nM', 'ss', ['s'])                       # threefold: degree 0.875, the other binding_regime members have none
    interpretation = convert_spr(grade_spr(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.875)
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]                    # lowest 0.6 x KD: degree 0.5
    assert convert_spr(grade_spr(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert convert_spr(grade_spr(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)


def interpretations_of(record):
    return convert_spr(grade_spr(record))['extraction']['interpretations']


def test_the_support_degrees_are_the_shared_constants():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORT_DEGREE
    assert SUPPORT_DEGREE == {'direct': 1.0, 'implied': 0.7, 'about_something_else': 0.3}


def test_a_criterion_resting_on_a_weakly_supported_fact_gets_the_support_degree_and_direct_changes_nothing():
    assert 'degree' not in interpretations_of(synthetic_record())['binding_species']
    for support, degree in (('direct', None), ('implied', 0.7), ('about_something_else', 0.3)):
        r = synthetic_record()
        r['facts']['immobilized_activity'] = fact('yes', ['s'], support=support)
        got = interpretations_of(r)['binding_species']
        assert got['status'] == 'supported'
        assert 'degree' not in got if degree is None else got['degree'] == pytest.approx(degree), support


def test_the_support_degree_multiplies_an_existing_degree_and_the_weakest_field_counts_once():
    r = synthetic_record()
    r['quantities']['rmax'] = point(80.0, 'RU', 'rmax', ['s'])                                  # observed over theoretical 0.2: degree 0.5
    assert interpretations_of(r)['calibration_applicability']['degree'] == pytest.approx(0.5)
    r['quantities']['rmax'] = point(80.0, 'RU', 'rmax', ['s'], support='implied')
    assert interpretations_of(r)['calibration_applicability']['degree'] == pytest.approx(0.35)
    r['quantities']['stoichiometry'] = point(1.0, 'dimensionless', 'st', ['s'], support='about_something_else')
    assert interpretations_of(r)['calibration_applicability']['degree'] == pytest.approx(0.15)     # 0.5 x 0.3, not 0.5 x 0.7 x 0.3
    r = synthetic_record()
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]
    r['concentration_series']['support'] = 'implied'                                            # the support of the series, a field of the regime
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.35)


def test_support_never_changes_a_status_and_a_conflicting_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['immobilized_activity'] = fact('no', ['s'], support='implied')
    got = interpretations_of(r)['binding_species']
    assert got['status'] == 'conflicting' and 'degree' not in got
    r['facts']['immobilized_activity'] = fact('unknown')
    got = interpretations_of(r)['binding_species']
    assert got['status'] == 'unknown' and 'degree' not in got
    weak = synthetic_record()
    for name in weak['facts']:
        weak['facts'][name] = fact(weak['facts'][name]['answer'], ['s'], support='about_something_else')
    assert {k: v['status'] for k, v in interpretations_of(weak).items()} == {k: v['status'] for k, v in interpretations_of(synthetic_record()).items()}
