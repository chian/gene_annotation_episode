"""A101's proteome numerical sheet is built and validated against A101's own sheet contracts, on the recorded native
directional report fixture."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.sequence_homology_evidence import (
    bvbrc_proteome_bundle_v2_contracts, bvbrc_proteome_directional_numerical_contracts)
from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation.sequence_homology_evidence import (
    bvbrc_proteome_numerical_sheet as sheet_module)
from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation.sequence_homology_evidence.bvbrc_proteome_numerical_sheet import (
    build_proteome_numerical_sheet)

from .test_bvbrc_proteome_directional_sheet import native_sheet


def test_the_numerical_sheet_binds_a101_contracts():
    assert sheet_module.validate_shape_v2 is bvbrc_proteome_bundle_v2_contracts.validate_shape_v2
    assert (sheet_module.validate_directional_numerical
            is bvbrc_proteome_directional_numerical_contracts.validate_directional_numerical)


def test_the_directional_sheet_is_composed_unbound_and_an_empty_composition_fails():
    directional = native_sheet()
    built = build_proteome_numerical_sheet(legacy_sheet=None, directional_sheet=directional)
    assert built['version'] == 'bvbrc_proteome_numerical_sheet_v2'
    assert built['directional_operand_binding'] == 'unbound'
    assert built['directional_sheet'] == directional and built['legacy_sheet'] is None
    with pytest.raises(bvbrc_proteome_bundle_v2_contracts.ProteomeBundleV2Error):
        build_proteome_numerical_sheet(legacy_sheet=None, directional_sheet=None)
