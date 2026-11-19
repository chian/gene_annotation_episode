"""The A102 ``structural_homology_evidence/resource_work_submission/local_resource_work_execution`` binding.

It executes the commissioned resource work (a frozen ``practical_assignment_v1``, ``resource_kind`` ``local``)
on its own configured local resource: model-written ``exec_command`` units, practical requirement credit and
completion continuation (``episode_support/jobs/local_execution/structural_homology_evidence/local_job_runtime.py``). ``a102_home_factory`` constructs it from
``services['a102']['local_resource_work_execution']``.
"""
from __future__ import annotations

from ...contract_binding import A102ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.local_job_runtime import A102LocalJobRuntime


class ResourceEpisode(A102LocalJobRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/resource_work_submission/local_resource_work_execution'
    commissioning_parent = 'structural_homology_evidence/resource_work_submission'
