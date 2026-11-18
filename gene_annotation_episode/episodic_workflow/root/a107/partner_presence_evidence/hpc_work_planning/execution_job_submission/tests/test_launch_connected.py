"""Connected A107 partner_presence_evidence/hpc_work_planning/execution_job_submission contracts."""
from gene_annotation_episode.episodic_workflow.root.a107.tests.launch_connected import LaunchConnectedChecks


class TestLaunchConnected(LaunchConnectedChecks):
    binding_path = "partner_presence_evidence/hpc_work_planning/execution_job_submission"

