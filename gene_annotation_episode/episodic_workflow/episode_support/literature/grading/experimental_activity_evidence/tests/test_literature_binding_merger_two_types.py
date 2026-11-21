"""First binding merger with two experiment types: an SPR result and ITC results for the same binding statement.

Every expected number is worked by hand in the comment above it. All results
here use a standard error as the spread, so a result's variance is its spread
squared (SPR 2 nM -> 4, ITC 3 nM -> 9, ITC 4 nM -> 16).
"""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import convert_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import grade_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record


def spr(ref='spr_1', analyte='spr_analyte_1', immobilized='spr_ligand_1', kd=20.0, spread=2.0):
    return convert_spr(grade_spr(spr_record(experiment_ref=ref, analyte_prep=analyte, immobilized_prep=immobilized, surface='spr_surface_' + ref, dataset='spr_data_' + ref, kd=kd, spread=spread)))


def itc(ref='itc_1', syringe='itc_syringe_1', cell='itc_cell_1', kd=30.0, spread=3.0):
    return convert_itc(grade_itc(itc_record(experiment_ref=ref, syringe_prep=syringe, cell_prep=cell, dataset='itc_data_' + ref, kd=kd, spread=spread)))


def test_a_spr_and_itc_on_different_preparations_are_two_independent_groups():
    row = merge_binding([spr(kd=20.0, spread=2.0), itc(kd=30.0, spread=3.0)])
    # variances 4 (SPR) and 9 (ITC); weights 1/4 and 1/9; sum of weights = 13/36
    # effect = (20 x 1/4 + 30 x 1/9) / (13/36) = (5 + 10/3) / (13/36) = 300/13 = 23.0769 nM
    # variance = 1 / (13/36) = 36/13 = 2.7692 nM^2; precision = 13/36 = 0.36111
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(300 / 13)
    assert row['cells']['effect_variance']['value'] == pytest.approx(36 / 13)
    assert row['cells']['effect_precision']['value'] == pytest.approx(13 / 36)
    assert row['experiment_types'] == ['itc', 'spr']
    assert row['group_experiment_types'] == [['spr'], ['itc']]


def test_b_spr_and_itc_sharing_an_analyte_preparation_are_one_dependent_group():
    shared_spr = spr(analyte='prep_shared')
    shared_itc = itc(syringe='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_spr, shared_itc])] == [['spr_1', 'itc_1']]
    row = merge_binding([shared_spr, shared_itc])
    # one group: effect = mean(20, 30) = 25 nM
    # variance = (mean of the standard errors)^2 = ((2 + 3) / 2)^2 = 6.25 nM^2, not 36/13: the second experiment
    # adds no independent information, and 6.25 is larger than the SPR-alone 4
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(25.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(6.25)
    assert row['cells']['effect_precision']['value'] == pytest.approx(0.16)
    assert row['experiment_types'] == ['itc', 'spr'] and row['group_experiment_types'] == [['itc', 'spr']]


def test_b2_the_same_preparation_in_the_other_role_is_still_one_preparation():
    # the SPR analyte is the ITC cell protein (the roles are swapped between the two experiments)
    assert len(dependence_groups([spr(analyte='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([spr(immobilized='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([spr(), itc()])) == 2


def test_c_unknown_preparation_is_dependent():
    unknown_itc = itc(cell=None)
    assert len(dependence_groups([spr(), unknown_itc])) == 1
    row = merge_binding([spr(), unknown_itc])
    # one group of two: mean(20, 30) = 25; variance ((2 + 3) / 2)^2 = 6.25
    assert row['counts']['independent_groups'] == 1
    assert row['cells']['measured_effect']['value'] == pytest.approx(25.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(6.25)


def test_d_mixed_two_dependent_plus_one_independent():
    a = spr(ref='spr_a', analyte='prep_p1', kd=20.0, spread=2.0)
    b = itc(ref='itc_b', syringe='prep_p1', kd=30.0, spread=3.0)
    c = itc(ref='itc_c', syringe='prep_p3', cell='cell_c', kd=40.0, spread=4.0)
    row = merge_binding([a, b, c])
    # group 1 = {a, b}: effect 25, variance ((2 + 3) / 2)^2 = 6.25; group 2 = {c}: effect 40, variance 16
    # weights 1/6.25 = 0.16 and 1/16 = 0.0625; sum = 0.2225
    # effect = (0.16 x 25 + 0.0625 x 40) / 0.2225 = (4 + 2.5) / 0.2225 = 29.2135 nM
    # variance = 1 / 0.2225 = 4.4944 nM^2
    assert row['dependence_groups'] == [['spr_a', 'itc_b'], ['itc_c']]
    assert row['counts'] == {'experiments': 3, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(6.5 / 0.2225)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / 0.2225)
    assert row['experiment_types'] == ['itc', 'spr']
    assert row['group_experiment_types'] == [['itc', 'spr'], ['itc']]


def test_types_listed_are_only_those_that_contributed():
    no_effect = itc(ref='itc_no_kd')
    no_effect['sheet']['cells']['measured_effect'] = {**no_effect['sheet']['cells']['measured_effect'], 'value': None, 'status': 'unavailable', 'reasons': ['x']}
    row = merge_binding([spr(), no_effect])
    assert row['experiment_types'] == ['spr'] and 'itc_no_kd' in row['excluded']
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
