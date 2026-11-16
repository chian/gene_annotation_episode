"""Pinned pure ComparativeSystems provider for the existing API result owner."""
from __future__ import annotations


from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_bundle_contracts import parameters_schema, validate_parameters
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_fact_contracts import requested_form_schema, validate_requested_form
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_bundle_resolution import consume_bundle
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_comparative_systems_bundle_projection import validate_projection_failure_context

ADAPTER_ID = "bvbrc_comparative_systems"
ADAPTER_VERSION = "1"

# The exact transitive package closure is audited in P's retained test receipt.
# Configuration-time file reads never occur in parsing/projection/calculation.
__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "parameters_schema",
           "validate_parameters", "validate_requested_form", "requested_form_schema", "consume_bundle",
           "validate_projection_failure_context"]
