"""Connected A110 biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission contracts."""
from gene_annotation_episode.episodic_workflow.root.a110.tests.launch_connected import LaunchConnectedChecks


class TestLaunchConnected(LaunchConnectedChecks):
    binding_path = "biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission"

