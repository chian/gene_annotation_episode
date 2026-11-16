"""Pinned pure GenomeComparison provider facade for the existing API owner."""
from .bvbrc_proteome_bundle_contracts import parameters_schema, validate_parameters
from .bvbrc_proteome_fact_contracts import requested_form_schema, validate_requested_form
from .bvbrc_proteome_bundle_resolution import consume_bundle

ADAPTER_ID = "bvbrc_proteome"
ADAPTER_VERSION = "1"

__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "consume_bundle", "parameters_schema",
           "validate_parameters", "requested_form_schema", "validate_requested_form"]
