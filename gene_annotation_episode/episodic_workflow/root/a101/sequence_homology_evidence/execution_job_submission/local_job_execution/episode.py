"""The A101 ``sequence_homology_evidence/execution_job_submission/local_job_execution`` binding.

Its exec_command decisions over the assigned local resource, practical requirement credit and
completion continuation are the A101 local job runtime's (``episode_support/jobs/local_execution/sequence_homology_evidence/local_job_runtime.py``).
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_job_runtime import A101LocalJobRuntime
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.contract_binding import (
    A101ContractBinding)


class LocalJobExecutionEpisode(A101LocalJobRuntime, A101ContractBinding):
    """Get the submitted computation executing as a bounded local job."""
    binding_path = 'sequence_homology_evidence/execution_job_submission/local_job_execution'
    goal = 'Get the submitted computation executing as a bounded local job'
    unit = 'One local job action'
    result = 'The local execution handle and its received status'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence/execution_job_submission'
