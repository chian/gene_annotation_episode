"""Dispatch saved CodonTree sheets to the fixed pure numerical functions."""
from __future__ import annotations

from copy import deepcopy

from . import phylogeny_calculation_contracts as c
from .bvbrc_codon_tree_inputs import validate_codon_tree_sheet
from .bvbrc_phylogeny_common_grader import calculate_common_components
from .bvbrc_codon_tree_calculators import (
    native_codon_literal_statistics, codon_family_population_components,
    native_codon_worst_sequence_ratios, codon_calculation_requirements,
)


__all__ = ["calculate_codon_tree"]
_COMMON = ("alignment_requests", "original_coverage_population_ids", "tree_requests", "bootstrap_requests",
           "composition_population_ids", "taxon_requests", "comparisons")
_PARAMETERS = set(_COMMON) | {"version", "literal_statistic_population_ids", "family_population_requests",
                            "worst_sequence_population_id"}


def _merge_requirements(*registries):
    result = {}
    for registry in registries:
        for row in registry:
            key = row["requirement_id"]
            if key in result and row != result[key]:
                raise ValueError("codon_provider_requirement_conflict")
            result[key] = deepcopy(row)
    return list(result.values())


def calculate_codon_tree(sheet: dict, parameters: dict) -> dict:
    """Recalculate only selected components; retain full original parameters.

    Shared and Codon requirement vocabularies are resolved by their respective
    dispatchers. No reader, filesystem, external service, model or job is used.
    """
    saved = validate_codon_tree_sheet(sheet)
    c.shape(parameters, _PARAMETERS, "codon_provider_calculation_parameters_invalid")
    c.require(parameters["version"] == "codon_tree_components_v1", "codon_provider_calculation_version_invalid")
    c.strings(parameters["literal_statistic_population_ids"])
    c.sequence(parameters["family_population_requests"], stored=True)
    c.text(parameters["worst_sequence_population_id"], nullable=True)
    seen = set()
    for request in parameters["family_population_requests"]:
        c.shape(request, {"family_population_id", "genome_population_id"}, "codon_provider_family_request_invalid")
        c.text(request["family_population_id"])
        c.text(request["genome_population_id"])
        key = (request["family_population_id"], request["genome_population_id"])
        c.require(key not in seen, "codon_provider_duplicate_family_request")
        seen.add(key)
    common = calculate_common_components(saved, provider="codon_tree",
        parameters={key: deepcopy(parameters[key]) for key in _COMMON})
    aps = {p["population_id"]: p for p in saved["populations"]["alignments"]}
    alignments = {a["alignment_id"]: a for a in saved["documents"]["store"]["alignments"]}
    literal = []
    for pid in parameters["literal_statistic_population_ids"]:
        c.require(pid in aps, "codon_provider_literal_population_unknown")
        population = aps[pid]
        literal.append(native_codon_literal_statistics(alignments[population["alignment_id"]], population=population))
    family = [codon_family_population_components(saved, **request) for request in parameters["family_population_requests"]]
    worst = None
    if parameters["worst_sequence_population_id"] is not None:
        history = [h for h in saved["assembly"]["historical_frequencies"]
                   if h["evaluated_family_population"]["population"]["population_id"] == parameters["worst_sequence_population_id"]]
        c.require(len(history) == 1, "codon_provider_historical_population_unknown")
        worst = native_codon_worst_sequence_ratios(
            pretrim_sequence_rows=tuple(history[0]["pretrim_sequence_rows"]),
            evaluated_family_population=history[0]["evaluated_family_population"])
    codon_requirements = [codon_calculation_requirements(component) for component in literal + family + ([worst] if worst is not None else [])]
    requirements = _merge_requirements(saved["missing_requirements"], common["missing_requirements"], *codon_requirements)
    diagnostics = deepcopy(saved["qualifications"])
    for row in common["diagnostics"]:
        if row not in diagnostics:
            diagnostics.append(deepcopy(row))
    return {"schema_version": "bvbrc_codon_tree_components_v1", "parameters": deepcopy(parameters),
            **{key: common[key] for key in common if key not in {"missing_requirements", "diagnostics"}},
            "literal_statistics": literal, "family_populations": family, "worst_sequence_ratios": worst,
            "missing_requirements": requirements, "diagnostics": diagnostics}
