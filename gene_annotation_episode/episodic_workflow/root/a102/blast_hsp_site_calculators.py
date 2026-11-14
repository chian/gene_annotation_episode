"""Deterministic selected BLAST-column counts/ratios from a saved sheet only.

These are literal alignment measurements, not function probabilities. Native
scores and reported whole-HSP counts remain inherited and unused in these
window calculations. No weighting or statistical uncertainty is invented.
"""
from __future__ import annotations

from copy import deepcopy

from .blast_hsp_site_inputs import validate_blast_hsp_column_sheet
from .blast_search import PROGRAM_UNITS


def _ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if numerator is not None and denominator else None}


def _definitions(units):
    fields = {
        "window_alignment_columns": ("column", "len(columns)", "selected realized alignment columns"),
        "paired_columns": ("column", "count(relationship in identical, substituted)", "selected paired columns"),
        "identical_pairs": ("pair", "count(relationship=identical)", "selected paired uppercase native symbols with literal equality"),
        "substituted_pairs": ("pair", "paired_columns-identical_pairs", "selected paired uppercase native symbols with literal inequality"),
        "query_gap_columns": ("column", "count(relationship=query_gap)", "selected columns with a query gap"),
        "reference_gap_columns": ("column", "count(relationship=reference_gap)", "selected columns with a reference gap"),
        "query_paired_units": (units[0], "length(union(query_interval for paired columns))", "selected checked paired query intervals"),
        "reference_paired_units": (units[1], "length(union(reference_interval for paired columns))", "selected checked paired reference intervals"),
        "paired_identity": ("fraction", "identical_pairs/paired_columns", "selected paired columns"),
        "alignment_identity": ("fraction", "identical_pairs/window_alignment_columns", "selected realized alignment columns including gaps"),
        "query_paired_coverage": ("fraction", "query_paired_units/operands.query.length", "complete original query operand in native coordinate units"),
        "reference_paired_coverage": ("fraction", "reference_paired_units/operands.reference.length", "complete original reference operand in native coordinate units"),
    }
    denominators = {"paired_identity": "paired_columns", "alignment_identity": "window_alignment_columns",
                    "query_paired_coverage": "operands.query.length", "reference_paired_coverage": "operands.reference.length"}
    return {name: {"unit": unit, "formula": formula, "population": population,
                   "denominator": denominators.get(name),
                   "coordinate_convention": "zero_based_half_open_original_operand" if "units" in name or "coverage" in name else None,
                   "missing_behavior": "null_if_input_unavailable_or_incompatible_or_denominator_zero",
                   "measurement_kind": "derived_from_retained_native_alignment", "uncertainty": None}
            for name, (unit, formula, population) in fields.items()}


def calculate_blast_hsp_column_components(sheet: dict) -> dict:
    """Calculate explicit selected-window fractions, preserving every denominator."""
    validate_blast_hsp_column_sheet(sheet)
    summary = deepcopy(sheet["measured_counts"])
    ratios = {
        "paired_identity": _ratio(summary["identical_pairs"], summary["paired_columns"]),
        "alignment_identity": _ratio(summary["identical_pairs"], summary["window_alignment_columns"]),
        "query_paired_coverage": _ratio(summary["query_paired_units"], sheet["operands"]["query"]["length"]),
        "reference_paired_coverage": _ratio(summary["reference_paired_units"], sheet["operands"]["reference"]["length"]),
    }
    summary.update({name: ratio["value"] for name, ratio in ratios.items()})
    component_status = {}
    for name, value in summary.items():
        if value is not None:
            component_status[name] = "available"
            continue
        geometry_component = name.endswith(("_units", "_coverage"))
        geometry_status = sheet["availability"]["geometry" if geometry_component else "traceback"]
        ratio = ratios.get(name)
        if ratio is not None and ratio["denominator"] == 0 and ratio["numerator"] is not None:
            component_status[name] = "not_applicable"
        elif geometry_status == "incompatible":
            component_status[name] = "incompatible"
        else:
            component_status[name] = "unavailable"
    return {"schema": "blast_hsp_column_components_v1", "status": sheet["status"],
            "summary": summary, "ratios": ratios, "component_status": component_status,
            "issues": deepcopy(sheet["issues"]), "definitions": _definitions(PROGRAM_UNITS[sheet["program"]])}


__all__ = ["calculate_blast_hsp_column_components"]
