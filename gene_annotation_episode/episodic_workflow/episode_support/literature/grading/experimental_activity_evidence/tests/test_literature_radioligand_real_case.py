"""The real published apelin receptor radioligand binding analysis (Nature Communications 15, 10714, 2024, doi 10.1038/s41467-024-55381-w,
PMC11680790): what the grader and the converter make of a record that holds only what the paper's Methods paragraph on the analysis of
the binding data states as part of the experiment (the specific activity of the radiolabel 2200 Ci/mmol, the radiolabel concentration of
the competition fit 0.1 nM, a non-linear fit of the saturation data). The paragraph's 'known KD value of the radiolabel (0.076 nM)' is a
value cited from elsewhere, not measured in the experiment, so the record does not hold it (owner's decision): without a KD the
radiolabel level cannot be judged against it, and no criterion conflicts."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import convert_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import grade_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.radioligand_cases import real_record


def test_the_nonlinear_fit_is_supported_and_everything_else_is_unknown():
    graded = grade_radioligand(real_record())
    statuses = {name: item['status'] for name, item in graded['criteria'].items()}
    assert [name for name, status in statuses.items() if status == 'supported'] == ['nonlinear_fit']
    assert graded['criteria']['nonlinear_fit']['support_refs'] == ['span_nonlinear']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == []
    assert graded['reasons']['competition_radioligand_level'] == 'radioligand_concentration_or_kd_not_given'
    assert graded['reasons']['ligand_depletion'] == 'fact_unknown' and graded['reasons']['nonspecific_excess'] == 'excess_not_given'
    assert graded['reasons']['radioligand_range'] == 'kd_or_series_missing' and graded['reasons']['equilibrium'] == 'fact_unknown'
    assert graded['reasons']['fit_model'] == 'fit_model_not_stated' and graded['reasons']['cheng_prusoff'] == 'fact_unknown'
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown' and graded['native']['incubation_min'] is None
    assert graded['native']['kd_nM'] is None and graded['native']['constant_name'] is None and graded['native']['radioligand_nM'] == 0.1


def test_the_converter_gives_no_effect_because_no_kd_was_measured():
    converted = convert_radioligand(grade_radioligand(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown' and interpretations['sampling_basis']['status'] == 'unknown'
