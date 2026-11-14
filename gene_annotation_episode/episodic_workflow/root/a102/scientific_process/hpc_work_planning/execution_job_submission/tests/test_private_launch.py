"""This parent's private Launch task and original child/report identities."""
from gene_annotation_episode.episodic_workflow.root.tests.hpc_launch_task_checks import LaunchTaskChecks


class TestPrivateLaunch(LaunchTaskChecks):
    axis = 'a102'
    binding_path = 'scientific_process/hpc_work_planning/execution_job_submission'
