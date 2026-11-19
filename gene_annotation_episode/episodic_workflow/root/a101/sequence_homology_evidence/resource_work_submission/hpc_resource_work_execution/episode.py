"""The A101 ``sequence_homology_evidence/resource_work_submission/hpc_resource_work_execution`` binding.

It executes the commissioned resource work (a ``practical_assignment_v1``, ``resource_kind`` ``hpc``) through
model-written ``exec_command`` units on its own ``HpcJobTools`` over the run's shared Store: credit is the
work's practical requirement credit and continuation its completion yield controller toward the work's own
target (``execution_job_submission/hpc_job_execution/runtime``). ``a101_home_factory`` constructs it with
``runtime.construct`` from ``services['a101']['hpc_resource_work_execution']``.
"""
from __future__ import annotations

from types import MappingProxyType

from ...contract_binding import A101ContractBinding
from ...execution_job_submission.hpc_job_execution.runtime import HpcJobExecutionRuntime


class HpcResourceWorkExecutionEpisode(HpcJobExecutionRuntime, A101ContractBinding):
    """Get the resource work executing as an HPC job."""
    binding_path = 'sequence_homology_evidence/resource_work_submission/hpc_resource_work_execution'
    goal = 'Get the resource work executing as an HPC job'
    unit = 'One HPC resource action'
    result = 'The HPC resource handle and its received status'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence/resource_work_submission'
