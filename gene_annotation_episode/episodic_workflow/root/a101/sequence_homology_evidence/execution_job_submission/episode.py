"""The A101 ``sequence_homology_evidence/execution_job_submission`` binding.

Its decision source and continuation are ``submission_source``: the model hands each commissioned
execution request to an execution route child; credit counts the requests with a usable handoff and the
completion controller's target is the number of requests.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.contract_binding import (
    A101ContractBinding)

from .submission_source import JobSubmissionBinding


class ExecutionJobSubmissionEpisode(JobSubmissionBinding, A101ContractBinding):
    """Get the selected sequence-homology computation accepted and running on a suitable execution route."""
    binding_path = 'sequence_homology_evidence/execution_job_submission'
    goal = 'Get the selected sequence-homology computation accepted and running on a suitable execution route'
    unit = 'One route child commission for one requested job'
    result = 'The execution handoffs for the submitted requests'
    child_slots = MappingProxyType({'api_job_execution': 'sequence_homology_evidence/execution_job_submission/api_job_execution', 'local_job_execution': 'sequence_homology_evidence/execution_job_submission/local_job_execution', 'hpc_job_execution': 'sequence_homology_evidence/execution_job_submission/hpc_job_execution'})
    commissioning_parent = 'sequence_homology_evidence'
