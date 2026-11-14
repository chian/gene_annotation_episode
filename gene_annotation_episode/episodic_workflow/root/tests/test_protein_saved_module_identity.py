"""Preserve saved producer names while accepting the relocated implementation."""
import pytest
from gene_annotation_episode.episodic_workflow.root.library import native_protein_structure_contracts
from .protein_saved_module_identity_checks import CASES, check


@pytest.mark.parametrize('case', CASES)
def test_retained_and_relocated_protein_module_identity(case):
    check(case, native_protein_structure_contracts)
