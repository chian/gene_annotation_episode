"""This private launch task's actual local-operation and replay checks."""
from gene_annotation_episode.episodic_workflow.root.a103.tests.native_task_checks import NativeTaskBehavior

class TestNativeTask(NativeTaskBehavior):
    home = 'scientific_process/execution_job_submission/local_job_execution'
