"""GCI converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_gci_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import (
    AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, CRITERIA_MAP, HIGH_FACTOR, HIGH_ZERO_FACTOR, IMMOBILIZATION_MAX_PG_MM2, IMMOBILIZATION_ZERO_PG_MM2, KINETIC_TOLERANCE, KINETIC_ZERO_TOLERANCE, LOW_FACTOR, LOW_ZERO_FACTOR,
    MIN_CONCENTRATIONS, MIN_REPLICATES, NULL_REASONS, RESPONSE_MIN_PG_MM2, RESPONSE_ZERO_PG_MM2, _criterion, convert_gci)
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
    r['quantities']['immobilization_level'] = point(5000.0, 'pg/mm2', 'l', ['s'])
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'


def judged(record, name):
    return _criterion(grade_gci(record), name)


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_FACTOR, HIGH_FACTOR, HIGH_ZERO_FACTOR, MIN_REPLICATES) == (5, 0.2, 1.0, 5.0, 1.0, 3)
    assert (IMMOBILIZATION_MAX_PG_MM2, IMMOBILIZATION_ZERO_PG_MM2, RESPONSE_MIN_PG_MM2, RESPONSE_ZERO_PG_MM2) == (2000.0, 4000.0, 1.0, 0.1)
    assert (KINETIC_TOLERANCE, KINETIC_ZERO_TOLERANCE, AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR) == (0.20, 0.8, 2.0, 10.0)


def test_the_sheet_judges_the_surface_level_and_the_response_with_a_degree():
    r = synthetic_record()                                                                     # level 500 pg/mm2, response 40 pg/mm2
    for level, response, expected, degree in ((2000.0, 1.0, 'supported', 1.0), (3000.0, 40.0, 'supported', 0.5), (500.0, 0.55, 'supported', 0.5), (3000.0, 0.55, 'supported', 0.5), (3500.0, 0.325, 'supported', 0.25),
                                              (4000.0, 40.0, 'conflicting', None), (6000.0, 40.0, 'conflicting', None), (500.0, 0.1, 'conflicting', None), (500.0, 0.0, 'conflicting', None)):
        r['quantities']['immobilization_level'] = point(level, 'pg/mm2', 'l', ['s'])
        r['quantities']['response_max'] = point(response, 'pg/mm2', 'r', ['s'])
        verdict = judged(r, 'surface_level_and_response')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (level, response)
        interpretation = convert_gci(grade_gci(r))['extraction']['interpretations']['calibration_applicability']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), (level, response)
    r = synthetic_record()
    r['quantities']['response_max'] = {**r['quantities']['response_max'], 'status': 'unavailable', 'value': None}
    assert judged(r, 'surface_level_and_response') == {'status': 'unknown', 'support_refs': []}      # the level alone cannot make it supported
    r['quantities']['immobilization_level'] = point(6000.0, 'pg/mm2', 'l', ['s'])
    assert judged(r, 'surface_level_and_response')['status'] == 'conflicting'                      # but it can make it conflicting


def test_the_sheet_judges_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                     # KD 20 nM
    for series, expected, degree in (([2.0, 4.0, 20.0, 100.0, 200.0], 'supported', 1.0), ([12.0, 20.0, 40.0, 100.0, 200.0], 'supported', 0.5), ([4.0, 6.0, 20.0, 40.0, 60.0], 'supported', 0.5),
                                     ([20.0, 40.0, 60.0, 100.0, 200.0], 'conflicting', None), ([2.0, 4.0, 6.0, 10.0, 20.0], 'conflicting', None), ([2.0, 20.0, 200.0, 600.0], 'conflicting', None)):
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
        interpretation = convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']
        assert interpretation['status'] == expected and interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), series


def test_the_sheet_judges_waverapid_on_the_highest_concentration_only():
    r = synthetic_record()
    r['facts']['repeated_pulse_kinetics_used'] = fact('yes', ['s'])
    for series, expected, degree in (([200.0], 'supported', 1.0), ([100.0], 'supported', 1.0), ([60.0], 'supported', 0.5), ([20.0], 'conflicting', None), ([2.0, 20.0, 60.0], 'supported', 0.5)):      # no count asked, no lowest asked
        r['concentration_series']['value'] = series
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
    r['facts']['repeated_pulse_kinetics_used'] = fact('no')
    r['concentration_series']['value'] = [200.0]
    assert judged(r, 'concentration_series')['status'] == 'conflicting'


def test_the_sheet_judges_the_replicate_count_without_a_degree():
    r = synthetic_record()
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_channels_or_chips'] = fact(independent, ['s'] if independent != 'unknown' else [])
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
    interpretation = convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.875)
    r['concentration_series']['value'] = [12.0, 20.0, 40.0, 100.0, 200.0]                    # lowest 0.6 x KD: degree 0.5
    assert convert_gci(grade_gci(r))['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert convert_gci(grade_gci(r))['sheet']['interpretations']['binding_regime']['degree'] == pytest.approx(0.5)
    assert 'degree' not in convert_gci(grade_gci(synthetic_record()))['extraction']['interpretations']['sampling_basis']


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
