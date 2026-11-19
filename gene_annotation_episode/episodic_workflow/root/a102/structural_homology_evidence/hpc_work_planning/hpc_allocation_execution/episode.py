"""The A102 ``structural_homology_evidence/hpc_work_planning/hpc_allocation_execution`` binding.

Its decision source, credit and continuation are ``allocation_runtime`` (role ``hpc_execution``):
model-selected handoff binding, job observation, result parsing and unit ordering over one frozen plan of
its owner's HPC ledger, and commissions of its launch, monitor and result children. Its assignment carries
the commissioning planner's typed assignment (``role_assignment``: ``owner_episode_id`` and ``plan_ref``).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding

from ..episode import HPC_ASSIGNMENT
from .allocation_runtime import AllocationRuntime


class HPCEpisode(AllocationRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution'
    commissioning_parent = 'structural_homology_evidence/hpc_work_planning'
    assignment_form = HPC_ASSIGNMENT
