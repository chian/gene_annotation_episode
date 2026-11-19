"""This A102 execution job submission binding on the generic runner (``episode_runtime``).

Its decision source and completion continuation are ``execution_job_submission.submission_source``: the model
hands each commissioned execution request to a route child; credit counts the requests with a usable handoff.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.execution_job_submission.submission_source import (
    JobSubmissionBinding)


class ExecutionEpisode(JobSubmissionBinding, A102ContractBinding):
    binding_path = 'structural_homology_evidence/execution_job_submission'
    commissioning_parent = 'structural_homology_evidence'
