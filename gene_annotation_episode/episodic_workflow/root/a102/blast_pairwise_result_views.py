"""Closed receiver-selected views of already calculated paired BLAST rows.

This module performs no acquisition, Store access, calculation or publication.
Native order and identities belong to the complete retained grading collection.
"""
from __future__ import annotations

import math

from .domain import ContractError, validate_schema
from .native_blast_contracts import PROGRAMS, finite_json_copy


NATIVE_BLAST_METRICS = {
    "pairwise_hsp": (
        "native_score_bits", "native_raw_score", "native_evalue",
        "alignment_columns", "paired_positions", "identical_positions",
        "substituted_positions", "query_gap_columns", "reference_gap_columns",
        "query_aligned_positions", "reference_aligned_positions",
        "query_length", "reference_length", "paired_identity", "alignment_identity",
        "query_paired_coverage", "reference_paired_coverage"),
    "pairwise_union": (
        "observed_distinct_residue_pairs", "observed_identical_residue_pairs",
        "observed_paired_query_positions", "observed_paired_reference_positions",
        "hsps_with_geometry", "hsps_without_geometry", "query_length", "reference_length",
        "query_paired_coverage", "reference_paired_coverage", "paired_identity",
        "query_selected_length", "reference_selected_length",
        "query_selected_paired_positions", "reference_selected_paired_positions",
        "query_selected_paired_coverage", "reference_selected_paired_coverage",
        "conflicting_mapping_count", "identical_mapping_group_count"),
}
FAMILY_SOURCES = {
    "pairwise_hsp": "execution_blast_pairwise_hsp_rows",
    "pairwise_union": "execution_blast_pairwise_union_rows",
}


def _object(properties):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


_KEY = {"type": "string", "minLength": 1}
_REF = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
_ROWS = {"oneOf": [
    _object({"offset": {"type": "integer", "minimum": 0},
             "limit": {"type": "integer", "minimum": 1}}),
    _object({"record_keys": {"type": "array", "minItems": 1,
                            "uniqueItems": True, "items": _KEY}})]}
SEARCH_KEY_SCHEMA = _object({
    "artifact_key": {"type": "string", "format": "identifier",
                     "x-reference-namespace": "native_blast_artifact_key"},
    "member_ordinal": {"type": ["integer", "null"], "minimum": 0},
    "report_index": {"type": "integer", "minimum": 0},
    "search_pointer": {"type": "string", "format": "identifier",
                       "x-reference-namespace": "native_blast_search_pointer"},
})
NATIVE_BLAST_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": "native_blast_result_selector_v1"},
    "acquisition": {"const": "complete_bound_bundle"},
    "projection": {"oneOf": [_object({
        "family": {"const": family}, "rows": _ROWS,
        "metrics": {"type": "array", "minItems": 1, "uniqueItems": True,
                    "items": {"enum": list(metrics)}}})
        for family, metrics in NATIVE_BLAST_METRICS.items()]},
})


def validate_native_blast_result_selector(selector, *, program):
    try:
        selector = finite_json_copy(selector)
        validate_schema(selector, NATIVE_BLAST_RESULT_SELECTOR_SCHEMA)
    except ValueError as error:
        raise ContractError("native_blast_result_selector_invalid") from error
    if program not in PROGRAMS:
        raise ContractError("native_blast_result_program_unsupported")
    rows = selector["projection"]["rows"]
    if "offset" in rows and any(type(rows[key]) is not int for key in ("offset", "limit")):
        raise ContractError("native_blast_result_selector_integer_required")
    return selector


def row_schema(family):
    metrics = {"type": "string", "enum": list(NATIVE_BLAST_METRICS[family])}
    ordinal = ({"type": "null"} if family == "pairwise_union" else
               {"type": "integer", "minimum": 0})
    return _object({
        "record_key": {"type": "string", "format": "identifier",
                       "x-reference-namespace": "native_blast_pairwise_row"},
        "source_ref": _REF,
        "observation_ref": ({"type": "null"} if family == "pairwise_union" else
                            {**_REF, "type": ["string", "null"]}),
        "subject_ref": {"type": ["string", "null"], "format": "reference",
                        "x-reference-namespace": "subject"},
        "reference_refs": {"type": "array", "uniqueItems": True, "items": _REF},
        "search_key": SEARCH_KEY_SCHEMA,
        "hit_ordinal": ordinal, "hsp_ordinal": ordinal,
        "program": {"type": "string", "enum": list(PROGRAMS)},
        "coordinate_units": _object({axis: {"type": "string", "enum": ["nt", "aa"]}
                                      for axis in ("query", "reference", "alignment")}),
        "status": {"type": "string", "enum": ["published", "unbound", "invalid"]},
        "native_status": {"type": "string", "enum": ["complete", "partial", "no_reported_alignment",
                                    "alignment_report_unavailable"]},
        "measurements": {"type": "array", "items": _object({"name": metrics,
                                                               "value": {"type": "number"}})},
        "unavailable": {"type": "array", "items": _object({"name": metrics,
            "reason": {"type": "string", "enum": ["missing_input", "incompatible_input",
                                  "invalid_native_row", "not_measured"]}})},
    })


def native_blast_fact_sources():
    return {source: {"type": "array", "meaning":
        "Requested native pairwise BLAST numbers in original search/HSP order. "
        "Coverage uses explicit full or selected operand denominators. Union rows summarize "
        "the observed HSP correspondences and have no additional observation. "
        "Unavailable numbers are not zero; E-value is not paired relevance.",
        "report_schema": {"type": "array", "items": row_schema(family), "x-source": source}}
        for family, source in FAMILY_SOURCES.items()}


def projected_measurements(row, metrics):
    """Select stored scalars and stored missingness; never recompute a number."""
    values, unavailable = [], []
    for name in metrics:
        value = row["values"].get(name)
        if type(value) in (int, float) and math.isfinite(value):
            values.append({"name": name, "value": value})
        else:
            unavailable.append({"name": name,
                "reason": row["unavailable"].get(name, "not_measured")})
    return values, unavailable


__all__ = ["NATIVE_BLAST_RESULT_SELECTOR_SCHEMA", "NATIVE_BLAST_METRICS", "FAMILY_SOURCES",
           "validate_native_blast_result_selector", "native_blast_fact_sources", "row_schema"]
