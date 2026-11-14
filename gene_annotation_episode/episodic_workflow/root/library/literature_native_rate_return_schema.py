from .literature_rate_return_schema import rate_cells_schema, UNAVAILABLE_REASONS

ROLES = ("reference", "test")

NATIVE_BINDINGS = tuple(role + "_" + field + "_ref" for role in ROLES
                        for field in ("subject", "construct", "preparation"))
NATIVE_REASONS = ("source_rate_unit_unreported", "unsupported_source_rate_unit",
    "source_defined_unit_definition_required", "source_spread_unit_unavailable",
    "source_endpoint_relationship_unknown", "source_endpoint_relationship_different",
    "source_normalization_relationship_unknown", "source_normalization_relationship_different",
    "incompatible_rate_dimensions", "reused_source_observation")

def rate_source_cells_schema():
    """Closed native return contract, distinct from the unchanged v1 projection."""
    schema = rate_cells_schema()
    properties = schema["items"]["properties"]
    properties["unavailable_reason"]["enum"] = [*UNAVAILABLE_REASONS, *NATIVE_REASONS, None]
    for field in NATIVE_BINDINGS:
        properties[field] = {"type": ["string", "null"], "format": "reference",
                             "x-reference-namespace": "reference"}
    properties["approximate"] = {"type": "boolean"}
    properties["threshold"] = {"type": ["number", "null"]}
    properties["bound"] = {"type": "string", "enum": ["none", "lt", "le", "gt", "ge"]}
    schema["items"]["required"] = list(properties)
    schema["x-source"] = "literature_rate_source_cells"
    return schema



