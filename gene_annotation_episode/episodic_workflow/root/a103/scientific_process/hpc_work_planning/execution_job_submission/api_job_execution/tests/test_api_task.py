"""This private API task's actual local-operation and replay checks."""
from gene_annotation_episode.episodic_workflow.root.a103.tests.api_task_checks import APIJobTaskBehavior

class TestAPIJobTask(APIJobTaskBehavior):
    home = 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution'
