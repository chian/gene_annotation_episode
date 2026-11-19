"""The A103 ``gene_context_evidence/hpc_work_planning/hpc_allocation_execution`` binding on the generic runner.

Its decision source, credit and continuation are ``allocation_runtime`` (role ``hpc_execution``): model-selected
handoff binding, job observation, result parsing and unit ordering over one frozen plan of its owner's HPC
ledger, and commissions of its launch, monitor and result children.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import (
    A103ContractBinding)

from .allocation_runtime import AllocationRuntime


class HPCEpisode(AllocationRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'
    grain_name = 'gene_context_evidence__hpc_work_planning__hpc_allocation_execution'
    goal = 'Improve the work completed inside one HPC allocation'
    unit = 'One allocation-portfolio action or child commission'
    result = 'The allocation portfolio outcome'
    child_slots = MappingProxyType({'execution_job_submission': 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'execution_progress_assessment': 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'execution_result_acquisition': 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'})
    commissioning_parent = 'gene_context_evidence/hpc_work_planning'
