"""The A110 local_job_execution binding: the A110 local job runtime (``episode_support/jobs/local_execution/biochemical_feasibility_evidence/local_job_runtime.py``).

Its exec_command decisions over the assigned local resource, practical requirement credit and
completion continuation are that runtime's own; this class declares its identity and forms.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    CHILD_ASSIGNMENT_FORM, RETURN_FORM, EpisodeRuntimeContract)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.local_job_runtime import A110LocalJobRuntime


class LocalJobExecutionEpisode(A110LocalJobRuntime, EpisodeRuntimeContract):
    """Execute the frozen request locally and retain its receipts."""
    binding_path = 'biochemical_feasibility_evidence/execution_job_submission/local_job_execution'
    grain_name = binding_path.replace('/', '__')
    goal = 'Execute the frozen request locally and retain its receipts'
    unit = 'One local execution action'
    result = 'The local execution receipts and committed records'
    child_slots = MappingProxyType({})
    assignment_form = CHILD_ASSIGNMENT_FORM
    return_form = RETURN_FORM
    commissioning_parent = 'biochemical_feasibility_evidence/execution_job_submission'
