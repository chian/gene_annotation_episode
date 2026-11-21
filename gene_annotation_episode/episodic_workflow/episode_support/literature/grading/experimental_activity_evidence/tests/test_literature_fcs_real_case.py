"""The real published FCS titration (the CLN3 aptamer with the c-Met protein, PMC10782416): what the grader and the converter make of a
record that holds only what its Results and Methods paragraphs state."""
from math import log10

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import _criterion, convert_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import grade_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fcs_cases import real_record


def test_the_stated_controls_are_supported_the_aptamer_concentration_below_the_window_gets_partial_credit_and_the_rest_is_unknown():
    graded = grade_fcs(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}      # as the sheet judges what the grader recorded
    assert [name for name, status in statuses.items() if status == 'supported'] == ['diffusion_change', 'diffusion_model', 'specificity_control', 'labelled_range', 'labelled_over_kd', 'acquisition', 'replicates']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == ['crosstalk']
    # 1.2 ms over 0.37 ms = 3.24 (and 90 over 30 um2/s = 3); the fit of one effective component has both reference times
    assert graded['native']['diffusion_ratio'] == pytest.approx(1.2 / 0.37) and graded['reasons']['diffusion_model'] == 'one_component_with_reference_values'
    # 100 pM labelled partner over a KD of 5 nM = 0.02; 0.1 nM is below the 0.3 nM at which a typical confocal volume holds 0.1 molecules: softened, it is
    # about half way down the decade to the 0.03 nM zero end on the log scale, partial credit log10(0.1 / 0.03) = 0.52 (was conflicting)
    assert graded['native']['labelled_over_kd'] == pytest.approx(0.02) and graded['native']['labelled_nM'] == pytest.approx(0.1)
    assert graded['reasons']['labelled_range'] == 'labelled_concentration_recorded_for_the_sheet' and graded['criteria']['labelled_range']['status'] == 'unknown'      # the grader records, the sheet judges
    assert _criterion(graded, 'labelled_range')['degree'] == pytest.approx(log10(0.1 / 0.03))
    # 180 s with three repetitions, four independent replicates
    assert graded['native']['acquisition_total_s'] == 540 and graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and graded['native']['replicate_count'] == 4
    assert _criterion(graded, 'diffusion_change')['degree'] == 1.0 and _criterion(graded, 'labelled_over_kd')['degree'] == 1.0      # a ratio of 3.2 and a labelled partner at 0.02 x KD
    # the c-Met concentrations are a range, the mass ratio, the maximum fraction bound, the corrections and the model of the binding curve are not stated
    assert graded['reasons']['concentration_series'] == 'kd_or_series_missing' and graded['reasons']['mass_consistency'] == 'mass_ratio_or_diffusion_not_given'
    assert graded['reasons']['saturation'] == 'fraction_bound_maximum_not_given' and graded['reasons']['fit_model'] == 'fit_model_not_stated'
    assert graded['reasons']['volume_calibration'] == 'fact_unknown' and graded['reasons']['equilibrium'] == 'fact_unknown'


def test_the_converter_gives_the_effect_and_no_variance_because_the_kind_of_the_spread_is_not_stated():
    converted = convert_fcs(grade_fcs(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(5.0) and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'spread_kind_not_stated'
    interpretations = converted['extraction']['interpretations']
    # the binding regime is unknown (the saturation, the span and the equilibrium are not stated); it no longer conflicts over the 0.1 nM aptamer
    assert interpretations['binding_regime']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown'
    assert interpretations['sampling_basis']['status'] == 'supported'
