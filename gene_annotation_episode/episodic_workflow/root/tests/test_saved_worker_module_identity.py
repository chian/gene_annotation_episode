"""Validate exact stored owner identities without executing native work."""
import importlib
import pytest
from .saved_worker_identity_checks import CASES, check


@pytest.mark.parametrize('case', CASES)
def test_original_and_current_worker_record_identity(case):
    stems = {'rna_job': 'native_rna_structure_contracts', 'genomic_job': 'genomic_overlap_job_validation',
             'flux_job': 'native_flux_balance_contracts', 'nmf_intent': 'native_expression_nmf_preparation',
             'genomic_intent': 'native_genomic_overlap_preparation'}
    family = case.split(':')[0]
    module = importlib.import_module('gene_annotation_episode.episodic_workflow.root.library.' + stems[family])
    check(case, {family: module})
