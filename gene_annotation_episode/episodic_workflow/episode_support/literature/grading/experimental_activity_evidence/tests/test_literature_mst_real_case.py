"""The real published MST case (NHS-RED labelled BmpA with thymidine, PMC13325309): what the grader and the converter make of a
record that holds only what its Results and Methods paragraphs state."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import _criterion, convert_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_grader import grade_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import real_record


def test_the_labelled_concentration_and_the_fit_model_are_decided_and_nothing_conflicts():
    graded = grade_mst(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}       # the sheet judges what the grader only records
    assert [name for name, status in statuses.items() if status == 'supported'] == ['labelled_concentration', 'equilibrium', 'fit_model']      # equilibrium: 10 min at a KD of 532 nM is past T_SLOW (the curve of the incubation)
    assert 'conflicting' not in statuses.values() and set(statuses.values()) <= {'supported', 'unknown', 'not_applicable'}
    # 10 nM detected partner over a KD of 532 nM = 0.0188
    assert graded['native']['kd_nM'] == pytest.approx(532.0) and graded['native']['labelled_over_kd'] == pytest.approx(10 / 532)
    assert graded['reasons']['labelled_concentration'] == 'labelled_over_kd_recorded_for_the_sheet' and graded['reasons']['fit_model'] == 'model_stated'      # the grader records the ratio, the sheet judges it
    assert _criterion(graded, 'labelled_concentration')['degree'] == 1.0
    # the label is an NHS-RED dye whose effect on binding is not stated; the series is a range, the signal and the readout are not stated
    assert graded['reasons']['labelling_scheme'] == 'label_not_shown_harmless'
    assert graded['reasons']['concentration_series'] == 'constant_or_series_missing'
    assert graded['reasons']['signal_amplitude'] == 'signal_not_given'
    assert graded['reasons']['readout_window'] == 'readout_signal_not_stated'
    assert graded['reasons']['initial_fluorescence'] == 'initial_fluorescence_result_not_stated'
    assert graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and _criterion(graded, 'replicates')['status'] == 'unknown'       # in triplicate, but independence is not stated
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and _criterion(graded, 'equilibrium') == {'status': 'supported', 'support_refs': graded['native']['incubation_refs'], 'degree': 1.0}      # 10 min, no statement of equilibrium; KD 532 nM: T_FAST 10 x 10 / 532 = 0.188 min, T_SLOW 1.88 min, so full
    assert graded['reasons']['aggregation_adsorption'] == 'fact_unknown'


def test_the_converter_gives_the_effect_and_no_variance_because_no_spread_is_given():
    converted = convert_mst(grade_mst(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(532.0) and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'unknown' and interpretations['binding_controls']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['calibration_applicability']['status'] == 'unknown'
