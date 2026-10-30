"""Sequence composition and declared FASTQ quality measurements, without I/O.

The builder retains supplied strings and extracts integer counts. The separate
calculator uses those counts to produce fractions, quality conversions and
threshold reports. It does not run sequence inspection, acquire data, select a
resource, assign annotation confidence or decide whether a read is acceptable.

Only ASCII letters are case-normalized; no whitespace or other symbols are
removed. Positions, where reported, are zero-based offsets in the exact supplied
string. Ambiguity means RYSWKMBDHVN for DNA/RNA and BXZJ for protein. Protein U
and O are specific residues and * is a stop symbol, not an ambiguous residue.
Unspecified molecule never acquires a biological identity from its alphabet.

Quality encoding names are the existing material/domain declarations. Their
score ranges and conversions follow Bio.SeqIO.QualityIO:
https://biopython.org/docs/latest/api/Bio.SeqIO.QualityIO.html
Phred33 uses ASCII 33..126 (Q=0..93), phred64 ASCII 64..126 (Q=0..62),
and solexa64 ASCII 59..126 (S=-5..62). For Solexa, p=1/(1+10**(S/10))
and Q=10*log10(1+10**(S/10)); no rounding precedes threshold comparison.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
import math

from . import sequence_composition_counts as composition_counts


SHEET_SCHEMA = "sequence_composition_sheet_v1"
SCORES_SCHEMA = "sequence_composition_scores_v1"
_MOLECULES = {"dna", "rna", "protein", "unspecified"}
_CANONICAL = composition_counts.CANONICAL_SYMBOLS
_AMBIGUOUS = composition_counts.AMBIGUOUS_SYMBOLS
_ENCODINGS = {"phred33": (33, 0, 93, "phred"),
              "phred64": (64, 0, 62, "phred"),
              "solexa64": (64, -5, 62, "solexa")}
_UPPER_ASCII = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_COMPOSITION_FIELDS = composition_counts.SUMMARY_FIELDS


def _validate_inputs(sequence, molecule, quality, quality_encoding):
    if not isinstance(sequence, str):
        raise ValueError("sequence_composition_sequence_string_required")
    if not isinstance(molecule, str) or molecule not in _MOLECULES:
        raise ValueError("sequence_composition_declared_molecule_required")
    if quality is not None and not isinstance(quality, str):
        raise ValueError("sequence_composition_quality_string_or_null_required")
    if quality_encoding is not None and not isinstance(quality_encoding, str):
        raise ValueError("sequence_composition_encoding_string_or_null_required")


def _finite_json_copy(value):
    def check(item):
        if type(item) is dict:
            return all(type(key) is str and check(child) for key, child in item.items())
        if type(item) is list:
            return all(check(child) for child in item)
        if type(item) is float:
            return math.isfinite(item)
        return item is None or type(item) in (str, int, bool)

    try:
        if not check(value):
            raise ValueError("non_json_value")
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("sequence_composition_finite_json_sheet_required") from error


def _counts(sequence):
    return dict(sorted(Counter(sequence.translate(_UPPER_ASCII)).items()))


def _composition(counts, molecule):
    return composition_counts.populate_composition_count_sheet(molecule=molecule, length=None,
        basis="literal_symbol_counts", counts=counts)["summary"]


def _quality_measurements(quality, encoding, sequence_length):
    """Extract native integer scores; invalid characters keep valid neighbours."""
    issues = []
    result = {"status": "not_supplied", "character_count": None,
              "length_matches_sequence": None, "native_score_type": None,
              "native_score_distribution": None, "decoded_character_count": None,
              "invalid_character_count": None, "invalid_characters": []}
    if quality is None:
        return result, issues
    result.update(character_count=len(quality), length_matches_sequence=len(quality) == sequence_length)
    if not result["length_matches_sequence"]:
        issues.append({"code": "quality_sequence_length_mismatch", "sequence_length": sequence_length,
                       "quality_length": len(quality)})
    if encoding is None or encoding == "unspecified":
        result["status"] = "encoding_unknown"
        issues.append({"code": "quality_encoding_not_declared"})
        return result, issues
    if encoding not in _ENCODINGS:
        result["status"] = "encoding_unsupported"
        issues.append({"code": "quality_encoding_unsupported", "quality_encoding": encoding})
        return result, issues
    offset, minimum, maximum, score_type = _ENCODINGS[encoding]
    native_counts = Counter()
    for position, character in enumerate(quality):
        score = ord(character) - offset
        if minimum <= score <= maximum:
            native_counts[score] += 1
        else:
            result["invalid_characters"].append({"position": position, "codepoint": ord(character)})
    invalid_count = len(result["invalid_characters"])
    result.update(native_score_type=score_type,
                  native_score_distribution=[{"native_score": score, "count": count}
                                             for score, count in sorted(native_counts.items())],
                  decoded_character_count=sum(native_counts.values()),
                  invalid_character_count=invalid_count,
                  status="complete" if not invalid_count and result["length_matches_sequence"] else "invalid")
    if invalid_count:
        issues.append({"code": "quality_characters_outside_declared_encoding", "count": invalid_count})
    return result, issues


def build_sequence_composition_sheet(sequence: str, *, molecule: str,
                                     quality: str | None = None,
                                     quality_encoding: str | None = None) -> dict:
    """Populate a finite numerical sheet from actual supplied sequence/quality.

    Invalid symbols and unusable quality retain valid partial observations with
    issue codes. Wrong argument types or an undeclared molecule value raise a
    specific ValueError. A declaration of ``unspecified`` is valid and leaves
    molecule-dependent measurements null. Quality encoding is never guessed.
    """
    _validate_inputs(sequence, molecule, quality, quality_encoding)
    counts = _counts(sequence)
    composition = _composition(counts, molecule)
    qualities, issues = _quality_measurements(quality, quality_encoding, len(sequence))
    if molecule == "unspecified":
        issues.append({"code": "molecule_unspecified"})
    elif composition["invalid_symbol_count"]:
        allowed = _CANONICAL[molecule] + _AMBIGUOUS[molecule] + ("*" if molecule == "protein" else "")
        issues.append({"code": "unexpected_symbol_for_declared_molecule",
                       "symbol_counts": {symbol: count for symbol, count in counts.items() if symbol not in allowed}})
    return {"schema": SHEET_SCHEMA, "status": "partial" if issues else "complete",
            "sequence": sequence, "molecule": molecule, "quality": quality,
            "quality_encoding": quality_encoding, "length": len(sequence),
            "symbol_counts": counts, "composition": composition,
            "quality_measurements": qualities, "issues": issues,
            "symbol_normalization": "ascii_letters_uppercase_no_symbols_removed",
            "coordinate_system": "zero_based_offsets_in_supplied_strings"}


def _checked_count(value, expected, field, issues):
    if expected is None:
        if value is not None:
            issues.append({"code": "measurement_unavailable_for_inputs", "field": field})
        return None
    if type(value) is not int or value < 0:
        issues.append({"code": "invalid_or_missing_count", "field": field})
        return None
    if value != expected:
        issues.append({"code": "count_conflicts_with_retained_input", "field": field})
        return None
    return value


def _validated_measurements(sheet):
    """Check saved associations without repairing or mutating historical cells."""
    if not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("sequence_composition_sheet_required")
    saved = _finite_json_copy(sheet)
    if not all(key in saved for key in ("sequence", "molecule", "quality", "quality_encoding")):
        raise ValueError("sequence_composition_saved_inputs_required")
    _validate_inputs(saved["sequence"], saved["molecule"], saved["quality"], saved["quality_encoding"])
    if (not isinstance(saved.get("symbol_counts"), dict)
            or not isinstance(saved.get("composition"), dict)
            or not isinstance(saved.get("quality_measurements"), dict)
            or not isinstance(saved.get("issues"), list)
            or any(not isinstance(issue, dict) for issue in saved["issues"])):
        raise ValueError("sequence_composition_sheet_measurements_required")
    issues = saved["issues"]
    length = _checked_count(saved.get("length"), len(saved["sequence"]), "length", issues)
    expected_counts = _counts(saved["sequence"])
    counts = {symbol: _checked_count(saved["symbol_counts"].get(symbol), expected_counts.get(symbol, 0),
                                     "symbol_counts." + symbol, issues)
              for symbol in sorted(set(saved["symbol_counts"]) | set(expected_counts))}
    expected_composition = _composition(counts, saved["molecule"])
    composition = {field: _checked_count(saved["composition"].get(field), value,
                                         "composition." + field, issues)
                   for field, value in expected_composition.items()}
    expected_quality, quality_issues = _quality_measurements(saved["quality"], saved["quality_encoding"],
                                                            len(saved["sequence"]))
    for issue in quality_issues:
        if issue not in issues:
            issues.append(issue)
    quality_available = expected_quality["status"] == "complete" and length is not None
    for field, expected in expected_quality.items():
        # JSON distinguishes booleans/floats from native integer counts even
        # where Python's value equality would accept True == 1 or 1.0 == 1.
        actual = saved["quality_measurements"].get(field)
        if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
            issues.append({"code": "quality_measurement_conflicts_with_retained_input",
                           "field": "quality_measurements." + field})
            quality_available = False
    return saved, length, counts, composition, quality_available, issues


def _fraction(numerator, denominator):
    return numerator / denominator if numerator is not None and denominator else None


def _definitions():
    # Descriptive metadata for ordinary functions, never an executable rule language.
    return {
        **composition_counts.composition_count_definitions(),
        "quality_observation_count": {"inputs": ["quality_measurements.native_score_distribution"],
            "calculation": "sum counts only for supported declared encoding and valid quality of matching length",
            "unit": "base_quality_observations"},
        "quality_components": {"inputs": ["quality_encoding", "quality_measurements.native_score_distribution"],
            "calculation": "phred: Q=native_score, p=10**(-Q/10); solexa: p=1/(1+10**(S/10)), Q=10*log10(1+10**(S/10))",
            "unit": "native_score; phred; probability"},
        "mean_phred": {"inputs": ["quality_components", "quality_observation_count"],
            "calculation": "sum(count * phred) / quality_observation_count", "unit": "phred"},
        "mean_error_probability": {"inputs": ["quality_components", "quality_observation_count"],
            "calculation": "sum(count * error_probability) / quality_observation_count", "unit": "probability"},
        "expected_error_count": {"inputs": ["quality_components"],
            "calculation": "sum(count * error_probability); additive expectation does not assume independence",
            "unit": "expected_base_call_errors"},
        "quality_thresholds": {"inputs": ["quality_components", "quality_observation_count", "quality_thresholds"],
            "calculation": "count_at_or_above=sum(count where unrounded phred >= threshold); fraction=count/denominator",
            "unit": "phred_threshold; observations; fraction", "comparison": "greater_than_or_equal"},
        "missing": "Unavailable measurements and zero-denominator fractions are null. A valid empty quality population has count and expected error sum zero.",
        "measurement_kind": "Counts are extracted from supplied symbols. Fractions and quality summaries are derived; errors are encoding-implied expectations, not observed errors.",
        "uncertainty": None,
        "uncertainty_meaning": "No uncertainty intervals or quality calibration metadata were supplied.",
    }


def calculate_sequence_composition_scores(sheet: dict, *,
                                          quality_thresholds: tuple[int, ...] = (20, 30)) -> dict:
    """Calculate inspectable numerical components from a saved populated sheet.

    Every requested integer threshold is reported in caller order, including
    duplicates; thresholds are measurements, not pass/fail gates. The saved
    distributions are checked against retained strings before use. Individual
    inconsistent cells become unknown with issues while valid cells survive.
    Nonfinite/non-JSON sheets or malformed top-level contracts raise ValueError.
    """
    if type(quality_thresholds) is not tuple or any(type(value) is not int for value in quality_thresholds):
        raise ValueError("sequence_composition_integer_quality_thresholds_tuple_required")
    try:
        json.dumps(quality_thresholds, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("sequence_composition_json_quality_thresholds_required") from error
    saved, length, counts, composition, available, issues = _validated_measurements(sheet)
    common = composition_counts.calculate_composition_count_components(
        composition_counts.populate_composition_count_sheet(molecule=saved["molecule"], length=length,
            basis="validated_saved_counts", counts=composition))
    components = None
    observation_count = mean_phred = mean_error = expected_errors = None
    if available:
        components = []
        for row in saved["quality_measurements"]["native_score_distribution"]:
            native = row["native_score"]
            if saved["quality_encoding"] == "solexa64":
                odds = 10 ** (native / 10)
                phred = 10 * math.log10(1 + odds)
                error = 1 / (1 + odds)
            else:
                phred, error = native, 10 ** (-native / 10)
            components.append({"native_score": native, "count": row["count"],
                               "phred": phred, "error_probability": error})
        observation_count = sum(row["count"] for row in components)
        expected_errors = math.fsum(row["count"] * row["error_probability"] for row in components)
        mean_error = _fraction(expected_errors, observation_count)
        mean_phred = _fraction(math.fsum(row["count"] * row["phred"] for row in components), observation_count)
    thresholds = []
    for threshold in quality_thresholds:
        count = sum(row["count"] for row in components if row["phred"] >= threshold) if available else None
        thresholds.append({"phred_threshold": threshold, "count_at_or_above": count,
                           "fraction_at_or_above": _fraction(count, observation_count),
                           "denominator": observation_count})
    return {"schema": SCORES_SCHEMA, "status": "partial" if issues else "complete",
            "length": length, "symbol_counts": counts,
            **{field: composition[field] for field in _COMPOSITION_FIELDS if field != "invalid_symbol_count"},
            "ambiguity_fraction": common["fractions"]["ambiguity_fraction"]["value"],
            "gc_fraction": common["fractions"]["gc_fraction"]["value"],
            "quality_observation_count": observation_count, "mean_phred": mean_phred,
            "mean_error_probability": mean_error, "expected_error_count": expected_errors,
            "quality_components": components, "quality_thresholds": thresholds,
            "denominators": {"ambiguity_fraction": length if saved["molecule"] != "unspecified" else None,
                             "gc_fraction": composition["gc_denominator"],
                             "mean_phred": observation_count, "mean_error_probability": observation_count},
            "definitions": _definitions(), "issues": deepcopy(issues)}


def grade_sequence_composition(sequence: str, *, molecule: str,
                               quality: str | None = None,
                               quality_encoding: str | None = None,
                               quality_thresholds: tuple[int, ...] = (20, 30)) -> dict:
    """Return the retained numerical sheet and separately calculated components."""
    sheet = build_sequence_composition_sheet(sequence, molecule=molecule, quality=quality,
                                              quality_encoding=quality_encoding)
    return {"sheet": sheet, "scores": calculate_sequence_composition_scores(
        sheet, quality_thresholds=quality_thresholds)}


__all__ = ["SHEET_SCHEMA", "SCORES_SCHEMA", "build_sequence_composition_sheet",
           "calculate_sequence_composition_scores", "grade_sequence_composition"]
