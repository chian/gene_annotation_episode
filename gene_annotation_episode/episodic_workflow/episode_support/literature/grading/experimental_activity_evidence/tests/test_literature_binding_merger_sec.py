"""First binding merger with an SEC (size-exclusion chromatography, with or without MALS) result together with the fifteen earlier types (SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS,
ELISA, AlphaScreen, radioligand, SPA, pull-down and EMSA) for the same binding statement.

An SEC has two shapes and the merger's contract is unchanged for both (this file changes nothing in the merger or in the pull-down and EMSA converters). With an apparent KD from peak areas
it is a QUANTITATIVE result: its KD is pooled like that of any other type (inverse-variance across independent groups) and it carries no qualitative effect. Without a KD (the usual case) it is a
QUALITATIVE result, like the pull-down and the EMSA without a KD: it adds nothing to the pooled effect, the variance or the counts of the experiments with a constant, and contributes its
interpretations and its statement (the row's qualitative block).
The numbers of the other types are those of the EMSA merger test (SPR 3 nM -> variance 9 and so on; the thirteen variances 196, 169, ... 4, 36, 49; the EMSA 10 nM with a variance of 1); the quantitative
SEC adds 15 nM with a variance of 4 (a standard error of 2 nM)."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import convert_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_grader import grade_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_populated_grader import populated_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.sec_cases import (
    qualitative_record as sec_qualitative_record, real_record as sec_real_record, synthetic_record as sec_record)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_emsa import emsa, emsa_qualitative
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_pulldown import pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_spa import (
    alpha, all_earlier, bli, elisa, fcs, fp, fret, gci, itc, mst, radioligand, spa, spr, trp)

VARIANCES = [196, 169, 144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49]        # spa, radioligand, alpha, elisa, fcs, trp, mst, spr, itc, bli, gci, fret, fp
EFFECTS = [140.0, 130.0, 120.0, 110.0, 100.0, 90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]


def sec(ref='sec_1', component_a='sec_a_1', component_b='sec_b_1', kd=15.0, spread=2.0, **changes):
    """A quantitative SEC: an apparent KD of ``kd`` nM from peak areas with a standard error of ``spread`` nM."""
    record = sec_record(experiment_ref=ref, component_a=component_a, component_b=component_b, dataset='sec_data_' + ref, kd=kd, spread=spread)
    for name, answer in changes.items():
        record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
    return convert_sec(grade_sec(record))


def sec_qualitative(ref='sec_q_1', component_a='sec_q_a_1', component_b='sec_q_b_1', **changes):
    """A qualitative SEC: a complex peak and its controls, no apparent KD."""
    record = sec_qualitative_record(experiment_ref=ref, component_a=component_a, component_b=component_b, dataset='sec_q_data_' + ref)
    for name, answer in changes.items():
        record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
    return convert_sec(grade_sec(record))


def pooled(effects, variances):
    weights = [1 / v for v in variances]
    return sum(w * e for w, e in zip(weights, effects)) / sum(weights), 1 / sum(weights)


def fifteen_earlier():
    return [emsa(), pulldown(), spa(), *all_earlier()]


def sec_with_mass(ref, component_a, component_b, measured, **kwargs):
    record = sec_record(experiment_ref=ref, component_a=component_a, component_b=component_b, dataset='sec_data_' + ref, kd=15.0, spread=2.0)
    record['quantities']['complex_mass_theoretical'] = point(100.0, 'kDa', 't', ['s_theory'])
    record['quantities']['complex_mass_measured'] = point(measured, 'kDa', 'm', ['s_mass'])
    return convert_sec(grade_sec(record))


def test_the_degrees_of_the_results_are_carried_per_result_and_the_pooled_numbers_do_not_change():
    full = sec_with_mass('sec_full', 'a_full', 'b_full', 100.0)
    partial = sec_with_mass('sec_partial', 'a_part', 'b_part', 70.0)
    row = merge_binding([full, partial])
    assert row['interpretation_degrees'] == {'binding_parameter_definition': {'sec_full': 1.0, 'sec_partial': pytest.approx(0.5)}}      # each result keeps its own degree, none is averaged
    assert row['interpretations']['binding_parameter_definition'] == 'supported'                                                      # the row's status rule ignores the degree
    plain = merge_binding([sec(ref='sec_full', component_a='a_full', component_b='b_full'), sec(ref='sec_partial', component_a='a_part', component_b='b_part')])
    assert plain['interpretation_degrees'] == {'binding_parameter_definition': {'sec_full': 1.0, 'sec_partial': 1.0}}                  # the default records' masses agree to 4 percent
    for name in ('measured_effect', 'effect_variance', 'effect_precision'):
        assert row['cells'][name] == plain['cells'][name]
    alone = merge_binding([partial])
    assert alone['cells']['effect_variance']['value'] == pytest.approx(4.0) and alone['interpretation_degrees'] == {'binding_parameter_definition': {'sec_partial': pytest.approx(0.5)}}


def test_a_qualitative_sec_beside_an_spr_does_not_change_the_pooled_effect_and_is_listed_as_qualitative():
    row = merge_binding([sec_qualitative(), spr(kd=30.0, spread=3.0)])
    assert row['cells']['measured_effect']['value'] == pytest.approx(30.0) and row['cells']['effect_variance']['value'] == pytest.approx(9.0)     # the SPR alone: 3 nM squared
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1} and row['excluded'] == {}
    assert row['experiment_types'] == ['spr'] and row['group_experiment_types'] == [['spr']]
    assert row['qualitative']['experiment_refs'] == ['sec_q_1'] and row['qualitative']['experiment_types'] == ['sec']
    assert row['qualitative']['statements'] == {'sec_q_1': 'interaction_detected'} and row['qualitative']['support_refs'] == {'sec_q_1': ['span_sec_q_1']}
    assert row['qualitative']['dependence_groups'] == [['sec_q_1']] and row['qualitative']['independent_groups'] == 1


def test_a_qualitative_sec_with_the_fifteen_earlier_types_leaves_the_numeric_pool_identical():
    base = fifteen_earlier()
    without = merge_binding(base)
    with_sec = merge_binding([sec_qualitative(), *base])
    assert with_sec['cells'] == without['cells']                                           # the same effect, variance and precision, cell for cell
    effect, variance = pooled([*EFFECTS, 10.0], [*VARIANCES, 1])
    assert with_sec['cells']['measured_effect']['value'] == pytest.approx(effect, rel=1e-9) and with_sec['cells']['effect_variance']['value'] == pytest.approx(variance, rel=1e-9)
    assert with_sec['counts'] == {'experiments': 16, 'independent_groups': 14} and without['counts'] == {'experiments': 15, 'independent_groups': 14}
    assert len(with_sec['experiment_types']) == 14 and 'sec' not in with_sec['experiment_types'] and 'emsa' in with_sec['experiment_types'] and with_sec['excluded'] == {}
    assert with_sec['qualitative']['experiment_types'] == ['pulldown', 'sec'] and with_sec['qualitative']['independent_groups'] == 2
    assert with_sec['interpretations']['binding_controls'] == 'supported' and with_sec['interpretations']['binding_regime'] == 'supported'
    assert with_sec['interpretations']['sampling_basis'] == 'supported' and with_sec['interpretations']['binding_species'] == 'unknown'     # the other types do not select it


def test_a_qualitative_sec_and_a_qualitative_emsa_together_leave_the_numeric_pool_identical():
    base = fifteen_earlier()
    both = merge_binding([sec_qualitative(), emsa_qualitative(), *base])
    assert both['cells'] == merge_binding(base)['cells']
    assert both['counts'] == {'experiments': 17, 'independent_groups': 14} and both['qualitative']['experiment_types'] == ['emsa', 'pulldown', 'sec'] and both['qualitative']['independent_groups'] == 3


def test_a_quantitative_sec_is_pooled_with_the_fifteen_earlier_types_as_a_fifteenth_independent_group():
    base = fifteen_earlier()
    row = merge_binding([sec(), *base])
    effect, variance = pooled([*EFFECTS, 10.0, 15.0], [*VARIANCES, 1, 4])
    assert row['cells']['measured_effect']['value'] == pytest.approx(effect, rel=1e-9) and row['cells']['effect_variance']['value'] == pytest.approx(variance, rel=1e-9)
    assert row['cells']['measured_effect']['status'] == 'populated' and row['cells']['effect_precision']['value'] == pytest.approx(1 / variance, rel=1e-9)
    assert row['counts'] == {'experiments': 16, 'independent_groups': 15} and len(row['experiment_types']) == 15 and 'sec' in row['experiment_types'] and 'pulldown' not in row['experiment_types']
    assert ['sec'] in row['group_experiment_types'] and row['excluded'] == {}
    assert row['qualitative']['experiment_refs'] == ['pulldown_1'] and row['qualitative']['experiment_types'] == ['pulldown']             # the SEC is not also counted as qualitative


def test_adding_a_qualitative_sec_to_a_row_with_a_quantitative_sec_changes_nothing_in_the_pool():
    quantitative = merge_binding([sec(), *fifteen_earlier()])
    both = merge_binding([sec_qualitative(), sec(), *fifteen_earlier()])
    assert both['cells'] == quantitative['cells'] and both['experiment_types'] == quantitative['experiment_types']
    assert both['counts'] == {'experiments': 17, 'independent_groups': 15} and both['qualitative']['statements'] == {'pulldown_1': both['qualitative']['statements']['pulldown_1'], 'sec_q_1': 'interaction_detected'}


def test_a_failed_control_of_a_qualitative_sec_makes_the_row_controls_conflicting_though_the_others_are_supported():
    bad = sec_qualitative(single_component_control_done='no')                              # the non-binding mutant co-eluted
    row = merge_binding([bad, spa(), *all_earlier()])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['binding_regime'] == 'supported'
    assert merge_binding([spa(), *all_earlier()])['interpretations']['binding_controls'] == 'supported'


def test_a_qualitative_sec_alone_gives_a_row_with_no_effect_but_its_interpretations_and_statement():
    row = merge_binding([sec_qualitative()])
    assert {name: cell['status'] for name, cell in row['cells'].items()} == dict.fromkeys(('measured_effect', 'effect_variance', 'effect_precision'), 'unavailable')
    assert row['cells']['measured_effect']['reasons'] == ['no_experiment_with_a_measured_effect'] and row['cells']['measured_effect']['value'] is None
    assert row['counts'] == {'experiments': 1, 'independent_groups': 0} and row['dependence_groups'] == [] and row['experiment_types'] == []
    assert row['excluded'] == {} and row['qualitative']['statements'] == {'sec_q_1': 'interaction_detected'}
    assert set(row['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis'}
    assert set(row['interpretations'].values()) == {'supported'}


def test_a_quantitative_sec_alone_gives_its_kd_as_the_row_effect_and_has_no_qualitative_block_entry():
    row = merge_binding([sec()])
    assert row['cells']['measured_effect']['value'] == pytest.approx(15.0) and row['cells']['effect_variance']['value'] == pytest.approx(4.0) and row['experiment_types'] == ['sec']
    assert row['counts'] == {'experiments': 1, 'independent_groups': 1} and row['qualitative']['experiment_refs'] == [] and row['qualitative']['independent_groups'] == 0
    assert set(row['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_an_sec_that_found_no_complex_peak_is_reported_as_not_detected():
    row = merge_binding([sec_qualitative(complex_peak_detected='no'), spr()])
    assert row['qualitative']['statements'] == {'sec_q_1': 'interaction_not_detected'} and row['interpretations']['binding_parameter_definition'] == 'conflicting'


def test_sec_preparations_that_are_a_protein_of_another_method_are_one_preparation():
    for make in (sec, sec_qualitative):
        for other in (spr(immobilized='prep_shared'), spr(analyte='prep_shared'), itc(cell='prep_shared'), itc(syringe='prep_shared'), bli(immobilized='prep_shared'), gci(analyte='prep_shared'), fp(tracer='prep_shared'),
                      fret(titrant='prep_shared'), mst(fixed='prep_shared'), trp(titrant='prep_shared'), fcs(fixed='prep_shared'), elisa(coated='prep_shared'), alpha(titrant='prep_shared'),
                      radioligand(receptor='prep_shared'), spa(target='prep_shared'), pulldown(bait='prep_shared'), emsa(protein='prep_shared'), emsa(probe='prep_shared')):
            assert len(dependence_groups([make(component_a='prep_shared'), other])) == 1
            assert len(dependence_groups([make(component_b='prep_shared'), other])) == 1
    assert len(dependence_groups([sec(), *fifteen_earlier()])) == 16
    assert sec()['dependence']['surface_ref'] is None and sec_qualitative()['dependence']['surface_ref'] is None


def test_two_sec_with_the_same_component_are_one_group_and_an_unknown_preparation_is_dependent():
    row = merge_binding([sec_qualitative(ref='a', component_a='comp_1'), sec_qualitative(ref='b', component_a='comp_1', component_b='comp_b2'), sec_qualitative(ref='c', component_a='comp_3', component_b='comp_c2')])
    assert row['qualitative']['dependence_groups'] == [['a', 'b'], ['c']] and row['qualitative']['independent_groups'] == 2 and row['counts'] == {'experiments': 3, 'independent_groups': 0}
    quantitative = merge_binding([sec(ref='a', component_a='comp_1'), sec(ref='b', component_a='comp_1', component_b='comp_b2', kd=14.0, spread=1.0), sec(ref='c', component_a='comp_3', component_b='comp_c2', kd=30.0, spread=3.0)])
    assert quantitative['dependence_groups'] == [['a', 'b'], ['c']] and quantitative['counts'] == {'experiments': 3, 'independent_groups': 2}
    record = sec_qualitative_record(experiment_ref='unknown_component')
    record['preparations']['component_b_preparation_ref'] = None
    unknown = convert_sec(grade_sec(record))
    assert len(dependence_groups([unknown, spr()])) == 1 and len(dependence_groups([unknown, sec()])) == 1


def test_the_real_sec_case_is_qualitative_so_it_leaves_the_pool_of_an_spr_alone_and_its_unknowns_make_the_row_interpretations_unknown():
    real = convert_sec(grade_sec(sec_real_record()))
    row = merge_binding([real, spr(kd=30.0, spread=3.0)])
    assert row['cells']['measured_effect']['value'] == pytest.approx(30.0) and row['cells']['effect_variance']['value'] == pytest.approx(9.0)
    assert row['experiment_types'] == ['spr'] and row['excluded'] == {} and row['qualitative']['experiment_refs'] == ['exp_mcu_mcub_ntd_sec_mals']
    assert row['qualitative']['statements'] == {'exp_mcu_mcub_ntd_sec_mals': 'interaction_detected'} and row['qualitative']['support_refs'] == {'exp_mcu_mcub_ntd_sec_mals': ['span_peak']}
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}
    assert row['interpretations']['binding_controls'] == 'unknown'          # the paragraph states the proteins alone and SDS-PAGE and no single-component control, resin or aggregation statement


def test_the_populated_grader_picks_the_sec_grader_by_the_records_own_type():
    record = sec_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'sec' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_sec(record) and len(held['grade']['criteria']) == 13
