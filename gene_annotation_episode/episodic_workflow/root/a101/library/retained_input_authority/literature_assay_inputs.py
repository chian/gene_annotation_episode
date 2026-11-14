"""Read source-bound A105 assay operands without acquiring or judging a paper.

A caller interprets which experiment and numerical role a source passage has.
This reader verifies custody, literal numeric/unit selections and explicit
covariance ownership. Those checks are not proof of the interpretation's truth.
There is no model call, score, source fetch, state mutation or episode decision.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a101.domain import REF, obj
PRIMITIVE_ORDER = ('q', 'g', 'k', 'E', 'u', 'v')
ASSAY_LITERAL_FIELDS = ('molecule', 'organism', 'genotype', 'construct', 'preparation', 'condition', 'intended_variable', 'experimental_system', 'expression_host', 'measured_entity', 'asserted_input', 'asserted_output')
ENDPOINTS = ('oxygen_consumption', 'product_formation', 'substrate_depletion', 'ligand_binding', 'transport_flux', 'growth', 'abundance', 'other_measured_endpoint', 'unknown', 'conflicting')
ARRANGEMENTS = ('single_preparation', 'replacement', 'coexistence', 'not_applicable', 'unknown', 'conflicting')
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture')

def _witness_schema():
    """Full retained witness contract; public input projections omit quote."""
    return obj({'source_ref': REF, 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}, 'quote': {'type': 'string', 'minLength': 1}})

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}
