"""This private launch task's actual local-operation and replay checks."""
from gene_annotation_episode.episodic_workflow.root.a103.tests.launch_task_checks import LaunchTaskBehavior

class TestLaunchTask(LaunchTaskBehavior):
    home = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
