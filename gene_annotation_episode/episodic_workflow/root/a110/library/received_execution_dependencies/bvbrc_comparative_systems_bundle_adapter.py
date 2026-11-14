from __future__ import annotations
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_bundle_contracts import validate_parameters
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_fact_contracts import validate_requested_form
ADAPTER_ID = 'bvbrc_comparative_systems'
ADAPTER_VERSION = '1'
_DEPENDENCIES = ('__init__.py', 'bvbrc_appservice_contracts.py', 'bvbrc_appservice_schemas.json', 'bvbrc_comparative_systems_bundle_adapter.py', 'bvbrc_comparative_systems_bundle_contracts.py', 'bvbrc_comparative_systems_bundle_resolution.py', 'bvbrc_comparative_systems_bundle_projection.py', 'bvbrc_comparative_systems_fact_contracts.py', 'bvbrc_comparative_systems_handoff_contracts.py', 'bvbrc_comparative_systems_handoff_schemas.json', 'bvbrc_comparative_systems_native.py', 'bvbrc_comparative_systems_sheet.py', 'bvbrc_comparative_systems_sheet_contracts.py', 'bvbrc_comparative_systems_calculators.py', 'bvbrc_comparative_systems_calculation_contracts.py', 'bvbrc_comparative_systems_data_inputs.py', 'bvbrc_comparative_systems_data_contracts.py', 'acquisition.py', 'execution_contracts.py', 'bvbrc_data_fields.py', 'bvbrc_data_query.py', 'bvbrc_data_readers.py', 'bvbrc_data_schema.py', 'chemistry.py', 'communication.py', 'domain.py', 'episode_bindings.py', 'form_reference_validation.py', 'launch_instructions.py', 'literature_assets.py', 'public_configuration.py', 'rfam_discovery.py', 'tool_knowledge.py')

def implementation_sha256():
    """Actual installed A110 reader identity; retained epochs are authenticated separately."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.adapter_source_identity import current_implementation_sha256
    return current_implementation_sha256('bvbrc_comparative_systems_bundle_adapter')
