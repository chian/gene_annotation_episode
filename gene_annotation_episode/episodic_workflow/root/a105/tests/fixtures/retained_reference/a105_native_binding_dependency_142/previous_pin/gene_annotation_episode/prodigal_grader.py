"""Native-output extraction and calculators for ``sequence_ops.predict_genes``.

The native worker already converts Prodigal's coordinates to zero-based,
half-open intervals. Supply that unshifted result, its submitted region length,
and the region's offset in the parent sequence. Parent intervals here refer to
that supplied parent's coordinates; mapping through an extracted/reversed
ancestor still belongs to the caller's existing sequence-mapping machinery.

Confidence is Pyrodigal's native gene-prediction percentage, never a probability
of function-annotation correctness. There is no overall grade. These functions
perform no I/O, acquisition, native execution, resource choice or credit update.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math


_SCHEMA = "prodigal_sheet_v1"
_COMPONENTS = ("interval", "strand", "code", "partial_begin", "partial_end",
               "protein_sequence", "native_confidence", "native_score")
_PROTEIN_SYMBOLS = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO*")


def _finite_json(value, code):
    """Reject values the native JSON worker cannot emit, without coercion."""
    def visit(item):
        if type(item) is dict:
            return all(type(key) is str and visit(child) for key, child in item.items())
        if type(item) is list:
            return all(visit(child) for child in item)
        if type(item) is float:
            return math.isfinite(item)
        return item is None or type(item) in (str, int, bool)
    try:
        valid = visit(value)
        if valid:
            json.dumps(value, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError(code) from error
    if not valid:
        raise ValueError(code)


def _input_geometry(input_length, input_start):
    if type(input_length) is not int or input_length < 0:
        raise ValueError("invalid_prodigal_input_length")
    if type(input_start) is not int or input_start < 0:
        raise ValueError("invalid_prodigal_input_start")


def _candidate(native, index, input_length, input_start, translation_code):
    issues, states = [], {}
    is_object = type(native) is dict
    values = native if is_object else {}
    if not is_object:
        issues.append({"code": "candidate_object_required"})

    def field(name, predicate, invalid_code):
        value = values.get(name)
        if not is_object:
            states[name] = "invalid"
            return None
        if value is None:
            states[name] = "missing"
            issues.append({"code": "missing_candidate_component", "field": name})
            return None
        if not predicate(value):
            states[name] = "invalid"
            issues.append({"code": invalid_code, "field": name})
            return None
        states[name] = "valid"
        return value

    start, end = values.get("start"), values.get("end")
    interval = None
    if not is_object:
        states["interval"] = "invalid"
    elif start is None or end is None:
        states["interval"] = "missing"
        issues.append({"code": "missing_candidate_interval",
                       "fields": [key for key in ("start", "end") if values.get(key) is None]})
    elif type(start) is not int or type(end) is not int:
        states["interval"] = "invalid"
        issues.append({"code": "candidate_interval_requires_integers"})
    elif not 0 <= start < end <= input_length:
        states["interval"] = "invalid"
        issues.append({"code": "candidate_interval_outside_input"})
    else:
        states["interval"] = "valid"
        interval = [start, end]
    strand = field("strand", lambda v: v in ("+", "-"), "invalid_candidate_strand")
    code = field("code", lambda v: type(v) is int and v > 0, "invalid_candidate_translation_code")
    if code is not None and translation_code is not None and code != translation_code:
        issues.append({"code": "candidate_translation_code_conflict", "field": "code"})
        states["code"] = "invalid"
        code = None
    begin = field("partial_begin", lambda v: type(v) is bool, "invalid_partial_flag")
    end_flag = field("partial_end", lambda v: type(v) is bool, "invalid_partial_flag")
    protein = field("protein_sequence", lambda v: type(v) is str and
                    set(v.upper()) <= _PROTEIN_SYMBOLS, "invalid_protein_sequence")
    confidence = field("native_confidence", lambda v: type(v) in (int, float) and
                       0 <= v <= 100, "native_confidence_outside_percent_range")
    score = field("native_score", lambda v: type(v) in (int, float), "invalid_native_score")
    if interval is not None and protein is not None and end - start != 3 * len(protein):
        issues.append({"code": "translation_span_symbol_count_conflict"})
    return {
        "candidate_index": index, "native_candidate": deepcopy(native),
        "relative_interval": interval,
        "parent_interval": [start + input_start, end + input_start] if interval is not None else None,
        "strand": strand, "translation_code": code,
        "partial_begin": begin, "partial_end": end_flag,
        "protein_sequence": protein, "native_confidence_percent": confidence,
        "native_score": score,
        # The worker does not report a frame. Do not infer a codon map from
        # boundary flags, sequence labels or the equality of two lengths.
        "native_frame": None,
        "component_status": states, "issues": issues,
        "status": "complete" if not issues else "partial" if "valid" in states.values() else "invalid",
    }


def build_prodigal_sheet(native: dict, *, input_length: int, input_start: int = 0) -> dict:
    """Retain all candidate rows and independently validate their components.

    Missing metadata is explicit; an explicitly incompatible mode or coordinate
    convention is a top-level contract error. Invalid finite candidate values
    remain in ``native_result`` and ``native_candidate`` while only affected
    normalized fields become null. Nonfinite/non-JSON input is rejected, as at
    the native worker's finite-JSON output boundary.
    """
    if type(native) is not dict:
        raise ValueError("prodigal_native_object_required")
    _finite_json(native, "finite_json_prodigal_native_required")
    _input_geometry(input_length, input_start)
    if type(native.get("candidates")) is not list:
        raise ValueError("prodigal_candidates_list_required")
    mode = native.get("mode")
    if mode is not None and mode not in ("meta", "single"):
        raise ValueError("invalid_prodigal_mode")
    coordinate_system = native.get("coordinate_system")
    if coordinate_system is not None and coordinate_system != "zero_based_half_open":
        raise ValueError("incompatible_prodigal_coordinate_system")
    code = native.get("translation_code")
    if code is not None and (type(code) is not int or code <= 0):
        raise ValueError("invalid_prodigal_translation_code")
    issues = []
    for name in ("mode", "translation_code", "coordinate_system", "pyrodigal_version"):
        if native.get(name) is None:
            issues.append({"code": "native_metadata_missing", "field": name})
    version = native.get("pyrodigal_version")
    if version is not None and (type(version) is not str or not version):
        issues.append({"code": "invalid_pyrodigal_version", "field": "pyrodigal_version"})
        version = None
    rows = [_candidate(item, index, input_length, input_start, code)
            for index, item in enumerate(native["candidates"])]
    issues.extend({**issue, "candidate_index": row["candidate_index"]}
                  for row in rows for issue in row["issues"])
    return {
        "schema": _SCHEMA,
        "status": "partial" if issues else "complete" if rows else "no_reported_candidates",
        "native_result": deepcopy(native), "mode": mode, "translation_code": code,
        "pyrodigal_version": version, "input_length": input_length, "input_start": input_start,
        "input_interval": [input_start, input_start + input_length],
        "coordinate_system": "zero_based_half_open",
        "coordinate_basis": "unshifted_sequence_ops_predict_genes_worker_contract",
        "candidates": rows, "issues": issues,
        "measurement_meanings": {
            "intervals": "predicted nucleotide spans; relative to submitted region and its supplied parent",
            "partial_flags": "native overlap with lower/upper sequence boundary, not biological 5-prime/3-prime labels",
            "native_confidence_percent": "native gene-calling confidence percentage in [0,100]; not function-annotation accuracy",
            "native_score": "unaltered Pyrodigal Gene.score model score; not a calibrated probability",
            "protein_sequence": "exact native translated symbols, including any literal stop markers",
            "native_frame": "not reported by sequence_ops.predict_genes; remains unknown",
            "uncertainty": "no interval or translation uncertainty reported beyond native confidence and partial flags",
        },
    }


def _checked_sheet(sheet):
    if type(sheet) is not dict or sheet.get("schema") != _SCHEMA:
        raise ValueError("prodigal_sheet_required")
    _finite_json(sheet, "finite_json_prodigal_sheet_required")
    # Verify saved projections against their retained source. This performs no
    # analysis rerun; it prevents a corrupted saved validity flag or interval
    # from authorizing a different numerical result.
    try:
        expected = build_prodigal_sheet(sheet.get("native_result"),
            input_length=sheet.get("input_length"), input_start=sheet.get("input_start"))
    except ValueError as error:
        raise ValueError("invalid_saved_prodigal_sheet") from error
    for key in ("mode", "translation_code", "pyrodigal_version", "input_interval",
                "coordinate_system", "coordinate_basis", "candidates", "status", "issues"):
        if sheet.get(key) != expected[key]:
            raise ValueError("inconsistent_saved_prodigal_sheet:" + key)


def _union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def calculate_prodigal_scores(sheet: dict) -> dict:
    """Calculate inspectable components from a saved sheet, without a total score.

    ``protein_length_aa`` counts non-stop symbols; ``translated_symbol_count``
    also includes ``*``. Stops are literal observations in the supplied protein
    string, not a new translation or a DNA-to-protein correspondence assertion.
    Coverage counts the union of valid reported intervals on either strand.
    Missing all intervals is unknown, while an explicit empty candidate list
    has zero covered bases. A zero-length input has null fractional coverage.
    """
    _checked_sheet(sheet)
    rows = []
    for candidate in sheet["candidates"]:
        interval = candidate["relative_interval"]
        protein = candidate["protein_sequence"]
        length_nt = interval[1] - interval[0] if interval is not None else None
        length_symbols = len(protein) if protein is not None else None
        stops = [index for index, symbol in enumerate(protein) if symbol == "*"] if protein is not None else None
        terminal = protein.endswith("*") if protein is not None else None
        begin, end = candidate["partial_begin"], candidate["partial_end"]
        partial = True if begin is True or end is True else False if begin is False and end is False else None
        rows.append({
            "candidate_index": candidate["candidate_index"],
            "relative_interval": deepcopy(interval), "parent_interval": deepcopy(candidate["parent_interval"]),
            "strand": candidate["strand"], "translation_code": candidate["translation_code"],
            "interval_length_nt": length_nt, "translated_symbol_count": length_symbols,
            "protein_length_aa": length_symbols - len(stops) if stops is not None else None,
            "native_score": candidate["native_score"],
            "native_confidence_percent": candidate["native_confidence_percent"],
            "partial_begin": begin, "partial_end": end, "partial": partial,
            "internal_stop_positions": [p for p in stops if p < length_symbols - 1] if stops is not None else None,
            "internal_stop_count": len(stops) - int(terminal) if stops is not None else None,
            "terminal_stop": terminal, "terminal_stop_count": int(terminal) if terminal is not None else None,
            "span_symbol_length_delta_nt": length_nt - 3 * length_symbols
                if length_nt is not None and length_symbols is not None else None,
            "component_status": deepcopy(candidate["component_status"]),
            "status": candidate["status"], "issues": deepcopy(candidate["issues"]),
        })
    intervals = [row["relative_interval"] for row in rows if row["relative_interval"] is not None]
    union = _union(intervals)
    union_bases = sum(end - start for start, end in union) if intervals or not rows else None
    length = sheet["input_length"]
    component_counts = {name: {state: sum(row["component_status"][name] == state for row in rows)
                              for state in ("valid", "missing", "invalid")} for name in _COMPONENTS}
    return {
        "schema": "prodigal_scores_v1", "status": sheet["status"],
        "mode": sheet["mode"], "translation_code": sheet["translation_code"],
        "candidates": rows,
        "summary": {
            "reported_candidate_count": len(rows), "valid_interval_candidate_count": len(intervals),
            "union_coding_bases": union_bases,
            "coding_coverage": union_bases / length if union_bases is not None and length else None,
            "coding_coverage_denominator_nt": length,
            "coverage_complete_for_reported_candidates": len(intervals) == len(rows),
            "relative_coding_intervals": union,
            "partial_candidate_count": sum(row["partial"] is True for row in rows),
            "partial_status_known_candidate_count": sum(row["partial"] is not None for row in rows),
            "partial_status_unknown_candidate_count": sum(row["partial"] is None for row in rows),
            "complete_candidate_count": sum(row["status"] == "complete" for row in rows),
            "candidate_with_invalid_component_count": sum("invalid" in row["component_status"].values() for row in rows),
            "candidate_with_missing_component_count": sum("missing" in row["component_status"].values() for row in rows),
            "invalid_component_count": sum(counts["invalid"] for counts in component_counts.values()),
            "missing_component_count": sum(counts["missing"] for counts in component_counts.values()),
            "component_counts": component_counts,
        },
        "calculations": {
            "population": "all reported candidate rows, including duplicates and invalid rows; order preserved",
            "interval_length_nt": "validated relative end - start; nt; null for missing/invalid interval",
            "translated_symbol_count": "len(native protein_sequence); residue/stop symbols; null for missing/invalid string",
            "protein_length_aa": "len(native protein_sequence) - count('*'); amino-acid symbols, including ambiguous symbols",
            "native_score": "native_score; native model-score units; no aggregation or normalization",
            "native_confidence_percent": "native_confidence; native prediction percent; null outside [0,100] or missing",
            "internal_stop_count": "count('*' in protein_sequence[:-1]); literal markers; zero-based positions retained",
            "terminal_stop_count": "1 if actual protein_sequence ends in '*' else 0; null if string unavailable",
            "span_symbol_length_delta_nt": "interval_length_nt - 3 * translated_symbol_count; arithmetic consistency only, not codon verification",
            "union_coding_bases": "size of union(valid relative candidate intervals), independent of strand; null if reported candidates exist but no interval is valid",
            "coding_coverage": "union_coding_bases / input_length; dimensionless; null for zero denominator or unknown numerator",
            "partial_candidate_count": "count with at least one native partial flag true; unknown flags are not false; known and unknown denominators retained",
            "component_counts": "counts of valid/missing/invalid for each of eight independently validated candidate components",
            "combinations": "interval union only; no overall score, annotation confidence or mean native score",
        },
        "issues": deepcopy(sheet["issues"]),
    }


def grade_prodigal(native: dict, *, input_length: int, input_start: int = 0) -> dict:
    """Return the tool-specific populated sheet and its numerical components."""
    sheet = build_prodigal_sheet(native, input_length=input_length, input_start=input_start)
    return {"sheet": sheet, "scores": calculate_prodigal_scores(sheet)}


__all__ = ["build_prodigal_sheet", "calculate_prodigal_scores", "grade_prodigal"]
