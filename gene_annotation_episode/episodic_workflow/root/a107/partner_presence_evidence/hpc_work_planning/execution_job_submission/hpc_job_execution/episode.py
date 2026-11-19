"""A107 binding ``partner_presence_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution``.

It executes the commissioned HPC job (its ``assignment``) through model-written ``exec_command`` units on
its own ``HpcJobTools`` (``execution_job_submission/hpc_job_execution/runtime``): credit is the job's
practical requirement credit and continuation its completion yield controller toward the job's own target.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_job_submission.\
    hpc_job_execution.runtime import HpcJobExecutionRuntime
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import (
    DescendantBinding)


class ExecutionEpisode(HpcJobExecutionRuntime, DescendantBinding):
    binding_path = 'partner_presence_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution'
    goal = 'Improve completion of the assigned HPC job and retention of its native outputs'
    unit = 'One HPC job action'
    result = 'The HPC job receipt and retained native outputs'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/hpc_work_planning/execution_job_submission'
