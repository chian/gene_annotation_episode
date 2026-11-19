"""Explicit sequence extraction under a caller-selected processing model.

The choice of model is an assumption of this operation, not a classification
of the original material. Input strings and caller declarations stay immutable.
ToolRegistry publishes selected views with source provenance and exact mappings.
"""
from __future__ import annotations

from Bio.Seq import Seq


VERSION = "explicit_sequence_view_v1"
NUCLEOTIDE_SYMBOLS = frozenset("ACGTURYSWKMBDHVN")


def view_sequence(sequence: str, *, molecule: str,
                  segments: list[dict] | None = None,
                  orientation: str = "as_is") -> dict:
    if molecule not in {"dna", "rna", "protein"}:
        raise ValueError("explicit_sequence_model_required")
    if orientation not in {"as_is", "reverse_complement"}:
        raise ValueError("unsupported_sequence_orientation")
    if not isinstance(sequence, str) or not sequence:
        raise ValueError("nonempty_sequence_required")
    if segments is None:
        segments = [{"start": 0, "end": len(sequence)}]
    if (not isinstance(segments, list) or not segments or any(
            not isinstance(row, dict) or set(row) != {"start", "end"}
            or type(row["start"]) is not int or type(row["end"]) is not int
            or not 0 <= row["start"] < row["end"] <= len(sequence) for row in segments)):
        raise ValueError("view_interval_outside_subject")
    selected = "".join(sequence[row["start"]:row["end"]] for row in segments)
    if orientation == "reverse_complement":
        if molecule == "protein":
            raise ValueError("protein_reverse_complement_undefined")
        if not set(selected.upper()) <= NUCLEOTIDE_SYMBOLS:
            raise ValueError("reverse_complement_requires_nucleotide_symbols")
        selected = str(Seq(selected).reverse_complement_rna() if molecule == "rna"
                       else Seq(selected).reverse_complement())
    return {"sequence": selected, "molecule_model": molecule,
        "molecule_assignment": "not_performed", "orientation": orientation,
        "input_segments": [dict(row) for row in segments], "input_length": len(sequence),
        "output_length": len(selected), "coordinate_system": "zero_based_half_open",
        "operation_version": VERSION,
        "limitations": ["selected_processing_model_does_not_establish_input_identity"]}
