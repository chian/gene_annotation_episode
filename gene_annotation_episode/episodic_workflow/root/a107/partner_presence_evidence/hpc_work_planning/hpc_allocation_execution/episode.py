"""A107 binding ``partner_presence_evidence/hpc_work_planning/hpc_allocation_execution`` on the generic runner.

Its decision source, credit and continuation are ``allocation_runtime`` (role ``hpc_execution``):
model-selected handoff binding, job observation, result parsing and unit ordering over one frozen plan of
its owner's HPC ledger, and commissions of its launch, monitor and results children.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import \
    DescendantBinding

from .allocation_runtime import AllocationRuntime


class HPCEpisode(AllocationRuntime, DescendantBinding):
    binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'
    goal = 'Improve the execution of one planned HPC allocation'
    unit = 'One allocation action or commissioned launch, monitor or results child'
    result = 'The allocation execution outcome and its handoffs'
    child_slots = {'launch': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'monitor': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'results': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'}
    commissioning_parent = 'partner_presence_evidence/hpc_work_planning'
