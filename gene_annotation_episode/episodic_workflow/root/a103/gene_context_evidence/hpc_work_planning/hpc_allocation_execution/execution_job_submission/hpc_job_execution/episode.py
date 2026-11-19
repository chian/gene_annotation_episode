"""The A103 ``gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution`` binding on the generic runner.

It executes the commissioned HPC job (its ``role_assignment``) through model-written ``exec_command``
units on its own ``HpcJobTools`` (``execution_job_submission/hpc_job_execution/runtime``): credit is the
job's practical requirement credit and continuation its completion yield controller toward the job's own target.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import A103ContractBinding
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_job_submission.\
    hpc_job_execution.runtime import HpcJobExecutionRuntime


class ExecutionEpisode(HpcJobExecutionRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution'
    grain_name = 'gene_context_evidence__hpc_work_planning__hpc_allocation_execution__execution_job_submission__hpc_job_execution'
    goal = 'Improve the HPC job submission and its handoff'
    unit = 'One HPC submission action'
    result = 'The HPC job handoff'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
