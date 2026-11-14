"""Saved GeneTree sheet to explicit numerical components, without I/O."""
from __future__ import annotations

from copy import deepcopy

from .bvbrc_gene_tree_inputs import validate_gene_tree_sheet
from .bvbrc_phylogeny_common_grader import calculate_common_components


COMMON_PARAMETER_FIELDS = (
    "alignment_requests", "original_coverage_population_ids", "tree_requests",
    "bootstrap_requests", "composition_population_ids", "taxon_requests", "comparisons",
)


def calculate_gene_tree(sheet: dict, parameters: dict) -> dict:
    """Recalculate the requested populations; no universal score is introduced.

    Native branch/support values remain saved separately from normalized or
    derived quantities. All arithmetic belongs to the shared fixed calculators.
    The complete explicit parameter object is retained with this calculation.
    """
    validated = validate_gene_tree_sheet(sheet)
    if (type(parameters) is not dict or set(parameters) != {"version", *COMMON_PARAMETER_FIELDS}
            or parameters["version"] != "gene_tree_components_v1"):
        raise ValueError("gene_tree_calculation_parameters_invalid")
    copied = deepcopy(parameters)
    common = calculate_common_components(validated, provider="gene_tree",
        parameters={name: copied[name] for name in COMMON_PARAMETER_FIELDS})
    return {"schema_version": "bvbrc_gene_tree_components_v1",
            "parameters": copied, **common}


__all__ = ["calculate_gene_tree"]
