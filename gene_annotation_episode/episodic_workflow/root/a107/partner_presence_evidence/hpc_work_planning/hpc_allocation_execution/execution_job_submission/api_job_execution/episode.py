"""A107 binding ``partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution``:
one assigned API job over its own API services, its model-selected operations and its
completion continuation (``execution_job_submission/api_job_execution/api_job_binding``).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_job_submission.\
    api_job_execution.api_job_binding import ApiJobExecutionBinding
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import \
    DescendantBinding


class ExecutionEpisode(ApiJobExecutionBinding, DescendantBinding):
    binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution'
    goal = 'Improve completion of the assigned API job and retention of its native response'
    unit = 'One API job action'
    result = 'The API job receipt and retained native response'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
