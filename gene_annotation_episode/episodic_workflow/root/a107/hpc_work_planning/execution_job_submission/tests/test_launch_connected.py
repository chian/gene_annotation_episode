"""Connected A107 hpc_work_planning/execution_job_submission contracts."""
from gene_annotation_episode.episodic_workflow.root.a107.tests.launch_connected import LaunchConnectedChecks


class TestLaunchConnected(LaunchConnectedChecks):
    binding_path = "hpc_work_planning/execution_job_submission"

