"""The published PopZ-ParB SPR case (Bowman et al., Cell 2008, PMC2745220) through grader, converter and merger.

The source gives a KD of 20 nM and the experimental setup; it gives no
concentration series for the affinity run, kon/koff, Rmax, fit model,
residuals, spread, replicate count, reference-surface statement, regeneration
or surface-activity information (owner's case record, paper_01_popz_2745220).
The grader must therefore answer unknown for every criterion, the converter
must fill only the effect, and the merger row must carry 20 nM without a
variance.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import CRITERIA, grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import popz_record


def test_popz_grader_every_criterion_unknown_and_kd_retained():
    graded = grade_spr(popz_record())
    assert {name: graded['criteria'][name]['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'unknown')
    assert graded['native']['kd_nM'] == 20.0
    assert graded['native']['kd_from_rates_nM'] is None and graded['native']['rmax_ratio'] is None
    assert graded['native']['quantities']['kd']['source_refs'] == ['span_kd']
    assert graded['reasons']['concentration_series'] == 'kd_or_series_missing'


def test_popz_converter_fills_only_the_effect():
    converted = convert_spr(grade_spr(popz_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == 20.0 and cells['measured_effect']['status'] == 'populated'
    for name in ('effect_variance', 'effect_precision', 'recovery_deviation', 'attributed_fraction', 'condition_response', 'source_log_evidence_ratio'):
        assert cells[name]['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}


def test_popz_merger_row():
    row = merge_binding([convert_spr(grade_spr(popz_record()))])
    assert row['counts'] == {'experiments': 1, 'independent_groups': 1}
    assert row['cells']['measured_effect']['value'] == 20.0
    assert row['cells']['measured_effect']['status'] == 'conditional'
    assert row['cells']['effect_variance']['value'] is None
    assert set(row['interpretations'].values()) == {'unknown'}
