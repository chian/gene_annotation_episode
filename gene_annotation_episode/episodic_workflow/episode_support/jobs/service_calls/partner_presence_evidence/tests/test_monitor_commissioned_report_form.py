"""A parent's commissioned report form (C5) for the A107 progress monitor: its added fields are recorded facts."""
import pytest

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.partner_presence_evidence.monitor_runtime import (
    FACT_FORM_TYPES, A107MonitorRuntimeError, commissioned_fact_fields, fact_sources)
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_progress_assessment.episode \
    import MonitorEpisode

RETURN = MonitorEpisode.return_form


def _form(**added):
    return RecordForm({**RETURN.fields, **added})


def test_every_recorded_fact_has_a_report_field_type():
    assert set(FACT_FORM_TYPES) == set(fact_sources())


def test_own_return_form_adds_nothing():
    assert commissioned_fact_fields(RETURN, RETURN) == ()


def test_added_recorded_facts_are_returned_by_name():
    form = _form(monitoring_progress_refs=Field('list', 'Delivered progress observations'),
                 monitoring_observed_at_unix_seconds=Field('number', 'Latest observation time', required=False))
    assert commissioned_fact_fields(RETURN, form) == ('monitoring_progress_refs',
                                                      'monitoring_observed_at_unix_seconds')


def test_field_without_a_monitor_source_raises():
    with pytest.raises(A107MonitorRuntimeError, match='has_no_source:summary'):
        commissioned_fact_fields(RETURN, _form(summary=Field('text', 'A summary the monitor never records')))


def test_field_of_another_type_raises():
    with pytest.raises(A107MonitorRuntimeError, match='type_differs:monitoring_target_handle'):
        commissioned_fact_fields(RETURN, _form(monitoring_target_handle=Field('list', 'Target handles')))
