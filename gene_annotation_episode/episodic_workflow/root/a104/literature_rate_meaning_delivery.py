"""Optional exact scientific meanings for the existing saved native rate cells.

This is a return projection, not a population operation or another scoring
sheet. Saved native selection/extraction validation supplies its custody. It
never reads scientific source bytes, chooses meanings, fits or changes cells.
"""
from copy import deepcopy

from .domain import ContractError, obj
from .literature_rate_storage import (
    COMPONENTS, PROVIDER, LiteratureRateSourceDomainProjection,
)


NAMESPACE = "literature_rate_source_meaning_cells"
MEANING_FIELDS = ("comparison_intended_change", "rate_meanings")
# These are the existing native domain trace's operand dependencies. They are
# roles, not new measurement/evidence categories or independence assertions.
COMPONENT_ROLES = {
    name: (("reference",) if name in ("reference_rate", "reference_mean_se") else
           ("test",) if name in ("test_rate", "test_mean_se") else
           ("reference", "test"))
    for name in COMPONENTS
}


def rate_source_meaning_cells_schema():
    """Closed additive view; null means absent from the saved selection.

    A null witness does not assert that the original publication omits the
    information. Definition quantity numbers are unit-conversion operands,
    not an automatic expansion of unrequested assay values or uncertainty.
    """
    from .literature_rate_domains import rate_source_domain_cells_schema
    from .literature_partner_defined_units import _enriched_schema, parsed_defined_rate_unit_schema
    from .literature_experimental_contracts import RATE_UNITS
    from .literature_rate_native_inputs import NATIVE_REASONS
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


class LiteratureRateSourceMeaningProjection(LiteratureRateSourceDomainProjection):
    """Same saved numerical rows, with independent exact-subset return custody."""

    received_table = "literature_rate_source_meaning_received"

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        rows = super().project_cells(sheet_refs, permitted_record_refs=permitted_record_refs,
            components=components)
        extractions = {}
        for row in rows:
            reference = row["sheet_ref"]
            if reference not in extractions:
                # read() validates the original selection and canonical saved
                # associations; it does not reacquire the original source text.
                extractions[reference] = self.read(reference)["sheet"]["extraction"]
            extraction = extractions[reference]
            row["comparison_intended_change"] = deepcopy(
                extraction["native_context"]["comparison"]["intended_change"])
            operands = {operand["arm"]: operand for operand in extraction["rows"]}
            row["rate_meanings"] = []
            for role in COMPONENT_ROLES[row["component"]]:
                source = operands.get(role, {}).get("source", {})
                meanings = source.get("meanings", {})
                row["rate_meanings"].append({"arm": role,
                    "endpoint": deepcopy(meanings.get("endpoint")),
                    "normalization": deepcopy(meanings.get("normalization")),
                    "rate_unit": deepcopy(source.get("unit"))})
        return rows


def source_meaning_projection(repository):
    """Construct a read-only adapter lazily; discovery installs no tables."""
    if repository.provider != PROVIDER or repository.operations_table != "literature_rate_operations":
        raise ContractError("native_rate_return_view_requires_rate_repository")
    return LiteratureRateSourceMeaningProjection(repository.store, repository.run_id)


__all__ = ["NAMESPACE", "COMPONENT_ROLES", "MEANING_FIELDS",
    "rate_source_meaning_cells_schema", "LiteratureRateSourceMeaningProjection", "source_meaning_projection"]
