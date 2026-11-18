"""This private API task's actual local-operation and replay checks."""
from gene_annotation_episode.episodic_workflow.root.a103.tests.api_task_checks import APIJobTaskBehavior

class TestAPIJobTask(APIJobTaskBehavior):
    home = 'gene_context_evidence/execution_job_submission/api_job_execution'
