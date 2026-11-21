"""First binding merger with a radioligand binding experiment together with the eleven earlier types (SPR, ITC, BLI, GCI, FP, FRET, MST,
intrinsic fluorescence quenching (Trp), FCS, ELISA and AlphaScreen) for the same binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the spread, so a
result's variance is its spread squared (radioligand 13 nM -> 169, AlphaScreen 12 nM -> 144, ELISA 11 nM -> 121, FCS 10 nM -> 100,
Trp 9 nM -> 81, MST 8 nM -> 64, FRET 7 nM -> 49, FP 6 nM -> 36, BLI 5 nM -> 25, ITC 4 nM -> 16, SPR 3 nM -> 9, GCI 2 nM -> 4).
"""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import convert_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_grader import grade_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import convert_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_converter import convert_elisa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_grader import grade_elisa
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
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import convert_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import grade_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import convert_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import grade_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.alpha_cases import synthetic_record as alpha_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import synthetic_record as bli_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.elisa_cases import synthetic_record as elisa_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fcs_cases import synthetic_record as fcs_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import synthetic_record as fp_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import synthetic_record as fret_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import synthetic_record as gci_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import synthetic_record as mst_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.radioligand_cases import real_record as radioligand_real_record, synthetic_record as radioligand_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.trp_cases import synthetic_record as trp_record


def radioligand(ref='radioligand_1', ligand='radioligand_ligand_1', receptor='radioligand_receptor_1', kd=130.0, spread=13.0):
    return convert_radioligand(grade_radioligand(radioligand_record(experiment_ref=ref, radioligand_prep=ligand, receptor_prep=receptor, dataset='radioligand_data_' + ref, kd=kd, spread=spread)))


def alpha(ref='alpha_1', titrant='alpha_titrant_1', fixed='alpha_fixed_1', kd=120.0, spread=12.0):
    return convert_alpha(grade_alpha(alpha_record(experiment_ref=ref, titrant_prep=titrant, fixed_prep=fixed, dataset='alpha_data_' + ref, kd=kd, spread=spread)))


def elisa(ref='elisa_1', titrant='elisa_titrant_1', coated='elisa_coated_1', kd=110.0, spread=11.0):
    return convert_elisa(grade_elisa(elisa_record(experiment_ref=ref, titrant_prep=titrant, fixed_prep=coated, dataset='elisa_data_' + ref, kd=kd, spread=spread)))


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


def all_earlier():
    return [alpha(), elisa(), fcs(), trp(), mst(), spr(), itc(), bli(), gci(), fp(), fret()]


def test_a_radioligand_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([radioligand(kd=130.0, spread=13.0), spr(kd=30.0, spread=3.0)])
    # variances 169 (radioligand) and 9 (SPR); weights 1/169 and 1/9; sum of weights = 178/1521
    # effect = (130 / 169 + 30 / 9) / (178 / 1521) = (130 * 9 + 30 * 169) / 1521 * (1521 / 178) = (1170 + 5070) / 178 = 6240 / 178 = 35.0562 nM
    # variance = 1521 / 178 = 8.5449 nM^2; precision = 178 / 1521
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(6240 / 178)
    assert row['cells']['measured_effect']['value'] == pytest.approx(35.0562, abs=1e-4)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1521 / 178)
    assert row['cells']['effect_precision']['value'] == pytest.approx(178 / 1521)
    assert row['experiment_types'] == ['radioligand', 'spr'] and row['group_experiment_types'] == [['radioligand'], ['spr']]


def test_all_twelve_experiment_types_independent_are_twelve_groups():
    row = merge_binding([radioligand(), *all_earlier()])
    # variances 169, 144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49; effects 130, 120, 110, 100, 90, 80, 30, 40, 50, 20, 60, 70
    variances = [169, 144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49]
    effects = [130.0, 120.0, 110.0, 100.0, 90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]
    weights = [1 / v for v in variances]
    assert row['counts'] == {'experiments': 12, 'independent_groups': 12}
    assert row['cells']['measured_effect']['value'] == pytest.approx(sum(w * e for w, e in zip(weights, effects)) / sum(weights), rel=1e-9)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / sum(weights))
    assert row['experiment_types'] == ['alphascreen', 'bli', 'elisa', 'fcs', 'fp', 'fret', 'gci', 'itc', 'mst', 'radioligand', 'spr', 'trp_quenching']
    assert row['interpretations']['binding_regime'] == 'supported' and row['interpretations']['calibration_applicability'] == 'supported'
    assert row['interpretations']['binding_controls'] == 'supported' and row['interpretations']['binding_parameter_definition'] == 'supported'


def test_a_radioligand_and_an_alphascreen_sharing_the_receptor_preparation_are_one_dependent_group():
    shared_radioligand, shared_alpha = radioligand(receptor='prep_shared'), alpha(fixed='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_radioligand, shared_alpha])] == [['radioligand_1', 'alpha_1']]
    row = merge_binding([shared_radioligand, shared_alpha])
    # one group: effect = mean(130, 120) = 125 nM; variance = ((13 + 12) / 2)^2 = 156.25 nM^2
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(125.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(156.25)
    assert row['group_experiment_types'] == [['alphascreen', 'radioligand']]


def test_the_radioligand_or_receptor_preparation_that_is_a_protein_of_another_method_is_one_preparation():
    assert len(dependence_groups([radioligand(receptor='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(ligand='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(receptor='prep_shared'), bli(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(receptor='prep_shared'), gci(analyte='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(ligand='prep_shared'), fp(tracer='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(receptor='prep_shared'), fret(titrant='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(receptor='prep_shared'), spr(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(ligand='prep_shared'), mst(fixed='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(receptor='prep_shared'), trp(titrant='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(ligand='prep_shared'), fcs(fixed='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(receptor='prep_shared'), elisa(coated='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(receptor='prep_shared'), alpha(titrant='prep_shared')])) == 1
    assert len(dependence_groups([radioligand(), *all_earlier()])) == 12


def test_two_radioligand_experiments_with_the_same_receptor_preparation_are_dependent_and_none_have_a_surface():
    assert len(dependence_groups([radioligand(ref='a', receptor='receptor_1'), radioligand(ref='b', ligand='ligand_b', receptor='receptor_1')])) == 1
    assert len(dependence_groups([radioligand(ref='a', receptor='receptor_1'), radioligand(ref='b', ligand='ligand_b', receptor='receptor_2')])) == 2
    assert radioligand()['dependence']['surface_ref'] is None


def test_an_unknown_radioligand_preparation_is_dependent():
    unknown = radioligand(receptor=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(130, 30) = 80; variance ((13 + 3) / 2)^2 = 64
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(80.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(64.0)


def test_a_result_without_a_binding_constant_is_excluded_and_its_type_is_not_listed():
    record = radioligand_record(experiment_ref='radioligand_no_kd')
    for name in ('kd', 'ki'):
        record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}
    row = merge_binding([spr(), convert_radioligand(grade_radioligand(record))])         # the IC50 stays, and is not a binding constant
    assert row['experiment_types'] == ['spr'] and 'radioligand_no_kd' in row['excluded']


def test_the_row_interpretations_pool_the_radioligand_criteria_with_the_others():
    bad = radioligand(ref='radioligand_bad', ligand='radioligand_ligand_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([radioligand(), spr(), elisa(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'


def test_the_real_radioligand_case_has_no_measured_kd_so_it_is_excluded_beside_an_spr():
    real = convert_radioligand(grade_radioligand(radioligand_real_record()))
    row = merge_binding([real, spr()])
    # the real paragraph cites only a known KD of the radiolabel (not measured), so its result carries no effect
    assert row['experiment_types'] == ['spr'] and 'exp_apelin_receptor_radioligand' in row['excluded']
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}


def test_the_populated_grader_picks_the_radioligand_grader_by_the_records_own_type():
    record = radioligand_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'radioligand' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_radioligand(record) and len(held['grade']['criteria']) == 15
