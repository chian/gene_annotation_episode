"""Bounded sequence measurements; scientific interpretation belongs to Episodes.

These operations never choose a follow-up experiment, change an input, select
an annotation or decide whether an investigation should continue.
"""

from __future__ import annotations

from collections import Counter
from importlib.metadata import version
from typing import Any

from Bio.Data import CodonTable
from Bio.Seq import Seq


def inspect_sequence(sequence: str) -> dict[str, Any]:
    sequence = sequence.upper()
    counts = Counter(sequence)
    dna = set(sequence) <= set("ACGTRYSWKMBDHVN")
    rna = set(sequence) <= set("ACGURYSWKMBDHVN")
    protein = set(sequence) <= set("ACDEFGHIKLMNPQRSTVWYBXZJUO*")
    gc_denominator = sum(counts[b] for b in "ACGTU")
    return {
        "length": len(sequence),
        "symbol_counts": dict(sorted(counts.items())),
        "compatible_alphabets": [name for name, yes in
                                 (("dna", dna), ("rna", rna), ("protein", protein)) if yes],
        "gc_fraction": ((counts["G"] + counts["C"]) / gc_denominator
                        if gc_denominator and (dna or rna) else None),
        "gc_denominator": gc_denominator if dna or rna else 0,
        "literal_stop_positions": [i for i, symbol in enumerate(sequence) if symbol == "*"],
        "coordinate_system": "zero_based_half_open",
        "interpretation": "alphabet_compatibility_is_not_biological_identity",
    }


def translation_codes() -> list[dict[str, Any]]:
    return [{"code": code, "names": list(table.names),
             "stop_codons": list(table.stop_codons), "start_codons": list(table.start_codons)}
            for code, table in sorted(CodonTable.unambiguous_dna_by_id.items())]


def translate(sequence: str, *, code: int, strand: str = "+", frame: int = 0,
              start: int = 0, end: int | None = None, cds: bool = False) -> dict[str, Any]:
    end = len(sequence) if end is None else end
    if type(code) is not int or code not in CodonTable.unambiguous_dna_by_id:
        raise ValueError("unknown_translation_code")
    if strand not in {"+", "-"} or type(frame) is not int or frame not in {0, 1, 2}:
        raise ValueError("invalid_translation_orientation")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(sequence):
        raise ValueError("invalid_sequence_interval")
    if not set(sequence.upper()) <= set("ACGTURYSWKMBDHVN"):
        raise ValueError("translation_requires_nucleotide_sequence")
    region = Seq(sequence[start:end].upper().replace("U", "T"))
    if strand == "-":
        region = region.reverse_complement()
    available = len(region) - frame
    used = available - available % 3
    if used <= 0:
        raise ValueError("no_complete_codon_in_interval")
    if cds and (frame != 0 or available % 3):
        raise ValueError("cds_translation_requires_complete_codon_interval")
    product = str(region[frame:frame + used].translate(table=code, cds=cds))
    span = [start + frame, start + frame + used] if strand == "+" else [end-frame-used, end-frame]
    table = CodonTable.unambiguous_dna_by_id[code]
    library_version = version("biopython")
    # Retain the execution's actual code table. Saved-result calculations must
    # not silently adopt a later installed table, including its dual-coding
    # stops or alternative starts. Native null table aliases stay null.
    genetic_code_snapshot = {"code": code, "names": list(table.names),
        "start_codons": list(table.start_codons), "stop_codons": list(table.stop_codons),
        "forward_table": dict(table.forward_table), "biopython_version": library_version}
    return {"sequence": product, "code": code, "strand": strand, "frame": frame,
            "input_interval": [start, end], "translated_interval": span,
            "trailing_untranslated_bases": available % 3, "cds": cds,
            "internal_stop_positions": [i for i, symbol in enumerate(product[:-1]) if symbol == "*"],
            "terminal_stop": product.endswith("*"), "biopython_version": library_version,
            "genetic_code_snapshot": genetic_code_snapshot}


