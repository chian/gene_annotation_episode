"""First binding merger: one input, and two inputs that share a preparation."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record


def converted(**kwargs):
    return convert_spr(grade_spr(synthetic_record(**kwargs)))


def test_one_input_gives_its_own_values():
    row = merge_binding([converted()])
    assert row['counts'] == {'experiments': 1, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == 20.0
    assert row['cells']['effect_variance']['value'] == pytest.approx(4.0)
    assert row['cells']['effect_precision']['value'] == pytest.approx(0.25)
    assert row['interpretations']['binding_controls'] == 'supported'
    assert 'condition_response' in row['unfilled_components']


def test_two_inputs_sharing_a_preparation_count_as_one_independent_group():
    a = converted(experiment_ref='exp_a', analyte_prep='prep_shared', immobilized_prep='lig_a', surface='surf_a', dataset='data_a', kd=20.0, spread=2.0)
    b = converted(experiment_ref='exp_b', analyte_prep='prep_shared', immobilized_prep='lig_b', surface='surf_b', dataset='data_b', kd=30.0, spread=2.0)
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([a, b])] == [['exp_a', 'exp_b']]
    row = merge_binding([a, b])
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == 25.0
    # fully dependent: the variance is not reduced by the second experiment
    assert row['cells']['effect_variance']['value'] == pytest.approx(4.0)
    single = merge_binding([a])
    assert row['cells']['effect_precision']['value'] == pytest.approx(single['cells']['effect_precision']['value'])


def test_independent_inputs_pool_by_inverse_variance():
    a = converted(experiment_ref='exp_a', analyte_prep='prep_1', immobilized_prep='lig_1', surface='s1', dataset='d1', kd=20.0, spread=2.0)
    b = converted(experiment_ref='exp_b', analyte_prep='prep_2', immobilized_prep='lig_2', surface='s2', dataset='d2', kd=30.0, spread=2.0)
    row = merge_binding([a, b])
    assert row['counts']['independent_groups'] == 2
    assert row['cells']['measured_effect']['value'] == pytest.approx(25.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(2.0)


def test_shared_surface_or_data_or_unknown_preparation_is_dependent():
    base = dict(analyte_prep='p1', immobilized_prep='l1', surface='s1', dataset='d1')
    other = dict(analyte_prep='p2', immobilized_prep='l2', surface='s2', dataset='d2')
    assert len(dependence_groups([converted(experiment_ref='a', **base), converted(experiment_ref='b', **{**other, 'surface': 's1'})])) == 1
    assert len(dependence_groups([converted(experiment_ref='a', **base), converted(experiment_ref='b', **{**other, 'dataset': 'd1'})])) == 1
    assert len(dependence_groups([converted(experiment_ref='a', **base), converted(experiment_ref='b', **{**other, 'analyte_prep': None})])) == 1
    assert len(dependence_groups([converted(experiment_ref='a', **base), converted(experiment_ref='b', **other)])) == 2


def test_missing_variance_in_a_group_is_never_zero():
    a = converted(experiment_ref='exp_a', analyte_prep='prep_1', immobilized_prep='lig_1', surface='s1', dataset='d1', kd=20.0, spread=2.0)
    b = converted(experiment_ref='exp_b', analyte_prep='prep_2', immobilized_prep='lig_2', surface='s2', dataset='d2', kd=30.0, spread=2.0)
    b['sheet']['cells']['effect_variance'] = {**b['sheet']['cells']['effect_variance'], 'value': None, 'status': 'unavailable', 'reasons': ['x']}
    row = merge_binding([a, b])
    assert row['cells']['measured_effect']['status'] == 'conditional'
    assert row['cells']['effect_variance']['value'] is None and row['cells']['effect_precision']['value'] is None
