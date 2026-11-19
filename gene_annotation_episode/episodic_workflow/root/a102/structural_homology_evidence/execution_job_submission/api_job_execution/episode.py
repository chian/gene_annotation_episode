"""The A102 ``structural_homology_evidence/execution_job_submission/api_job_execution``
binding on the generic runner: one assigned API job over its own API services, its
model-selected operations and its completion continuation (``runtime_binding``).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.execution_job_submission.\
    api_job_execution.runtime_binding import ApiJobExecutionBinding


class ExecutionEpisode(ApiJobExecutionBinding, A102ContractBinding):
    binding_path = 'structural_homology_evidence/execution_job_submission/api_job_execution'
    commissioning_parent = 'structural_homology_evidence/execution_job_submission'
