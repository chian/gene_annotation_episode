"""First binding merger with MST together with SPR, ITC, BLI, GCI, FP and FRET for the same binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the
spread, so a result's variance is its spread squared (MST 8 nM -> 64, FRET 7 nM -> 49, FP 6 nM -> 36, SPR 3 nM -> 9,
ITC 4 nM -> 16, BLI 5 nM -> 25, GCI 2 nM -> 4).
"""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import convert_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import convert_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_grader import grade_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import convert_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_grader import grade_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import convert_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_grader import grade_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import convert_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import grade_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import convert_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_grader import grade_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_populated_grader import populated_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import synthetic_record as bli_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import synthetic_record as fp_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import synthetic_record as fret_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import synthetic_record as gci_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import real_record as mst_real_record, synthetic_record as mst_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record


def mst(ref='mst_1', titrant='mst_titrant_1', fixed='mst_fixed_1', kd=80.0, spread=8.0):
    return convert_mst(grade_mst(mst_record(experiment_ref=ref, titrant_prep=titrant, fixed_prep=fixed, dataset='mst_data_' + ref, kd=kd, spread=spread)))


def fret(ref='fret_1', titrant='fret_titrant_1', fixed='fret_fixed_1', kd=70.0, spread=7.0):
    return convert_fret(grade_fret(fret_record(experiment_ref=ref, titrant_prep=titrant, fixed_prep=fixed, dataset='fret_data_' + ref, kd=kd, spread=spread)))


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


def test_an_mst_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([mst(kd=80.0, spread=8.0), spr(kd=30.0, spread=3.0)])
    # variances 64 (MST) and 9 (SPR); weights 1/64 and 1/9; sum of weights = 73/576
    # effect = (80 / 64 + 30 / 9) / (73 / 576) = (5/4 + 10/3) / (73/576) = (55/12) x (576/73) = 2640/73 = 36.1644 nM
    # variance = 576 / 73 = 7.8904 nM^2; precision = 73/576
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(2640 / 73)
    assert row['cells']['effect_variance']['value'] == pytest.approx(576 / 73)
    assert row['cells']['effect_precision']['value'] == pytest.approx(73 / 576)
    assert row['experiment_types'] == ['mst', 'spr'] and row['group_experiment_types'] == [['mst'], ['spr']]


def test_mst_spr_itc_bli_gci_fp_and_fret_all_independent_are_seven_groups():
    row = merge_binding([mst(), spr(), itc(), bli(), gci(), fp(), fret()])
    # variances 64, 9, 16, 25, 4, 36, 49; weights 1/64, 1/9, 1/16, 1/25, 1/4, 1/36, 1/49
    # sum = 0.015625 + 0.111111 + 0.0625 + 0.04 + 0.25 + 0.027778 + 0.020408 = 0.527422
    # numerator = 80/64 + 30/9 + 40/16 + 50/25 + 20/4 + 60/36 + 70/49 = 1.25 + 3.333333 + 2.5 + 2 + 5 + 1.666667 + 1.428571 = 17.178571
    weights = [1 / 64, 1 / 9, 1 / 16, 1 / 25, 1 / 4, 1 / 36, 1 / 49]
    assert row['counts'] == {'experiments': 7, 'independent_groups': 7}
    assert row['cells']['measured_effect']['value'] == pytest.approx(17.178571 / sum(weights), rel=1e-6)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / sum(weights))
    assert row['experiment_types'] == ['bli', 'fp', 'fret', 'gci', 'itc', 'mst', 'spr']


def test_an_mst_and_an_spr_sharing_the_titrant_preparation_are_one_dependent_group():
    shared_mst, shared_spr = mst(titrant='prep_shared'), spr(analyte='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_mst, shared_spr])] == [['mst_1', 'spr_1']]
    row = merge_binding([shared_mst, shared_spr])
    # one group: effect = mean(80, 30) = 55 nM; variance = ((8 + 3) / 2)^2 = 30.25 nM^2
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(55.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(30.25)
    assert row['group_experiment_types'] == [['mst', 'spr']]


def test_the_mst_titrant_or_fixed_partner_that_is_a_protein_of_another_method_is_one_preparation():
    assert len(dependence_groups([mst(titrant='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([mst(fixed='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([mst(titrant='prep_shared'), bli(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([mst(fixed='prep_shared'), gci(analyte='prep_shared')])) == 1
    assert len(dependence_groups([mst(titrant='prep_shared'), fp(tracer='prep_shared')])) == 1
    assert len(dependence_groups([mst(fixed='prep_shared'), fret(titrant='prep_shared')])) == 1
    assert len(dependence_groups([mst(fixed='prep_shared'), spr(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([mst(), itc(), bli(), gci(), fp(), fret(), spr()])) == 7


def test_two_mst_experiments_with_the_same_fixed_partner_are_dependent_and_none_have_a_surface():
    assert len(dependence_groups([mst(ref='a', fixed='fixed_1'), mst(ref='b', titrant='titrant_b', fixed='fixed_1')])) == 1
    assert len(dependence_groups([mst(ref='a', fixed='fixed_1'), mst(ref='b', titrant='titrant_b', fixed='fixed_2')])) == 2
    assert mst()['dependence']['surface_ref'] is None


def test_an_unknown_mst_preparation_is_dependent():
    unknown = mst(fixed=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(80, 30) = 55; variance ((8 + 3) / 2)^2 = 30.25
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(55.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(30.25)


def test_a_result_without_a_constant_is_excluded_and_its_type_is_not_listed():
    no_effect = mst(ref='mst_no_kd')
    no_effect['sheet']['cells']['measured_effect'] = {**no_effect['sheet']['cells']['measured_effect'], 'value': None, 'status': 'unavailable', 'reasons': ['x']}
    row = merge_binding([spr(), no_effect])
    assert row['experiment_types'] == ['spr'] and 'mst_no_kd' in row['excluded']


def test_the_row_interpretations_pool_the_mst_criteria_with_the_others():
    bad = mst(ref='mst_bad', titrant='mst_titrant_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([mst(), spr(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'


def test_the_real_mst_case_pools_with_an_spr_without_a_variance():
    real = convert_mst(grade_mst(mst_real_record()))
    row = merge_binding([real, spr()])
    # the real record's preparations are unknown, so the two are one dependent group whose effect is the mean of 532 and
    # 30 nM = 281 nM; the real MST gives no spread, so the variance stays unavailable and the effect is conditional
    assert row['counts']['independent_groups'] == 1 and row['cells']['effect_variance']['value'] is None
    assert row['cells']['measured_effect']['value'] == pytest.approx(281.0) and row['cells']['measured_effect']['status'] == 'conditional'


def test_the_populated_grader_picks_the_mst_grader_by_the_records_own_type():
    record = mst_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'mst' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_mst(record) and len(held['grade']['criteria']) == 13
