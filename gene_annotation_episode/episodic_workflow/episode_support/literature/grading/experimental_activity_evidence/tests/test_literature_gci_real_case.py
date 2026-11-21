"""The real published GCI case (CrcA and Crc, PMC10213629): what the grader and the converter make of a record that
holds only what the paragraph states."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import _criterion, convert_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_grader import grade_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import real_record


def test_only_the_two_estimates_agreement_is_decided_and_nothing_conflicts():
    graded = grade_gci(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}      # as the sheet judges what the grader recorded
    # KD 10.99 uM (1:1 kinetic) and 11.99 uM (equilibrium): ratio 11.99 / 10.99 = 1.091, within a factor of 2
    assert [name for name, status in statuses.items() if status == 'supported'] == ['steady_state_vs_kinetic']
    assert 'conflicting' not in statuses.values() and set(statuses.values()) <= {'supported', 'unknown', 'not_applicable'}
    # 15 pg/mm2 is below the 2000 pg/mm2 maximum but no response is stated; the 1:1 model is stated but not whether CrcA is bivalent
    assert graded['reasons']['surface_level_and_response'] == 'surface_level_and_response_recorded_for_the_sheet' and statuses['surface_level_and_response'] == 'unknown'      # the level is recorded, the response is not stated
    assert graded['reasons']['fit_model'] == 'bivalence_or_oligomer_state_unknown_for_one_to_one_model'
    assert graded['reasons']['concentration_series'] == 'kd_or_series_missing'
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    assert graded['native']['kd_nM'] == pytest.approx(10990.0) and graded['native']['immobilization_level_pg_mm2'] == 15.0


def test_the_converter_gives_the_effect_and_no_variance():
    converted = convert_gci(grade_gci(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(10990.0) and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert converted['extraction']['interpretations']['binding_controls']['status'] == 'unknown'
    assert converted['extraction']['interpretations']['binding_regime']['status'] == 'unknown'
