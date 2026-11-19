"""The A101 ``sequence_homology_evidence/execution_progress_assessment`` binding.

Binds the A101 monitor runtime (``episode_support/jobs/service_calls/sequence_homology_evidence/monitor_runtime.py``): its progress
tools, model-selected decisions, information credit and information-accumulation
yield continuation. Its commission carries the head's monitor assignment in
``role_assignment``.
"""
from __future__ import annotations

from types import MappingProxyType

from episode_runtime import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.sequence_homology_evidence.monitor_runtime import A101MonitorRuntime
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.contract_binding import (
    SCOPE, A101ContractBinding)


class ExecutionProgressAssessmentEpisode(A101MonitorRuntime, A101ContractBinding):
    """Improve what is known about the progress of the assigned execution."""
    binding_path = 'sequence_homology_evidence/execution_progress_assessment'
    goal = 'Improve what is known about the progress of the assigned execution'
    unit = 'One progress observation'
    result = 'Progress references for the assigned execution'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence'
    assignment_form = RecordForm({
        'scope': SCOPE,
        'role_assignment': Field('record', "The commissioning head's monitor assignment (monitor_assignment_v1)"),
    })

    @staticmethod
    def role_assignment(assignment):
        return assignment['role_assignment']
