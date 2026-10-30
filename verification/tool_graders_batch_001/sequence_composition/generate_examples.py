"""Write deliberately synthetic filled examples; the grader itself has no I/O."""
from pathlib import Path
import json

from gene_annotation_episode.sequence_composition_grader import (
    calculate_sequence_composition_scores,
    grade_sequence_composition,
)


EXAMPLES = [
    ("dna_phred33_hand_checked", {"sequence": "acgN", "molecule": "dna", "quality": "!+5?", "quality_encoding": "phred33"}),
    ("rna_no_quality", {"sequence": "ggcuuN", "molecule": "rna"}),
    ("protein_ambiguity", {"sequence": "ABXZWJOu*", "molecule": "protein"}),
    ("unspecified_molecule", {"sequence": "ACGT", "molecule": "unspecified"}),
    ("solexa_odds", {"sequence": "ACG", "molecule": "dna", "quality": ";@J", "quality_encoding": "solexa64",
                     "quality_thresholds": (0, 2, 3, 10, 11)}),
    ("quality_length_mismatch", {"sequence": "ACGT", "molecule": "dna", "quality": "II?", "quality_encoding": "phred33"}),
    ("valid_empty_population", {"sequence": "", "molecule": "dna", "quality": "", "quality_encoding": "phred33"}),
]


def main():
    destination = Path(__file__).parent
    examples = [{"name": name, "inputs": inputs, **grade_sequence_composition(**inputs)}
                for name, inputs in EXAMPLES]
    path = destination / "filled_examples.json"
    path.write_text(json.dumps({"kind": "synthetic_numerical_examples", "examples": examples},
                               indent=2, allow_nan=False) + "\n")
    saved_sheet = json.loads(path.read_text())["examples"][0]["sheet"]
    recalculated = calculate_sequence_composition_scores(saved_sheet, quality_thresholds=(10, 21, 31))
    (destination / "recalculated_thresholds.json").write_text(json.dumps(recalculated, indent=2,
                                                                        allow_nan=False) + "\n")
    for row in examples:
        scores = row["scores"]
        print(json.dumps({"example": row["name"], **{key: scores[key] for key in (
            "length", "ambiguous_symbol_count", "ambiguity_fraction", "gc_count", "gc_denominator", "gc_fraction",
            "quality_observation_count", "mean_phred", "expected_error_count", "quality_thresholds")}}, allow_nan=False))
    print(json.dumps({"recalculated_from_saved_sheet": recalculated["quality_thresholds"]}))


if __name__ == "__main__":
    main()
