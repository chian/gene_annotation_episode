"""FCS converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import (
    ACQUISITION_NOISE_EXPONENT, CRITERIA_MAP, DEPLETION_BIAS_SLOPE, KON_SLOW_PER_M_S, DIFFUSION_RATIO_ZERO_AGREEMENT, EQUILIBRATION_HALF_LIVES, FRACTION_BOUND_ZERO_AGREEMENT_PERCENT, JUDGES, KON_MAX_PER_M_S,
    LABELLED_HIGH_ZERO_AGREEMENT_NM, LABELLED_LOW_ZERO_AGREEMENT_NM, LABELLED_MAX_OVER_KD, LABELLED_OVER_KD_ZERO_AGREEMENT, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR,
    COUNT_RATE_ZERO_KHZ, MASS_CONSISTENCY_FACTOR, MASS_CONSISTENCY_ZERO_FACTOR, MAX_COUNT_RATE_KHZ, MAX_LABELLED_NM, PHOTONS_PER_KHZ_US, REFERENCE_BRIGHTNESS_KHZ, REFERENCE_DIFFUSION_TIME_US, TYPICAL_TIME_SCATTER, MAX_PARTICLE_NUMBER, MIN_CONCENTRATIONS, MIN_DIFFUSION_RATIO, MIN_FRACTION_BOUND_MAXIMUM_PERCENT, MIN_INCUBATION_MIN, MIN_LABELLED_NM, MIN_PARTICLE_NUMBER,
    MIN_REPLICATES, MIN_TOTAL_ACQUISITION_S, NULL_REASONS, PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT, PARTICLE_NUMBER_LOW_ZERO_AGREEMENT, REPLICATE_PRECISION_EXPONENT, SERIES_PRECISION_EXPONENT,
    TIGHT_BINDING_FULL_OVER_KD, TIGHT_BINDING_ZERO_OVER_KD, convert_fcs)
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


def test_fewer_independent_titrations_give_the_precision_of_their_mean_and_their_sd_becomes_a_variance():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    converted = convert_fcs(grade_fcs(r))
    # replicates are the precision of the mean, sqrt(n / 3): two give 0.82, so sd 6 nM over 2 gives 36 / 2 = 18
    assert converted['extraction']['interpretations']['sampling_basis']['status'] == 'supported' and converted['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx((2 / 3) ** 0.5)
    assert converted['sheet']['cells']['effect_variance']['value'] == pytest.approx(18.0)
    r['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])
    converted = convert_fcs(grade_fcs(r))
    # one independent titration still gives a fitted KD: low partial credit, never conflicting (was conflicting)
    assert converted['extraction']['interpretations']['sampling_basis']['status'] == 'supported' and converted['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx((1 / 3) ** 0.5)
    assert converted['sheet']['cells']['effect_variance']['value'] == pytest.approx(36.0)


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
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MIN_INCUBATION_MIN, MIN_TOTAL_ACQUISITION_S, MIN_REPLICATES) == (8, 0.2, 1.0, 5.0, 60.0, 3)
    # the zero ends and the shapes added by the softening and the 2026-11-21 review (EXPERT_REVIEW, owner to confirm)
    assert (PARTICLE_NUMBER_LOW_ZERO_AGREEMENT, PARTICLE_NUMBER_HIGH_ZERO_AGREEMENT, LABELLED_LOW_ZERO_AGREEMENT_NM, LABELLED_HIGH_ZERO_AGREEMENT_NM) == (0.01, 100.0, 0.03, 300.0)
    assert (ACQUISITION_NOISE_EXPONENT, SERIES_PRECISION_EXPONENT, REPLICATE_PRECISION_EXPONENT) == (0.5, 0.5, 0.5)
    assert (TYPICAL_TIME_SCATTER, MAX_COUNT_RATE_KHZ, COUNT_RATE_ZERO_KHZ, REFERENCE_DIFFUSION_TIME_US, REFERENCE_BRIGHTNESS_KHZ) == (0.10, 1000.0, 10000.0, 1000.0, 10.0)      # added 2026-11-21, the grader gaps
    assert (TIGHT_BINDING_FULL_OVER_KD, TIGHT_BINDING_ZERO_OVER_KD, KON_MAX_PER_M_S, EQUILIBRATION_HALF_LIVES) == (10.0, 100.0, 1.0e8, 5.0)
    assert (KON_SLOW_PER_M_S, DEPLETION_BIAS_SLOPE) == (1.0e5, 0.5)      # added 2026-11-21 (decisions A and B)


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


# The softened former lone limits (A105_EXPERIMENT_SOP step 3): monotone, bounded, no step at the researched value, unknown stays unknown.
def _credit(verdict):
    """The credit of a judged verdict: the degree when supported with one, 1.0 when supported without one, 0.0 when conflicting, None when unknown."""
    if verdict['status'] == 'unknown':
        return None
    if verdict['status'] == 'conflicting':
        assert 'degree' not in verdict and verdict['support_refs']
        return 0.0
    return verdict.get('degree', 1.0)


def _judge(criterion, reason, native):
    return JUDGES[(criterion, reason)](native)


def _particle(number, rate=None):
    return _credit(_judge('labelled_range', 'particle_number_recorded_for_the_sheet', {'particle_number_used': number, 'count_rate_kHz': rate, 'labelled_range_refs': ['s']}))


def _labelled(nm):
    return _credit(_judge('labelled_range', 'labelled_concentration_recorded_for_the_sheet', {'labelled_nM': nm, 'labelled_range_refs': ['s']}))


def _count(count, low=0.1, high=20.0):
    native = {'concentration_count': count, 'concentration_count_refs': ['s'], 'concentration_low_over_constant': low, 'concentration_high_over_constant': high, 'concentration_span_refs': ['s']}
    return _judge('concentration_series', 'concentration_series_recorded_for_the_sheet', native)


def _acquisition(total, repeats_given=True, free_time_us=None, brightness_kHz=None):
    return _judge('acquisition', 'acquisition_recorded_for_the_sheet', {'acquisition_total_s': total, 'measurement_repeats_given': repeats_given, 'free_diffusion_time_us': free_time_us, 'brightness_kHz': brightness_kHz, 'acquisition_refs': ['s']})


def _diffusion(ratio, scatter=None):
    return _judge('diffusion_change', 'diffusion_ratio_recorded_for_the_sheet', {'diffusion_ratio': ratio, 'diffusion_time_scatter': scatter, 'diffusion_refs': ['s']})


def _replicates(count, independent='yes'):
    return _judge('replicates', 'replicate_count_recorded_for_the_sheet', {'replicate_count': count, 'replicate_independent': independent, 'replicate_refs': ['s']})


def _non_decreasing(credits):
    return all(a <= b + 1e-12 for a, b in zip(credits, credits[1:]))


def test_the_labelled_range_rises_to_full_credit_inside_the_window_and_falls_outside_it_with_no_step():
    dilute = [_particle(n) for n in (0.001, 0.01, 0.02, 0.05, 0.09, 0.099, 0.1, 0.8)]
    crowded = [_particle(n) for n in (0.8, 10.0, 10.1, 12.0, 30.0, 99.0, 100.0, 500.0)]
    assert _non_decreasing(dilute) and _non_decreasing(crowded[::-1]) and all(0.0 <= c <= 1.0 for c in dilute + crowded)
    assert _particle(0.1) == _particle(10.0) == 1.0 and _particle(0.01) == _particle(100.0) == 0.0
    assert 0.99 < _particle(0.0999) < 1.0 and 0.99 < _particle(10.01) < 1.0       # just outside the researched window: nearly full credit, not 0
    assert _particle(10 ** -1.5) == pytest.approx(0.5) and _particle(10 ** 1.5) == pytest.approx(0.5)      # halfway in the logarithm
    nanomolar = [_labelled(c) for c in (0.01, 0.03, 0.1, 0.29, 0.3, 2.0, 30.0, 31.0, 100.0, 300.0, 1000.0)]
    assert _non_decreasing(nanomolar[:6]) and _non_decreasing(nanomolar[5:][::-1]) and all(0.0 <= c <= 1.0 for c in nanomolar)
    assert 0.99 < _labelled(0.2999) < 1.0 and 0.99 < _labelled(30.01) < 1.0 and _labelled(0.03) == _labelled(300.0) == 0.0


def test_the_stated_scatter_of_the_free_diffusion_time_raises_the_ratio_needed_and_never_lowers_it_below_the_typical_one():
    assert _credit(_diffusion(1.3)) == 1.0 and _credit(_diffusion(1.3, 0.05)) == 1.0 and _credit(_diffusion(1.3, TYPICAL_TIME_SCATTER)) == 1.0   # no scatter, a smaller one and the typical one: 1.3 as committed
    assert _credit(_diffusion(1.15, 0.05)) == _credit(_diffusion(1.15)) == pytest.approx(0.5)                # a small stated scatter does not lower the need
    assert _credit(_diffusion(1.3, 0.20)) == pytest.approx(0.3 / 0.6) and _credit(_diffusion(1.6, 0.20)) == 1.0      # twice the typical scatter: full credit needs a ratio of 1.6
    credits = [_credit(_diffusion(1.3, scatter)) for scatter in (0.0, 0.1, 0.15, 0.2, 0.3, 0.5)]
    assert all(b <= a for a, b in zip(credits, credits[1:])) and all(0.0 < c <= 1.0 for c in credits)         # a larger scatter never raises the credit, and the credit stays partial (no step)
    assert _diffusion(1.0, 0.2)['status'] == 'conflicting' and _diffusion(1.3, 0.2)['status'] == 'supported'


def test_the_count_rate_is_judged_against_the_detector_range_with_the_particle_number_and_the_weaker_counts():
    assert _particle(0.8, MAX_COUNT_RATE_KHZ) == _particle(0.8, 10.0) == 1.0 and _particle(0.8) == 1.0          # at and below the linear range, and not known
    assert _particle(0.8, COUNT_RATE_ZERO_KHZ) == 0.0 and _credit(_judge('labelled_range', 'particle_number_recorded_for_the_sheet', {'particle_number_used': 0.8, 'count_rate_kHz': COUNT_RATE_ZERO_KHZ, 'labelled_range_refs': ['s']})) == 0.0
    rates = [_particle(0.8, r) for r in (500.0, 1000.0, 1001.0, 2000.0, 3000.0, 5000.0, 9999.0, 10000.0, 50000.0)]
    assert all(b <= a for a, b in zip(rates, rates[1:])) and all(0.0 <= c <= 1.0 for c in rates) and 0.99 < rates[2] < 1.0      # monotone, bounded, no step
    assert _particle(0.8, 10 ** 3.5) == pytest.approx(0.5)                                                      # halfway in the logarithm
    assert _particle(0.05, 100.0) == _particle(0.05) and _particle(0.05, 100000.0) == 0.0                        # the weaker of the window and the rate counts


def test_the_labelled_concentration_with_the_detection_volume_is_judged_as_a_particle_number():
    judged = _judge('labelled_range', 'particle_number_derived_from_volume_recorded_for_the_sheet', {'particle_number_used': 0.8, 'count_rate_kHz': None, 'labelled_range_refs': ['s']})
    assert judged == {'status': 'supported', 'support_refs': ['s']}
    assert ('labelled_range', 'particle_number_derived_from_volume_recorded_for_the_sheet') in JUDGES


def test_the_acquisition_needed_scales_with_the_diffusion_time_and_the_brightness_and_is_the_committed_sixty_seconds_at_the_reference():
    ref_time, ref_brightness = REFERENCE_DIFFUSION_TIME_US, REFERENCE_BRIGHTNESS_KHZ
    assert _credit(_acquisition(60.0, True, ref_time, ref_brightness)) == 1.0 and _credit(_acquisition(15.0, True, ref_time, ref_brightness)) == pytest.approx(0.5)   # as before
    assert _credit(_acquisition(15.0, True, ref_time, None)) == pytest.approx(0.5) and _credit(_acquisition(15.0, True, None, ref_brightness)) == pytest.approx(0.5)  # a value not given is at its reference
    assert _credit(_acquisition(30.0, True, 2 * ref_time, ref_brightness)) < 1.0 and _credit(_acquisition(60.0, True, 2 * ref_time, ref_brightness)) < 1.0   # a slower molecule needs more time
    assert _credit(_acquisition(60.0, True, ref_time / 10, ref_brightness)) == 1.0 and _credit(_acquisition(25.0, True, ref_time / 10, ref_brightness)) == 1.0      # a faster one needs less (20 s: a tenth of the passage time, but fewer photons per passage)
    dim = [_credit(_acquisition(10.0, True, 60.0, b)) for b in (0.5, 1.0, 2.0, 5.0, 12.0, 100.0)]                # a brighter molecule never needs more time
    assert all(b >= a for a, b in zip(dim, dim[1:])) and all(0.0 < c <= 1.0 for c in dim)
    bright = (_credit(_acquisition(10.0, True, 1000.0, 1000.0)), _credit(_acquisition(10.0, True, 1000.0, 100000.0)))
    assert bright[0] == pytest.approx(bright[1], rel=0.02)                                                       # above a photon per passage a brighter dye does not help
    assert _acquisition(5.0, False, 1000.0, ref_brightness)['status'] == 'unknown'                               # a short single measurement is still unknown
    assert PHOTONS_PER_KHZ_US == 1.0e-3


def test_the_concentration_count_is_the_precision_of_its_points_and_a_short_series_is_low_partial_credit_never_conflicting():
    credits = [_credit(_count(n)) for n in range(1, 13)]
    assert _non_decreasing(credits) and all(0.0 < c <= 1.0 for c in credits)
    assert all(_count(n)['status'] == 'supported' for n in range(1, 13))            # was conflicting at three or fewer
    assert _credit(_count(MIN_CONCENTRATIONS)) == 1.0 and _credit(_count(2)) == pytest.approx(0.5) and _credit(_count(1)) == pytest.approx(0.125 ** 0.5)
    assert 0.9 < _credit(_count(7)) < 1.0                                          # just below the researched count: nearly full, no step
    assert _credit(_count(7, low=0.6)) == pytest.approx(0.375)                     # the weaker of the count (0.94) and the low end on the occupancy scale: (0.5 - 0.375) / (0.5 - 1 / 6) = 0.375 (was 0.5, linear in x)
    assert _credit(_count(12, low=0.5)) == pytest.approx(0.5) and _credit(_count(12, low=0.25)) == pytest.approx(0.9) and _credit(_count(12, low=0.2)) == 1.0 and _count(12, low=1.0)['status'] == 'conflicting'
    lows = [_credit(_count(12, low=x)) for x in (0.99, 0.8, 0.5, 0.25, 0.21, 0.2, 0.1)]
    assert _non_decreasing(lows) and 0.99 < _credit(_count(12, low=0.2001)) < 1.0 and _credit(_count(12, low=0.99)) > 0.0      # no step at either end
    assert _count(7, low=None, high=None)['status'] == 'unknown' and _count(2, low=None, high=None)['status'] == 'unknown'      # no list: unknown, never opposition


def test_the_high_end_of_the_span_is_judged_on_the_saturation_scale_so_the_same_reach_gets_the_same_credit():
    saturation = JUDGES[('saturation', 'fraction_bound_maximum_recorded_for_the_sheet')]
    for over_kd in (0.5, 1.0, 2.0, 3.0):
        percent = 100.0 * over_kd / (1.0 + over_kd)
        assert _credit(_count(12, high=over_kd)) == pytest.approx(_credit(saturation({'fraction_bound_maximum': percent, 'fraction_bound_maximum_refs': ['s']})))
    assert _credit(_count(12, high=1.0)) == pytest.approx(0.5)                     # a top at the KD, half bound: half credit (was conflicting)
    assert _credit(_count(12, high=4.0)) == 1.0 and _count(12, high=0.25)['status'] == 'conflicting'      # 80 percent full, 20 percent conflicting
    highs = [_credit(_count(12, high=h)) for h in (0.25, 0.3, 0.5, 1.0, 2.0, 3.9, 4.0, 100.0)]
    assert _non_decreasing(highs) and 0.99 < _credit(_count(12, high=3.99)) < 1.0


def test_the_mass_mismatch_falls_with_the_logarithm_of_the_fold_either_way():
    def mass(ratio, expected):
        return _credit(_judge('mass_consistency', 'mass_consistency_recorded_for_the_sheet', {'diffusion_ratio': ratio, 'expected_diffusion_ratio': expected, 'mass_consistency_refs': ['s']}))
    folds = (1.0, 1.4, 1.5, 1.6, 2.0, 2.5, 2.99, 3.0, 4.0)
    credits = [mass(f, 1.0) for f in folds]
    assert _non_decreasing(credits[::-1]) and all(0.0 <= c <= 1.0 for c in credits)
    assert mass(1.5, 1.0) == 1.0 and mass(3.0, 1.0) == 0.0 and 0.99 < mass(1.505, 1.0) < 1.0
    assert mass(2.0, 1.0) == pytest.approx(0.585, abs=1e-3) and mass(1.0, 2.0) == mass(2.0, 1.0)      # a twofold mismatch (eightfold in mass): 0.58, was 0.67; symmetric


def test_a_tight_binding_analysis_keeps_full_credit_to_ten_times_the_kd_and_falls_with_the_curves_rounding_to_a_hundred():
    def over_kd(ratio, tight):
        return _judge('labelled_over_kd', 'labelled_over_kd_recorded_for_the_sheet', {'labelled_over_kd': ratio, 'tight_binding_analysis': tight, 'labelled_over_kd_refs': ['s']})
    ratios = (0.5, 1.0, 2.0, 5.0, 10.0, 10.5, 20.0, 50.0, 99.0, 100.0, 300.0)
    tight = [_credit(over_kd(r, True)) for r in ratios]
    plain = [_credit(over_kd(r, False)) for r in ratios]
    assert _non_decreasing(tight[::-1]) and _non_decreasing(plain[::-1]) and all(t >= p for t, p in zip(tight, plain))
    assert over_kd(TIGHT_BINDING_FULL_OVER_KD, True) == {'status': 'supported', 'support_refs': ['s']} and 0.95 < _credit(over_kd(10.5, True)) < 1.0
    assert _credit(over_kd(30.0, True)) == pytest.approx((30.0 ** -0.5 - 0.1) / (10.0 ** -0.5 - 0.1))     # was full credit at any ratio
    assert over_kd(TIGHT_BINDING_ZERO_OVER_KD, True)['status'] == 'conflicting' and over_kd(30.0, False)['status'] == 'conflicting'
    # without the analysis: linear in the log of the depletion bias b = 1 + r / 2, b(1) = 1.5 full, b(10) = 6 zero: ln(6 / b) / ln 4
    assert _credit(over_kd(5.0, False)) == pytest.approx(0.3888, abs=1e-3) and _credit(over_kd(3.0, False)) == pytest.approx(0.6315, abs=1e-3) and _credit(over_kd(2.0, False)) == pytest.approx(0.7925, abs=1e-3)
    assert _credit(over_kd(1.0, False)) == 1.0 and over_kd(10.0, False)['status'] == 'conflicting' and 0.99 < _credit(over_kd(1.01, False)) < 1.0


def test_the_acquisition_rises_as_the_square_root_of_the_time_to_full_credit_at_sixty_seconds():
    totals = (0.5, 5.0, 15.0, 30.0, 45.0, 59.0, 60.0, 61.0, 600.0)
    credits = [_credit(_acquisition(t)) for t in totals]
    assert _non_decreasing(credits) and all(0.0 < c <= 1.0 for c in credits)
    assert _credit(_acquisition(15.0)) == pytest.approx(0.5) and _credit(_acquisition(60.0)) == 1.0 and 'degree' not in _acquisition(60.0)
    assert 0.99 < _credit(_acquisition(59.5)) < 1.0                                # just below the researched minimum: nearly full credit, not a failure
    assert _acquisition(30.0, repeats_given=False)['status'] == 'unknown' and _credit(_acquisition(90.0, repeats_given=False)) == 1.0


def test_the_replicates_are_the_precision_of_the_mean_and_one_titration_keeps_partial_credit():
    credits = [_credit(_replicates(n)) for n in (1, 2, 3, 4, 6)]
    assert credits == [pytest.approx((1 / 3) ** 0.5), pytest.approx((2 / 3) ** 0.5), 1.0, 1.0, 1.0] and _non_decreasing(credits)
    assert _replicates(1)['status'] == 'supported' and 'degree' not in _replicates(MIN_REPLICATES)      # never conflicting (was conflicting at one)
    assert all(_replicates(n, 'unknown')['status'] == 'unknown' for n in (1, 2, 5))                    # independence not stated: unknown, never opposition


def _equilibrium(minutes, kd_nM):
    native = {'incubation_min': minutes, 'incubation_refs': ['s'], 'kd_nM': kd_nM, 'quantities': {'kd': {'source_refs': ['k']}}}
    return JUDGES[('equilibrium', 'incubation_recorded_for_the_sheet')](native)


def test_without_a_kd_the_incubation_has_no_scale_and_is_unknown_also_below_the_floor():
    for minutes in (0.1, 4.9, MIN_INCUBATION_MIN, 60.0):
        assert _equilibrium(minutes, None) == {'status': 'unknown', 'support_refs': []}


def test_a_micromolar_binder_is_judged_by_the_floor_alone_and_a_picomolar_one_by_the_association_rate():
    # KD 1 uM = 1000 nM: T_FAST = 5 ln 2 / (2 * 1e8 * 1e-6) s = 0.01733 s = 2.89e-4 min; T_SLOW (1e5) = 17.33 s = 0.2888 min; the floor 5 min decides
    t_fast = EQUILIBRATION_HALF_LIVES * 0.6931471805599453 / (2.0 * KON_MAX_PER_M_S * 1e-6) / 60.0
    t_slow = EQUILIBRATION_HALF_LIVES * 0.6931471805599453 / (2.0 * KON_SLOW_PER_M_S * 1e-6) / 60.0
    assert t_fast == pytest.approx(2.888e-4, rel=1e-3) and t_slow == pytest.approx(0.2888, rel=1e-3)
    assert _equilibrium(1.0, 1000.0) == {'status': 'supported', 'support_refs': ['s', 'k'], 'degree': pytest.approx(0.2)}      # d_kon 1, d_floor 1 / 5
    assert _credit(_equilibrium(2.5, 1000.0)) == pytest.approx(0.5) and _equilibrium(MIN_INCUBATION_MIN, 1000.0) == {'status': 'supported', 'support_refs': ['s', 'k']}
    assert _equilibrium(2.0e-4, 1000.0) == {'status': 'conflicting', 'support_refs': ['s', 'k']}       # at or below T_FAST: even the fastest association has not equilibrated
    # KD 10 pM = 0.01 nM: T_FAST = 28.88 min, T_SLOW = 1000 x that = 28 881 min (20 days); the curve is on the log scale between them
    t_fast = EQUILIBRATION_HALF_LIVES * 0.6931471805599453 / (2.0 * KON_MAX_PER_M_S * 1e-11) / 60.0
    assert t_fast == pytest.approx(28.88, abs=0.01)
    assert _equilibrium(20.0, 0.01) == {'status': 'conflicting', 'support_refs': ['s', 'k']}           # the incubation and the KD it is judged against
    assert _equilibrium(t_fast, 0.01)['status'] == 'conflicting'
    assert _credit(_equilibrium(60.0, 0.01)) == pytest.approx(0.1059, abs=1e-3) and _credit(_equilibrium(300.0, 0.01)) == pytest.approx(0.3391, abs=1e-3)      # ln(60 / 28.88) / ln 1000, ln(300 / 28.88) / ln 1000
    assert _credit(_equilibrium(t_fast * 1000.0, 0.01)) == 1.0 and _credit(_equilibrium(1.0e6, 0.01)) == 1.0
    assert _credit(_equilibrium(t_fast * 1.0001, 0.01)) < 1e-4                  # no step at the conflict end: the degree rises from 0
    # monotone: a tighter KD never makes a given incubation look better, a longer incubation never worse
    credits = [_credit(_equilibrium(20.0, kd)) for kd in (0.001, 0.01, 0.1, 1.0, 100.0)]
    # 20 min: KD 0.1 nM T_FAST 2.888 min, ln(20 / 2.888) / ln 1000 = 0.280; KD 1 nM T_FAST 0.2888 min, 0.613; KD 100 nM: full
    assert credits == [0.0, 0.0, pytest.approx(0.280, abs=1e-3), pytest.approx(0.613, abs=1e-3), 1.0] and _non_decreasing(credits)
    minutes = (6.0, 28.0, 29.0, 100.0, 1000.0, 3.0e4)
    assert _non_decreasing([_credit(_equilibrium(m, 0.01)) for m in minutes])
