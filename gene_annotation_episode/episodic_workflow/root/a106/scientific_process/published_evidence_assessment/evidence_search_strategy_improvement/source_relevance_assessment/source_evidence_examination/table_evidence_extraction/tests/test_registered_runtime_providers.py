"""Original provider boundaries for this existing A106 private task."""
import pytest
from gene_annotation_episode.episodic_workflow.root.a106.tests import a106_registered_provider_checks as checks

HOME = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'

def test_private_source_providers_and_original_builtin(monkeypatch):
    checks.assert_private_owners(HOME, monkeypatch)

