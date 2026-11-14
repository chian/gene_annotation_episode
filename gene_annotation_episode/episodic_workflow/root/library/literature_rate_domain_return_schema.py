NAMESPACE = "literature_rate_source_domain_cells"

def rate_source_domain_cells_schema():
    """A separate closed view; existing native rows remain unchanged."""
    from gene_annotation_episode.domain import obj
    from .literature_native_rate_return_schema import rate_source_cells_schema
    from .literature_rate_return_schema import UNAVAILABLE_REASONS
    from .literature_native_rate_return_schema import NATIVE_REASONS
    schema = rate_source_cells_schema()
    schema["x-source"] = NAMESPACE
    properties = schema["items"]["properties"]
    properties["reported_domain"] = obj({
        "kind": {"type": "string", "enum": ["point", "lower_bounded", "upper_bounded", "finite_interval", "unbounded", "undefined", "unavailable", "numerical_range"]},
        "lower": {"type": ["number", "null"]}, "upper": {"type": ["number", "null"]},
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"},
        "projection": {"type": "string", "enum": ["exact", "outward", "none"]},
        "basis": {"type": "string", "enum": ["reported_point", "reported_censoring", "reported_operand_algebra", "stored_numerical_point", "legacy_stored_cell"]},
        "conditioning": {"type": "string", "enum": ["reported_endpoint_normalization_unit_relations", "stored_source_cell"]},
        "failure": {"type": ["string", "null"], "enum": [*UNAVAILABLE_REASONS, *NATIVE_REASONS, None]}})
    schema["items"]["required"] = list(properties)
    return schema


# These pure view helpers deliberately preserve the original native masking and
# scientific label renderer. Domain rows never fall through a generic record
# expansion merely because their closed contract has an additional field.

