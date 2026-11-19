"""The A102 ``structural_homology_evidence/resource_work_submission/api_resource_work_execution`` binding.

It runs the commissioned resource work through one of its own configured API services, its model-selected
service operations and its completion continuation toward one usable handoff
(``execution_job_submission/api_job_execution/runtime_binding``). ``a102_home_factory`` constructs it from
``services['a102']['api_resource_work_execution']`` over its own A102 tool registry on the shared store.
"""
from __future__ import annotations

from ...contract_binding import A102ContractBinding
from ...execution_job_submission.api_job_execution.runtime_binding import ApiJobExecutionBinding


class ResourceEpisode(ApiJobExecutionBinding, A102ContractBinding):
    binding_path = 'structural_homology_evidence/resource_work_submission/api_resource_work_execution'
    commissioning_parent = 'structural_homology_evidence/resource_work_submission'
