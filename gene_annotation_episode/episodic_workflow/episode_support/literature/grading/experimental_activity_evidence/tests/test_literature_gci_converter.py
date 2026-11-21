"""GCI converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import inspect
import math
import re
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_gci_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_gci_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CONCENTRATIONS_ZERO_COUNT, DISSOCIATION_DECAY_MIN, DISSOCIATION_DECAY_ZERO, RMAX_RATIO_MAX, RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MAX, RMAX_RATIO_ZERO_MIN, CRITERIA_MAP, HIGH_FACTOR, HIGH_ZERO_FACTOR, IMMOBILIZATION_MAX_PG_MM2, IMMOBILIZATION_ZERO_PG_MM2, KINETIC_FOLD, KINETIC_ZERO_FOLD,
    LOW_FACTOR, LOW_ZERO_FACTOR, MIN_CONCENTRATIONS, MIN_REPLICATES, NULL_REASONS, RESPONSE_MIN_PG_MM2, RESPONSE_ZERO_PG_MM2, SERIES_COUNT_CURVE_POWER, _criterion, convert_gci)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_grader import CRITERIA, grade_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import sparse_record, synthetic_record


def test_every_gci_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) <= set(CRITERIA)
    # kept out of the sheet on purpose: none (every criterion has a sheet counterpart)
    assert set(CRITERIA) - set(mapped) == set()


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_gci(grade_gci(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'gci'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'binding_species', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_other_converters_and_nulls_have_reasons():
    converted = convert_gci(grade_gci(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_the_chip_as_the_surface():
    converted = convert_gci(grade_gci(synthetic_record(analyte_prep='ana', immobilized_prep='lig', chip='chip_lot', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'ana', 'immobilized_preparation_ref': 'lig', 'surface_ref': 'chip_lot', 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_channels_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent replicates: variance 36 / 3 = 12
    assert convert_gci(grade_gci(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    # two independent replicates: the replicates criterion is supported with partial credit, so sd 6 nM still gives 36 / 2 = 18
    assert convert_gci(grade_gci(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(18.0)
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    r['facts']['independent_channels_or_chips'] = fact('unknown')
    converted = convert_gci(grade_gci(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_a_picomolar_spread_and_kd_are_converted_to_nanomolar():
    r = synthetic_record()
    r['quantities']['kd'] = point(94.0, 'pM', 'kd', ['s'])
    r['quantities']['kd_spread'] = point(10.0, 'pM', 'sp', ['s'])
    cells = convert_gci(grade_gci(r))['sheet']['cells']
    # KD 94 pM = 0.094 nM; standard error 10 pM = 0.01 nM -> variance 1e-4 nM^2
    assert cells['measured_effect']['value'] == pytest.approx(0.094) and cells['effect_variance']['value'] == pytest.approx(1e-4)


def test_missing_kd_and_confidence_interval_stay_null():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    assert convert_gci(grade_gci(r))['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_gci(grade_gci(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'kd_not_given_as_a_point_value'


def test_sparse_record_fills_only_the_effect():
    converted = convert_gci(grade_gci(sparse_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == 20.0
    assert cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_conflicting_unknown_and_not_applicable_members_combine_by_the_rule():
    r = synthetic_record()
    r['facts']['nonspecific_binding_checked'] = fact('no', ['s'])
    r['facts']['baseline_stable'] = fact('unknown')
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['binding_controls']['status'] == 'conflicting'
    r = synthetic_record()
    r['facts']['bulk_solvent_corrected'] = fact('not_applicable')     # dropped: the other binding_controls members are supported
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['binding_controls']['status'] == 'supported'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    r['quantities']['kd_steady_state'] = {**r['quantities']['kd_steady_state'], 'status': 'unavailable', 'value': None}
    # steady_state_vs_kinetic is not_applicable and dropped; the other binding_regime members are supported
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']['status'] == 'supported'
    r['facts']['mass_transport_checked'] = fact('unknown')
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']['status'] == 'unknown'
    r = synthetic_record()
    r['quantities']['response_max'] = point(0.05, 'pg/mm2', 'r', ['s'])                       # a response below the noise is shown against the standard
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'
    r = synthetic_record()
    r['quantities']['immobilization_level'] = point(5000.0, 'pg/mm2', 'l', ['s'])             # a dense surface: no credit, but never conflicting (the level is a proxy)
    r['quantities']['analyte_mass'] = point(2.0, 'kDa', 'm', ['s'])                           # keeps the maximum response ratio in range (2 / 100 x 5000 = 100 pg/mm2, ratio 0.4)
    got = convert_gci(grade_gci(r))['extraction']['interpretations']['calibration_applicability']
    assert got['status'] == 'supported' and got['degree'] == 0.0


def judged(record, name):
    return _criterion(grade_gci(record), name)


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_CONCENTRATIONS, CONCENTRATIONS_ZERO_COUNT, SERIES_COUNT_CURVE_POWER, LOW_FACTOR, LOW_ZERO_FACTOR, HIGH_FACTOR, HIGH_ZERO_FACTOR, MIN_REPLICATES) == (5, 1, 2, 0.2, 1.0, 5.0, 1.0, 3)
    assert (IMMOBILIZATION_MAX_PG_MM2, IMMOBILIZATION_ZERO_PG_MM2, RESPONSE_MIN_PG_MM2, RESPONSE_ZERO_PG_MM2) == (2000.0, 4000.0, 1.0, 0.1)
    assert (KINETIC_FOLD, KINETIC_ZERO_FOLD, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (1.2, 1.8, 2.0, 10.0)
    assert (RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MIN, RMAX_RATIO_MAX, RMAX_RATIO_ZERO_MAX, DISSOCIATION_DECAY_MIN, DISSOCIATION_DECAY_ZERO) == (0.3, 0.1, 1.2, 2.0, 0.05, 0.01)


def test_every_number_the_judges_use_is_a_named_expert_review_constant():
    source = inspect.getsource(literature_gci_converter)
    constants = [line for line in source.splitlines() if re.match(r'^[A-Z][A-Z0-9_]* = [0-9]', line)]
    assert len(constants) == 22 and all('# EXPERT_REVIEW: ' in line for line in constants)


def test_the_range_review_answers_are_written_for_every_researched_value():
    doc = literature_gci_converter.__doc__
    review = doc[doc.index('Range review'):]
    for name in ('MIN_CONCENTRATIONS', 'CONCENTRATIONS_ZERO_COUNT', 'SERIES_COUNT_CURVE_POWER', 'LOW_FACTOR', 'LOW_ZERO_FACTOR', 'HIGH_FACTOR', 'HIGH_ZERO_FACTOR', 'IMMOBILIZATION_MAX_PG_MM2', 'IMMOBILIZATION_ZERO_PG_MM2',
                 'RESPONSE_MIN_PG_MM2', 'RESPONSE_ZERO_PG_MM2', 'MIN_REPLICATES', 'KINETIC_FOLD', 'KINETIC_ZERO_FOLD', 'AGREEMENT_FACTOR', 'AGREEMENT_ZERO_FACTOR',
                 'RMAX_RATIO_MIN', 'RMAX_RATIO_ZERO_MIN', 'RMAX_RATIO_MAX', 'RMAX_RATIO_ZERO_MAX', 'DISSOCIATION_DECAY_MIN', 'DISSOCIATION_DECAY_ZERO'):
        assert name in review, name
    assert all(q in review for q in ('Q1', 'Q2', 'Q3', 'Q4', 'Q5')) and 'Grader gaps' in review


def test_the_sheet_judges_the_surface_level_and_the_response_with_a_degree():
    r = synthetic_record()                                                                     # level 500 pg/mm2, response 40 pg/mm2
    for level, response, expected, degree in ((2000.0, 1.0, 'supported', 1.0), (3000.0, 40.0, 'supported', 0.5), (500.0, 0.55, 'supported', 0.5), (3000.0, 0.55, 'supported', 0.5), (3500.0, 0.325, 'supported', 0.25),
                                              (4000.0, 40.0, 'supported', 0.0), (6000.0, 40.0, 'supported', 0.0),       # the level's zero end: no credit, never conflicting (a proxy without the masses)
                                              (500.0, 0.1, 'conflicting', None), (500.0, 0.0, 'conflicting', None), (6000.0, 0.05, 'conflicting', None)):
        r['quantities']['immobilization_level'] = point(level, 'pg/mm2', 'l', ['s'])
        r['quantities']['response_max'] = point(response, 'pg/mm2', 'r', ['s'])
        verdict = judged(r, 'surface_level_and_response')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (level, response)
    degrees = []
    for level in (500.0, 2000.0, 2500.0, 3000.0, 3900.0, 4000.0, 8000.0):                     # a denser surface never raises the degree
        r['quantities']['immobilization_level'] = point(level, 'pg/mm2', 'l', ['s'])
        r['quantities']['response_max'] = point(40.0, 'pg/mm2', 'r', ['s'])
        degrees.append(judged(r, 'surface_level_and_response')['degree'])
    assert degrees == sorted(degrees, reverse=True) and 0 < degrees[4] < 1
    r = synthetic_record()
    r['quantities']['response_max'] = {**r['quantities']['response_max'], 'status': 'unavailable', 'value': None}
    assert judged(r, 'surface_level_and_response') == {'status': 'unknown', 'support_refs': []}      # the level alone cannot make it supported
    r['quantities']['immobilization_level'] = point(6000.0, 'pg/mm2', 'l', ['s'])
    assert judged(r, 'surface_level_and_response') == {'status': 'unknown', 'support_refs': []}      # nor conflicting (it was conflicting before the range review)
    r = synthetic_record()
    r['quantities']['immobilization_level'] = {**r['quantities']['immobilization_level'], 'status': 'unavailable', 'value': None}
    r['quantities']['response_max'] = point(0.05, 'pg/mm2', 'r', ['s'])
    assert judged(r, 'surface_level_and_response')['status'] == 'conflicting'                      # a response below the noise is conflicting on its own


def test_the_sheet_judges_the_maximum_response_ratio_with_a_degree_and_no_step():
    r = synthetic_record()                                                                     # theoretical 100 pg/mm2
    degrees = []
    for response in (10.0, 15.0, 20.0, 30.0, 40.0, 120.0, 140.0, 160.0, 200.0):                # ratios 0.1 .. 2.0
        r['quantities']['response_max'] = point(response, 'pg/mm2', 'r', ['s'])
        verdict = judged(r, 'rmax_consistency')
        degrees.append(0.0 if verdict['status'] == 'conflicting' else verdict['degree'])
        assert verdict['status'] == ('conflicting' if response in (10.0, 200.0) else 'supported') and 0.0 <= degrees[-1] <= 1.0, response
    assert degrees == pytest.approx([0.0, 0.25, 0.5, 1.0, 1.0, 1.0, 0.75, 0.5, 0.0]) and degrees[1] > 0       # just inside the researched ends: partial credit, no step; better never lowers it
    assert degrees[:5] == sorted(degrees[:5]) and degrees[5:] == sorted(degrees[5:], reverse=True)
    r['quantities']['stoichiometry'] = {**r['quantities']['stoichiometry'], 'status': 'unavailable', 'value': None}
    assert judged(r, 'rmax_consistency') == {'status': 'unknown', 'support_refs': []}            # not stated: unknown, never 0
    got = convert_gci(grade_gci(synthetic_record()))['extraction']['interpretations']['calibration_applicability']
    assert got['status'] == 'supported' and got['degree'] == 1.0
    r = synthetic_record()
    r['quantities']['response_max'] = point(20.0, 'pg/mm2', 'r', ['s'])                         # rmax degree 0.5 is the weakest member of calibration_applicability
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)
    r['quantities']['analyte_mass'] = {**r['quantities']['analyte_mass'], 'status': 'unavailable', 'value': None}
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'unknown'


def test_the_sheet_judges_the_dissociation_decay_with_a_degree_and_no_step():
    r = synthetic_record()                                                                     # koff 2.0e-3 s^-1, response 40 pg/mm2
    degrees = []
    for seconds in (2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 600.0):                                  # decays 0.4 % .. 70 %
        r['quantities']['dissociation_time'] = point(seconds, 's', 't', ['s'])
        verdict = judged(r, 'dissociation_window')
        decay = 1 - math.exp(-2.0e-3 * seconds)
        expected = None if decay <= DISSOCIATION_DECAY_ZERO else min(1.0, (decay - DISSOCIATION_DECAY_ZERO) / (DISSOCIATION_DECAY_MIN - DISSOCIATION_DECAY_ZERO))
        assert verdict['status'] == ('conflicting' if expected is None else 'supported') and verdict.get('degree') == (pytest.approx(expected) if expected is not None else None), seconds
        degrees.append(verdict.get('degree', 0.0))
    assert degrees == sorted(degrees) and 0 < degrees[3] < 1 and degrees[-1] == 1.0              # longer never lowers it; partial credit between 1 % and 5 %
    r['quantities']['response_max'] = point(0.5, 'pg/mm2', 'r', ['s'])                          # 70 % of a 0.5 pg/mm2 response: 0.35 pg/mm2 decayed, below the 1 pg/mm2 full-credit end
    assert judged(r, 'dissociation_window')['degree'] == pytest.approx((0.6988 * 0.5 - RESPONSE_ZERO_PG_MM2) / (RESPONSE_MIN_PG_MM2 - RESPONSE_ZERO_PG_MM2), abs=1e-3)
    interpretation = convert_gci(grade_gci(synthetic_record()))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and 'degree' in interpretation


def occupancy(r):
    return r / (1 + r)


def test_the_sheet_judges_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM
    low_06 = (0.5 - occupancy(0.6)) / (0.5 - occupancy(0.2))                                  # lowest 0.6 x KD on the occupancy scale: 0.375
    high_3 = (occupancy(3.0) - 0.5) / (occupancy(5.0) - 0.5)                                  # highest 3 x KD: 0.75
    assert low_06 == pytest.approx(0.375) and high_3 == pytest.approx(0.75)
    for series, expected, degree in (([2.0, 4.0, 20.0, 100.0, 200.0], 'supported', 1.0), ([12.0, 20.0, 40.0, 100.0, 200.0], 'supported', low_06), ([4.0, 6.0, 20.0, 40.0, 60.0], 'supported', high_3),
                                     ([20.0, 40.0, 60.0, 100.0, 200.0], 'conflicting', None), ([2.0, 4.0, 6.0, 10.0, 20.0], 'conflicting', None), ([2.0, 20.0, 200.0, 600.0], 'supported', 1 - (1 / 4) ** 2)):
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
        interpretation = convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), series


def test_the_concentration_count_is_a_curve_full_from_five_partial_below_and_monotone():
    r = synthetic_record()                                                                     # KD 20 nM; every series spans 0.1 x to 10 x KD, so only the count varies
    # one concentration: its lowest and highest are the same point, so it cannot bracket the KD: conflicting by the lowest-over-KD ramp, not by its count
    ladder = {1: [200.0], 2: [2.0, 200.0], 3: [2.0, 20.0, 200.0], 4: [2.0, 6.0, 60.0, 200.0], 5: [2.0, 6.0, 20.0, 60.0, 200.0], 6: [2.0, 4.0, 10.0, 20.0, 60.0, 200.0], 8: [2.0, 3.0, 6.0, 10.0, 20.0, 40.0, 100.0, 200.0]}
    expected = {1: None, 2: 0.4375, 3: 0.75, 4: 0.9375, 5: 1.0, 6: 1.0, 8: 1.0}               # concave, as BLI: 1 - ((5 - n) / (5 - 1))^2, capped at 1
    assert all(expected[n] == pytest.approx(1 - ((MIN_CONCENTRATIONS - n) / (MIN_CONCENTRATIONS - CONCENTRATIONS_ZERO_COUNT)) ** SERIES_COUNT_CURVE_POWER) for n in (2, 3, 4, 5))
    steps = [expected[n + 1] - expected[n] for n in (2, 3, 4)]
    assert steps == sorted(steps, reverse=True)                                                # each added concentration adds less than the one before (gentle near five)
    degrees = []
    for count, series in ladder.items():
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        if expected[count] is None:
            assert verdict['status'] == 'conflicting' and 'degree' not in verdict                 # 200 nM is 10 x KD as its lowest: the ramp's zero end
            degrees.append(0.0)
        else:
            assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(expected[count]), count
            degrees.append(verdict['degree'])
    assert degrees == sorted(degrees)                                                          # more concentrations never lower the degree
    assert 0 < expected[MIN_CONCENTRATIONS - 1] < 1                                           # just below the researched value: partial credit, no step to 0
    alone = literature_gci_converter._judge_series({**grade_gci(synthetic_record())['native'], 'concentration_count': 1, 'concentration_low_over_kd': 0.1, 'concentration_high_over_kd': 10.0})
    assert alone['status'] == 'supported' and alone['degree'] == 0.0                         # the count alone (span ratios fine): no credit, never conflicting
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert judged(r, 'concentration_series')['status'] == 'unknown' and 'degree' not in judged(r, 'concentration_series')     # not stated: unknown, never 0


def test_the_sheet_judges_waverapid_on_the_highest_concentration_only():
    r = synthetic_record()
    r['facts']['repeated_pulse_kinetics_used'] = fact('yes', ['s'])
    for series, expected, degree in (([200.0], 'supported', 1.0), ([100.0], 'supported', 1.0), ([60.0], 'supported', 0.75), ([20.0], 'conflicting', None), ([2.0, 20.0, 60.0], 'supported', 0.75)):      # no count asked, no lowest asked; 3 x KD samples 75 % saturation: 0.75 on the occupancy scale
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
    r['facts']['repeated_pulse_kinetics_used'] = fact('no')
    r['concentration_series']['value'] = [200.0]
    assert judged(r, 'concentration_series')['status'] == 'conflicting'


def test_the_sheet_judges_the_replicate_count_with_a_degree():
    r = synthetic_record()
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', (2 / 3) ** 0.5), (1, 'yes', 'supported', (1 / 3) ** 0.5),
                                                 (2, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None), (1, 'unknown', 'unknown', None)):      # sqrt(n / 3); a stated count is never conflicting
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_channels_or_chips'] = fact(independent, ['s'] if independent != 'unknown' else [])
        verdict = judged(r, 'replicates')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (count, independent)


def test_the_replicate_count_is_a_curve_full_from_three_partial_below_and_monotone():
    r = synthetic_record()
    degrees = []
    for count in (1, 2, 3, 4, 6):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        verdict = judged(r, 'replicates')
        degrees.append(verdict.get('degree', 0.0))
        assert 0.0 <= degrees[-1] <= 1.0
    assert degrees == pytest.approx([(1 / 3) ** 0.5, (2 / 3) ** 0.5, 1.0, 1.0, 1.0]) and degrees == sorted(degrees)      # sqrt(n / 3), capped at 1
    r['quantities']['replicate_count'] = point(MIN_REPLICATES - 1, 'count', 'n', ['s'])
    assert judged(r, 'replicates')['status'] == 'supported' and 0 < judged(r, 'replicates')['degree'] < 1      # just below the researched value: partial credit
    interpretation = convert_gci(grade_gci(r))['extraction']['interpretations']['sampling_basis']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx((2 / 3) ** 0.5)
    r['quantities']['replicate_count'] = {**r['quantities']['replicate_count'], 'status': 'unavailable', 'value': None}
    assert judged(r, 'replicates')['status'] == 'unknown' and 'degree' not in judged(r, 'replicates')               # not stated: unknown, never 0


def log_share(fold, full, zero):
    return math.log(zero / fold) / math.log(zero / full)


def test_the_sheet_judges_the_kd_from_the_rates_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM, kon 1e5: koff 2e-3 gives 20 nM
    for koff, expected, degree in ((2.0e-3, 'supported', 1.0), (2.3e-3, 'supported', 1.0), (2.8e-3, 'supported', log_share(1.4, 1.2, 1.8)), (3.4e-3, 'supported', log_share(1.7, 1.2, 1.8)), (3.8e-3, 'conflicting', None),
                                   (1.7e-3, 'supported', 1.0), (1.6e-3, 'supported', log_share(1.25, 1.2, 1.8)), (1.0e-3, 'conflicting', None), (0.3e-3, 'conflicting', None)):
        r['quantities']['koff'] = point(koff, 's^-1', 'koff', ['s'])
        verdict = judged(r, 'kinetic_consistency')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), koff


def test_the_kd_from_the_rates_is_judged_on_a_symmetric_fold():
    r = synthetic_record()                                                                     # KD 20 nM
    for fold in (1.1, 1.3, 1.5, 1.7, 1.9, 2.5, 5.0):                                          # the same fold above and below the KD gets the same verdict (the old relative gap gave 5 x below partial credit)
        r['quantities']['koff'] = point(2.0e-3 * fold, 's^-1', 'koff', ['s'])
        above = judged(r, 'kinetic_consistency')
        r['quantities']['koff'] = point(2.0e-3 / fold, 's^-1', 'koff', ['s'])
        below = judged(r, 'kinetic_consistency')
        assert above['status'] == below['status'] and above.get('degree') == (pytest.approx(below['degree']) if 'degree' in below else None), fold
    degrees = []
    for kd_from_rates in (20.0, 23.0, 25.0, 28.0, 32.0, 35.0):                               # a wider fold never raises the degree, and no step at KINETIC_FOLD
        r['quantities']['koff'] = point(kd_from_rates * 1e-4, 's^-1', 'koff', ['s'])
        degrees.append(judged(r, 'kinetic_consistency')['degree'])
    assert degrees == sorted(degrees, reverse=True) and 0 < degrees[2] < 1


def test_the_sheet_judges_the_fold_between_the_two_estimates_with_a_degree():
    r = synthetic_record()                                                                     # kinetic KD 20 nM; linear in log fold from 2 to 10
    for steady, expected, degree in ((20.0, 'supported', 1.0), (40.0, 'supported', 1.0), (60.0, 'supported', log_share(3, 2, 10)), (5.0, 'supported', log_share(4, 2, 10)), (120.0, 'supported', log_share(6, 2, 10)),
                                     (180.0, 'supported', log_share(9, 2, 10)), (400.0, 'conflicting', None), (1.0, 'conflicting', None)):
        r['quantities']['kd_steady_state'] = point(steady, 'nM', 'ss', ['s'])
        verdict = judged(r, 'steady_state_vs_kinetic')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), steady
    assert log_share(3, 2, 10) == pytest.approx(0.748, abs=1e-3) and log_share(6, 2, 10) == pytest.approx(0.317, abs=1e-3)      # equal ratios, equal steps
    degrees = []
    for steady in (40.0, 44.0, 60.0, 100.0, 160.0, 199.0):                                    # a wider gap never raises the degree, no step at AGREEMENT_FACTOR
        r['quantities']['kd_steady_state'] = point(steady, 'nM', 'ss', ['s'])
        degrees.append(judged(r, 'steady_state_vs_kinetic')['degree'])
    assert degrees == sorted(degrees, reverse=True) and 0 < degrees[1] < 1


def test_a_member_degree_reaches_the_sheet_interpretation_as_the_smallest_one():
    r = synthetic_record()
    r['quantities']['kd_steady_state'] = point(60.0, 'nM', 'ss', ['s'])                       # threefold: degree log(10/3) / log(5), about 0.748
    interpretation = convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(log_share(3, 2, 10))
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]                    # lowest 0.6 x KD: degree 0.375 on the occupancy scale
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(0.375)
    assert convert_gci(grade_gci(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.375)
    assert convert_gci(grade_gci(synthetic_record()))['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(1.0)      # three independent replicates: full credit


def interpretations_of(record):
    return convert_gci(grade_gci(record))['extraction']['interpretations']


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
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]                    # lowest 0.6 x KD: degree 0.375
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.375)
    r['concentration_series']['support'] = 'implied'
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.2625)
    r['quantities']['kd'] = point(20.0, 'nM', 'kd', ['s'], support='about_something_else')
    assert interpretations_of(r)['binding_regime']['degree'] == pytest.approx(0.1125)           # 0.375 x 0.3, not 0.375 x 0.7 x 0.3


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
