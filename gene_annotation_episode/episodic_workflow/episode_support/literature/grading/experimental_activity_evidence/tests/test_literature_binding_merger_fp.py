"""First binding merger with FP together with SPR, ITC, BLI and GCI for the same binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the
spread, so a result's variance is its spread squared (FP 6 nM -> 36, SPR 3 nM -> 9, ITC 4 nM -> 16, BLI 5 nM -> 25,
GCI 2 nM -> 4).
"""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import convert_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import convert_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_grader import grade_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import convert_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_grader import grade_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import convert_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import grade_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import synthetic_record as bli_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import real_record as fp_real_record, synthetic_record as fp_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import synthetic_record as gci_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record


def fp(ref='fp_1', titrant='fp_titrant_1', tracer='fp_tracer_1', kd=60.0, spread=6.0):
    return convert_fp(grade_fp(fp_record(experiment_ref=ref, titrant_prep=titrant, tracer_prep=tracer, dataset='fp_data_' + ref, kd=kd, spread=spread)))


def gci(ref='gci_1', analyte='gci_analyte_1', immobilized='gci_ligand_1', kd=20.0, spread=2.0):
    return convert_gci(grade_gci(gci_record(experiment_ref=ref, analyte_prep=analyte, immobilized_prep=immobilized, chip='gci_chip_' + ref, dataset='gci_data_' + ref, kd=kd, spread=spread)))


def spr(ref='spr_1', analyte='spr_analyte_1', immobilized='spr_ligand_1', kd=30.0, spread=3.0):
    return convert_spr(grade_spr(spr_record(experiment_ref=ref, analyte_prep=analyte, immobilized_prep=immobilized, surface='spr_surface_' + ref, dataset='spr_data_' + ref, kd=kd, spread=spread)))


def itc(ref='itc_1', syringe='itc_syringe_1', cell='itc_cell_1', kd=40.0, spread=4.0):
    return convert_itc(grade_itc(itc_record(experiment_ref=ref, syringe_prep=syringe, cell_prep=cell, dataset='itc_data_' + ref, kd=kd, spread=spread)))


def bli(ref='bli_1', analyte='bli_analyte_1', immobilized='bli_ligand_1', kd=50.0, spread=5.0):
    return convert_bli(grade_bli(bli_record(experiment_ref=ref, analyte_prep=analyte, immobilized_prep=immobilized, sensor='bli_sensor_' + ref, dataset='bli_data_' + ref, kd=kd, spread=spread)))


def test_an_fp_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([fp(kd=60.0, spread=6.0), spr(kd=30.0, spread=3.0)])
    # variances 36 (FP) and 9 (SPR); weights 1/36 and 1/9; sum of weights = 5/36
    # effect = (60 / 36 + 30 / 9) / (5 / 36) = (5/3 + 10/3) / (5/36) = 5 x 36 / 5 = 36 nM
    # variance = 36 / 5 = 7.2 nM^2; precision = 5/36
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(36.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(7.2)
    assert row['cells']['effect_precision']['value'] == pytest.approx(5 / 36)
    assert row['experiment_types'] == ['fp', 'spr'] and row['group_experiment_types'] == [['fp'], ['spr']]


def test_fp_spr_itc_bli_and_gci_all_independent_are_five_groups():
    row = merge_binding([fp(), spr(), itc(), bli(), gci()])
    # variances 36, 9, 16, 25, 4; weights 1/36, 1/9, 1/16, 1/25, 1/4; sum = 0.027778 + 0.111111 + 0.0625 + 0.04 + 0.25 = 0.491389
    # numerator = 60/36 + 30/9 + 40/16 + 50/25 + 20/4 = 1.666667 + 3.333333 + 2.5 + 2 + 5 = 14.5
    weights = [1 / 36, 1 / 9, 1 / 16, 1 / 25, 1 / 4]
    assert row['counts'] == {'experiments': 5, 'independent_groups': 5}
    assert row['cells']['measured_effect']['value'] == pytest.approx(14.5 / sum(weights))
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / sum(weights))
    assert row['experiment_types'] == ['bli', 'fp', 'gci', 'itc', 'spr']


def test_an_fp_and_an_spr_sharing_the_titrant_preparation_are_one_dependent_group():
    shared_fp, shared_spr = fp(titrant='prep_shared'), spr(analyte='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_fp, shared_spr])] == [['fp_1', 'spr_1']]
    row = merge_binding([shared_fp, shared_spr])
    # one group: effect = mean(60, 30) = 45 nM; variance = ((6 + 3) / 2)^2 = 20.25 nM^2
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(45.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(20.25)
    assert row['group_experiment_types'] == [['fp', 'spr']]


def test_the_fp_titrant_or_tracer_that_is_an_itc_bli_or_gci_protein_is_one_preparation():
    assert len(dependence_groups([fp(titrant='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([fp(tracer='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([fp(titrant='prep_shared'), bli(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([fp(tracer='prep_shared'), gci(analyte='prep_shared')])) == 1
    assert len(dependence_groups([fp(), itc(), bli(), gci()])) == 4


def test_two_fp_experiments_with_the_same_tracer_are_dependent_and_none_have_a_surface():
    assert len(dependence_groups([fp(ref='a', tracer='tracer_1'), fp(ref='b', titrant='titrant_b', tracer='tracer_1')])) == 1
    assert len(dependence_groups([fp(ref='a', tracer='tracer_1'), fp(ref='b', titrant='titrant_b', tracer='tracer_2')])) == 2
    assert fp()['dependence']['surface_ref'] is None


def test_an_unknown_fp_preparation_is_dependent():
    unknown = fp(tracer=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(60, 30) = 45; variance ((6 + 3) / 2)^2 = 20.25
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(45.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(20.25)


def test_a_result_without_a_constant_is_excluded_and_its_type_is_not_listed():
    no_effect = fp(ref='fp_no_kd')
    no_effect['sheet']['cells']['measured_effect'] = {**no_effect['sheet']['cells']['measured_effect'], 'value': None, 'status': 'unavailable', 'reasons': ['x']}
    row = merge_binding([spr(), no_effect])
    assert row['experiment_types'] == ['spr'] and 'fp_no_kd' in row['excluded']


def test_the_row_interpretations_pool_the_fp_criteria_with_the_others():
    bad = fp(ref='fp_bad', titrant='fp_titrant_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([fp(), spr(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'


def test_the_real_fp_case_pools_with_an_spr_without_a_variance():
    real = convert_fp(grade_fp(fp_real_record()))
    row = merge_binding([real, spr()])
    # the real record's preparations are unknown, so the two are one dependent group whose effect is the mean of 400 and
    # 30 nM = 215 nM; the real FP has no spread kind, so the variance stays unavailable and the effect is conditional
    assert row['counts']['independent_groups'] == 1 and row['cells']['effect_variance']['value'] is None
    assert row['cells']['measured_effect']['value'] == pytest.approx(215.0) and row['cells']['measured_effect']['status'] == 'conditional'
