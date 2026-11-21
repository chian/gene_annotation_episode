"""Split-reporter converter: the sheet-side judgements keep the researched EXPERT_REVIEW values and are gradual around them (owner rule, SOP step 3).

Built on the synthetic passage's record (forms/.../tests/split_reporter_passages.py) through the real extraction, grader and converter; a judge is then
exercised by changing one recorded number of the grader's native values. Proven per judge: monotone (better never lowers the degree), bounded in [0, 1],
no step at a researched value (just below it is partial credit, not a conflict), unknown when the value is not stated, conflicting only at or beyond the
researched zero-agreement value, every number a named EXPERT_REVIEW constant, and quote support lowering the degree without changing the status.
"""
import ast
import copy
import inspect
import math

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_split_reporter_extraction import (
    UNITS, field_names, record_from_answer, validate_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.split_reporter_passages import (
    SYNTHETIC, SYNTHETIC_STATED)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_split_reporter_converter as converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_converter import (
    JUDGES, _criterion, convert_split_reporter)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_grader import grade_split_reporter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORT_DEGREE, apply_support


def synthetic_answer(unavailable=()):
    """The answer stating every field of SYNTHETIC_STATED with direct support, except the fields in ``unavailable`` (not stated in the passage)."""
    answer = {name: {'status': 'stated', 'value': SYNTHETIC_STATED[name][0], 'quote': SYNTHETIC_STATED[name][2], 'support': 'direct', 'reason': None,
                     **({'unit': SYNTHETIC_STATED[name][1]} if name in UNITS else {})} for name in field_names()}
    for name in unavailable:
        answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None, 'reason': 'not_stated_in_passage', **({'unit': None} if name in UNITS else {})}
    return answer


def graded(unavailable=()):
    record = record_from_answer(validate_answer(synthetic_answer(unavailable), SYNTHETIC), SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')
    return grade_split_reporter(record)


def judged(name, **native):
    result = copy.deepcopy(graded())
    result['native'].update(native)
    return _criterion(result, name)


# criterion -> (native field, its researched full-agreement value, its researched zero-agreement value, values from worse to better)
SINGLE = {
    'signal_to_background': ('signal_to_background', converter.SIGNAL_TO_BACKGROUND_FULL_AGREEMENT, converter.SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT, (1.0, 2.0, 2.5, 4.0, 6.0, 9.9, 10.0, 85.0)),
    'negative_control_ratio': ('signal_over_negative_control', converter.NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT, converter.NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT, (1.0, 1.5, 1.8, 3.0, 4.9, 5.0, 40.0)),
    'fusion_orientations': ('orientation_pairs_positive', converter.MIN_ORIENTATIONS, None, (0, 1, 2, 4, 8)),
    'titration_series': ('concentration_count', converter.MIN_CONCENTRATIONS, None, (1, 2, 3, 8, 24)),
    'replicates': ('replicate_count', converter.MIN_REPLICATES, None, (1, 2, 3, 10)),
}
# the count criteria: the researched minimum and the count just below it; a count has no conflicting zero end (owner rule), only its own shape
COUNTS = ('fusion_orientations', 'titration_series', 'replicates')
COUNT_SHAPES = {'fusion_orientations': lambda n: min(1.0, n / converter.MIN_ORIENTATIONS),
                'titration_series': lambda n: max(0.0, min(1.0, (n - converter.CONCENTRATIONS_ZERO_AGREEMENT) / (converter.MIN_CONCENTRATIONS - converter.CONCENTRATIONS_ZERO_AGREEMENT))),
                'replicates': lambda n: min(1.0, (n / converter.MIN_REPLICATES) ** 0.5)}


def degree_of(verdict):
    """0 for a conflict (no agreement), else the degree of the supported verdict."""
    return 0.0 if verdict['status'] == 'conflicting' else verdict['degree']


def test_the_synthetic_record_meets_every_researched_value_and_converts_supported():
    result = graded()
    for criterion, reason in JUDGES:
        assert result['reasons'][criterion] in {r for c, r in JUDGES if c == criterion}
        verdict = _criterion(result, criterion)
        assert verdict['status'] == 'supported' and verdict['support_refs'] and verdict['degree'] == 1.0
    converted = convert_split_reporter(result)
    assert set(converted['extraction']['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}
    assert all(i['status'] == 'supported' for i in converted['extraction']['interpretations'].values())


@pytest.mark.parametrize('criterion', sorted(SINGLE))
def test_monotone_and_bounded(criterion):
    field, _, _, values = SINGLE[criterion]
    degrees = [degree_of(judged(criterion, **{field: v})) for v in values]
    assert all(0 <= d <= 1 for d in degrees)
    assert degrees == sorted(degrees)
    assert degrees[0] < 1.0 and degrees[-1] == 1.0
    if criterion in COUNTS:
        verdicts = [judged(criterion, **{field: v}) for v in values]
        assert all(v['status'] == 'supported' for v in verdicts)                              # a short count is never conflicting
        assert degrees == pytest.approx([COUNT_SHAPES[criterion](v) for v in values])
    else:
        assert degrees[0] == 0.0


@pytest.mark.parametrize('criterion', sorted(SINGLE))
def test_full_credit_at_the_researched_value(criterion):
    field, full, _, _ = SINGLE[criterion]
    verdict = judged(criterion, **{field: full})
    assert verdict['status'] == 'supported' and verdict['degree'] == 1.0


@pytest.mark.parametrize('criterion', COUNTS)
def test_a_count_just_below_the_researched_minimum_is_partial_credit_not_a_conflict(criterion):
    field, minimum, _, _ = SINGLE[criterion]
    verdict = judged(criterion, **{field: minimum - 1})
    assert verdict['status'] == 'supported' and verdict['support_refs']
    assert 0 < verdict['degree'] < 1
    assert verdict['degree'] == pytest.approx(COUNT_SHAPES[criterion](minimum - 1))


def test_the_count_shapes_chosen_for_the_split_reporter():
    # one fusion geometry: half; titration: one residual per point beyond the isotherm's two parameters (range review: 5 / 2), two or fewer no credit, never conflicting;
    # replicates sqrt(n / 3)
    assert judged('fusion_orientations', orientation_pairs_positive=1)['degree'] == pytest.approx(0.5)
    assert judged('fusion_orientations', orientation_pairs_positive=0) == {'status': 'supported', 'support_refs': judged('fusion_orientations', orientation_pairs_positive=0)['support_refs'], 'degree': 0.0}
    for count, degree in ((1, 0.0), (2, 0.0), (3, 1 / 3), (4, 2 / 3), (5, 1.0)):
        verdict = judged('titration_series', concentration_count=count)
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(degree), count
    assert judged('replicates', replicate_count=2)['degree'] == pytest.approx((2 / 3) ** 0.5)
    assert judged('replicates', replicate_count=1)['degree'] == pytest.approx((1 / 3) ** 0.5)
    assert judged('replicates', replicate_count=2, replicate_independent='no')['status'] == 'unknown'      # the judge only sees yes; a stated no is the grader's conflicting before it


@pytest.mark.parametrize('criterion', ['signal_to_background', 'negative_control_ratio'])
def test_a_ratio_just_below_its_researched_value_is_nearly_full_credit_no_step(criterion):
    field, full, zero, _ = SINGLE[criterion]
    just_below = judged(criterion, **{field: full * 0.99})
    assert just_below['status'] == 'supported' and 0.95 < just_below['degree'] < 1
    just_above_zero = judged(criterion, **{field: zero * 1.01})
    assert just_above_zero['status'] == 'supported' and 0 < just_above_zero['degree'] < 0.05


# only the ratios have a conflicting zero end; a count never conflicts (owner rule)
@pytest.mark.parametrize('criterion', sorted(c for c in SINGLE if c not in COUNTS))
def test_conflicting_with_refs_at_the_researched_zero_value(criterion):
    field, _, zero, _ = SINGLE[criterion]
    verdict = judged(criterion, **{field: zero})
    assert verdict['status'] == 'conflicting' and verdict['support_refs'] and 'degree' not in verdict


def test_the_titration_range_ramps_are_kept_and_the_weaker_end_decides():
    lows = [degree_of(judged('titration_range', low_over_kd=lo, high_over_kd=25.0)) for lo in (1.0, 0.8, 0.5, 0.21, 0.2, 0.025)]
    highs = [degree_of(judged('titration_range', low_over_kd=0.025, high_over_kd=hi)) for hi in (1.0, 2.0, 4.0, 4.99, 5.0, 1000.0)]
    for degrees in (lows, highs):
        assert all(0 <= d <= 1 for d in degrees) and degrees == sorted(degrees)
        assert degrees[0] == 0.0 and degrees[-1] == 1.0 and 0 < degrees[2] < 1
    both = judged('titration_range', low_over_kd=0.6, high_over_kd=3.0)['degree']
    assert both == pytest.approx(min(0.375, 0.75))                   # linear in occupancy: low 0.6 x -> 0.375, high 3 x -> 0.75


def test_the_titration_range_is_linear_in_the_one_site_occupancy():
    # range review: 0.2 x and 5 x KD are mirror images on the binding curve (1/6 and 5/6), so the two ends are judged alike
    occupancy = lambda r: r / (1 + r)
    for low, expected in ((0.5, 0.5), (0.6, 0.375), (0.3, (0.5 - occupancy(0.3)) / (0.5 - occupancy(0.2)))):
        assert judged('titration_range', low_over_kd=low, high_over_kd=25.0)['degree'] == pytest.approx(expected)
    for high, expected in ((2.0, 0.5), (3.0, 0.75), (4.0, (occupancy(4.0) - 0.5) / (occupancy(5.0) - 0.5))):
        assert judged('titration_range', low_over_kd=0.025, high_over_kd=high)['degree'] == pytest.approx(expected)
    for shortfall in (0.6, 0.75, 0.9):
        low = judged('titration_range', low_over_kd=1.0 - shortfall * 0.8, high_over_kd=25.0)['degree']
        assert low == pytest.approx(judged('titration_range', low_over_kd=0.025, high_over_kd=1 / (1.0 - shortfall * 0.8))['degree'])


def test_one_concentration_is_a_short_series_not_a_badly_placed_low_end():
    # lowest = highest: no lower end to judge; the high end still decides, and the count criterion gives the short series its low credit
    single = judged('titration_range', low_over_kd=8.0, high_over_kd=8.0)
    assert single['status'] == 'supported' and single['degree'] == 1.0
    assert judged('titration_range', low_over_kd=0.8, high_over_kd=0.8)['status'] == 'conflicting'      # one concentration below the KD: the high end is not reached


@pytest.mark.parametrize('criterion', ['signal_to_background', 'negative_control_ratio'])
def test_a_fold_is_judged_linearly_in_its_log(criterion):
    # range review: a fold is multiplicative, so the degree is linear in log fold between the researched values; equal ratios cost the same
    field, full, zero, _ = SINGLE[criterion]
    assert judged(criterion, **{field: (full * zero) ** 0.5})['degree'] == pytest.approx(0.5)
    steps = [zero * (full / zero) ** (k / 4) for k in range(1, 5)]
    degrees = [judged(criterion, **{field: v})['degree'] for v in steps]
    assert degrees == pytest.approx([0.25, 0.5, 0.75, 1.0])
    assert judged('signal_to_background', signal_to_background=4.0)['degree'] == pytest.approx(0.4307, abs=1e-4)          # was 0.25 linear
    assert judged('negative_control_ratio', signal_over_negative_control=3.0)['degree'] == pytest.approx(0.5757, abs=1e-4)  # was 0.43 linear


def test_the_orientations_that_gave_a_signal_are_the_evidence_and_a_stated_single_orientation_is_partial_credit_not_a_conflict():
    # grader gap + grader rule change (2026-11-21): the 'no' for signal_in_several_orientations was conflicting; a real pair often signals in only some geometries
    assert graded()['reasons']['fusion_orientations'] == 'orientation_positive_recorded_for_the_sheet'
    only_one = graded(unavailable=('orientation_pairs_positive',))
    only_one['native'].update({'orientation_single': True, 'orientation_single_refs': ['span_x']})
    only_one['reasons']['fusion_orientations'] = 'orientation_single_recorded_for_the_sheet'
    verdict = _criterion(only_one, 'fusion_orientations')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(0.5) and verdict['support_refs'] == ['span_x']
    tested_only = graded(unavailable=('orientation_pairs_positive',))
    assert tested_only['reasons']['fusion_orientations'] == 'orientation_pairs_recorded_for_the_sheet'
    assert _criterion(tested_only, 'fusion_orientations')['degree'] == 1.0                     # four tested, as before
    tested_only['native']['orientation_pairs_tested'] = 1
    assert _criterion(tested_only, 'fusion_orientations')['degree'] == pytest.approx(0.5)


def test_the_constant_partner_is_judged_on_its_depletion_bias_gradually_like_the_fp_tracer():
    bias = lambda r: 1 + 0.5 * r
    full, zero = converter.FIXED_PARTNER_MAX_OVER_KD, converter.FIXED_PARTNER_ZERO_AGREEMENT_OVER_KD
    ratios = (10.0, 5.0, 2.0, 1.01, 1.0, 0.1, 0.0018)
    degrees = [degree_of(judged('titration_range', low_over_kd=0.025, high_over_kd=25.0, fixed_over_kd=r, fixed_refs=['span_f'])) for r in ratios]
    assert degrees == sorted(degrees) and degrees[0] == 0.0 and degrees[-1] == 1.0 and all(0 <= d <= 1 for d in degrees)
    assert judged('titration_range', low_over_kd=0.025, high_over_kd=25.0, fixed_over_kd=10.0, fixed_refs=['span_f'])['status'] == 'conflicting'
    assert judged('titration_range', low_over_kd=0.025, high_over_kd=25.0, fixed_over_kd=2.0, fixed_refs=['span_f'])['degree'] == pytest.approx(
        (math.log(bias(zero)) - math.log(bias(2.0))) / (math.log(bias(zero)) - math.log(bias(full))))
    just_above = judged('titration_range', low_over_kd=0.025, high_over_kd=25.0, fixed_over_kd=1.01, fixed_refs=['span_f'])
    assert just_above['status'] == 'supported' and 0.95 < just_above['degree'] < 1                  # no step at the researched value
    assert judged('titration_range', low_over_kd=0.6, high_over_kd=3.0, fixed_over_kd=0.1, fixed_refs=['span_f'])['degree'] == pytest.approx(0.375)   # the weakest part decides


def test_the_constant_partner_alone_is_judged_and_not_stated_is_not_judged():
    alone = graded(unavailable=('loaded_concentration_lowest',))
    assert alone['reasons']['titration_range'] == 'titration_range_recorded_for_the_sheet' and alone['native']['fixed_over_kd'] == pytest.approx(2 / 40)
    assert _criterion(alone, 'titration_range')['status'] == 'supported'
    without = graded(unavailable=('fixed_partner_concentration',))
    assert without['native']['fixed_over_kd'] is None and _criterion(without, 'titration_range')['degree'] == 1.0


def test_expression_not_matched_to_the_control_is_the_papers_own_conflict_and_matched_or_silent_changes_nothing():
    no = copy.deepcopy(SYNTHETIC_RECORD_FOR_FACT_TESTS())
    no['facts']['expression_matched_to_control'] = {**no['facts']['expression_matched_to_control'], 'answer': 'no'}
    result = grade_split_reporter(no)
    assert result['reasons']['negative_control_ratio'] == 'expression_not_matched'
    verdict = _criterion(result, 'negative_control_ratio')
    assert verdict['status'] == 'conflicting' and verdict['support_refs']
    for answer in ('yes', 'unknown'):
        record = copy.deepcopy(SYNTHETIC_RECORD_FOR_FACT_TESTS())
        record['facts']['expression_matched_to_control'] = {**record['facts']['expression_matched_to_control'], 'answer': answer}
        yes = grade_split_reporter(record)
        assert yes['reasons']['negative_control_ratio'] == 'negative_control_ratio_recorded_for_the_sheet'
        assert _criterion(yes, 'negative_control_ratio')['degree'] == 1.0


def SYNTHETIC_RECORD_FOR_FACT_TESTS():
    return record_from_answer(validate_answer(synthetic_answer(), SYNTHETIC), SYNTHETIC, 5000, 'exp_1', 'source_1', 'hypothesis_1')


def test_replicates_whose_independence_is_not_stated_yes_are_unknown_not_zero():
    for count in (2, 3, 10):
        assert judged('replicates', replicate_count=count, replicate_independent='unknown') == {'status': 'unknown', 'support_refs': []}


@pytest.mark.parametrize('criterion, fields, reason', [
    ('signal_to_background', ('signal_to_background',), 'signal_to_background_not_given'),
    ('negative_control_ratio', ('signal_over_negative_control',), 'negative_control_ratio_not_given'),
    ('titration_series', ('concentration_count',), 'concentration_count_not_given'),
    ('titration_range', ('loaded_concentration_lowest', 'fixed_partner_concentration'), 'titration_range_not_given'),
])
def test_a_value_not_stated_is_unknown_not_zero(criterion, fields, reason):
    result = graded(unavailable=fields)
    assert result['reasons'][criterion] == reason
    assert _criterion(result, criterion) == {'status': 'unknown', 'support_refs': []}


@pytest.mark.parametrize('criterion', COUNTS)
def test_support_lowers_the_degree_and_never_changes_the_status(criterion):
    field, minimum, _, _ = SINGLE[criterion]
    for value in (minimum - 1, minimum):
        verdict = judged(criterion, **{field: value})
        lowered = apply_support(verdict, ['implied'])
        assert lowered['status'] == verdict['status'] == 'supported'
        assert lowered['degree'] == pytest.approx(verdict['degree'] * SUPPORT_DEGREE['implied'])
    conflict = judged('signal_to_background', signal_to_background=1.0)
    assert apply_support(conflict, ['about_something_else'])['status'] == 'conflicting'


def test_every_number_a_judge_uses_is_a_named_expert_review_constant():
    tree = ast.parse(inspect.getsource(converter))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith('_judge_'):
            literals = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
            assert literals == [], node.name
    lines = inspect.getsource(converter).splitlines()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
            assert 'EXPERT_REVIEW' in lines[node.lineno - 1], node.targets[0].id
    assert not hasattr(converter, 'ORIENTATIONS_ZERO_AGREEMENT') and not hasattr(converter, 'REPLICATES_ZERO_AGREEMENT')      # removed: no reason in the assay's science (owner rule 4) / replaced by sqrt(n / MIN_REPLICATES) (rule 1)
    for name in ('FIXED_PARTNER_MAX_OVER_KD', 'FIXED_PARTNER_ZERO_AGREEMENT_OVER_KD', 'FIXED_PARTNER_BOUND_AT_MIDPOINT'):
        assert hasattr(converter, name)
    for name in ('MIN_ORIENTATIONS', 'MIN_CONCENTRATIONS', 'CONCENTRATIONS_ZERO_AGREEMENT', 'MIN_REPLICATES',
                 'SIGNAL_TO_BACKGROUND_FULL_AGREEMENT', 'SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT', 'NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT', 'NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT',
                 'LOW_OVER_KD_FULL_AGREEMENT', 'LOW_OVER_KD_ZERO_AGREEMENT', 'HIGH_OVER_KD_FULL_AGREEMENT', 'HIGH_OVER_KD_ZERO_AGREEMENT'):
        assert hasattr(converter, name)


def test_the_researched_values_are_kept():
    assert (converter.SIGNAL_TO_BACKGROUND_FULL_AGREEMENT, converter.SIGNAL_TO_BACKGROUND_ZERO_AGREEMENT) == (10.0, 2.0)
    assert (converter.NEGATIVE_CONTROL_RATIO_FULL_AGREEMENT, converter.NEGATIVE_CONTROL_RATIO_ZERO_AGREEMENT) == (5.0, 1.5)
    assert (converter.MIN_ORIENTATIONS, converter.MIN_REPLICATES) == (2, 3)
    assert (converter.MIN_CONCENTRATIONS, converter.CONCENTRATIONS_ZERO_AGREEMENT) == (5, 2)      # range review 2026-11-21: was 3 / 1 (three points left one residual)
    assert (converter.LOW_OVER_KD_FULL_AGREEMENT, converter.LOW_OVER_KD_ZERO_AGREEMENT, converter.HIGH_OVER_KD_FULL_AGREEMENT, converter.HIGH_OVER_KD_ZERO_AGREEMENT) == (0.2, 1.0, 5.0, 1.0)


def test_the_range_review_answers_every_researched_value():
    doc = converter.__doc__
    assert 'Range review' in doc and 'Grader gaps' in doc
    for name in ('SIGNAL_TO_BACKGROUND', 'NEGATIVE_CONTROL_RATIO', 'MIN_ORIENTATIONS', 'FIXED_PARTNER', 'MIN_CONCENTRATIONS', 'CONCENTRATIONS_ZERO_AGREEMENT', 'LOW_OVER_KD', 'HIGH_OVER_KD', 'MIN_REPLICATES'):
        block = doc.split('Range review', 1)[1]
        assert name in block, name
    assert all(q in doc.split('Range review', 1)[1] for q in ('Q1', 'Q2', 'Q3', 'Q4', 'Q5'))
