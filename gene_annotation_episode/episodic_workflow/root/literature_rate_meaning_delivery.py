"""Optional exact scientific meanings for the existing saved native rate cells.

This is a return projection, not a population operation or another scoring
sheet. Saved native selection/extraction validation supplies its custody. It
never reads scientific source bytes, chooses meanings, fits or changes cells.
"""
from copy import deepcopy

from gene_annotation_episode.domain import ContractError, obj
from .literature_rate_storage import (
    COMPONENTS, PROVIDER, LiteratureRateSourceDomainProjection,
)


from gene_annotation_episode.episodic_workflow.root.library.literature_rate_meaning_return_schema import NAMESPACE, MEANING_FIELDS
# These are the existing native domain trace's operand dependencies. They are
# roles, not new measurement/evidence categories or independence assertions.
COMPONENT_ROLES = {
    name: (("reference",) if name in ("reference_rate", "reference_mean_se") else
           ("test",) if name in ("test_rate", "test_mean_se") else
           ("reference", "test"))
    for name in COMPONENTS
}


from gene_annotation_episode.episodic_workflow.root.library.literature_rate_meaning_return_schema import rate_source_meaning_cells_schema
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
