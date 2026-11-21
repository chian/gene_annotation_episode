"""The real published BLI case (pantinin-1 and the Chikungunya virus nsP2 protease, PMC13065029): what the grader and
the converter make of a record that holds only what the paragraph states."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import _criterion, convert_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import real_record


def test_only_the_stated_control_is_decided_and_nothing_conflicts():
    graded = grade_bli(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}      # as the sheet judges what the grader recorded
    assert statuses['nonspecific_binding_control'] == 'supported'
    assert [name for name, status in statuses.items() if status == 'supported'] == ['nonspecific_binding_control']
    assert 'conflicting' not in statuses.values() and set(statuses.values()) <= {'supported', 'unknown', 'not_applicable'}
    # koff is not stated, so the 600 s dissociation window cannot be judged; the triplicates are not said to be independent sensors
    assert graded['reasons']['dissociation_window'] == 'koff_or_dissociation_time_missing'
    assert graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and statuses['replicates'] == 'unknown' and graded['native']['replicate_independent'] == 'unknown'
    assert graded['native']['kd_nM'] == pytest.approx(9290.0) and graded['native']['dissociation_time_s'] == 600.0


def test_the_converter_gives_the_effect_and_no_variance():
    converted = convert_bli(grade_bli(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(9290.0) and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given'
    assert converted['extraction']['interpretations']['binding_controls']['status'] == 'unknown'
