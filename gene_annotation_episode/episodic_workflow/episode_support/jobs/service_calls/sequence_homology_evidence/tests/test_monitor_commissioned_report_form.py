"""A parent's commissioned report form (C5) for the A101 progress monitor: its added fields are recorded facts."""
import pytest

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.sequence_homology_evidence.monitor_runtime import (
    FACT_FORM_TYPES, A101MonitorRuntimeError, commissioned_fact_fields, fact_sources)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.execution_progress_assessment.episode \
    import ExecutionProgressAssessmentEpisode

RETURN = ExecutionProgressAssessmentEpisode.return_form


def _form(**added):
    return RecordForm({**RETURN.fields, **added})


def test_every_recorded_fact_has_a_report_field_type():
    assert set(FACT_FORM_TYPES) == set(fact_sources())


def test_own_return_form_adds_nothing():
    assert commissioned_fact_fields(RETURN, RETURN) == ()


def test_added_recorded_facts_are_returned_by_name():
    form = _form(monitoring_dependency_handles=Field('list', 'Exposed direct dependencies'),
                 monitoring_execution_state=Field('text', 'Latest lifecycle state', required=False))
    assert commissioned_fact_fields(RETURN, form) == ('monitoring_dependency_handles', 'monitoring_execution_state')


def test_field_without_a_monitor_source_raises():
    with pytest.raises(A101MonitorRuntimeError, match='has_no_source:summary'):
        commissioned_fact_fields(RETURN, _form(summary=Field('text', 'A summary the monitor never records')))


def test_field_of_another_type_raises():
    with pytest.raises(A101MonitorRuntimeError, match='type_differs:monitoring_result_available'):
        commissioned_fact_fields(RETURN, _form(monitoring_result_available=Field('text', 'Availability')))
