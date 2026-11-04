"""Bounded sequence measurements; scientific interpretation belongs to Episodes.

These operations never choose a follow-up experiment, change an input, select
an annotation or decide whether an investigation should continue.
"""

from __future__ import annotations

from collections import Counter
from importlib.metadata import version
from typing import Any

from Bio import Align
from Bio.Align import substitution_matrices
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
    return {"sequence": product, "code": code, "strand": strand, "frame": frame,
            "input_interval": [start, end], "translated_interval": span,
            "trailing_untranslated_bases": available % 3, "cds": cds,
            "internal_stop_positions": [i for i, symbol in enumerate(product[:-1]) if symbol == "*"],
            "terminal_stop": product.endswith("*"), "biopython_version": version("biopython")}


def predict_genes(sequence: str, *, code: int, mode: str = "meta") -> dict[str, Any]:
    import pyrodigal
    if code not in CodonTable.unambiguous_dna_by_id:
        raise ValueError("unknown_translation_code")
    if mode not in {"meta", "single"}:
        raise ValueError("unknown_gene_calling_mode")
    if not set(sequence.upper()) <= set("ACGTRYSWKMBDHVN"):
        raise ValueError("gene_calling_requires_dna")
    raw = sequence.upper().encode("ascii")
    if mode == "meta":
        bins = [item for item in pyrodigal.METAGENOMIC_BINS if item.training_info.translation_table == code]
        if not bins:
            raise ValueError("no_native_metagenomic_model_for_translation_code")
        finder = pyrodigal.GeneFinder(meta=True, metagenomic_bins=pyrodigal.MetagenomicBins(bins))
    else:
        finder = pyrodigal.GeneFinder(meta=False)
        finder.train(raw, translation_table=code)
    genes = finder.find_genes(raw)
    candidates = [{"start": gene.begin - 1, "end": gene.end,
                   "strand": "+" if gene.strand == 1 else "-", "code": code,
                   "partial_begin": bool(gene.partial_begin), "partial_end": bool(gene.partial_end),
                   "protein_sequence": gene.translate(translation_table=code),
                   "native_confidence": gene.confidence(), "native_score": gene.score}
                  for gene in genes]
    return {"candidates": candidates, "mode": mode, "translation_code": code,
            "pyrodigal_version": version("pyrodigal"),
            "coordinate_system": "zero_based_half_open",
            "limitations": ["native_confidence_is_not_calibrated_annotation_accuracy",
                            "circular_origin_spanning_models_not_searched",
                            "programmed_recoding_not_resolved_by_this_operation"]}


def align_pair(query: str, reference: str, *, molecule: str, mode: str = "local",
               gap_open: float = -10.0, gap_extend: float = -0.5) -> dict[str, Any]:
    if molecule not in {"protein", "dna", "rna"} or mode not in {"local", "global"}:
        raise ValueError("invalid_alignment_model")
    query, reference = query.upper(), reference.upper()
    if not query or not reference:
        raise ValueError("empty_alignment_sequence")
    aligner = Align.PairwiseAligner(mode=mode, open_gap_score=gap_open, extend_gap_score=gap_extend)
    if molecule == "protein":
        aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
        matrix = "BLOSUM62"
    else:
        query, reference = query.replace("U", "T"), reference.replace("U", "T")
        aligner.match_score, aligner.mismatch_score = 2, -1
        matrix = "match_2_mismatch_minus_1"
    results = iter(aligner.align(query, reference))
    result = next(results, None)
    if result is None:
        return {"aligned": False, "query_length": len(query), "reference_length": len(reference),
                "mode": mode, "matrix": matrix, "biopython_version": version("biopython")}
    query_indices, reference_indices = result.indices
    paired = [(int(i), int(j)) for i, j in zip(query_indices, reference_indices) if i >= 0 and j >= 0]
    identical = sum(query[i] == reference[j] for i, j in paired)
    q_positions = {int(i) for i in query_indices if i >= 0}
    r_positions = {int(j) for j in reference_indices if j >= 0}
    return {
        "aligned": True, "native_score": float(result.score),
        "query_length": len(query), "reference_length": len(reference),
        "paired_positions": len(paired), "identical_positions": identical,
        "identity_fraction": identical / len(paired) if paired else 0.0,
        "query_coverage": len(q_positions) / len(query),
        "reference_coverage": len(r_positions) / len(reference),
        "query_interval": [min(q_positions), max(q_positions) + 1] if q_positions else None,
        "reference_interval": [min(r_positions), max(r_positions) + 1] if r_positions else None,
        "coordinates": result.coordinates.tolist(), "aligned_query": str(result[0]),
        "aligned_reference": str(result[1]), "mode": mode, "matrix": matrix,
        "gap_open": gap_open, "gap_extend": gap_extend,
        "biopython_version": version("biopython"),
        "limitations": ["pairwise_alignment_is_not_a_database_significance_test",
                        "one_alignment_is_not_an_orthology_or_function_assignment"],
    }


def compare_sites(alignment: dict[str, Any], reference_positions: list[int]) -> list[dict[str, Any]]:
    """Observe caller-selected sites in an existing alignment; do not interpret activity."""
    if not alignment.get("aligned"):
        raise ValueError("site_comparison_requires_alignment")
    wanted = set(reference_positions)
    if any(type(p) is not int or p < 0 or p >= alignment["reference_length"] for p in wanted):
        raise ValueError("invalid_reference_site")
    q_start = alignment["query_interval"][0]
    r_start = alignment["reference_interval"][0]
    query_position, reference_position = q_start, r_start
    found = {}
    for query_residue, reference_residue in zip(alignment["aligned_query"], alignment["aligned_reference"]):
        if reference_residue != "-" and reference_position in wanted:
            found[reference_position] = {
                "reference_position": reference_position, "reference_residue": reference_residue,
                "query_position": query_position if query_residue != "-" else None,
                "query_residue": query_residue if query_residue != "-" else None,
                "relationship": "gap" if query_residue == "-" else
                                "identical" if query_residue == reference_residue else "substituted",
            }
        if query_residue != "-":
            query_position += 1
        if reference_residue != "-":
            reference_position += 1
    return [found.get(p, {"reference_position": p, "relationship": "outside_alignment",
                          "reference_residue": None, "query_position": None, "query_residue": None})
            for p in reference_positions]
