import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_genome_alignment_bundle_contracts import validate_parameters, validate_requested_form
ADAPTER_ID = 'bvbrc_genome_alignment'
ADAPTER_VERSION = '1'
_DEPENDENCIES = ('__init__.py', 'acquisition.py', 'bvbrc_alignment_values.py', 'bvbrc_analysis_protocol.py', 'bvbrc_appservice_contracts.py', 'bvbrc_appservice_readers.py', 'bvbrc_appservice_schemas.json', 'bvbrc_genome_alignment_associations.py', 'bvbrc_genome_alignment_bundle_adapter.py', 'bvbrc_genome_alignment_bundle_contracts.py', 'bvbrc_genome_alignment_bundle_projection.py', 'bvbrc_genome_alignment_bundle_resolution.py', 'bvbrc_genome_alignment_calculation_contracts.py', 'bvbrc_genome_alignment_calculators.py', 'bvbrc_genome_alignment_input_contracts.py', 'bvbrc_genome_alignment_inputs.py', 'bvbrc_genome_alignment_retained_records.py', 'bvbrc_genome_alignment_sheet.py', 'chemistry.py', 'communication.py', 'domain.py', 'execution_contracts.py', 'episode_bindings.py', 'form_reference_validation.py', 'launch_instructions.py', 'literature_assets.py', 'mauve_backbone_calculators.py', 'mauve_backbone_contracts.py', 'mauve_backbone_formats.py', 'mauve_v4_calculation_contracts.py', 'mauve_v4_calculators.py', 'mauve_v4_format_contracts.py', 'mauve_v4_formats.py', 'phylogeny_calculation_contracts.py', 'phylogeny_format_contracts.py', 'public_configuration.py', 'rfam_discovery.py', 'tool_knowledge.py', 'xmfa_calculation_contracts.py', 'xmfa_calculators.py', 'xmfa_coordinates.py', 'xmfa_format_contracts.py', 'xmfa_formats.py', 'xmfa_source_contracts.py', 'xmfa_sources.py')

def implementation_sha256() -> str:
    """Actual installed A110 reader identity; retained epochs are authenticated separately."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.adapter_source_identity import current_implementation_sha256
    return current_implementation_sha256('bvbrc_genome_alignment_bundle_adapter')
