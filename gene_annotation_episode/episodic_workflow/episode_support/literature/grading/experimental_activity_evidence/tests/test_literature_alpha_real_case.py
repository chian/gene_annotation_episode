"""The real published AlphaLISA matrix cross-titration (His-Spindlin1 and biotin-H3(1-23)K4me3, streptavidin donor and Ni-NTA acceptor beads,
Nucleic Acids Research 2016, doi 10.1093/nar/gkw089, PMC4872087): what the grader and the converter make of a record that holds only what
the paper's Results paragraph on the optimal assay concentrations states."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import convert_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_grader import grade_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.alpha_cases import real_record


def test_the_prevented_hook_effect_is_supported_by_its_span_and_everything_else_is_unknown():
    graded = grade_alpha(real_record())
    statuses = {name: item['status'] for name, item in graded['criteria'].items()}
    assert [name for name, status in statuses.items() if status == 'supported'] == ['hook_effect']
    assert graded['criteria']['hook_effect']['support_refs'] == ['span_hook']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == [] and graded['reasons']['direct_vs_competition'] == 'kd_or_ki_missing'
    # no KD, EC50, IC50 or Ki value, no signal, background, S/B or Z', no incubation time, no list of concentrations
    assert graded['native']['constant_name'] is None and graded['reasons']['concentration_series'] == 'constant_or_series_missing'
    assert graded['reasons']['signal_window'] == 'signal_window_not_given' and graded['reasons']['assay_quality'] == 'z_prime_not_given'
    assert graded['reasons']['equilibrium'] == 'fact_unknown' and graded['native']['incubation_min'] is None
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown' and graded['reasons']['fit_model'] == 'fit_model_not_stated'
    assert graded['native']['titration_design'] == 'cross_titration' and graded['native']['donor_bead'] == 'streptavidin' and graded['native']['acceptor_bead'] == 'nickel_chelate'


def test_the_converter_gives_no_effect_because_the_paragraph_reports_no_binding_constant():
    converted = convert_alpha(grade_alpha(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'unknown'
    assert interpretations['binding_regime']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown' and interpretations['sampling_basis']['status'] == 'unknown'
