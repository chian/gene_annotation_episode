"""First binding merger with an AlphaScreen binding experiment together with the ten earlier types (SPR, ITC, BLI, GCI, FP, FRET, MST,
intrinsic fluorescence quenching (Trp), FCS and ELISA) for the same binding statement.

Every expected number is worked by hand in the comment above it. All results here use a standard error as the spread, so a
result's variance is its spread squared (AlphaScreen 12 nM -> 144, ELISA 11 nM -> 121, FCS 10 nM -> 100, Trp 9 nM -> 81, MST 8 nM -> 64,
FRET 7 nM -> 49, FP 6 nM -> 36, BLI 5 nM -> 25, ITC 4 nM -> 16, SPR 3 nM -> 9, GCI 2 nM -> 4).
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
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import convert_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import grade_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.alpha_cases import real_record as alpha_real_record, synthetic_record as alpha_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import synthetic_record as bli_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.elisa_cases import synthetic_record as elisa_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fcs_cases import synthetic_record as fcs_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import synthetic_record as fp_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import synthetic_record as fret_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import synthetic_record as gci_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import synthetic_record as itc_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import synthetic_record as mst_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record as spr_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.trp_cases import synthetic_record as trp_record


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
    return [elisa(), fcs(), trp(), mst(), spr(), itc(), bli(), gci(), fp(), fret()]


def test_an_alphascreen_and_an_spr_on_different_preparations_are_two_independent_groups():
    row = merge_binding([alpha(kd=120.0, spread=12.0), spr(kd=30.0, spread=3.0)])
    # variances 144 (AlphaScreen) and 9 (SPR); weights 1/144 and 1/9; sum of weights = 17/144
    # effect = (120 / 144 + 30 / 9) / (17 / 144) = (120 / 144 + 480 / 144) * (144 / 17) = 600 / 17 = 35.2941 nM
    # variance = 144 / 17 = 8.4706 nM^2; precision = 17 / 144
    assert row['counts'] == {'experiments': 2, 'independent_groups': 2}
    assert row['cells']['measured_effect']['value'] == pytest.approx(600 / 17)
    assert row['cells']['measured_effect']['value'] == pytest.approx(35.2941, abs=1e-4)
    assert row['cells']['effect_variance']['value'] == pytest.approx(144 / 17)
    assert row['cells']['effect_precision']['value'] == pytest.approx(17 / 144)
    assert row['experiment_types'] == ['alphascreen', 'spr'] and row['group_experiment_types'] == [['alphascreen'], ['spr']]


def test_all_eleven_experiment_types_independent_are_eleven_groups():
    row = merge_binding([alpha(), *all_earlier()])
    # variances 144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49; effects 120, 110, 100, 90, 80, 30, 40, 50, 20, 60, 70
    variances = [144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49]
    effects = [120.0, 110.0, 100.0, 90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]
    weights = [1 / v for v in variances]
    assert row['counts'] == {'experiments': 11, 'independent_groups': 11}
    assert row['cells']['measured_effect']['value'] == pytest.approx(sum(w * e for w, e in zip(weights, effects)) / sum(weights), rel=1e-9)
    assert row['cells']['effect_variance']['value'] == pytest.approx(1 / sum(weights))
    assert row['experiment_types'] == ['alphascreen', 'bli', 'elisa', 'fcs', 'fp', 'fret', 'gci', 'itc', 'mst', 'spr', 'trp_quenching']
    assert row['interpretations']['binding_regime'] == 'supported' and row['interpretations']['calibration_applicability'] == 'supported'


def test_an_alphascreen_and_an_elisa_sharing_the_titrant_preparation_are_one_dependent_group():
    shared_alpha, shared_elisa = alpha(titrant='prep_shared'), elisa(titrant='prep_shared')
    assert [[r['experiment_ref'] for r in g] for g in dependence_groups([shared_alpha, shared_elisa])] == [['alpha_1', 'elisa_1']]
    row = merge_binding([shared_alpha, shared_elisa])
    # one group: effect = mean(120, 110) = 115 nM; variance = ((12 + 11) / 2)^2 = 132.25 nM^2
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == pytest.approx(115.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(132.25)
    assert row['group_experiment_types'] == [['alphascreen', 'elisa']]


def test_the_alphascreen_titrant_or_fixed_partner_that_is_a_protein_of_another_method_is_one_preparation():
    assert len(dependence_groups([alpha(titrant='prep_shared'), itc(cell='prep_shared')])) == 1
    assert len(dependence_groups([alpha(fixed='prep_shared'), itc(syringe='prep_shared')])) == 1
    assert len(dependence_groups([alpha(titrant='prep_shared'), bli(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([alpha(fixed='prep_shared'), gci(analyte='prep_shared')])) == 1
    assert len(dependence_groups([alpha(titrant='prep_shared'), fp(tracer='prep_shared')])) == 1
    assert len(dependence_groups([alpha(fixed='prep_shared'), fret(titrant='prep_shared')])) == 1
    assert len(dependence_groups([alpha(fixed='prep_shared'), spr(immobilized='prep_shared')])) == 1
    assert len(dependence_groups([alpha(titrant='prep_shared'), mst(fixed='prep_shared')])) == 1
    assert len(dependence_groups([alpha(fixed='prep_shared'), trp(titrant='prep_shared')])) == 1
    assert len(dependence_groups([alpha(titrant='prep_shared'), fcs(fixed='prep_shared')])) == 1
    assert len(dependence_groups([alpha(fixed='prep_shared'), elisa(coated='prep_shared')])) == 1
    assert len(dependence_groups([alpha(), *all_earlier()])) == 11


def test_two_alphascreen_experiments_with_the_same_fixed_partner_are_dependent_and_none_have_a_surface():
    assert len(dependence_groups([alpha(ref='a', fixed='fixed_1'), alpha(ref='b', titrant='titrant_b', fixed='fixed_1')])) == 1
    assert len(dependence_groups([alpha(ref='a', fixed='fixed_1'), alpha(ref='b', titrant='titrant_b', fixed='fixed_2')])) == 2
    assert alpha()['dependence']['surface_ref'] is None


def test_an_unknown_alphascreen_preparation_is_dependent():
    unknown = alpha(fixed=None)
    assert len(dependence_groups([unknown, spr()])) == 1
    row = merge_binding([unknown, spr()])
    # one group of two: mean(120, 30) = 75; variance ((12 + 3) / 2)^2 = 56.25
    assert row['counts']['independent_groups'] == 1 and row['cells']['measured_effect']['value'] == pytest.approx(75.0)
    assert row['cells']['effect_variance']['value'] == pytest.approx(56.25)


def test_a_result_without_a_binding_constant_is_excluded_and_its_type_is_not_listed():
    record = alpha_record(experiment_ref='alpha_no_kd')
    for name in ('kd', 'ki'):
        record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}
    row = merge_binding([spr(), convert_alpha(grade_alpha(record))])         # the EC50 and the IC50 stay, and are not binding constants
    assert row['experiment_types'] == ['spr'] and 'alpha_no_kd' in row['excluded']


def test_the_row_interpretations_pool_the_alphascreen_criteria_with_the_others():
    bad = alpha(ref='alpha_bad', titrant='alpha_titrant_2')
    bad['extraction']['interpretations']['binding_controls'] = {'status': 'conflicting', 'support_refs': []}
    row = merge_binding([alpha(), spr(), elisa(), bad])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['sampling_basis'] == 'supported'


def test_the_real_alphascreen_case_has_no_binding_constant_so_it_is_excluded_beside_an_spr_and_an_elisa():
    real = convert_alpha(grade_alpha(alpha_real_record()))
    row = merge_binding([real, spr(), elisa()])
    # the real paragraph reports no KD, EC50, IC50 or Ki value, so its result carries no effect
    assert row['experiment_types'] == ['elisa', 'spr'] and 'exp_spindlin1_alphalisa' in row['excluded']
    assert row['counts']['independent_groups'] == 2


def test_the_populated_grader_picks_the_alphascreen_grader_by_the_records_own_type():
    record = alpha_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'alphascreen' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_alpha(record) and len(held['grade']['criteria']) == 15
