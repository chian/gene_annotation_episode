"""The A103 ``gene_context_evidence/execution_job_submission`` binding on the generic runner.

Its decision source and completion continuation are ``execution_job_submission.submission_source``:
the model hands each commissioned execution request to a route child; credit counts the requests with a
usable handoff.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import A103ContractBinding
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_job_submission.submission_source import (
    JobSubmissionBinding)


class ExecutionEpisode(JobSubmissionBinding, A103ContractBinding):
    binding_path = 'gene_context_evidence/execution_job_submission'
    grain_name = 'gene_context_evidence__execution_job_submission'
    goal = 'Improve the execution work submitted for the parent requested jobs'
    unit = 'One route child commissioned for one requested job'
    result = 'Execution handoffs for the submitted jobs'
    child_slots = MappingProxyType({'api_job_execution': 'gene_context_evidence/execution_job_submission/api_job_execution', 'hpc_job_execution': 'gene_context_evidence/execution_job_submission/hpc_job_execution', 'local_job_execution': 'gene_context_evidence/execution_job_submission/local_job_execution'})
    commissioning_parent = 'gene_context_evidence'
