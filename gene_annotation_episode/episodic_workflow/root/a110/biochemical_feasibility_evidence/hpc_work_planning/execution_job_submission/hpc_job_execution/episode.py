"""The A110 ``biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution`` binding on the generic runner.

It executes the commissioned HPC job (its ``assignment``) through model-written ``exec_command`` units on
its own ``HpcJobTools`` (``execution_job_submission/hpc_job_execution/runtime``): credit is the job's
practical requirement credit and continuation its completion yield controller toward the job's own target.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.execution_job_submission.\
    hpc_job_execution.runtime import HpcJobExecutionRuntime
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    EpisodeRuntimeContract)


class HpcJobExecutionEpisode(HpcJobExecutionRuntime, EpisodeRuntimeContract):
    """Execute the frozen request on the HPC service and retain its receipts."""
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution'
    grain_name = binding_path.replace('/', '__')
    goal = 'Execute the frozen request on the HPC service and retain its receipts'
    unit = 'One HPC execution action'
    result = 'The HPC execution receipts and committed records'
    child_slots = MappingProxyType({})
    commissioning_parent = 'biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission'
