"""BRET converter: the researched EXPERT_REVIEW values kept or changed by the range review (2026-11-21: titration points 5 -> 8, ratio range linear in the share of the plateau, fit zero end 0.80 -> 0.50), the count minimums gradual, the qualitative effect and the mapping."""
import ast
import inspect
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bret_record import FACTS, PREPARATION_KEYS, QUANTITIES, UNITS, fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_bret_converter as converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_converter import CRITERIA_MAP, _criterion, convert_bret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_grader import CRITERIA, grade_bret

# a saturation titration that meets every researched value: BRET50 control/pair 5, signal over control 6, range 0.1x to 10x BRET50, 8 points, R squared 0.98, 3 independent experiments
STATED = {'kd': None, 'kd_spread': None, 'ki': None, 'ki_spread': None, 'bret50': 0.5, 'bret50_negative_control': 2.5, 'bret_max': 0.35, 'bret_ratio_pair': 0.3, 'bret_ratio_negative_control': 0.05,
          'ratio_lowest': 0.05, 'ratio_highest': 5.0, 'titration_point_count': 8.0, 'tracer_concentration': None, 'fit_r_squared': 0.98, 'replicate_count': 3.0,
          'bret50_spread': None, 'bret50_negative_control_spread': None, 'bret_ratio_pair_spread': None, 'bret_ratio_negative_control_spread': None, 'bret_ratio_donor_only': None, 'tracer_kd': None}


def record(spread_kind=None, **values):
    """A BRET record stating every fact as yes and every quantity of STATED (overridden by ``values``; None makes it unavailable)."""
    stated = {**STATED, **values}
    quantities = {name: unavailable(UNITS[name][0], name, 'not_stated_in_passage') if stated[name] is None else point(stated[name], UNITS[name][0] if name not in ('kd', 'kd_spread', 'ki', 'ki_spread', 'tracer_concentration', 'tracer_kd') else 'nM', name, ['span_' + name]) for name in QUANTITIES}
    return {'version': 'a105_bret_record', 'experiment_type': 'bret', 'experiment_ref': 'exp_bret_1', 'source_ref': 'src_bret_1', 'assertion_ref': 'assert_bret_1',
            'preparations': {'component_a_preparation_ref': 'prep_a', 'component_b_preparation_ref': 'prep_b', 'dataset_ref': 'dataset_bret_1'}, 'quantities': quantities,
            'bret_format': 'saturation_titration', 'donor': 'rluc', 'acceptor': 'fluorescent_protein', 'expression': 'transient_transfection', 'spread_kind': spread_kind,
            'facts': {name: fact('yes', ['span_' + name]) for name in FACTS},
            'choice_support': {'bret_format': 'direct', 'donor': 'direct', 'acceptor': 'direct', 'expression': 'direct', 'spread_kind': 'direct' if spread_kind else None}, 'spans': {}}


def judged(name, rec=None, **values):
    return _criterion(grade_bret(rec if rec is not None else record(**values)), name)


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    assert set(PREPARATION_KEYS) == set(record()['preparations'])
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped))


def test_the_researched_values_are_kept_or_changed_by_the_range_review():
    assert (converter.MIN_TITRATION_POINTS, converter.TITRATION_POINTS_ZERO_AGREEMENT, converter.MIN_REPLICATES) == (8, 2, 3)     # range review: 5 -> 8 (x measured with error; usual 8 to 15 ratios)
    assert (converter.BRET50_CONTROL_FULL_AGREEMENT, converter.BRET50_CONTROL_ZERO_AGREEMENT, converter.SIGNAL_FULL_AGREEMENT, converter.SIGNAL_ZERO_AGREEMENT) == (3.0, 1.0, 3.0, 1.0)
    assert (converter.LOW_OVER_BRET50_FULL_AGREEMENT, converter.LOW_OVER_BRET50_ZERO_AGREEMENT, converter.HIGH_OVER_BRET50_FULL_AGREEMENT, converter.HIGH_OVER_BRET50_ZERO_AGREEMENT) == (0.2, 1.0, 5.0, 1.0)
    assert (converter.FIT_R_SQUARED_FULL_AGREEMENT, converter.FIT_R_SQUARED_ZERO_AGREEMENT) == (0.95, 0.50)     # range review: zero end 0.80 -> 0.50 (owner to confirm)
    assert 'Range review' in converter.__doc__ and all(name in converter.__doc__ for name in ('bret50_specificity', 'signal_over_control', 'titration_points', 'ratio_range', 'fit_quality', 'replicates'))


def test_a_record_meeting_every_researched_value_is_fully_supported():
    interpretations = convert_bret(grade_bret(record()))['extraction']['interpretations']
    assert {name: item['status'] for name, item in interpretations.items()} == dict.fromkeys(CRITERIA_MAP, 'supported')
    assert all(item.get('degree', 1.0) == 1.0 for item in interpretations.values())


def test_titration_points_rise_linearly_with_the_residual_degrees_of_freedom_to_full_credit_at_the_researched_minimum():
    assert judged('titration_points', titration_point_count=2.0) == {'status': 'supported', 'support_refs': ['span_titration_point_count'], 'degree': 0.0}   # as many points as parameters: no credit, never conflicting
    assert judged('titration_points', titration_point_count=1.0)['status'] == 'supported' and judged('titration_points', titration_point_count=1.0)['degree'] == 0.0
    assert judged('titration_points', titration_point_count=3.0)['degree'] == pytest.approx(1 / 6)
    assert judged('titration_points', titration_point_count=4.0)['degree'] == pytest.approx(2 / 6)
    assert judged('titration_points', titration_point_count=5.0)['degree'] == pytest.approx(0.5)        # the old full-credit count: now half credit (range review)
    assert judged('titration_points', titration_point_count=7.0)['degree'] == pytest.approx(5 / 6)      # just below MIN_TITRATION_POINTS: partial credit, not conflicting
    assert judged('titration_points', titration_point_count=8.0) == {'status': 'supported', 'support_refs': ['span_titration_point_count'], 'degree': 1.0}
    assert judged('titration_points', titration_point_count=12.0)['degree'] == 1.0


def test_replicates_rise_as_the_precision_of_the_mean_to_full_credit_at_the_researched_minimum():
    assert judged('replicates', replicate_count=1.0)['degree'] == pytest.approx(math.sqrt(1 / 3))      # a single stated run: partial credit, never conflicting
    assert judged('replicates', replicate_count=2.0)['degree'] == pytest.approx(math.sqrt(2 / 3))      # just below MIN_REPLICATES: partial credit, not conflicting
    assert judged('replicates', replicate_count=3.0)['degree'] == 1.0
    assert judged('replicates', replicate_count=6.0)['degree'] == 1.0


@pytest.mark.parametrize('name, field, better', [
    ('titration_points', 'titration_point_count', (3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 20.0)),
    ('replicates', 'replicate_count', (1.0, 2.0, 3.0, 4.0, 10.0)),
    ('bret50_specificity', 'bret50_negative_control', (0.6, 1.0, 1.5, 2.5, 10.0)),     # the control needs ever more acceptor than the pair (BRET50 of the pair 0.5)
    ('signal_over_control', 'bret_ratio_negative_control', (0.29, 0.2, 0.15, 0.1, 0.01)),   # a lower control under the same pair signal
    ('ratio_range', 'ratio_lowest', (0.45, 0.35, 0.3, 0.2, 0.1, 0.01)),
    ('ratio_range', 'ratio_highest', (0.55, 1.0, 1.5, 2.5, 10.0)),
    ('fit_quality', 'fit_r_squared', (0.55, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99)),
])
def test_a_better_value_never_lowers_the_degree_and_the_degree_is_bounded(name, field, better):
    verdicts = [judged(name, **{field: value}) for value in better]
    assert all(v['status'] == 'supported' and v['support_refs'] for v in verdicts)
    degrees = [v['degree'] for v in verdicts]
    assert all(0 < d <= 1 for d in degrees) and degrees == sorted(degrees) and degrees[0] < degrees[-1]


def test_the_kept_full_to_zero_agreement_ramps_are_unchanged():
    assert judged('signal_over_control', bret_ratio_negative_control=0.15)['degree'] == pytest.approx(0.5)       # signal over control 2: halfway from 1 to 3
    assert judged('bret50_specificity', bret50_negative_control=1.0)['degree'] == pytest.approx(0.5)            # BRET50 control over pair 2
    assert judged('bret50_specificity', bret50_negative_control=0.75)['degree'] == pytest.approx(0.25)          # 1.5-fold, within the run-to-run BRET50 scatter: little credit
    for field, value in (('bret_ratio_negative_control', 0.3), ('bret_ratio_negative_control', 0.6)):
        assert judged('signal_over_control', **{field: value})['status'] == 'conflicting'                     # no larger than the paper's own control
    assert judged('bret50_specificity', bret50_negative_control=0.5)['status'] == 'conflicting'


def test_the_ratio_range_falls_linearly_in_the_share_of_the_plateau_reached():
    # BRET50 0.5: x / (1 + x) is 1/6 at the full ends (0.2x and 5x) and 1/2 at the zero ends (1x); the old ramps were linear in x
    assert judged('ratio_range', ratio_lowest=0.3)['degree'] == pytest.approx((0.5 - 0.6 / 1.6) / (0.5 - 1 / 6))       # lowest at 0.6x: 0.375 (was 0.5)
    assert judged('ratio_range', ratio_lowest=0.25)['degree'] == pytest.approx(0.5)                                     # lowest at 0.5x: one third of the plateau
    assert judged('ratio_range', ratio_highest=1.5)['degree'] == pytest.approx(0.75)                                    # highest at 3x: 75 percent of BRETmax (was 0.5)
    assert judged('ratio_range', ratio_highest=1.0)['degree'] == pytest.approx(0.5)                                     # highest at 2x (was 0.25)
    assert judged('ratio_range', ratio_lowest=0.1, ratio_highest=2.5)['degree'] == 1.0                                  # exactly at both full ends
    for field, value in (('ratio_lowest', 0.5), ('ratio_lowest', 0.8), ('ratio_highest', 0.5), ('ratio_highest', 0.3)):
        assert judged('ratio_range', **{field: value})['status'] == 'conflicting'                                       # never leaves or never passes half of the plateau
    # the two ends are mirror images on the hyperbola: a bottom at BRET50 / k and a top at k x BRET50 score alike
    for k in (1.5, 2.0, 3.0, 4.0):
        assert judged('ratio_range', ratio_lowest=0.5 / k)['degree'] == pytest.approx(judged('ratio_range', ratio_highest=0.5 * k)['degree'])


def test_the_fit_ramp_reaches_zero_only_where_the_curve_explains_no_more_than_it_leaves():
    assert judged('fit_quality', fit_r_squared=0.95)['degree'] == 1.0
    assert judged('fit_quality', fit_r_squared=0.875)['degree'] == pytest.approx(0.375 / 0.45)           # was 0.5
    assert judged('fit_quality', fit_r_squared=0.8)['status'] == 'supported' and judged('fit_quality', fit_r_squared=0.8)['degree'] == pytest.approx(0.3 / 0.45)   # was conflicting: usual scatter of pooled cell data
    assert judged('fit_quality', fit_r_squared=0.6)['degree'] == pytest.approx(0.1 / 0.45)
    assert judged('fit_quality', fit_r_squared=0.5)['status'] == 'conflicting'
    assert judged('fit_quality', fit_r_squared=0.3)['status'] == 'conflicting'


def with_facts(rec, **answers):
    rec['facts'].update({name: fact(answer, ['span_' + name] if answer in ('yes', 'no') else []) for name, answer in answers.items()})
    return rec


def test_raw_ratios_are_judged_net_of_the_donor_only_background_when_it_is_stated():
    # raw pair 0.2, control 0.1: quotient 2 (degree 0.5); net of a donor-only 0.05 it is 3 (full credit)
    assert judged('signal_over_control', bret_ratio_pair=0.2, bret_ratio_negative_control=0.1)['degree'] == pytest.approx(0.5)
    raw = lambda **values: with_facts(record(**values), background_subtracted='no')
    assert judged('signal_over_control', raw(bret_ratio_pair=0.2, bret_ratio_negative_control=0.1, bret_ratio_donor_only=0.05))['degree'] == 1.0
    assert judged('signal_over_control', raw(bret_ratio_pair=0.2, bret_ratio_negative_control=0.1))['degree'] == pytest.approx(0.5)            # raw, no donor-only ratio: as stated (the old under-credit)
    assert judged('signal_over_control', with_facts(record(bret_ratio_pair=0.2, bret_ratio_negative_control=0.1, bret_ratio_donor_only=0.05), background_subtracted='yes'))['degree'] == pytest.approx(0.5)   # already net: unchanged
    assert judged('signal_over_control', with_facts(record(bret_ratio_pair=0.2, bret_ratio_negative_control=0.1, bret_ratio_donor_only=0.05), background_subtracted='unknown'))['degree'] == pytest.approx(0.5)
    assert judged('signal_over_control', raw(bret_ratio_pair=0.2, bret_ratio_negative_control=0.1, bret_ratio_donor_only=0.25))['status'] == 'conflicting'      # no more than the donor alone: no net signal
    assert judged('signal_over_control', raw(bret_ratio_pair=0.12, bret_ratio_negative_control=0.06, bret_ratio_donor_only=0.07))['degree'] == 1.0            # the control is no larger than the donor alone: no net control signal
    degrees = [judged('signal_over_control', raw(bret_ratio_pair=0.2, bret_ratio_negative_control=0.1, bret_ratio_donor_only=donor))['degree'] for donor in (0.01, 0.03, 0.04, 0.05)]   # the more of the control the donor-only background accounts for, the larger the net quotient
    assert degrees == sorted(degrees) and 0 < degrees[0] < degrees[-1] <= 1


def test_the_stated_spreads_of_the_ratios_add_the_paper_s_own_noise_to_the_quotient():
    assert judged('signal_over_control', spread_kind='standard_error', bret_ratio_pair_spread=0.05, bret_ratio_negative_control_spread=0.01)['degree'] == 1.0       # a gap of about 5 standard errors
    weak = judged('signal_over_control', spread_kind='standard_error', bret_ratio_pair_spread=0.15, bret_ratio_negative_control_spread=0.05)
    assert weak['status'] == 'supported' and weak['degree'] == pytest.approx((0.25 / math.hypot(0.15, 0.05) - 1) / 2)                                              # the quotient 6 is full; the noise lowers it
    assert judged('signal_over_control', spread_kind='standard_error', bret_ratio_pair_spread=0.3, bret_ratio_negative_control_spread=0.05)['status'] == 'conflicting'  # the gap is within one standard error
    sd = judged('signal_over_control', spread_kind='standard_deviation', bret_ratio_pair_spread=0.15, bret_ratio_negative_control_spread=0.05)
    assert sd['degree'] == pytest.approx((0.25 / math.hypot(0.15 / math.sqrt(3), 0.05 / math.sqrt(3)) - 1) / 2)                                # sd / sqrt(n) over three independent experiments
    for kwargs in ({'spread_kind': 'confidence_interval'}, {'spread_kind': None}, {'spread_kind': 'standard_error', 'bret_ratio_negative_control_spread': None}):
        assert judged('signal_over_control', bret_ratio_pair_spread=0.3, **{'bret_ratio_negative_control_spread': 0.05, **kwargs})['degree'] == 1.0                  # a spread of unusable kind or of one only is not used
    degrees = [judged('signal_over_control', spread_kind='standard_error', bret_ratio_pair_spread=value, bret_ratio_negative_control_spread=0.05)['degree'] for value in (0.24, 0.2, 0.15, 0.1, 0.05)]
    assert degrees == sorted(degrees) and 0 < degrees[0] < degrees[-1] == 1.0
    assert judged('bret50_specificity', spread_kind='standard_error', bret50_spread=0.1, bret50_negative_control_spread=0.5)['degree'] == 1.0                         # 20 percent each: z about 5.7
    noisy = judged('bret50_specificity', spread_kind='standard_error', bret50_spread=0.3, bret50_negative_control_spread=1.5)
    assert noisy['degree'] == pytest.approx((math.log(5) / math.hypot(0.6, 0.6) - 1) / 2)                                                                        # the same quotient 5 over a 60 percent scatter
    assert judged('bret50_specificity', spread_kind='standard_error', bret50_spread=1.0, bret50_negative_control_spread=5.0)['status'] == 'conflicting'                # a fold of 5 inside a 200 percent scatter (z 0.57)
    degrees = [judged('bret50_specificity', spread_kind='standard_error', bret50_spread=0.5 * f, bret50_negative_control_spread=2.5 * f)['degree'] for f in (0.8, 0.5, 0.3, 0.2)]   # a smaller scatter never lowers
    assert degrees == sorted(degrees) and 0 < degrees[0] < degrees[-1] == 1.0


def test_the_bystander_tests_are_supported_by_either_fact_and_fail_on_a_stated_no():
    both = lambda a, b: judged('bystander_test', with_facts(record(), hyperbola_preferred_over_linear=a, bret_constant_across_expression=b))
    assert both('yes', 'yes') == {'status': 'supported', 'support_refs': ['span_hyperbola_preferred_over_linear', 'span_bret_constant_across_expression']}
    assert both('yes', 'unknown')['status'] == 'supported' and both('unknown', 'yes')['status'] == 'supported'     # one test is enough: the other unstated does not make it unknown
    assert both('no', 'yes')['status'] == 'conflicting' and both('unknown', 'no')['status'] == 'conflicting'      # the paper itself states it fails
    assert both('unknown', 'unknown') == {'status': 'unknown', 'support_refs': []}
    interpretations = convert_bret(grade_bret(with_facts(record(), hyperbola_preferred_over_linear='unknown', bret_constant_across_expression='unknown')))['extraction']['interpretations']
    assert interpretations['background_alternatives']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'supported'   # unstated tests do not lower the controls


def test_the_tracer_regime_for_a_ki_is_full_at_the_researched_quotient_and_falls_in_log_steps_to_no_credit():
    judged_ratio = lambda ratio, **values: judged('tracer_regime', ki=50.0, tracer_kd=50.0, tracer_concentration=50.0 * ratio, **values)
    assert judged_ratio(0.1)['degree'] == 1.0 and judged_ratio(1.0)['degree'] == 1.0
    assert judged_ratio(2.0)['degree'] == pytest.approx(1 - math.log10(2))                                           # one step above the KD: partial credit, no step
    assert judged_ratio(10.0)['status'] == 'supported' and judged_ratio(10.0)['degree'] == 0.0 and judged_ratio(100.0)['degree'] == 0.0     # never conflicting
    degrees = [judged_ratio(ratio)['degree'] for ratio in (8.0, 5.0, 3.0, 2.0, 1.2, 1.0, 0.5)]
    assert degrees == sorted(degrees) and 0 < degrees[0] < degrees[-1] == 1.0
    assert judged('tracer_regime', ki=50.0, tracer_concentration=50.0) == {'status': 'unknown', 'support_refs': []}   # the tracer KD is not stated: unknown, not 0
    assert grade_bret(record())['criteria']['tracer_regime']['status'] == 'not_applicable'                            # no Ki: not applicable
    converted = convert_bret(grade_bret(record(ki=50.0, tracer_kd=50.0, tracer_concentration=100.0)))['extraction']['interpretations']
    assert converted['binding_regime']['degree'] == pytest.approx(1 - math.log10(2))


def test_with_the_value_not_stated_the_judgement_is_unknown_not_zero():
    for name, field in (('titration_points', 'titration_point_count'), ('replicates', 'replicate_count'), ('fit_quality', 'fit_r_squared'), ('signal_over_control', 'bret_ratio_negative_control'), ('bret50_specificity', 'bret50_negative_control'), ('ratio_range', 'ratio_highest')):
        assert judged(name, **{field: None}) == {'status': 'unknown', 'support_refs': []}
    rec = record(replicate_count=2.0)
    rec['facts']['independent_experiments'] = fact('unknown')
    assert judged('replicates', rec) == {'status': 'unknown', 'support_refs': []}              # the count is not known to be of independent experiments
    rec['facts']['independent_experiments'] = fact('no', ['s'])
    assert judged('replicates', rec)['status'] == 'conflicting'                                # a stated no is a fact of the record


def test_support_lowers_the_degree_and_never_changes_a_status():
    weak = record(titration_point_count=4.0)
    weak['quantities']['titration_point_count'] = point(4.0, 'count', 'titration_point_count', ['s'], support='implied')
    direct = record(titration_point_count=4.0)
    weak_i, direct_i = (convert_bret(grade_bret(r))['extraction']['interpretations'] for r in (weak, direct))
    assert direct_i['binding_regime']['degree'] == pytest.approx(2 / 6)
    assert weak_i['binding_regime']['degree'] == pytest.approx(2 / 6 * 0.7)
    assert {k: v['status'] for k, v in weak_i.items()} == {k: v['status'] for k, v in direct_i.items()}


def test_a_standard_deviation_over_two_independent_experiments_now_gives_a_variance():
    converted = convert_bret(grade_bret(record(spread_kind='standard_deviation', kd=50.0, kd_spread=10.0, replicate_count=2.0)))
    assert converted['extraction']['quantities']['effect']['value'] == 50.0
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(100.0 / 2)
    assert converted['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(math.sqrt(2 / 3))
    assert converted['direction_field_support'] == 'direct' and 'qualitative_effect' not in converted


def test_the_statement_is_detected_not_detected_or_not_stated():
    rec = record()
    assert convert_bret(grade_bret(rec))['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_interaction_detected'], 'signal_over_control': pytest.approx(6.0)}
    rec['facts']['interaction_detected'] = fact('no', ['s'])
    assert convert_bret(grade_bret(rec))['qualitative_effect']['statement'] == 'interaction_not_detected'
    rec['facts']['interaction_detected'] = fact('unknown')
    converted = convert_bret(grade_bret(rec))
    assert converted['qualitative_effect']['statement'] == 'interaction_not_stated' and converted['direction_field_support'] is None
    assert converted['extraction']['quantities']['effect'] is None and converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant'


def test_every_number_a_judge_uses_is_a_named_expert_review_constant():
    tree = ast.parse(inspect.getsource(converter))
    in_functions = {node.value for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef) for node in ast.walk(fn) if isinstance(node, ast.Constant) and type(node.value) in (int, float)}
    assert in_functions <= {0, 1}
    lines = inspect.getsource(converter).splitlines()
    numeric = [node for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and type(node.value.value) in (int, float)]
    assert numeric and all('# EXPERT_REVIEW:' in lines[node.lineno - 1] for node in numeric)
