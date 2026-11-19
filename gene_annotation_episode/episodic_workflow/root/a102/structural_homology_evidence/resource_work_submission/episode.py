"""The A102 ``structural_homology_evidence/resource_work_submission`` binding on the generic runner.

Commissioned with the concrete resource work requests its parent selected (``requests``: each a
``request_id`` and the requested ``job``), it hands each request to a resource route child
(``api_resource_work_execution``, ``local_resource_work_execution`` or ``hpc_resource_work_execution``) with
that child's own declared assignment. Its decision source and continuation are A102's submission source
(``execution_job_submission/submission_source``): credit counts the requests with a usable handoff and the
completion controller's target is the number of requests.
"""
from __future__ import annotations

from ..contract_binding import A102ContractBinding
from ..execution_job_submission.submission_source import JobSubmissionBinding


class ResourceEpisode(JobSubmissionBinding, A102ContractBinding):
    binding_path = 'structural_homology_evidence/resource_work_submission'
    commissioning_parent = 'structural_homology_evidence'
