"""The A103 ``gene_context_evidence/hpc_work_planning/execution_job_submission/local_job_execution`` binding on the generic runner.

Binds the A103 local job runtime (``episode_support/jobs/local_execution/gene_context_evidence/local_job_runtime.py``): its exec_command
decisions over the assigned local resource, practical requirement credit and completion
continuation.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import A103ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.local_job_runtime import A103LocalJobRuntime


class ExecutionEpisode(A103LocalJobRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning/execution_job_submission/local_job_execution'
    grain_name = 'gene_context_evidence__hpc_work_planning__execution_job_submission__local_job_execution'
    goal = 'Improve the local job execution and its handoff'
    unit = 'One local execution action'
    result = 'The local job handoff'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/hpc_work_planning/execution_job_submission'
