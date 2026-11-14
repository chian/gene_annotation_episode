"""This private launch task's actual local-operation and replay checks."""
from gene_annotation_episode.episodic_workflow.root.a102.tests.native_task_checks import NativeTaskBehavior

class TestNativeTask(NativeTaskBehavior):
    home = 'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution'
