"""Deterministic components from saved native report sheets; no parsing or I/O."""
from __future__ import annotations

from copy import deepcopy

from .rfam_batch_contracts import rfam_digest, validate_rfam_parameters
from .rfam_batch_grader import union_length
from .rfam_batch_report_contracts import (
    REPORT_CALCULATION_VERSION, RFAM_REPORT_HIT_METRICS, RFAM_QUERY_STRAND_METRICS,
    RFAM_ALIGNMENT_COUNT_FIELDS, validate_rfam_report_sheet,
)

_NATIVE_FIELDS = {"native_rank": "rank", "native_score_bits": "score", "native_evalue": "evalue",
    "native_bias_bits": "bias", "native_gc_fraction": "gc", "native_alignment_accuracy": "accuracy",
    "native_start_1i": "query_from", "native_end_1i": "query_to",
    "native_model_from_1i": "model_from", "native_model_to_1i": "model_to"}


def calculate_rfam_batch_report_components(sheet, *, parameters) -> dict:
    """Use all reported rows, with separate occurrence/strand coordinate unions.

Rows retain duplicate multiplicity. Native model span includes a model local
end; represented positions exclude all abbreviated columns. Full model length
and model coverage require absent metadata and remain null. A missing or
invalid correspondence cannot turn into a measured zero. Complete zero-hit
populations yield zero span; an incomplete empty population remains unknown.
"""
    parameters = validate_rfam_parameters(parameters)
    sheet = validate_rfam_report_sheet(sheet)
    queries = {q["query_occurrence_key"]: q for q in sheet["input_identity"]["queries"]}
    hits = []
    groups = {}
    for hit in sheet["hits"]:
        values = dict.fromkeys(RFAM_REPORT_HIT_METRICS)
        missing = {k: "identity_rejected" for k in values}
        query = queries.get(hit["query_occurrence_key"])
        native = hit["native"]
        if query is not None:
            values["query_length_nt"] = query["submitted_length_nt"]
            missing = {k: "not_reported" for k in values}
            for metric, cell in _NATIVE_FIELDS.items():
                values[metric] = None if cell in hit["missing"] else native[cell]
                missing[metric] = hit["missing"].get(cell, "invalid_native_value")
            start, end = values["native_start_1i"], values["native_end_1i"]
            if (start is not None and end is not None and hit["strand"] in {"+", "-"}
                    and 1 <= start <= query["submitted_length_nt"] and 1 <= end <= query["submitted_length_nt"]
                    and (start <= end if hit["strand"] == "+" else start >= end)):
                values["query_span_nt"] = abs(end - start) + 1
                values["query_span_fraction"] = values["query_span_nt"] / query["submitted_length_nt"]
            else:
                missing["query_span_nt"] = missing["query_span_fraction"] = "coordinates_invalid"
            mstart, mend = values["native_model_from_1i"], values["native_model_to_1i"]
            if mstart is not None and mend is not None and mstart <= mend:
                values["native_model_span_positions"] = mend - mstart + 1
            else:
                missing["native_model_span_positions"] = "coordinates_invalid" if mstart is not None or mend is not None else "not_reported"
            missing["model_length_positions"] = missing["model_coverage_fraction"] = "model_length_unavailable"
            correspondence = hit["correspondence"]
            alignment_fields = ("display_model_from", "display_model_to", "represented_model_positions",
                "represented_query_positions", "model_consensus_equal_fraction", *RFAM_ALIGNMENT_COUNT_FIELDS)
            if correspondence is not None and correspondence["status"] in {"complete", "partial"}:
                values.update({k: correspondence[k] for k in (*RFAM_ALIGNMENT_COUNT_FIELDS, "display_model_from", "display_model_to")})
                values["represented_model_positions"] = union_length(correspondence["aligned_model_intervals"])
                values["represented_query_positions"] = union_length(correspondence["aligned_query_intervals"])
                compared = values["model_consensus_compared_count"]
                if compared:
                    values["model_consensus_equal_fraction"] = values["model_consensus_equal_count"] / compared
                else:
                    missing["model_consensus_equal_fraction"] = "no_determinate_pairs"
            else:
                reason = hit["missing"].get("correspondence", "alignment_unsupported" if correspondence is not None and correspondence["status"] == "unsupported" else "alignment_conflict")
                missing.update({k: reason for k in alignment_fields})
        row = {k: hit[k] for k in ("hit_key", "query_occurrence_key", "native_query_name", "model_name", "family_accession", "strand")}
        row.update(values, missing={k: missing[k] for k, v in values.items() if v is None})
        hits.append(row)
        if query is not None and hit["strand"] in {"+", "-"}:
            groups.setdefault((hit["query_occurrence_key"], hit["strand"]), []).append(row)
    strands = []
    for query in sheet["input_identity"]["queries"]:
        for strand in ("+", "-"):
            rows = groups.get((query["query_occurrence_key"], strand), [])
            valid = [row for row in rows if row["query_span_nt"] is not None]
            complete = sheet["population_complete"] and len(valid) == len(rows)
            values = dict.fromkeys(RFAM_QUERY_STRAND_METRICS)
            values["query_length_nt"] = query["submitted_length_nt"]
            if rows or sheet["population_complete"]:
                values["selected_row_count"], values["valid_interval_row_count"] = len(rows), len(valid)
            if valid or complete:
                total = sum(row["query_span_nt"] for row in valid)
                union = union_length([[min(row["native_start_1i"], row["native_end_1i"]) - 1,
                    max(row["native_start_1i"], row["native_end_1i"])] for row in valid])
                values.update(query_strand_sum_span_nt=total, query_strand_union_span_nt=union,
                    query_strand_overlap_excess_nt=total - union)
                if complete:
                    values["query_strand_union_fraction"] = union / query["submitted_length_nt"]
            strands.append(dict(query_occurrence_key=query["query_occurrence_key"], strand=strand,
                population_complete=complete, **values,
                missing={k: "partial_body" for k, v in values.items() if v is None}))
    return dict(version=REPORT_CALCULATION_VERSION, sheet_digest=rfam_digest(sheet),
        parameters=deepcopy(parameters), hits=hits, query_strands=strands,
        population_complete=sheet["population_complete"], issues=deepcopy(sheet["issues"]))


__all__ = ["calculate_rfam_batch_report_components"]
