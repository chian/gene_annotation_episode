"""First binding merger with a pull-down / co-immunoprecipitation result (a QUALITATIVE experiment: no binding constant, no effect to pool) together with the thirteen earlier
types (SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand and SPA) for the same binding statement.

The pull-down contributes its interpretations and its qualitative statement; it adds nothing to the pooled effect, the variance or the counts of the experiments with a constant.
The numbers of the other types are those of the SPA merger test (SPR 3 nM -> variance 9 and so on; the thirteen variances 196, 169, ... 4, 36, 49)."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import fact
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_populated_grader import populated_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import convert_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import grade_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.pulldown_cases import real_record as pulldown_real_record, synthetic_record as pulldown_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.radioligand_cases import synthetic_record as radioligand_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_spa import (
    alpha, all_earlier, bli, elisa, fcs, fp, fret, gci, itc, mst, radioligand, spa, spr, trp)


def pulldown(ref='pulldown_1', bait='pulldown_bait_1', prey='pulldown_prey_1', **changes):
    record = pulldown_record(experiment_ref=ref, bait_prep=bait, prey_prep=prey, dataset='pulldown_data_' + ref)
    for name, answer in changes.items():
        record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
    return convert_pulldown(grade_pulldown(record))


def test_a_pulldown_beside_an_spr_does_not_change_the_pooled_effect_and_is_listed_as_qualitative():
    row = merge_binding([pulldown(), spr(kd=30.0, spread=3.0)])
    assert row['cells']['measured_effect']['value'] == pytest.approx(30.0) and row['cells']['effect_variance']['value'] == pytest.approx(9.0)     # the SPR alone: 3 nM squared
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1} and row['excluded'] == {}
    assert row['experiment_types'] == ['spr'] and row['group_experiment_types'] == [['spr']]
    assert row['qualitative']['experiment_refs'] == ['pulldown_1'] and row['qualitative']['experiment_types'] == ['pulldown']
    assert row['qualitative']['statements'] == {'pulldown_1': 'interaction_detected'} and row['qualitative']['support_refs'] == {'pulldown_1': ['span_pulldown_1']}
    assert row['qualitative']['dependence_groups'] == [['pulldown_1']] and row['qualitative']['independent_groups'] == 1


def test_a_pulldown_with_the_thirteen_earlier_types_leaves_their_pool_unchanged_and_adds_its_controls():
    with_pulldown = merge_binding([pulldown(), spa(), *all_earlier()])
    without = merge_binding([spa(), *all_earlier()])
    assert with_pulldown['cells'] == without['cells']                                          # 13 groups, the same effect and variance
    variances = [196, 169, 144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49]
    effects = [140.0, 130.0, 120.0, 110.0, 100.0, 90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]
    weights = [1 / v for v in variances]
    assert with_pulldown['cells']['measured_effect']['value'] == pytest.approx(sum(w * e for w, e in zip(weights, effects)) / sum(weights), rel=1e-9)
    assert with_pulldown['counts'] == {'experiments': 14, 'independent_groups': 13} and len(with_pulldown['experiment_types']) == 13 and 'pulldown' not in with_pulldown['experiment_types']
    assert with_pulldown['qualitative']['experiment_types'] == ['pulldown']
    assert with_pulldown['interpretations']['binding_controls'] == 'supported' and with_pulldown['interpretations']['binding_regime'] == 'supported'
    assert with_pulldown['interpretations']['sampling_basis'] == 'supported' and with_pulldown['interpretations']['binding_species'] == 'unknown'     # the other types do not select it


def test_a_failed_control_of_the_pulldown_makes_the_row_controls_conflicting_though_the_thirteen_are_supported():
    bad = pulldown(prey_absent_in_negative_control='no')                                   # the prey sticks to the control
    row = merge_binding([bad, spa(), *all_earlier()])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['binding_regime'] == 'supported'
    assert merge_binding([spa(), *all_earlier()])['interpretations']['binding_controls'] == 'supported'


def test_a_pulldown_alone_gives_a_row_with_no_effect_but_its_interpretations_and_statement():
    row = merge_binding([pulldown()])
    assert {name: cell['status'] for name, cell in row['cells'].items()} == dict.fromkeys(('measured_effect', 'effect_variance', 'effect_precision'), 'unavailable')
    assert row['cells']['measured_effect']['reasons'] == ['no_experiment_with_a_measured_effect'] and row['cells']['measured_effect']['value'] is None
    assert row['counts'] == {'experiments': 1, 'independent_groups': 0} and row['dependence_groups'] == [] and row['experiment_types'] == []
    assert row['excluded'] == {} and row['qualitative']['statements'] == {'pulldown_1': 'interaction_detected'}
    assert set(row['interpretations']) == {'binding_controls', 'binding_regime', 'binding_species', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis'}
    assert set(row['interpretations'].values()) == {'supported'}


def test_a_pulldown_that_found_no_interaction_is_reported_as_not_detected():
    row = merge_binding([pulldown(prey_detected_in_eluate='no'), spr()])
    assert row['qualitative']['statements'] == {'pulldown_1': 'interaction_not_detected'} and row['interpretations']['binding_parameter_definition'] == 'conflicting'


def test_pulldown_preparations_that_are_a_protein_of_another_method_are_one_preparation():
    for other in (spr(immobilized='prep_shared'), spr(analyte='prep_shared'), itc(cell='prep_shared'), itc(syringe='prep_shared'), bli(immobilized='prep_shared'), gci(analyte='prep_shared'), fp(tracer='prep_shared'),
                  fret(titrant='prep_shared'), mst(fixed='prep_shared'), trp(titrant='prep_shared'), fcs(fixed='prep_shared'), elisa(coated='prep_shared'), alpha(titrant='prep_shared'),
                  radioligand(receptor='prep_shared'), spa(target='prep_shared')):
        assert len(dependence_groups([pulldown(prey='prep_shared'), other])) == 1
        assert len(dependence_groups([pulldown(bait='prep_shared'), other])) == 1
    assert len(dependence_groups([pulldown(), spa(), *all_earlier()])) == 14
    assert pulldown()['dependence']['surface_ref'] is None


def test_two_pulldowns_with_the_same_bait_are_one_qualitative_group_and_an_unknown_preparation_is_dependent():
    row = merge_binding([pulldown(ref='a', bait='bait_1'), pulldown(ref='b', bait='bait_1', prey='prey_b'), pulldown(ref='c', bait='bait_3', prey='prey_c')])
    assert row['qualitative']['dependence_groups'] == [['a', 'b'], ['c']] and row['qualitative']['independent_groups'] == 2 and row['counts'] == {'experiments': 3, 'independent_groups': 0}
    record = pulldown_record(experiment_ref='unknown_bait')
    record['preparations']['bait_preparation_ref'] = None
    unknown = convert_pulldown(grade_pulldown(record))
    assert len(dependence_groups([unknown, spr()])) == 1 and len(dependence_groups([unknown, pulldown()])) == 1


def test_the_real_pulldown_case_is_taken_in_beside_an_spr_without_an_effect():
    real = convert_pulldown(grade_pulldown(pulldown_real_record()))
    row = merge_binding([real, spr()])
    assert row['qualitative']['statements'] == {'exp_recq1_ku_coip': 'interaction_detected'} and row['qualitative']['support_refs'] == {'exp_recq1_ku_coip': ['span_detected']}
    assert row['experiment_types'] == ['spr'] and row['excluded'] == {} and row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['interpretations']['binding_controls'] == 'unknown'          # the paragraph states four controls' results and no input lane, bait-minus or specificity control
    assert row['cells']['measured_effect']['value'] == pytest.approx(30.0)


def test_the_populated_grader_picks_the_pulldown_grader_by_the_records_own_type():
    record = pulldown_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'pulldown' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_pulldown(record) and len(held['grade']['criteria']) == 16
    other = populated_grader('record_ref_2', radioligand_record())
    assert other['experiment_type'] == 'radioligand' and len(other['grade']['criteria']) == 15
