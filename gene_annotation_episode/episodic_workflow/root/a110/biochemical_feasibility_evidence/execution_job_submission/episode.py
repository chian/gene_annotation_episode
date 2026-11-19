"""The A110 execution_job_submission binding.

Its decision source and completion continuation are ``execution_job_submission.submission_source``: the model
hands each commissioned execution request to a route child; credit counts the requests with a usable handoff.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    CHILD_ASSIGNMENT_FORM, REQUIRED_COLLABORATORS, RETURN_FORM, EpisodeRuntimeContract)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.execution_job_submission.submission_source import (
    JobSubmissionBinding)


class ExecutionJobSubmissionEpisode(JobSubmissionBinding, EpisodeRuntimeContract):
    """Submit the planned computation and keep its handoff to the actual job and inputs."""
    binding_path = 'biochemical_feasibility_evidence/execution_job_submission'
    grain_name = binding_path.replace('/', '__')
    goal = 'Submit the planned computation and keep its handoff to the actual job and inputs'
    unit = 'One local or HPC route child commissioned for one requested job'
    result = 'The job handoff references and submission findings'
    child_slots = MappingProxyType({'hpc_job_execution': 'biochemical_feasibility_evidence/execution_job_submission/hpc_job_execution', 'local_job_execution': 'biochemical_feasibility_evidence/execution_job_submission/local_job_execution'})
    required_collaborators = REQUIRED_COLLABORATORS
    assignment_form = CHILD_ASSIGNMENT_FORM
    return_form = RETURN_FORM
    commissioning_parent = 'biochemical_feasibility_evidence'
