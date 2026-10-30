"""Read retained source logs and calculate only their supplied site rows.

The named source profile is declared, not an execution/transport receipt. A
complete source-format log does not prove a complete scan, glycan occupancy,
native use, or calibrated prediction accuracy. No missing site is enumerated.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .sequence_composition_grader import (
    build_sequence_composition_sheet, calculate_sequence_composition_scores,
)
from .sequence_mapping import validate_mapping, map_interval


SHEET_SCHEMA = "glycosylation_measurement_sheet_v1"
COMPONENTS_SCHEMA = "glycosylation_measurement_components_v1"
SOURCE_SHA256 = "ed3726d318f239e98183a359f18bcd341f4159ef2e400322c6141f77dcd2aff2"
_N = "find_n_glycosylation_motifs"
_O = "predict_o_glycosylation_hotspots"
_PROFILES = {
    _N: {"defaults": {"allow_overlap": False},
        "title": "# N-linked glycosylation sequon scan (N-X-[S/T], X≠P)",
        "heading": "Positions (1-based):",
        "empty": "No canonical N-linked sequons detected.",
        "callable_sha256": "d574294b1088dfb22b6f4242cc0c94b17de4999e86330e07620a83a0b4754c61"},
    _O: {"defaults": {"window": 7, "min_st_fraction": 0.4, "disallow_proline_next": True},
        "title": "# Heuristic O-glycosylation hotspot prediction (S/T density based)",
        "heading": "Top candidates:",
        "empty": "No candidate O-glycosylation hotspots met the heuristic threshold.",
        "callable_sha256": "dac5fa5bd182e0f7d4154ad72289c9adae173864e07e6392ae32d1e1102b2ca6"},
}
_NOTE = "Note: For state-of-the-art O-glycosite prediction, use NetOGlyc 4.0 (web service)."
_N_ROW = re.compile(r"- ([0-9]+): (.*)\Z")
_O_ROW = re.compile(r"- pos ([0-9]+) \((.*?)\): S/T fraction=([^ ]+) in window ([0-9]+)-([0-9]+)\Z")


def _issue(issues, code, field, **details):
    issues.append({"code": "glycosylation_" + code, "field": field, **details})


def _json(value, path=""):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for i, child in enumerate(value):
            _json(child, path + "/" + str(i))
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for key, child in value.items():
            _json(child, path + "/" + key.replace("~", "~0").replace("/", "~1"))
        return
    raise ValueError("glycosylation_finite_json_required:" + path)


def _finite_json(value):
    try:
        _json(value)
        json.dumps(value, allow_nan=False)
    except RecursionError as error:
        raise ValueError("glycosylation_finite_json_required:recursive_input") from error
    except (TypeError, ValueError, OverflowError) as error:
        if isinstance(error, ValueError) and str(error).startswith("glycosylation_finite_json_required:"):
            raise
        raise ValueError("glycosylation_finite_json_required:json_encoding") from error


def _parameters(operation, supplied, issues):
    defaults = _PROFILES[operation]["defaults"]
    requested = {key: deepcopy(supplied.get(key, value)) for key, value in defaults.items()}
    compatible = not (set(supplied) - set(defaults))
    for key in sorted(set(supplied) - set(defaults)):
        _issue(issues, "unknown_parameter", "/inputs/parameters/" + key)
    effective = deepcopy(requested)
    for key in ("allow_overlap",) if operation == _N else ("disallow_proline_next",):
        if type(requested[key]) is not bool:
            compatible = False
            effective[key] = None
            _issue(issues, "boolean_parameter_required", "/inputs/parameters/" + key)
    if operation == _O:
        if type(requested["window"]) is not int:
            compatible = False
            effective["window"] = None
            _issue(issues, "integer_window_required", "/inputs/parameters/window")
        elif requested["window"] < 3 or requested["window"] % 2 == 0:
            effective["window"] = 7
        if type(requested["min_st_fraction"]) not in (int, float):
            compatible = False
            effective["min_st_fraction"] = None
            _issue(issues, "numeric_threshold_required", "/inputs/parameters/min_st_fraction")
        elif not 0 <= requested["min_st_fraction"] <= 1:
            _issue(issues, "threshold_outside_documented_domain", "/inputs/parameters/min_st_fraction",
                meaning="finite supplied source arithmetic retained; native source performs no domain rejection")
    return {"supplied": deepcopy(supplied), "source_defaults": deepcopy(defaults),
        "defaulted_keys": [key for key in defaults if key not in supplied],
        "requested_with_defaults": requested, "effective": effective, "compatible": compatible}


def _number(token, issues, field):
    try:
        result = float(token)
    except ValueError:
        result = None
    if result is None or not math.isfinite(result):
        _issue(issues, "finite_native_number_required", field, native_token=token)
        return None
    return result


def _integer(token, issues, field):
    try:
        return int(token)
    except ValueError:
        _issue(issues, "native_integer_unrepresentable", field, native_token=token)
        return None


def _density(numerator, denominator):
    fraction = numerator / denominator if numerator is not None and denominator else None
    return fraction, None if fraction is None else round(fraction, 3)


def _parse(operation, log, issues):
    profile = _PROFILES[operation]
    lines, kinds, rows, metadata = [], [], [], []
    in_rows = False
    for line_index, line in enumerate([] if log is None else log.split("\n")):
        line_number = line_index + 1
        kind, values = "unknown", None
        if line == profile["title"]:
            kind = "title"
        elif line == "":
            kind = "blank"
        elif line == profile["heading"]:
            kind, in_rows = "heading", True
        elif line == profile["empty"]:
            kind = "empty"
        elif operation == _O and line == _NOTE:
            kind, in_rows = "note", False
        else:
            match = re.fullmatch(r"Sequence length: ([0-9]+)", line) if operation == _N else re.fullmatch(
                r"Sequence length: ([0-9]+) \| window=([0-9]+) \| threshold=(.+)", line)
            if match:
                kind = "sequence"
                values = {"sequence_length": _integer(match[1], issues, "/native/sequence_length")}
                if operation == _O:
                    values.update(window=_integer(match[2], issues, "/native/window"), threshold_token=match[3],
                        threshold=_number(match[3], issues, "/native/lines/" + str(line_index) + "/threshold"))
            else:
                match = re.fullmatch((r"Total sequons found: ([0-9]+)" if operation == _N else
                    r"Total candidate sites: ([0-9]+)"), line)
                if match:
                    kind, values = "total", {"total_count": _integer(match[1], issues, "/native/total_count")}
                else:
                    match = re.fullmatch(r"\.\.\. and ([0-9]+) more", line)
                    if match:
                        kind, values, in_rows = "remaining", {"remaining_count": _integer(match[1], issues, "/native/remaining_count")}, False
                    elif line.startswith("- ") or in_rows:
                        kind = "row"
                        rows.append({"row_ordinal": len(rows), "line_number": line_number,
                            "native_line": line})
        if values is not None:
            metadata.append({"kind": kind, "line_number": line_number, "native_line": line, "values": values})
        if kind == "unknown":
            _issue(issues, "unrecognized_log_line", "/native/lines/" + str(line_index))
        lines.append(line)
        kinds.append(kind)
    selected = {}
    for kind in ("sequence", "total", "remaining"):
        matches = [row for row in metadata if row["kind"] == kind]
        selected[kind] = matches[0]["values"] if len(matches) == 1 else None
        if len(matches) > 1:
            _issue(issues, "duplicate_native_metadata", "/native/" + kind)
    return {"lines": lines, "line_kinds": kinds, "metadata_occurrences": metadata,
        "selected_metadata": selected}, rows


def _mapping(sequence, processed, supplied, issues):
    result = {"supplied": deepcopy(supplied), "available": False,
        "reason": "not_supplied", "normalization_preserves_positions": None}
    if sequence is None:
        result["reason"] = "original_operand_unknown"
        return result
    one_to_one = all(len(character.upper()) == 1 for character in sequence) and len(sequence) == len(processed)
    result["normalization_preserves_positions"] = one_to_one
    if supplied is None:
        return result
    try:
        validate_mapping(supplied)
        if supplied["symbol_length"] != len(sequence):
            raise ValueError("mapping_length_conflicts_with_original_input")
    except (ValueError, TypeError, KeyError) as error:
        result["reason"] = "invalid_supplied_mapping"
        _issue(issues, "invalid_supplied_mapping", "/inputs/input_mapping", cause=str(error))
        return result
    if not one_to_one:
        result["reason"] = "unicode_uppercase_expansion"
        _issue(issues, "normalization_mapping_unavailable", "/inputs/sequence")
        return result
    result.update(available=True, reason=None)
    return result


def _project(mapping, interval):
    return map_interval(mapping["supplied"], *interval) if mapping["available"] and interval is not None else None


def _row(operation, row, processed, operand_known, parameter, mapping, previous):
    result = {**row, "native_values": None, "cells": {}, "issues": [], "source_compatible": False}
    issues, cells = result["issues"], result["cells"]
    field = "/rows/" + str(row["row_ordinal"])
    match = (_N_ROW if operation == _N else _O_ROW).fullmatch(row["native_line"])
    if match is None:
        _issue(issues, "malformed_native_site_row", field + "/native_line")
        return result, None
    position = _integer(match[1], issues, field + "/native_values/position_1based")
    values = {"position_1based": position}
    if operation == _N:
        values["motif"] = match[2]
    else:
        values.update(residue=match[2], st_fraction_token=match[3],
            st_fraction=_number(match[3], issues, field + "/native_values/st_fraction"),
            window_start_1based=_integer(match[4], issues, field + "/native_values/window_start_1based"),
            window_end_1based=_integer(match[5], issues, field + "/native_values/window_end_1based"))
    result["native_values"] = values
    size = 3 if operation == _N else 1
    interval = [position - 1, position - 1 + size] if position is not None and position > 0 else None
    if interval is None or operand_known and interval[1] > len(processed):
        _issue(issues, "site_interval_outside_operand", field + "/native_values/position_1based")
        interval = None
    cells["processed_interval"] = interval
    cells["source_intervals"] = _project(mapping, interval)
    actual = processed[interval[0]:interval[1]] if operand_known and interval is not None else None
    cells["operand_symbols"] = actual
    step = (1 if parameter["effective"]["allow_overlap"] else 3) if operation == _N and parameter["effective"]["allow_overlap"] is not None else 1 if operation == _O else None
    order = True if row["row_ordinal"] == 0 else position - previous >= step if position is not None and previous is not None and step is not None else None
    cells["order_compatible"] = order
    if order is not True:
        _issue(issues, "native_site_order_or_overlap_conflict" if order is False else "native_site_order_unknown", field)
    if operation == _N:
        cells["printed_symbols_match_operand"] = None if actual is None else values["motif"] == actual
        cells["literal_sequon"] = None if actual is None else len(actual) == 3 and actual[0] == "N" and actual[1] != "P" and actual[2] in {"S", "T"}
        checks = [cells["printed_symbols_match_operand"], cells["literal_sequon"]]
    else:
        native_window = ([values["window_start_1based"] - 1, values["window_end_1based"]]
            if values["window_start_1based"] is not None and values["window_end_1based"] is not None else None)
        if native_window is None or not 0 <= native_window[0] < native_window[1] or operand_known and native_window[1] > len(processed):
            _issue(issues, "native_window_outside_operand", field + "/native_values/window")
            native_window = None
        effective = parameter["effective"]
        window = effective["window"]
        expected = ([max(0, position - 1 - window // 2), min(len(processed), position + window // 2)]
            if operand_known and interval is not None and window is not None else None)
        segment = processed[native_window[0]:native_window[1]] if operand_known and native_window is not None else None
        counts = None if segment is None else build_sequence_composition_sheet(segment, molecule="protein")["symbol_counts"]
        numerator = None if counts is None else counts.get("S", 0) + counts.get("T", 0)
        denominator = len(segment) if segment is not None else None
        fraction, rounded = _density(numerator, denominator)
        following_p = (position < len(processed) and processed[position] == "P") if operand_known and interval is not None else None
        threshold = effective["min_st_fraction"]
        above = fraction >= threshold if fraction is not None and threshold is not None else None
        allowed = not (effective["disallow_proline_next"] and following_p) if following_p is not None and effective["disallow_proline_next"] is not None else None
        cells.update(native_window_interval=native_window, expected_clipped_window_interval=expected,
            window_source_intervals=_project(mapping, native_window), window_symbols=segment,
            window_symbol_counts=counts, st_count=numerator, window_denominator_symbols=denominator,
            printed_symbols_match_operand=None if actual is None else values["residue"] == actual,
            st_center=None if actual is None else actual in {"S", "T"},
            window_matches_source_clipping=None if expected is None or native_window is None else native_window == expected,
            following_proline=following_p, following_proline_allowed=allowed,
            unrounded_threshold_satisfied=above,
            printed_fraction_matches_calculation=None if fraction is None or values["st_fraction"] is None else values["st_fraction"] == rounded)
        checks = [cells[key] for key in ("printed_symbols_match_operand", "st_center",
            "window_matches_source_clipping", "following_proline_allowed", "unrounded_threshold_satisfied",
            "printed_fraction_matches_calculation")]
    if any(check is False for check in checks):
        _issue(issues, "native_site_conflicts_with_operand_or_source_rule", field + "/cells")
    if any(check is None for check in checks):
        _issue(issues, "site_checks_unavailable", field + "/cells")
    result["source_compatible"] = parameter["compatible"] and order is True and all(check is True for check in checks)
    return result, position


def build_glycosylation_sheet(operation: str, native_log: str | None, *, sequence: str | None,
        parameters: dict, native_outcome: str = "completed", input_ref: str | None = None,
        input_mapping: dict | None = None) -> dict:
    """Retain complete supplied logs/operands and extract only printed rows.

    Unsupported finite parameter values remain inspectable partial input. Null
    original operand remains unknown, separately from the source's null-to-empty
    normalization behavior. No execution, byte custody or exhaustive scan is
    established by selecting this profile or supplying a completed outcome.
    """
    if type(operation) is not str or operation not in _PROFILES:
        raise ValueError("glycosylation_operation_required")
    if native_log is not None and type(native_log) is not str:
        raise ValueError("glycosylation_native_log_string_or_null_required")
    if sequence is not None and type(sequence) is not str:
        raise ValueError("glycosylation_sequence_string_or_null_required")
    if type(parameters) is not dict:
        raise ValueError("glycosylation_parameters_object_required")
    if native_outcome not in ("completed", "partial", "failed"):
        raise ValueError("glycosylation_native_outcome_required")
    if input_ref is not None and (type(input_ref) is not str or not input_ref):
        raise ValueError("glycosylation_input_reference_or_null_required")
    inputs = dict(operation=operation, native_log=native_log, sequence=sequence,
        parameters=parameters, native_outcome=native_outcome, input_ref=input_ref, input_mapping=input_mapping)
    _finite_json(inputs)
    inputs = deepcopy(inputs)
    issues = []
    profile = _PROFILES[operation]
    parameter = _parameters(operation, parameters, issues)
    processed = (sequence or "").upper()
    composition = None if sequence is None else build_sequence_composition_sheet(sequence, molecule="protein")
    if sequence is None:
        _issue(issues, "original_operand_unknown", "/inputs/sequence")
    elif composition["status"] != "complete":
        _issue(issues, "supplied_protein_has_noncanonical_symbols", "/inputs/sequence",
            meaning="literal source rules retained; no biological alphabet repair")
    mapping = _mapping(sequence, processed, input_mapping, issues)
    native, retained_rows = _parse(operation, native_log, issues)
    rows, previous = [], None
    for retained in retained_rows:
        row, previous = _row(operation, retained, processed, sequence is not None, parameter, mapping, previous)
        rows.append(row)
    selected = native["selected_metadata"]
    total = None if selected["total"] is None else selected["total"]["total_count"]
    remaining = None if selected["remaining"] is None else selected["remaining"]["remaining_count"]
    metadata_matches = None
    if selected["sequence"] is not None and sequence is not None:
        metadata_matches = selected["sequence"]["sequence_length"] == len(processed)
        if operation == _O:
            metadata_matches = metadata_matches and parameter["compatible"] and selected["sequence"]["window"] == parameter["effective"]["window"] and selected["sequence"]["threshold"] == parameter["effective"]["min_st_fraction"]
    if metadata_matches is False:
        _issue(issues, "native_header_conflicts_with_operand_or_parameters", "/native/selected_metadata/sequence")
    expected = ["title", "sequence", "total"]
    if total is not None:
        expected += (["blank", "heading", *(["row"] * len(rows))] if total else ["empty"])
        if total > 100:
            expected.append("remaining")
        if operation == _O:
            expected += ["blank", "note"]
    count_matches = total is not None and len(rows) == min(total, 100) and (remaining == total - 100 if total > 100 else remaining is None)
    upper_bound = None
    if sequence is not None:
        if operation == _N and parameter["effective"]["allow_overlap"] is not None:
            upper_bound = max(0, len(processed) - 2) if parameter["effective"]["allow_overlap"] else len(processed) // 3
        elif operation == _O:
            processed_counts = build_sequence_composition_sheet(processed, molecule="protein")["symbol_counts"]
            upper_bound = processed_counts.get("S", 0) + processed_counts.get("T", 0)
    bound_matches = None if upper_bound is None or total is None else total <= upper_bound
    if bound_matches is False:
        _issue(issues, "native_total_exceeds_operand_upper_bound", "/native/selected_metadata/total")
    layout_matches = total is not None and native["line_kinds"] == expected
    if native_log is None:
        _issue(issues, "native_log_missing", "/inputs/native_log")
    if not count_matches or not layout_matches:
        _issue(issues, "native_log_layout_or_count_incomplete", "/native")
    usable = sum(row["source_compatible"] for row in rows)
    # These flags qualify retained source-format rows only, never transport
    # byte completeness, an executed invocation, or biological detectability.
    log_complete = (native_outcome == "completed" and parameter["compatible"] and metadata_matches is True
        and count_matches and layout_matches and bound_matches is True and usable == len(rows))
    report_complete = log_complete and total == usable
    if native_outcome != "completed":
        _issue(issues, "native_outcome_incomplete", "/inputs/native_outcome")
    return {"schema": SHEET_SCHEMA, "inputs": inputs,
        "source_profile": {"module_sha256": SOURCE_SHA256, "callable": operation,
            "callable_sha256": profile["callable_sha256"], "identity_kind": "declared_source_profile_not_observed_execution"},
        "parameters": parameter, "source_normalization": {"expression": "(sequence or '').upper()",
            "processed_sequence": processed, "original_operand_known": sequence is not None,
            "original_symbol_count": None if sequence is None else len(sequence),
            "processed_symbol_count": len(processed)},
        "supplied_protein_composition_sheet": composition, "mapping": mapping,
        "native": native, "rows": rows,
        "completeness": {"native_log_complete": log_complete, "native_report_complete": report_complete,
            "scan_exhaustiveness_verified": False, "source_profile_layout_compatible": layout_matches,
            "native_count_rows_compatible": count_matches, "native_metadata_matches_operands": metadata_matches,
            "native_total_operand_upper_bound": upper_bound, "native_total_within_operand_upper_bound": bound_matches},
        "status": "failed" if native_outcome == "failed" else "partial" if issues or any(row["issues"] for row in rows) or not report_complete else "complete",
        "issues": issues}


def _difference(left, right, path=""):
    if type(left) is not type(right):
        return path
    if type(left) is dict:
        if left.keys() != right.keys():
            return path
        for key in left:
            found = _difference(left[key], right[key], path + "/" + key)
            if found is not None:
                return found
        return None
    if type(left) is list:
        if len(left) != len(right):
            return path
        for i, (a, b) in enumerate(zip(left, right)):
            found = _difference(a, b, path + "/" + str(i))
            if found is not None:
                return found
        return None
    return None if left == right else path


def _definitions():
    return {
        "population": "actual retained printed native row occurrences in original log order, including malformed and duplicate rows; never unprinted sites",
        "source_profile": "declared original literal source behavior; no execution, transport, accession, scientific confidence or occupancy authentication",
        "original_symbol_count": "len(actual supplied string); supplied symbols; null for unknown original operand",
        "processed_symbol_count": "len((sequence or '').upper()); source-processed symbols; original null behavior remains distinct from supplied empty string",
        "native_metadata": "sequence length, effective window, threshold, total and remaining counts are direct parsed source log assertions; null if missing/duplicate/unusable; raw tokens and occurrences retained",
        "native_reported_sequence_length": "native Sequence length header; source-processed symbols; null for missing/duplicate/unrepresentable header; separately compared with the supplied processed string",
        "native_reported_total_count": "native total header; source-reported site occurrences, including unprinted rows; null for missing/duplicate/unrepresentable total, never replaced by the retained row count",
        "native_reported_remaining_count": "native '... and N more' assertion; source-reported unprinted site rows; null when absent, including uncapped complete logs",
        "parameters": "supplied values, source-declared defaults and effective values remain separate; integer window<3 or even gives source fallback7; incompatible selector types unknown rather than arbitrary truthiness",
        "parameter_units": "window: source-processed symbols, odd integer after source fallback; min_st_fraction and parsed threshold: dimensionless S/T fraction, with finite out-of-[0,1] supplied arithmetic retained and qualified",
        "row_ordinal": "zero-based ordinal among retained site-row occurrences; malformed/duplicate rows count",
        "line_number": "one-based line ordinal in exact supplied log split on newline",
        "position_1based": "native printed source-processed symbol position; zero/invalid interval remains unusable",
        "processed_interval": "[native position-1,position-1+3) for N motif or [position-1,position) for O center; zero-based source-processed symbols, not inferred original genome coordinates",
        "source_intervals": "sequence_mapping.map_interval of explicitly supplied validated mapping only when original uppercase is position preserving; original physical units/strand/order retained; otherwise null",
        "literal_sequon": "shown operand triplet starts N, middle literal symbol!=P, last S/T; source accepts noncanonical middle symbols; no glycosylation observation",
        "order_compatible": "strictly increasing native printed positions; N default requires delta>=3, overlap requires delta>=1; O delta>=1; unknown after unparsed previous row or incompatible overlap setting",
        "window_intervals": "native 1-based inclusive printed window [a,b] becomes [a-1,b); expected source clipping is [max(0,p-1-floor(w/2)),min(L,p+floor(w/2)))",
        "native_st_fraction": "finite parsed native display value, dimensionless and already rounded by the source; raw token retained; conflict never overwritten by the calculated full-precision fraction",
        "window_symbol_counts": "shared declared-protein count authority applied to actual reported-window operand symbols; no smoothing or unseen windows",
        "st_count": "saved shared window counts['S']+counts['T']; source-processed S/T symbols in this retained reported window; null when operand/window unavailable",
        "window_denominator_symbols": "len(actual clipped reported-window segment); source-processed symbols; no full-window denominator substitution",
        "calculated_st_fraction": "st_count/window_denominator_symbols, full precision; dimensionless; null for unavailable numerator or zero/missing denominator",
        "source_rounded_st_fraction": "round(calculated_st_fraction,3), source Python rounding; separate from native printed fraction and full precision comparison",
        "threshold_and_proline": "compare unrounded reported-window fraction>=effective supplied threshold; separately require actual S/T center, correct source clipping and optional immediate-next-P exclusion",
        "retained_printed_row_count": "len(actual retained row occurrences); rows; null when no native log was supplied, zero for a supplied log with no site rows",
        "usable_checked_row_count": "count with compatible shown position/symbols/ordering/parameters and every source rule check true; rows; not a confidence score",
        "malformed_row_count": "count retained rows with no parsed native values; rows; null for absent log",
        "unretained_reported_row_count": "native total-len(retained printed rows) if both known and difference>=0; source-reported rows, not inferred positions; null for conflict or unavailable total/log",
        "native_total_operand_upper_bound": "N: max(0,L-2) for overlap, floor(L/3) for nonoverlap; O: shared whole-processed-string S+T counts; rows; upper bound only, never a scan or inferred exact total; null for unknown operand or required parameter",
        "native_log_complete": "supplied completed outcome and source-profile structural/header/count/retained-row validation; does not independently certify transport bytes or invocation",
        "native_report_complete": "native_log_complete and native total==usable retained row count; false for capped>100 reports or unavailable checks",
        "scan_exhaustiveness_verified": "always false; only supplied rows checked, no absent site enumerated",
        "missingness": "native totals/rows and independently available arithmetic stay separate; failed/partial outcomes cannot become complete; malformed native input is retained with specific issues; corrupt saved sheets raise specific conflicts without repair",
        "uncertainty": "no experimental, calibration, occupancy or uncertainty interval supplied or invented",
    }


def calculate_glycosylation_components(sheet: dict) -> dict:
    """Validate saved associations and calculate retained-row components only.

    Re-reading the supplied literal log is pure and does not execute the source
    scan. Corrupt saved projections are rejected, never repaired in place.
    """
    _finite_json(sheet)
    if type(sheet) is not dict or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("glycosylation_sheet_required")
    inputs = sheet.get("inputs")
    if type(inputs) is not dict or set(inputs) != {"operation", "native_log", "sequence", "parameters", "native_outcome", "input_ref", "input_mapping"}:
        raise ValueError("glycosylation_saved_inputs_required")
    expected = build_glycosylation_sheet(**inputs)
    conflict = _difference(expected, sheet)
    if conflict is not None:
        raise ValueError("glycosylation_saved_sheet_conflict:" + conflict)
    result_rows = []
    for row in sheet["rows"]:
        cells = deepcopy(row["cells"])
        if sheet["inputs"]["operation"] == _O and row["native_values"] is not None:
            numerator, denominator = cells["st_count"], cells["window_denominator_symbols"]
            fraction, rounded = _density(numerator, denominator)
            cells.update(calculated_st_fraction=fraction,
                source_rounded_st_fraction=rounded)
        result_rows.append({**deepcopy(row), "cells": cells})
    selected = sheet["native"]["selected_metadata"]
    total = None if selected["total"] is None else selected["total"]["total_count"]
    retained = len(result_rows) if inputs["native_log"] is not None else None
    return {"schema": COMPONENTS_SCHEMA, "operation": inputs["operation"], "status": sheet["status"],
        "parameters": deepcopy(sheet["parameters"]), "rows": result_rows,
        "supplied_protein_composition": None if sheet["supplied_protein_composition_sheet"] is None else
            calculate_sequence_composition_scores(sheet["supplied_protein_composition_sheet"]),
        "summary": {"original_symbol_count": sheet["source_normalization"]["original_symbol_count"],
            "processed_symbol_count": sheet["source_normalization"]["processed_symbol_count"],
            "native_reported_sequence_length": None if selected["sequence"] is None else selected["sequence"]["sequence_length"],
            "native_reported_total_count": total, "retained_printed_row_count": retained,
            "usable_checked_row_count": sum(row["source_compatible"] for row in result_rows) if retained is not None else None,
            "malformed_row_count": sum(row["native_values"] is None for row in result_rows) if retained is not None else None,
            "native_reported_remaining_count": None if selected["remaining"] is None else selected["remaining"]["remaining_count"],
            "unretained_reported_row_count": total - retained if total is not None and retained is not None and total >= retained else None,
            **deepcopy(sheet["completeness"])},
        "definitions": _definitions(), "issues": deepcopy(sheet["issues"])}


__all__ = ["SHEET_SCHEMA", "COMPONENTS_SCHEMA", "build_glycosylation_sheet", "calculate_glycosylation_components"]
