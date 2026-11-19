"""The A103 ``gene_context_evidence/resource_work_submission/hpc_resource_work_execution`` binding.

It executes the commissioned resource work (a ``practical_assignment_v1``, ``resource_kind`` ``hpc``) through
model-written ``exec_command`` units on its own ``HpcJobTools`` over the run's shared Store: practical
requirement credit and completion continuation (``execution_job_submission/hpc_job_execution/runtime``). The
A103 home factory constructs it with ``runtime.construct`` from ``a103_hpc_resource_work_execution``.
"""
from __future__ import annotations

from types import MappingProxyType

from ...contract_binding import A103ContractBinding
from ...execution_job_submission.hpc_job_execution.runtime import HpcJobExecutionRuntime


class ResourceEpisode(HpcJobExecutionRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/resource_work_submission/hpc_resource_work_execution'
    grain_name = 'gene_context_evidence__resource_work_submission__hpc_resource_work_execution'
    goal = 'Improve the HPC resource work and its handoff'
    unit = 'One HPC resource action'
    result = 'The HPC resource handoff'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/resource_work_submission'
