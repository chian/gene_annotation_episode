"""Pure extraction of a selected window from an explicitly supplied BLAST HSP.

The caller authenticates the observation, native locator and operand identities.
This parser neither resolves those references nor executes/acquires anything.
Full supplied HSP data stays separate from selected-column measurements; native
whole-HSP scores are inherited and never assigned to individual columns.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .alignment_site_mapping import map_operand_interval
from .blast_pairwise_grader import blast_hsp_column_correspondence
from .blast_search import PROGRAM_UNITS
from .minimap2_grading_inputs import require_finite_json


SHEET_SCHEMA = "blast_hsp_column_sheet_v1"
COUNT_FIELDS = ("window_alignment_columns", "paired_columns", "identical_pairs",
                "substituted_pairs", "query_gap_columns", "reference_gap_columns",
                "query_paired_units", "reference_paired_units")


def _validate_inputs(hsp, program, query_length, reference_length, column_offset,
                     column_limit, operands, source, original_mappings):
    require_finite_json([hsp, program, query_length, reference_length, column_offset,
                         column_limit, operands, source, original_mappings], "site_finite_json_required")
    if type(hsp) is not dict:
        raise ValueError("site_native_input_invalid")
    if type(program) is not str or program not in PROGRAM_UNITS:
        raise ValueError("unsupported_blast_program")
    if (type(column_offset) is not int or column_offset < 0
            or type(column_limit) is not int or not 1 <= column_limit <= 4096):
        raise ValueError("bounded_blast_alignment_window_required")
    if type(operands) is not dict or set(operands) != {"query", "reference"}:
        raise ValueError("site_operands_invalid")
    qunit, runit, aunit = PROGRAM_UNITS[program]
    for role, length, unit in (("query", query_length, qunit), ("reference", reference_length, runit)):
        operand = operands[role]
        if (type(operand) is not dict
                or set(operand) != {"subject_ref", "length", "unit", "alignment_unit", "molecule"}
                or type(operand["subject_ref"]) is not str or not operand["subject_ref"]
                or length is not None and (type(length) is not int or length < 0)
                or operand["length"] is not None and (type(operand["length"]) is not int or operand["length"] < 0)
                or operand["unit"] not in ("aa", "nt", "symbol")
                or operand["alignment_unit"] not in ("aa", "nt")
                or operand["molecule"] not in ("protein", "dna", "rna", "unknown")):
            raise ValueError("site_operand_invalid")
        if (operand["length"] != length or operand["alignment_unit"] != aunit
                or operand["unit"] not in (unit, "symbol")
                or operand["unit"] == "symbol" and operand["molecule"] != "unknown"
                or unit == "aa" and operand["molecule"] not in ("protein", "unknown")
                or unit == "nt" and operand["molecule"] not in ("dna", "rna", "unknown")):
            raise ValueError("site_operand_identity_conflict")
    if (type(source) is not dict or set(source) != {"alignment_ref", "source_ref", "native_artifact_ref",
            "provider", "format", "native_version", "native_locator"}
            or any(type(source[name]) is not str or not source[name]
                   for name in ("alignment_ref", "source_ref", "native_artifact_ref"))
            or source["provider"] != "ncbi_blast" or source["format"] != "ncbi_blast_json_hsp"
            or source["native_version"] is not None and type(source["native_version"]) is not str):
        raise ValueError("site_source_invalid")
    locator = source["native_locator"]
    if (type(locator) is not dict or set(locator) != {"report_ordinal", "hit_ordinal", "hsp_ordinal"}
            or any(type(value) is not int or value < 0 for value in locator.values())):
        raise ValueError("site_source_locator_invalid")
    if original_mappings is not None and (type(original_mappings) is not dict
            or set(original_mappings) != {"query", "reference"}):
        raise ValueError("site_original_mappings_invalid")


def _union_size(intervals):
    total, boundary = 0, -1
    for start, end in sorted(intervals):
        total += max(0, end - max(start, boundary))
        boundary = max(boundary, end)
    return total


def _selected_counts(columns, traceback_status, geometry_status):
    counts = dict.fromkeys(COUNT_FIELDS)
    if traceback_status != "available":
        return counts
    counts.update(window_alignment_columns=len(columns),
        paired_columns=sum(row["relationship"] in ("identical", "substituted") for row in columns),
        identical_pairs=sum(row["relationship"] == "identical" for row in columns),
        substituted_pairs=sum(row["relationship"] == "substituted" for row in columns),
        query_gap_columns=sum(row["relationship"] == "query_gap" for row in columns),
        reference_gap_columns=sum(row["relationship"] == "reference_gap" for row in columns))
    if geometry_status == "available":
        for role in ("query", "reference"):
            counts[role + "_paired_units"] = _union_size(row[role + "_interval"] for row in columns
                if row["relationship"] in ("identical", "substituted"))
    return counts


def _mapping_status(rows, role):
    statuses = {row[role + "_mapping_status"] for row in rows}
    for status in ("incompatible", "unavailable", "available"):
        if status in statuses:
            return status
    return "not_applicable"


def extract_blast_hsp_columns(
    hsp: dict, *, program: str, query_length: int | None,
    reference_length: int | None, column_offset: int, column_limit: int,
    operands: dict, source: dict, original_mappings: dict | None = None,
) -> dict:
    """Populate finite native facts and checked selected-column measurements.

    Missing strings yield no realized window or invented counts. A readable
    traceback with invalid coordinates retains literal string counts but no
    positional coverage. Gaps have no local/original interval; missing geometry
    is explicitly unavailable, not a gap or an inferred identity mapping.
    """
    _validate_inputs(hsp, program, query_length, reference_length, column_offset,
                     column_limit, operands, source, original_mappings)
    full = blast_hsp_column_correspondence(hsp, program=program,
        query_length=query_length, reference_length=reference_length)
    traceback, geometry = full["traceback_status"], full["geometry_status"]
    issues = []
    for item in full["issues"]:
        issue = {"code": item["code"]}
        if "field" in item:
            issue["field"] = item["field"]
        if "operand" in item:
            issue["role"] = "reference" if item["operand"] == "hit" else item["operand"]
        if issue not in issues:
            issues.append(issue)
    total, realized, next_offset, columns = None, None, None, []
    if traceback == "available":
        total = len(full["columns"])
        if column_offset > total:
            raise ValueError("blast_alignment_window_out_of_bounds")
        end = min(total, column_offset + column_limit)
        realized = {"column_offset": column_offset, "column_end": end}
        next_offset = end if end < total else None
        columns = full["columns"][column_offset:end]
        for row in columns:
            for role in ("query", "reference"):
                interval = row[role + "_interval"]
                if interval is None and row[role + "_symbol"] != "-":
                    mapped = {"status": "unavailable", "intervals": None,
                              "reason": "site_original_mapping_unavailable"}
                else:
                    # The processing coordinate unit is known even when the
                    # material descriptor is symbol/unknown. Validate ancestry
                    # against those native coordinates, preserving the supplied
                    # material descriptor unchanged in the sheet.
                    mapping_operand = {**operands[role], "unit": row[role + "_unit"]}
                    mapped = map_operand_interval(mapping_operand,
                        original_mappings[role] if original_mappings is not None else None, interval)
                row[role + "_original_intervals"] = mapped["intervals"]
                row[role + "_mapping_status"] = mapped["status"]
                row[role + "_mapping_reason"] = mapped["reason"]
                if mapped["reason"] is not None:
                    issue = {"code": mapped["reason"], "role": role}
                    if issue not in issues:
                        issues.append(issue)
    if geometry != "available":
        code = "site_native_geometry_unavailable" if geometry == "unavailable" else "site_native_geometry_conflict"
        if {"code": code} not in issues:
            issues.append({"code": code})
    availability = {"traceback": traceback, "geometry": geometry}
    for role in ("query", "reference"):
        availability[role + "_length"] = "available" if operands[role]["length"] is not None else "unavailable"
        availability[role + "_original_mapping"] = _mapping_status(columns, role) if traceback == "available" else "unavailable"
    status = "unavailable" if traceback != "available" else "partial" if issues or any(
        value in ("unavailable", "incompatible") for value in availability.values()) else "complete"
    return {"schema": SHEET_SCHEMA, "status": status,
        "source": deepcopy(source), "program": program, "native_version": source["native_version"],
        "operands": deepcopy(operands), "native_input": deepcopy(hsp),
        "inherited_native_measurements": {"scope": "whole_hsp",
            "native_scores": full["native_scores"], "reported_counts": full["reported_counts"],
            "reported_percentages": full["reported_percentages"]},
        "requested_window": {"column_offset": column_offset, "column_limit": column_limit},
        "realized_window": realized, "total_columns": total, "next_column_offset": next_offset,
        "columns": columns, "original_mapping_inputs": deepcopy(original_mappings),
        "measured_counts": _selected_counts(columns, traceback, geometry),
        "availability": availability, "issues": issues}


def validate_blast_hsp_column_sheet(sheet: dict) -> None:
    """Verify saved row, selector, geometry and count relationships, without I/O.

    Re-extract only from the complete native facts already saved in the sheet;
    no current reference, native execution or external state is consulted.
    """
    require_finite_json(sheet, "site_finite_json_required")
    if type(sheet) is not dict or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("blast_hsp_column_sheet_required")
    try:
        expected = extract_blast_hsp_columns(sheet["native_input"], program=sheet["program"],
            query_length=sheet["operands"]["query"]["length"],
            reference_length=sheet["operands"]["reference"]["length"],
            column_offset=sheet["requested_window"]["column_offset"],
            column_limit=sheet["requested_window"]["column_limit"], operands=sheet["operands"],
            source=sheet["source"], original_mappings=sheet["original_mapping_inputs"])
    except (KeyError, TypeError) as error:
        raise ValueError("blast_hsp_column_sheet_invalid") from error
    if json.dumps(sheet, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ValueError("blast_hsp_column_sheet_conflict")


__all__ = ["extract_blast_hsp_columns", "validate_blast_hsp_column_sheet"]
