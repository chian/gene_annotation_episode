"""The A101 ``sequence_homology_evidence/resource_work_submission/local_resource_work_execution`` binding.

It executes the commissioned resource work (a frozen ``practical_assignment_v1``, ``resource_kind`` ``local``)
on its own configured local resource: model-written ``exec_command`` units run by its own
``TerminalExecution``, practical requirement credit and the completion continuation toward the
assignment's total requirement credit (``episode_support/jobs/local_execution/sequence_homology_evidence/local_job_runtime.py``). ``a101_home_factory``
constructs it from ``services['a101']['local_resource_work_execution']``.
"""
from __future__ import annotations

from types import MappingProxyType

from ...contract_binding import A101ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_job_runtime import A101LocalJobRuntime


class LocalResourceWorkExecutionEpisode(A101LocalJobRuntime, A101ContractBinding):
    """Get the resource work executing as a bounded local job."""
    binding_path = 'sequence_homology_evidence/resource_work_submission/local_resource_work_execution'
    goal = 'Get the resource work executing as a bounded local job'
    unit = 'One local resource action'
    result = 'The local resource handle and its received status'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence/resource_work_submission'
