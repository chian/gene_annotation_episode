"""Optional exact scientific meanings for the existing saved native rate cells.

This is a return projection, not a population operation or another scoring
sheet. Saved native selection/extraction validation supplies its custody. It
never reads scientific source bytes, chooses meanings, fits or changes cells.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
NAMESPACE = 'literature_rate_source_meaning_cells'

def rate_source_meaning_cells_schema():
    """Closed additive view; null means absent from the saved selection.

    A null witness does not assert that the original publication omits the
    information. Definition quantity numbers are unit-conversion operands,
    not an automatic expansion of unrequested assay values or uncertainty.
    """
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_domains import rate_source_domain_cells_schema
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_partner_defined_units import _enriched_schema, parsed_defined_rate_unit_schema
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_experimental_contracts import RATE_UNITS
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_native_inputs import NATIVE_REASONS

    def typed_references(schema):
        for name, child in schema.get('properties', {}).items():
            if name in ('source_ref', 'artifact_ref'):
                child.update(format='reference', **{'x-reference-namespace': name.removesuffix('_ref')})
            typed_references(child)
        for child in schema.get('anyOf', ()):
            typed_references(child)
        return schema
    witness = typed_references(_enriched_schema())
    nullable_witness = {'anyOf': [witness, {'type': 'null'}]}
    unit = obj({'witness': deepcopy(witness), 'raw_unit': {'type': 'string', 'minLength': 1}, 'canonical_unit': {'type': ['string', 'null'], 'enum': [*RATE_UNITS, None]}, 'multiplier': {'type': ['number', 'null']}, 'source_defined_unit': {'anyOf': [typed_references(parsed_defined_rate_unit_schema()), {'type': 'null'}]}, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [*NATIVE_REASONS, None]}})
    arm = obj({'arm': {'enum': ['reference', 'test']}, 'endpoint': deepcopy(nullable_witness), 'normalization': deepcopy(nullable_witness), 'rate_unit': {'anyOf': [unit, {'type': 'null'}]}})
    schema = rate_source_domain_cells_schema()
    properties = schema['items']['properties']
    properties['comparison_intended_change'] = deepcopy(nullable_witness)
    properties['rate_meanings'] = {'type': 'array', 'maxItems': 2, 'items': arm}
    schema['items']['required'] = list(properties)
    schema['x-source'] = NAMESPACE
    return schema
