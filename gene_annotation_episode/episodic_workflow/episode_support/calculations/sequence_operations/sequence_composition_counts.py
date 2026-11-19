"""Shared composition counts and fractions, without sequence reconstruction.

Literal symbol counts, native DNA partitions and already validated saved
summary cells populate the same numerical sheet. Callers retain ownership of
source custody, population completeness, invalid-symbol policies and quality.
Unknown cells remain unknown; this module never repairs a saved summary from
another representation of its operands.
"""
from copy import deepcopy


SHEET_SCHEMA = "sequence_composition_count_sheet_v1"
COMPONENTS_SCHEMA = "sequence_composition_count_components_v1"
CANONICAL_SYMBOLS = {"dna": "ACGT", "rna": "ACGU", "protein": "ACDEFGHIKLMNPQRSTVWYOU"}
AMBIGUOUS_SYMBOLS = {"dna": "RYSWKMBDHVN", "rna": "RYSWKMBDHVN", "protein": "BXZJ"}
SUMMARY_FIELDS = ("unambiguous_nucleotide_count", "ambiguous_symbol_count",
                  "gc_count", "gc_denominator", "invalid_symbol_count")
_MOLECULES = {"dna", "rna", "protein", "unspecified"}
_PARTITIONS = ("A", "C", "G", "T", "N", "other_iupac", "invalid")


def _require(condition):
    if not condition:
        raise ValueError("sequence_composition_count_sheet_invalid")


def _count(value):
    _require(value is None or type(value) is int and value >= 0)
    return value


def _sum(values):
    values = list(values)
    return sum(values) if all(value is not None for value in values) else None


def _literal_summary(counts, molecule):
    if molecule == "unspecified":
        return dict.fromkeys(SUMMARY_FIELDS)
    canonical, ambiguous = CANONICAL_SYMBOLS[molecule], AMBIGUOUS_SYMBOLS[molecule]
    allowed = canonical + ambiguous + ("*" if molecule == "protein" else "")
    nucleotide = molecule in {"dna", "rna"}
    unambiguous = _sum(counts.get(symbol, 0) for symbol in canonical) if nucleotide else None
    return {"unambiguous_nucleotide_count": unambiguous,
            "ambiguous_symbol_count": _sum(counts.get(symbol, 0) for symbol in ambiguous),
            "gc_count": _sum(counts.get(symbol, 0) for symbol in "GC") if nucleotide else None,
            "gc_denominator": unambiguous,
            "invalid_symbol_count": _sum(value for symbol, value in counts.items() if symbol not in allowed)}


def populate_composition_count_sheet(*, molecule, length, basis, counts):
    """Retain true count operands and populate the common summary schema.

    In a complete literal-symbol table an absent key is an observed zero;
    explicit nulls are never zeros. Native partitions have all seven keys.
    The validated-saved basis copies each actual validated summary cell,
    including independent nulls in otherwise related summary fields.
    """
    _require(type(molecule) is str and molecule in _MOLECULES)
    _count(length)
    _require(type(counts) is dict and all(type(symbol) is str for symbol in counts))
    operands = {symbol: _count(value) for symbol, value in counts.items()}
    if basis == "literal_symbol_counts":
        summary = _literal_summary(operands, molecule)
    elif basis == "dna_partition_counts":
        _require(molecule == "dna" and set(operands) == set(_PARTITIONS))
        unambiguous = _sum(operands[symbol] for symbol in "ACGT")
        summary = {"unambiguous_nucleotide_count": unambiguous,
                   "ambiguous_symbol_count": _sum(operands[symbol] for symbol in ("N", "other_iupac")),
                   "gc_count": _sum(operands[symbol] for symbol in "GC"),
                   "gc_denominator": unambiguous, "invalid_symbol_count": operands["invalid"]}
    elif basis == "validated_saved_counts":
        _require(set(operands) == set(SUMMARY_FIELDS))
        summary = {field: operands[field] for field in SUMMARY_FIELDS}
    else:
        raise ValueError("sequence_composition_count_sheet_invalid")
    return {"schema": SHEET_SCHEMA, "molecule": molecule, "length": length,
            "basis": basis, "operands": operands, "summary": summary}


def composition_count_definitions():
    """Existing composition definitions, shared without changing projections."""
    return {
        "length": {"inputs": ["sequence"], "calculation": "len(sequence)", "unit": "supplied_symbols"},
        "symbol_counts": {"inputs": ["sequence"], "calculation": "count each symbol after ASCII-only uppercase",
                          "unit": "supplied_symbols"},
        "unambiguous_nucleotide_count": {"inputs": ["molecule", "symbol_counts"],
            "calculation": "sum A,C,G,T for dna; sum A,C,G,U for rna; otherwise null", "unit": "nt"},
        "ambiguous_symbol_count": {"inputs": ["molecule", "symbol_counts"],
            "calculation": "sum R,Y,S,W,K,M,B,D,H,V,N for dna/rna; sum B,X,Z,J for protein; unspecified null",
            "unit": "supplied_symbols"},
        "ambiguity_fraction": {"inputs": ["composition.ambiguous_symbol_count", "length"],
            "calculation": "ambiguous_symbol_count / length", "unit": "fraction_of_all_supplied_symbols"},
        "gc_count": {"inputs": ["molecule", "symbol_counts"],
            "calculation": "C + G for declared dna/rna; otherwise null", "unit": "nt"},
        "gc_denominator": {"inputs": ["composition.unambiguous_nucleotide_count"],
            "calculation": "unambiguous_nucleotide_count", "unit": "nt"},
        "gc_fraction": {"inputs": ["composition.gc_count", "composition.gc_denominator"],
            "calculation": "gc_count / gc_denominator; ambiguous and invalid symbols excluded", "unit": "fraction"},
    }


def calculate_composition_count_components(sheet, *, requested_fractions=("gc_fraction", "ambiguity_fraction")):
    """Calculate only requested ratios, retaining every actual operand cell.

    Choosing a fraction is the caller's decision after its own qualification;
    an unrequested fraction performs no division and retains its operands.
    """
    _require(type(requested_fractions) is tuple and all(type(name) is str and name in
        {"gc_fraction", "ambiguity_fraction"} for name in requested_fractions)
        and len(requested_fractions) == len(set(requested_fractions)))
    _require(type(sheet) is dict and set(sheet) == {
        "schema", "molecule", "length", "basis", "operands", "summary"})
    _require(sheet["schema"] == SHEET_SCHEMA)
    expected = populate_composition_count_sheet(molecule=sheet["molecule"], length=sheet["length"],
        basis=sheet["basis"], counts=sheet["operands"])
    _require(type(sheet["summary"]) is dict and set(sheet["summary"]) == set(SUMMARY_FIELDS))
    for field in SUMMARY_FIELDS:
        _count(sheet["summary"][field])
    _require(sheet["summary"] == expected["summary"])
    summary = sheet["summary"]
    fractions = {}
    for name, numerator, denominator in (
            ("gc_fraction", summary["gc_count"], summary["gc_denominator"]),
            ("ambiguity_fraction", summary["ambiguous_symbol_count"], sheet["length"])):
        reason = ("not_requested" if name not in requested_fractions else
                  "missing_count" if numerator is None or denominator is None else
                  "zero_denominator" if denominator == 0 else None)
        fractions[name] = {"numerator": numerator, "denominator": denominator,
                           "value": numerator / denominator if reason is None else None,
                           "reason": reason}
    return {"schema": COMPONENTS_SCHEMA, "summary": deepcopy(summary),
            "fractions": fractions, "definitions": composition_count_definitions()}


__all__ = ["SHEET_SCHEMA", "COMPONENTS_SCHEMA", "CANONICAL_SYMBOLS", "AMBIGUOUS_SYMBOLS",
           "SUMMARY_FIELDS", "populate_composition_count_sheet",
           "calculate_composition_count_components", "composition_count_definitions"]
