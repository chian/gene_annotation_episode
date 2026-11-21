"""Y2H converter: the qualitative effect, the empty sheet cells, the reporter-fold ramp (researched ends kept, linear in log fold since the range review) and the softened
replicate count (owner rule, A105_EXPERIMENT_SOP.md step 3: researched values kept, made gradual around them, no pass/fail cut-off)."""
import ast
import inspect
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_y2h_record import FACTS, QUANTITIES, UNITS, VERSION, fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_y2h_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_y2h_converter import CRITERIA_MAP, MIN_REPLICATES, REPORTER_FOLD_FULL_AGREEMENT, REPORTER_FOLD_ZERO_AGREEMENT, _criterion, convert_y2h
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_y2h_grader import grade_y2h

REF = 'span_exp_synthetic_y2h_1'
VALUES = {'three_at_concentration': 5.0, 'bait_alone_three_at_concentration': 2.5,'beta_galactosidase_interaction': 142.0, 'beta_galactosidase_negative_control': 3.1, 'beta_galactosidase_positive_control': 160.0, 'incubation_temperature': 30.0, 'incubation_time': 4.0, 'replicate_count': 3}


def synthetic_record():
    """A built record stating every field (the values of the synthetic passage of y2h_passages)."""
    return {'version': VERSION, 'experiment_type': 'y2h', 'experiment_ref': 'exp_synthetic_y2h_1', 'source_ref': 'source_synthetic', 'assertion_ref': 'hypothesis_synthetic_interaction',
            'preparations': {'bait_preparation_ref': 'prep_bait_a', 'prey_preparation_ref': 'prep_prey_a', 'dataset_ref': 'dataset_y2h_1'},
            'quantities': {name: point(VALUES[name], UNITS[name][-1 if name == 'incubation_time' else 0], name, [REF], name) if name in VALUES else unavailable(UNITS[name][0], name, 'not_stated_in_passage') for name in QUANTITIES},      # the spreads and the growth dilutions are unstated unless a test sets them
            'system_kind': 'y2h', 'bait_fusion_domain': 'gal4_dbd', 'prey_fusion_domain': 'gal4_ad', 'yeast_strain': 'ah109', 'selective_medium_scored': 'minus_histidine_and_adenine',
            'choice_support': dict.fromkeys(('system_kind', 'bait_fusion_domain', 'prey_fusion_domain', 'yeast_strain', 'selective_medium_scored'), 'direct'),
            'facts': {name: fact('yes', [REF]) for name in FACTS}, 'spans': {REF: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}}


def with_activities(pair, control, support='direct'):
    record = synthetic_record()
    record['quantities']['beta_galactosidase_interaction'] = point(pair, 'Miller_units', 'pair', ['s'], support=support)
    record['quantities']['beta_galactosidase_negative_control'] = point(control, 'Miller_units', 'control', ['s'])
    return record


def with_replicates(count, independent='yes'):
    record = synthetic_record()
    record['quantities']['replicate_count'] = point(count, 'count', 'replicates', ['s'])
    record['facts']['independent_experiments'] = fact(independent, [REF] if independent != 'unknown' else [])
    return record


def judged(record, criterion):
    return _criterion(grade_y2h(record), criterion)


def credit(verdict):
    """The credit of a supported verdict: its degree, or full credit (1.0) when it carries none."""
    assert verdict['status'] == 'supported'
    return verdict.get('degree', 1.0)


def interpretations(record):
    return convert_y2h(grade_y2h(record))['extraction']['interpretations']


def test_a_y2h_has_no_effect_and_no_variance_but_a_qualitative_effect_and_the_output_keeps_its_shape():
    converted = convert_y2h(grade_y2h(synthetic_record()))
    assert set(converted) == {'version', 'experiment_type', 'experiment_ref', 'source_ref', 'dependence', 'extraction', 'sheet', 'qualitative_effect', 'direction_field_support', 'null_components'}
    assert converted['extraction']['quantities']['effect'] is None and converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': [REF], 'reporter_fold': pytest.approx(142.0 / 3.1)}
    assert converted['direction_field_support'] == 'direct'
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_prey_a', 'immobilized_preparation_ref': 'prep_bait_a', 'surface_ref': None, 'dataset_ref': 'dataset_y2h_1'}
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(CRITERIA_MAP, 'supported')


def test_the_researched_values_are_kept_as_named_constants_and_the_judges_use_no_other_number():
    assert (REPORTER_FOLD_FULL_AGREEMENT, REPORTER_FOLD_ZERO_AGREEMENT, MIN_REPLICATES) == (10.0, 2.0, 3)
    source = inspect.getsource(literature_y2h_converter)
    for name in ('REPORTER_FOLD_FULL_AGREEMENT', 'REPORTER_FOLD_ZERO_AGREEMENT', 'MIN_REPLICATES', 'SPREAD_Z_FULL', 'GROWTH_TITRE_FULL_AGREEMENT', 'GROWTH_TITRE_ZERO_AGREEMENT', 'ONE_OF_TWO_SHARE'):
        assert '# EXPERT_REVIEW:' in next(line for line in source.splitlines() if line.startswith(name + ' = '))
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    numbers = {node.value for function in functions for node in ast.walk(function) if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)}
    assert numbers <= {0, 1}      # 0 and full credit only; every researched number is a named constant


def log_credit(fold):
    """The range-reviewed shape: linear in the log of the fold from the conflicting 2 to the full 10."""
    return math.log(fold / 2.0) / math.log(10.0 / 2.0)


def test_the_reporter_fold_ramp_keeps_its_ends_full_from_ten_falling_linearly_in_log_fold_to_the_conflicting_two():
    assert credit(judged(with_activities(10.0, 1.0), 'reporter_fold')) == pytest.approx(1.0)
    assert credit(judged(with_activities(100.0, 1.0), 'reporter_fold')) == pytest.approx(1.0)
    assert judged(with_activities(6.0, 1.0), 'reporter_fold') == {'status': 'supported', 'support_refs': ['s'], 'degree': pytest.approx(log_credit(6.0))}      # 0.68, was 0.5 linear in the fold
    assert credit(judged(with_activities(20.0 ** 0.5, 1.0), 'reporter_fold')) == pytest.approx(0.5)      # the geometric middle of 2 and 10 is half credit
    assert credit(judged(with_activities(9.5, 1.0), 'reporter_fold')) == pytest.approx(log_credit(9.5))      # just below the researched ten-fold: partial credit, no step
    assert 0 < credit(judged(with_activities(2.05, 1.0), 'reporter_fold')) < 0.05      # just above the zero end: low partial credit, no step
    for pair, control in ((2.0, 1.0), (3.0, 3.0), (2.0, 4.0)):
        assert judged(with_activities(pair, control), 'reporter_fold') == {'status': 'conflicting', 'support_refs': ['s']}


def test_equal_ratio_steps_of_the_fold_count_equally_so_the_curve_is_steep_in_fold_near_the_noise_and_gentle_near_ten():
    step = [credit(judged(with_activities(2 * low, 1.0), 'reporter_fold')) - credit(judged(with_activities(low, 1.0), 'reporter_fold')) for low in (2.5, 4.0)]
    assert step[0] == pytest.approx(step[1]) == pytest.approx(math.log(2) / math.log(5))      # 2.5 -> 5 and 4 -> 8 are both a doubling
    near_noise = credit(judged(with_activities(3.0, 1.0), 'reporter_fold')) - credit(judged(with_activities(2.5, 1.0), 'reporter_fold'))
    near_full = credit(judged(with_activities(10.0, 1.0), 'reporter_fold')) - credit(judged(with_activities(9.5, 1.0), 'reporter_fold'))
    assert near_noise > 3 * near_full      # the same half-fold step matters far more just out of the noise


def test_the_positive_control_window_does_not_rescale_the_fold():
    """Range review Q3: the positive control shows the reporter's sensitivity, not the background noise the fold is judged against."""
    weak, strong = with_activities(6.0, 1.0), with_activities(6.0, 1.0)
    weak['quantities']['beta_galactosidase_positive_control'] = point(5.0, 'Miller_units', 'positive', ['p'])
    strong['quantities']['beta_galactosidase_positive_control'] = point(500.0, 'Miller_units', 'positive', ['p'])
    assert judged(weak, 'reporter_fold') == judged(strong, 'reporter_fold') == {'status': 'supported', 'support_refs': ['s'], 'degree': pytest.approx(log_credit(6.0))}


def test_a_larger_fold_never_lowers_the_credit_and_a_higher_background_never_raises_it():
    credits = [credit(judged(with_activities(pair, 1.0), 'reporter_fold')) for pair in (2.1, 3.0, 5.0, 9.0, 9.9, 10.0, 50.0)]
    assert all(0 <= c <= 1 for c in credits) and credits == sorted(credits)
    worse = [credit(judged(with_activities(20.0, control), 'reporter_fold')) for control in (0.5, 2.0, 4.0, 8.0, 9.5)]
    assert worse == sorted(worse, reverse=True)


def test_a_replicate_count_just_below_the_researched_three_gets_partial_credit_not_a_fail():
    assert judged(with_replicates(2), 'replicates') == {'status': 'supported', 'support_refs': ['s', REF], 'degree': pytest.approx((2 / 3) ** 0.5)}      # sqrt(n / 3), the precision of the mean
    assert judged(with_replicates(1), 'replicates') == {'status': 'supported', 'support_refs': ['s', REF], 'degree': pytest.approx((1 / 3) ** 0.5)}
    assert judged(with_replicates(3), 'replicates') == {'status': 'supported', 'support_refs': ['s', REF]}      # full credit at the researched value: no degree, as before
    assert judged(with_replicates(8), 'replicates') == {'status': 'supported', 'support_refs': ['s', REF]}


def test_more_independent_experiments_never_lower_the_credit():
    credits = [credit(judged(with_replicates(count), 'replicates')) for count in (1, 2, 3, 4, 10)]
    assert all(0 < c <= 1 for c in credits) and credits == sorted(credits)
    assert credits[0] < credits[1] < credits[2] == credits[-1]


def test_unknown_when_the_paper_gives_nothing_to_judge_and_conflicting_only_for_a_stated_no():
    for count in (1, 12):
        assert judged(with_replicates(count, 'unknown'), 'replicates') == {'status': 'unknown', 'support_refs': []}      # the count alone does not say independent
    assert judged(with_replicates(5, 'no'), 'replicates') == {'status': 'conflicting', 'support_refs': ['s', REF]}      # the paper states it: the grader's fact
    record = synthetic_record()
    record['quantities']['beta_galactosidase_negative_control'] = {**record['quantities']['beta_galactosidase_negative_control'], 'value': None, 'status': 'unavailable', 'reason': 'not_stated_in_passage', 'source_refs': [], 'support': None}
    assert judged(record, 'reporter_fold') == {'status': 'unknown', 'support_refs': []}


def test_the_degree_travels_into_the_sheet_criterion_and_is_the_weakest_member_degree():
    found = interpretations(synthetic_record())
    assert found['binding_parameter_definition']['degree'] == pytest.approx(1.0)
    assert 'degree' not in found['sampling_basis'] and 'degree' not in found['binding_controls'] and 'degree' not in found['binding_species']
    converted = convert_y2h(grade_y2h(with_activities(6.0, 1.0)))
    assert converted['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(log_credit(6.0))
    assert converted['sheet']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(log_credit(6.0))
    assert interpretations(with_replicates(2))['sampling_basis'] == {'status': 'supported', 'support_refs': ['s', REF], 'degree': pytest.approx((2 / 3) ** 0.5)}
    verdict = interpretations(with_activities(1.0, 2.0))['binding_parameter_definition']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict


def test_the_support_degree_lowers_the_degree_and_never_changes_a_status():
    verdict = interpretations(with_activities(6.0, 1.0, support='implied'))['binding_parameter_definition']
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(log_credit(6.0) * 0.7)
    verdict = interpretations(with_activities(1.0, 2.0, support='about_something_else'))['binding_parameter_definition']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = with_replicates(2)
    record['quantities']['replicate_count']['support'] = 'implied'
    assert interpretations(record)['sampling_basis']['degree'] == pytest.approx((2 / 3) ** 0.5 * 0.7)
    record = with_replicates(3, 'unknown')
    record['quantities']['replicate_count']['support'] = 'implied'
    assert interpretations(record)['sampling_basis'] == {'status': 'unknown', 'support_refs': []}


# ---- the gap pass (2026-11-21): spread, growth titre, 3-AT of the bait-alone test, stated no of the controls, stated negative ----

def with_spread(pair, control, **spread):
    record = with_activities(pair, control)
    for name, value in spread.items():
        record['quantities']['beta_galactosidase_' + name] = point(value, 'Miller_units', name, ['sp_' + name])
    return record


def with_titre(pair, control, activities=False):
    record = synthetic_record()
    record['quantities']['growth_dilution_interaction'] = point(pair, 'dilution_factor', 'dp', ['tp'])
    record['quantities']['growth_dilution_negative_control'] = point(control, 'dilution_factor', 'dc', ['tc'])
    if not activities:
        for name in ('beta_galactosidase_interaction', 'beta_galactosidase_negative_control'):
            record['quantities'][name] = unavailable('Miller_units', name, 'not_stated_in_passage')
    return record


def test_a_stated_spread_limits_the_fold_degree_in_addition_and_a_larger_spread_never_raises_it():
    unspread = credit(judged(with_activities(20.0, 1.0), 'reporter_fold'))
    assert unspread == 1.0
    small = judged(with_spread(20.0, 1.0, interaction_sem=0.5), 'reporter_fold')      # fold 20, SE 20 * 0.5 / 20 = 0.5, distance (20 - 2) / 0.5 >> 2 standard errors: full
    assert credit(small) == 1.0 and set(small['support_refs']) == {'s', 'sp_interaction_sem'}
    large = judged(with_spread(20.0, 1.0, interaction_sem=10.0), 'reporter_fold')      # SE 10: distance 18 / 10 / 2 = 0.9
    assert credit(large) == pytest.approx(0.9)
    credits = [credit(judged(with_spread(20.0, 1.0, interaction_sem=error), 'reporter_fold')) for error in (0.1, 1.0, 5.0, 10.0, 30.0)]
    assert credits == sorted(credits, reverse=True) and all(0 <= c <= 1 for c in credits)
    assert 'sp_interaction_sem' in judged(with_spread(20.0, 1.0, interaction_sem=10.0), 'reporter_fold')['support_refs']


def test_a_stated_sd_is_divided_by_sqrt_of_the_count_and_a_sem_is_used_as_it_is_and_the_control_spread_counts_too():
    by_sem = credit(judged(with_spread(20.0, 1.0, interaction_sem=10.0 / math.sqrt(3)), 'reporter_fold'))
    by_sd = credit(judged(with_spread(20.0, 1.0, interaction_sd=10.0), 'reporter_fold'))      # count 3 in the synthetic record
    assert by_sd == pytest.approx(by_sem)
    only_pair = credit(judged(with_spread(20.0, 2.0, interaction_sem=2.0), 'reporter_fold'))
    both = credit(judged(with_spread(20.0, 2.0, interaction_sem=2.0, negative_control_sem=1.0), 'reporter_fold'))
    assert both < only_pair      # the control's own spread widens the fold's error
    assert judged(with_spread(20.0, 1.0, interaction_sem=1000.0), 'reporter_fold')['status'] == 'supported'      # a huge spread gives a low degree, never conflicting


def test_a_growth_only_result_is_judged_by_the_titre_ratio_on_a_log_ramp_and_the_fold_steps_aside():
    graded = grade_y2h(with_titre(1000.0, 10.0))
    assert graded['criteria']['reporter_fold']['status'] == 'not_applicable' and graded['reasons']['reporter_fold'] == 'growth_titre_is_the_readout'
    assert credit(_criterion(graded, 'growth_titre')) == 1.0      # a hundred-fold titre difference: full
    assert credit(judged(with_titre(10.0, 1.0), 'growth_titre')) == pytest.approx(0.5)      # one ten-fold step: half on the log ramp from 1 to 100
    assert 0 < credit(judged(with_titre(10.0, 9.0), 'growth_titre')) < 0.1
    assert judged(with_titre(10.0, 10.0), 'growth_titre')['status'] == 'conflicting'      # no further along the series than the negative control
    credits = [credit(judged(with_titre(pair, 10.0), 'growth_titre')) for pair in (11.0, 30.0, 100.0, 1000.0, 10000.0)]
    assert credits == sorted(credits) and all(0 <= c <= 1 for c in credits)
    assert interpretations(with_titre(1000.0, 10.0))['binding_parameter_definition']['status'] == 'supported'


def test_the_titre_is_not_applicable_when_the_activities_are_the_readout_and_unknown_when_neither_is_given():
    both = grade_y2h(with_titre(1000.0, 10.0, activities=True))
    assert both['criteria']['reporter_fold']['status'] == 'unknown' and both['criteria']['growth_titre']['status'] == 'unknown'      # both stated: both recorded
    assert grade_y2h(synthetic_record())['criteria']['growth_titre']['status'] == 'not_applicable'
    neither = synthetic_record()
    for name in ('beta_galactosidase_interaction', 'beta_galactosidase_negative_control'):
        neither['quantities'][name] = unavailable('Miller_units', name, 'not_stated_in_passage')
    graded = grade_y2h(neither)
    assert graded['criteria']['reporter_fold']['status'] == graded['criteria']['growth_titre']['status'] == 'unknown'
    assert interpretations(neither)['binding_parameter_definition']['status'] == 'unknown'


def with_bait_alone(bait_at, scoring_at):
    record = synthetic_record()
    record['quantities']['bait_alone_three_at_concentration'] = point(bait_at, 'mM', 'b', ['b3'])
    record['quantities']['three_at_concentration'] = point(scoring_at, 'mM', 's3', ['s3'])
    return record


def test_a_bait_alone_test_at_a_higher_3at_than_the_scoring_gets_partial_credit_by_the_ratio_and_otherwise_full_credit():
    for bait_at in (0.0001, 2.5, 5.0):
        verdict = judged(with_bait_alone(bait_at, 5.0), 'bait_autoactivation')
        assert verdict['status'] == 'supported' and 'degree' not in verdict      # at or below the scoring's stringency: full
    assert credit(judged(with_bait_alone(10.0, 5.0), 'bait_autoactivation')) == pytest.approx(0.5)
    credits = [credit(judged(with_bait_alone(bait_at, 5.0), 'bait_autoactivation')) for bait_at in (5.0, 5.1, 10.0, 50.0, 500.0)]
    assert credits == sorted(credits, reverse=True) and credits[1] > 0.95 and 0 < credits[-1] < 1      # gradual, never a step, never conflicting
    record = synthetic_record()
    record['quantities']['bait_alone_three_at_concentration'] = unavailable('mM', 'b', 'not_stated_in_passage')
    assert grade_y2h(record)['reasons']['bait_autoactivation'] == 'facts_answered_yes'      # not both stated: the fact alone, as before
    record = with_bait_alone(50.0, 5.0)
    record['facts']['bait_alone_inactive'] = fact('no', [REF])
    assert grade_y2h(record)['criteria']['bait_autoactivation']['status'] == 'conflicting'      # a stated autoactivation stays conflicting


def test_a_stated_no_of_the_reciprocal_orientation_or_of_the_second_reporter_is_partial_credit_never_conflicting():
    for fact_name, criterion in (('reciprocal_orientation_tested', 'reciprocal_orientation'), ('more_than_one_reporter_activated', 'reporter_concordance')):
        record = synthetic_record()
        record['facts'][fact_name] = fact('no', ['r1'])
        graded = grade_y2h(record)
        assert graded['criteria'][criterion]['status'] == 'unknown' and graded['reasons'][criterion].endswith('_recorded_for_the_sheet')
        assert _criterion(graded, criterion) == {'status': 'supported', 'support_refs': ['r1'], 'degree': 0.5}
        for answer in ('unknown', 'not_applicable'):
            record['facts'][fact_name] = fact(answer, [])
            assert grade_y2h(record)['reasons'][criterion] in ('fact_unknown', 'fact_not_applicable')
    record = synthetic_record()
    record['facts']['reciprocal_orientation_tested'] = fact('no', ['r1'])
    found = interpretations(record)['binding_controls']
    assert found['status'] == 'supported' and found['degree'] == 0.5 and 'r1' in found['support_refs']      # the weakest member's degree travels into the sheet criterion


def test_a_failed_positive_control_counts_against_a_negative_result_only_not_against_an_observed_interaction():
    record = synthetic_record()
    record['facts']['positive_control_done'] = fact('no', ['p1'])
    assert grade_y2h(record)['criteria']['positive_control']['status'] == 'unknown'
    assert _criterion(grade_y2h(record), 'positive_control') == {'status': 'supported', 'support_refs': ['p1']}      # the pair is stated to interact: its growth stands
    record['facts']['interaction_detected'] = fact('no', ['i1'])
    assert _criterion(grade_y2h(record), 'positive_control') == {'status': 'conflicting', 'support_refs': ['p1']}      # a negative from a system that did not work means nothing


def test_a_stated_negative_interaction_is_not_a_failed_quality_criterion_and_the_direction_carries_it():
    record = synthetic_record()
    record['facts']['interaction_detected'] = fact('no', ['i1'])
    record['quantities']['beta_galactosidase_interaction'] = point(2.0, 'Miller_units', 'pair', ['s'])      # a fold of 0.65: part of the negative result
    graded = grade_y2h(record)
    assert graded['criteria']['interaction_observed']['status'] == 'not_applicable' and graded['reasons']['interaction_observed'] == 'negative_statement_carried_by_the_direction'
    converted = convert_y2h(graded)
    assert converted['qualitative_effect']['statement'] == 'interaction_not_detected'
    assert converted['extraction']['interpretations']['binding_parameter_definition']['status'] == 'supported'      # the fold of a stated negative is not judged; the fold's 0.65 would otherwise have been conflicting
    assert interpretations(with_titre(10.0, 10.0))['binding_parameter_definition']['status'] == 'conflicting'      # the same ratio for a stated positive is still conflicting
    unstated = synthetic_record()
    unstated['facts']['interaction_detected'] = fact('unknown', [])
    assert grade_y2h(unstated)['reasons']['interaction_observed'] == 'fact_unknown'
