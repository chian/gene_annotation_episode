"""Pinned pure GenomeAlignment facade for the existing AppService owner."""
import hashlib
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_genome_alignment_bundle_contracts import (
    validate_parameters, parameters_schema, requested_form_schema, validate_requested_form,
)
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_genome_alignment_bundle_resolution import consume_bundle

ADAPTER_ID = 'bvbrc_genome_alignment'
ADAPTER_VERSION = '1'

# This exact transitive source/resource closure is audited by the facade tests.
# It includes actual C receipt-decoding imports; consumers are not dependencies.
_DEPENDENCIES = (
    '__init__.py',
    'acquisition.py',
    'addgene_access.py',
    'addgene_sequence_native.py',
    'episodic_workflow/root/library/alignment_correspondence.py',
    'alphafold_acquisition.py',
    'episodic_workflow/root/library/biopython_pairwise_grader.py',
    'boundary_validation.py',
    'episodic_workflow/root/library/bvbrc_alignment_values.py',
    'bvbrc_analysis_protocol.py',
    'bvbrc_appservice_contracts.py',
    'bvbrc_appservice_readers.py',
    'bvbrc_appservice_schemas.json',
    'episodic_workflow/root/library/bvbrc_genome_alignment_bundle_contracts.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_bundle_projection.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_calculation_contracts.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_input_contracts.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_sheet.py',
    'episodic_workflow/root/library/chemistry.py',
    'credentials.py',
    'data_acquisition_receipts.py',
    'domain.py',
    'emdb_acquisition.py',
    'ensembl_acquisition.py',
    'episodic_workflow/__init__.py',
    'episodic_workflow/root/__init__.py',
    'episodic_workflow/root/library/__init__.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_associations.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_bundle_adapter.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_bundle_resolution.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_calculators.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_inputs.py',
    'episodic_workflow/root/library/bvbrc_genome_alignment_retained_records.py',
    'episodic_workflow/root/library/mauve_backbone_calculators.py',
    'episodic_workflow/root/library/mauve_backbone_formats.py',
    'episodic_workflow/root/library/mauve_v4_calculators.py',
    'episodic_workflow/root/library/mauve_v4_formats.py',
    'episodic_workflow/root/library/xmfa_calculators.py',
    'episodic_workflow/root/library/xmfa_coordinates.py',
    'episodic_workflow/root/library/xmfa_formats.py',
    'episodic_workflow/root/library/xmfa_sources.py',
    'literature_assets.py',
    'episodic_workflow/root/library/mauve_backbone_contracts.py',
    'episodic_workflow/root/library/mauve_v4_calculation_contracts.py',
    'episodic_workflow/root/library/mauve_v4_format_contracts.py',
    'molecular_provider_acquisition.py',
    'episodic_workflow/root/library/phylogeny_calculation_contracts.py',
    'episodic_workflow/root/library/phylogeny_format_contracts.py',
    'episodic_workflow/root/library/protein_structure_contracts.py',
    'public_configuration.py',
    'rcsb_acquisition.py',
    'execution_contracts.py',
    'episodic_workflow/root/communication.py',
    'episodic_workflow/root/library/rfam_discovery.py',
    'ucsc_acquisition.py',
    'uniprot_native.py',
    'uniprot_native_contracts.py',
    'episodic_workflow/root/library/xmfa_calculation_contracts.py',
    'episodic_workflow/root/library/xmfa_format_contracts.py',
    'episodic_workflow/root/library/xmfa_source_contracts.py',
)


def implementation_sha256() -> str:
    """Configuration-only, length-framed filename-sorted source digest."""
    digest = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        content = (Path(__file__).resolve().parents[3] / name).read_bytes()
        digest.update(name.encode() + b'\0' + str(len(content)).encode() + b'\0' + content)
    return digest.hexdigest()


__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'validate_parameters', 'parameters_schema',
    'requested_form_schema', 'validate_requested_form', 'consume_bundle', 'implementation_sha256']
