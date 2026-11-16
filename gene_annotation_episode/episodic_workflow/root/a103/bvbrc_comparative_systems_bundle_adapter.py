"""Pinned pure ComparativeSystems provider for the existing API result owner."""
from __future__ import annotations

from .bvbrc_comparative_systems_bundle_contracts import parameters_schema, validate_parameters
from .bvbrc_comparative_systems_fact_contracts import requested_form_schema, validate_requested_form
from .bvbrc_comparative_systems_bundle_resolution import consume_bundle
from .bvbrc_comparative_systems_bundle_projection import validate_projection_failure_context

ADAPTER_ID = "bvbrc_comparative_systems"
ADAPTER_VERSION = "1"

__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "parameters_schema",
           "validate_parameters", "validate_requested_form", "requested_form_schema", "consume_bundle",
           "validate_projection_failure_context"]
