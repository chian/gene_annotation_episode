"""A107 binding ``partner_presence_evidence/execution_job_submission/local_job_execution``: the A107 local job runtime (``episode_support/jobs/local_execution/partner_presence_evidence/local_job_runtime.py``)."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.partner_presence_evidence.local_job_runtime import A107LocalJobRuntime
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import DescendantBinding


class ExecutionEpisode(A107LocalJobRuntime, DescendantBinding):
    binding_path = 'partner_presence_evidence/execution_job_submission/local_job_execution'
    goal = 'Improve completion of the assigned local job and retention of its native outputs'
    unit = 'One local job action'
    result = 'The local job receipt and retained native outputs'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/execution_job_submission'
