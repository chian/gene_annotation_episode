"""DSF converter: grader result -> the ligand_binding sheet's quantities, criteria and cells.

The judgements follow the owner rule (A105_EXPERIMENT_SOP step 3): every researched DSF value is kept as a named EXPERT_REVIEW constant; a lone
minimum (MIN_CONCENTRATIONS, MIN_CONCENTRATIONS_FOR_KD, MIN_REPLICATES) is where full credit is reached, with partial credit below it, no step and
never a conflict from the count (replicates: sqrt(n / MIN); a short series: low partial credit); the full-agreement to zero-agreement ramps are kept
(the concentration range linear in the occupancy, symmetric about the KD); a positive shift inside the typical noise is no credit, never opposition;
a better value never lowers the degree; a value not stated is unknown, never 0. Records are built from the synthetic DSF passage through the
extraction's own validator and record builder."""
import ast
import inspect
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dsf_extraction import UNITS, field_names, record_from_answer, validate_answer
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import dsf_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_dsf_converter, literature_dsf_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_converter import (
    CRITERIA_MAP, HEATING_RATE_FULL_AGREEMENT, HEATING_RATE_ZERO_AGREEMENT, HIGH_OVER_KD_FULL_AGREEMENT, HIGH_OVER_KD_ZERO_AGREEMENT, BETWEEN_EXPERIMENT_TM_SD_C, JUDGES, KD_OVER_PROTEIN_FULL_AGREEMENT, SHIFT_REFERENCE_OVER_KD, LOW_OVER_KD_FULL_AGREEMENT,
    LOW_OVER_KD_ZERO_AGREEMENT, MIN_CONCENTRATIONS, MIN_CONCENTRATIONS_FOR_KD, MIN_REPLICATES, SD_MIN_EXPERIMENTS, SHIFT_FULL_AGREEMENT_C, SHIFT_OVER_SPREAD_FULL_AGREEMENT,
    SHIFT_OVER_SPREAD_ZERO_AGREEMENT, SHIFT_ZERO_AGREEMENT_C, _criterion, _variance, convert_dsf)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_grader import CRITERIA, grade_dsf

SHIFT = ('shift_size', 'thermal_shift_recorded_for_the_sheet')
SPREAD = ('shift_over_spread', 'shift_over_spread_recorded_for_the_sheet')
SERIES = ('concentration_series', 'concentration_count_recorded_for_the_sheet')
RANGE = ('concentration_range', 'concentration_range_recorded_for_the_sheet')
HEATING = ('heating_rate', 'heating_rate_recorded_for_the_sheet')
REPLICATES = ('replicates', 'replicate_count_recorded_for_the_sheet')


def answer(stated, support=None):
    """The extraction answer stating ``stated`` (field -> (value, unit, quote)) of the synthetic passage, every other field unavailable."""
    support = support or {}
    items = {}
    for name in field_names():
        if name in stated:
            value, unit, quote = stated[name]
            item = {'status': 'stated', 'value': value, 'quote': quote, 'support': support.get(name, 'direct'), 'reason': None}
        else:
            unit = None
            item = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None, 'reason': 'not_stated_in_passage'}
        if name in UNITS:
            item['unit'] = unit
        items[name] = item
    return validate_answer(items, dsf_passages.SYNTHETIC)


def record(stated=None, support=None):
    """The record of the synthetic passage stating ``stated`` (default: every field)."""
    return record_from_answer(answer(dsf_passages.SYNTHETIC_STATED if stated is None else stated, support), dsf_passages.SYNTHETIC, 0, 'experiment:dsf', 'source:dsf', 'assertion:dsf')


def without(*names):
    return {name: value for name, value in dsf_passages.SYNTHETIC_STATED.items() if name not in names}


def native():
    return grade_dsf(record())['native']


def judge(key, **changes):
    return JUDGES[key]({**native(), **changes})


def test_every_dsf_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) == set(CRITERIA)


def test_the_full_synthetic_record_supports_every_criterion():
    graded = grade_dsf(record())
    for name in CRITERIA:
        assert _criterion(graded, name)['status'] == 'supported', name
    # eight concentrations for a KD and three independent experiments reach the researched minimums: full credit
    assert _criterion(graded, 'concentration_series')['degree'] == 1.0 and _criterion(graded, 'replicates')['degree'] == 1.0
    interpretations = convert_dsf(graded)['extraction']['interpretations']
    assert {c['status'] for c in interpretations.values()} == {'supported'}


def test_the_researched_values_are_kept():
    assert (MIN_CONCENTRATIONS, MIN_REPLICATES, SHIFT_FULL_AGREEMENT_C, SHIFT_ZERO_AGREEMENT_C, SHIFT_OVER_SPREAD_FULL_AGREEMENT, SHIFT_OVER_SPREAD_ZERO_AGREEMENT) == (3, 3, 2.0, 0.5, 3.0, 1.0)
    assert (LOW_OVER_KD_FULL_AGREEMENT, LOW_OVER_KD_ZERO_AGREEMENT, HIGH_OVER_KD_FULL_AGREEMENT, HIGH_OVER_KD_ZERO_AGREEMENT, HEATING_RATE_FULL_AGREEMENT, HEATING_RATE_ZERO_AGREEMENT) == (0.2, 1.0, 5.0, 1.0, 2.0, 10.0)
    assert (MIN_CONCENTRATIONS_FOR_KD, SD_MIN_EXPERIMENTS) == (5, 2)
    assert not hasattr(literature_dsf_converter, 'CONCENTRATIONS_ZERO') and not hasattr(literature_dsf_converter, 'REPLICATES_ZERO')


def test_a_short_series_without_a_kd_is_proportional_partial_credit_never_conflicting():
    assert judge(SERIES, kd_nM=None, concentration_count=MIN_CONCENTRATIONS)['degree'] == 1.0
    for count in (1, 2):
        verdict = judge(SERIES, kd_nM=None, concentration_count=count)
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(count / MIN_CONCENTRATIONS)      # 1 -> 0.33, 2 -> 0.67


def test_a_kd_needs_more_concentrations_and_loses_credit_faster_below_them():
    assert judge(SERIES, concentration_count=MIN_CONCENTRATIONS_FOR_KD)['degree'] == 1.0
    three = judge(SERIES, concentration_count=3)
    assert three['status'] == 'supported' and three['degree'] == pytest.approx((3 / MIN_CONCENTRATIONS_FOR_KD) ** 2)      # 3 points cannot test a three-parameter fit
    assert judge(SERIES, concentration_count=1)['status'] == 'supported'      # still low partial credit, never conflicting
    for count in (1, 2, 3, 4):      # the same count gives less credit when a KD rests on it than when only a dose dependence does
        assert judge(SERIES, concentration_count=count)['degree'] < judge(SERIES, kd_nM=None, concentration_count=count)['degree']


def test_replicates_are_the_precision_of_the_mean_never_conflicting():
    assert judge(REPLICATES, replicate_count=MIN_REPLICATES)['degree'] == 1.0
    for count in (1, 2):
        verdict = judge(REPLICATES, replicate_count=count)
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(math.sqrt(count / MIN_REPLICATES))      # 1 -> 0.58, 2 -> 0.82


@pytest.mark.parametrize('key, name, changes', [(SERIES, 'concentration_count', {}), (SERIES, 'concentration_count', {'kd_nM': None}), (REPLICATES, 'replicate_count', {})])
def test_more_concentrations_or_experiments_never_lower_the_degree(key, name, changes):
    degrees = [judge(key, **changes, **{name: n})['degree'] for n in range(1, 12)]
    assert degrees == sorted(degrees) and all(0 < d <= 1 for d in degrees)
    assert degrees[0] < 1 and degrees[-1] == 1.0


@pytest.mark.parametrize('key, name, full, worse, changes', [
    (SHIFT, 'thermal_shift_c', SHIFT_FULL_AGREEMENT_C, -0.1, {}), (SPREAD, 'shift_over_spread', SHIFT_OVER_SPREAD_FULL_AGREEMENT, -0.1, {}),
    (RANGE, 'low_over_kd', LOW_OVER_KD_FULL_AGREEMENT, 0.05, {}), (RANGE, 'high_over_kd', HIGH_OVER_KD_FULL_AGREEMENT, -0.1, {}),
    (HEATING, 'heating_rate_c_per_min', HEATING_RATE_FULL_AGREEMENT, 0.5, {}), (SERIES, 'concentration_count', MIN_CONCENTRATIONS, -1, {'kd_nM': None}),
    (SERIES, 'concentration_count', MIN_CONCENTRATIONS_FOR_KD, -1, {}), (REPLICATES, 'replicate_count', MIN_REPLICATES, -1, {})])
def test_no_step_at_any_researched_value(key, name, full, worse, changes):
    assert judge(key, **changes, **{name: full})['degree'] == 1.0
    just_worse = judge(key, **changes, **{name: full + worse})
    assert just_worse['status'] == 'supported' and 0 < just_worse['degree'] < 1


def test_the_kept_ramps_are_monotone_and_bounded():
    for key, name, values in ((SHIFT, 'thermal_shift_c', [0.1, 0.5, 0.6, 1.0, 1.5, 2.0, 5.0]), (SPREAD, 'shift_over_spread', [1.1, 2.0, 3.0, 9.0]), (RANGE, 'low_over_kd', [0.9, 0.5, 0.2, 0.01]),
                              (RANGE, 'high_over_kd', [1.1, 2.0, 3.0, 5.0, 50.0]), (HEATING, 'heating_rate_c_per_min', [9.0, 5.0, 2.0, 0.5])):
        degrees = [judge(key, **{name: v})['degree'] for v in values]
        assert degrees == sorted(degrees) and all(0 <= d <= 1 for d in degrees), name


def test_a_shift_inside_the_typical_noise_is_no_credit_but_not_opposition():
    for shift in (0.1, SHIFT_ZERO_AGREEMENT_C):
        assert judge(SHIFT, thermal_shift_c=shift) == {'status': 'supported', 'support_refs': [*native()['thermal_shift_refs'], *native()['shift_concentration_refs']], 'degree': 0.0}
    assert judge(SHIFT, thermal_shift_c=1.25)['degree'] == pytest.approx(0.5)      # linear between the noise end and the clear stabilisation
    # what the paper itself shows against the standard stays conflicting: no rise of the Tm, a fall, or a shift no larger than its own scatter
    for shift in (0.0, -1.0):
        assert judge(SHIFT, thermal_shift_c=shift)['status'] == 'conflicting'
    for ratio in (SHIFT_OVER_SPREAD_ZERO_AGREEMENT, 0.5, -2.0):
        assert judge(SPREAD, shift_over_spread=ratio)['status'] == 'conflicting'


def test_the_range_is_symmetric_in_fold_distance_from_the_kd():
    # 0.2x and 5x are the same fold distance from the KD; so are 0.5x and 2x: the same credit on either side (linear in the occupancy x / (1 + x))
    low, high = judge(RANGE, low_over_kd=0.5, high_over_kd=50.0)['degree'], judge(RANGE, low_over_kd=0.01, high_over_kd=2.0)['degree']
    assert low == pytest.approx(high) == pytest.approx(0.5)
    # a KD the series does not reach past on one side is conflicting (the paper's own numbers show an extrapolated KD)
    assert judge(RANGE, low_over_kd=LOW_OVER_KD_ZERO_AGREEMENT)['status'] == 'conflicting' and judge(RANGE, high_over_kd=HIGH_OVER_KD_ZERO_AGREEMENT)['status'] == 'conflicting'


def test_values_not_stated_are_unknown_not_0():
    graded = grade_dsf(record(without('ligand_concentration_count', 'ligand_titration_measured', 'replicate_count', 'heating_rate', 'tm_spread')))
    for name in ('concentration_series', 'replicates', 'heating_rate', 'shift_over_spread'):
        assert _criterion(graded, name) == {'status': 'unknown', 'support_refs': []}, name
    interpretations = convert_dsf(graded)['extraction']['interpretations']
    assert interpretations['sampling_basis']['status'] == 'unknown' and 'degree' not in interpretations['sampling_basis']


def test_replicates_not_stated_independent_are_unknown_at_any_count():
    graded = grade_dsf(record(without('independent_experiments')))
    for count in (1, MIN_REPLICATES - 1, MIN_REPLICATES):
        assert JUDGES[REPLICATES]({**graded['native'], 'replicate_count': count}) == {'status': 'unknown', 'support_refs': []}


def test_a_standard_deviation_of_one_experiment_is_not_made_a_variance():
    graded = grade_dsf(record())
    graded['native']['spread_kind'] = 'standard_deviation'
    graded['native']['quantities']['replicate_count']['value'] = 1
    graded['native']['replicate_count'] = 1
    assert _criterion(graded, 'replicates')['status'] == 'supported'      # one experiment is low credit, not a conflict
    assert _variance(graded) == (None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', [])
    graded['native']['quantities']['replicate_count']['value'] = graded['native']['replicate_count'] = SD_MIN_EXPERIMENTS
    assert _variance(graded)[0] == pytest.approx(1500.0 ** 2 / SD_MIN_EXPERIMENTS)


def test_support_lowers_the_degree_and_never_changes_a_status():
    direct = convert_dsf(grade_dsf(record()))['extraction']['interpretations']
    implied = convert_dsf(grade_dsf(record(support={'ligand_concentration_count': 'implied', 'replicate_count': 'about_something_else'})))['extraction']['interpretations']
    assert {n: c['status'] for n, c in direct.items()} == {n: c['status'] for n, c in implied.items()}
    assert implied['binding_regime']['degree'] < direct['binding_regime']['degree']
    assert implied['sampling_basis']['degree'] < direct['sampling_basis']['degree']


def test_a_record_with_no_kd_carries_the_detected_statement_and_no_effect():
    converted = convert_dsf(grade_dsf(record(without('kd', 'kd_spread'))))
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_thermal_shift_observed'], 'thermal_shift_c': 4.8}
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['extraction']['quantities']['effect'] is None
    assert converted['direction_field_support'] == 'direct'


def test_a_record_with_a_kd_fills_the_effect_and_its_variance():
    converted = convert_dsf(grade_dsf(record()))
    assert converted['extraction']['quantities']['effect']['value'] == 12000.0
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(1500.0 ** 2)      # standard error -> se^2
    assert converted['direction_field_support'] == 'direct' and 'qualitative_effect' not in converted


@pytest.mark.parametrize('module', [literature_dsf_converter, literature_dsf_grader])
def test_no_unnamed_number_in_a_judgement(module):
    tree = ast.parse(inspect.getsource(module))
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    numbers = {node.value for function in functions for node in ast.walk(function) if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)}
    assert numbers <= {0, 1}


SINGLE = ('concentration_series', 'single_concentration_recorded_for_the_sheet')


def test_a_stated_no_titration_is_a_single_concentration_screen_low_credit_never_conflicting():
    graded = grade_dsf(record({**without('ligand_concentration_count', 'kd', 'kd_spread'), 'ligand_titration_measured': ('no', None, 'as a ligand titration')}))
    assert graded['reasons']['concentration_series'] == SINGLE[1] and graded['criteria']['concentration_series']['status'] == 'unknown'
    verdict = _criterion(graded, 'concentration_series')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(1 / MIN_CONCENTRATIONS)
    assert _criterion(graded, 'concentration_series')['support_refs'] == ['span_ligand_titration_measured']


def test_the_shift_read_below_saturation_needs_less_to_count_as_clear_and_never_more():
    shift = 1.0
    degrees = [judge(SHIFT, thermal_shift_c=shift, shift_concentration_over_kd=x)['degree'] for x in (0.05, 0.2, 1.0, 3.0, SHIFT_REFERENCE_OVER_KD, 50.0)]
    assert degrees == sorted(degrees, reverse=True) and degrees[0] == 1.0      # a higher occupancy for the same shift is less than expected
    assert degrees[-1] == degrees[-2] == pytest.approx((shift - SHIFT_ZERO_AGREEMENT_C) / (SHIFT_FULL_AGREEMENT_C - SHIFT_ZERO_AGREEMENT_C))      # at saturation the absolute ramp
    assert judge(SHIFT, thermal_shift_c=shift, shift_concentration_over_kd=None)['degree'] == degrees[-1]      # no concentration or no KD: absolute, as before
    assert judge(SHIFT, thermal_shift_c=SHIFT_ZERO_AGREEMENT_C, shift_concentration_over_kd=0.1)['degree'] == 0.0      # the noise end is absolute
    assert judge(SHIFT, thermal_shift_c=-0.5, shift_concentration_over_kd=0.1)['status'] == 'conflicting'


def test_the_grader_records_the_concentration_of_the_shift_over_the_kd():
    graded_native = native()
    assert graded_native['shift_concentration_over_kd'] == pytest.approx(200 / 12)
    assert set(graded_native['shift_concentration_refs']) == {'span_shift_ligand_concentration', 'span_kd'}
    assert grade_dsf(record(without('shift_ligand_concentration')))['native']['shift_concentration_over_kd'] is None


def test_a_kd_below_the_protein_concentration_is_titration_limited_proportional_partial_credit():
    assert native()['kd_over_protein'] == pytest.approx(12 / 5)      # 12 uM KD, 5 uM protein
    assert judge(RANGE, kd_over_protein=KD_OVER_PROTEIN_FULL_AGREEMENT)['degree'] == judge(RANGE, kd_over_protein=None)['degree']
    half = judge(RANGE, kd_over_protein=0.5)
    assert half['status'] == 'supported' and half['degree'] == pytest.approx(0.5 * KD_OVER_PROTEIN_FULL_AGREEMENT)
    degrees = [judge(RANGE, kd_over_protein=r)['degree'] for r in (0.01, 0.1, 0.5, 1.0, 5.0)]
    assert degrees == sorted(degrees) and all(0 < d <= 1 for d in degrees)
    assert grade_dsf(record(without('protein_concentration')))['native']['kd_over_protein'] is None


def test_a_standard_deviation_over_wells_gets_the_between_experiment_scatter_added():
    stated = judge(SPREAD, tm_spread_independent='yes')
    unknown = judge(SPREAD, tm_spread_independent='unknown')
    wells = judge(SPREAD, tm_spread_independent='no')
    assert stated == unknown and wells['degree'] <= stated['degree']      # wells-only scatter overstates the ratio: never more credit
    ratio = 4.8 / math.hypot(0.3, BETWEEN_EXPERIMENT_TM_SD_C)
    assert wells['degree'] == pytest.approx(min(1.0, (ratio - SHIFT_OVER_SPREAD_ZERO_AGREEMENT) / (SHIFT_OVER_SPREAD_FULL_AGREEMENT - SHIFT_OVER_SPREAD_ZERO_AGREEMENT)))
    assert judge(SPREAD, tm_spread_independent='no', thermal_shift_c=0.5, tm_spread_c=0.3)['status'] == 'conflicting'      # 0.5 over sqrt(0.3^2 + 0.5^2) is 0.86, no larger than the scatter
