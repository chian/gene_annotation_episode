"""The A110 hpc_allocation_execution binding on the generic runner.

Its decision source, credit and continuation are ``allocation_runtime`` (role ``hpc_execution``):
model-selected handoff binding, job observation, result parsing and unit ordering over one frozen plan of
its owner's HPC ledger, and commissions of its launch, monitor and result children.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    CHILD_ASSIGNMENT_FORM, RETURN_FORM, EpisodeRuntimeContract)

from .allocation_runtime import AllocationRuntime


class HpcAllocationExecutionEpisode(AllocationRuntime, EpisodeRuntimeContract):
    """Run the planned work inside one HPC allocation."""
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution'
    grain_name = binding_path.replace('/', '__')
    goal = 'Run the planned work inside one HPC allocation'
    unit = 'One allocation action or commissioned job'
    result = 'The allocation execution findings'
    child_slots = MappingProxyType({'execution_job_submission': 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'execution_progress_assessment': 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'execution_result_acquisition': 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'})
    assignment_form = CHILD_ASSIGNMENT_FORM
    return_form = RETURN_FORM
    commissioning_parent = 'biochemical_feasibility_evidence/hpc_work_planning'
