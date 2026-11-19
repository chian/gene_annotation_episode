"""This A102 local job execution binding on the generic runner (``episode_runtime``).

Its exec_command decisions over the assigned local resource, practical requirement credit and
completion continuation are the A102 local job runtime's (``episode_support/jobs/local_execution/structural_homology_evidence/local_job_runtime.py``).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.local_job_runtime import A102LocalJobRuntime


class ExecutionEpisode(A102LocalJobRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution'
    commissioning_parent = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
