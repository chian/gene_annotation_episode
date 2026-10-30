"""Numerical validation of an executed sequence.view supporting transformation.

The reader retains the actual input/result and ordered source correspondence.
The calculator uses only that saved sheet. Neither performs native execution,
I/O, resource selection, biological classification or annotation scoring.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from .sequence_mapping import map_interval, reverse_path, slice_path, validate_mapping


SHEET_SCHEMA = "sequence_extraction_sheet_v1"
SCORES_SCHEMA = "sequence_extraction_scores_v1"
NATIVE_VERSION = "explicit_sequence_view_v1"
_REQUEST_KEYS = {"molecule", "segments", "orientation"}
# Fixed semantics of explicit_sequence_view_v1, independent of installed Bio at
# recalculation. The helper accepts both T and U and preserves ASCII case.
_DNA = dict(zip("ACGTURYSWKMBDHVN", "TGCAAYRSWMKVHDBN"))
_RNA = {**_DNA, "A": "U"}
_DNA.update({key.lower(): value.lower() for key, value in list(_DNA.items())})
_RNA.update({key.lower(): value.lower() for key, value in list(_RNA.items())})


def frozen_reverse_complement(sequence, *, molecule):
    """Inspect symbols with the existing frozen DNA/RNA complement authority.

    None means that a symbol has no complement in this declared model. This
    pure helper does not execute Bio or establish a molecule assignment.
    """
    if type(sequence) is not str or molecule not in ("dna", "rna"):
        raise ValueError("sequence_extraction_complement_operands_required")
    complement = _RNA if molecule == "rna" else _DNA
    if all(symbol in complement for symbol in sequence):
        return "".join(complement[symbol] for symbol in reversed(sequence))
    return None


def _json_copy(value):
    def check(item):
        if item is None or type(item) in (str, int, bool):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("sequence_extraction_finite_json_required")
    try:
        check(value)
        return deepcopy(value)
    except RecursionError as error:
        raise ValueError("sequence_extraction_finite_json_required") from error


def _same(left, right):
    # Bool/int and float/int are different typed measurements, even when ==.
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def _union(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def _coverage(path):
    if path is None:
        return None
    groups = {}
    for row in path:
        key = row["subject_ref"], row["unit"]
        groups.setdefault(key, []).append([row["start"], row["end"]])
    # Only this coverage projection is a union. The source path remains ordered.
    return [{"subject_ref": ref, "unit": unit, "intervals": _union(spans),
             "distinct_source_position_count": sum(b - a for a, b in _union(spans)),
             "source_position_occurrence_count": sum(b - a for a, b in spans),
             "repeated_source_position_count": sum(b - a for a, b in spans)
                 - sum(b - a for a, b in _union(spans))}
            for (ref, unit), spans in sorted(groups.items())]


def _matching_runs(expected, observed):
    runs, start = [], None
    for offset, (left, right) in enumerate(zip(expected, observed)):
        if left == right and start is None:
            start = offset
        elif left != right and start is not None:
            runs.append([start, offset])
            start = None
    if start is not None:
        runs.append([start, min(len(expected), len(observed))])
    return runs


def _read(native, *, input_sequence, subject_ref, parent_mapping, request):
    """Extract and cross-check supplied operands; never call the native helper."""
    if type(native) is not dict or (native.get("operation_version") is not None
            and native["operation_version"] != NATIVE_VERSION) or "schema" in native:
        raise ValueError("sequence_extraction_native_schema_required")
    if type(request) is not dict or set(request) != _REQUEST_KEYS:
        raise ValueError("sequence_extraction_effective_request_required")
    issues, status = [], {}

    def issue(field, code, state="incompatible"):
        issues.append({"field": field, "code": code})
        status[field] = state

    def text_operand(value, field):
        if isinstance(value, str):
            status[field] = "present"
            return value
        issue(field, "missing_string" if value is None else "invalid_string",
              "missing" if value is None else "incompatible")
        return None

    source = text_operand(input_sequence, "input_sequence")
    output = text_operand(native.get("sequence"), "native_result.sequence")
    subject = text_operand(subject_ref, "subject_ref")
    if subject == "":
        issue("subject_ref", "nonempty_subject_ref_required")
        subject = None
    input_length = len(source) if source is not None else None
    output_length = len(output) if output is not None else None
    if source == "":
        issue("input_sequence", "native_view_requires_nonempty_input")
    molecule, orientation = request["molecule"], request["orientation"]
    model_ok = molecule in ("dna", "rna", "protein")
    orientation_ok = orientation in ("as_is", "reverse_complement")
    if not model_ok:
        issue("request.molecule", "explicit_processing_model_required",
              "missing" if molecule is None else "incompatible")
    if not orientation_ok:
        issue("request.orientation", "explicit_orientation_required",
              "missing" if orientation is None else "incompatible")
    if molecule == "protein" and orientation == "reverse_complement":
        issue("request.orientation", "protein_reverse_complement_undefined")
        orientation_ok = False

    supplied_segments = request["segments"]
    if not isinstance(supplied_segments, list) or not supplied_segments:
        issue("request.segments", "nonempty_selected_segments_required",
              "missing" if supplied_segments is None else "incompatible")
    raw_rows = supplied_segments if isinstance(supplied_segments, list) else []
    lengths = []
    for ordinal, segment in enumerate(raw_rows):
        valid = (type(segment) is dict and set(segment) == {"start", "end"}
                 and type(segment["start"]) is int and type(segment["end"]) is int
                 and 0 <= segment["start"] < segment["end"]
                 and input_length is not None and segment["end"] <= input_length)
        lengths.append(segment["end"] - segment["start"] if valid else None)
        if not valid:
            issue(f"request.segments.{ordinal}", "interval_unavailable_or_outside_input",
                  "missing" if input_length is None else "incompatible")
    selection_complete = bool(raw_rows) and all(length is not None for length in lengths)
    selected_length = sum(lengths) if selection_complete else None

    # Native assertions do not override the actual request or the actual strings.
    metadata_expected = {
        "molecule_model": molecule, "orientation": orientation,
        "input_segments": supplied_segments, "input_length": input_length,
        "output_length": output_length, "coordinate_system": "zero_based_half_open",
        "operation_version": NATIVE_VERSION, "molecule_assignment": "not_performed",
    }
    metadata_ok = True
    for field, expected in metadata_expected.items():
        key = "native_result." + field
        if native.get(field) is None:
            issue(key, "missing_native_field", "missing")
            metadata_ok = False
        elif expected is None:
            issue(key, "native_field_cannot_be_checked_without_operand", "incomplete")
            metadata_ok = False
        elif not _same(native[field], expected):
            issue(key, "native_field_conflicts_with_supplied_operand")
            metadata_ok = False
        else:
            status[key] = "present"

    mapping_ok = False
    if parent_mapping is None:
        issue("parent_mapping", "original_source_correspondence_not_supplied", "missing")
    else:
        try:
            validate_mapping(parent_mapping)
            if input_length is None or parent_mapping["symbol_length"] != input_length:
                raise ValueError("mapping_symbol_length_conflicts_with_input")
            if parent_mapping["units_per_symbol"] == 3 and any(
                    part["unit"] not in {"nt", "symbol"} for part in parent_mapping["path"]):
                raise ValueError("three_unit_ancestry_requires_nucleotide_or_unspecified_source_units")
            mapping_ok = subject is not None
            status["parent_mapping"] = "present" if mapping_ok else "incomplete"
        except (ValueError, TypeError) as error:
            issue("parent_mapping", str(error))

    # Each segment's output position is known only if all preceding segments in
    # output order have valid lengths. This preserves valid prefixes of partial
    # data without clipping or reordering the caller's selection.
    offsets = [None] * len(raw_rows)
    output_order = list(range(len(raw_rows)))
    if orientation == "reverse_complement":
        output_order.reverse()
    offset = 0
    if orientation_ok:
        for ordinal in output_order:
            length = lengths[ordinal]
            if length is None:
                offset = None
            elif offset is not None:
                offsets[ordinal] = [offset, offset + length]
                offset += length

    rows = []
    for ordinal, segment in enumerate(raw_rows):
        length, bounds = lengths[ordinal], offsets[ordinal]
        input_interval = [segment["start"], segment["end"]] if length is not None else None
        selected = source[slice(*input_interval)] if input_interval is not None else None
        expected = None
        if selected is not None and model_ok and orientation_ok:
            if orientation == "as_is":
                expected = selected
            else:
                expected = frozen_reverse_complement(selected, molecule=molecule)
                if expected is None:
                    issue(f"segments.{ordinal}.expected_output_symbols",
                          "reverse_complement_requires_nucleotide_symbols")
        observed_bounds = ([min(bounds[0], output_length), min(bounds[1], output_length)]
                           if bounds is not None and output is not None else None)
        observed = output[slice(*observed_bounds)] if observed_bounds is not None else None
        compared = min(len(expected), len(observed)) if expected is not None and observed is not None else None
        matches = sum(a == b for a, b in zip(expected, observed)) if compared is not None else None
        requested_path = None
        if mapping_ok and input_interval is not None and orientation_ok:
            requested_path = map_interval(parent_mapping, *input_interval)
            if orientation == "reverse_complement":
                requested_path = reverse_path(requested_path)
        runs = None
        if requested_path is not None and metadata_ok and compared is not None:
            scale = parent_mapping["units_per_symbol"]
            runs = [{"output_interval": [bounds[0] + a, bounds[0] + b],
                     "source_path": slice_path(requested_path, a * scale, b * scale)}
                    for a, b in _matching_runs(expected, observed)]
        rows.append({"request_ordinal": ordinal, "subject_ref": subject_ref,
            "input_interval": input_interval, "orientation": orientation,
            "expected_output_interval": bounds, "actual_output_interval": observed_bounds,
            "input_symbols": selected, "expected_output_symbols": expected,
            "actual_output_symbols": observed, "selected_symbol_occurrence_count": length,
            "compared_symbol_count": compared, "matching_symbol_count": matches,
            "mismatching_symbol_count": compared - matches if compared is not None else None,
            "requested_source_path": requested_path, "verified_output_runs": runs})
        if compared is None:
            issue(f"segments.{ordinal}.symbol_comparison", "comparison_operands_unavailable", "missing")
        elif compared != length:
            issue(f"segments.{ordinal}.symbol_comparison", "output_segment_incomplete", "incomplete")
        elif matches != compared:
            issue(f"segments.{ordinal}.symbol_comparison", "actual_output_symbols_conflict_with_input")
        else:
            status[f"segments.{ordinal}.symbol_comparison"] = "present"

    measurements = {"input_symbol_count": input_length, "output_symbol_count": output_length,
        "requested_segment_count": len(raw_rows) if isinstance(supplied_segments, list) else None,
        "selected_symbol_occurrence_count": selected_length,
        "selected_input_intervals": _union([row["input_interval"] for row in rows]) if selection_complete else None}
    if selected_length is not None and output_length is not None and selected_length != output_length:
        issue("output_length", "actual_output_length_differs_from_selected_occurrences", "incomplete")
    # None denotes unavailable correspondence, [] denotes a known empty set.
    requested_path = ([part for i in output_order for part in (rows[i]["requested_source_path"] or [])]
                      if selection_complete and mapping_ok and orientation_ok else None)
    verified_path = ([part for i in output_order for run in (rows[i]["verified_output_runs"] or [])
                      for part in run["source_path"]]
                     if mapping_ok and metadata_ok and output is not None and orientation_ok else None)
    return {"measurements": measurements, "segments": rows, "output_segment_order": output_order,
            "requested_source_path": requested_path, "verified_output_source_path": verified_path,
            "component_status": status, "issues": issues}


def build_extraction_sheet(native, *, input_sequence, subject_ref, parent_mapping, request) -> dict:
    """Retain supplied bytes-as-strings, native fields and numerical segment cells."""
    inputs = _json_copy({"native_result": native, "input_sequence": input_sequence,
        "subject_ref": subject_ref, "parent_mapping": parent_mapping, "request": request})
    extracted = _read(inputs["native_result"], **{key: inputs[key] for key in (
        "input_sequence", "subject_ref", "parent_mapping", "request")})
    return {"schema": SHEET_SCHEMA, **inputs, **extracted}


def _definitions():
    rows = {
        "input_symbol_count": ("input_sequence", "len(input_sequence)", "input_symbols"),
        "output_symbol_count": ("native_result.sequence", "len(actual output string)", "output_symbols"),
        "requested_segment_count": ("request.segments", "len(request.segments), including repetitions", "segments"),
        "selected_symbol_occurrence_count": ("segments.input_interval", "sum(end-start) over every selected occurrence", "input_symbol_occurrences"),
        "distinct_selected_input_symbol_count": ("measurements.selected_input_intervals", "length of union of selected input intervals", "distinct_input_positions"),
        "repeated_selected_input_symbol_count": ("selected_symbol_occurrence_count,distinct_selected_input_symbol_count", "occurrences minus distinct positions; extra occurrences beyond the first", "input_symbol_occurrences"),
        "selected_input_fraction": ("distinct_selected_input_symbol_count,input_symbol_count", "distinct/input length; null for zero or missing denominator", "fraction"),
        "selected_input_fraction_denominator_symbols": ("input_symbol_count", "exact supplied input length", "input_symbols"),
        "expected_output_symbol_count": ("selected_symbol_occurrence_count", "selected occurrences (extraction is length preserving)", "output_symbols"),
        "output_length_difference": ("output_symbol_count,expected_output_symbol_count", "actual minus expected, retaining the sign", "output_symbols"),
        "compared_symbol_count": ("segments.compared_symbol_count", "sum positions with both actual and expected symbols; positional comparison, not alignment", "output_symbols"),
        "matching_symbol_count": ("segments.matching_symbol_count", "sum exact case-sensitive symbol matches at compared positions", "output_symbols"),
        "mismatching_symbol_count": ("segments.mismatching_symbol_count", "sum unequal symbols at compared positions; missing suffix is excluded", "output_symbols"),
        "mapped_output_symbol_count": ("segments.verified_output_runs", "sum verified run lengths with validated supplied parent ancestry and native metadata", "output_symbols"),
        "unmapped_output_symbol_count": ("output_symbol_count,mapped_output_symbol_count", "actual output length minus positions with verified supplied original correspondence; missing mapping counts as unverified, not absent biology", "output_symbols"),
        "source_segment_count": ("verified_output_source_path", "number of ordered verified source path pieces, including repeated pieces and split ancestry", "source_intervals"),
    }
    result = {name: {"inputs": fields.split(","), "calculation": formula, "unit": unit,
                    "kind": "observed_count" if name in {"input_symbol_count", "output_symbol_count"} else "derived",
                    "population": "supplied input and actual output of this selected extraction only",
                    "denominator": "input_symbol_count" if name == "selected_input_fraction" else None,
                    "range": "[0,1]" if name == "selected_input_fraction" else "integer" if name == "output_length_difference" else "nonnegative integer",
                    "uncertainty": None,
                    "missing": "null when required operands or saved cells are unavailable/incompatible; valid partial comparisons retain their actual compared denominator"}
              for name, (fields, formula, unit) in rows.items()}
    result.update({
        "coordinate_system": "zero_based_half_open; request_ordinal is zero based",
        "segment_intervals": "expected_output_interval is requested output placement; actual_output_interval is its intersection with the retained output string (possibly empty)",
        "processing_model": "as_is preserves every symbol; reverse_complement uses frozen explicit_sequence_view_v1 DNA/RNA complements with case preservation; U and T complement to A; the model does not establish input identity",
        "source_coverage": {"inputs": ["requested_source_path", "verified_output_source_path"],
            "calculation": "group by exact (subject_ref,unit); union intervals for distinct_source_position_count; sum lengths for source_position_occurrence_count; subtract distinct from occurrences for repeated_source_position_count",
            "unit": "each group's original nt, aa or symbol; never pooled across identities or units",
            "denominator": None, "range": "nonnegative integer", "uncertainty": None,
            "missing": "null when the relevant path is unavailable; no original source sequence or total length is inferred"},
        "three_unit_ancestry": "units_per_symbol=3 maps one protein output symbol to three original nt or unspecified source symbols, including split intervals; output-symbol counts stay separate",
        "original_source_validation_limit": "parent_mapping is explicitly supplied by the host; source contents, lengths and identity bindings cannot be independently reacquired or verified from this mapping alone",
        "combination": None, "annotation_probability": "not_calculated_supporting_transformation",
    })
    return result


def calculate_extraction_scores(sheet) -> dict:
    """Calculate numerical components from a saved sheet, with no reacquisition.

    Normalized cells are checked against their retained operands. Tampering does
    not silently repair the saved sheet: affected components become unavailable.
    The checks are arithmetic and literal symbol comparisons, never a native run.
    """
    saved = _json_copy(sheet)
    required = {"schema", "native_result", "input_sequence", "subject_ref", "parent_mapping", "request",
                "measurements", "segments", "output_segment_order", "requested_source_path",
                "verified_output_source_path", "component_status", "issues"}
    if (type(saved) is not dict or set(saved) != required or saved["schema"] != SHEET_SCHEMA
            or type(saved["measurements"]) is not dict or type(saved["segments"]) is not list
            or type(saved["component_status"]) is not dict or type(saved["issues"]) is not list):
        raise ValueError("sequence_extraction_sheet_schema_required")
    expected = _read(saved["native_result"], **{key: saved[key] for key in (
        "input_sequence", "subject_ref", "parent_mapping", "request")})
    issues = deepcopy(expected["issues"])
    status = deepcopy(expected["component_status"])

    def checked(actual, wanted, field):
        if not _same(actual, wanted):
            issues.append({"field": field, "code": "saved_cell_conflicts_with_retained_operands"})
            status[field] = "incompatible"
            return None
        return deepcopy(actual)

    values = {key: checked(saved["measurements"].get(key), value, "measurements." + key)
              for key, value in expected["measurements"].items()}
    rows = []
    for ordinal, wanted in enumerate(expected["segments"]):
        actual = saved["segments"][ordinal] if ordinal < len(saved["segments"]) else None
        row = checked(actual, wanted, f"segments.{ordinal}")
        rows.append(row if row is not None else {"request_ordinal": ordinal, "status": "incompatible"})
    if len(saved["segments"]) != len(expected["segments"]):
        issues.append({"field": "segments", "code": "saved_segment_count_conflicts_with_request"})
        status["segments"] = "incompatible"
    order = checked(saved["output_segment_order"], expected["output_segment_order"], "output_segment_order")
    requested_path = checked(saved["requested_source_path"], expected["requested_source_path"], "requested_source_path")
    verified_path = checked(saved["verified_output_source_path"], expected["verified_output_source_path"], "verified_output_source_path")
    complete_rows = all(row.get("status") != "incompatible" for row in rows) and len(rows) == len(saved["segments"])
    if not complete_rows or order is None:
        requested_path = verified_path = None
    available = [row for row in rows if row.get("compared_symbol_count") is not None]
    count = lambda name: sum(row[name] for row in available) if available else None
    union = values.pop("selected_input_intervals")
    distinct = sum(b - a for a, b in union) if union is not None else None
    selected, actual = values["selected_symbol_occurrence_count"], values["output_symbol_count"]
    denominator = values["input_symbol_count"]
    mapped = (sum(b - a for row in rows for run in (row.get("verified_output_runs") or [])
                  for a, b in [run["output_interval"]]) if verified_path is not None else 0)
    summary = {**values,
        "distinct_selected_input_symbol_count": distinct,
        "repeated_selected_input_symbol_count": selected - distinct if selected is not None and distinct is not None else None,
        "selected_input_fraction": distinct / denominator if distinct is not None and denominator else None,
        "selected_input_fraction_denominator_symbols": denominator,
        "expected_output_symbol_count": selected,
        "output_length_difference": actual - selected if actual is not None and selected is not None else None,
        "compared_symbol_count": count("compared_symbol_count"),
        "matching_symbol_count": count("matching_symbol_count"),
        "mismatching_symbol_count": count("mismatching_symbol_count"),
        "mapped_output_symbol_count": mapped if actual is not None else None,
        "unmapped_output_symbol_count": actual - mapped if actual is not None else None,
        "source_segment_count": len(verified_path) if verified_path is not None else None}
    result = {"schema": SCORES_SCHEMA, "summary": summary,
        "segments": rows, "output_segment_order": order,
        "requested_source_path": requested_path, "verified_output_source_path": verified_path,
        "selected_source_coverage": _coverage(requested_path), "output_source_coverage": _coverage(verified_path),
        "component_status": status, "issues": issues, "definitions": _definitions()}
    for field, value in summary.items():
        if value is None:
            status[field] = "missing" if not any(v == "incompatible" for v in status.values()) else "incompatible"
            issues.append({"field": field, "code": "required_component_operands_unavailable"})
        else:
            status[field] = "present"
    result["status"] = "complete" if not issues else "partial"
    return result


def grade_extraction(native, *, input_sequence, subject_ref, parent_mapping, request) -> dict:
    sheet = build_extraction_sheet(native, input_sequence=input_sequence, subject_ref=subject_ref,
                                   parent_mapping=parent_mapping, request=request)
    return {"sheet": sheet, "scores": calculate_extraction_scores(sheet)}


__all__ = ["SHEET_SCHEMA", "SCORES_SCHEMA", "build_extraction_sheet",
           "calculate_extraction_scores", "grade_extraction", "frozen_reverse_complement"]
