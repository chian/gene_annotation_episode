"""Finite actual saved and declared-current module identity boundaries."""
import pytest

from gene_annotation_episode.episodic_workflow.root.tests.fluorescence_module_identity_checks import CASES, check
from gene_annotation_episode.episodic_workflow.root.library import native_fluorescence_contracts as contracts
from gene_annotation_episode.episodic_workflow.root.library import native_fluorescence_preparation as preparation


@pytest.mark.parametrize('case', CASES)
def test_fluorescence_module_and_source_identity(case):
    check(case, contracts, preparation)
