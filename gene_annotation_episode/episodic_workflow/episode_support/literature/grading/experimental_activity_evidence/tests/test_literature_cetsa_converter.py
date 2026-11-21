"""CETSA converter: grader result -> the ligand_binding sheet's quantities, criteria and cells.

The judgements follow the owner rule of A105_EXPERIMENT_SOP.md step 3 and the range review in the converter's docstring: the researched
CETSA values are kept as named EXPERT_REVIEW constants; the thermal-shift ramp is linear between its researched ends, with a positive
shift inside the reproducibility of the Tm at degree 0 (not conflicting) and only no shift or a fall conflicting; the concentration
range is linear in the occupancy x / (1 + x) (symmetric in fold distance from the EC50); the lone count minimums (MIN_TEMPERATURES,
MIN_CONCENTRATIONS for a dose dependence, MIN_CONCENTRATIONS_FOR_EC50 for an EC50, MIN_REPLICATES) are where full credit is reached,
with partial credit below them (no step, never conflicting). Better values never lower the degree; a value not stated is unknown, not 0.
Records are built from the synthetic CETSA passage through the extraction's own record builder."""
import ast
import inspect

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_cetsa_extraction import record_from_answer
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import cetsa_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_cetsa_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_converter import (
    CRITERIA_MAP, ISOTHERMAL_WINDOW_FULL_C, ISOTHERMAL_WINDOW_ZERO_C, TEMPERATURE_MARGIN_FULL_C, TEMPERATURE_MARGIN_ZERO_C, HIGH_OVER_EC50_FULL_AGREEMENT, HIGH_OVER_EC50_ZERO_AGREEMENT, JUDGES, LOW_OVER_EC50_FULL_AGREEMENT, LOW_OVER_EC50_ZERO_AGREEMENT, MIN_CONCENTRATIONS,
    MIN_CONCENTRATIONS_FOR_EC50, MIN_REPLICATES, MIN_TEMPERATURES, SD_MIN_EXPERIMENTS, TM_SHIFT_FULL_AGREEMENT_C, TM_SHIFT_ZERO_AGREEMENT_C, _criterion, convert_cetsa)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_grader import CRITERIA, grade_cetsa

SHIFT = ('thermal_shift', 'thermal_shift_recorded_for_the_sheet')
RANGE = ('concentration_range', 'concentration_range_recorded_for_the_sheet')
DOSE = ('dose_response', 'concentration_count_recorded_for_the_sheet')
COUNTS = ((('temperature_series', 'temperature_count_recorded_for_the_sheet'), 'temperature_count', MIN_TEMPERATURES, {}),
          (DOSE, 'concentration_count', MIN_CONCENTRATIONS_FOR_EC50, {}),      # the synthetic record reports an EC50
          (DOSE, 'concentration_count', MIN_CONCENTRATIONS, {'ec50_nM': None}),      # no EC50: a dose dependence
          (('replicates', 'replicate_count_recorded_for_the_sheet'), 'replicate_count', MIN_REPLICATES, {}))


def record(stated=None, support=None):
    """The record of the synthetic passage stating ``stated`` (default: every field)."""
    answer = cetsa_passages.answer_from(cetsa_passages.SYNTHETIC, cetsa_passages.SYNTHETIC_STATED if stated is None else stated, support)
    return record_from_answer(answer, cetsa_passages.SYNTHETIC, 0, 'experiment:cetsa', 'source:cetsa', 'assertion:cetsa')


def without(*names):
    return {name: value for name, value in cetsa_passages.SYNTHETIC_STATED.items() if name not in names}


def native():
    return grade_cetsa(record())['native']


def judged(key, native_values):
    return JUDGES[key](native_values)


def test_every_cetsa_criterion_maps_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(set(mapped)) and set(mapped) == set(CRITERIA)


def test_the_full_synthetic_record_meets_every_researched_value_and_gets_full_credit():
    # 10 temperatures, 11 concentrations, 3 independent experiments, a shift of 5.5 C, 0.01-30 uM around an EC50 of 0.8 uM
    graded = grade_cetsa(record())
    for name in CRITERIA:
        assert _criterion(graded, name)['status'] == 'supported', name
    interpretations = convert_cetsa(graded)['extraction']['interpretations']
    assert {c['status'] for c in interpretations.values()} == {'supported'}
    for name in ('binding_regime', 'binding_parameter_definition', 'sampling_basis'):
        assert interpretations[name]['degree'] == pytest.approx(1.0), name


def test_the_thermal_shift_ramp_is_monotone_with_partial_credit_between_its_researched_ends():
    base = {**native(), 'tm_spread_c': None}      # the absolute ramp alone: no spread of the Tm stated
    shifts = [0.1, TM_SHIFT_ZERO_AGREEMENT_C, TM_SHIFT_ZERO_AGREEMENT_C + 0.01, 1.0, 1.75, TM_SHIFT_FULL_AGREEMENT_C - 0.01, TM_SHIFT_FULL_AGREEMENT_C, 10.0]
    verdicts = [judged(SHIFT, {**base, 'shift_celsius': s}) for s in shifts]
    assert {v['status'] for v in verdicts} == {'supported'}
    degrees = [v['degree'] for v in verdicts]
    assert degrees == sorted(degrees) and all(0 <= d <= 1 for d in degrees)
    assert 0 < degrees[2] and 0 < degrees[5] < 1 and degrees[-2] == pytest.approx(1.0)      # just above the noise end and just below the full shift: partial credit
    assert degrees[4] == pytest.approx((1.75 - TM_SHIFT_ZERO_AGREEMENT_C) / (TM_SHIFT_FULL_AGREEMENT_C - TM_SHIFT_ZERO_AGREEMENT_C))


def test_a_small_positive_shift_is_no_credit_not_opposition_and_only_no_rise_or_a_fall_is_conflicting():
    base = {**native(), 'tm_spread_c': None}
    for shift in (0.05, 0.3, TM_SHIFT_ZERO_AGREEMENT_C):      # inside the reproducibility of the Tm: no paper spread is collected to call it scatter
        verdict = judged(SHIFT, {**base, 'shift_celsius': shift})
        assert verdict['status'] == 'supported' and verdict['degree'] == 0.0, shift
    for shift in (0.0, -1.0):      # the paper's own Tm values show no rise
        assert judged(SHIFT, {**base, 'shift_celsius': shift})['status'] == 'conflicting'


def test_the_grader_records_the_tm_spread_the_bracket_and_the_window_as_facts_for_the_synthetic_record():
    values = native()
    assert values['tm_spread_c'] == 0.4 and values['tm_spread_independent'] == 'yes' and values['shift_spread_refs']
    assert values['temperature_margin_low_c'] == pytest.approx(48.5 - 40) and values['temperature_margin_high_c'] == pytest.approx(67 - 54.0) and values['temperature_bracket_refs']
    assert values['isothermal_over_tm_c'] == pytest.approx(52 - 48.5) and values['isothermal_window_refs']
    absent = grade_cetsa(record(without('tm_spread', 'tm_spread_over_independent_experiments', 'temperature_lowest', 'tm_vehicle')))['native']
    assert absent['tm_spread_c'] is None and absent['temperature_margin_low_c'] is None and absent['isothermal_over_tm_c'] is None


def test_the_shift_over_the_stated_tm_spread_is_monotone_gradual_and_conflicting_only_inside_one_sd():
    base = native()      # shift 5.5 C
    sds = [0.4, 1.0, 1.8, 2.5, 5.5, 6.0]      # shift / sd: 13.75, 5.5, 3.06, 2.2, 1.0, 0.92
    verdicts = [judged(SHIFT, {**base, 'tm_spread_c': sd}) for sd in sds]
    assert [v['status'] for v in verdicts] == ['supported'] * 4 + ['conflicting'] * 2
    degrees = [v['degree'] for v in verdicts[:4]]
    assert degrees == sorted(degrees, reverse=True) and degrees[0] == pytest.approx(1.0) and 0 < degrees[3] < degrees[2] <= 1
    # an SD over technical replicates only gets the between-experiment scatter added: never a better degree than the same SD stated over independent experiments
    wells = judged(SHIFT, {**base, 'tm_spread_c': 1.8, 'tm_spread_independent': 'no'})
    independent = judged(SHIFT, {**base, 'tm_spread_c': 1.8, 'tm_spread_independent': 'yes'})
    assert wells['degree'] < independent['degree']
    unknown_basis = judged(SHIFT, {**base, 'tm_spread_c': 1.8, 'tm_spread_independent': 'unknown'})
    assert unknown_basis['degree'] == independent['degree']


def test_the_sampled_range_must_bracket_the_stated_tm_gradually_and_a_tm_outside_it_is_conflicting():
    key = ('temperature_series', 'temperature_count_recorded_for_the_sheet')
    base = native()
    margins = [TEMPERATURE_MARGIN_ZERO_C + 0.01, 1.0, 2.5, TEMPERATURE_MARGIN_FULL_C - 0.01, TEMPERATURE_MARGIN_FULL_C, 20.0]
    verdicts = [judged(key, {**base, 'temperature_margin_low_c': m}) for m in margins]
    assert {v['status'] for v in verdicts} == {'supported'}
    degrees = [v['degree'] for v in verdicts]
    assert degrees == sorted(degrees) and 0 < degrees[0] and 0 < degrees[3] < 1 and degrees[4] == pytest.approx(1.0)
    for margin in (TEMPERATURE_MARGIN_ZERO_C, -3.0):
        assert judged(key, {**base, 'temperature_margin_high_c': margin})['status'] == 'conflicting'
    no_range = judged(key, {**base, 'temperature_margin_low_c': None, 'temperature_margin_high_c': None})      # unknown, not opposition: the count alone decides
    assert no_range['status'] == 'supported' and no_range['degree'] == pytest.approx(1.0)


def test_the_isothermal_temperature_must_lie_near_the_unbound_tm_gradually_and_symmetrically():
    key = ('isothermal_window', 'isothermal_window_recorded_for_the_sheet')
    base = native()
    distances = [0.0, ISOTHERMAL_WINDOW_FULL_C, ISOTHERMAL_WINDOW_FULL_C + 0.01, 8.0, ISOTHERMAL_WINDOW_ZERO_C - 0.01]
    degrees = [judged(key, {**base, 'isothermal_over_tm_c': d})['degree'] for d in distances]
    assert degrees == sorted(degrees, reverse=True) and degrees[1] == pytest.approx(1.0) and 0 < degrees[2] < 1 and 0 < degrees[-1] < degrees[3]
    for d in distances:
        assert judged(key, {**base, 'isothermal_over_tm_c': -d}) == judged(key, {**base, 'isothermal_over_tm_c': d})
    assert judged(key, {**base, 'isothermal_over_tm_c': ISOTHERMAL_WINDOW_ZERO_C})['status'] == 'conflicting'
    assert judged(key, {**base, 'isothermal_over_tm_c': -20.0})['status'] == 'conflicting'


def test_the_isothermal_window_fact_is_used_when_the_numbers_are_not_both_stated_and_no_stays_conflicting():
    without_tm = grade_cetsa(record(without('tm_vehicle')))
    assert without_tm['reasons']['isothermal_window'] == 'facts_answered_yes' and without_tm['criteria']['isothermal_window']['status'] == 'supported'
    answer = cetsa_passages.answer_from(cetsa_passages.SYNTHETIC, cetsa_passages.SYNTHETIC_STATED)
    answer['isothermal_temperature_in_window'] = {**answer['isothermal_temperature_in_window'], 'value': 'no'}
    said_no = grade_cetsa(record_from_answer(answer, cetsa_passages.SYNTHETIC, 0, 'experiment:cetsa', 'source:cetsa', 'assertion:cetsa'))
    assert said_no['criteria']['isothermal_window']['status'] == 'conflicting' and said_no['reasons']['isothermal_window'] == 'fact_answered_no'


def test_the_concentration_range_is_monotone_and_linear_in_occupancy_between_its_researched_ends():
    base = native()
    lows = [LOW_OVER_EC50_ZERO_AGREEMENT - 0.01, 0.6, LOW_OVER_EC50_FULL_AGREEMENT + 0.01, LOW_OVER_EC50_FULL_AGREEMENT, 0.01]
    degrees = [judged(RANGE, {**base, 'low_over_ec50': low})['degree'] for low in lows]
    assert degrees == sorted(degrees) and all(0 < d <= 1 for d in degrees) and 0 < degrees[2] < 1
    highs = [HIGH_OVER_EC50_ZERO_AGREEMENT + 0.01, 3.0, HIGH_OVER_EC50_FULL_AGREEMENT - 0.01, HIGH_OVER_EC50_FULL_AGREEMENT, 100.0]
    degrees = [judged(RANGE, {**base, 'high_over_ec50': high})['degree'] for high in highs]
    assert degrees == sorted(degrees) and all(0 < d <= 1 for d in degrees) and 0 < degrees[2] < 1
    assert judged(RANGE, {**base, 'low_over_ec50': LOW_OVER_EC50_ZERO_AGREEMENT})['status'] == 'conflicting'
    assert judged(RANGE, {**base, 'high_over_ec50': HIGH_OVER_EC50_ZERO_AGREEMENT})['status'] == 'conflicting'
    # symmetric in fold distance from the EC50: half the EC50 at the low end and twice it at the high end both give 0.5 (linear in the ratio gave 0.63 and 0.25)
    assert judged(RANGE, {**base, 'low_over_ec50': 0.5})['degree'] == pytest.approx(0.5)
    assert judged(RANGE, {**base, 'high_over_ec50': 2.0})['degree'] == pytest.approx(0.5)


@pytest.mark.parametrize('key, count_key, researched, overrides', COUNTS)
def test_a_count_minimum_is_full_credit_at_the_researched_value_and_partial_credit_below_it(key, count_key, researched, overrides):
    base = {**native(), **overrides}
    counts = list(range(1, researched + 4))
    verdicts = [judged(key, {**base, count_key: n}) for n in counts]
    assert {v['status'] for v in verdicts} == {'supported'}      # no count is a cut-off to conflicting
    degrees = [v['degree'] for v in verdicts]
    assert degrees == sorted(degrees) and all(0 < d <= 1 for d in degrees)
    assert 0 < degrees[researched - 2] < 1      # just below the researched value: partial credit, not 0
    assert all(d == pytest.approx(1.0) for d in degrees[researched - 1:])      # full credit at the researched value and beyond


def test_each_count_curve_has_the_shape_chosen_for_cetsa():
    base = native()
    temperatures = [judged(COUNTS[0][0], {**base, 'temperature_count': n})['degree'] for n in (1, 2, 3, 4)]
    assert temperatures == pytest.approx([0.04, 0.16, 0.36, 0.64])      # (n / 5) ** 2: below the four sigmoid parameters the Tm is not defined
    for_ec50 = [judged(DOSE, {**base, 'concentration_count': n})['degree'] for n in (1, 2, 3, 4)]
    assert for_ec50 == pytest.approx([0.04, 0.16, 0.36, 0.64])      # (n / 5) ** 2 with an EC50: below the four logistic parameters the EC50 is not defined
    dependence = [judged(DOSE, {**base, 'ec50_nM': None, 'concentration_count': n})['degree'] for n in (1, 2, 3)]
    assert dependence == pytest.approx([1 / 3, 2 / 3, 1.0])      # n / 3 with no EC50: each concentration adds the dose dependence in equal parts
    replicates = [judged(COUNTS[3][0], {**base, 'replicate_count': n})['degree'] for n in (1, 2)]
    assert replicates == pytest.approx([(1 / 3) ** 0.5, (2 / 3) ** 0.5])      # (n / 3) ** 0.5: the precision of a mean


def test_the_same_short_series_counts_less_for_an_ec50_than_for_a_dose_dependence():
    base = native()
    for n in range(1, MIN_CONCENTRATIONS_FOR_EC50):
        assert judged(DOSE, {**base, 'concentration_count': n})['degree'] < judged(DOSE, {**base, 'ec50_nM': None, 'concentration_count': n})['degree'], n


def test_a_short_series_reaches_the_sheet_as_partial_credit_not_conflicting():
    graded = grade_cetsa(record())
    graded['native'].update({'temperature_count': MIN_TEMPERATURES - 1, 'replicate_count': MIN_REPLICATES - 1})
    interpretations = convert_cetsa(graded)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.64)
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx((2 / 3) ** 0.5)


def test_replicates_not_stated_independent_or_not_counted_are_unknown_not_0():
    for missing in ('independent_experiments', 'replicate_count'):
        graded = grade_cetsa(record(without(missing)))
        assert _criterion(graded, 'replicates')['status'] == 'unknown', missing
        assert convert_cetsa(graded)['extraction']['interpretations']['sampling_basis']['status'] == 'unknown', missing
    base = native()
    assert judged(COUNTS[3][0], {**base, 'replicate_count': 1, 'replicate_independent': 'unknown'})['status'] == 'unknown'      # below the minimum: unknown, no longer conflicting


def test_a_standard_deviation_becomes_a_variance_only_from_at_least_two_independent_experiments():
    def with_sd(n):
        graded = grade_cetsa(record())
        graded['native']['spread_kind'] = 'standard_deviation'
        graded['native']['replicate_count'] = n
        graded['native']['quantities']['replicate_count'] = {**graded['native']['quantities']['replicate_count'], 'value': n}
        return convert_cetsa(graded)
    single = with_sd(SD_MIN_EXPERIMENTS - 1)      # one experiment is supported (partial credit) but cannot have a between-experiment SD
    assert single['extraction']['interpretations']['sampling_basis']['status'] == 'supported'
    assert single['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    assert 'variance_correspondence' not in single['extraction']['interpretations']
    two = with_sd(SD_MIN_EXPERIMENTS)
    assert two['extraction']['quantities']['effect_variance']['value'] == pytest.approx(100.0 ** 2 / SD_MIN_EXPERIMENTS)      # 0.1 uM = 100 nM
    assert two['extraction']['interpretations']['variance_correspondence']['status'] == 'supported'


def test_support_lowers_the_degree_and_never_changes_a_status():
    direct = convert_cetsa(grade_cetsa(record()))['extraction']['interpretations']
    implied = convert_cetsa(grade_cetsa(record(support={'temperature_count': 'implied', 'replicate_count': 'about_something_else'})))['extraction']['interpretations']
    assert {n: c['status'] for n, c in direct.items()} == {n: c['status'] for n, c in implied.items()}
    assert implied['binding_regime']['degree'] < direct['binding_regime']['degree']
    assert implied['sampling_basis']['degree'] < direct['sampling_basis']['degree']


def test_a_record_with_no_ec50_carries_the_detected_statement_and_no_effect():
    converted = convert_cetsa(grade_cetsa(record(without('engagement_ec50', 'engagement_ec50_spread'))))
    assert converted['qualitative_effect']['statement'] == 'interaction_detected'
    assert converted['qualitative_effect']['thermal_shift_celsius'] == 5.5
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['direction_field_support'] == 'direct'


def test_every_number_a_judge_uses_is_a_named_expert_review_constant():
    source = inspect.getsource(literature_cetsa_converter)
    tree = ast.parse(source)
    lines = source.splitlines()
    named = [node for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float))]
    assert {target.id for node in named for target in node.targets} >= {'MIN_TEMPERATURES', 'MIN_CONCENTRATIONS', 'MIN_CONCENTRATIONS_FOR_EC50', 'MIN_REPLICATES', 'TEMPERATURE_CREDIT_POWER', 'CONCENTRATION_CREDIT_POWER',
                                                                        'EC50_CONCENTRATION_CREDIT_POWER', 'REPLICATE_CREDIT_POWER', 'SD_MIN_EXPERIMENTS', 'SHIFT_OVER_SPREAD_FULL_AGREEMENT', 'SHIFT_OVER_SPREAD_ZERO_AGREEMENT',
                                                                        'BETWEEN_EXPERIMENT_TM_SD_C', 'TEMPERATURE_MARGIN_FULL_C', 'ISOTHERMAL_WINDOW_FULL_C', 'ISOTHERMAL_WINDOW_ZERO_C'}
    for node in named:      # a researched value is EXPERT_REVIEW; a count that follows from a definition is FIXED_BY_DEFINITION
        assert 'EXPERT_REVIEW' in lines[node.lineno - 1] or 'FIXED_BY_DEFINITION' in lines[node.lineno - 1], node.targets[0].id
    in_functions = {n.value for f in tree.body if isinstance(f, ast.FunctionDef) for n in ast.walk(f) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}
    assert in_functions <= {0, 1}
