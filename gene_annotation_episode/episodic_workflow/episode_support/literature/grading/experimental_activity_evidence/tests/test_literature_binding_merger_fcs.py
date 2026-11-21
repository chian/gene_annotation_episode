"""First binding merger with fluorescence correlation spectroscopy (FCS) together with SPR, ITC, BLI, GCI, FP, FRET, MST and intrinsic
fluorescence quenching (Trp) for the same binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the spread, so a
result's variance is its spread squared (FCS 10 nM -> 100, Trp 9 nM -> 81, MST 8 nM -> 64, FRET 7 nM -> 49, FP 6 nM -> 36,
BLI 5 nM -> 25, ITC 4 nM -> 16, SPR 3 nM -> 9, GCI 2 nM -> 4).
"""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import convert_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import convert_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import grade_fcs
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
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fcs_cases import real_record as fcs_real_record, synthetic_record as fcs_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import synthetic_record as fp_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import synthetic_record as fret_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import synthetic_record as gci_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import synthetic_record as mst_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.trp_cases import synthetic_record as trp_record


def fcs(ref='fcs_1', titrant='fcs_titrant_1', fixed='fcs_labelled_1', kd=100.0, spread=10.0):
    return convert_fcs(grade_fcs(fcs_record(experiment_ref=ref, titrant_prep=titrant, fixed_prep=fixed, dataset='fcs_data_' + ref, kd=kd, spread=spread)))


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


def test_an_fcs_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([fcs(kd=100.0, spread=10.0), spr(kd=30.0, spread=3.0)])
    # variances 100 (FCS) and 9 (SPR); weights 1/100 and 1/9; sum of weights = 109/900
    # effect = (100 / 100 + 30 / 9) / (109 / 900) = (1 + 10/3) x (900 / 109) = (13/3) x (900 / 109) = 3900 / 109 = 35.78 nM
    # variance = 900 / 109 = 8.257 nM^2; precision = 109 / 900
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(3900 / 109)
    assert row['cells']['effect_variance']['value'] == pytest.approx(900 / 109)
    assert row['cells']['effect_precision']['value'] == pytest.approx(109 / 900)
    assert row['experiment_types'] == ['fcs', 'spr'] and row['group_experiment_types'] == [['fcs'], ['spr']]


def test_all_nine_experiment_types_independent_are_nine_groups():
    row = merge_binding([fcs(), trp(), mst(), spr(), itc(), bli(), gci(), fp(), fret()])
    # variances 100, 81, 64, 9, 16, 25, 4, 36, 49; effects 100, 90, 80, 30, 40, 50, 20, 60, 70
    # weights = 1/100, 1/81, 1/64, 1/9, 1/16, 1/25, 1/4, 1/36, 1/49
    weights = [1 / 100, 1 / 81, 1 / 64, 1 / 9, 1 / 16, 1 / 25, 1 / 4, 1 / 36, 1 / 49]
    effects = [100.0, 90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]
    assert row['counts'] == {'experiments': 9, 'independent_groups': 9}
    assert row['cells']['measured_effect']['value'] == pytest.approx(sum(w * e for w, e in zip(weights, effects)) / sum(weights), rel=1e-9)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / sum(weights))
    assert row['experiment_types'] == ['bli', 'fcs', 'fp', 'fret', 'gci', 'itc', 'mst', 'spr', 'trp_quenching']


def test_an_fcs_and_a_trp_sharing_the_labelled_partner_preparation_are_one_dependent_group():
    shared_fcs, shared_trp = fcs(fixed='prep_shared'), trp(fixed='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_fcs, shared_trp])] == [['fcs_1', 'trp_1']]
    row = merge_binding([shared_fcs, shared_trp])
    # one group: effect = mean(100, 90) = 95 nM; variance = ((10 + 9) / 2)^2 = 90.25 nM^2
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(95.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(90.25)
    assert row['group_experiment_types'] == [['fcs', 'trp_quenching']]


def test_the_fcs_titrant_or_labelled_partner_that_is_a_protein_of_another_method_is_one_preparation():
    assert len(dependence_groups([fcs(titrant='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([fcs(fixed='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([fcs(titrant='prep_shared'), bli(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([fcs(fixed='prep_shared'), gci(analyte='prep_shared')])) == 1
    assert len(dependence_groups([fcs(titrant='prep_shared'), fp(tracer='prep_shared')])) == 1
    assert len(dependence_groups([fcs(fixed='prep_shared'), fret(titrant='prep_shared')])) == 1
    assert len(dependence_groups([fcs(fixed='prep_shared'), spr(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([fcs(titrant='prep_shared'), mst(fixed='prep_shared')])) == 1
    assert len(dependence_groups([fcs(fixed='prep_shared'), trp(titrant='prep_shared')])) == 1
    assert len(dependence_groups([fcs(), trp(), mst(), itc(), bli(), gci(), fp(), fret(), spr()])) == 9


def test_two_fcs_experiments_with_the_same_labelled_partner_are_dependent_and_none_have_a_surface():
    assert len(dependence_groups([fcs(ref='a', fixed='labelled_1'), fcs(ref='b', titrant='titrant_b', fixed='labelled_1')])) == 1
    assert len(dependence_groups([fcs(ref='a', fixed='labelled_1'), fcs(ref='b', titrant='titrant_b', fixed='labelled_2')])) == 2
    assert fcs()['dependence']['surface_ref'] is None


def test_an_unknown_fcs_preparation_is_dependent():
    unknown = fcs(fixed=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(100, 30) = 65; variance ((10 + 3) / 2)^2 = 42.25
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(65.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(42.25)


def test_a_result_without_a_kd_is_excluded_and_its_type_is_not_listed():
    record = fcs_record(experiment_ref='fcs_no_kd')
    record['quantities']['kd'] = {**record['quantities']['kd'], 'status': 'unavailable', 'value': None}
    row = merge_binding([spr(), convert_fcs(grade_fcs(record))])
    assert row['experiment_types'] == ['spr'] and 'fcs_no_kd' in row['excluded']


def test_the_row_interpretations_pool_the_fcs_criteria_with_the_others():
    bad = fcs(ref='fcs_bad', titrant='fcs_titrant_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([fcs(), spr(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'


def test_the_real_fcs_case_pools_with_an_spr_with_a_conditional_effect_and_no_variance():
    real = convert_fcs(grade_fcs(fcs_real_record()))
    row = merge_binding([real, spr()])
    # the real record's preparations are unknown, so the two are one dependent group whose effect is the mean of 5 and 30 nM = 17.5 nM;
    # the real record gives a spread whose kind is not stated, so its variance stays unavailable and the effect is conditional
    assert row['counts']['independent_groups'] == 1 and row['cells']['effect_variance']['value'] is None
    assert row['cells']['measured_effect']['value'] == pytest.approx(17.5) and row['cells']['measured_effect']['status'] == 'conditional'


def test_the_populated_grader_picks_the_fcs_grader_by_the_records_own_type():
    record = fcs_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'fcs' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_fcs(record) and len(held['grade']['criteria']) == 21
