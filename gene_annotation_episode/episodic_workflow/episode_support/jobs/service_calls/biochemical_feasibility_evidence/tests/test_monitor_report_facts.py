"""A commissioned report form (C5) on an A110 progress monitor adds only its recorded report facts.

Real monitor binding with its own A110 ``ToolRegistry`` over a real Store; no model, network or job.
"""
import pytest

from method_loop import Field, RecordForm
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.\
    execution_progress_assessment.episode import ExecutionProgressAssessmentEpisode
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.biochemical_feasibility_evidence.monitor_runtime import (
    A110MonitorRuntimeError, commissioned_report_facts, fact_sources)
from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import ToolRegistry
from gene_annotation_episode.state import Store

YIELD = {'kind': 'information_accumulation', 'cutoff': 0.5, 'uncertainty_alpha': 0.1}


def test_monitor_report_form_adds_recorded_facts_and_refuses_unrecorded_fields(tmp_path):
    with Store(tmp_path / 'state') as store:
        binding = ExecutionProgressAssessmentEpisode(information_unit=1.0, yield_settings=YIELD,
                                                     tool_registry=ToolRegistry(store))
        assert commissioned_report_facts(binding, binding.return_form) == ()
        requested = RecordForm({**binding.return_form.fields,
                                'monitoring_execution_state': Field('text', 'Latest target state', required=False),
                                'monitoring_progress_refs': Field('list', 'Delivered progress observations')})
        assert commissioned_report_facts(binding, requested) == ('monitoring_execution_state',
                                                                 'monitoring_progress_refs')
        assert set(commissioned_report_facts(binding, requested)) <= set(fact_sources())
        unrecorded = RecordForm({**binding.return_form.fields, 'monitoring_stall': Field('boolean', 'Not recorded')})
        with pytest.raises(A110MonitorRuntimeError, match='report_form_requests_unrecorded_facts:.*monitoring_stall'):
            commissioned_report_facts(binding, unrecorded)
