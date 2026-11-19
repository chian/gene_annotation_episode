"""The A102 ``structural_homology_evidence/hpc_work_planning/hpc_resource_prediction`` binding.

Its decision source, credit and continuation are ``hpc_work_planning/hpc_runtime`` (role
``hpc_prediction``): model-selected fit, measurement and comparison operations over its owner's HPC
ledger.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding

from ..episode import HPC_ASSIGNMENT
from ..hpc_runtime import PREDICTION, HPCRuntime


class HPCEpisode(HPCRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/hpc_work_planning/hpc_resource_prediction'
    commissioning_parent = 'structural_homology_evidence/hpc_work_planning'
    assignment_form = HPC_ASSIGNMENT
    hpc_role = PREDICTION
