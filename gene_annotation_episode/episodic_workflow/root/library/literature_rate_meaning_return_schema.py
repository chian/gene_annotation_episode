from copy import deepcopy
from gene_annotation_episode.domain import obj

NAMESPACE = "literature_rate_source_meaning_cells"
MEANING_FIELDS = ("comparison_intended_change", "rate_meanings")

def rate_source_meaning_cells_schema():
    """Closed additive view; null means absent from the saved selection.

    A null witness does not assert that the original publication omits the
    information. Definition quantity numbers are unit-conversion operands,
    not an automatic expansion of unrequested assay values or uncertainty.
    """
    from .literature_rate_domain_return_schema import rate_source_domain_cells_schema
    from .literature_rate_unit_witness_schema import _enriched_schema, parsed_defined_rate_unit_schema
    from .literature_rate_return_schema import RATE_UNITS
    from .literature_native_rate_return_schema import NATIVE_REASONS
    def typed_references(schema):
        # Operation-selector REF patterns alone do not request the ordinary
        # return boundary's contextual reference resolver. Retain the pattern
        # and declare the actual semantic namespaces in every witness branch.
        for name, child in schema.get("properties", {}).items():
            if name in ("source_ref", "artifact_ref"):
                child.update(format="reference", **{"x-reference-namespace": name.removesuffix("_ref")})
            typed_references(child)
        for child in schema.get("anyOf", ()):
            typed_references(child)
        return schema
    witness = typed_references(_enriched_schema())
    nullable_witness = {"anyOf": [witness, {"type": "null"}]}
    unit = obj({"witness": deepcopy(witness),
        "raw_unit": {"type": "string", "minLength": 1},
        "canonical_unit": {"type": ["string", "null"], "enum": [*RATE_UNITS, None]},
        "multiplier": {"type": ["number", "null"]},
        "source_defined_unit": {"anyOf": [typed_references(parsed_defined_rate_unit_schema()), {"type": "null"}]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*NATIVE_REASONS, None]}})
    arm = obj({"arm": {"enum": ["reference", "test"]},
        "endpoint": deepcopy(nullable_witness), "normalization": deepcopy(nullable_witness),
        "rate_unit": {"anyOf": [unit, {"type": "null"}]}})
    schema = rate_source_domain_cells_schema()
    properties = schema["items"]["properties"]
    properties["comparison_intended_change"] = deepcopy(nullable_witness)
    properties["rate_meanings"] = {"type": "array", "maxItems": 2, "items": arm}
    schema["items"]["required"] = list(properties)
    schema["x-source"] = NAMESPACE
    return schema



