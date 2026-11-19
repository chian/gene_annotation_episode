"""The A103 ``gene_context_evidence/hpc_work_planning`` binding on the generic runner.

Its decision source, credit and continuation are ``hpc_runtime`` (role ``hpc``):
model-selected HPC planning operations over the commission's own ledger and
commissions of its ``hpc_resource_prediction`` sister. It commissions none of its
other declared child slots.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import (
    A103ContractBinding)

from .hpc_runtime import PLANNING, HPCRuntime


class HPCEpisode(HPCRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning'
    grain_name = 'gene_context_evidence__hpc_work_planning'
    goal = 'Improve the HPC work plan for the parent computational requests'
    unit = 'One planning action or child commission'
    result = 'The HPC work plan and its executed portfolio'
    child_slots = MappingProxyType({'execution_job_submission': 'gene_context_evidence/hpc_work_planning/execution_job_submission', 'execution_progress_assessment': 'gene_context_evidence/hpc_work_planning/execution_progress_assessment', 'execution_result_acquisition': 'gene_context_evidence/hpc_work_planning/execution_result_acquisition', 'hpc_allocation_execution': 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution', 'hpc_resource_prediction': 'gene_context_evidence/hpc_work_planning/hpc_resource_prediction'})
    commissioning_parent = 'gene_context_evidence'
    hpc_role = PLANNING
