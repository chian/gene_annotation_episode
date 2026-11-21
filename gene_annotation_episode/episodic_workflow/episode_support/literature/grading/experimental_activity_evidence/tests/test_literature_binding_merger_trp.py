"""First binding merger with intrinsic fluorescence quenching (Trp) together with SPR, ITC, BLI, GCI, FP, FRET and MST for the same
binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the spread, so a
result's variance is its spread squared (Trp 9 nM -> 81, MST 8 nM -> 64, FRET 7 nM -> 49, FP 6 nM -> 36, BLI 5 nM -> 25,
ITC 4 nM -> 16, SPR 3 nM -> 9, GCI 2 nM -> 4).
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
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import convert_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import grade_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import synthetic_record as bli_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import synthetic_record as fp_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import synthetic_record as fret_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import synthetic_record as gci_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import synthetic_record as mst_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.trp_cases import real_record as trp_real_record, synthetic_record as trp_record


def trp(ref='trp_1', titrant='trp_ligand_1', fixed='trp_protein_1', kd=90.0, spread=9.0):
    return convert_trp(grade_trp(trp_record(experiment_ref=ref, titrant_prep=titrant, fixed_prep=fixed, dataset='trp_data_' + ref, kd=kd, spread=spread)))


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


def test_a_trp_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([trp(kd=90.0, spread=9.0), spr(kd=30.0, spread=3.0)])
    # variances 81 (Trp) and 9 (SPR); weights 1/81 and 1/9; sum of weights = 10/81
    # effect = (90 / 81 + 30 / 9) / (10 / 81) = (10/9 + 10/3) / (10/81) = (40/9) x (81/10) = 36 nM
    # variance = 81 / 10 = 8.1 nM^2; precision = 10/81
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(36.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(8.1)
    assert row['cells']['effect_precision']['value'] == pytest.approx(10 / 81)
    assert row['experiment_types'] == ['spr', 'trp_quenching'] and row['group_experiment_types'] == [['trp_quenching'], ['spr']]


def test_all_eight_experiment_types_independent_are_eight_groups():
    row = merge_binding([trp(), mst(), spr(), itc(), bli(), gci(), fp(), fret()])
    # variances 81, 64, 9, 16, 25, 4, 36, 49; effects 90, 80, 30, 40, 50, 20, 60, 70
    # weights = 1/81, 1/64, 1/9, 1/16, 1/25, 1/4, 1/36, 1/49
    weights = [1 / 81, 1 / 64, 1 / 9, 1 / 16, 1 / 25, 1 / 4, 1 / 36, 1 / 49]
    effects = [90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]
    assert row['counts'] == {'experiments': 8, 'independent_groups': 8}
    assert row['cells']['measured_effect']['value'] == pytest.approx(sum(w * e for w, e in zip(weights, effects)) / sum(weights), rel=1e-9)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / sum(weights))
    assert row['experiment_types'] == ['bli', 'fp', 'fret', 'gci', 'itc', 'mst', 'spr', 'trp_quenching']


def test_a_trp_and_an_mst_sharing_the_protein_preparation_are_one_dependent_group():
    shared_trp, shared_mst = trp(fixed='prep_shared'), mst(fixed='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_trp, shared_mst])] == [['trp_1', 'mst_1']]
    row = merge_binding([shared_trp, shared_mst])
    # one group: effect = mean(90, 80) = 85 nM; variance = ((9 + 8) / 2)^2 = 72.25 nM^2
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(85.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(72.25)
    assert row['group_experiment_types'] == [['mst', 'trp_quenching']]


def test_the_trp_ligand_or_protein_that_is_a_protein_of_another_method_is_one_preparation():
    assert len(dependence_groups([trp(titrant='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([trp(fixed='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([trp(titrant='prep_shared'), bli(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([trp(fixed='prep_shared'), gci(analyte='prep_shared')])) == 1
    assert len(dependence_groups([trp(titrant='prep_shared'), fp(tracer='prep_shared')])) == 1
    assert len(dependence_groups([trp(fixed='prep_shared'), fret(titrant='prep_shared')])) == 1
    assert len(dependence_groups([trp(fixed='prep_shared'), spr(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([trp(titrant='prep_shared'), mst(fixed='prep_shared')])) == 1
    assert len(dependence_groups([trp(), mst(), itc(), bli(), gci(), fp(), fret(), spr()])) == 8


def test_two_trp_experiments_with_the_same_protein_are_dependent_and_none_have_a_surface():
    assert len(dependence_groups([trp(ref='a', fixed='protein_1'), trp(ref='b', titrant='ligand_b', fixed='protein_1')])) == 1
    assert len(dependence_groups([trp(ref='a', fixed='protein_1'), trp(ref='b', titrant='ligand_b', fixed='protein_2')])) == 2
    assert trp()['dependence']['surface_ref'] is None


def test_an_unknown_trp_preparation_is_dependent():
    unknown = trp(fixed=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(90, 30) = 60; variance ((9 + 3) / 2)^2 = 36
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(60.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(36.0)


def test_a_result_without_a_constant_is_excluded_and_its_type_is_not_listed():
    ksv_only = trp(ref='trp_ksv_only')
    ksv_only = convert_trp(grade_trp({**trp_record(experiment_ref='trp_ksv_only'), 'fit_model': 'stern_volmer'}))
    row = merge_binding([spr(), ksv_only])
    assert row['experiment_types'] == ['spr'] and 'trp_ksv_only' in row['excluded']


def test_the_row_interpretations_pool_the_trp_criteria_with_the_others():
    bad = trp(ref='trp_bad', titrant='trp_ligand_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([trp(), spr(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'


def test_the_real_trp_case_pools_with_an_spr_with_a_conditional_effect_and_no_variance():
    real = convert_trp(grade_trp(trp_real_record()))
    row = merge_binding([real, spr()])
    # the real record's preparations are unknown, so the two are one dependent group whose effect is the mean of 16 and 30 nM = 23 nM;
    # the real record gives a spread whose kind is not stated, so its variance stays unavailable and the effect is conditional
    assert row['counts']['independent_groups'] == 1 and row['cells']['effect_variance']['value'] is None
    assert row['cells']['measured_effect']['value'] == pytest.approx(23.0) and row['cells']['measured_effect']['status'] == 'conditional'


def test_the_populated_grader_picks_the_trp_grader_by_the_records_own_type():
    record = trp_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'trp_quenching' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_trp(record) and len(held['grade']['criteria']) == 15
