"""The real published TR-FRET case (CoraFluor-1 labelled KLHL11 and AF488-labelled CUL3 N-terminal domain, PMC10564622): what
the grader and the converter make of a record that holds only what the Results paragraph states."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import _criterion, convert_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_grader import grade_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import real_record


def test_only_the_labelling_scheme_is_decided_and_nothing_conflicts():
    graded = grade_fret(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}       # the sheet judges what the grader only records
    assert [name for name, status in statuses.items() if status == 'supported'] == ['labelling_scheme']
    assert 'conflicting' not in statuses.values() and set(statuses.values()) <= {'supported', 'unknown', 'not_applicable'}
    assert graded['reasons']['labelling_scheme'] == 'labelling_shown_not_to_alter_binding'
    assert graded['native']['kd_nM'] == pytest.approx(20.0)
    # TR-FRET is stated but the paragraph gives no delay; no ratio ends, labelled concentrations, series, model or replicate count
    assert graded['reasons']['time_gating'] == 'delay_not_stated'
    assert graded['reasons']['assay_window'] == 'minimum_or_maximum_missing'
    assert graded['reasons']['labelled_concentration'] == 'labelled_or_kd_missing'
    assert graded['reasons']['concentration_series'] == 'constant_or_series_missing'
    assert graded['reasons']['fit_model'] == 'fit_model_not_stated'
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    assert graded['reasons']['spectral_crosstalk'] == 'fact_unknown'


def test_the_converter_gives_the_effect_and_no_variance_because_the_interval_is_given_by_its_limits():
    converted = convert_fret(grade_fret(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(20.0) and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert converted['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'      # the fit and the readout are not stated
    assert converted['extraction']['interpretations']['binding_controls']['status'] == 'unknown'
    assert converted['extraction']['interpretations']['calibration_applicability']['status'] == 'unknown'
