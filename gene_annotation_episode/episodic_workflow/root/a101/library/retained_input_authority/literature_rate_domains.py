"""Exact reported-operand enclosures, without sampling or independence claims.

Marginal source limits define a Cartesian enclosure, not co-attainability or a
confidence interval. Finite JSON numbers are outward projections of retained
rationals. This module neither reads scientific sources nor fits a model.
"""
NAMESPACE = 'literature_rate_source_domain_cells'

def rate_source_domain_cells_schema():
    """A separate closed view; existing native rows remain unchanged."""
    from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_storage import rate_source_cells_schema, UNAVAILABLE_REASONS
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_rate_native_inputs import NATIVE_REASONS
    schema = rate_source_cells_schema()
    schema['x-source'] = NAMESPACE
    properties = schema['items']['properties']
    properties['reported_domain'] = obj({'kind': {'type': 'string', 'enum': ['point', 'lower_bounded', 'upper_bounded', 'finite_interval', 'unbounded', 'undefined', 'unavailable', 'numerical_range']}, 'lower': {'type': ['number', 'null']}, 'upper': {'type': ['number', 'null']}, 'lower_inclusive': {'type': 'boolean'}, 'upper_inclusive': {'type': 'boolean'}, 'projection': {'type': 'string', 'enum': ['exact', 'outward', 'none']}, 'basis': {'type': 'string', 'enum': ['reported_point', 'reported_censoring', 'reported_operand_algebra', 'stored_numerical_point', 'legacy_stored_cell']}, 'conditioning': {'type': 'string', 'enum': ['reported_endpoint_normalization_unit_relations', 'stored_source_cell']}, 'failure': {'type': ['string', 'null'], 'enum': [*UNAVAILABLE_REASONS, *NATIVE_REASONS, None]}})
    schema['items']['required'] = list(properties)
    return schema
