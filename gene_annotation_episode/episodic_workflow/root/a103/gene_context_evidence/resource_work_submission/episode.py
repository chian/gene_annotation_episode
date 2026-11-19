"""The A103 ``gene_context_evidence/resource_work_submission`` binding on the generic runner.

Commissioned with the concrete resource work requests its parent selected (``requests``: each a
``request_id`` and the requested ``job``), it hands each request to a resource route child
(``api_resource_work_execution``, ``local_resource_work_execution`` or ``hpc_resource_work_execution``) with
that child's own declared assignment. Its decision source and continuation are A103's submission source
(``execution_job_submission/submission_source``): credit counts the requests with a usable handoff and the
completion controller's target is the number of requests.
"""
from __future__ import annotations

from types import MappingProxyType

from ..contract_binding import A103ContractBinding
from ..execution_job_submission.submission_source import JobSubmissionBinding


class ResourceEpisode(JobSubmissionBinding, A103ContractBinding):
    binding_path = 'gene_context_evidence/resource_work_submission'
    grain_name = 'gene_context_evidence__resource_work_submission'
    goal = 'Improve the resource work submitted for the parent request'
    unit = 'One resource route child commissioned for one requested piece of resource work'
    result = 'The resource work handoff'
    child_slots = MappingProxyType({'api_resource_work_execution': 'gene_context_evidence/resource_work_submission/api_resource_work_execution', 'hpc_resource_work_execution': 'gene_context_evidence/resource_work_submission/hpc_resource_work_execution', 'local_resource_work_execution': 'gene_context_evidence/resource_work_submission/local_resource_work_execution'})
    commissioning_parent = 'gene_context_evidence'
