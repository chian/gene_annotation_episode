"""The A101 ``sequence_homology_evidence/execution_job_submission/hpc_job_execution`` binding.

It executes the commissioned HPC job through model-written ``exec_command`` units
on its own ``HpcJobTools`` (``runtime``): credit is the job's practical requirement
credit and continuation its completion yield controller toward the job's own target.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.contract_binding import (
    A101ContractBinding)

from .runtime import HpcJobExecutionRuntime


class HpcJobExecutionEpisode(HpcJobExecutionRuntime, A101ContractBinding):
    """Get the submitted computation executing as an HPC job."""
    binding_path = 'sequence_homology_evidence/execution_job_submission/hpc_job_execution'
    goal = 'Get the submitted computation executing as an HPC job'
    unit = 'One HPC job action'
    result = 'The HPC execution handle and its received status'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence/execution_job_submission'
