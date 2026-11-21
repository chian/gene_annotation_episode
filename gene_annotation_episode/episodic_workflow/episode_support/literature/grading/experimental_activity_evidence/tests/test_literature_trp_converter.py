"""Trp converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import (
    ABSORBANCE_ZERO_AGREEMENT, CRITERIA_MAP, DILUTION_ZERO_AGREEMENT_PERCENT, FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MAX_UNCORRECTED_ABSORBANCE,
    MAX_UNCORRECTED_DILUTION_PERCENT, MIN_CONCENTRATIONS, MIN_FLUORESCENCE_CHANGE_PERCENT, MIN_INCUBATION_MIN, MIN_REPLICATES, NULL_REASONS, PROTEIN_MAX_OVER_KD, PROTEIN_ZERO_AGREEMENT_OVER_KD, TRP_SELECTIVE_EXCITATION_MIN_NM,
    _criterion, convert_trp)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import CRITERIA, grade_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.trp_cases import sparse_record, synthetic_record


def test_every_trp_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) <= set(CRITERIA)
    assert set(CRITERIA) - set(mapped) == set()


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_trp(grade_trp(synthetic_record()))
    cells = converted['sheet']['cells']
    assert converted['experiment_type'] == 'trp_quenching'
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['unit'] == 'nM'
    # standard error 2 nM -> variance 4 nM^2 -> precision 0.25
    assert cells['effect_variance']['value'] == pytest.approx(4.0)
    assert cells['effect_precision']['value'] == pytest.approx(0.25)
    assert converted['extraction']['quantities']['effect']['measurement_keys'] == ['trp_kd:exp_synthetic_trp_1']
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_the_same_sheet_components_as_the_other_converters_and_nulls_have_reasons():
    converted = convert_trp(grade_trp(synthetic_record()))
    cells = converted['sheet']['cells']
    for name in ('recovery_deviation', 'attributed_fraction', 'condition_response', 'assertion_prediction_error', 'alternative_prediction_error', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None and cells[name]['status'] == 'unavailable' and cells[name]['reasons']
    assert set(NULL_REASONS) <= set(converted['null_components'])


def test_dependence_keys_name_the_ligand_and_the_protein_and_have_no_surface():
    converted = convert_trp(grade_trp(synthetic_record(titrant_prep='li', fixed_prep='pr', dataset='dat')))
    assert converted['dependence'] == {'analyte_preparation_ref': 'li', 'immobilized_preparation_ref': 'pr', 'surface_ref': None, 'dataset_ref': 'dat'}


def test_standard_deviation_needs_independent_titrations_and_divides_by_n():
    r = synthetic_record(spread=6.0)
    r['spread_kind'] = 'standard_deviation'
    # sd 6 nM, 3 independent titrations: variance 36 / 3 = 12
    assert convert_trp(grade_trp(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(12.0)
    r['facts']['independent_titrations'] = fact('unknown')
    converted = convert_trp(grade_trp(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_a_confidence_interval_is_not_converted_and_an_unstated_kind_gives_no_variance():
    r = synthetic_record()
    r['spread_kind'] = 'confidence_interval'
    converted = convert_trp(grade_trp(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None and converted['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['spread_kind'] = None
    assert convert_trp(grade_trp(r))['null_components']['effect_variance'] == 'spread_kind_not_stated'


def test_a_picomolar_spread_and_kd_are_converted_to_nanomolar():
    r = synthetic_record()
    r['quantities']['kd'] = point(94.0, 'pM', 'kd', ['s'])
    r['quantities']['kd_spread'] = point(10.0, 'pM', 'sp', ['s'])
    cells = convert_trp(grade_trp(r))['sheet']['cells']
    # KD 94 pM = 0.094 nM; standard error 10 pM = 0.01 nM -> variance 1e-4 nM^2
    assert cells['measured_effect']['value'] == pytest.approx(0.094) and cells['effect_variance']['value'] == pytest.approx(1e-4)


def test_a_stern_volmer_constant_alone_is_not_a_binding_constant_and_is_never_the_effect():
    r = synthetic_record()
    r['quantities']['kd'] = {**r['quantities']['kd'], 'status': 'unavailable', 'value': None}
    converted = convert_trp(grade_trp(r))                          # the record still holds Ksv 2.0e4 M^-1
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'only_a_stern_volmer_quenching_constant_given_not_a_dissociation_constant'
    assert converted['null_components']['effect_variance'] == 'no_effect_to_carry_a_variance'
    r['quantities']['ksv'] = {**r['quantities']['ksv'], 'status': 'unavailable', 'value': None}
    assert convert_trp(grade_trp(r))['null_components']['effect'] == 'no_kd_given_as_a_point_value'


def test_a_kd_from_a_stern_volmer_fit_is_not_carried_and_its_sheet_criterion_conflicts():
    r = synthetic_record()
    r['fit_model'] = 'stern_volmer'
    converted = convert_trp(grade_trp(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None
    assert converted['null_components']['effect'] == 'the_kd_was_fitted_with_the_stern_volmer_equation_which_gives_a_quenching_constant'
    assert converted['extraction']['interpretations']['binding_parameter_definition']['status'] == 'conflicting'


def test_the_sparse_record_has_an_effect_and_no_variance_and_unknown_criteria():
    converted = convert_trp(grade_trp(sparse_record()))
    assert converted['sheet']['cells']['measured_effect']['value'] == 20.0 and converted['sheet']['cells']['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_a_tyrosine_exciting_wavelength_makes_the_parameter_definition_unknown_not_conflicting():
    r = synthetic_record()
    r['quantities']['excitation_wavelength'] = point(280.0, 'nm', 'e', ['s'])
    assert convert_trp(grade_trp(r))['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'
    r['quantities']['fluorescence_change'] = point(1.0, 'percent', 'c', ['s'])        # the sheet's calibration criterion is the signal: at the noise
    assert convert_trp(grade_trp(r))['extraction']['interpretations']['calibration_applicability']['status'] == 'conflicting'


def judged(record, name):
    return _criterion(grade_trp(record), name)


def sheet_status_and_degree(record, name):
    verdict = judged(record, name)
    return verdict['status'], verdict.get('degree')


def check_scale(record, name, cases):
    for value_setter, expected, degree in cases:
        value_setter(record)
        status, got = sheet_status_and_degree(record, name)
        assert status == expected, (name, status, expected)
        assert got == (pytest.approx(degree) if degree is not None else None), (name, got, degree)


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_FLUORESCENCE_CHANGE_PERCENT, FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT, TRP_SELECTIVE_EXCITATION_MIN_NM, MAX_UNCORRECTED_ABSORBANCE, ABSORBANCE_ZERO_AGREEMENT) == (5.0, 1.0, 295.0, 0.05, 0.3)
    assert (MAX_UNCORRECTED_DILUTION_PERCENT, DILUTION_ZERO_AGREEMENT_PERCENT, MIN_CONCENTRATIONS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (5.0, 50.0, 8, 0.2, 1.0, 10.0, 1.0)
    assert (PROTEIN_MAX_OVER_KD, PROTEIN_ZERO_AGREEMENT_OVER_KD, MIN_INCUBATION_MIN, MIN_REPLICATES) == (1.0, 10.0, 2.0, 3)


def test_the_sheet_judges_the_fluorescence_change_with_a_degree():
    r = synthetic_record()

    def change(percent):
        return lambda record: record['quantities'].update(fluorescence_change=point(percent, 'percent', 'c', ['s']))
    check_scale(r, 'signal_amplitude', ((change(40.0), 'supported', 1.0), (change(5.0), 'supported', 1.0), (change(3.0), 'supported', 0.5), (change(1.5), 'supported', 0.125),
                                        (change(1.0), 'conflicting', None), (change(0.0), 'conflicting', None)))
    assert judged(r, 'signal_amplitude')['support_refs'] == ['s']


def test_the_sheet_judges_the_excitation_wavelength_without_a_degree_and_never_as_a_conflict():
    r = synthetic_record()

    def excitation(nm):
        return lambda record: record['quantities'].update(excitation_wavelength=point(nm, 'nm', 'e', ['s']))
    check_scale(r, 'excitation_selectivity', ((excitation(295.0), 'supported', None), (excitation(300.0), 'supported', None), (excitation(294.0), 'unknown', None), (excitation(280.0), 'unknown', None)))
    excitation(295.0)(r)
    assert judged(r, 'excitation_selectivity')['support_refs'] == ['s']


def test_the_sheet_judges_the_ligand_absorbance_with_a_degree_only_when_no_correction_is_stated():
    r = synthetic_record()
    r['facts']['inner_filter_corrected'] = fact('no', ['s'])

    def absorbance(au):
        return lambda record: record['quantities'].update(ligand_absorbance=point(au, 'AU', 'a', ['s']))
    check_scale(r, 'inner_filter', ((absorbance(0.0), 'supported', 1.0), (absorbance(0.05), 'supported', 1.0), (absorbance(0.175), 'supported', 0.5), (absorbance(0.3), 'conflicting', None), (absorbance(0.8), 'conflicting', None)))
    r['facts']['inner_filter_corrected'] = fact('yes', ['s'])                                 # a stated correction is the grader's: supported, no degree, whatever the absorbance
    assert sheet_status_and_degree(r, 'inner_filter') == ('supported', None)


def test_the_sheet_judges_the_added_volume_with_a_degree_only_when_no_correction_is_stated():
    r = synthetic_record()
    r['facts']['dilution_corrected'] = fact('no', ['s'])

    def added(percent):
        return lambda record: record['quantities'].update(added_volume_fraction=point(percent, 'percent', 'v', ['s']))
    check_scale(r, 'dilution', ((added(0.0), 'supported', 1.0), (added(5.0), 'supported', 1.0), (added(27.5), 'supported', 0.5), (added(50.0), 'conflicting', None), (added(90.0), 'conflicting', None)))
    r['facts']['dilution_corrected'] = fact('yes', ['s'])
    assert sheet_status_and_degree(r, 'dilution') == ('supported', None)


def test_the_sheet_judges_the_protein_over_the_kd_with_a_degree_unless_tight_binding_is_handled():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')

    def protein(nm):
        return lambda record: record['quantities'].update(protein_concentration=point(nm, 'nM', 'p', ['s']))
    check_scale(r, 'protein_concentration', ((protein(5.0), 'supported', 1.0), (protein(20.0), 'supported', 1.0), (protein(110.0), 'supported', 0.5), (protein(200.0), 'conflicting', None), (protein(400.0), 'conflicting', None)))
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])                               # handled: the ratio no longer matters
    check_scale(r, 'protein_concentration', ((protein(400.0), 'supported', None),))
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = 'quadratic'
    check_scale(r, 'protein_concentration', ((protein(400.0), 'supported', None),))
    r['fit_model'] = '1:1'
    r['quantities']['protein_concentration'] = {**r['quantities']['protein_concentration'], 'status': 'unavailable', 'value': None}      # without a number the grader's fact decides, as before
    r['facts']['protein_at_or_below_kd'] = fact('no', ['s'])
    assert judged(r, 'protein_concentration')['status'] == 'conflicting'


def test_the_sheet_judges_the_count_and_the_span_of_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM

    def series(values):
        return lambda record: record['concentration_series'].update(value=values)
    spanning = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 400.0]                            # eight values, 0.2 x KD to 20 x KD
    mid = [30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    check_scale(r, 'concentration_series', ((series(spanning), 'supported', 1.0), (series([12.0, *mid, 110.0]), 'supported', 0.5),      # lowest 0.6 x KD: 0.5; highest 5.5 x KD: 0.5
                                            (series([12.0, *mid, 400.0]), 'supported', 0.5), (series([4.0, *mid, 110.0]), 'supported', 0.5),
                                            (series([20.0, *mid, 400.0]), 'conflicting', None), (series([4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0, 20.0]), 'conflicting', None),   # lowest at 1 x KD; highest at 1 x KD
                                            (series(spanning[:7]), 'conflicting', None)))                                                                                      # seven values: fewer than MIN_CONCENTRATIONS
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_trp_1']
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}      # a count without a list: below the minimum conflicts, otherwise the span is not known
    for count, expected in ((7, 'conflicting'), (8, 'unknown'), (12, 'unknown')):
        r['quantities']['titration_point_count'] = point(count, 'count', 'n', ['s'])
        assert sheet_status_and_degree(r, 'concentration_series') == (expected, None), count
    assert judged(r, 'concentration_series')['support_refs'] == []


def test_the_sheet_judges_the_incubation_without_a_degree():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, expected in ((2.0, 'unknown'), (1.9, 'conflicting'), (0.5, 'conflicting'), (60.0, 'unknown')):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert sheet_status_and_degree(r, 'equilibrium') == (expected, None), minutes
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported'                                  # the stated fact is the grader's, whatever the time


def test_the_sheet_judges_the_replicate_count_and_its_independence_without_a_degree():
    r = synthetic_record()
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert sheet_status_and_degree(r, 'replicates') == (expected, None), (count, independent)
    r['facts']['independent_titrations'] = fact('no', ['s'])
    assert judged(r, 'replicates')['status'] == 'conflicting'


def test_a_degree_of_a_member_travels_into_its_sheet_criterion_and_the_weakest_member_counts():
    r = synthetic_record()
    r['quantities']['fluorescence_change'] = point(3.0, 'percent', 'c', ['s'])                # 0.5, the only member of calibration_applicability
    r['facts']['inner_filter_corrected'] = fact('no', ['s'])
    r['quantities']['ligand_absorbance'] = point(0.175, 'AU', 'a', ['s'])                     # 0.5, in binding_controls
    r['quantities']['protein_concentration'] = point(110.0, 'nM', 'p', ['s'])                 # 5.5 x KD: 0.5 (tight binding considered: no)
    r['facts']['tight_binding_considered'] = fact('unknown')
    interpretations = convert_trp(grade_trp(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['degree'] == pytest.approx(0.5)
    assert interpretations['binding_controls']['degree'] == pytest.approx(0.5) and interpretations['binding_regime']['degree'] == pytest.approx(0.5)
    r['facts']['dilution_corrected'] = fact('no', ['s'])
    r['quantities']['added_volume_fraction'] = point(38.75, 'percent', 'v', ['s'])            # 0.25: the weakest of binding_controls' members
    assert convert_trp(grade_trp(r))['extraction']['interpretations']['binding_controls']['degree'] == pytest.approx(0.25)
    assert interpretations['sampling_basis'].get('degree') is None and interpretations['binding_parameter_definition'].get('degree') is None
    assert convert_trp(grade_trp(r))['sheet']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)      # it travels into the sheet


def interpretation(record, name):
    return convert_trp(grade_trp(record))['extraction']['interpretations'][name]


def test_support_implied_or_about_something_else_gives_the_support_degree_and_direct_leaves_it():
    r = synthetic_record()
    assert interpretation(r, 'binding_controls').get('degree', 1.0) == 1.0 and interpretation(r, 'binding_regime').get('degree', 1.0) == 1.0      # all direct: unchanged
    r['facts']['buffer_blank_subtracted'] = fact('yes', ['s'], 'implied')
    assert interpretation(r, 'binding_controls')['degree'] == pytest.approx(0.7)
    r['facts']['ligand_only_control_measured'] = fact('yes', ['s'], 'about_something_else')      # the weakest member field counts
    assert interpretation(r, 'binding_controls')['degree'] == pytest.approx(0.3)
    r['facts']['signal_saturates'] = fact('yes', ['s'], 'about_something_else')
    assert interpretation(r, 'binding_regime')['degree'] == pytest.approx(0.3)


def test_the_support_degree_multiplies_a_degree_the_criterion_already_has():
    r = synthetic_record()
    r['quantities']['fluorescence_change'] = point(3.0, 'percent', 'c', ['s'], support='implied')        # degree 0.5
    assert interpretation(r, 'calibration_applicability')['degree'] == pytest.approx(0.5 * 0.7)


def test_support_never_changes_a_status_and_a_conflicting_or_unknown_criterion_keeps_no_degree():
    r = synthetic_record()
    r['facts']['buffer_blank_subtracted'] = fact('no', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_controls')
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    r = synthetic_record()
    r['facts']['buffer_blank_subtracted'] = fact('unknown')
    r['facts']['ligand_only_control_measured'] = fact('yes', ['s'], 'about_something_else')
    verdict = interpretation(r, 'binding_controls')
    assert verdict['status'] == 'unknown' and 'degree' not in verdict
