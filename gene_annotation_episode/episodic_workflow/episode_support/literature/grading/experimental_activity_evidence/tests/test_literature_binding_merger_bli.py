"""First binding merger with BLI together with SPR and ITC for the same binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the
spread, so a result's variance is its spread squared (BLI 2 nM -> 4, SPR 3 nM -> 9, ITC 4 nM -> 16, BLI 5 nM -> 25).
"""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import convert_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import convert_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import grade_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import synthetic_record as bli_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record


def bli(ref='bli_1', analyte='bli_analyte_1', immobilized='bli_ligand_1', sensor=None, kd=20.0, spread=2.0):
    return convert_bli(grade_bli(bli_record(experiment_ref=ref, analyte_prep=analyte, immobilized_prep=immobilized, sensor=sensor or 'bli_sensor_' + ref, dataset='bli_data_' + ref, kd=kd, spread=spread)))


def spr(ref='spr_1', analyte='spr_analyte_1', immobilized='spr_ligand_1', kd=30.0, spread=3.0):
    return convert_spr(grade_spr(spr_record(experiment_ref=ref, analyte_prep=analyte, immobilized_prep=immobilized, surface='spr_surface_' + ref, dataset='spr_data_' + ref, kd=kd, spread=spread)))


def itc(ref='itc_1', syringe='itc_syringe_1', cell='itc_cell_1', kd=40.0, spread=4.0):
    return convert_itc(grade_itc(itc_record(experiment_ref=ref, syringe_prep=syringe, cell_prep=cell, dataset='itc_data_' + ref, kd=kd, spread=spread)))


def test_a_bli_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([bli(kd=20.0, spread=2.0), spr(kd=30.0, spread=3.0)])
    # variances 4 (BLI) and 9 (SPR); weights 1/4 and 1/9; sum of weights = 13/36
    # effect = (20 x 1/4 + 30 x 1/9) / (13/36) = (5 + 10/3) / (13/36) = 300/13 = 23.0769 nM
    # variance = 1 / (13/36) = 36/13 = 2.7692 nM^2; precision = 13/36 = 0.36111
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(300 / 13)
    assert row['cells']['effect_variance']['value'] == pytest.approx(36 / 13)
    assert row['cells']['effect_precision']['value'] == pytest.approx(13 / 36)
    assert row['experiment_types'] == ['bli', 'spr'] and row['group_experiment_types'] == [['bli'], ['spr']]


def test_bli_spr_and_itc_all_independent_are_three_groups():
    row = merge_binding([bli(kd=20.0, spread=2.0), spr(kd=30.0, spread=3.0), itc(kd=40.0, spread=4.0)])
    # variances 4, 9, 16; weights 1/4, 1/9, 1/16; sum = (36 + 16 + 9) / 144 = 61/144
    # effect = (20/4 + 30/9 + 40/16) / (61/144) = (5 + 10/3 + 5/2) / (61/144) = (65/6) x (144/61) = 1560/61 = 25.5738 nM
    # variance = 144/61 = 2.3607 nM^2
    assert row['counts'] == {'experiments': 3, 'independent_groups': 3}
    assert row['cells']['measured_effect']['value'] == pytest.approx(1560 / 61)
    assert row['cells']['effect_variance']['value'] == pytest.approx(144 / 61)
    assert row['experiment_types'] == ['bli', 'itc', 'spr']


def test_a_bli_and_an_spr_sharing_the_analyte_preparation_are_one_dependent_group():
    shared_bli, shared_spr = bli(analyte='prep_shared'), spr(analyte='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_bli, shared_spr])] == [['bli_1', 'spr_1']]
    row = merge_binding([shared_bli, shared_spr])
    # one group: effect = mean(20, 30) = 25 nM; variance = ((2 + 3) / 2)^2 = 6.25 nM^2, not 36/13
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(25.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(6.25)
    assert row['group_experiment_types'] == [['bli', 'spr']]


def test_the_bli_analyte_that_is_the_itc_cell_protein_is_one_preparation():
    assert len(dependence_groups([bli(analyte='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([bli(immobilized='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([bli(), itc()])) == 2


def test_two_bli_experiments_on_one_sensor_lot_are_dependent_and_different_sensors_are_not():
    one = bli(ref='a', sensor='lot_1')
    assert len(dependence_groups([one, bli(ref='b', analyte='ana_b', immobilized='lig_b', sensor='lot_1')])) == 1     # only the sensor lot is shared
    assert len(dependence_groups([one, bli(ref='b', analyte='ana_b', immobilized='lig_b', sensor='lot_2')])) == 2


def test_an_unknown_bli_preparation_is_dependent():
    unknown = bli(immobilized=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(20, 30) = 25; variance ((2 + 3) / 2)^2 = 6.25
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(25.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(6.25)


def test_mixed_two_dependent_plus_one_independent():
    a = bli(ref='bli_a', analyte='prep_p1', kd=20.0, spread=2.0)
    b = itc(ref='itc_b', syringe='prep_p1', kd=30.0, spread=3.0)
    c = bli(ref='bli_c', analyte='prep_p3', immobilized='lig_c', kd=40.0, spread=4.0)
    row = merge_binding([a, b, c])
    # group 1 = {a, b}: effect 25, variance ((2 + 3) / 2)^2 = 6.25; group 2 = {c}: effect 40, variance 16
    # weights 0.16 and 0.0625; sum 0.2225; effect = (0.16 x 25 + 0.0625 x 40) / 0.2225 = 6.5 / 0.2225 = 29.2135 nM
    assert row['dependence_groups'] == [['bli_a', 'itc_b'], ['bli_c']]
    assert row['cells']['measured_effect']['value'] == pytest.approx(6.5 / 0.2225)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / 0.2225)
    assert row['group_experiment_types'] == [['bli', 'itc'], ['bli']]


def test_a_bli_result_without_a_kd_is_excluded_and_its_type_is_not_listed():
    no_effect = bli(ref='bli_no_kd')
    no_effect['sheet']['cells']['measured_effect'] = {**no_effect['sheet']['cells']['measured_effect'], 'value': None, 'status': 'unavailable', 'reasons': ['x']}
    row = merge_binding([spr(), no_effect])
    assert row['experiment_types'] == ['spr'] and 'bli_no_kd' in row['excluded']


def test_the_row_interpretations_pool_the_bli_criteria_with_the_others():
    bad = bli(ref='bli_bad', analyte='bli_analyte_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([bli(), spr(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'
