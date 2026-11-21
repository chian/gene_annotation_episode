"""The real published SPA Methods paragraph on purified LeuT variants (eLife 2024, doi 10.7554/eLife.87985, PMC10945697): what the grader and the
converter make of a record that holds only what the paragraph states about the experiments (tritiated leucine of 25 Ci/mmol, YSi-Cu His-tag
SPA beads at 1.25 mg/ml, purified protein, a MicroBeta2 counter, 100 uM unlabelled leucine to correct for unspecific binding, ligand depletion avoided
by a 20-fold molar excess of the radioligand, about 16 hours at 4 C). It states no measured KD or Bmax, IC50 or Ki, so nothing in it can conflict
with a threshold: two criteria are supported by stated facts and the others are unknown. A conflict would be a real one only if a stated
number crossed a threshold; none does here."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import _criterion, convert_spa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_grader import grade_spa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spa_cases import real_record


def test_two_facts_are_supported_and_everything_else_is_unknown():
    graded = grade_spa(real_record())
    statuses = {name: item['status'] for name, item in graded['criteria'].items()}
    assert [name for name, status in statuses.items() if status == 'supported'] == ['ligand_depletion', 'nonspecific_binding']
    assert graded['criteria']['ligand_depletion']['support_refs'] == ['span_depletion'] and graded['criteria']['nonspecific_binding']['support_refs'] == ['span_nonspecific']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == []
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and graded['native']['incubation_min'] == 960.0       # about 16 hours: recorded for the sheet
    assert _criterion(graded, 'equilibrium') == {'status': 'unknown', 'support_refs': []}                                                     # not short, and no time course is stated
    assert graded['reasons']['nonspecific_excess'] == 'excess_reference_not_given' and graded['native']['nonspecific_ligand_nM'] == 100000.0
    assert graded['reasons']['competition_radioligand_level'] == 'radioligand_concentration_or_kd_not_given' and graded['reasons']['radioligand_range'] == 'kd_or_series_missing'
    assert graded['reasons']['bead_only_control'] == 'fact_unknown' and graded['reasons']['homogeneous_format'] == 'fact_unknown'
    assert graded['reasons']['fit_model'] == 'fit_model_not_stated' and graded['reasons']['cheng_prusoff'] == 'fact_unknown'
    assert graded['native']['kd_nM'] is None and graded['native']['constant_name'] is None
    assert graded['native']['radioligand_isotope'] == 'tritium' and graded['native']['bead_type'] == 'ysi' and graded['native']['capture_method'] == 'metal_chelate'


def test_the_converter_gives_no_effect_because_no_kd_was_measured():
    converted = convert_spa(grade_spa(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect'] == 'neither_kd_nor_ki_given_as_a_point_value'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown' and interpretations['sampling_basis']['status'] == 'unknown'
