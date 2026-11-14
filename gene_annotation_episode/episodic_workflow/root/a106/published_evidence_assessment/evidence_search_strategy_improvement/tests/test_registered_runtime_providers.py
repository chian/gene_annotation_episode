"""Original provider boundaries for this existing A106 private task."""
import pytest
from gene_annotation_episode.episodic_workflow.root.a106.tests import a106_registered_provider_checks as checks

HOME = 'published_evidence_assessment/evidence_search_strategy_improvement'

def test_private_source_providers_and_original_builtin(monkeypatch):
    checks.assert_private_owners(HOME, monkeypatch)

