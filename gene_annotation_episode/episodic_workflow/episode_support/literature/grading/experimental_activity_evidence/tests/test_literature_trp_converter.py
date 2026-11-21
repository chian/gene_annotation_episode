"""Trp converter: grader result -> the ligand_binding sheet's quantities, criteria and cells."""
import ast
import inspect
import math
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_record import fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_trp_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import weight_unknown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import (
    ABSORBANCE_ZERO_AGREEMENT, ARTEFACT_FULL_OVER_CHANGE, ARTEFACT_ZERO_OVER_CHANGE, CRITERIA_MAP, DILUTION_ZERO_AGREEMENT_PERCENT, EQUILIBRATION_HALF_LIVES, FAST_KON_PER_M_PER_S,
    FIT_PARAMETERS, FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR, HILL_FIT_PARAMETERS,
    INCUBATION_ZERO_AGREEMENT_MIN, SLOW_KON_PER_M_PER_S, JUDGES, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, MAX_UNCORRECTED_ABSORBANCE, MAX_UNCORRECTED_DILUTION_PERCENT, MIN_CONCENTRATIONS, MIN_FLUORESCENCE_CHANGE_PERCENT,
    MIN_INCUBATION_MIN, MIN_REPLICATES, NULL_REASONS, PROTEIN_MAX_OVER_KD, PROTEIN_ZERO_AGREEMENT_OVER_KD, TRP_EXCITATION_SHARE_AT_280, TRP_SELECTIVE_EXCITATION_MIN_NM, TYROSINE_EXCITATION_NM,
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
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    # two independent titrations are supported with partial credit, so the sd becomes a variance: 36 / 2 = 18 (the sampling basis carries the lower degree)
    assert convert_trp(grade_trp(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(18.0)
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
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


def test_a_tyrosine_exciting_wavelength_lowers_the_parameter_definition_to_the_tryptophan_share_and_never_conflicts():
    r = synthetic_record()
    r['quantities']['excitation_wavelength'] = point(280.0, 'nm', 'e', ['s'])
    interpretation = convert_trp(grade_trp(r))['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(TRP_EXCITATION_SHARE_AT_280)
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
    assert (MIN_FLUORESCENCE_CHANGE_PERCENT, FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT, TRP_SELECTIVE_EXCITATION_MIN_NM, TYROSINE_EXCITATION_NM, MAX_UNCORRECTED_ABSORBANCE, ABSORBANCE_ZERO_AGREEMENT) == (5.0, 1.0, 295.0, 280.0, 0.05, 0.3)
    assert (MAX_UNCORRECTED_DILUTION_PERCENT, DILUTION_ZERO_AGREEMENT_PERCENT, MIN_CONCENTRATIONS, FIT_PARAMETERS, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR) == (5.0, 50.0, 8, 2, 0.2, 1.0, 10.0, 1.0)
    assert (PROTEIN_MAX_OVER_KD, PROTEIN_ZERO_AGREEMENT_OVER_KD, MIN_INCUBATION_MIN, INCUBATION_ZERO_AGREEMENT_MIN, MIN_REPLICATES, TRP_EXCITATION_SHARE_AT_280) == (1.0, 10.0, 2.0, 1.0, 3, 0.58)
    # range review 2026-11-21: the artefact-over-change ends (the full end is the signal standard's own noise share, 1 / 5), the Hill fit's parameters, the equilibration scale
    assert (ARTEFACT_FULL_OVER_CHANGE, ARTEFACT_ZERO_OVER_CHANGE, HILL_FIT_PARAMETERS, EQUILIBRATION_HALF_LIVES, FAST_KON_PER_M_PER_S, SLOW_KON_PER_M_PER_S) == (pytest.approx(0.2), 1.0, 3, 5.0, 1.0e8, 1.0e5)
    assert ARTEFACT_FULL_OVER_CHANGE == FLUORESCENCE_CHANGE_ZERO_AGREEMENT_PERCENT / MIN_FLUORESCENCE_CHANGE_PERCENT
    assert not hasattr(literature_trp_converter, 'WEIGHT_UNKNOWN')                           # owner rule: no unknown weight inside a degree (not even imported)


def test_every_number_a_judge_uses_is_a_named_constant():
    """The judges hold no unexplained inline number: the only literal is 1.0, the full degree (and the curve's 0 and 1 in _agreement)."""
    for judge in JUDGES.values():
        literals = {node.value for node in ast.walk(ast.parse(inspect.getsource(judge))) if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)}
        assert literals <= {1.0}, (judge.__name__, literals)
    source = inspect.getsource(literature_trp_converter)
    for name in ('TYROSINE_EXCITATION_NM', 'TRP_EXCITATION_SHARE_AT_280', 'FIT_PARAMETERS', 'HILL_FIT_PARAMETERS', 'INCUBATION_ZERO_AGREEMENT_MIN', 'MIN_CONCENTRATIONS', 'MIN_REPLICATES', 'MIN_INCUBATION_MIN',
                 'TRP_SELECTIVE_EXCITATION_MIN_NM', 'ARTEFACT_FULL_OVER_CHANGE', 'ARTEFACT_ZERO_OVER_CHANGE', 'EQUILIBRATION_HALF_LIVES', 'FAST_KON_PER_M_PER_S', 'SLOW_KON_PER_M_PER_S', 'PROTEIN_MAX_OVER_KD', 'LOW_FACTOR', 'HIGH_FACTOR'):
        assert any(line.startswith(name + ' = ') and '# EXPERT_REVIEW:' in line for line in source.splitlines()), name
    assert 'Range review' in literature_trp_converter.__doc__ and 'Grader gaps' in literature_trp_converter.__doc__     # the owner's questions are answered in the docstring


def test_the_sheet_judges_the_fluorescence_change_with_a_degree():
    r = synthetic_record()

    def change(percent):
        return lambda record: record['quantities'].update(fluorescence_change=point(percent, 'percent', 'c', ['s']))
    check_scale(r, 'signal_amplitude', ((change(40.0), 'supported', 1.0), (change(5.0), 'supported', 1.0), (change(3.0), 'supported', 0.5), (change(1.5), 'supported', 0.125),
                                        (change(1.0), 'conflicting', None), (change(0.0), 'conflicting', None)))
    assert judged(r, 'signal_amplitude')['support_refs'] == ['s']


def test_the_sheet_judges_the_excitation_wavelength_with_its_own_researched_ends_and_never_conflicts():
    r = synthetic_record()

    def excitation(nm):
        return lambda record: record['quantities'].update(excitation_wavelength=point(nm, 'nm', 'e', ['s']))
    share = TRP_EXCITATION_SHARE_AT_280
    # full agreement at or above 295 nm; below it the degree falls linearly to the tryptophan share of the 280 nm excitation, and stays there at or below 280 nm
    check_scale(r, 'excitation_selectivity', ((excitation(300.0), 'supported', 1.0), (excitation(295.0), 'supported', 1.0), (excitation(294.0), 'supported', share + (1 - share) * 14 / 15),
                                              (excitation(287.5), 'supported', share + (1 - share) * 0.5), (excitation(280.0), 'supported', share), (excitation(270.0), 'supported', share)))
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


def relative_degree(loss_percent, change_percent):
    return (loss_percent / change_percent - ARTEFACT_ZERO_OVER_CHANGE) / (ARTEFACT_FULL_OVER_CHANGE - ARTEFACT_ZERO_OVER_CHANGE)


def test_an_uncorrected_inner_filter_is_also_judged_against_the_papers_own_quenching():
    """Range review: the inner filter's loss 1 - 10^(-A / 2) over the stated quenching, in addition to the absolute ramp; conflicting when it is the whole quench."""
    r = synthetic_record()
    r['facts']['inner_filter_corrected'] = fact('no', ['s'])
    r['quantities']['ligand_absorbance'] = point(0.1, 'AU', 'a', ['a'])                      # absolute ramp: 0.8; smallest loss 10.87 percent
    loss = 100 * (1 - 10 ** -0.05)

    def change(percent, direction='quenching'):
        def setter(record):
            record['quantities']['fluorescence_change'] = point(percent, 'percent', 'c', ['c'])
            record['change_direction'] = direction
        return setter
    check_scale(r, 'inner_filter', ((change(60.0), 'supported', 0.8), (change(15.0), 'supported', relative_degree(loss, 15.0)),        # 15 percent: the loss takes 72 percent of it, 0.34
                                    (change(11.0), 'supported', relative_degree(loss, 11.0)), (change(10.0), 'conflicting', None), (change(5.0), 'conflicting', None),
                                    (change(10.0, 'enhancement'), 'supported', 0.8), (change(10.0, None), 'supported', 0.8)))      # a loss cannot make an enhancement; an unstated direction is not assumed
    change(15.0)(r)
    assert judged(r, 'inner_filter')['support_refs'][-1] == 'c'                               # the change the judgement used is cited
    r['quantities']['fluorescence_change'] = {**r['quantities']['fluorescence_change'], 'status': 'unavailable', 'value': None}
    assert sheet_status_and_degree(r, 'inner_filter') == ('supported', pytest.approx(0.8))     # no stated change: the absolute ramp alone
    # the old absolute ramp scored this case 0.8 although the inner filter alone is the whole 10 percent quench; now it is evidence against the binding
    change(10.0)(r)
    assert convert_trp(grade_trp(r))['extraction']['interpretations']['binding_controls']['status'] == 'conflicting'


def test_an_uncorrected_dilution_is_also_judged_against_the_papers_own_quenching():
    r = synthetic_record()
    r['facts']['dilution_corrected'] = fact('no', ['s'])
    r['quantities']['added_volume_fraction'] = point(10.0, 'percent', 'v', ['s'])            # absolute ramp: 40 / 45; loss 10 / 110 = 9.09 percent
    loss = 100 * 10 / 110
    for percent, direction, expected, degree in ((40.0, 'quenching', 'supported', 40 / 45), (20.0, 'quenching', 'supported', relative_degree(loss, 20.0)),
                                                 (8.0, 'quenching', 'conflicting', None), (8.0, 'enhancement', 'supported', 40 / 45)):
        r['quantities']['fluorescence_change'] = point(percent, 'percent', 'c', ['s'])
        r['change_direction'] = direction
        assert sheet_status_and_degree(r, 'dilution') == (expected, pytest.approx(degree) if degree is not None else None), (percent, direction)


@pytest.mark.parametrize('criterion, fact_name, setter, value', (
    ('inner_filter', 'inner_filter_corrected', lambda r, v: r['quantities'].update(ligand_absorbance=point(v, 'AU', 'a', ['s'])), 0.12),
    ('dilution', 'dilution_corrected', lambda r, v: r['quantities'].update(added_volume_fraction=point(v, 'percent', 'v', ['s'])), 12.0)))
def test_a_larger_stated_quenching_never_lowers_the_artefact_degree(criterion, fact_name, setter, value):
    r = synthetic_record()
    r['facts'][fact_name] = fact('no', ['s'])
    setter(r, value)
    weights = []
    for percent in (0.5, 5.0, 10.0, 11.0, 12.0, 14.0, 20.0, 40.0, 80.0):
        r['quantities']['fluorescence_change'] = point(percent, 'percent', 'c', ['s'])
        weights.append(resolution(judged(r, criterion), criterion))
    assert weights == sorted(weights) and weights[0] == 0.0, weights
    assert any(0.0 < w < weights[-1] for w in weights), weights                               # gradual between the ends: partial credit, not a step to conflicting


def test_the_sheet_judges_the_protein_over_the_kd_with_a_degree_unless_tight_binding_is_handled():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')

    def protein(nm):
        return lambda record: record['quantities'].update(protein_concentration=point(nm, 'nM', 'p', ['s']))

    def log_bias_degree(ratio):                                                               # range review: linear in log(1 + r / 2), the apparent KD's fold error
        return math.log(6.0 / (1 + ratio / 2)) / math.log(6.0 / 1.5)
    check_scale(r, 'protein_concentration', ((protein(5.0), 'supported', 1.0), (protein(20.0), 'supported', 1.0), (protein(40.0), 'supported', log_bias_degree(2.0)),
                                             (protein(110.0), 'supported', log_bias_degree(5.5)), (protein(200.0), 'conflicting', None), (protein(400.0), 'conflicting', None)))
    for nm, degree in ((40.0, 0.7925), (62.5, 0.6137), (110.0, 0.3390)):                     # r 2, 3.125 (the real TRKB case), 5.5 (was 0.89, 0.76, 0.50)
        protein(nm)(r)
        assert judged(r, 'protein_concentration')['degree'] == pytest.approx(degree, abs=1e-4), nm
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])                               # handled: the ratio no longer matters
    check_scale(r, 'protein_concentration', ((protein(400.0), 'supported', None),))
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = 'quadratic'
    check_scale(r, 'protein_concentration', ((protein(400.0), 'supported', None),))
    r['fit_model'] = '1:1'
    r['quantities']['protein_concentration'] = {**r['quantities']['protein_concentration'], 'status': 'unavailable', 'value': None}      # without a number the grader's fact decides, as before
    r['facts']['protein_at_or_below_kd'] = fact('no', ['s'])
    assert judged(r, 'protein_concentration')['status'] == 'conflicting'


def occupancy_degree(ratio, full, zero):
    occupancy = ratio / (1 + ratio)
    return min(1.0, (occupancy - zero / (1 + zero)) / (full / (1 + full) - zero / (1 + zero)))


def test_the_sheet_judges_the_count_and_the_span_of_the_concentration_series_with_a_degree():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')                                  # a hyperbola fit: the KD is the curve's midpoint

    def series(values):
        return lambda record: record['concentration_series'].update(value=values)
    spanning = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 400.0]                            # eight values, 0.2 x KD to 20 x KD
    mid = [30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    low_06, high_55 = occupancy_degree(0.6, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR), occupancy_degree(5.5, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR)
    assert (low_06, high_55) == (pytest.approx(0.375), pytest.approx(0.8462, abs=1e-4))      # range review: on the occupancy (was 0.5 and 0.5, linear in the ratio)
    check_scale(r, 'concentration_series', ((series(spanning), 'supported', 1.0), (series([12.0, *mid, 110.0]), 'supported', low_06),      # lowest 0.6 x KD; highest 5.5 x KD
                                            (series([12.0, *mid, 400.0]), 'supported', low_06), (series([4.0, *mid, 110.0]), 'supported', high_55),
                                            (series([4.0, 10.0, 20.0, 30.0, 40.0, 50.0, 55.0, 60.0]), 'supported', occupancy_degree(3.0, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR)),   # top at 3 x KD (75 percent bound): 0.61 (was 0.22)
                                            (series([20.0, *mid, 400.0]), 'conflicting', None), (series([4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0, 20.0]), 'conflicting', None),   # lowest at 1 x KD; highest at 1 x KD
                                            (series([*spanning[:6], 400.0]), 'supported', 5 / 6),          # seven values: (7 - 2) / (8 - 2), the span is full
                                            (series([4.0, 16.0, 40.0, 80.0, 400.0]), 'supported', 0.5),    # five values: (5 - 2) / (8 - 2)
                                            (series([4.0, 400.0]), 'supported', 0.0),                      # two values: the isotherm is drawn through them: no credit, never conflicting
                                            (series([400.0]), 'supported', 0.0),                           # one value: a short series (the lowest is not judged against itself), not a conflict
                                            (series([20.0]), 'conflicting', None)))                        # one value at the KD: the plateau is not reached
    series(spanning)(r)
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_trp_1']


def test_a_range_stated_without_a_list_is_judged_from_its_stated_ends_and_an_unstated_end_adds_nothing():
    r = synthetic_record()                                                                    # KD 20 nM
    r['facts']['tight_binding_considered'] = fact('unknown')                                  # the KD is the curve's midpoint
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    r['quantities']['titration_point_count'] = point(8, 'count', 'n', ['s'])
    for low, high, degree in ((4.0, 200.0, 1.0), (12.0, 110.0, occupancy_degree(0.6, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR)),
                              (None, 110.0, occupancy_degree(5.5, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR)), (None, 400.0, 1.0)):
        r['quantities']['concentration_lowest'] = unavailable('nM', 'lo', 'not_stated_in_passage') if low is None else point(low, 'nM', 'lo', ['lo'])
        r['quantities']['concentration_highest'] = point(high, 'nM', 'hi', ['hi'])
        assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(degree)), (low, high)
    r['quantities']['concentration_highest'] = point(20.0, 'nM', 'hi', ['hi'])                # the top at the KD: the plateau is not reached
    assert sheet_status_and_degree(r, 'concentration_series')[0] == 'conflicting'
    r['quantities']['concentration_highest'] = unavailable('nM', 'hi', 'not_stated_in_passage')       # only a lowest end: it alone is judged
    r['quantities']['concentration_lowest'] = point(4.0, 'nM', 'lo', ['lo'])
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', pytest.approx(1.0))


def test_the_span_is_judged_on_the_curves_midpoint_when_tight_binding_is_handled_and_a_hill_fit_needs_one_more_point():
    r = synthetic_record()                                                                    # KD 20 nM, tight binding considered
    r['quantities']['protein_concentration'] = point(60.0, 'nM', 'p', ['p'])                  # midpoint KD + 60 / 2 = 50 nM
    r['concentration_series'] = {**r['concentration_series'], 'value': [4.0, 10.0, 20.0, 40.0, 60.0, 80.0, 100.0, 200.0]}      # top 200 nM: 10 x KD but 4 x the midpoint
    verdict = judged(r, 'concentration_series')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(occupancy_degree(4.0, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR))
    assert 'p' in verdict['support_refs']                                                     # the protein concentration the midpoint used is cited
    r['facts']['tight_binding_considered'] = fact('unknown')
    r['fit_model'] = '1:1'                                                                    # not handled: the hyperbola's KD is the apparent midpoint
    assert judged(r, 'concentration_series')['degree'] == pytest.approx(1.0)
    r['concentration_series'] = {**r['concentration_series'], 'value': [4.0, 16.0, 40.0, 80.0, 400.0]}      # five values, the span is full
    assert judged(r, 'concentration_series')['degree'] == pytest.approx((5 - FIT_PARAMETERS) / (MIN_CONCENTRATIONS - FIT_PARAMETERS))
    r['fit_model'] = 'hill'                                                                   # the Hill coefficient is one more free parameter
    assert judged(r, 'concentration_series')['degree'] == pytest.approx((5 - HILL_FIT_PARAMETERS) / (MIN_CONCENTRATIONS - HILL_FIT_PARAMETERS))
    r['concentration_series'] = {**r['concentration_series'], 'value': [4.0, 40.0, 400.0]}
    assert sheet_status_and_degree(r, 'concentration_series') == ('supported', 0.0)           # three points for three parameters: no credit, never conflicting
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}      # a count without a list: the span is not known, whatever the count
    for count, expected in ((1, 'unknown'), (2, 'unknown'), (3, 'unknown'), (7, 'unknown'), (8, 'unknown'), (12, 'unknown')):
        r['quantities']['titration_point_count'] = point(count, 'count', 'n', ['s'])
        assert sheet_status_and_degree(r, 'concentration_series') == (expected, None), count
    assert judged(r, 'concentration_series')['support_refs'] == []


def test_the_incubation_is_a_curve_in_the_log_of_the_time_between_the_fast_and_the_slow_association():
    """Hand-derived: T_FAST = 5 ln2 / (1e8 x KD), T_SLOW the same at 1e5 (1000 x T_FAST); degree = min(t / 2 min, ln(t / T_FAST) / ln 1000)."""
    r = synthetic_record()                                                                    # KD 20 nM: T_FAST 1.733 s = 0.02888 min, T_SLOW 28.88 min
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert 5 * math.log(2) / (1e8 * 20e-9) / 60 == pytest.approx(0.02888, abs=1e-4)
    for minutes, expected, degree in ((0.02, 'conflicting', None), (0.5, 'supported', 0.25),                    # floor 0.25 (d_kon 0.413)
                                      (1.0, 'supported', 0.5),                                                 # floor 0.5 (d_kon 0.513)
                                      (1.5, 'supported', 0.5719),                                             # d_kon = ln(1.5 / 0.02888) / ln 1000 = 0.572, floor 0.75
                                      (2.0, 'supported', 0.6134),                                              # floor 1, d_kon 0.613
                                      (5.0, 'supported', 0.7461), (28.0, 'supported', 0.9953), (30.0, 'supported', 1.0), (60.0, 'supported', 1.0)):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        status, got = sheet_status_and_degree(r, 'equilibrium')
        assert status == expected and got == (pytest.approx(degree, abs=2e-3) if degree is not None else None), minutes
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])
    assert judged(r, 'equilibrium')['status'] == 'supported' and 'degree' not in judged(r, 'equilibrium')      # the stated fact is the grader's, whatever the time


def test_a_weak_and_a_tight_binder_meet_the_two_ends_of_the_incubation_curve():
    """KD 20 uM: T_FAST 1.7 ms, T_SLOW 1.7 s, so the floor alone limits (1 min 0.5, 2 min 1). KD 1 nM: T_FAST 0.578 min, T_SLOW 578 min (5 min 0.3125, 60 min 0.6722).
    KD 50 pM: T_FAST 11.55 min, T_SLOW 11552 min (11.5 conflicting, 60 min 0.2385, 24 h 0.6985, 200 h 1)."""
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    for kd, cases in ((('20000', 'nM'), ((0.5, 'supported', 0.25), (1.0, 'supported', 0.5), (2.0, 'supported', 1.0), (60.0, 'supported', 1.0))),
                      (('1', 'nM'), ((0.5, 'conflicting', None), (5.0, 'supported', 0.3125), (60.0, 'supported', 0.6722), (60000.0, 'supported', 1.0))),
                      (('50', 'pM'), ((2.0, 'conflicting', None), (10.0, 'conflicting', None), (11.5, 'conflicting', None), (12.0, 'supported', 0.0058), (60.0, 'supported', 0.2385),
                                      (1440.0, 'supported', 0.6985), (12000.0, 'supported', 1.0)))):
        r['quantities']['kd'] = point(float(kd[0]), kd[1], 'kd', ['k'])
        for minutes, expected, degree in cases:
            r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['i'])
            status, got = sheet_status_and_degree(r, 'equilibrium')
            assert status == expected and got == (pytest.approx(degree, abs=2e-3) if degree is not None else None), (kd, minutes)
    r['quantities']['incubation_time'] = point(60.0, 'min', 'i', ['i'])
    assert judged(r, 'equilibrium')['support_refs'] == ['i', 'k']                             # the incubation and the KD that set the scale are cited


def test_without_a_binding_constant_the_incubation_is_unknown_also_within_the_mixing():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    r['fit_model'] = 'stern_volmer'                                                            # a Stern-Volmer 'KD' is a Ksv, not a KD: it sets no scale
    for minutes in (0.5, 1.0, 5.0, 600.0):
        r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['i'])
        assert sheet_status_and_degree(r, 'equilibrium') == ('unknown', None), minutes


def test_the_sheet_judges_the_replicate_count_with_a_degree_and_its_independence():
    r = synthetic_record()
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', (2 / 3) ** 0.5), (2, 'unknown', 'unknown', None),
                                                 (1, 'yes', 'supported', (1 / 3) ** 0.5), (1, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None)):      # sqrt(n / 3); never conflicting for a stated count
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_titrations'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert sheet_status_and_degree(r, 'replicates') == (expected, pytest.approx(degree) if degree is not None else None), (count, independent)
    r['facts']['independent_titrations'] = fact('no', ['s'])
    assert judged(r, 'replicates')['status'] == 'conflicting'


SHEET_CRITERION = {member: sheet for sheet, members in CRITERIA_MAP.items() for member in members}


def resolution(verdict, criterion):
    """The row weight of a verdict (OWNER_DECISION 4): supported = its degree (1.0 without one), unknown = this assay's own unknown weight for the sheet
    criterion the member belongs to (weight_unknown, per type and criterion), conflicting = 0."""
    return {'supported': verdict.get('degree', 1.0), 'unknown': weight_unknown('trp_quenching', SHEET_CRITERION[criterion]), 'conflicting': 0.0}[verdict['status']]


SWEEPS = (
    # (criterion, setter, values from worse to better, the record change that hands the value to the sheet, a value just worse than the researched full end)
    ('excitation_selectivity', lambda r, v: r['quantities'].update(excitation_wavelength=point(v, 'nm', 'e', ['s'])), [270.0, 279.9, 280.0, 280.1, 285.0, 290.0, 294.0, 294.9, 295.0, 300.0], None, 294.9),
    ('concentration_series', lambda r, v: r['concentration_series'].update(value=[4.0 + i for i in range(v - 1)] + [400.0]), [2, 3, 4, 5, 6, 7, 8, 9, 12], None, 7),
    ('replicates', lambda r, v: r['quantities'].update(replicate_count=point(v, 'count', 'n', ['s'])), [1, 2, 3, 4, 10], None, 2),
    ('protein_concentration', lambda r, v: r['quantities'].update(protein_concentration=point(v, 'nM', 'p', ['s'])), [400.0, 200.0, 199.0, 150.0, 110.0, 62.5, 40.0, 21.0, 20.0, 5.0],
     ('tight_binding_considered', 'unknown'), 20.5),
    ('inner_filter', lambda r, v: r['quantities'].update(ligand_absorbance=point(v, 'AU', 'a', ['s'])), [0.8, 0.3, 0.29, 0.2, 0.12, 0.1, 0.06, 0.05, 0.0], ('inner_filter_corrected', 'no'), 0.051),
    ('dilution', lambda r, v: r['quantities'].update(added_volume_fraction=point(v, 'percent', 'v', ['s'])), [90.0, 50.0, 49.0, 30.0, 10.0, 5.1, 5.0, 0.0], ('dilution_corrected', 'no'), 5.1),
)


def test_the_incubation_weight_is_monotone_in_the_time():
    for kd_pm in (20000.0, 50.0):                                                             # the floor and the KD's own curve
        r = synthetic_record()
        r['facts']['equilibrium_reached'] = fact('unknown')
        r['quantities']['kd'] = point(kd_pm, 'pM', 'kd', ['s'])
        weights = []
        for minutes in (0.5, 1.0, 1.01, 1.5, 1.99, 2.0, 5.0, 11.0, 12.0, 60.0):
            r['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
            weights.append(resolution(judged(r, 'equilibrium'), 'equilibrium'))
        assert weights == sorted(weights), kd_pm                                              # a longer incubation never lowers the weight


@pytest.mark.parametrize('criterion, setter, values, fact_change, researched', SWEEPS, ids=[sweep[0] for sweep in SWEEPS])
def test_each_softened_judge_is_monotone_bounded_and_has_no_step_at_its_researched_value(criterion, setter, values, fact_change, researched):
    r = synthetic_record()
    if fact_change:
        r['facts'][fact_change[0]] = fact(fact_change[1])
    weights = []
    for value in values:
        setter(r, value)
        verdict = judged(r, criterion)
        assert 0.0 <= verdict.get('degree', 1.0) <= 1.0
        weights.append(resolution(verdict, criterion))
    assert weights == sorted(weights), (criterion, list(zip(values, weights)))              # a better value never lowers the weight
    full = weights[-1]
    setter(r, researched)
    just_below = resolution(judged(r, criterion), criterion)
    assert 0.0 < just_below < full, (criterion, just_below, full)      # partial credit just below the researched value (one count less, or just under it), not 0


def test_a_degree_of_a_member_travels_into_its_sheet_criterion_and_the_weakest_member_counts():
    r = synthetic_record()
    r['quantities']['fluorescence_change'] = point(3.0, 'percent', 'c', ['s'])                # 0.5, the only member of calibration_applicability
    r['change_direction'] = 'enhancement'                                                     # an enhancement: the artefacts get their absolute ramps only (see below for a quenching)
    r['facts']['inner_filter_corrected'] = fact('no', ['s'])
    r['quantities']['ligand_absorbance'] = point(0.175, 'AU', 'a', ['s'])                     # 0.5, in binding_controls
    r['quantities']['protein_concentration'] = point(110.0, 'nM', 'p', ['s'])                 # 5.5 x KD: log(6 / 3.75) / log(4) = 0.34 (tight binding considered: no)
    r['facts']['tight_binding_considered'] = fact('unknown')
    interpretations = convert_trp(grade_trp(r))['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['degree'] == pytest.approx(0.5)
    assert interpretations['binding_controls']['degree'] == pytest.approx(0.5) and interpretations['binding_regime']['degree'] == pytest.approx(math.log(6 / 3.75) / math.log(4))
    r['change_direction'] = 'quenching'                                                       # a 3 percent quench beside an inner-filter loss of 18 percent: the loss is the whole quench
    assert convert_trp(grade_trp(r))['extraction']['interpretations']['binding_controls']['status'] == 'conflicting'
    r['change_direction'] = 'enhancement'
    r['facts']['dilution_corrected'] = fact('no', ['s'])
    r['quantities']['added_volume_fraction'] = point(38.75, 'percent', 'v', ['s'])            # 0.25: the weakest of binding_controls' members
    assert convert_trp(grade_trp(r))['extraction']['interpretations']['binding_controls']['degree'] == pytest.approx(0.25)
    assert interpretations['sampling_basis']['degree'] == pytest.approx(1.0) and interpretations['binding_parameter_definition']['degree'] == pytest.approx(1.0)      # three titrations, 295 nm: full agreement
    assert convert_trp(grade_trp(r))['sheet']['interpretations']['calibration_applicability']['degree'] == pytest.approx(0.5)      # it travels into the sheet
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert convert_trp(grade_trp(r))['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx((2 / 3) ** 0.5)


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
