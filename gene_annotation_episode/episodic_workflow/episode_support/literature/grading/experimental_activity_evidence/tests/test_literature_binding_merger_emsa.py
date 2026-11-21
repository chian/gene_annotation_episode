"""First binding merger with an EMSA (electrophoretic mobility shift assay) result together with the fourteen earlier types (SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS,
ELISA, AlphaScreen, radioligand, SPA and pull-down) for the same binding statement.

An EMSA has two shapes and the merger's contract is unchanged for both. With an apparent KD it is a QUANTITATIVE result: its KD is pooled like that of any other type
(inverse-variance across independent groups) and it carries no qualitative effect. Without a KD it is a QUALITATIVE result, like the pull-down: it adds nothing to the pooled effect,
the variance or the counts of the experiments with a constant, and contributes its interpretations and its statement (the row's qualitative block).
The numbers of the other types are those of the SPA merger test (SPR 3 nM -> variance 9 and so on; the thirteen variances 196, 169, ... 4, 36, 49); the quantitative EMSA adds
10 nM with a variance of 1 (a standard error of 1 nM)."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import fact
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import dependence_groups, merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import convert_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import grade_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_populated_grader import populated_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.emsa_cases import (
    qualitative_record as emsa_qualitative_record, real_record as emsa_real_record, synthetic_record as emsa_record)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.radioligand_cases import synthetic_record as radioligand_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_pulldown import pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_spa import (
    alpha, all_earlier, bli, elisa, fcs, fp, fret, gci, itc, mst, radioligand, spa, spr, trp)

VARIANCES = [196, 169, 144, 121, 100, 81, 64, 9, 16, 25, 4, 36, 49]        # spa, radioligand, alpha, elisa, fcs, trp, mst, spr, itc, bli, gci, fret, fp (in the order of the 13 below)
EFFECTS = [140.0, 130.0, 120.0, 110.0, 100.0, 90.0, 80.0, 30.0, 40.0, 50.0, 20.0, 60.0, 70.0]


def emsa(ref='emsa_1', protein='emsa_protein_1', probe='emsa_probe_1', kd=10.0, spread=1.0, **changes):
    """A quantitative EMSA: an apparent KD of ``kd`` nM with a standard error of ``spread`` nM."""
    record = emsa_record(experiment_ref=ref, probe_prep=probe, protein_prep=protein, dataset='emsa_data_' + ref, kd=kd, spread=spread)
    for name, answer in changes.items():
        record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
    return convert_emsa(grade_emsa(record))


def emsa_qualitative(ref='emsa_q_1', protein='emsa_q_protein_1', probe='emsa_q_probe_1', **changes):
    """A qualitative EMSA: a shift and its controls, no apparent KD."""
    record = emsa_qualitative_record(experiment_ref=ref, probe_prep=probe, protein_prep=protein, dataset='emsa_q_data_' + ref)
    for name, answer in changes.items():
        record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
    return convert_emsa(grade_emsa(record))


def pooled(effects, variances):
    weights = [1 / v for v in variances]
    return sum(w * e for w, e in zip(weights, effects)) / sum(weights), 1 / sum(weights)


def test_a_qualitative_emsa_beside_an_spr_does_not_change_the_pooled_effect_and_is_listed_as_qualitative():
    row = merge_binding([emsa_qualitative(), spr(kd=30.0, spread=3.0)])
    assert row['cells']['measured_effect']['value'] == pytest.approx(30.0) and row['cells']['effect_variance']['value'] == pytest.approx(9.0)     # the SPR alone: 3 nM squared
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1} and row['excluded'] == {}
    assert row['experiment_types'] == ['spr'] and row['group_experiment_types'] == [['spr']]
    assert row['qualitative']['experiment_refs'] == ['emsa_q_1'] and row['qualitative']['experiment_types'] == ['emsa']
    assert row['qualitative']['statements'] == {'emsa_q_1': 'interaction_detected'} and row['qualitative']['support_refs'] == {'emsa_q_1': ['span_emsa_q_1']}
    assert row['qualitative']['dependence_groups'] == [['emsa_q_1']] and row['qualitative']['independent_groups'] == 1


def test_a_qualitative_emsa_with_the_fourteen_earlier_types_leaves_the_numeric_pool_identical():
    base = [pulldown(), spa(), *all_earlier()]
    without = merge_binding(base)
    with_emsa = merge_binding([emsa_qualitative(), *base])
    assert with_emsa['cells'] == without['cells']                                          # the same effect, variance and precision, cell for cell
    effect, variance = pooled(EFFECTS, VARIANCES)
    assert with_emsa['cells']['measured_effect']['value'] == pytest.approx(effect, rel=1e-9) and with_emsa['cells']['effect_variance']['value'] == pytest.approx(variance, rel=1e-9)
    assert with_emsa['counts'] == {'experiments': 15, 'independent_groups': 13} and without['counts'] == {'experiments': 14, 'independent_groups': 13}
    assert len(with_emsa['experiment_types']) == 13 and 'emsa' not in with_emsa['experiment_types'] and with_emsa['excluded'] == {}
    assert with_emsa['qualitative']['experiment_types'] == ['emsa', 'pulldown'] and with_emsa['qualitative']['independent_groups'] == 2
    assert with_emsa['interpretations']['binding_controls'] == 'supported' and with_emsa['interpretations']['binding_regime'] == 'supported'
    assert with_emsa['interpretations']['sampling_basis'] == 'supported' and with_emsa['interpretations']['binding_species'] == 'unknown'     # the other types do not select it


def test_a_quantitative_emsa_is_pooled_with_the_fourteen_earlier_types_as_a_fourteenth_independent_group():
    base = [pulldown(), spa(), *all_earlier()]
    row = merge_binding([emsa(), *base])
    effect, variance = pooled([*EFFECTS, 10.0], [*VARIANCES, 1])
    assert row['cells']['measured_effect']['value'] == pytest.approx(effect, rel=1e-9) and row['cells']['effect_variance']['value'] == pytest.approx(variance, rel=1e-9)
    assert row['cells']['measured_effect']['status'] == 'populated' and row['cells']['effect_precision']['value'] == pytest.approx(1 / variance, rel=1e-9)
    assert row['counts'] == {'experiments': 15, 'independent_groups': 14} and len(row['experiment_types']) == 14 and 'emsa' in row['experiment_types'] and 'pulldown' not in row['experiment_types']
    assert ['emsa'] in row['group_experiment_types'] and row['excluded'] == {}
    assert row['qualitative']['experiment_refs'] == ['pulldown_1'] and row['qualitative']['experiment_types'] == ['pulldown']         # the EMSA is not also counted as qualitative
    assert row['cells']['measured_effect']['value'] < merge_binding(base)['cells']['measured_effect']['value']                       # a precise 10 nM pulls the pool down


def test_adding_a_qualitative_emsa_to_a_row_with_a_quantitative_emsa_changes_nothing_in_the_pool():
    quantitative = merge_binding([emsa(), spa(), *all_earlier()])
    both = merge_binding([emsa_qualitative(), emsa(), spa(), *all_earlier()])
    assert both['cells'] == quantitative['cells'] and both['experiment_types'] == quantitative['experiment_types']
    assert both['counts'] == {'experiments': 15, 'independent_groups': 14} and both['qualitative']['statements'] == {'emsa_q_1': 'interaction_detected'}


def test_a_failed_control_of_a_qualitative_emsa_makes_the_row_controls_conflicting_though_the_others_are_supported():
    bad = emsa_qualitative(mutant_probe_does_not_shift='no')                               # the mutant probe shifted
    row = merge_binding([bad, spa(), *all_earlier()])
    assert row['interpretations']['binding_controls'] == 'conflicting' and row['interpretations']['binding_regime'] == 'supported'
    assert merge_binding([spa(), *all_earlier()])['interpretations']['binding_controls'] == 'supported'


def test_a_qualitative_emsa_alone_gives_a_row_with_no_effect_but_its_interpretations_and_statement():
    row = merge_binding([emsa_qualitative()])
    assert {name: cell['status'] for name, cell in row['cells'].items()} == dict.fromkeys(('measured_effect', 'effect_variance', 'effect_precision'), 'unavailable')
    assert row['cells']['measured_effect']['reasons'] == ['no_experiment_with_a_measured_effect'] and row['cells']['measured_effect']['value'] is None
    assert row['counts'] == {'experiments': 1, 'independent_groups': 0} and row['dependence_groups'] == [] and row['experiment_types'] == []
    assert row['excluded'] == {} and row['qualitative']['statements'] == {'emsa_q_1': 'interaction_detected'}
    assert set(row['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis'}
    assert set(row['interpretations'].values()) == {'supported'}


def test_a_quantitative_emsa_alone_gives_its_kd_as_the_row_effect_and_has_no_qualitative_block_entry():
    row = merge_binding([emsa()])
    assert row['cells']['measured_effect']['value'] == pytest.approx(10.0) and row['cells']['effect_variance']['value'] == pytest.approx(1.0) and row['experiment_types'] == ['emsa']
    assert row['counts'] == {'experiments': 1, 'independent_groups': 1} and row['qualitative']['experiment_refs'] == [] and row['qualitative']['independent_groups'] == 0
    assert set(row['interpretations']) == {'binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis', 'variance_correspondence'}


def test_an_emsa_that_found_no_shift_is_reported_as_not_detected():
    row = merge_binding([emsa_qualitative(shift_detected='no'), spr()])
    assert row['qualitative']['statements'] == {'emsa_q_1': 'interaction_not_detected'} and row['interpretations']['binding_parameter_definition'] == 'conflicting'


def test_emsa_preparations_that_are_a_protein_of_another_method_are_one_preparation():
    for make in (emsa, emsa_qualitative):
        for other in (spr(immobilized='prep_shared'), spr(analyte='prep_shared'), itc(cell='prep_shared'), itc(syringe='prep_shared'), bli(immobilized='prep_shared'), gci(analyte='prep_shared'), fp(tracer='prep_shared'),
                      fret(titrant='prep_shared'), mst(fixed='prep_shared'), trp(titrant='prep_shared'), fcs(fixed='prep_shared'), elisa(coated='prep_shared'), alpha(titrant='prep_shared'),
                      radioligand(receptor='prep_shared'), spa(target='prep_shared'), pulldown(bait='prep_shared')):
            assert len(dependence_groups([make(protein='prep_shared'), other])) == 1
            assert len(dependence_groups([make(probe='prep_shared'), other])) == 1
    assert len(dependence_groups([emsa(), pulldown(), spa(), *all_earlier()])) == 15
    assert emsa()['dependence']['surface_ref'] is None and emsa_qualitative()['dependence']['surface_ref'] is None


def test_two_emsa_with_the_same_probe_are_one_group_and_an_unknown_preparation_is_dependent():
    row = merge_binding([emsa_qualitative(ref='a', probe='probe_1'), emsa_qualitative(ref='b', probe='probe_1', protein='protein_b'), emsa_qualitative(ref='c', probe='probe_3', protein='protein_c')])
    assert row['qualitative']['dependence_groups'] == [['a', 'b'], ['c']] and row['qualitative']['independent_groups'] == 2 and row['counts'] == {'experiments': 3, 'independent_groups': 0}
    quantitative = merge_binding([emsa(ref='a', probe='probe_1'), emsa(ref='b', probe='probe_1', protein='protein_b', kd=14.0, spread=1.0), emsa(ref='c', probe='probe_3', protein='protein_c', kd=30.0, spread=3.0)])
    assert quantitative['dependence_groups'] == [['a', 'b'], ['c']] and quantitative['counts'] == {'experiments': 3, 'independent_groups': 2}
    record = emsa_qualitative_record(experiment_ref='unknown_probe')
    record['preparations']['probe_preparation_ref'] = None
    unknown = convert_emsa(grade_emsa(record))
    assert len(dependence_groups([unknown, spr()])) == 1 and len(dependence_groups([unknown, emsa()])) == 1


def test_the_real_emsa_case_is_pooled_with_its_kd_but_has_no_variance_so_the_row_variance_is_unavailable():
    real = convert_emsa(grade_emsa(emsa_real_record()))
    row = merge_binding([real, spr()])
    assert row['experiment_types'] == ['emsa', 'spr'] and row['excluded'] == {} and row['qualitative']['experiment_refs'] == []
    assert row['counts'] == {'experiments': 2, 'independent_groups': 1}                    # the real record's preparations are unknown, so it is dependent on the SPR
    assert row['cells']['measured_effect']['value'] == pytest.approx(20.5) and row['cells']['measured_effect']['status'] == 'conditional'     # the mean of 11 and 30 nM
    assert row['cells']['effect_variance']['value'] is None and row['cells']['effect_variance']['reasons'] == ['variance_unavailable_for_at_least_one_independent_group']
    assert row['interpretations']['binding_controls'] == 'unknown'          # the paragraph states a competitor and a purified protein and no mutant probe or probe-alone lane


def test_the_populated_grader_picks_the_emsa_grader_by_the_records_own_type():
    record = emsa_record()
    held = populated_grader('record_ref_1', record)
    assert held['experiment_type'] == 'emsa' and held['record_ref'] == 'record_ref_1'
    assert held['grade'] == grade_emsa(record) and len(held['grade']['criteria']) == 17
    other = populated_grader('record_ref_2', radioligand_record())
    assert other['experiment_type'] == 'radioligand' and len(other['grade']['criteria']) == 15
