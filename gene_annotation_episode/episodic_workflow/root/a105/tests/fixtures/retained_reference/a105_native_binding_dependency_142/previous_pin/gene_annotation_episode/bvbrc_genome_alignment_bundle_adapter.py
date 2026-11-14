"""Pinned pure GenomeAlignment facade for the existing AppService owner."""
import hashlib
from pathlib import Path

from .bvbrc_genome_alignment_bundle_contracts import (
    validate_parameters, parameters_schema, requested_form_schema, validate_requested_form,
)
from .bvbrc_genome_alignment_bundle_resolution import consume_bundle

ADAPTER_ID = 'bvbrc_genome_alignment'
ADAPTER_VERSION = '1'

# This exact transitive source/resource closure is audited by the facade tests.
# It includes actual C receipt-decoding imports; consumers are not dependencies.
_DEPENDENCIES = (
    '__init__.py',
    'acquisition.py',
    'bvbrc_alignment_values.py',
    'bvbrc_analysis_protocol.py',
    'bvbrc_appservice_contracts.py',
    'bvbrc_appservice_readers.py',
    'bvbrc_appservice_schemas.json',
    'bvbrc_genome_alignment_associations.py',
    'bvbrc_genome_alignment_bundle_adapter.py',
    'bvbrc_genome_alignment_bundle_contracts.py',
    'bvbrc_genome_alignment_bundle_projection.py',
    'bvbrc_genome_alignment_bundle_resolution.py',
    'bvbrc_genome_alignment_calculation_contracts.py',
    'bvbrc_genome_alignment_calculators.py',
    'bvbrc_genome_alignment_input_contracts.py',
    'bvbrc_genome_alignment_inputs.py',
    'bvbrc_genome_alignment_retained_records.py',
    'bvbrc_genome_alignment_sheet.py',
    'chemistry.py',
    'communication.py',
    'domain.py',
    'execution_contracts.py',
    'episode_bindings.py',
    'form_reference_validation.py',
    'launch_instructions.py',
    'literature_assets.py',
    'mauve_backbone_calculators.py',
    'mauve_backbone_contracts.py',
    'mauve_backbone_formats.py',
    'mauve_v4_calculation_contracts.py',
    'mauve_v4_calculators.py',
    'mauve_v4_format_contracts.py',
    'mauve_v4_formats.py',
    'phylogeny_calculation_contracts.py',
    'phylogeny_format_contracts.py',
    'public_configuration.py',
    'rfam_discovery.py',
    'tool_knowledge.py',
    'xmfa_calculation_contracts.py',
    'xmfa_calculators.py',
    'xmfa_coordinates.py',
    'xmfa_format_contracts.py',
    'xmfa_formats.py',
    'xmfa_source_contracts.py',
    'xmfa_sources.py',
)


def implementation_sha256() -> str:
    """Configuration-only, length-framed filename-sorted source digest."""
    digest = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        content = Path(__file__).with_name(name).read_bytes()
        digest.update(name.encode() + b'\0' + str(len(content)).encode() + b'\0' + content)
    return digest.hexdigest()


__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'validate_parameters', 'parameters_schema',
    'requested_form_schema', 'validate_requested_form', 'consume_bundle', 'implementation_sha256']
