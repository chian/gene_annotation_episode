"""The A106 launch binding (``perturbation_evidence/published_evidence_assessment/execution_job_submission``): its submission source and completion continuation are
``execution_job_submission.submission_source.JobSubmissionContract``."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_job_submission.submission_source import (
    JobSubmissionContract)


class ExecutionEpisode(JobSubmissionContract):
    binding_path = 'perturbation_evidence/published_evidence_assessment/execution_job_submission'
    commissioning_parent = 'perturbation_evidence/published_evidence_assessment'
    roles = ('launch',)
    goal = "The analysis work its parent commissioned, carried to retained native records"
    unit = "One API launch child commissioned for one requested job"
    result = "The retained handoff and acquired record references"
