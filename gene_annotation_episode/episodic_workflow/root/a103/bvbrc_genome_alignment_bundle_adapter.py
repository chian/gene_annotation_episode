"""Pinned pure GenomeAlignment facade for the existing AppService owner."""
from .bvbrc_genome_alignment_bundle_contracts import (
    validate_parameters, parameters_schema, requested_form_schema, validate_requested_form,
)
from .bvbrc_genome_alignment_bundle_resolution import consume_bundle

ADAPTER_ID = 'bvbrc_genome_alignment'
ADAPTER_VERSION = '1'

__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'validate_parameters', 'parameters_schema',
    'requested_form_schema', 'validate_requested_form', 'consume_bundle']
