"""A107 binding ``partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission``: its submission source and completion continuation are ``execution_job_submission.submission_source``."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_job_submission.submission_source import (
    JobSubmissionBinding)
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import DescendantBinding


class ExecutionEpisode(JobSubmissionBinding, DescendantBinding):
    binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
    goal = 'Improve delivery of the assigned computation as submitted jobs with original inputs and handoff receipts'
    unit = 'One API, local or HPC route child commissioned for one requested job'
    result = 'Execution handoffs and their receipts'
    child_slots = {'launch_api': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'launch_hpc': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'launch_local': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution'}
    commissioning_parent = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'
