"""The real published ELISA-type solid-phase binding (clusterin and RAP to the VLDLR ectodomain, PMC12527946): what the grader and the
converter make of a record that holds only what the paper's Methods paragraph 'Solid-phase binding assay' states."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_converter import _criterion, convert_elisa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_grader import grade_elisa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.elisa_cases import real_record


def test_the_stated_blank_subtraction_is_supported_the_named_model_has_no_constant_to_support_it_and_everything_else_is_unknown():
    graded = grade_elisa(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}      # as the sheet judges what the grader recorded
    assert [name for name, status in statuses.items() if status == 'supported'] == ['blank_subtraction']
    assert graded['reasons']['fit_model'] == 'model_stated_without_a_reported_constant' and statuses['fit_model'] == 'unknown'
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == [] and graded['reasons']['direct_vs_competition'] == 'kd_or_ki_missing'
    # a 1 h binding step is not shorter than the 30 min minimum, but no statement of equilibrium was made
    assert graded['native']['incubation_min'] == 60 and graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and statuses['equilibrium'] == 'unknown'
    # no KD, EC50, IC50 or Ki value, no plateau or background absorbance, no list of concentrations
    assert graded['native']['constant_name'] is None and graded['reasons']['concentration_series'] == 'constant_or_series_missing'
    assert graded['reasons']['signal_window'] == 'signal_or_background_not_given' and graded['reasons']['detector_range'] == 'fact_unknown'
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown' and graded['reasons']['saturation'] == 'fact_unknown'


def test_the_converter_gives_no_effect_because_the_paragraph_reports_no_binding_constant():
    converted = convert_elisa(grade_elisa(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'unknown'
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['calibration_applicability']['status'] == 'unknown' and interpretations['sampling_basis']['status'] == 'unknown'
