from __future__ import annotations
import hashlib
from pathlib import Path
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_alignment_bundle_contracts as contracts
ADAPTER_ID = 'bvbrc_msa'
ADAPTER_VERSION = '1'
_DEPENDENCIES = ('bvbrc_alignment_bundle_contracts.py', 'bvbrc_alignment_bundle_resolution.py', 'bvbrc_alignment_bundle_projection.py', 'bvbrc_msa_bundle_adapter.py', 'bvbrc_metacats_bundle_adapter.py', 'bvbrc_alignment_provider_contracts.py', 'bvbrc_alignment_associations.py', 'bvbrc_alignment_values.py', 'bvbrc_msa_provider_contracts.py', 'bvbrc_msa_inputs.py', 'bvbrc_msa_grader.py', 'bvbrc_msa_xmfa_inputs.py', 'bvbrc_msa_formats.py', 'bvbrc_msa_format_contracts.py', 'bvbrc_msa_calculators.py', 'bvbrc_msa_calculation_contracts.py', 'bvbrc_metacats_provider_contracts.py', 'bvbrc_metacats_inputs.py', 'bvbrc_metacats_grader.py', 'bvbrc_metacats_associations.py', 'bvbrc_metacats_association_contracts.py', 'bvbrc_metacats_formats.py', 'bvbrc_metacats_format_contracts.py', 'bvbrc_metacats_input_formats.py', 'bvbrc_metacats_calculators.py', 'bvbrc_metacats_calculation_contracts.py', 'bvbrc_metacats_biological_calculators.py', 'bvbrc_metacats_biological_contracts.py', 'bvbrc_metacats_adequacy.py', 'bvbrc_contingency_math.py', 'phylogeny_formats.py', 'phylogeny_format_contracts.py', 'phylogeny_calculators.py', 'phylogeny_calculation_contracts.py', 'xmfa_formats.py', 'xmfa_format_contracts.py', 'xmfa_sources.py', 'xmfa_source_contracts.py', 'xmfa_coordinates.py', 'xmfa_calculators.py', 'xmfa_calculation_contracts.py', 'bvbrc_appservice_contracts.py', 'bvbrc_appservice_schemas.json')

def validate_parameters(parameters: dict) -> dict:
    return contracts.validate_parameters(parameters, provider='msa')

def validate_requested_form(requested_form: dict) -> dict:
    return contracts.validate_requested_form(requested_form, provider='msa')

def implementation_sha256() -> str:
    """Actual installed A110 reader identity; retained epochs are authenticated separately."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.adapter_source_identity import current_implementation_sha256
    return current_implementation_sha256('bvbrc_msa_bundle_adapter')
