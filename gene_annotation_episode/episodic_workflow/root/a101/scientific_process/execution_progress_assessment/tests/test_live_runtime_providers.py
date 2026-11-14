"""Original-provider controls owned by this existing private task."""
from gene_annotation_episode.episodic_workflow.root.a101.tests import other_task_runtime_provider_checks as checks

HOME = 'scientific_process/execution_progress_assessment'

def test_private_runtime_provider_ownership(monkeypatch):
    checks.assert_private_owners(HOME)
    checks.assert_conversation_lookup(HOME, monkeypatch)
