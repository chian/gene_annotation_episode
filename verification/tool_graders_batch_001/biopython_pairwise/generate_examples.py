"""Regenerate tiny, direct native examples; no database, service, or episode run.

From the repository root:
  .venv/bin/python -m verification.tool_graders_batch_001.biopython_pairwise.generate_examples
"""
from importlib.metadata import version
import json
from pathlib import Path

from gene_annotation_episode.biopython_pairwise_grader import grade_biopython_pairwise
from gene_annotation_episode.sequence_ops import align_pair


CASES = [
    ("dna_global_gap", {"query": "ACGTT", "reference": "ACTT", "molecule": "dna", "mode": "global", "gap_open": -2}),
    ("dna_local_flanks", {"query": "GGACGTCC", "reference": "TTACGTAA", "molecule": "dna", "mode": "local"}),
    ("rna_global_substitution", {"query": "AUGC", "reference": "AUAC", "molecule": "rna", "mode": "global"}),
    ("rna_local_flanks", {"query": "GGAUGCCC", "reference": "AAAUGCUU", "molecule": "rna", "mode": "local"}),
    ("protein_global_gap", {"query": "ACDE", "reference": "ACE", "molecule": "protein", "mode": "global", "gap_open": -2}),
    ("protein_local_flanks", {"query": "WWACDEWW", "reference": "GGACDEGG", "molecule": "protein", "mode": "local"}),
    ("dna_no_local_alignment", {"query": "AAA", "reference": "CCC", "molecule": "dna", "mode": "local"}),
    ("dna_zero_paired_global_alignment", {"query": "A", "reference": "C", "molecule": "dna", "mode": "global",
                                          "gap_open": -.1, "gap_extend": -.1}),
]


def main():
    directory = Path(__file__).resolve().parent
    native_examples, filled_examples = [], []
    for name, arguments in CASES:
        native = align_pair(**arguments)
        grading = grade_biopython_pairwise(native, molecule=arguments["molecule"])
        native_examples.append({"name": name, "arguments": arguments, "native": native})
        filled_examples.append({"name": name, "grading": grading})
    for filename, value in (("native_examples.json", native_examples), ("filled_examples.json", filled_examples)):
        (directory / filename).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    provenance = {
        "native_operation": "gene_annotation_episode.sequence_ops.align_pair",
        "biopython_version": version("biopython"),
        "execution": "actual_local_native_alignment_on_explicit_tiny_synthetic_sequences",
        "native_examples": len(native_examples),
        "episode_publication_verified_by_this_script": False,
        "resource_child_verified_by_this_script": False,
        "external_services_or_databases_used": False,
        "command": ".venv/bin/python -m verification.tool_graders_batch_001.biopython_pairwise.generate_examples",
    }
    (directory / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance))


if __name__ == "__main__":
    main()
