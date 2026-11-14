import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_bundle_contracts import validate_parameters
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_fact_contracts import validate_requested_form
ADAPTER_ID = 'bvbrc_proteome'
ADAPTER_VERSION = '1'
_DEPENDENCIES = ('__init__.py', 'bvbrc_appservice_contracts.py', 'bvbrc_appservice_schemas.json', 'bvbrc_proteome_bundle_adapter.py', 'bvbrc_proteome_bundle_contracts.py', 'bvbrc_proteome_bundle_projection.py', 'bvbrc_proteome_bundle_resolution.py', 'bvbrc_proteome_bundle_schemas.json', 'bvbrc_proteome_calculators.py', 'bvbrc_proteome_data_contracts.py', 'bvbrc_proteome_data_schemas.json', 'bvbrc_proteome_fact_contracts.py', 'bvbrc_proteome_inputs.py', 'bvbrc_proteome_joins.py', 'bvbrc_proteome_native.py', 'bvbrc_proteome_native_contracts.py', 'bvbrc_proteome_native_schemas.json', 'bvbrc_proteome_sheet.py', 'bvbrc_proteome_sheet_contracts.py', 'bvbrc_proteome_sheet_schemas.json')

def implementation_sha256() -> str:
    """Actual installed A110 reader identity; retained epochs are authenticated separately."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.adapter_source_identity import current_implementation_sha256
    return current_implementation_sha256('bvbrc_proteome_bundle_adapter')
