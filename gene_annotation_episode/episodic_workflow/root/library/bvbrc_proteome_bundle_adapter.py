"""Pinned pure GenomeComparison provider facade for the existing API owner."""

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_bundle_contracts import parameters_schema, validate_parameters
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_fact_contracts import requested_form_schema, validate_requested_form
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_proteome_bundle_resolution import consume_bundle

ADAPTER_ID = "bvbrc_proteome"
ADAPTER_VERSION = "1"

# Audited against the actual transitive package imports and schema assets.
# Host consumers, future full-report readers and tests are not dependencies.
__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "consume_bundle", "parameters_schema",
           "validate_parameters", "requested_form_schema", "validate_requested_form"]
