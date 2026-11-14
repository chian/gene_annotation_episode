"""Connected A110 hpc_work_planning/execution_job_submission contracts."""
from gene_annotation_episode.episodic_workflow.root.a110.tests.launch_connected import LaunchConnectedChecks


class TestLaunchConnected(LaunchConnectedChecks):
    binding_path = "hpc_work_planning/execution_job_submission"

