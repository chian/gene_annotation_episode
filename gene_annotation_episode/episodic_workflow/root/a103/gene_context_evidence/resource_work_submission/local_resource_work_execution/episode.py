"""The A103 ``gene_context_evidence/resource_work_submission/local_resource_work_execution`` binding.

It executes the commissioned resource work (a frozen ``practical_assignment_v1``, ``resource_kind`` ``local``)
on its own configured local resource: model-written ``exec_command`` units, practical requirement credit and
completion continuation (``episode_support/jobs/local_execution/gene_context_evidence/local_job_runtime.py``). The A103 home factory constructs it from
``a103_local_resource_work_execution``.
"""
from __future__ import annotations

from types import MappingProxyType

from ...contract_binding import A103ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.local_job_runtime import A103LocalJobRuntime


class ResourceEpisode(A103LocalJobRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/resource_work_submission/local_resource_work_execution'
    grain_name = 'gene_context_evidence__resource_work_submission__local_resource_work_execution'
    goal = 'Improve the local resource work and its handoff'
    unit = 'One local resource action'
    result = 'The local resource handoff'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/resource_work_submission'
