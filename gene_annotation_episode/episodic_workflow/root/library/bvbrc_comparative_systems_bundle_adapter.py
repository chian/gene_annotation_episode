"""Pinned pure ComparativeSystems provider for the existing API result owner."""
from __future__ import annotations

import hashlib
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_bundle_contracts import parameters_schema, validate_parameters
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_fact_contracts import requested_form_schema, validate_requested_form
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_bundle_resolution import consume_bundle
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_bundle_projection import validate_projection_failure_context

ADAPTER_ID = "bvbrc_comparative_systems"
ADAPTER_VERSION = "1"

# The exact transitive package closure is audited in P's retained test receipt.
# Configuration-time file reads never occur in parsing/projection/calculation.
_DEPENDENCIES = (
    '__init__.py',
    'acquisition.py',
    'addgene_access.py',
    'addgene_sequence_native.py',
    'episodic_workflow/root/library/alignment_correspondence.py',
    'alphafold_acquisition.py',
    'episodic_workflow/root/library/biopython_pairwise_grader.py',
    'boundary_validation.py',
    'bvbrc_appservice_contracts.py',
    'bvbrc_appservice_schemas.json',
    'episodic_workflow/root/library/bvbrc_comparative_systems_bundle_contracts.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_bundle_projection.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_calculation_contracts.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_data_contracts.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_fact_contracts.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_handoff_contracts.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_handoff_schemas.json',
    'episodic_workflow/root/library/bvbrc_comparative_systems_sheet_contracts.py',
    'episodic_workflow/root/library/bvbrc_data_fields.py',
    'episodic_workflow/root/library/bvbrc_data_query.py',
    'episodic_workflow/root/library/bvbrc_data_readers.py',
    'episodic_workflow/root/library/bvbrc_data_schema.py',
    'episodic_workflow/root/library/chemistry.py',
    'credentials.py',
    'data_acquisition_receipts.py',
    'domain.py',
    'emdb_acquisition.py',
    'ensembl_acquisition.py',
    'episodic_workflow/__init__.py',
    'episodic_workflow/root/__init__.py',
    'episodic_workflow/root/library/__init__.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_bundle_adapter.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_bundle_resolution.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_calculators.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_data_inputs.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_native.py',
    'episodic_workflow/root/library/bvbrc_comparative_systems_sheet.py',
    'literature_assets.py',
    'molecular_provider_acquisition.py',
    'episodic_workflow/root/library/protein_structure_contracts.py',
    'public_configuration.py',
    'rcsb_acquisition.py',
    'execution_contracts.py',
    'episodic_workflow/root/communication.py',
    'episodic_workflow/root/library/rfam_discovery.py',
    'ucsc_acquisition.py',
    'uniprot_native.py',
    'uniprot_native_contracts.py',
)


def implementation_sha256():
    result = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        raw = (Path(__file__).resolve().parents[3] / name).read_bytes()
        result.update(name.encode("utf-8") + b"\0" + str(len(raw)).encode("ascii") + b"\0" + raw)
    return result.hexdigest()


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "implementation_sha256", "parameters_schema",
           "validate_parameters", "validate_requested_form", "requested_form_schema", "consume_bundle",
           "validate_projection_failure_context"]
