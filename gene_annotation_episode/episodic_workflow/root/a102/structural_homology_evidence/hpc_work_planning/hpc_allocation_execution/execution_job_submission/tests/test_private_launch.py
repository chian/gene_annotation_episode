"""This parent's private Launch task and original child/report identities."""
from gene_annotation_episode.episodic_workflow.root.tests.hpc_launch_task_checks import LaunchTaskChecks


class TestPrivateLaunch(LaunchTaskChecks):
    axis = 'a102'
    binding_path = 'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
