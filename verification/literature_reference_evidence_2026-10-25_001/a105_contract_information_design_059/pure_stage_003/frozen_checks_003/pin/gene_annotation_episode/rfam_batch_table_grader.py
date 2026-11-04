"""Rfam original-input populations composed with unchanged Infernal scores.

Native Infernal cells/calculations remain fully inspectable. This adds only
their explicit original-query associations, sum/union excess, and both-strand
rows for the complete submitted population. No acquisition or parsing occurs.
"""
from __future__ import annotations

from copy import deepcopy

from .domain import ContractError
from .infernal_search_grader import calculate_infernal_search_scores
from .rfam_batch_contracts import (RFAM_TABLE_HIT_METRICS, closed_object,
    finite_json_copy, is_int, is_number, rfam_digest)
from .rfam_batch_table import RfamBatchTableParseResult


VERSION = "rfam_batch_table_calculation_v1"
PARAMETERS = {"hit_scope": "reported"}


def validate_rfam_table_inputs(parsed):
    code = "rfam_projection_reference_conflict"
    parsed = finite_json_copy(parsed, code=code)
    closed_object(parsed, RfamBatchTableParseResult.__annotations__, code=code)
    if (parsed["version"] != "rfam_batch_tblout_parse_result_v1"
            or parsed["status"] not in {"complete", "partial"}
            or parsed["format"] != "infernal_tblout_1_cmscan_1_1_5"
            or type(parsed["sheet"]) is not dict
            or parsed["sheet"].get("schema") != "infernal_search_sheet_v1"
            or type(parsed["input_identity"]) is not dict):
        raise ContractError(code)
    queries = parsed["input_identity"].get("queries")
    bindings, populations = parsed["occurrence_bindings"], parsed["query_population"]
    if (type(queries) is not list or not queries or type(bindings) is not list
            or type(populations) is not list or len(bindings) != len(queries)
            or len(populations) != len(queries)
            or len(parsed["sheet"].get("sequence_metadata", [])) != len(queries)):
        raise ContractError(code)
    seen = set()
    for index, (query, binding, population, metadata) in enumerate(zip(
            queries, bindings, populations, parsed["sheet"]["sequence_metadata"])):
        key = query.get("query_occurrence_key")
        if (type(key) is not str or not key or key in seen
                or binding != {"sequence_metadata_index": index,
                    "native_query_name": query.get("native_query_name"),
                    "query_occurrence_key": key, "selected_occurrence_ordinal": index}
                or query.get("selected_occurrence_ordinal") != index
                or population.get("query_occurrence_key") != key
                or population.get("submitted_length_nt") != query.get("submitted_length_nt")
                or not is_int(query.get("submitted_length_nt"), minimum=1)
                or type(population.get("reported_set_complete")) is not bool
                or population.get("reported_row_count") is not None and not is_int(population["reported_row_count"])
                or metadata.get("name") != query.get("native_query_name")
                or metadata.get("length") != query["submitted_length_nt"]
                or metadata.get("sequence") != query.get("submitted_sequence")):
            raise ContractError(code)
        seen.add(key)
    return parsed


def _index(identity, queries):
    if type(identity) is not dict or identity.get("kind") != "supplied_sequence_metadata":
        return None
    index = identity.get("metadata_index")
    if not is_int(index) or index >= len(queries):
        raise ContractError("rfam_projection_reference_conflict")
    return index


def calculate_rfam_batch_table_components(parsed, *, parameters):
    """Calculate from saved cells; missing model/alignment quantities stay null.

    Sum-span counts multiplicity; excess=sum-span-union-span. Both derive from
    Infernal's validated physical query intervals, separately per occurrence and
    strand. A complete input with no reported rows has measured zero spans;
    an incomplete absent population is unknown. Table spans never become
    represented alignment positions or consensus identity.
    """
    parsed = validate_rfam_table_inputs(parsed)
    if finite_json_copy(parameters) != PARAMETERS:
        raise ContractError("rfam_parameters_invalid")
    sheet = parsed["sheet"]
    native = calculate_infernal_search_scores(sheet, parameters=parameters)
    queries = parsed["input_identity"]["queries"]
    model_reason = ("model_metadata_conflict" if any(
        issue["code"] == "rfam_batch_model_metadata_invalid" for issue in parsed["issues"])
        else "model_length_unavailable")
    native_by_id = {row["hit_id"]: row for row in sheet["hits"]}
    if len(native_by_id) != len(sheet["hits"]):
        raise ContractError("rfam_projection_reference_conflict")
    hits, grouped = [], {}
    for row in native["hits"]:
        original = native_by_id[row["hit_id"]]
        index = _index(row.get("sequence", {}).get("identity"), queries)
        values = {key: None for key in RFAM_TABLE_HIT_METRICS}
        missing = {key: "identity_rejected" if index is None else "not_reported" for key in RFAM_TABLE_HIT_METRICS}
        key = None if index is None else queries[index]["query_occurrence_key"]
        if index is not None:
            if row["sequence"].get("name") != queries[index]["native_query_name"]:
                raise ContractError("rfam_projection_reference_conflict")
            values.update(native_score_bits=row["components"]["bitscore"],
                native_evalue=row["components"]["evalue"], native_gc_fraction=row["components"]["gc_fraction"],
                native_start_1i=original["sequence_from"], native_end_1i=original["sequence_to"],
                query_length_nt=queries[index]["submitted_length_nt"],
                query_span_nt=row["components"]["sequence_span_length"],
                query_span_fraction=row["components"]["sequence_span_fraction"],
                model_length_positions=row["denominators"]["consensus_length"],
                native_bias_bits=row["components"]["bias_bits"],
                native_model_from_1i=original["model_from"] if row["model_interval"] is not None else None,
                native_model_to_1i=original["model_to"] if row["model_interval"] is not None else None,
                native_model_span_positions=row["components"]["model_span_length"],
                native_model_span_fraction=row["components"]["model_span_fraction"])
            for name in ("native_score_bits", "native_evalue", "native_gc_fraction", "native_bias_bits"):
                missing[name] = "invalid_native_value"
            for name in ("native_start_1i", "native_end_1i", "query_span_nt", "query_span_fraction"):
                missing[name] = "coordinates_invalid"
            missing["model_length_positions"] = missing["model_coverage_fraction"] = model_reason
            missing["native_model_span_fraction"] = model_reason
            for name in ("native_model_from_1i", "native_model_to_1i", "native_model_span_positions"):
                missing[name] = "coordinates_invalid"
            if row["strand"] in {"+", "-"}:
                grouped.setdefault((index, row["strand"]), []).append(row)
        hits.append({"hit_key": row["hit_id"], "query_occurrence_key": key,
            "family_accession": row.get("model", {}).get("accession"), "strand": row["strand"],
            **values, "missing": {name: missing[name] for name, value in values.items() if value is None}})
    aggregates = {}
    for row in native["sequence_strand_aggregates"]:
        index = _index(row.get("sequence_identity"), queries)
        if index is not None:
            key = index, row["strand"]
            if key in aggregates:
                raise ContractError("rfam_projection_reference_conflict")
            aggregates[key] = row
    strands = []
    for index, (query, population) in enumerate(zip(queries, parsed["query_population"])):
        for strand in ("+", "-"):
            rows = grouped.get((index, strand), [])
            aggregate = aggregates.get((index, strand))
            complete = population["reported_set_complete"]
            if aggregate is None:
                if rows:
                    raise ContractError("rfam_projection_reference_conflict")
                count = valid = total = union = fraction = excess = 0 if complete else None
            else:
                count = aggregate["hit_count"]
                valid = count - aggregate["invalid_geometry_count"]
                spans = [r["components"]["sequence_span_length"] for r in rows
                         if r["selected_for_aggregate"] and r["sequence_interval"] is not None]
                total = sum(spans) if spans or not count else None
                union = aggregate["union_numerator"]
                fraction = aggregate["union_span_fraction"]
                excess = total - union if total is not None and union is not None else None
                complete = complete and aggregate["complete_for_selected_population"]
                if not complete:
                    fraction = None
            strands.append({"query_occurrence_key": query["query_occurrence_key"], "strand": strand,
                "query_length_nt": query["submitted_length_nt"], "selected_row_count": count,
                "valid_interval_row_count": valid, "query_strand_sum_span_nt": total,
                "query_strand_union_span_nt": union, "query_strand_union_fraction": fraction,
                "query_strand_overlap_excess_nt": excess, "population_complete": complete})
    return {"version": VERSION, "sheet_digest": rfam_digest(sheet), "parse_digest": rfam_digest(parsed),
        "parameters": deepcopy(parameters), "native_calculation": native,
        "hits": hits, "query_strands": strands,
        "population_complete": all(row["reported_set_complete"] for row in parsed["query_population"])}


__all__ = ["calculate_rfam_batch_table_components", "validate_rfam_table_inputs", "VERSION", "PARAMETERS"]
