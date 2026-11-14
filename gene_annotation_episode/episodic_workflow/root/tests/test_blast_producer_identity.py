"""Preserve recorded producers and qualify the actual running implementation."""
import pytest
from gene_annotation_episode.episodic_workflow.root.library import native_blast_database_contracts as contracts
from gene_annotation_episode.episodic_workflow.root.library import native_blast_database_driver as driver
from .blast_producer_identity_checks import CASES, check


@pytest.mark.parametrize('case', CASES)
def test_saved_blast_producer_and_running_module_identity(case, tmp_path):
    check(case, contracts, driver, tmp_path)
