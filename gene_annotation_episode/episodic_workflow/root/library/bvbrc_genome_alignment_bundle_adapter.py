"""Pinned pure GenomeAlignment facade for the existing AppService owner."""

from gene_annotation_episode.episodic_workflow.root.library.bvbrc_genome_alignment_bundle_contracts import (
    validate_parameters, parameters_schema, requested_form_schema, validate_requested_form,
)
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_genome_alignment_bundle_resolution import consume_bundle

ADAPTER_ID = 'bvbrc_genome_alignment'
ADAPTER_VERSION = '1'

# This exact transitive source/resource closure is audited by the facade tests.
# It includes actual C receipt-decoding imports; consumers are not dependencies.
__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'validate_parameters', 'parameters_schema',
    'requested_form_schema', 'validate_requested_form', 'consume_bundle']
