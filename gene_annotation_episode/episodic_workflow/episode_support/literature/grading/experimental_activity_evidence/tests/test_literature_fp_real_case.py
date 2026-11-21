"""The real published FP case (FAM-LANA1-22 and nucleosomes, PMC10606924): what the grader and the converter make of a
record that holds only what the Results paragraph states."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import _criterion, convert_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_grader import grade_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import real_record


def test_only_the_tracer_concentration_is_decided_and_nothing_conflicts():
    graded = grade_fp(real_record())
    assert graded['criteria']['tracer_concentration']['status'] == 'unknown' and graded['reasons']['tracer_concentration'] == 'tracer_over_kd_recorded_for_the_sheet'      # the grader only records the ratio
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}       # the sheet judges it
    # tracer 100 nM and Kd 0.4 uM = 400 nM: 0.25 x KD, below the limit of 1 x KD
    assert [name for name, status in statuses.items() if status == 'supported'] == ['tracer_concentration']
    assert 'conflicting' not in statuses.values() and set(statuses.values()) <= {'supported', 'unknown', 'not_applicable'}
    assert graded['native']['tracer_over_kd'] == pytest.approx(0.25) and graded['native']['kd_nM'] == pytest.approx(400.0)
    # no window, no series values, no model, no replicate count in the paragraph
    assert graded['reasons']['assay_window'] == 'minimum_or_maximum_missing'
    assert graded['reasons']['concentration_series'] == 'constant_or_series_missing'
    assert graded['reasons']['fit_model'] == 'fit_model_not_stated'
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    assert graded['reasons']['surface_adsorption'] == 'fact_unknown'


def test_the_converter_gives_the_effect_and_no_variance_because_the_spread_kind_is_not_stated():
    converted = convert_fp(grade_fp(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(400.0) and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'spread_kind_not_stated'
    assert converted['extraction']['interpretations']['binding_regime']['status'] == 'unknown'
    assert converted['extraction']['interpretations']['binding_controls']['status'] == 'unknown'
