"""The A103 ``gene_context_evidence/resource_work_submission/api_resource_work_execution`` binding.

It runs the commissioned resource work through one of its own configured API services, its model-selected
service operations and its completion continuation toward one usable handoff
(``execution_job_submission/api_job_execution/runtime_binding``). The A103 home factory constructs it from
``a103_api_resource_work_execution`` over its own ``A103ToolRegistry`` on the shared store.
"""
from __future__ import annotations

from types import MappingProxyType

from ...contract_binding import A103ContractBinding
from ...execution_job_submission.api_job_execution.runtime_binding import ApiJobExecutionBinding


class ResourceEpisode(ApiJobExecutionBinding, A103ContractBinding):
    binding_path = 'gene_context_evidence/resource_work_submission/api_resource_work_execution'
    grain_name = 'gene_context_evidence__resource_work_submission__api_resource_work_execution'
    goal = 'Improve the API resource work and its handoff'
    unit = 'One API resource action'
    result = 'The API resource handoff'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/resource_work_submission'
