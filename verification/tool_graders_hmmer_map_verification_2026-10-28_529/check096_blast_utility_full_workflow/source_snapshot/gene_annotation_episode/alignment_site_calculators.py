"""Literal selected-reference-site quantities from saved numerical sheets.

Native whole-alignment scores are retained by the reader and remain unused in
these ratios. No model, I/O, alignment execution or annotation-credit formula
is invoked by this calculator.
"""
from __future__ import annotations

from copy import deepcopy

from .alignment_site_inputs import COUNT_NAMES, _observed_counts, _validate_saved_sheet


RATIO_NAMES = (
    "selected_paired_identity", "selected_alignment_identity",
    "selected_reference_aligned_fraction", "selected_reference_paired_fraction",
    "selected_query_paired_coverage", "selected_reference_paired_coverage",
)
SUMMARY_NAMES = COUNT_NAMES + RATIO_NAMES


def _definitions(operands):
    formulas = {
        "requested_position_count": "len(requested_positions)",
        "unique_requested_position_count": "len(unique_requested_positions)",
        "duplicate_requested_position_count": "requested_position_count - unique_requested_position_count",
        "identical_positions": "count(unique requested rows with relationship identical)",
        "substituted_positions": "count(unique requested rows with relationship substituted)",
        "paired_positions": "identical_positions + substituted_positions",
        "query_gap_positions": "count(unique requested rows with relationship query_gap)",
        "reference_skip_positions": "count(unique requested rows with relationship reference_skip)",
        "outside_alignment_positions": "count(unique requested rows with relationship outside_alignment)",
        "unavailable_positions": "count(unique requested rows with relationship unavailable)",
        "aligned_reference_positions": "paired_positions + query_gap_positions",
        "selected_insertion_events": "len(selected unique native insertion runs)",
        "inserted_query_positions": "sum(query_interval[1] - query_interval[0] for selected insertion runs)",
        "selected_query_paired_units": "length(union(query_interval for unique paired requested rows))",
        "selected_reference_paired_units": "length(union(reference_interval for unique paired requested rows))",
        "selected_paired_identity": "identical_positions / paired_positions",
        "selected_alignment_identity": "identical_positions / (paired_positions + query_gap_positions + inserted_query_positions)",
        "selected_reference_aligned_fraction": "aligned_reference_positions / unique_requested_position_count",
        "selected_reference_paired_fraction": "paired_positions / unique_requested_position_count",
        "selected_query_paired_coverage": "selected_query_paired_units / operands.query.length",
        "selected_reference_paired_coverage": "selected_reference_paired_units / operands.reference.length",
    }
    ratio_inputs = {
        "selected_paired_identity": ["identical_positions", "paired_positions"],
        "selected_alignment_identity": ["identical_positions", "paired_positions", "query_gap_positions", "inserted_query_positions"],
        "selected_reference_aligned_fraction": ["aligned_reference_positions", "unique_requested_position_count"],
        "selected_reference_paired_fraction": ["paired_positions", "unique_requested_position_count"],
        "selected_query_paired_coverage": ["selected_query_paired_units", "operands.query.length"],
        "selected_reference_paired_coverage": ["selected_reference_paired_units", "operands.reference.length"],
    }
    definitions = {}
    for name in SUMMARY_NAMES:
        ratio = name in RATIO_NAMES
        population = ("full_query_operand" if name == "selected_query_paired_coverage" else
            "full_reference_operand" if name == "selected_reference_paired_coverage" else
            "unique_selected_paired_reference_positions" if name == "selected_paired_identity" else
            "selected_alignment_columns_including_adjacent_insertions_excluding_reference_skips" if name == "selected_alignment_identity" else
            "requested_rows_with_multiplicity" if name in ("requested_position_count", "duplicate_requested_position_count") else
            "unique_selected_native_insertion_runs" if name in ("selected_insertion_events", "inserted_query_positions") else
            "unique_requested_reference_positions")
        unit = ("fraction" if ratio else "events" if name == "selected_insertion_events" else
            "rows" if name in ("requested_position_count", "duplicate_requested_position_count") else
            operands["query"]["unit"] if name in ("inserted_query_positions", "selected_query_paired_units") else
            operands["reference"]["unit"])
        definitions[name] = {"inputs": ratio_inputs.get(name, ["measured_counts."+name, "sites", "insertions"]),
            "formula": formulas[name], "units": unit, "population": population,
            "denominator": "ratios."+name+".denominator" if ratio else None,
            "coordinate_system": "zero_based_half_open_local_operands",
            "kind": "derived_ratio" if ratio else "derived_count_from_checked_correspondence",
            "missing": "null_if_required_component_or_length_unavailable_or_incompatible_or_denominator_zero" if ratio else
                "request_and_unavailable_counts_remain_known; other_full_request_totals_null_if_any_requested_row_unavailable",
            "uncertainty": None}
    return definitions


def calculate_reference_site_components(sheet: dict) -> dict:
    """Validate saved custody-independent data and calculate explicit counts/ratios.

Duplicate rows are response facts, counted once per reference position. Invalid
geometry never supplies a measured zero. Valid subset counts remain named
separately when a full-request component is unavailable.
"""
    _validate_saved_sheet(sheet)
    summary = deepcopy(sheet["measured_counts"])
    count = summary
    columns = (sum(count[name] for name in ("paired_positions", "query_gap_positions", "inserted_query_positions"))
               if all(count[name] is not None for name in ("paired_positions", "query_gap_positions", "inserted_query_positions")) else None)
    inputs = {
        "selected_paired_identity": (count["identical_positions"], count["paired_positions"]),
        "selected_alignment_identity": (count["identical_positions"], columns),
        "selected_reference_aligned_fraction": (count["aligned_reference_positions"], count["unique_requested_position_count"]),
        "selected_reference_paired_fraction": (count["paired_positions"], count["unique_requested_position_count"]),
        "selected_query_paired_coverage": (count["selected_query_paired_units"], sheet["operands"]["query"]["length"]),
        "selected_reference_paired_coverage": (count["selected_reference_paired_units"], sheet["operands"]["reference"]["length"]),
    }
    ratios = {name: {"numerator": numerator, "denominator": denominator,
                      "value": numerator / denominator if numerator is not None and denominator not in (None, 0) else None}
              for name, (numerator, denominator) in inputs.items()}
    summary.update({name: row["value"] for name, row in ratios.items()})
    incompatible = any(issue["code"] in ("site_native_geometry_conflict", "site_operand_identity_conflict") for issue in sheet["issues"])
    states = {name: "available" if value is not None else "incompatible" if incompatible else "unavailable"
              for name, value in summary.items()}
    for name, row in ratios.items():
        if row["numerator"] is not None and row["denominator"] == 0:
            states[name] = "not_applicable"
    return {"schema": "reference_site_components_v1", "status": sheet["status"],
        "summary": summary, "ratios": ratios,
        "observed_subset_counts": _observed_counts(sheet["sites"], sheet["insertions"]),
        "component_status": states, "issues": deepcopy(sheet["issues"]),
        "definitions": _definitions(sheet["operands"])}


__all__ = ["calculate_reference_site_components"]
