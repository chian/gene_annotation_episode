import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_bundle_v2_contracts import validate_parameters_v2 as validate_parameters, validate_result_selector_v2 as validate_result_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_directional_fact_contracts import validate_requested_form_v2 as validate_requested_form
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_bundle_adapter import _DEPENDENCIES as _LEGACY_DEPENDENCIES
ADAPTER_ID = 'bvbrc_proteome'
ADAPTER_VERSION = '2'
_DEPENDENCIES = tuple(sorted(set(_LEGACY_DEPENDENCIES) | {'bvbrc_proteome_bundle_adapter_v2.py', 'bvbrc_proteome_bundle_v2_contracts.py', 'bvbrc_proteome_bundle_v2_schemas.json', 'bvbrc_proteome_bundle_v2_resolution.py', 'bvbrc_proteome_numerical_sheet.py', 'bvbrc_proteome_directional_saved_validation.py', 'bvbrc_proteome_directional.py', 'bvbrc_proteome_directional_contracts.py', 'bvbrc_proteome_directional_schemas.json', 'bvbrc_proteome_directional_numerical_contracts.py', 'bvbrc_proteome_directional_numerical_schemas.json', 'bvbrc_proteome_directional_sheet.py', 'bvbrc_proteome_directional_geometry.py', 'bvbrc_proteome_directional_calculators.py', 'bvbrc_proteome_directional_fact_contracts.py', 'bvbrc_proteome_directional_projection.py', 'blast_pairwise_grader.py', 'blast_search.py', 'alignment_correspondence.py'}))

def implementation_sha256():
    """Actual installed A110 reader identity; retained epochs are authenticated separately."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.adapter_source_identity import current_implementation_sha256
    return current_implementation_sha256('bvbrc_proteome_bundle_adapter_v2')
