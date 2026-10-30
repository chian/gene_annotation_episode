"""Filled synthetic population examples, executed only through run_checks_001."""
from copy import deepcopy
import json
from pathlib import Path

from test_blast_sequence_population_association import sequence_inputs
from gene_annotation_episode.blast_sequence_database import (
    populate_blast_sequence_database_sheet, calculate_blast_sequence_database_components)
from gene_annotation_episode.blast_database_grader import calculate_database_probabilities

examples = []
for program, kind in [(p, "sequence") for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx", "psiblast", "deltablast")] + [
        ("tblastn", "pssm"), ("psiblast", "pssm"), ("psiblast", "msa")]:
    supplied = sequence_inputs(program, kind)
    outer = populate_blast_sequence_database_sheet(**supplied)
    components = calculate_blast_sequence_database_components(outer)
    saved = json.loads(json.dumps(components["components"]["database_sheet"]))
    frozen = deepcopy(saved)
    calculations = []
    for temperature in (1, 2):
        probabilities = calculate_database_probabilities(saved, model={"temperature_bits": temperature})
        counts = {r["function"]: r["database_sequence_count"] for r in saved["database_representation"]["function_representation"]}
        products = {name: mass * probabilities["parameters"]["function_priors"][name] for name, mass in probabilities["function_masses"].items()}
        calculations.append(dict(temperature_bits=temperature, result=probabilities,
            prior_weighted_function_masses=products, representation_adjustment_rates={name: mass / counts[name] for name, mass in products.items()}))
    assert saved == frozen
    examples.append(dict(evidence="deliberately_synthetic_native_format_and_supplied_assertion_not_live_execution",
        program=program, query_kind=kind, outer_sheet=outer, components=components,
        saved_inner_sheet=saved, calculations=calculations))
output = Path.cwd() / "numerical_examples.json"
output.write_text(json.dumps(dict(schema="u06_synthetic_numerical_examples_v1", examples=examples), indent=2, allow_nan=False) + "\n")
for row in examples:
    print(json.dumps(dict(program=row["program"], query_kind=row["query_kind"],
        original_native_database=row["saved_inner_sheet"]["normalized_result"]["search"]["database"],
        population_relation=row["saved_inner_sheet"]["database_population_relation"]["status"],
        census_fractions={r["function"]: r["database_fraction"] for r in row["saved_inner_sheet"]["database_representation"]["function_representation"]},
        calculations=[{k: c[k] for k in ("temperature_bits", "prior_weighted_function_masses", "representation_adjustment_rates")} | dict(
            masses=c["result"]["function_masses"], unadjusted=c["result"]["unadjusted_probabilities"],
            adjusted=c["result"]["representation_adjusted_probabilities"]) for c in row["calculations"]])))
print(json.dumps(dict(output=str(output), example_count=len(examples))))
