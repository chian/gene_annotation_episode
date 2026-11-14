"""Retained release hashes name their original modules, not current import paths."""
import pytest

from gene_annotation_episode.episodic_workflow.root.a106.library import literature_kinetic_inputs as kinetic
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_optical_inputs as optical
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_optical_validation as validation
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_amount_inputs as amount


LEGACY = {
    'custody_module': 'gene_annotation_episode.literature_assay_inputs',
    'custody_sha256': '52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e',
    'scalar_module': 'gene_annotation_episode.literature_rate_native_inputs',
    'scalar_sha256': '55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500',
    'scalar_scope_module': 'gene_annotation_episode.literature_partner_source_fields',
    'scalar_scope_sha256': '20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17',
}
LEXICAL = {
    'module': 'gene_annotation_episode.literature_rate_native_inputs',
    'sha256_at_release': '55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500',
    'interface': "_number(selection,sources,role='rate'); _field_contexts",
    'scope_module': 'gene_annotation_episode.literature_partner_source_fields',
    'scope_sha256_at_release': '20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17',
    'custody_module': 'gene_annotation_episode.literature_assay_inputs',
    'custody_sha256_at_release': '52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e',
}


def test_original_kinetic_release_identities_and_hashes_are_not_relabelled():
    assert kinetic.LEGACY_DEPENDENCIES == LEGACY
    assert kinetic.DEPENDENCY_RELEASES[kinetic.LEGACY_VERSION] == LEGACY
    assert kinetic.DEPENDENCIES == {**LEGACY,
        'scalar_scope_sha256': '6683a39272203ff0b2844c951ab13b2333ae0ae16e3966c4eb932970f30764a8'}


@pytest.mark.parametrize('actual', [optical.LEXICAL_DEPENDENCY, validation._LEXICAL_DEPENDENCY])
def test_optical_reader_and_validator_preserve_original_release_identity(actual):
    assert actual == LEXICAL


@pytest.mark.parametrize('actual,expected', [
    (amount._RELEASED027_LEXICAL_DEPENDENCY, {
        'module': 'gene_annotation_episode.literature_rate_native_inputs',
        'sha256_at_release': '264328313d32a8ed0315eb4a80388be775a8c7c2b51ad25041aad071a295dc67',
        'interface': "_number(selection,sources,role='rate'); _field_contexts"}),
    (amount.LEXICAL_DEPENDENCY, {
        'module': 'gene_annotation_episode.literature_rate_native_inputs',
        'sha256_at_release': '55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500',
        'interface': "_number(selection,sources,role='rate'); _field_contexts",
        'scope_generation': 'completed_allocation_addition_v1',
        'scope_module': 'gene_annotation_episode.literature_partner_source_fields',
        'scope_sha256_at_release': '20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17'}),
])
def test_amount_releases_keep_their_exact_module_identity_and_hash(actual, expected):
    assert actual == expected
