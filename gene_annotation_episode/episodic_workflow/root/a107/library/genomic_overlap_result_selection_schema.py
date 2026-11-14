"""A107 original genomic overlap result selection schema; selected retained metadata/operand declarations.

Original source qualifications and identity checks remain intact; no acquisition or dispatch is added.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.historical_genomic_overlap_contracts import genomic_overlap_schema

def genomic_overlap_result_selector_schema() -> dict:
    """Return the unchanged G1 selector with its own embedded reference scope."""
    schema = genomic_overlap_schema('Selector')
    definitions = schema.pop('$defs')
    wanted = set()

    def visit(value):
        if isinstance(value, dict):
            reference = value.get('$ref')
            if reference is not None:
                if not reference.startswith('#/$defs/'):
                    raise ValueError('genomic_overlap_selector_external_schema_reference')
                name = reference.removeprefix('#/$defs/')
                if name not in wanted:
                    wanted.add(name)
                    visit(definitions[name])
            for key, child in value.items():
                if key != '$ref':
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(schema)
    schema['$defs'] = {name: definitions[name] for name in sorted(wanted)}
    schema['$id'] = 'urn:gene-annotation:genomic-overlap:result-selector:' + digest(schema)
    return schema
