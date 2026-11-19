"""The A101 ``sequence_homology_evidence/resource_work_submission`` binding.

Commissioned with the concrete resource work requests its parent selected (``requests``: each a
``request_id`` and the requested ``job``), it hands each request to a resource route child
(``api_resource_work_execution``, ``local_resource_work_execution`` or ``hpc_resource_work_execution``) with
that child's own declared assignment. Its decision source and continuation are A101's submission source
(``execution_job_submission/submission_source``): credit counts the requests with a usable handoff (a child
return with positive credit) and the completion controller's target is the number of requests.
"""
from __future__ import annotations

from types import MappingProxyType

from ..contract_binding import A101ContractBinding
from ..execution_job_submission.submission_source import JobSubmissionBinding


class ResourceWorkSubmissionEpisode(JobSubmissionBinding, A101ContractBinding):
    """Get the selected resource work accepted and running on a suitable route."""
    binding_path = 'sequence_homology_evidence/resource_work_submission'
    goal = 'Get the selected resource work accepted and running on a suitable route'
    unit = 'One resource route child commission for one requested piece of resource work'
    result = 'Resource work handoff references'
    child_slots = MappingProxyType({'api_resource_work_execution': 'sequence_homology_evidence/resource_work_submission/api_resource_work_execution', 'local_resource_work_execution': 'sequence_homology_evidence/resource_work_submission/local_resource_work_execution', 'hpc_resource_work_execution': 'sequence_homology_evidence/resource_work_submission/hpc_resource_work_execution'})
    commissioning_parent = 'sequence_homology_evidence'
