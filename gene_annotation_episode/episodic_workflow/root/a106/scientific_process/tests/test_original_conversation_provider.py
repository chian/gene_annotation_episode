"""Only the newly bound original Scientific conversation-key lookup."""
from gene_annotation_episode.episodic_workflow.root.a106.tests import a106_registered_provider_checks as checks

def test_original_scientific_conversation_builtin(monkeypatch):
    checks.assert_conversation_lookup("scientific_process", monkeypatch)
