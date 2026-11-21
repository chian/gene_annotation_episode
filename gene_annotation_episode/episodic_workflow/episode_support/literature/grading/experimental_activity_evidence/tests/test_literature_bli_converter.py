"""BLI converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_bli_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, DISSOCIATION_DECAY_MIN, DISSOCIATION_DECAY_ZERO, FIT_R_SQUARED_MIN, FIT_R_SQUARED_ZERO, HIGH_FACTOR, HIGH_ZERO_FACTOR, KINETIC_FIT_MODELS, KINETIC_FOLD_MAX, KINETIC_ZERO_FOLD,
    LOADING_MAX_NM, LOADING_ZERO_NM, LOW_FACTOR, LOW_ZERO_FACTOR, MIN_CONCENTRATIONS, MIN_REPLICATES, NULL_REASONS, RESPONSE_MIN_NM, RESPONSE_ZERO_NM, SERIES_COUNT_CURVE_POWER, SERIES_ZERO_CONCENTRATIONS, SERIES_ZERO_CONCENTRATIONS_KINETIC,
    _criterion, convert_bli)
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
    # 2 independent sensors: the replicates criterion has partial credit and is supported, so the variance is 36 / 2 = 18
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert convert_bli(grade_bli(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(18.0)
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
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
    assert (KINETIC_FOLD_MAX, KINETIC_ZERO_FOLD, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.2, 1.8, 2.0, 10.0)
    assert (SERIES_ZERO_CONCENTRATIONS, SERIES_ZERO_CONCENTRATIONS_KINETIC, SERIES_COUNT_CURVE_POWER) == (1, 0, 2)
    assert KINETIC_FIT_MODELS == ('1:1', '2:1_bivalent_analyte', 'heterogeneous_ligand')


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


def test_the_sheet_judges_the_concentration_series_of_an_isotherm_fit_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM
    for model in ('steady_state', 'other', None):                                              # not stated as kinetic: the isotherm rules (the old ones, kept)
        r['fit_model'] = model
        # count degree below five: 1 - ((5 - n) / 4)^2, so four 0.9375, three 0.75, two 0.4375; one concentration gives no isotherm KD: no credit, never conflicting
        for series, expected, degree in (([2.0, 4.0, 20.0, 100.0, 200.0], 'supported', 1.0), ([12.0, 20.0, 40.0, 100.0, 200.0], 'supported', 0.5), ([4.0, 6.0, 20.0, 40.0, 60.0], 'supported', 0.5),
                                         ([20.0, 40.0, 60.0, 100.0, 200.0], 'conflicting', None), ([2.0, 4.0, 6.0, 10.0, 20.0], 'conflicting', None), ([2.0, 20.0, 200.0, 600.0], 'supported', 0.9375),
                                         ([2.0, 20.0, 200.0], 'supported', 0.75), ([2.0, 200.0], 'supported', 0.4375), ([12.0, 200.0], 'supported', 0.4375), ([12.0, 20.0, 200.0, 600.0], 'supported', 0.5),
                                         ([2.0], 'conflicting', None)):      # one concentration at 0.1 x KD: conflicting by the highest-over-KD ramp (it never passes the KD), not by its count
            r['concentration_series']['value'] = series
            verdict = judged(r, 'concentration_series')
            assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (model, series)


def test_the_sheet_judges_the_concentration_series_of_a_kinetic_fit_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM, fit model 1:1 (kinetic)
    # count degree below five: 1 - ((5 - n) / 5)^2, so four 0.96, three 0.84, two 0.64; the lowest over the KD: (1 + 0.2) / (1 + low), never conflicting
    for series, expected, degree in (([2.0, 4.0, 20.0, 100.0, 200.0], 'supported', 1.0), ([12.0, 20.0, 40.0, 100.0, 200.0], 'supported', 0.75), ([4.0, 6.0, 20.0, 40.0, 60.0], 'supported', 0.5),
                                     ([20.0, 40.0, 60.0, 100.0, 200.0], 'supported', 0.6), ([60.0, 120.0, 240.0, 480.0, 960.0], 'supported', 0.3), ([2.0, 4.0, 6.0, 10.0, 20.0], 'conflicting', None),
                                     ([2.0, 20.0, 200.0, 600.0], 'supported', 0.96), ([2.0, 20.0, 200.0], 'supported', 0.84), ([2.0, 200.0], 'supported', 0.64), ([12.0, 200.0], 'supported', 0.64),
                                     ([12.0, 20.0, 200.0, 600.0], 'supported', 0.75),
                                     ([200.0], 'supported', 1.2 / 11.0),        # one concentration at 10 x KD: the low end (0.11) is weaker than the count (0.36); supported, not conflicting
                                     ([2.0], 'conflicting', None)):             # one concentration at 0.1 x KD: conflicting by the highest-over-KD ramp (it never passes the KD), not by its count
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
        interpretation = convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), series


def test_the_low_end_of_a_kinetic_series_is_gentle_and_never_conflicting_and_the_isotherm_keeps_its_ramp():
    native = grade_bli(synthetic_record())['native']
    kinetic, isotherm = [], []
    for low in (0.05, 0.2, 0.3, 0.6, 0.9, 1.0, 1.5, 3.0, 10.0, 100.0):
        case = {**native, 'concentration_count': MIN_CONCENTRATIONS, 'concentration_low_over_kd': low, 'concentration_high_over_kd': max(10.0, 2 * low)}
        verdict = literature_bli_converter._judge_series(case)
        assert verdict['status'] == 'supported' and 0 < verdict['degree'] <= 1, low               # a series wholly above the KD still measures kon and koff
        kinetic.append(verdict['degree'])
        verdict = literature_bli_converter._judge_series({**case, 'fit_model': 'steady_state'})
        isotherm.append(verdict.get('degree', 0.0))
        assert (verdict['status'] == 'conflicting') == (low >= LOW_ZERO_FACTOR), low
    assert kinetic == sorted(kinetic, reverse=True) and kinetic[:2] == [1.0, 1.0]                 # a lower lowest concentration never lowers the degree
    assert isotherm == sorted(isotherm, reverse=True) and all(k >= i for k, i in zip(kinetic, isotherm))      # the kinetic rule is never stricter than the isotherm one
    assert kinetic[2] == pytest.approx(1.2 / 1.3) and kinetic[5] == pytest.approx(0.6)          # just past 0.2 x KD: partial credit close to full, no step


def test_the_concentration_count_is_gradual_and_monotone_around_the_researched_minimum():
    r = synthetic_record()                                                                     # KD 20 nM; every series below spans 0.1 x to 10 x KD, so only the count varies
    degrees = []
    for count in range(2, 10):
        r['concentration_series']['value'] = [2.0 * (100.0 ** (i / (count - 1))) for i in range(count)]
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == 'supported' and 0 < verdict['degree'] <= 1, count
        degrees.append(verdict['degree'])
    assert degrees == sorted(degrees)                                                          # more concentrations never lower the degree
    assert degrees[MIN_CONCENTRATIONS - 2:] == [1.0] * (len(degrees) - MIN_CONCENTRATIONS + 2)  # full credit from the researched minimum on
    assert 0.9 < degrees[MIN_CONCENTRATIONS - 3] < 1.0                                         # one fewer: partial credit close to full, no step
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert judged(r, 'concentration_series') == {'status': 'unknown', 'support_refs': []}      # no series stated: unknown, not 0
    one = {**grade_bli(synthetic_record())['native'], 'concentration_count': 1, 'concentration_low_over_kd': 0.1, 'concentration_high_over_kd': 10.0}      # a count of one alone (span ratios fine)
    count_degree = literature_bli_converter._judge_series(one)
    assert count_degree['status'] == 'supported' and count_degree['degree'] == pytest.approx(0.36)      # kinetic fit: one association/dissociation pair measures kon and koff: low partial credit
    count_degree = literature_bli_converter._judge_series({**one, 'fit_model': 'steady_state'})
    assert count_degree['status'] == 'supported' and count_degree['degree'] == 0.0           # isotherm: one point gives no KD (two unknowns): no credit, never conflicting
    for model in ('1:1', 'steady_state'):                                                    # both count curves are monotone and reach full credit at the researched minimum
        degrees = [literature_bli_converter._judge_series({**one, 'fit_model': model, 'concentration_count': n})['degree'] for n in range(1, 9)]
        assert degrees == sorted(degrees) and degrees[MIN_CONCENTRATIONS - 1:] == [1.0] * (9 - MIN_CONCENTRATIONS), model


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
    r = synthetic_record()                                                                     # koff 2.0e-3 s^-1, maximum response 0.8 nm
    for seconds, expected in ((600.0, 'supported'), (30.0, 'supported'), (10.0, 'supported'), (2.0, 'conflicting')):
        r['quantities']['dissociation_time'] = point(seconds, 's', 't', ['s'])
        graded = grade_bli(r)
        decay = graded['native']['dissociation_decay']
        verdict = _criterion(graded, 'dissociation_window')
        assert verdict['status'] == expected, seconds
        if expected == 'supported':
            # the decayed fraction (1 -> 5 percent) and the decayed signal (fraction x 0.8 nm, 0.01 -> 0.05 nm): the smaller counts
            assert verdict['degree'] == pytest.approx(min(1.0, (decay - 0.01) / 0.04, (decay * 0.8 - 0.01) / 0.04)), seconds
        else:
            assert decay < 0.01 and 'degree' not in verdict
    assert judged(r, 'dissociation_window')['status'] == 'conflicting'


def test_the_decayed_signal_is_judged_against_the_noise_when_the_response_is_given():
    r = synthetic_record()
    r['quantities']['dissociation_time'] = point(30.0, 's', 't', ['s'])                       # decayed fraction 0.058: full credit on the fraction alone
    degrees = []
    for response in (2.0, 0.8, 0.5, 0.3, 0.2):                                                 # decayed signal 0.116, 0.047, 0.029, 0.017, 0.012 nm
        r['quantities']['response_max'] = point(response, 'nm', 'r', ['span_response'])
        verdict = judged(r, 'dissociation_window')
        assert verdict['status'] == 'supported' and 0 < verdict['degree'] <= 1 and 'span_response' in verdict['support_refs'], response
        degrees.append(verdict['degree'])
    assert degrees == sorted(degrees, reverse=True) and degrees[0] == 1.0 and degrees[-1] < 0.1      # a smaller response never raises the degree; gradual, no step
    r['quantities']['response_max'] = point(0.1, 'nm', 'r', ['s'])                             # 0.006 nm decayed: within the noise, koff not measured
    assert judged(r, 'dissociation_window')['status'] == 'conflicting'
    r['quantities']['response_max'] = {**r['quantities']['response_max'], 'status': 'unavailable', 'value': None}
    verdict = judged(r, 'dissociation_window')
    assert verdict['status'] == 'supported' and verdict['degree'] == 1.0                     # no response stated: the fraction alone, as before


def test_the_loading_ends_scale_with_a_stated_partner_mass_above_the_reference_and_never_below():
    r = synthetic_record()
    r['quantities']['loading_level'] = point(3.0, 'nm', 'l', ['s'])                           # no mass stated: the absolute ends (degree 0.5)
    assert judged(r, 'loading_and_response')['degree'] == pytest.approx(0.5)
    degrees = []
    for mass in (5.0, 50.0, 60.0, 100.0, 150.0):
        r['quantities']['partner_mass'] = point(mass, 'kDa', 'm', ['span_mass'])
        verdict = judged(r, 'loading_and_response')
        assert verdict['status'] == 'supported' and 0 < verdict['degree'] <= 1, mass
        degrees.append(verdict['degree'])
    assert degrees == sorted(degrees) and degrees[0] == pytest.approx(0.5) == degrees[1] and degrees[3] == 1.0 and 0.5 < degrees[2] < 1.0      # a larger partner never lowers it; below the reference unchanged; no step
    assert 'span_mass' in judged(r, 'loading_and_response')['support_refs']
    r['quantities']['loading_level'] = point(5.0, 'nm', 'l', ['s'])                           # a dense loading of a 5 kDa partner stays conflicting, of a 150 kDa partner it is fine
    r['quantities']['partner_mass'] = point(5.0, 'kDa', 'm', ['span_mass'])
    assert judged(r, 'loading_and_response')['status'] == 'conflicting'
    r['quantities']['partner_mass'] = point(150.0, 'kDa', 'm', ['span_mass'])
    assert judged(r, 'loading_and_response')['status'] == 'supported'


def test_a_stated_baseline_noise_replaces_the_fixed_noise_ends_of_the_response_and_the_decayed_signal():
    r = synthetic_record()
    r['quantities']['loading_level'] = point(1.0, 'nm', 'l', ['s'])
    r['quantities']['response_max'] = point(0.03, 'nm', 'r', ['s'])                           # fixed ends: degree 0.5
    assert judged(r, 'loading_and_response')['degree'] == pytest.approx(0.5)
    degrees = []
    for noise in (0.02, 0.01, 0.005, 0.002):                                                  # a quieter instrument: the same response is a better signal
        r['quantities']['baseline_noise'] = point(noise, 'nm', 'n', ['span_noise'])
        verdict = judged(r, 'loading_and_response')
        assert verdict['status'] == 'supported' and 'span_noise' in verdict['support_refs']
        degrees.append(verdict['degree'])
    assert degrees == pytest.approx([0.125, 0.5, 1.0, 1.0])                                    # monotone in the noise, gradual
    r['quantities']['baseline_noise'] = point(0.03, 'nm', 'n', ['span_noise'])                # response no larger than the stated noise: no signal
    assert judged(r, 'loading_and_response')['status'] == 'conflicting'
    r['quantities']['response_max'] = point(0.8, 'nm', 'r', ['span_response'])
    r['quantities']['dissociation_time'] = point(30.0, 's', 't', ['s'])                       # decayed signal 0.047 nm
    verdict = judged(r, 'dissociation_window')
    assert verdict['status'] == 'conflicting' or 'span_noise' in verdict['support_refs']
    r['quantities']['baseline_noise'] = point(0.002, 'nm', 'n', ['span_noise'])
    verdict = judged(r, 'dissociation_window')
    assert verdict['status'] == 'supported' and verdict['degree'] == 1.0 and 'span_noise' in verdict['support_refs']


def test_the_sheet_judges_the_replicate_count_with_a_degree():
    r = synthetic_record()
    # degree min(1, sqrt(n / 3)), the precision of the mean over n independent sensors; a stated count is never conflicting
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', (2 / 3) ** 0.5), (2, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None),
                                                 (1, 'yes', 'supported', (1 / 3) ** 0.5), (1, 'unknown', 'unknown', None)):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_sensors'] = fact(independent, ['s'] if independent != 'unknown' else [])
        verdict = judged(r, 'replicates')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (count, independent)
        if expected == 'unknown':
            assert verdict == {'status': 'unknown', 'support_refs': []}


def test_the_replicate_count_is_gradual_and_monotone_around_the_researched_minimum():
    r = synthetic_record()                                                                     # independent sensors: yes
    degrees = []
    for count in range(1, 8):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        verdict = judged(r, 'replicates')
        assert verdict['status'] == 'supported' and 0 < verdict['degree'] <= 1, count
        degrees.append(verdict['degree'])
        if verdict['degree'] < 1:
            assert convert_bli(grade_bli(r))['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(verdict['degree']), count
    assert degrees == sorted(degrees) and degrees[MIN_REPLICATES - 1:] == [1.0] * (len(degrees) - MIN_REPLICATES + 1)
    assert 0 < degrees[0] < degrees[MIN_REPLICATES - 2] < 1                                    # one and two runs: partial credit, not a conflict
    r['quantities']['replicate_count'] = {**r['quantities']['replicate_count'], 'status': 'unavailable', 'value': None}
    assert judged(r, 'replicates')['status'] == 'unknown'                                     # no count stated: unknown, not 0


def kinetic_degree(fold):
    return math.log(1.8 / fold) / math.log(1.8 / 1.2)                                          # linear in the log of the fold, 1.2-fold full, 1.8-fold zero


def test_the_sheet_judges_the_kd_from_the_rates_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM, kon 1e5: koff 2e-3 gives 20 nM
    for koff, expected, degree in ((2.0e-3, 'supported', 1.0), (2.3e-3, 'supported', 1.0), (2.4e-3, 'supported', 1.0), (2.8e-3, 'supported', kinetic_degree(1.4)), (3.4e-3, 'supported', kinetic_degree(1.7)),
                                   (3.8e-3, 'conflicting', None), (1.7e-3, 'supported', 1.0), (1.6e-3, 'supported', kinetic_degree(1.25)), (1.4e-3, 'supported', kinetic_degree(2.0 / 1.4)),
                                   (1.0e-3, 'conflicting', None), (0.6e-3, 'conflicting', None)):      # half the KD: twofold off, conflicting (was 0.5 on the one-sided relative gap)
        r['quantities']['koff'] = point(koff, 's^-1', 'koff', ['s'])
        verdict = judged(r, 'kinetic_consistency')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), koff


def test_the_kd_from_the_rates_is_judged_the_same_either_way_and_is_monotone_in_the_fold():
    r = synthetic_record()
    degrees = []
    for fold in (1.0, 1.1, 1.2, 1.25, 1.4, 1.6, 1.75):
        above, below = [], []
        for koff, side in ((2.0e-3 * fold, above), (2.0e-3 / fold, below)):
            r['quantities']['koff'] = point(koff, 's^-1', 'koff', ['s'])
            verdict = judged(r, 'kinetic_consistency')
            assert verdict['status'] == 'supported' and 0 < verdict['degree'] <= 1, (fold, koff)
            side.append(verdict['degree'])
        assert above == pytest.approx(below), fold                                             # koff/kon a factor above or below the KD: the same degree
        degrees.append(above[0])
    assert degrees == sorted(degrees, reverse=True) and degrees[2] == pytest.approx(1.0) and 0.85 < degrees[3] < 1.0      # just past 1.2-fold: partial credit close to full, no step


def agreement_degree(fold):
    return math.log(10.0 / fold) / math.log(10.0 / 2.0)                                        # linear in the log of the fold, 2-fold full, 10-fold zero


def test_the_sheet_judges_the_fold_between_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                     # kinetic KD 20 nM
    for steady, expected, degree in ((20.0, 'supported', 1.0), (40.0, 'supported', 1.0), (60.0, 'supported', agreement_degree(3.0)), (5.0, 'supported', agreement_degree(4.0)), (120.0, 'supported', agreement_degree(6.0)),
                                     (180.0, 'supported', agreement_degree(9.0)), (400.0, 'conflicting', None), (1.0, 'conflicting', None)):
        r['quantities']['kd_steady_state'] = point(steady, 'nM', 'ss', ['s'])
        verdict = judged(r, 'steady_state_vs_kinetic')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), steady
    assert agreement_degree(3.0) == pytest.approx(0.748, abs=1e-3) and agreement_degree(4.0) == pytest.approx(0.569, abs=1e-3)      # each doubling of the gap costs the same (was 0.875 and 0.75, linear in the fold)
    degrees = []
    for fold in (1.0, 2.0, 2.2, 3.0, 5.0, 8.0, 9.9):
        r['quantities']['kd_steady_state'] = point(20.0 * fold, 'nM', 'ss', ['s'])
        degrees.append(judged(r, 'steady_state_vs_kinetic')['degree'])
    assert degrees == sorted(degrees, reverse=True) and degrees[1] == pytest.approx(1.0) and 0.9 < degrees[2] < 1.0 and 0 < degrees[-1] < 0.01


def test_a_member_degree_reaches_the_sheet_interpretation_as_the_smallest_one():
    r = synthetic_record()
    r['quantities']['kd_steady_state'] = point(60.0, 'nM', 'ss', ['s'])                       # threefold: degree 0.748
    interpretation = convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(agreement_degree(3.0))
    r['concentration_series']['value'] = [4.0, 6.0, 20.0, 40.0, 60.0]                         # highest 3 x KD: degree 0.5
    assert convert_bli(grade_bli(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert convert_bli(grade_bli(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert convert_bli(grade_bli(synthetic_record()))['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(1.0)      # three independent sensors: full credit


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
    r['concentration_series']['value'] = [4.0, 6.0, 20.0, 40.0, 60.0]                         # highest 3 x KD: degree 0.5
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
