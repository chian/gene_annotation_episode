"""SPR converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CHI2_OVER_NOISE2_MAX, CHI2_OVER_NOISE2_ZERO, CHI2_OVER_RMAX_MAX, CHI2_OVER_RMAX_ZERO, CONCENTRATIONS_ZERO, HIGH_FACTOR, HIGH_ZERO_FACTOR, KINETIC_CONCENTRATIONS_ZERO, KINETIC_FOLD_MAX, KINETIC_FOLD_ZERO, LOW_FACTOR, LOW_ZERO_FACTOR, MIN_CONCENTRATIONS,
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
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                         # two independent replicates are now supported with partial credit, so their SD becomes a variance
    assert convert_spr(grade_spr(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(36.0 / 2)
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
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
    assert (MIN_CONCENTRATIONS, CONCENTRATIONS_ZERO, KINETIC_CONCENTRATIONS_ZERO, LOW_FACTOR, LOW_ZERO_FACTOR, HIGH_FACTOR, HIGH_ZERO_FACTOR) == (5, 2, 1, 0.2, 1.0, 5.0, 1.0)
    assert MIN_REPLICATES == 3
    assert (CHI2_OVER_RMAX_MAX, CHI2_OVER_RMAX_ZERO, RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MIN, RMAX_RATIO_MAX, RMAX_RATIO_ZERO_MAX) == (0.10, 0.30, 0.3, 0.1, 1.2, 2.0)
    assert (KINETIC_FOLD_MAX, KINETIC_FOLD_ZERO, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.2, 1.8, 2.0, 10.0)


def test_the_sheet_judges_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM, kon and koff stated: a kinetic fit
    for series, expected, degree in (([2.0, 4.0, 20.0, 100.0, 200.0], 'supported', 1.0), ([4.0, 6.0, 20.0, 100.0, 200.0], 'supported', 1.0),                # lowest 0.2 x KD, highest 10 x KD
                                     ([12.0, 20.0, 40.0, 100.0, 200.0], 'supported', 0.375), ([4.0, 6.0, 20.0, 60.0, 100.0], 'supported', 1.0),       # lowest 0.6 x KD: occupancy 3/8, (1/2 - 3/8) / (1/2 - 1/6); highest exactly 5 x KD
                                     ([4.0, 6.0, 20.0, 40.0, 60.0], 'supported', 0.75), ([20.0, 40.0, 60.0, 100.0, 200.0], 'conflicting', None),     # highest 3 x KD: occupancy 3/4, (3/4 - 1/2) / (5/6 - 1/2); lowest at the KD: zero
                                     ([2.0, 4.0, 6.0, 10.0, 20.0], 'conflicting', None), ([2.0, 20.0, 200.0, 600.0], 'supported', 0.75)):           # highest at the KD; four concentrations of a kinetic fit: (4 - 1) / (5 - 1), no step at five
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
        assert verdict['support_refs'] == ['span_exp_synthetic_spr_1']
        interpretation = convert_spr(grade_spr(r))['extraction']['interpretations']['binding_regime']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), series


SERIES_BY_COUNT = ([60.0], [2.0, 200.0], [2.0, 20.0, 200.0], [2.0, 6.0, 60.0, 200.0], [2.0, 6.0, 20.0, 60.0, 200.0], [2.0, 6.0, 20.0, 60.0, 120.0, 200.0], [2.0, 4.0, 6.0, 20.0, 60.0, 120.0, 200.0])      # 1 to 7 concentrations; from two on they span 0.1 x to 10 x KD 20 nM, so only the count decides


def without_rates(record):
    """A KD with no stated rates and no stated analysis (kd_analysis unknown)."""
    record['quantities']['kon'] = {**record['quantities']['kon'], 'status': 'unavailable', 'value': None}
    record['facts']['kd_analysis'] = fact('unknown')
    return record


def without_noise(record):
    record['quantities']['baseline_noise'] = {**record['quantities']['baseline_noise'], 'status': 'unavailable', 'value': None}
    return record


def test_the_concentration_count_is_a_gradual_curve_reaching_full_credit_at_the_researched_minimum():
    for record, zero in ((synthetic_record(), KINETIC_CONCENTRATIONS_ZERO), (without_rates(synthetic_record()), CONCENTRATIONS_ZERO)):      # a kinetic fit, then a KD with no stated rates
        curve = []
        for series in SERIES_BY_COUNT:
            record['concentration_series']['value'] = series
            verdict = judged(record, 'concentration_series')
            count = len(series)
            assert verdict['status'] == 'supported', series                                    # a short series is weaker evidence, never conflicting (one concentration included)
            assert verdict['degree'] == pytest.approx(max(0.0, min(1.0, (count - zero) / (MIN_CONCENTRATIONS - zero)))), (zero, series)
            curve.append(verdict['degree'])
        assert curve == sorted(curve)                                                          # monotone: one more concentration never lowers the degree
        assert 0 < curve[MIN_CONCENTRATIONS - 2] < 1 and curve[MIN_CONCENTRATIONS - 1] == pytest.approx(1.0)      # just below the researched five: partial credit, not 0
    kinetic, steady = synthetic_record(), without_rates(synthetic_record())
    for series, kinetic_degree, steady_degree in ((SERIES_BY_COUNT[1], 0.25, 0.0), (SERIES_BY_COUNT[2], 0.5, 1 / 3), (SERIES_BY_COUNT[3], 0.75, 2 / 3)):
        kinetic['concentration_series']['value'] = steady['concentration_series']['value'] = series
        assert judged(kinetic, 'concentration_series')['degree'] == pytest.approx(kinetic_degree)      # one sensorgram fixes kon and koff: each further one is a check
        assert judged(steady, 'concentration_series')['degree'] == pytest.approx(steady_degree)        # the isotherm uses two points for KD and Rmax


def test_the_two_ends_of_the_series_are_mirror_images_on_the_occupancy_scale():
    r = synthetic_record()                                                                     # KD 20 nM
    r['concentration_series']['value'] = [10.0, 20.0, 60.0, 100.0, 200.0]                    # lowest 0.5 x KD: occupancy 1/3
    low = judged(r, 'concentration_series')['degree']
    r['concentration_series']['value'] = [2.0, 6.0, 10.0, 20.0, 40.0]                        # highest 2 x KD: occupancy 2/3
    high = judged(r, 'concentration_series')['degree']
    assert low == pytest.approx(0.5) and high == pytest.approx(0.5)
    curve = []
    for lowest in (1.0, 2.0, 4.0, 8.0, 12.0, 16.0, 19.0):                                    # the lowest concentration moves up towards the KD
        r['concentration_series']['value'] = [lowest, 40.0, 60.0, 100.0, 200.0]
        curve.append(judged(r, 'concentration_series')['degree'])
    assert curve == sorted(curve, reverse=True) and 0 < curve[-1] < curve[0] == 1.0         # monotone and gradual towards the zero end
    r['concentration_series']['value'] = [10.0]                                                # one concentration below the KD: the paper's only point never reaches half occupancy
    assert judged(r, 'concentration_series')['status'] == 'conflicting'


def test_the_sheet_judges_the_fit_with_a_degree_and_keeps_the_one_to_one_bivalence_question():
    r = without_noise(synthetic_record())                                                      # Rmax 200; the noise is not stated, so only the Rmax scale applies
    for chi2, expected, degree in ((20.0, 'supported', 1.0), (30.0, 'supported', 0.75), (40.0, 'supported', 0.5), (59.0, 'supported', 0.025), (60.0, 'conflicting', None), (100.0, 'conflicting', None)):
        r['quantities']['chi_squared'] = point(chi2, 'RU^2', 'chi', ['s'])
        verdict = judged(r, 'fit_model')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), chi2
    r['quantities']['chi_squared'] = point(100.0, 'RU^2', 'chi', ['s'])
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('unknown')
    assert judged(r, 'fit_model')['status'] == 'conflicting'                                   # a poor fit stays conflicting whatever the bivalence answer
    r['quantities']['chi_squared'] = point(20.0, 'RU^2', 'chi', ['s'])
    assert judged(r, 'fit_model') == {'status': 'unknown', 'support_refs': []}


def test_the_noise_scale_of_chi_squared_is_gradual_monotone_and_used_only_when_the_noise_is_stated():
    assert (CHI2_OVER_NOISE2_MAX, CHI2_OVER_NOISE2_ZERO) == (2.0, 10.0)
    r = synthetic_record()                                                                     # Rmax 200 RU, noise 1.5 RU: noise^2 2.25 RU^2
    curve = []
    for chi2 in (2.0, 4.5, 6.0, 9.0, 12.0, 18.0, 22.0):                                      # 0.9, 2, 2.7, 4, 5.3, 8, 9.8 times noise^2; at most 0.11 of Rmax
        r['quantities']['chi_squared'] = point(chi2, 'RU^2', 'chi', ['s'])
        verdict = judged(r, 'fit_model')
        assert verdict['status'] == 'supported' and 0 < verdict['degree'] <= 1, chi2            # the Rmax scale alone gives full credit up to 20 RU^2
        curve.append(verdict['degree'])
    assert curve[:2] == [1.0, pytest.approx(1.0)] and curve == sorted(curve, reverse=True) and curve[2] < 1   # full at 2 x noise^2, then falling: no step, never rising
    assert curve[3] == pytest.approx(1 - math.log(4 / 2) / math.log(10 / 2))                  # linear in log ratio
    r['quantities']['chi_squared'] = point(22.5, 'RU^2', 'chi', ['s'])                         # exactly 10 x noise^2: the zero end
    assert judged(r, 'fit_model')['status'] == 'conflicting'
    r['quantities']['chi_squared'] = point(9.0, 'RU^2', 'chi', ['s'])
    assert judged(r, 'fit_model')['degree'] < 1
    r = without_noise(r)
    assert judged(r, 'fit_model')['status'] == 'supported' and judged(r, 'fit_model')['degree'] == 1.0      # noise not stated: the same record is judged on the Rmax scale only (0.045 of Rmax)


def test_a_stated_analysis_of_the_kd_decides_the_zero_end_of_the_concentration_count():
    r = synthetic_record()                                                                     # kon and koff stated, kd_analysis kinetic_fit
    r['concentration_series']['value'] = [2.0, 200.0]
    assert judged(r, 'concentration_series')['degree'] == pytest.approx(0.25)
    r['facts']['kd_analysis'] = fact('steady_state_fit', ['s'])                                # the paper says the KD is a steady-state fit, whatever else it reports
    assert judged(r, 'concentration_series')['degree'] == pytest.approx(0.0) and judged(r, 'concentration_series')['status'] == 'supported'
    r['facts']['kd_analysis'] = fact('unknown')
    assert judged(r, 'concentration_series')['degree'] == pytest.approx(0.25)                  # silence: the stated rates stand for a kinetic fit, as before


def test_the_sheet_judges_the_rmax_ratio_on_both_sides_with_a_degree():
    r = synthetic_record()                                                                     # theoretical Rmax 400
    for rmax, expected, degree in ((120.0, 'supported', 1.0), (480.0, 'supported', 1.0), (80.0, 'supported', 0.5), (60.0, 'supported', 0.25), (40.0, 'conflicting', None), (20.0, 'conflicting', None),
                                   (560.0, 'supported', 0.75), (640.0, 'supported', 0.5), (800.0, 'conflicting', None), (900.0, 'conflicting', None)):
        r['quantities']['rmax'] = point(rmax, 'RU', 'rmax', ['s'])
        verdict = judged(r, 'rmax_consistency')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), rmax


def test_the_sheet_judges_the_replicate_count_with_a_gradual_degree():
    r = synthetic_record()
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', (2 / 3) ** 0.5), (1, 'yes', 'supported', (1 / 3) ** 0.5),
                                                 (2, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None), (1, 'unknown', 'unknown', None)):      # sqrt(n / MIN_REPLICATES); a stated count is never conflicting
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_surfaces'] = fact(independent, ['s'] if independent != 'unknown' else [])
        verdict = judged(r, 'replicates')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (count, independent)
    curve = []
    for count in range(1, 7):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_surfaces'] = fact('yes', ['s'])
        curve.append(judged(r, 'replicates').get('degree', 0.0))
    assert curve == sorted(curve)                                                              # monotone: one more independent replicate never lowers the degree
    assert 0 < curve[0] < curve[MIN_REPLICATES - 2] < 1 and curve[MIN_REPLICATES - 1] == pytest.approx(1.0)      # one and two runs: partial credit, not 0, not conflicting
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert convert_spr(grade_spr(r))['extraction']['interpretations']['sampling_basis'] == {'status': 'supported', 'support_refs': ['s'], 'degree': pytest.approx((2 / 3) ** 0.5)}
    r['facts']['independent_surfaces'] = fact('no', ['s'])
    assert judged(r, 'replicates')['status'] == 'conflicting'                                  # a stated no stays the grader's conflicting fact


def test_the_sheet_judges_the_kd_from_the_rates_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM, kon 1e5: koff 2e-3 gives 20 nM

    def log_degree(fold):
        return math.log(KINETIC_FOLD_ZERO / fold) / math.log(KINETIC_FOLD_ZERO / KINETIC_FOLD_MAX)
    for koff, expected, degree in ((2.0e-3, 'supported', 1.0), (2.3e-3, 'supported', 1.0), (1.7e-3, 'supported', 1.0), (2.8e-3, 'supported', log_degree(1.4)), (3.4e-3, 'supported', log_degree(1.7)),
                                   (3.8e-3, 'conflicting', None), (2.0e-3 / 1.4, 'supported', log_degree(1.4)), (2.0e-3 / 1.7, 'supported', log_degree(1.7)), (1.0e-3, 'conflicting', None),
                                   (0.3e-3, 'conflicting', None)):      # folds 1 / 1.15 / 1.18 / 1.4 / 1.7 / 1.9 above, then 1.4 / 1.7 / 2 / 6.7 below the KD: the same fold either way scores the same
        r['quantities']['koff'] = point(koff, 's^-1', 'koff', ['s'])
        verdict = judged(r, 'kinetic_consistency')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), koff
        assert verdict['support_refs'] == ['span_exp_synthetic_spr_1', 's']                  # the KD's span and the replaced koff's
    assert 0 < log_degree(1.7) < log_degree(1.4) < 1 and log_degree(1.4) == pytest.approx(0.6198, abs=1e-4)
    curve = []
    for fold in (1.0, 1.1, 1.2, 1.3, 1.5, 1.7, 1.79):
        r['quantities']['koff'] = point(2.0e-3 * fold, 's^-1', 'koff', ['s'])
        curve.append(judged(r, 'kinetic_consistency')['degree'])
    assert curve == sorted(curve, reverse=True) and curve[2] == pytest.approx(1.0) and 0 < curve[-1] < curve[3] < 1      # monotone, no step past the researched 1.2


def test_the_sheet_judges_the_fold_between_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                     # kinetic KD 20 nM
    def log_degree(fold):
        return math.log(AGREEMENT_ZERO_FACTOR / fold) / math.log(AGREEMENT_ZERO_FACTOR / AGREEMENT_FACTOR)
    for steady, expected, degree in ((20.0, 'supported', 1.0), (40.0, 'supported', 1.0), (10.0, 'supported', 1.0), (60.0, 'supported', log_degree(3)), (5.0, 'supported', log_degree(4)), (120.0, 'supported', log_degree(6)),
                                     (180.0, 'supported', log_degree(9)), (200.0, 'conflicting', None), (2.0, 'conflicting', None)):
        r['quantities']['kd_steady_state'] = point(steady, 'nM', 'ss', ['s'])
        verdict = judged(r, 'steady_state_vs_kinetic')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), steady
    assert log_degree(3) == pytest.approx(0.748, abs=1e-3) and log_degree(6) == pytest.approx(0.317, abs=1e-3)      # linear in log fold: 2 -> 4 costs as much as 5 -> 10
    assert log_degree(2) - log_degree(4) == pytest.approx(log_degree(5) - log_degree(10))


def test_a_member_degree_reaches_the_sheet_interpretation_as_the_smallest_one():
    r = synthetic_record()
    r['quantities']['kd_steady_state'] = point(60.0, 'nM', 'ss', ['s'])                       # threefold: degree log(10/3) / log(5), the other binding_regime members are full
    interpretation = convert_spr(grade_spr(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(math.log(10 / 3) / math.log(5))
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]                    # lowest 0.6 x KD: degree 0.375
    assert convert_spr(grade_spr(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(0.375)
    assert convert_spr(grade_spr(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.375)


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
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.375 * 0.7)


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
