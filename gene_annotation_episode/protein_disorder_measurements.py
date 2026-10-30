"""Source-faithful IUPred2A postprocessing of explicitly supplied outputs.

This executes no predictor or service. A declared source profile and supplied
completed outcome are not execution/transport receipts. Native row-occurrence
arithmetic, descriptive means and unique input coverage have separate meanings.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import csv
import io
import json
import math
import re

from .sequence_composition_grader import build_sequence_composition_sheet, calculate_sequence_composition_scores
from .sequence_mapping import validate_mapping, map_interval


SHEET_SCHEMA = "protein_disorder_sheet_v1"
COMPONENTS_SCHEMA = "protein_disorder_components_v1"
SOURCE_SHA256 = "7eb57d570d516ab22c089f0ff22141d3bb4f0fa73875208f32bcf375a0cb4127"
CALLABLE_SHA256 = "2e48ec328127e36a5fbc1b7cf30b93b931baad674c12a3fb63f69457be64c260"
_HEADER = ["Position", "Amino_Acid", "Disorder_Score", "Is_Disordered"]
_NO_DATA = "No valid prediction data was returned from the server."
_ASCII = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
_CANONICAL = frozenset("ACDEFGHIKLMNPQRSTVWY")


def _issue(issues, code, field, **details):
    issues.append({"code": "protein_disorder_" + code, "field": field, **details})


def _finite_json(value):
    def check(item, path):
        if item is None or type(item) in (str, int, bool):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for i, child in enumerate(item):
                check(child, path + "/" + str(i))
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for key, child in item.items():
                check(child, path + "/" + key.replace("~", "~0").replace("/", "~1"))
            return
        raise ValueError("protein_disorder_finite_json_required:" + path)
    try:
        check(value, "")
        json.dumps(value, allow_nan=False)
    except RecursionError as error:
        raise ValueError("protein_disorder_finite_json_required:recursive_input") from error
    except (ValueError, TypeError, OverflowError) as error:
        if isinstance(error, ValueError) and str(error).startswith("protein_disorder_finite_json_required:"):
            raise
        raise ValueError("protein_disorder_finite_json_required:json_encoding") from error


def _score(token):
    try:
        value = float(token)
    except (ValueError, OverflowError):
        return {"token": token, "kind": "unparseable", "finite_value": None}
    kind = "nan" if math.isnan(value) else "positive_infinity" if value == math.inf else "negative_infinity" if value == -math.inf else "finite"
    return {"token": token, "kind": kind, "finite_value": value if kind == "finite" else None}


def _parse_values(tokens, issues, field):
    if len(tokens) < 3:
        _issue(issues, "native_row_requires_three_tokens", field)
        return None
    try:
        position = int(tokens[0])
    except ValueError:
        position = None
        _issue(issues, "native_position_not_integer", field + "/position", token=tokens[0])
    score = _score(tokens[2])
    if score["kind"] == "unparseable":
        _issue(issues, "native_score_not_float", field + "/score", token=tokens[2])
    return {"position_token": tokens[0], "position_1based": position,
        "residue_token": tokens[1], "score": score}


def _accepted(values):
    return values is not None and values["position_1based"] is not None and values["score"]["kind"] != "unparseable"


def _response(text):
    lines, rows = [], []
    for ordinal, line in enumerate([] if text is None else text.split("\n")):
        kind = "comment" if line.startswith("#") else "blank" if not line.strip() else "data"
        record = {"line_ordinal": ordinal, "native_line": line, "kind": kind, "tokens": line.split()}
        if kind == "data":
            issues = []
            row = {"row_ordinal": len(rows), "line_start_1based": ordinal + 1,
                "line_end_1based": ordinal + 1, "raw_record": line,
                "raw_tokens": record["tokens"], "native_values": None, "native_csv_flag": None, "issues": issues}
            row["native_values"] = _parse_values(record["tokens"], issues, "/response/rows/" + str(len(rows)))
            row["source_parse_accepted"] = _accepted(row["native_values"])
            record["row_ordinal"] = len(rows)
            rows.append(row)
        lines.append(record)
    return {"supplied": text is not None, "population_available": text is not None,
        "lines": lines, "rows": rows, "parser_tail_complete": text is not None}


def _csv(text):
    result = {"supplied": text is not None, "header": None, "header_compatible": None,
        "population_available": False, "parser_tail_complete": text is not None, "rows": [], "issues": []}
    if text is None:
        return result
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    physical = io.StringIO(text, newline="").readlines()
    previous = 0
    try:
        result["header"] = next(reader, None)
        result["header_compatible"] = result["header"] == _HEADER
        result["population_available"] = result["header_compatible"]
        previous = reader.line_num
        while True:
            fields = next(reader, None)
            if fields is None:
                break
            index, issues = len(result["rows"]), []
            row = {"row_ordinal": index, "line_start_1based": previous + 1,
                "line_end_1based": reader.line_num, "raw_record": "".join(physical[previous:reader.line_num]),
                "raw_tokens": fields, "native_values": None,
                "native_csv_flag": fields[3] if len(fields) == 4 else None, "issues": issues}
            if len(fields) == 4 and result["header_compatible"]:
                row["native_values"] = _parse_values(fields, issues, "/csv/rows/" + str(index))
                residue = fields[1]
                if not residue or len(residue.split()) != 1 or residue.split()[0] != residue:
                    _issue(issues, "csv_residue_cannot_be_original_response_token", "/csv/rows/" + str(index))
                    row["source_parse_accepted"] = False
                else:
                    row["source_parse_accepted"] = _accepted(row["native_values"])
            else:
                _issue(issues, "csv_header_or_field_count_incompatible", "/csv/rows/" + str(index))
                row["source_parse_accepted"] = False
            if row["native_csv_flag"] not in ("Yes", "No"):
                _issue(issues, "csv_disorder_flag_not_yes_no", "/csv/rows/" + str(index))
            result["rows"].append(row)
            previous = reader.line_num
    except csv.Error as error:
        result["parser_tail_complete"] = False
        _issue(result["issues"], "csv_parse_failed", "/csv", message=str(error))
        result["rows"].append({"row_ordinal": len(result["rows"]), "line_start_1based": previous + 1,
            "line_end_1based": max(reader.line_num, previous + 1), "raw_record": "".join(physical[previous:]),
            "raw_tokens": None, "native_values": None, "native_csv_flag": None,
            "source_parse_accepted": False, "issues": [{"code": "protein_disorder_csv_unparsed_tail", "field": "/csv"}]})
    if not result["header_compatible"]:
        _issue(result["issues"], "csv_header_required", "/csv/header")
    return result


def _same_native(left, right):
    if not _accepted(left) or not _accepted(right):
        return False
    return (left["position_1based"] == right["position_1based"]
        and left["residue_token"] == right["residue_token"]
        and left["score"]["kind"] == right["score"]["kind"]
        and left["score"]["finite_value"] == right["score"]["finite_value"])


def _comparison(score, threshold):
    if threshold is None or score["kind"] == "unparseable":
        return None
    if score["kind"] == "finite":
        return score["finite_value"] >= threshold
    return score["kind"] == "positive_infinity"  # Native NaN and -inf compare false.


def _log(text):
    result = {"supplied": text is not None, "kind": "missing", "occurrences": [], "regions": [],
        "selected": {}, "unrecognized_lines": [], "no_regions_marker_count": None, "issues": []}
    if text is None:
        return result
    result["kind"] = "no_valid_data" if text == _NO_DATA else "request_error" if text.startswith("Error accessing IUPred2A server: ") else "summary"
    patterns = {
        "parsed_count": r"Protein sequence length: ([0-9]+) amino acids",
        "threshold": r"Disorder threshold: (.+)",
        "disordered": r"- ([0-9]+) residues \(([^ ]+)%\) predicted as disordered",
        "region_count": r"- ([0-9]+) distinct disordered regions identified",
    }
    constants = {"", "Intrinsically Disordered Region (IDR) Prediction Research Log:",
        "=============================================================",
        "Analysis performed using IUPred2A algorithm (long disorder mode)",
        "Results Summary:", "Disordered Regions:", "- No significant disordered regions found", _NO_DATA}
    result["no_regions_marker_count"] = text.split("\n").count("- No significant disordered regions found")

    def integer(token, field):
        try:
            return int(token)
        except ValueError:
            _issue(result["issues"], "native_log_integer_unrepresentable", field, native_token=token)
            return None

    for ordinal, line in enumerate(text.split("\n")):
        recognized = line in constants or line.startswith("Detailed per-residue scores saved to: ")
        for kind, pattern in patterns.items():
            match = re.fullmatch(pattern, line)
            if match:
                recognized = True
                values = {"threshold": _score(match[1])} if kind == "threshold" else {
                    "count": integer(match[1], "/log/" + kind), **({"percentage": _score(match[2])} if kind == "disordered" else {})}
                result["occurrences"].append({"kind": kind, "line_ordinal": ordinal, "native_line": line, "values": values})
        match = re.fullmatch(r"- Region (-?[0-9]+)-(-?[0-9]+) \(length: (-?[0-9]+) residues\)", line)
        if match:
            recognized = True
            result["regions"].append({"row_ordinal": len(result["regions"]), "line_ordinal": ordinal,
                "native_line": line, "start_1based": integer(match[1], "/log/region/start"),
                "end_1based": integer(match[2], "/log/region/end"), "length_residues": integer(match[3], "/log/region/length")})
        if not recognized:
            result["unrecognized_lines"].append({"line_ordinal": ordinal, "native_line": line})
    for kind in patterns:
        matches = [row for row in result["occurrences"] if row["kind"] == kind]
        result["selected"][kind] = matches[0]["values"] if len(matches) == 1 else None
        if len(matches) > 1:
            _issue(result["issues"], "duplicate_log_field", "/log/" + kind)
    result["summary_structure_present"] = not result["unrecognized_lines"] and all(value is not None for value in result["selected"].values()) and all(
        value in text for value in ("Intrinsically Disordered Region (IDR) Prediction Research Log:",
            "Analysis performed using IUPred2A algorithm (long disorder mode)", "Results Summary:",
            "Disordered Regions:", "Detailed per-residue scores saved to: "))
    return result


def _source_arithmetic(rows, available, threshold, stop_reason, *, csv_incomplete=False):
    accepted = [row for row in rows if row["source_parse_accepted"]]
    count = len(accepted) if available else None
    stage = "population_unknown" if not available else "early_no_parsed_rows" if not accepted else "source_request_error" if stop_reason == "request_error" else "log_early_return_conflict" if stop_reason == "no_valid_data" else "threshold_unknown" if threshold is None else "source_equivalent_postprocessing"
    result = {"stage": stage, "parsed_row_denominator": count, "thresholded_row_count": None,
        "disordered_percentage": None, "expected_percentage_display": None, "regions": None, "region_count": None}
    if stage != "source_equivalent_postprocessing":
        return result
    hits = sum(row["cells"]["native_threshold_comparison"] is True for row in accepted)
    percentage = (hits / count) * 100
    if csv_incomplete:
        result.update(stage="retained_partial_csv_arithmetic", thresholded_row_count=hits,
            disordered_percentage=percentage, expected_percentage_display=format(percentage, ".2f"))
        return result
    runs, current = [], []

    def retain():
        if len(current) > 1:
            start, end = current[0]["native_values"]["position_1based"], current[-1]["native_values"]["position_1based"]
            corresponding = all(row["cells"]["input_correspondence"] is True for row in current)
            mapped = corresponding and all(row["cells"]["source_intervals"] is not None for row in current)
            runs.append({"region_ordinal": len(runs), "start_1based": start, "end_1based": end,
                "length_residues": end - start + 1, "member_row_ordinals": [row["row_ordinal"] for row in current],
                "all_members_correspond_to_input": corresponding,
                "all_members_usable_for_descriptive_mean": all(row["cells"]["usable_for_descriptive_mean"] for row in current),
                "cleaned_interval": [start - 1, end] if corresponding else None,
                "original_character_intervals": [row["cells"]["original_character_interval"] for row in current] if corresponding else None,
                "source_intervals": [span for row in current for span in row["cells"]["source_intervals"]] if mapped else None})

    for row in accepted:
        position = row["native_values"]["position_1based"]
        if row["cells"]["native_threshold_comparison"]:
            if current and position != current[-1]["native_values"]["position_1based"] + 1:
                retain()
                current = []
            current.append(row)
        else:
            retain()
            current = []
    retain()
    result.update(thresholded_row_count=hits, disordered_percentage=percentage,
        expected_percentage_display=format(percentage, ".2f"), regions=runs, region_count=len(runs))
    return result


def _difference(a, b, path=""):
    if type(a) is not type(b):
        return path
    if type(a) is dict:
        if a.keys() != b.keys():
            return path
        pairs = ((a[key], b[key], path + "/" + key) for key in a)
    elif type(a) is list:
        if len(a) != len(b):
            return path
        pairs = ((x, y, path + "/" + str(i)) for i, (x, y) in enumerate(zip(a, b)))
    else:
        return None if a == b else path
    for x, y, child in pairs:
        found = _difference(x, y, child)
        if found is not None:
            return found
    return None


def build_disorder_sheet(native_csv: str | None, *, protein_sequence: str | None,
        threshold: float | int | None, native_response: str | None = None,
        native_log: str | None = None, native_outcome: str = "completed",
        input_ref: str | None = None, input_mapping: dict | None = None) -> dict:
    """Retain all supplied views; response-first source parsing never fills gaps.

    Threshold None and input None are unknown, never source defaults. CSV-only
    calculations concern the retained CSV population, not unseen response rows.
    Scientific score values for nonfinite tokens remain null; their source float
    comparison behavior is separately represented without nonfinite JSON.
    """
    for name, value in (("native_csv", native_csv), ("protein_sequence", protein_sequence),
            ("native_response", native_response), ("native_log", native_log)):
        if value is not None and type(value) is not str:
            raise ValueError("protein_disorder_string_or_null_required:" + name)
    if threshold is not None and type(threshold) not in (int, float):
        raise ValueError("protein_disorder_numeric_threshold_or_null_required")
    if native_outcome not in ("completed", "partial", "failed"):
        raise ValueError("protein_disorder_native_outcome_required")
    if input_ref is not None and (type(input_ref) is not str or not input_ref):
        raise ValueError("protein_disorder_input_reference_or_null_required")
    inputs = dict(native_csv=native_csv, protein_sequence=protein_sequence, threshold=threshold,
        native_response=native_response, native_log=native_log, native_outcome=native_outcome,
        input_ref=input_ref, input_mapping=input_mapping)
    _finite_json(inputs)
    issues = []
    indices = None if protein_sequence is None else [i for i, character in enumerate(protein_sequence) if character in _ASCII]
    cleaned = None if indices is None else "".join(protein_sequence[i] for i in indices)
    original_composition = None if protein_sequence is None else build_sequence_composition_sheet(protein_sequence, molecule="protein")
    cleaned_composition = None if cleaned is None else build_sequence_composition_sheet(cleaned, molecule="protein")
    if cleaned is None:
        _issue(issues, "original_input_unknown", "/inputs/protein_sequence")
    elif set(cleaned.upper()) - _CANONICAL:
        _issue(issues, "predictor_domain_unestablished", "/inputs/protein_sequence",
            meaning="ambiguous/noncanonical ASCII letters retain descriptive computability, not model accuracy")
    if indices is not None and len(indices) != len(protein_sequence):
        _issue(issues, "source_cleaning_removed_characters", "/cleaning")
    if threshold is None:
        _issue(issues, "threshold_unknown", "/inputs/threshold")
    elif not 0 <= threshold <= 1:
        _issue(issues, "threshold_outside_documented_domain", "/inputs/threshold")
    mapping = {"supplied": deepcopy(input_mapping), "available": False, "reason": "not_supplied"}
    if input_mapping is not None and protein_sequence is not None:
        try:
            validate_mapping(input_mapping)
            if input_mapping["symbol_length"] != len(protein_sequence):
                raise ValueError("mapping_length_conflicts_with_original_string")
            mapping.update(available=True, reason=None)
        except (ValueError, TypeError, KeyError) as error:
            mapping["reason"] = "invalid_supplied_mapping"
            _issue(issues, "invalid_supplied_mapping", "/inputs/input_mapping", cause=str(error))
    elif input_mapping is not None:
        mapping["reason"] = "original_input_unknown"
    response, table, log = _response(native_response), _csv(native_csv), _log(native_log)
    authority = "response" if native_response is not None else "csv" if native_csv is not None else None
    selected = response if authority == "response" else table if authority == "csv" else {"rows": [], "population_available": False}
    rows = deepcopy(selected["rows"])
    accepted_rows = [row for row in rows if row["source_parse_accepted"]]
    accepted_index = {row["row_ordinal"]: i for i, row in enumerate(accepted_rows)}
    positions = Counter(row["native_values"]["position_1based"] for row in accepted_rows)
    values_by_position = {}
    for row in accepted_rows:
        values = row["native_values"]
        values_by_position.setdefault(values["position_1based"], set()).add((values["residue_token"], values["score"]["kind"], values["score"]["finite_value"]))
    join = {"state": "not_supplied", "rows": [], "counts_match": None}
    if native_response is not None and native_csv is not None:
        join["counts_match"] = len(accepted_rows) == len(table["rows"])
        for i, row in enumerate(accepted_rows):
            other = table["rows"][i] if i < len(table["rows"]) else None
            compatible = other is not None and _same_native(row["native_values"], other["native_values"])
            join["rows"].append({"response_row_ordinal": row["row_ordinal"], "csv_row_ordinal": None if other is None else other["row_ordinal"], "compatible": compatible})
        join["state"] = "compatible" if table["header_compatible"] and table["parser_tail_complete"] and join["counts_match"] and all(row["compatible"] for row in join["rows"]) else "conflict"
        if join["state"] == "conflict":
            _issue(issues, "response_csv_conflict", "/response_csv_join")
    previous = None
    for row in rows:
        values, row_issues = row["native_values"], row["issues"]
        cells = {"native_threshold_comparison": None, "input_correspondence": None,
            "exact_case_match": None, "ascii_case_compatible": None, "cleaned_interval": None,
            "original_character_interval": None, "source_intervals": None, "duplicate_native_position": False,
            "conflicting_native_position": False, "position_order_increasing": None,
            "usable_for_descriptive_mean": False, "native_csv_flag_matches_comparison": None}
        row["cells"] = cells
        row["source_parser_index"] = accepted_index.get(row["row_ordinal"])
        if not row["source_parse_accepted"]:
            continue
        position, residue, score = values["position_1based"], values["residue_token"], values["score"]
        comparison = _comparison(score, threshold)
        cells.update(native_threshold_comparison=comparison,
            duplicate_native_position=positions[position] > 1,
            conflicting_native_position=len(values_by_position[position]) > 1,
            position_order_increasing=True if previous is None else position > previous,
            score_in_unit_interval=score["kind"] == "finite" and 0 <= score["finite_value"] <= 1)
        previous = position
        if cells["duplicate_native_position"]:
            _issue(row_issues, "duplicate_native_position", "/rows/" + str(row["row_ordinal"]))
        if cells["position_order_increasing"] is False:
            _issue(row_issues, "native_position_order_conflict", "/rows/" + str(row["row_ordinal"]))
        if not cells["score_in_unit_interval"]:
            _issue(row_issues, "score_nonfinite_or_outside_documented_domain", "/rows/" + str(row["row_ordinal"]) + "/score", kind=score["kind"])
        bounded = cleaned is not None and 1 <= position <= len(cleaned)
        cells["position_within_cleaned_input"] = None if cleaned is None else bounded
        if bounded:
            native_ascii = len(residue) == 1 and residue in _ASCII
            cells.update(exact_case_match=residue == cleaned[position - 1],
                ascii_case_compatible=native_ascii and residue.upper() == cleaned[position - 1].upper(),
                cleaned_interval=[position - 1, position], original_character_interval=[indices[position - 1], indices[position - 1] + 1])
            cells["input_correspondence"] = cells["ascii_case_compatible"]
            if cells["input_correspondence"] and mapping["available"]:
                cells["source_intervals"] = map_interval(mapping["supplied"], *cells["original_character_interval"])
            if cells["ascii_case_compatible"] and not cells["exact_case_match"]:
                _issue(row_issues, "native_residue_case_differs", "/rows/" + str(row["row_ordinal"]))
        elif cleaned is not None:
            cells["input_correspondence"] = False
        if cells["input_correspondence"] is not True:
            _issue(row_issues, "input_correspondence_unavailable_or_conflicting", "/rows/" + str(row["row_ordinal"]))
        cells["usable_for_descriptive_mean"] = cells["input_correspondence"] is True and cells["score_in_unit_interval"]
        flag = row["native_csv_flag"]
        if authority == "response" and native_csv is not None:
            i = row["source_parser_index"]
            if i < len(table["rows"]):
                flag = table["rows"][i]["native_csv_flag"]
        row["reported_csv_flag_at_ordinal"] = flag
        if flag is not None and comparison is not None:
            cells["native_csv_flag_matches_comparison"] = flag == ("Yes" if comparison else "No")
            if not cells["native_csv_flag_matches_comparison"]:
                _issue(row_issues, "csv_threshold_flag_conflict", "/rows/" + str(row["row_ordinal"]))
    csv_incomplete = authority == "csv" and (not table["parser_tail_complete"] or any(not row["source_parse_accepted"] for row in rows))
    arithmetic = _source_arithmetic(rows, selected["population_available"], threshold, log["kind"], csv_incomplete=csv_incomplete)
    log_checks = {"parsed_count_matches": None, "threshold_matches": None,
        "thresholded_count_matches": None, "percentage_display_matches": None, "regions_match": None}
    fields = log["selected"]
    if fields and log["kind"] == "summary":
        if fields.get("parsed_count") is not None and fields["parsed_count"]["count"] is not None and arithmetic["parsed_row_denominator"] is not None:
            log_checks["parsed_count_matches"] = fields["parsed_count"]["count"] == arithmetic["parsed_row_denominator"]
        if fields.get("threshold") is not None and threshold is not None:
            native_threshold = fields["threshold"]["threshold"]
            log_checks["threshold_matches"] = native_threshold["kind"] == "finite" and native_threshold["finite_value"] == threshold
        if arithmetic["thresholded_row_count"] is not None and fields.get("disordered") is not None and fields["disordered"]["count"] is not None:
            log_checks["thresholded_count_matches"] = fields["disordered"]["count"] == arithmetic["thresholded_row_count"]
            log_checks["percentage_display_matches"] = fields["disordered"]["percentage"]["token"] == arithmetic["expected_percentage_display"]
        if arithmetic["regions"] is not None and fields.get("region_count") is not None:
            log_checks["regions_match"] = log["no_regions_marker_count"] == (1 if arithmetic["region_count"] == 0 else 0) and fields["region_count"]["count"] == arithmetic["region_count"] and [
                {key: row[key] for key in ("start_1based", "end_1based", "length_residues")} for row in log["regions"]] == [
                {key: row[key] for key in ("start_1based", "end_1based", "length_residues")} for row in arithmetic["regions"]]
        if any(value is False for value in log_checks.values()):
            _issue(issues, "logged_summary_conflict", "/log_checks")
        if not log["summary_structure_present"]:
            _issue(issues, "native_log_summary_structure_incomplete", "/log")
    if log["kind"] == "request_error":
        _issue(issues, "native_log_reports_request_error", "/log")
    if log["kind"] == "no_valid_data" and arithmetic["parsed_row_denominator"] not in (None, 0):
        _issue(issues, "native_log_early_return_conflicts_with_population", "/log")
    if arithmetic["parsed_row_denominator"] == 0:
        _issue(issues, "source_early_return_no_scores", "/rows")
    if arithmetic["parsed_row_denominator"] == 0 and native_csv is not None:
        _issue(issues, "empty_csv_not_produced_after_source_early_return", "/inputs/native_csv")
    if authority is None:
        _issue(issues, "native_residue_outputs_missing", "/inputs")
    if native_outcome != "completed":
        _issue(issues, "native_outcome_incomplete", "/inputs/native_outcome")
    if authority == "csv" and (not table["header_compatible"] or not table["parser_tail_complete"] or any(not row["source_parse_accepted"] for row in rows)):
        _issue(issues, "csv_population_incomplete", "/csv")
    return {"schema": SHEET_SCHEMA, "inputs": deepcopy(inputs),
        "source_profile": {"callable": "predict_protein_disorder_regions", "module_sha256": SOURCE_SHA256,
            "callable_sha256": CALLABLE_SHA256, "identity_kind": "declared_not_execution_receipt",
            "algorithm_location": "remote_IUPred2A_service", "request": {"url": "https://iupred2a.elte.hu/iupred2a", "iupred2": "long", "anchor2": "no"}, "source_default_threshold_not_inserted": 0.5},
        "cleaning": {"expression": "ASCII-letter selection preserving original case", "cleaned_sequence": cleaned,
            "original_character_indices": indices, "original_symbol_count": None if protein_sequence is None else len(protein_sequence),
            "cleaned_symbol_count": None if cleaned is None else len(cleaned),
            "removed_character_count": None if indices is None else len(protein_sequence) - len(indices)},
        "original_composition_sheet": original_composition, "cleaned_composition_sheet": cleaned_composition,
        "mapping": mapping, "response": response, "csv": table, "log": log,
        "authority": authority, "response_csv_join": join, "rows": rows, "log_checks": log_checks,
        "status": "failed" if native_outcome == "failed" else "partial" if issues or table["issues"] or log["issues"] or any(row["issues"] for row in rows) else "complete",
        "issues": issues}


def _definitions():
    return {
        "scope": "supplied IUPred2A-style data and declared original wrapper postprocessing; no scientific service, experiment, score calibration, transport completeness or invocation proof",
        "cleaning": "retain each original ASCII A-Z/a-z character in order, preserving case; indices are zero-based Python string characters/codepoints, never guessed UTF-8 bytes or FASTA parsing",
        "input_counts": "original_symbol_count=len(original string) characters; cleaned_symbol_count=count retained ASCII letters; removed_character_count=original-cleaned; all null for unknown original input",
        "row_ordinals": "original data-row occurrences within chosen view; response raw-line ordinals retain comments/blanks/skipped rows; source_parser_index counts accepted original source rows without changing native position labels",
        "csv_lines": "line_start_1based/line_end_1based are original physical CSV line ordinals from the standard reader, including quoted multiline records; original record text retained",
        "authority": "supplied response first, else supplied source-shaped CSV retained population; both supplied join by original CSV data ordinal and normalized int/float meaning+exact residue; never fallback/fill on conflict",
        "source_parse_accepted": "original int(position), residue token and float(score) parser acceptance; includes nonfinite floats, multi-letter residues, duplicate/out-of-range/unsorted native positions; malformed rows remain retained",
        "native_score": "native finite numeric value unaltered; nonfinite/unparseable tokens stay strings with numeric null; dimensionless predictor output, not function correctness probability",
        "native_threshold_comparison": "native float >= explicitly supplied finite threshold; NaN false,+inf true,-inf false; None threshold is unknown, not default0.5; finite OOD threshold qualified but comparison retained",
        "source_equivalent": "conditional original accepted-row postprocessing in supplied order; denominator is parsed accepted row occurrences, including duplicates and nonfinite tokens; never input length or unique position count",
        "parsed_row_denominator": "count accepted rows in supplied authoritative population; rows; null if unknown representation; zero for actually empty parsed population, without a native summary stage",
        "retained_data_row_count": "response noncomment/nonblank data-line occurrences or CSV data records, including malformed rows; rows; null when neither view supplied",
        "thresholded_row_count": "count source comparisons true over accepted row occurrences; rows; null for unknown threshold, request-error stage or empty/unknown population",
        "disordered_percentage": "(thresholded_row_count/parsed_row_denominator)*100; percent of supplied parsed occurrences; native expected display format .2f kept separately; null when source summary stage is not reached",
        "regions": "only original ordered runs of threshold-true consecutive numbered positions, length>1; below-threshold rows reset, skipped response lines do not enter source loop; singleton hits still count in thresholded rows; no repaired-region algorithm",
        "partial_csv_regions": "malformed/incomplete CSV-only populations keep compatible-row counts/means but region reconstruction stays null; unknown native CSV rows are not silently dropped to join a run; supplied response remains authoritative when present",
        "region_coordinates": "source printed one-based inclusive start/end; length=end-start+1 residues; member row ordinals retained; cleaned half-open [start-1,end) and original character intervals available only from checked input correspondence",
        "mapping": "existing sequence_mapping on explicitly supplied valid original-string path and actual cleaning-index arithmetic only; physical units/strand/order unchanged; source-numbered prediction coordinate projection is not biological validation",
        "usable_for_descriptive_mean": "finite score in[0,1], bounded native position, single ASCII residue matching cleaned input modulo ASCII case; exact case kept separately; duplicates/order conflicts remain flagged and INCLUDED as row occurrences",
        "descriptive_score_sum": "math.fsum of usable row-occurrence finite scores; dimensionless score sum; zero for a known population with zero usable rows, null for unknown population",
        "descriptive_mean_score": "descriptive_score_sum/descriptive_mean_denominator_rows; dimensionless predictor-score mean; null for zero/unknown denominator; not a source-native mean, calibration or independent confidence",
        "unique_input_coverage": "unique bounded cleaned positions among usable row occurrences / actual cleaned string length; dimensionless, duplicate positions count once only for this coverage; null for missing/zero input denominator",
        "duplicate_counts": "distinct native position labels appearing>1, plus number of accepted occurrences at those labels; positions may be out of range; conflicting labels/scores kept, no consensus/sort/dedup repair",
        "native_log_parsed_row_count": "direct source log's misleading 'Protein sequence length' value is parsed-row count, not original or cleaned input length; counts/percent/regions remain raw source assertions and checks never overwrite them",
        "missingness": "unknown inputs/views differ from empty; original empty score population returns before CSV/threshold/region/log-summary stage, so no fabricated zero percentage/regions; partial arithmetic and all raw records stay available; corrupt saved projections reject without repair",
        "uncertainty": "no uncertainty interval, predictor calibration, native disorder observation or function correctness probability supplied or invented",
    }


def calculate_disorder_components(sheet: dict) -> dict:
    """Recalculate one saved finite sheet without rereading files or a service."""
    _finite_json(sheet)
    if type(sheet) is not dict or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("protein_disorder_sheet_required")
    inputs = sheet.get("inputs")
    if type(inputs) is not dict or set(inputs) != {"native_csv", "protein_sequence", "threshold", "native_response", "native_log", "native_outcome", "input_ref", "input_mapping"}:
        raise ValueError("protein_disorder_saved_inputs_required")
    expected = build_disorder_sheet(**inputs)
    conflict = _difference(expected, sheet)
    if conflict is not None:
        raise ValueError("protein_disorder_saved_sheet_conflict:" + conflict)
    population_available = sheet["response"]["population_available"] if sheet["authority"] == "response" else sheet["csv"]["population_available"] if sheet["authority"] == "csv" else False
    rows = sheet["rows"]
    usable = [row for row in rows if row["cells"]["usable_for_descriptive_mean"]]
    score_sum = math.fsum(row["native_values"]["score"]["finite_value"] for row in usable) if population_available else None
    denominator = len(usable) if population_available else None
    unique = list(dict.fromkeys(row["native_values"]["position_1based"] for row in usable))
    length = sheet["cleaning"]["cleaned_symbol_count"]
    accepted = [row for row in rows if row["source_parse_accepted"]]
    counts = Counter(row["native_values"]["position_1based"] for row in accepted)
    csv_incomplete = sheet["authority"] == "csv" and (not sheet["csv"]["parser_tail_complete"] or any(not row["source_parse_accepted"] for row in rows))
    source = _source_arithmetic(rows, population_available, inputs["threshold"], sheet["log"]["kind"], csv_incomplete=csv_incomplete)
    return {"schema": COMPONENTS_SCHEMA, "status": sheet["status"], "authority": sheet["authority"],
        "rows": deepcopy(rows), "source_equivalent": source,
        "native_log": deepcopy(sheet["log"]), "log_checks": deepcopy(sheet["log_checks"]),
        "response_csv_join": deepcopy(sheet["response_csv_join"]),
        "original_composition": None if sheet["original_composition_sheet"] is None else calculate_sequence_composition_scores(sheet["original_composition_sheet"]),
        "cleaned_composition": None if sheet["cleaned_composition_sheet"] is None else calculate_sequence_composition_scores(sheet["cleaned_composition_sheet"]),
        "summary": {"original_symbol_count": sheet["cleaning"]["original_symbol_count"],
            "cleaned_symbol_count": length, "removed_character_count": sheet["cleaning"]["removed_character_count"],
            "retained_data_row_count": len(rows) if sheet["authority"] is not None else None,
            "source_parsed_row_count": source["parsed_row_denominator"],
            "usable_row_occurrence_count": denominator, "descriptive_score_sum": score_sum,
            "descriptive_mean_denominator_rows": denominator,
            "descriptive_mean_score": score_sum / denominator if denominator else None,
            "unique_usable_input_positions_1based": unique if population_available else None,
            "unique_usable_input_position_count": len(unique) if population_available else None,
            "input_coverage_denominator_symbols": length,
            "unique_input_coverage": len(unique) / length if population_available and length else None,
            "duplicate_native_position_count": sum(count > 1 for count in counts.values()) if population_available else None,
            "duplicate_native_position_occurrence_count": sum(count for count in counts.values() if count > 1) if population_available else None,
            "native_summary_stage_reached_by_source_equivalent": source["stage"] == "source_equivalent_postprocessing",
            "scientific_service_execution_verified": False},
        "definitions": _definitions(), "issues": deepcopy(sheet["issues"])}


__all__ = ["SHEET_SCHEMA", "COMPONENTS_SCHEMA", "build_disorder_sheet", "calculate_disorder_components"]
