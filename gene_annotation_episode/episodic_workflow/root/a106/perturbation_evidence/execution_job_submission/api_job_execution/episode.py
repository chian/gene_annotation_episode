"""The A106 launch_api binding (``perturbation_evidence/execution_job_submission/api_job_execution``): one assigned
BV-BRC AppService job on ``episode_runtime`` (``binding.ApiJobBinding``)."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_job_submission.api_job_execution.\
    binding import ApiJobBinding


class ExecutionEpisode(ApiJobBinding):
    binding_path = 'perturbation_evidence/execution_job_submission/api_job_execution'
    commissioning_parent = 'perturbation_evidence/execution_job_submission'
    roles = ('launch_api',)
    goal = "The analysis work its parent commissioned, carried to retained native records"
    unit = "One API service action"
    result = "The retained API handoff and record references"
