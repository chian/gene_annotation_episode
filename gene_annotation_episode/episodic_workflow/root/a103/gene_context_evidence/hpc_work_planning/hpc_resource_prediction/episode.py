"""The A103 ``gene_context_evidence/hpc_work_planning/hpc_resource_prediction`` binding on the generic runner.

Its decision source, credit and continuation are ``hpc_work_planning/hpc_runtime``
(role ``hpc_prediction``): model-selected fit, measurement and comparison
operations over its owner's HPC ledger.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import (
    A103ContractBinding)

from ..hpc_runtime import PREDICTION, HPCRuntime


class HPCEpisode(HPCRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning/hpc_resource_prediction'
    grain_name = 'gene_context_evidence__hpc_work_planning__hpc_resource_prediction'
    goal = 'Improve the predicted resource needs of the planned HPC work'
    unit = 'One prediction action'
    result = 'The resource prediction'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/hpc_work_planning'
    hpc_role = PREDICTION
