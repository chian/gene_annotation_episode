"""Proximity-labeling converter: the researched EXPERT_REVIEW values are kept, the full-agreement -> zero-agreement ramps are kept (since the 2026-11-21 range review
the fold and the expression ratio ramp in the log, the false discovery rate stays linear), and the lone replicate minimum is softened (full credit at MIN_REPLICATES,
partial credit below it, no step), per A105_EXPERIMENT_SOP.md step 3.

The record is explicitly SYNTHETIC (not a publication); its numbers are those of the synthetic passage of forms/.../tests/proximity_passages.py: an APEX2 fusion
expressed at 1.5 times the endogenous bait, the candidate enriched 8.5-fold over the free-enzyme control at a false discovery rate of 0.8 percent, three
independent experiments, every control and check done.
"""
import ast
import inspect
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_proximity_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_proximity_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_proximity_converter import CRITERIA_MAP, JUDGES, MIN_REPLICATES, _criterion, convert_proximity
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_proximity_grader import CRITERIA, grade_proximity

STATED = {'enrichment_fold': (8.5, 'ratio'), 'enrichment_fdr': (0.8, 'percent'), 'bait_expression_ratio': (1.5, 'ratio'), 'labeling_time': (1.0, 'min'),
          'biotin_concentration': (500.0, 'uM'), 'peroxide_concentration': (1.0, 'mM'), 'replicate_count': (3, 'count')}


def synthetic_record():
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': 'exp_synthetic_proximity', 'source_ref': 'source_synthetic', 'assertion_ref': 'hypothesis_synthetic_proximity',
            'preparations': {'bait_preparation_ref': 'prep_bait', 'candidate_preparation_ref': 'prep_candidate', 'dataset_ref': 'dataset_proximity'},
            'quantities': {name: point(STATED[name][0], STATED[name][1], name, ['span_' + name]) for name in QUANTITIES},
            'ligase': 'apex2', 'fusion_site': 'c_terminal', 'cell_system': 'mammalian_cells', 'readout': 'western_blot_and_mass_spectrometry', 'quantification': 'label_free_intensity',
            'choice_support': dict.fromkeys(('ligase', 'fusion_site', 'cell_system', 'readout', 'quantification'), 'direct'),
            'facts': {name: fact('yes', ['span_' + name]) for name in FACTS},
            'spans': {'span_' + name: {'locator': 'synthetic', 'quote': 'synthetic fixture: ' + name} for name in (*QUANTITIES, *FACTS)}}


def judged(record, name):
    return _criterion(grade_proximity(record), name)


def with_quantity(name, value, unit=None):
    record = synthetic_record()
    record['quantities'][name] = point(value, unit or STATED[name][1], name, ['span_' + name])
    return record


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped))


def test_the_researched_values_are_kept_as_named_expert_review_constants():
    assert {name: getattr(literature_proximity_converter, name) for name in ('FOLD_FULL_AGREEMENT', 'FOLD_ZERO_AGREEMENT', 'FDR_FULL_AGREEMENT_PERCENT', 'FDR_ZERO_AGREEMENT_PERCENT',
                                                                             'EXPRESSION_FULL_AGREEMENT', 'EXPRESSION_ZERO_AGREEMENT', 'MIN_REPLICATES')} == {
        'FOLD_FULL_AGREEMENT': 4.0, 'FOLD_ZERO_AGREEMENT': 1.0, 'FDR_FULL_AGREEMENT_PERCENT': 1.0, 'FDR_ZERO_AGREEMENT_PERCENT': 10.0,
        'EXPRESSION_FULL_AGREEMENT': 2.0, 'EXPRESSION_ZERO_AGREEMENT': 10.0, 'MIN_REPLICATES': 3}
    source = inspect.getsource(literature_proximity_converter)
    numeric = [name for name, value in vars(literature_proximity_converter).items() if name.isupper() and isinstance(value, (int, float)) and not isinstance(value, bool)]
    for name in numeric:
        assert 'EXPERT_REVIEW' in next(line for line in source.splitlines() if line.startswith(name + ' = ')), name


def test_no_unexplained_inline_number_in_the_judges():
    numbers = {node.value for function in (*JUDGES.values(), literature_proximity_converter._degree) for node in ast.walk(ast.parse(inspect.getsource(function)))
               if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)}
    assert numbers <= {0, 1}


def test_the_synthetic_record_is_supported_everywhere_at_full_credit():
    converted = convert_proximity(grade_proximity(synthetic_record()))
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(CRITERIA_MAP, 'supported')
    for name in ('enrichment_magnitude', 'enrichment_significance', 'expression_level', 'replicates'):
        assert judged(synthetic_record(), name)['degree'] == pytest.approx(1.0), name
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_candidate_enriched'], 'fold_enrichment': 8.5}
    assert converted['extraction']['quantities']['effect'] is None and converted['direction_field_support'] == 'direct'


# (criterion, quantity, values from worse to better, all inside the supported range)
SWEEPS = (('enrichment_magnitude', 'enrichment_fold', (1.01, 1.5, 2.0, 3.0, 4.0, 8.5, 100.0)),
          ('enrichment_significance', 'enrichment_fdr', (9.9, 7.0, 5.0, 2.0, 1.0, 0.01)),
          ('expression_level', 'bait_expression_ratio', (9.9, 7.0, 4.0, 2.0, 1.5, 1.0)),
          ('replicates', 'replicate_count', (1, 2, 3, 5, 12)))


@pytest.mark.parametrize('criterion, quantity, values', SWEEPS)
def test_a_better_value_never_lowers_the_degree_and_the_degree_is_bounded(criterion, quantity, values):
    degrees = []
    for value in values:
        verdict = judged(with_quantity(quantity, value), criterion)
        assert verdict['status'] == 'supported' and verdict['support_refs']
        degrees.append(verdict['degree'])
    assert all(0 <= d <= 1 for d in degrees)
    assert degrees == sorted(degrees) and degrees[0] < degrees[-1]


def test_the_replicate_minimum_is_soft_full_credit_at_the_researched_value_partial_credit_just_below():
    degrees = {n: judged(with_quantity('replicate_count', n), 'replicates') for n in (1, 2, MIN_REPLICATES, MIN_REPLICATES + 1)}
    assert all(verdict['status'] == 'supported' and verdict['support_refs'] == ['span_replicate_count', 'span_independent_experiments'] for verdict in degrees.values())      # never conflicting below it
    assert degrees[MIN_REPLICATES]['degree'] == degrees[MIN_REPLICATES + 1]['degree'] == 1.0
    assert degrees[2]['degree'] == pytest.approx(math.sqrt(2 / 3)) and degrees[1]['degree'] == pytest.approx(math.sqrt(1 / 3))
    assert 0 < degrees[1]['degree'] < degrees[2]['degree'] < 1      # just below the researched value: partial credit, not 0 and not a step to conflicting
    assert degrees[2]['degree'] - degrees[1]['degree'] > degrees[MIN_REPLICATES]['degree'] - degrees[2]['degree']      # each further experiment adds less (an average's precision)


def test_the_kept_ramps_give_partial_credit_between_their_researched_limits():
    assert judged(with_quantity('enrichment_fold', 2.0), 'enrichment_magnitude')['degree'] == pytest.approx(0.5)      # the usual lower cut-off: half way in log2 fold
    assert judged(with_quantity('enrichment_fdr', 5.5), 'enrichment_significance')['degree'] == pytest.approx(0.5)
    assert judged(with_quantity('bait_expression_ratio', math.sqrt(20.0)), 'expression_level')['degree'] == pytest.approx(0.5)      # the geometric middle of 2 and 10
    for criterion, quantity, value in (('enrichment_magnitude', 'enrichment_fold', 3.9), ('enrichment_magnitude', 'enrichment_fold', 1.05), ('enrichment_significance', 'enrichment_fdr', 1.1),
                                       ('enrichment_significance', 'enrichment_fdr', 9.5), ('expression_level', 'bait_expression_ratio', 2.1), ('expression_level', 'bait_expression_ratio', 9.5)):
        assert 0 < judged(with_quantity(quantity, value), criterion)['degree'] < 1, (criterion, value)      # just inside either researched limit: partial, no step


def test_the_fold_and_the_expression_ratio_ramp_in_the_log_the_rate_in_the_rate():
    fold = {f: judged(with_quantity('enrichment_fold', f), 'enrichment_magnitude')['degree'] for f in (1.25, 1.5625, 2.0, 2.5, 3.125)}
    assert fold[1.5625] - fold[1.25] == pytest.approx(fold[3.125] - fold[2.5])      # the same factor of fold adds the same credit anywhere on the ramp
    assert fold[1.5625] == pytest.approx(math.log(1.5625) / math.log(4.0))
    expression = {r: judged(with_quantity('bait_expression_ratio', r), 'expression_level')['degree'] for r in (2.5, 3.125, 6.4, 8.0)}
    assert expression[2.5] - expression[3.125] == pytest.approx(expression[6.4] - expression[8.0])      # each equal factor of overexpression costs the same
    assert expression[2.5] == pytest.approx(math.log(10.0 / 2.5) / math.log(5.0))
    rate = {p: judged(with_quantity('enrichment_fdr', p), 'enrichment_significance')['degree'] for p in (2.0, 3.0, 8.0, 9.0)}
    assert rate[2.0] - rate[3.0] == pytest.approx(rate[8.0] - rate[9.0]) == pytest.approx(1 / 9)      # one point of false calls costs the same anywhere


def test_a_value_beyond_the_full_end_or_at_zero_needs_no_logarithm():
    assert judged(with_quantity('bait_expression_ratio', 0.0), 'expression_level')['degree'] == 1.0      # low expression costs sensitivity, not a false proximity
    assert judged(with_quantity('bait_expression_ratio', 0.3), 'expression_level')['degree'] == 1.0
    assert judged(with_quantity('enrichment_fold', 0.0), 'enrichment_magnitude')['status'] == 'conflicting'
    assert judged(with_quantity('enrichment_fdr', 0.0), 'enrichment_significance')['degree'] == 1.0


def test_the_log2_fold_and_the_fraction_rate_are_judged_as_their_ratio_and_percent():
    assert judged(with_quantity('enrichment_fold', 1.0, 'log2_ratio'), 'enrichment_magnitude')['degree'] == pytest.approx(0.5)      # twofold: log2 fold 1 of 2
    assert judged(with_quantity('enrichment_fold', 2.0, 'log2_ratio'), 'enrichment_magnitude')['degree'] == pytest.approx(1.0)      # fourfold
    assert judged(with_quantity('enrichment_fdr', 0.05, 'fraction'), 'enrichment_significance')['degree'] == pytest.approx(5 / 9)      # 5 percent


def test_conflicting_is_kept_where_the_record_states_a_value_at_or_beyond_the_zero_agreement_limit_or_a_no():
    assert judged(with_quantity('enrichment_fold', 1.0), 'enrichment_magnitude')['status'] == 'conflicting'          # no more than the paper's own control
    assert judged(with_quantity('enrichment_fold', 0.5), 'enrichment_magnitude')['status'] == 'conflicting'
    assert judged(with_quantity('enrichment_fdr', 10.0), 'enrichment_significance')['status'] == 'conflicting'
    assert judged(with_quantity('bait_expression_ratio', 10.0), 'expression_level')['status'] == 'conflicting'
    record = synthetic_record()
    record['facts']['independent_experiments'] = fact('no', ['span_independent_experiments'])
    assert judged(record, 'replicates')['status'] == 'conflicting'      # the grader's own: independence stated no


def test_with_nothing_to_compare_the_result_is_unknown_not_zero():
    record = synthetic_record()
    record['facts']['independent_experiments'] = fact('unknown')
    assert judged(record, 'replicates') == {'status': 'unknown', 'support_refs': []}
    record = synthetic_record()
    record['quantities']['replicate_count'] = {**record['quantities']['replicate_count'], 'status': 'unavailable', 'value': None}
    assert judged(record, 'replicates') == {'status': 'unknown', 'support_refs': []}
    record = synthetic_record()
    record['quantities']['enrichment_fold'] = {**record['quantities']['enrichment_fold'], 'status': 'unavailable', 'value': None}
    assert judged(record, 'enrichment_magnitude') == {'status': 'unknown', 'support_refs': []}


def test_support_lowers_the_degree_and_never_changes_a_status():
    direct = convert_proximity(grade_proximity(synthetic_record()))['extraction']['interpretations']['sampling_basis']
    record = synthetic_record()
    record['quantities']['replicate_count']['support'] = 'implied'
    implied = convert_proximity(grade_proximity(record))['extraction']['interpretations']['sampling_basis']
    assert implied['status'] == direct['status'] == 'supported' and implied['degree'] < direct['degree']
    record = with_quantity('enrichment_fold', 1.0)
    record['quantities']['enrichment_fold']['support'] = 'about_something_else'
    assert convert_proximity(grade_proximity(record))['extraction']['interpretations']['binding_parameter_definition']['status'] == 'conflicting'


def test_the_statement_is_detected_not_detected_or_not_stated():
    record = synthetic_record()
    record['facts']['candidate_enriched'] = fact('no', ['span_candidate_enriched'])
    assert convert_proximity(grade_proximity(record))['qualitative_effect']['statement'] == 'interaction_not_detected'
    record['facts']['candidate_enriched'] = fact('unknown')
    converted = convert_proximity(grade_proximity(record))
    assert converted['qualitative_effect']['statement'] == 'interaction_not_stated' and converted['direction_field_support'] is None


def with_matched(answer):
    record = synthetic_record()
    record['facts']['fold_over_matched_control'] = fact(answer, ['span_fold_over_matched_control']) if answer != 'unknown' else fact('unknown')
    return record


def test_a_fold_over_an_unmatched_control_needs_more_enrichment_for_full_credit_gradually():
    folds = [1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0]
    matched = [judged(with_quantity_matched('yes', f), 'enrichment_magnitude')['degree'] for f in folds]
    unmatched = [judged(with_quantity_matched('no', f), 'enrichment_magnitude')['degree'] for f in folds]
    assert matched == sorted(matched) and unmatched == sorted(unmatched)      # monotone
    assert all(0 < u <= m <= 1 for u, m in zip(unmatched, matched))      # never raises the degree, never a step to 0 or conflicting
    assert matched[3] == 1.0 and 0.5 < unmatched[3] < 1.0 and unmatched[5] == 1.0      # fourfold: full over a matched control, partial over an unmatched one; eightfold: full
    unknown = [judged(with_quantity_matched('unknown', f), 'enrichment_magnitude')['degree'] for f in folds]
    assert unknown == matched      # silence about the control changes nothing


def with_quantity_matched(answer, fold):
    record = with_matched(answer)
    record['quantities']['enrichment_fold'] = point(fold, 'ratio', 'enrichment_fold', ['span_enrichment_fold'])
    return record


def test_a_candidate_stated_not_enriched_is_a_stated_result_and_the_magnitude_and_significance_do_not_apply():
    record = synthetic_record()
    record['facts']['candidate_enriched'] = fact('no', ['span_candidate_enriched'])
    record['quantities']['enrichment_fold'] = point(1.0, 'ratio', 'enrichment_fold', ['span_enrichment_fold'])
    graded = grade_proximity(record)
    assert graded['criteria']['proximity_observed']['status'] == 'supported' and graded['reasons']['proximity_observed'] == 'candidate_enrichment_stated'
    assert graded['criteria']['enrichment_magnitude']['status'] == graded['criteria']['enrichment_significance']['status'] == 'not_applicable'
    interpretation = convert_proximity(graded)['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported'      # only the orthogonal validation remains: the negative result does not make the definition conflicting
    record['facts']['candidate_enriched'] = fact('unknown')
    assert grade_proximity(record)['criteria']['proximity_observed']['status'] == 'unknown'
