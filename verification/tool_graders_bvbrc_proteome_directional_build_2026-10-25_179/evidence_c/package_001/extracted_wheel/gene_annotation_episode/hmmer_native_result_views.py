"""Closed requested numerical projections of retained native HMMER rows.

These schemas and projections perform no acquisition, grading, publication or
credit calculation. Native order is the grader's retained row order; there is
no implicit ranking or threshold. Detailed missing-data reasons remain in the
saved sheet and calculations.
"""
from __future__ import annotations

from copy import deepcopy
import math

from .domain import ContractError, validate_schema
from .hmmer_graders import HMMER_DOMAIN_METRICS
from .native_hmmer_contracts import finite_json_copy


NATIVE_HMMER_METRICS = {
    "protein_domain": HMMER_DOMAIN_METRICS,
    "nucleotide_locus": (
        "native_score_bits", "native_bias_bits", "native_evalue", "native_accuracy",
        "model_length", "sequence_length", "model_span_positions", "sequence_span_positions",
        "sequence_envelope_positions", "model_span_coverage", "sequence_span_coverage",
        "sequence_envelope_coverage", "paired_positions", "insert_positions", "delete_positions",
        "alignment_columns", "paired_model_coverage", "paired_sequence_coverage",
        "posterior_lower_mean", "posterior_upper_mean"),
    "alignment_sequence": (
        "original_length", "model_length", "retained_residues", "match_state_residues",
        "deleted_model_positions", "insert_state_residues", "terminal_unaligned_residues",
        "missing_model_positions", "nonresidue_model_positions", "trimmed_residues",
        "model_occupancy", "sequence_match_coverage", "posterior_lower_mean",
        "posterior_upper_mean", "posterior_bounded_residue_count", "posterior_unavailable_residue_count"),
}
FAMILY_SOURCES = {"protein_domain": "execution_hmmer_domain_rows",
    "nucleotide_locus": "execution_nhmmer_locus_rows",
    "alignment_sequence": "execution_hmmalign_sequence_rows"}


def _object(properties):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


_KEY = {"type": "string", "minLength": 1}
_REF = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
_NULL_REF = {**_REF, "type": ["string", "null"]}
_ROWS = {"oneOf": [
    _object({"offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1}}),
    _object({"record_keys": {"type": "array", "minItems": 1, "uniqueItems": True, "items": _KEY}})]}
NATIVE_HMMER_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": "native_hmmer_result_selector_v1"},
    "acquisition": {"const": "complete_bound_bundle"},
    "projection": {"oneOf": [_object({"family": {"const": family}, "rows": _ROWS,
        "metrics": {"type": "array", "minItems": 1, "uniqueItems": True,
                    "items": {"enum": list(metrics)}}}) for family, metrics in NATIVE_HMMER_METRICS.items()]},
})


def family_for_program(program):
    if program in {"phmmer", "hmmscan", "hmmsearch", "jackhmmer"}:
        return "protein_domain"
    if program in {"nhmmer", "nhmmscan"}:
        return "nucleotide_locus"
    if program == "hmmalign":
        return "alignment_sequence"
    raise ContractError("native_hmmer_result_program_unsupported")


def validate_native_hmmer_result_selector(selector, *, program):
    selector = finite_json_copy(selector)
    try:
        validate_schema(selector, NATIVE_HMMER_RESULT_SELECTOR_SCHEMA)
    except ContractError as error:
        raise ContractError("native_hmmer_result_selector_invalid") from error
    if selector["projection"]["family"] != family_for_program(program):
        raise ContractError("native_hmmer_result_selector_family_mismatch")
    # JSON Schema considers 1.0 an integer; ordinal/index operands are integers.
    rows = selector["projection"]["rows"]
    if "offset" in rows and any(type(rows[k]) is not int for k in ("offset", "limit")):
        raise ContractError("native_hmmer_result_selector_integer_required")
    return selector


def row_schema(family):
    metric = {"type": "string", "enum": list(NATIVE_HMMER_METRICS[family])}
    return _object({
        "record_key": {"type": "string", "format": "identifier", "x-reference-namespace": "native_hmmer_row"},
        "source_ref": _REF, "observation_ref": _NULL_REF,
        "subject_ref": {"type": ["string", "null"], "format": "reference",
            "x-reference-namespace": "subject"},
        "reference_refs": {"type": "array", "uniqueItems": True, "items": _REF},
        **{key: {"type": ["integer", "null"], "minimum": 0}
           for key in ("query_occurrence", "target_occurrence", "iteration")},
        "strand": {"type": ["string", "null"], "enum": ["plus", "minus", None],
            "description": "Native strand '+' projects to plus and '-' projects to minus; null means strand was not applicable or unavailable. Native symbols remain in retained sheets."},
        "status": {"type": "string", "enum": ["published", "unbound", "invalid"]},
        "measurements": {"type": "array", "items": _object({"name": metric, "value": {"type": "number"}})},
        "unavailable": {"type": "array", "items": _object({"name": metric,
            "reason": {"type": "string", "enum": ["missing_input", "incompatible_input", "invalid_native_row", "not_measured"]}})},
    })


# A union permits all three families; each x-source has its narrower family enum.
NATIVE_HMMER_ROW_SCHEMA = {"anyOf": [row_schema(family) for family in NATIVE_HMMER_METRICS]}


def native_hmmer_fact_sources():
    return {source: {"type": "array", "meaning":
        "Explicitly selected native numerical rows with exact source and observation bindings. "
        "Unbound rows are measurements without an invented biological subject; unavailable values are not zero. "
        "Native occurrences and dependent rounds retain their original meanings. No annotation score.",
        "report_schema": {"type": "array", "items": row_schema(family), "x-source": source}}
        for family, source in FAMILY_SOURCES.items()}


def projected_measurements(score, metrics):
    """Only requested finite scalar values; retain a closed missingness class."""
    values, unavailable = [], []
    reasons = score.get("unavailable") or score.get("availability") or {}
    if not isinstance(reasons, dict):
        reasons = {}
    for name in metrics:
        value = score.get(name)
        if type(value) in (int, float) and math.isfinite(value):
            values.append({"name": name, "value": value})
            continue
        reason = str(reasons.get(name, ""))
        if score.get("status") == "invalid" or "row_invalid" in reason:
            category = "invalid_native_row"
        elif any(part in reason for part in ("invalid", "mismatch", "conflict", "incompatible", "ambiguous")):
            category = "incompatible_input"
        elif any(part in reason for part in ("input", "length", "denominator", "operand", "metadata", "trim")):
            category = "missing_input"
        else:
            category = "not_measured"
        unavailable.append({"name": name, "reason": category})
    return values, unavailable


__all__ = ["NATIVE_HMMER_RESULT_SELECTOR_SCHEMA", "NATIVE_HMMER_METRICS", "NATIVE_HMMER_ROW_SCHEMA",
           "validate_native_hmmer_result_selector", "native_hmmer_fact_sources"]
