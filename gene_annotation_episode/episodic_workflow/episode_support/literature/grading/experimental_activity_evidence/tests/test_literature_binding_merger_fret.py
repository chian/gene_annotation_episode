"""First binding merger with FRET together with SPR, ITC, BLI, GCI and FP for the same binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the
spread, so a result's variance is its spread squared (FRET 7 nM -> 49, FP 6 nM -> 36, SPR 3 nM -> 9, ITC 4 nM -> 16,
BLI 5 nM -> 25, GCI 2 nM -> 4).
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
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_populated_grader import populated_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import synthetic_record as bli_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import synthetic_record as fp_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import real_record as fret_real_record, synthetic_record as fret_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import synthetic_record as gci_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record


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


def test_a_fret_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([fret(kd=70.0, spread=7.0), spr(kd=30.0, spread=3.0)])
    # variances 49 (FRET) and 9 (SPR); weights 1/49 and 1/9; sum of weights = 58/441
    # effect = (70 / 49 + 30 / 9) / (58 / 441) = (10/7 + 10/3) / (58/441) = (100/21) x (441/58) = 2100/58 = 36.2069 nM
    # variance = 441 / 58 = 7.6034 nM^2; precision = 58/441
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(2100 / 58)
    assert row['cells']['effect_variance']['value'] == pytest.approx(441 / 58)
    assert row['cells']['effect_precision']['value'] == pytest.approx(58 / 441)
    assert row['experiment_types'] == ['fret', 'spr'] and row['group_experiment_types'] == [['fret'], ['spr']]


def test_fret_spr_itc_bli_gci_and_fp_all_independent_are_six_groups():
    row = merge_binding([fret(), spr(), itc(), bli(), gci(), fp()])
    # variances 49, 9, 16, 25, 4, 36; weights 1/49, 1/9, 1/16, 1/25, 1/4, 1/36
    # sum = 0.020408 + 0.111111 + 0.0625 + 0.04 + 0.25 + 0.027778 = 0.511797
    # numerator = 70/49 + 30/9 + 40/16 + 50/25 + 20/4 + 60/36 = 1.428571 + 3.333333 + 2.5 + 2 + 5 + 1.666667 = 15.928571
    weights = [1 / 49, 1 / 9, 1 / 16, 1 / 25, 1 / 4, 1 / 36]
    assert row['counts'] == {'experiments': 6, 'independent_groups': 6}
    assert row['cells']['measured_effect']['value'] == pytest.approx(15.928571 / sum(weights), rel=1e-6)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / sum(weights))
    assert row['experiment_types'] == ['bli', 'fp', 'fret', 'gci', 'itc', 'spr']


def test_a_fret_and_an_spr_sharing_the_titrant_preparation_are_one_dependent_group():
    shared_fret, shared_spr = fret(titrant='prep_shared'), spr(analyte='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_fret, shared_spr])] == [['fret_1', 'spr_1']]
    row = merge_binding([shared_fret, shared_spr])
    # one group: effect = mean(70, 30) = 50 nM; variance = ((7 + 3) / 2)^2 = 25 nM^2
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(50.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(25.0)
    assert row['group_experiment_types'] == [['fret', 'spr']]


def test_the_fret_titrant_or_fixed_partner_that_is_a_protein_of_another_method_is_one_preparation():
    assert len(dependence_groups([fret(titrant='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([fret(fixed='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([fret(titrant='prep_shared'), bli(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([fret(fixed='prep_shared'), gci(analyte='prep_shared')])) == 1
    assert len(dependence_groups([fret(titrant='prep_shared'), fp(tracer='prep_shared')])) == 1
    assert len(dependence_groups([fret(fixed='prep_shared'), spr(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([fret(), itc(), bli(), gci(), fp(), spr()])) == 6


def test_two_fret_experiments_with_the_same_fixed_partner_are_dependent_and_none_have_a_surface():
    assert len(dependence_groups([fret(ref='a', fixed='fixed_1'), fret(ref='b', titrant='titrant_b', fixed='fixed_1')])) == 1
    assert len(dependence_groups([fret(ref='a', fixed='fixed_1'), fret(ref='b', titrant='titrant_b', fixed='fixed_2')])) == 2
    assert fret()['dependence']['surface_ref'] is None


def test_an_unknown_fret_preparation_is_dependent():
    unknown = fret(fixed=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(70, 30) = 50; variance ((7 + 3) / 2)^2 = 25
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(50.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(25.0)


def test_a_result_without_a_constant_is_excluded_and_its_type_is_not_listed():
    no_effect = fret(ref='fret_no_kd')
    no_effect['sheet']['cells']['measured_effect'] = {**no_effect['sheet']['cells']['measured_effect'], 'value': None, 'status': 'unavailable', 'reasons': ['x']}
    row = merge_binding([spr(), no_effect])
    assert row['experiment_types'] == ['spr'] and 'fret_no_kd' in row['excluded']


def test_the_row_interpretations_pool_the_fret_criteria_with_the_others():
    bad = fret(ref='fret_bad', titrant='fret_titrant_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([fret(), spr(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'


def test_the_real_fret_case_pools_with_an_spr_without_a_variance():
    real = convert_fret(grade_fret(fret_real_record()))
    row = merge_binding([real, spr()])
    # the real record's preparations are unknown, so the two are one dependent group whose effect is the mean of 20 and
    # 30 nM = 25 nM; the real FRET gives its interval by its limits, so the variance stays unavailable and the effect is conditional
    assert row['counts']['independent_groups'] == 1 and row['cells']['effect_variance']['value'] is None
    assert row['cells']['measured_effect']['value'] == pytest.approx(25.0) and row['cells']['measured_effect']['status'] == 'conditional'


def test_the_populated_grader_picks_the_fret_grader_by_the_records_own_type():
    record = fret_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'fret' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_fret(record) and len(held['grade']['criteria']) == 13
