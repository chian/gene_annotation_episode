"""The A102 ``structural_homology_evidence/execution_job_submission/hpc_job_execution`` binding on the generic runner.

It executes the commissioned HPC job through model-written ``exec_command`` units on its own
``HpcJobTools`` (``execution_job_submission/hpc_job_execution/runtime``): credit is the job's practical
requirement credit and continuation its completion yield controller toward the job's own target.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.execution_job_submission.\
    hpc_job_execution.runtime import HpcJobExecutionRuntime


class ExecutionEpisode(HpcJobExecutionRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/execution_job_submission/hpc_job_execution'
    commissioning_parent = 'structural_homology_evidence/execution_job_submission'
