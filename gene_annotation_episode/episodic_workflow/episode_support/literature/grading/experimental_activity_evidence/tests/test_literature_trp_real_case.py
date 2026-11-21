"""The real published tryptophan fluorescence titration (TRKB-ECD-His with 7,8-DHF, PMC9654711): what the grader and the converter make of a
record that holds only what its Results and Methods paragraphs state."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import _criterion, convert_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import grade_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.trp_cases import real_record


def test_the_excitation_is_supported_the_protein_over_kd_is_supported_with_a_partial_degree_and_everything_else_is_unknown():
    graded = grade_trp(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}       # the sheet judges what the grader only records
    assert [name for name, status in statuses.items() if status == 'supported'] == ['excitation_selectivity', 'concentration_series', 'protein_concentration']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert set(statuses.values()) <= {'supported', 'unknown'}
    # 50 nM protein over a KD of 16 nM = 3.125: above the full-agreement limit of 1 and below the zero-agreement limit of 10, and the passage does not name a tight-binding model or say depletion was considered
    assert graded['native']['kd_nM'] == pytest.approx(16.0) and graded['native']['protein_over_kd'] == pytest.approx(50 / 16)
    assert graded['native']['tight_binding_handled'] is False
    assert graded['reasons']['protein_concentration'] == 'protein_over_kd_recorded_for_the_sheet' and graded['criteria']['protein_concentration']['status'] == 'unknown'
    assert _criterion(graded, 'protein_concentration')['degree'] == pytest.approx((math.log(1 + 10.0 / 2) - math.log(1 + 50 / 16 / 2)) / (math.log(1 + 10.0 / 2) - math.log(1 + 1.0 / 2)))      # linear in log(1 + r / 2) (range review), 0.614
    assert graded['reasons']['excitation_selectivity'] == 'excitation_recorded_for_the_sheet'
    assert _criterion(graded, 'excitation_selectivity')['degree'] == pytest.approx(1.0)                 # 295 nm: at the researched tryptophan-selective wavelength, full agreement
    # the compounds are given as a range 0-1000 nM: only its top end is a concentration, 1000 nM = 62.5 x the KD (the plateau is reached), no count, no lowest end
    assert graded['reasons']['concentration_series'] == 'series_recorded_for_the_sheet' and graded['native']['concentration_count'] is None
    assert graded['native']['concentration_high_over_constant'] == pytest.approx(1000 / 16) and graded['native']['concentration_low_over_constant'] is None
    assert _criterion(graded, 'concentration_series')['degree'] == pytest.approx(1.0)
    # the size of the change, the corrections, the controls and the replicates are not stated
    assert graded['reasons']['signal_amplitude'] == 'fluorescence_change_not_given'
    assert graded['reasons']['inner_filter'] == 'inner_filter_not_addressed' and graded['reasons']['dilution'] == 'dilution_not_addressed'
    assert graded['reasons']['fit_model'] == 'fit_model_not_stated'
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    assert _criterion(graded, 'equilibrium')['status'] == 'unknown'


def test_the_converter_gives_the_effect_and_no_variance_because_the_kind_of_the_spread_is_not_stated():
    converted = convert_trp(grade_trp(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(16.0) and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'spread_kind_not_stated'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'unknown'      # the protein over the KD is only partly supported; the series and the saturation are not stated
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown'
