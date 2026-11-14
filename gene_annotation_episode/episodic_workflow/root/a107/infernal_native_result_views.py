"""Receiver-selected numerical projections of retained Infernal measurements.

Full native tables and alignments remain in artifacts. These contracts select
explicit rows and quantities; they perform no acquisition or scientific grading.
Names identify native operands, and missing measurements never become zero.
"""
from __future__ import annotations

import math

from .domain import ContractError, validate_schema
from .native_infernal_contracts import finite_json_copy


NATIVE_INFERNAL_METRICS = {
    "search_hit": (
        "bitscore", "evalue", "bias_bits", "gc_fraction", "model_span_length",
        "model_span_fraction", "sequence_span_length", "sequence_span_fraction",
        "consensus_length", "sequence_length"),
    "search_sequence": (
        "hit_count", "union_numerator", "union_denominator", "union_span_fraction",
        "unselected_hit_count", "unknown_selection_count", "invalid_geometry_count"),
    "alignment_sequence": (
        "native_bit_score", "native_avg_pp", "original_length", "model_length",
        "retained_nucleotides", "model_match_nucleotides", "model_gap_positions",
        "missing_model_positions", "nonresidue_model_positions",
        "retained_insert_nucleotides", "retained_local_end_nucleotides",
        "deleted_model_positions", "local_end_skipped_model_positions",
        "total_insert_nucleotides", "total_local_end_nucleotides", "omitted_nucleotides",
        "model_occupancy", "sequence_matched_coverage", "posterior_available_count",
        "posterior_unavailable_count", "posterior_lower_mean", "posterior_upper_mean"),
    "alignment_column": (
        "row_count", "occupancy_numerator", "occupancy_denominator", "occupancy",
        "missing_rows", "nonresidue_rows", "unavailable_rows"),
    "alignment_pair": (
        "row_count", "observed_two_nucleotide_pairs", "canonical_pairs",
        "noncanonical_pairs", "unambiguous_pair_denominator", "canonical_pair_fraction",
        "excluded_gap_rows", "excluded_missing_rows", "excluded_ambiguous_rows",
        "excluded_nonresidue_rows", "excluded_unavailable_rows"),
}
COLLECTIONS = {
    "search_hit": "hits", "search_sequence": "sequence_strand_aggregates",
    "alignment_sequence": "sequences", "alignment_column": "columns",
    "alignment_pair": "pairs",
}
FAMILY_SOURCES = {
    family: "execution_infernal_" + family + "_rows"
    for family in NATIVE_INFERNAL_METRICS
}
IDENTIFIER_NAMESPACES = ("native_infernal_row", "native_infernal_sequence_name",
                         "native_infernal_model_name")


def _object(properties):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


_TEXT = {"type": "string", "minLength": 1}
_REF = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
_NULL_REF = {**_REF, "type": ["string", "null"]}
_ROWS = {"oneOf": [
    _object({"offset": {"type": "integer", "minimum": 0},
             "limit": {"type": "integer", "minimum": 1}}),
    _object({"record_keys": {"type": "array", "minItems": 1,
                             "uniqueItems": True, "items": _TEXT}})]}
NATIVE_INFERNAL_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": "native_infernal_result_selector_v1"},
    "acquisition": {"const": "complete_bound_bundle"},
    "projection": {"oneOf": [_object({"family": {"const": family}, "rows": _ROWS,
        "metrics": {"type": "array", "minItems": 1, "uniqueItems": True,
                    "items": {"enum": list(metrics)}}})
        for family, metrics in NATIVE_INFERNAL_METRICS.items()]},
})


def families_for_program(program):
    if program in {"cmsearch", "cmscan"}:
        return ("search_hit", "search_sequence")
    if program == "cmalign":
        return ("alignment_sequence", "alignment_column", "alignment_pair")
    raise ContractError("native_infernal_result_program_unsupported")


def validate_native_infernal_result_selector(selector, *, program):
    selector = finite_json_copy(selector)
    try:
        validate_schema(selector, NATIVE_INFERNAL_RESULT_SELECTOR_SCHEMA)
    except ContractError as error:
        raise ContractError("native_infernal_result_selector_invalid") from error
    if selector["projection"]["family"] not in families_for_program(program):
        raise ContractError("native_infernal_result_selector_family_mismatch")
    rows = selector["projection"]["rows"]
    if "offset" in rows and any(type(rows[k]) is not int for k in ("offset", "limit")):
        raise ContractError("native_infernal_result_selector_integer_required")
    return selector


def row_schema(family):
    metric = {"type": "string", "enum": list(NATIVE_INFERNAL_METRICS[family])}
    pair = {"type": ["array", "null"], "minItems": 2, "maxItems": 2,
            "items": {"type": "integer", "minimum": 0}}
    return _object({
        "record_key": {"type": "string", "format": "identifier",
                       "x-reference-namespace": "native_infernal_row"},
        "source_ref": _REF, "observation_ref": _NULL_REF,
        "subject_ref": {"type": ["string", "null"], "format": "reference",
                        "x-reference-namespace": "subject"},
        "reference_refs": {"type": "array", "uniqueItems": True, "items": _REF},
        "sequence_name": {"type": ["string", "null"], "format": "identifier",
                          "x-reference-namespace": "native_infernal_sequence_name"},
        "model_name": {"type": ["string", "null"], "format": "identifier",
                       "x-reference-namespace": "native_infernal_model_name"},
        "strand": {"type": ["string", "null"], "enum": ["plus", "minus", None]},
        "origin": {"type": ["string", "null"], "enum": ["newly_aligned", "inherited", "unknown", None]},
        "population": {"type": ["string", "null"], "enum": ["all", "newly_aligned", "inherited", "reported", "included", None]},
        "column_index": {"type": ["integer", "null"], "minimum": 0},
        "pair_columns": pair,
        "status": {"type": "string", "enum": ["published", "unbound", "invalid"]},
        "measurements": {"type": "array", "items": _object({"name": metric, "value": {"type": "number"}})},
        "unavailable": {"type": "array", "items": _object({"name": metric,
            "reason": {"type": "string", "enum": ["missing_input", "incompatible_input", "invalid_native_row", "not_measured"]}})},
    })


NATIVE_INFERNAL_ROW_SCHEMA = {"anyOf": [row_schema(f) for f in NATIVE_INFERNAL_METRICS]}


def native_infernal_fact_sources():
    return {source: {"type": "array", "meaning":
        "Requested native Infernal quantities with their original sequence/model associations. "
        "Search spans are not aligned-residue coverage. Alignment gaps are not automatically deletions. "
        "Column and pair denominators retain the explicitly selected population. "
        "Unbound rows retain measurements without inventing an annotation target. No annotation score.",
        "report_schema": {"type": "array", "items": row_schema(family), "x-source": source}}
        for family, source in FAMILY_SOURCES.items()}


def measurement_values(score, *, family):
    """Select existing fields without recomputing a scientific quantity."""
    values = dict(score)
    if family == "search_hit":
        values.update(score.get("components") or {})
        values.update(score.get("denominators") or {})
    elif family == "alignment_pair":
        values.update({"excluded_" + name + "_rows": value
                       for name, value in (score.get("excluded") or {}).items()})
    return values


def projected_measurements(score, metrics, *, family):
    if family not in NATIVE_INFERNAL_METRICS or any(
            name not in NATIVE_INFERNAL_METRICS[family] for name in metrics):
        raise ContractError("native_infernal_projection_metric_invalid")
    if len(set(metrics)) != len(metrics):
        raise ContractError("native_infernal_projection_metric_duplicate")
    values = measurement_values(score, family=family)
    measured, unavailable = [], []
    reasons = score.get("unavailable") or {}
    for name in metrics:
        value = values.get(name)
        if type(value) in (int, float) and math.isfinite(value):
            measured.append({"name": name, "value": value})
            continue
        reason = str(reasons.get(name, "")) if isinstance(reasons, dict) else ""
        if score.get("status") == "invalid":
            category = "invalid_native_row"
        elif any(word in reason for word in ("conflict", "incompatible", "ambiguous", "mismatch")):
            category = "incompatible_input"
        elif any(word in reason for word in ("unvisited", "traceback", "not_measured")):
            category = "not_measured"
        else:
            category = "missing_input"
        unavailable.append({"name": name, "reason": category})
    return measured, unavailable


__all__ = ["NATIVE_INFERNAL_METRICS", "COLLECTIONS", "FAMILY_SOURCES",
    "IDENTIFIER_NAMESPACES",
    "NATIVE_INFERNAL_RESULT_SELECTOR_SCHEMA", "NATIVE_INFERNAL_ROW_SCHEMA",
    "families_for_program", "validate_native_infernal_result_selector",
    "native_infernal_fact_sources", "row_schema", "measurement_values", "projected_measurements"]
