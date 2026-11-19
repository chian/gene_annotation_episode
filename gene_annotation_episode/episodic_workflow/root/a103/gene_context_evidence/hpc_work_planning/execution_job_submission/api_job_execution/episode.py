"""The A103 ``gene_context_evidence/hpc_work_planning/execution_job_submission/api_job_execution``
binding on the generic runner: one assigned API job over its own API services, its
model-selected operations and its completion continuation (``runtime_binding``).
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import A103ContractBinding
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_job_submission.\
    api_job_execution.runtime_binding import ApiJobExecutionBinding


class ExecutionEpisode(ApiJobExecutionBinding, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning/execution_job_submission/api_job_execution'
    grain_name = 'gene_context_evidence__hpc_work_planning__execution_job_submission__api_job_execution'
    goal = 'Improve the API job submission and its handoff'
    unit = 'One API submission action'
    result = 'The API job handoff'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/hpc_work_planning/execution_job_submission'
