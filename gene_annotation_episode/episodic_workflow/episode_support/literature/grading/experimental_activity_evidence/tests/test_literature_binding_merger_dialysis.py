"""First binding merger with an equilibrium dialysis / ultrafiltration (dialysis) result together with the sixteen earlier types (SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS,
ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA and SEC) for the same binding statement.

A dialysis has two shapes and the merger's contract is unchanged for both (this file changes nothing in the merger or in the pull-down, EMSA and SEC converters). With a KD (or a Ki) it is a
QUANTITATIVE result: its constant is pooled like that of any other type (inverse-variance across independent groups) and it carries no qualitative effect. Without a constant (only a percent bound or a
percent unbound at one concentration) it is a QUALITATIVE result, like the pull-down, the EMSA and the SEC without a KD: it adds nothing to the pooled effect, the variance or the counts of the experiments
with a constant, and contributes its interpretations and its statement (the row's qualitative block).
The numbers of the other types are those of the SEC merger test (SPR 3 nM -> variance 9 and so on; the thirteen variances 196, 169, ... 4, 36, 49; the EMSA 10 nM with a variance of 1; the quantitative SEC 15 nM with a
variance of 4); the quantitative dialysis adds 25 nM with a variance of 9 (a standard error of 3 nM), and a Ki-only dialysis 35 nM with a variance of 4."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import convert_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import grade_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_populated_grader import populated_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.dialysis_cases import (
    qualitative_record as dialysis_qualitative_record, synthetic_record as dialysis_record)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_emsa import emsa, emsa_qualitative
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_pulldown import pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_sec import sec, sec_qualitative
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_spa import (
    alpha, all_earlier, bli, elisa, fcs, fp, fret, gci, itc, mst, radioligand, spa, spr, trp)

VARIANCES = [196, 169, 144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49]        # spa, radioligand, alpha, elisa, fcs, trp, mst, spr, itc, bli, gci, fret, fp
EFFECTS = [140.0, 130.0, 120.0, 110.0, 100.0, 90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]
SIXTEEN = ([*EFFECTS, 10.0, 15.0], [*VARIANCES, 1, 4])                      # the thirteen above, the EMSA and the quantitative SEC (the pull-down is qualitative)


def dialysis(ref='dial_1', ligand='dial_l_1', protein='dial_p_1', kd=25.0, spread=3.0, **changes):
    """A quantitative dialysis: a KD of ``kd`` nM with a standard error of ``spread`` nM."""
    record = dialysis_record(experiment_ref=ref, ligand=ligand, protein=protein, dataset='dial_data_' + ref, kd=kd, spread=spread)
    for name, answer in changes.items():
        record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
    return convert_dialysis(grade_dialysis(record))


def dialysis_ki(ref='dial_ki_1', ligand='dial_ki_l_1', protein='dial_ki_p_1', ki=35.0, spread=2.0):
    """A dialysis that reports a Ki only: ``ki`` nM with a standard error of ``spread`` nM."""
    record = dialysis_record(experiment_ref=ref, ligand=ligand, protein=protein, dataset='dial_data_' + ref)
    record['quantities']['kd'] = {**record['quantities']['kd'], 'status': 'unavailable', 'value': None}
    record['quantities']['ki'] = point(ki, 'nM', 'ki', ['s'])
    record['quantities']['ki_spread'] = point(spread, 'nM', 'ki_spread', ['s'])
    return convert_dialysis(grade_dialysis(record))


def dialysis_qualitative(ref='dial_q_1', ligand='dial_q_l_1', protein='dial_q_p_1', **changes):
    """A qualitative dialysis: a percent bound at one concentration and its controls, no KD and no Ki."""
    record = dialysis_qualitative_record(experiment_ref=ref, ligand=ligand, protein=protein, dataset='dial_q_data_' + ref)
    for name, answer in changes.items():
        record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
    return convert_dialysis(grade_dialysis(record))


def pooled(effects, variances):
    weights = [1 / v for v in variances]
    return sum(w * e for w, e in zip(weights, effects)) / sum(weights), 1 / sum(weights)


def sixteen_earlier():
    return [sec(), emsa(), pulldown(), spa(), *all_earlier()]


def test_a_qualitative_dialysis_beside_an_spr_does_not_change_the_pooled_effect_and_is_listed_as_qualitative():
    row = merge_binding([dialysis_qualitative(), spr(kd=30.0, spread=3.0)])
    assert row['cells']['measured_effect']['value'] == pytest.approx(30.0) and row['cells']['effect_variance']['value'] == pytest.approx(9.0)     # the SPR alone: 3 nM squared
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1} and row['excluded'] == {}
    assert row['experiment_types'] == ['spr'] and row['group_experiment_types'] == [['spr']]
    assert row['qualitative']['experiment_refs'] == ['dial_q_1'] and row['qualitative']['experiment_types'] == ['dialysis']
    assert row['qualitative']['statements'] == {'dial_q_1': 'interaction_detected'} and row['qualitative']['support_refs'] == {'dial_q_1': ['span_dial_q_1']}
    assert row['qualitative']['dependence_groups'] == [['dial_q_1']] and row['qualitative']['independent_groups'] == 1


def test_a_qualitative_dialysis_with_the_sixteen_earlier_types_leaves_the_numeric_pool_identical():
    base = sixteen_earlier()
    assert len({r['experiment_type'] for r in base}) == 16
    without = merge_binding(base)
    with_dialysis = merge_binding([dialysis_qualitative(), *base])
    assert with_dialysis['cells'] == without['cells']                                      # the same effect, variance and precision, cell for cell
    effect, variance = pooled(*SIXTEEN)
    assert with_dialysis['cells']['measured_effect']['value'] == pytest.approx(effect, rel=1e-9) and with_dialysis['cells']['effect_variance']['value'] == pytest.approx(variance, rel=1e-9)
    assert with_dialysis['counts'] == {'experiments': 17, 'independent_groups': 15} and without['counts'] == {'experiments': 16, 'independent_groups': 15}
    assert len(with_dialysis['experiment_types']) == 15 and 'dialysis' not in with_dialysis['experiment_types'] and 'sec' in with_dialysis['experiment_types'] and with_dialysis['excluded'] == {}
    assert with_dialysis['qualitative']['experiment_types'] == ['dialysis', 'pulldown'] and with_dialysis['qualitative']['independent_groups'] == 2
    assert with_dialysis['interpretations']['binding_controls'] == 'supported' and with_dialysis['interpretations']['binding_regime'] == 'supported'
    assert with_dialysis['interpretations']['sampling_basis'] == 'supported' and with_dialysis['interpretations']['binding_species'] == 'unknown'     # the other types do not select it


def test_qualitative_dialysis_sec_and_emsa_together_leave_the_numeric_pool_identical():
    base = sixteen_earlier()
    all_three = merge_binding([dialysis_qualitative(), sec_qualitative(), emsa_qualitative(), *base])
    assert all_three['cells'] == merge_binding(base)['cells']
    assert all_three['counts'] == {'experiments': 19, 'independent_groups': 15} and all_three['qualitative']['experiment_types'] == ['dialysis', 'emsa', 'pulldown', 'sec'] and all_three['qualitative']['independent_groups'] == 4


def test_a_quantitative_dialysis_is_pooled_with_the_sixteen_earlier_types_as_a_sixteenth_independent_group():
    base = sixteen_earlier()
    row = merge_binding([dialysis(), *base])
    effect, variance = pooled([*SIXTEEN[0], 25.0], [*SIXTEEN[1], 9])
    assert row['cells']['measured_effect']['value'] == pytest.approx(effect, rel=1e-9) and row['cells']['effect_variance']['value'] == pytest.approx(variance, rel=1e-9)
    assert row['cells']['measured_effect']['status'] == 'populated' and row['cells']['effect_precision']['value'] == pytest.approx(1 / variance, rel=1e-9)
    assert row['counts'] == {'experiments': 17, 'independent_groups': 16} and len(row['experiment_types']) == 16 and 'dialysis' in row['experiment_types'] and 'pulldown' not in row['experiment_types']
    assert ['dialysis'] in row['group_experiment_types'] and row['excluded'] == {}
    assert row['qualitative']['experiment_refs'] == ['pulldown_1'] and row['qualitative']['experiment_types'] == ['pulldown']             # the dialysis is not also counted as qualitative


def test_a_dialysis_with_only_a_ki_is_pooled_by_its_ki_and_its_own_spread():
    row = merge_binding([dialysis_ki(), *sixteen_earlier()])
    effect, variance = pooled([*SIXTEEN[0], 35.0], [*SIXTEEN[1], 4])
    assert row['cells']['measured_effect']['value'] == pytest.approx(effect, rel=1e-9) and row['cells']['effect_variance']['value'] == pytest.approx(variance, rel=1e-9)
    assert row['counts'] == {'experiments': 17, 'independent_groups': 16} and 'dialysis' in row['experiment_types']


def test_adding_a_qualitative_dialysis_to_a_row_with_a_quantitative_dialysis_changes_nothing_in_the_pool():
    quantitative = merge_binding([dialysis(), *sixteen_earlier()])
    both = merge_binding([dialysis_qualitative(), dialysis(), *sixteen_earlier()])
    assert both['cells'] == quantitative['cells'] and both['experiment_types'] == quantitative['experiment_types']
    assert both['counts'] == {'experiments': 18, 'independent_groups': 16} and both['qualitative']['statements']['dial_q_1'] == 'interaction_detected'


def test_a_failed_control_of_a_qualitative_dialysis_makes_the_row_controls_conflicting_though_the_others_are_supported():
    bad = dialysis_qualitative(buffer_only_control_equal='no')                             # the ligand did not equalise across the membrane without protein
    row = merge_binding([bad, spa(), *all_earlier()])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['binding_regime'] == 'supported'
    assert merge_binding([spa(), *all_earlier()])['interpretations']['binding_controls'] == 'supported'


def test_a_qualitative_dialysis_alone_gives_a_row_with_no_effect_but_its_interpretations_and_statement():
    row = merge_binding([dialysis_qualitative()])
    assert {name: cell['status'] for name, cell in row['cells'].items()} == dict.fromkeys(('measured_effect', 'effect_variance', 'effect_precision'), 'unavailable')
    assert row['cells']['measured_effect']['reasons'] == ['no_experiment_with_a_measured_effect'] and row['cells']['measured_effect']['value'] is None
    assert row['counts'] == {'experiments': 1, 'independent_groups': 0} and row['dependence_groups'] == [] and row['experiment_types'] == []
    assert row['excluded'] == {} and row['qualitative']['statements'] == {'dial_q_1': 'interaction_detected'}
    assert set(row['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis'}
    assert set(row['interpretations'].values()) == {'supported'}


def test_a_quantitative_dialysis_alone_gives_its_kd_as_the_row_effect_and_has_no_qualitative_block_entry():
    row = merge_binding([dialysis()])
    assert row['cells']['measured_effect']['value'] == pytest.approx(25.0) and row['cells']['effect_variance']['value'] == pytest.approx(9.0) and row['experiment_types'] == ['dialysis']
    assert row['counts'] == {'experiments': 1, 'independent_groups': 1} and row['qualitative']['experiment_refs'] == [] and row['qualitative']['independent_groups'] == 0
    assert set(row['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_a_dialysis_that_saw_no_binding_is_reported_as_not_detected():
    row = merge_binding([dialysis_qualitative(binding_detected='no'), spr()])
    assert row['qualitative']['statements'] == {'dial_q_1': 'interaction_not_detected'} and row['interpretations']['binding_parameter_definition'] == 'conflicting'


def test_dialysis_preparations_that_are_a_protein_of_another_method_are_one_preparation():
    for make in (dialysis, dialysis_qualitative):
        for other in (spr(immobilized='prep_shared'), spr(analyte='prep_shared'), itc(cell='prep_shared'), itc(syringe='prep_shared'), bli(immobilized='prep_shared'), gci(analyte='prep_shared'), fp(tracer='prep_shared'),
                      fret(titrant='prep_shared'), mst(fixed='prep_shared'), trp(titrant='prep_shared'), fcs(fixed='prep_shared'), elisa(coated='prep_shared'), alpha(titrant='prep_shared'),
                      radioligand(receptor='prep_shared'), spa(target='prep_shared'), pulldown(bait='prep_shared'), emsa(protein='prep_shared'), emsa(probe='prep_shared'), sec(component_a='prep_shared'), sec(component_b='prep_shared')):
            assert len(dependence_groups([make(ligand='prep_shared'), other])) == 1
            assert len(dependence_groups([make(protein='prep_shared'), other])) == 1
    assert len(dependence_groups([dialysis(), *sixteen_earlier()])) == 17
    assert dialysis()['dependence']['surface_ref'] is None and dialysis_qualitative()['dependence']['surface_ref'] is None


def test_two_dialysis_with_the_same_ligand_are_one_group_and_an_unknown_preparation_is_dependent():
    row = merge_binding([dialysis_qualitative(ref='a', ligand='lig_1'), dialysis_qualitative(ref='b', ligand='lig_1', protein='prot_b2'), dialysis_qualitative(ref='c', ligand='lig_3', protein='prot_c2')])
    assert row['qualitative']['dependence_groups'] == [['a', 'b'], ['c']] and row['qualitative']['independent_groups'] == 2 and row['counts'] == {'experiments': 3, 'independent_groups': 0}
    quantitative = merge_binding([dialysis(ref='a', ligand='lig_1'), dialysis(ref='b', ligand='lig_1', protein='prot_b2', kd=14.0, spread=1.0), dialysis(ref='c', ligand='lig_3', protein='prot_c2', kd=30.0, spread=3.0)])
    assert quantitative['dependence_groups'] == [['a', 'b'], ['c']] and quantitative['counts'] == {'experiments': 3, 'independent_groups': 2}
    record = dialysis_qualitative_record(experiment_ref='unknown_protein')
    record['preparations']['protein_preparation_ref'] = None
    unknown = convert_dialysis(grade_dialysis(record))
    assert len(dependence_groups([unknown, spr()])) == 1 and len(dependence_groups([unknown, dialysis()])) == 1


def test_the_populated_grader_picks_the_dialysis_grader_by_the_records_own_type():
    record = dialysis_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'dialysis' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_dialysis(record) and len(held['grade']['criteria']) == 15
