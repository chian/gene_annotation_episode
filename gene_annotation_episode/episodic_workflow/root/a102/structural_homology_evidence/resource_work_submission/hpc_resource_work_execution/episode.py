"""The A102 ``structural_homology_evidence/resource_work_submission/hpc_resource_work_execution`` binding.

It executes the commissioned resource work (a ``practical_assignment_v1``, ``resource_kind`` ``hpc``) through
model-written ``exec_command`` units on its own ``HpcJobTools`` over the run's shared Store: practical
requirement credit and completion continuation (``execution_job_submission/hpc_job_execution/runtime``).
``a102_home_factory`` constructs it with ``runtime.construct`` from
``services['a102']['hpc_resource_work_execution']``.
"""
from __future__ import annotations

from ...contract_binding import A102ContractBinding
from ...execution_job_submission.hpc_job_execution.runtime import HpcJobExecutionRuntime


class ResourceEpisode(HpcJobExecutionRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/resource_work_submission/hpc_resource_work_execution'
    commissioning_parent = 'structural_homology_evidence/resource_work_submission'
