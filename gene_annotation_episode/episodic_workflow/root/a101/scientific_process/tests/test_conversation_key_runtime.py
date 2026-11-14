"""Only the newly bound original Scientific conversation-key method."""
from gene_annotation_episode.episodic_workflow.root.a101.tests import other_task_runtime_provider_checks as checks

def test_original_conversation_key_lookup(monkeypatch):
    checks.assert_conversation_lookup("scientific_process", monkeypatch)
