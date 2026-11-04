"""Deterministic Rfam components calculated only from a supplied saved sheet.

Inclusive query spans, strand-specific unions and overlap multiplicity describe
the returned hit population. They do not sum bit scores, assume independent
families, infer annotation correctness, or reacquire any missing denominator.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .domain import ContractError
from .rfam_batch_contracts import (
    RFAM_HIT_METRICS, RFAM_MISSING_REASONS, RfamBatchSheet, RfamCalculationParameters,
    RfamCalculationResult, closed_object, finite_json_copy, is_int, is_number,
    is_text, rfam_digest, validate_issue, validate_rfam_alignment_result,
    validate_rfam_capture, validate_rfam_input_identity, validate_rfam_parameters)


HIT_FIELDS = frozenset(("hit_key", "native_json_pointer", "document_ordinal", "family_list_ordinal",
    "query_occurrence_key", "family_name", "family_accession", "identity_valid", "native", "query_length_nt",
    "query_interval", "query_coordinates_valid", "model_metadata_ref", "model_length_positions",
    "alignment_components", "duplicate_of", "missing", "issues"))
CALCULATED_HIT_METRICS = RFAM_HIT_METRICS


def union_length(intervals):
    """Measure a half-open union; no expansion to one item per nucleotide."""
    total, boundary = 0, -1
    for start, end in sorted(intervals):
        total += max(0, end - max(start, boundary))
        boundary = max(end, boundary)
    return total


def validate_rfam_sheet(sheet):
    """Validate saved-sheet relationships without opening the raw artifact."""
    code = "rfam_sheet_invalid"
    sheet = finite_json_copy(sheet, code=code)
    closed_object(sheet, RfamBatchSheet.__annotations__, code=code)
    if sheet["schema_version"] != "rfam_batch_sheet_v1":
        raise ContractError(code)
    identity, capture = validate_rfam_input_identity(sheet["input"]), validate_rfam_capture(sheet["source"])
    closed_object(sheet["job"], ("job_id", "opened", "started", "closed"), code=code)
    closed_object(sheet["format_metadata"], ("native_program", "native_program_version", "rfam_release", "search_space_nt",
        "searched_model_count", "reporting_thresholds", "inclusion_thresholds", "native_model_mode"), code=code)
    if (capture["request_job_id"] != identity["expected_job_id"] or sheet["job"]["job_id"] != identity["expected_job_id"]
            or capture["request_sequence_sha256"] != identity["submitted_sequence_sha256"]
            or capture["representation"] != "json" or capture["http_status"] not in (None, 200)
            or capture["evidence_kind"] == "native_response" and capture["http_status"] is None):
        raise ContractError(code)
    if any(sheet["job"][k] is not None and type(sheet["job"][k]) is not str for k in ("opened", "started", "closed")):
        raise ContractError(code)
    population = sheet["population"]
    closed_object(population, ("native_reported_count", "observed_row_count", "family_bucket_count", "count_agrees",
        "body_complete", "result_identity_matches", "reported_set_complete", "provider_filtering_known", "all_model_hits_complete"), code=code)
    if (population["result_identity_matches"] is not True or population["body_complete"] != capture["body_complete"]
            or type(sheet["hits"]) is not list or type(sheet["issues"]) is not list
            or population["observed_row_count"] != len(sheet["hits"])
            or not is_int(population["observed_row_count"]) or not is_int(population["family_bucket_count"])
            or population["native_reported_count"] is not None and not is_int(population["native_reported_count"])
            or any(type(population[k]) is not bool for k in ("count_agrees", "body_complete", "result_identity_matches", "reported_set_complete"))
            or population["reported_set_complete"] and (not population["body_complete"] or not population["count_agrees"])
            or population["count_agrees"] and population["native_reported_count"] != len(sheet["hits"])):
        raise ContractError(code)
    for issue in sheet["issues"]:
        validate_issue(issue)
    known = {}
    for ordinal, row in enumerate(sheet["hits"]):
        closed_object(row, HIT_FIELDS, code=code)
        closed_object(row["native"], ("start", "end", "strand", "score_bits", "evalue", "gc_fraction"), code=code)
        if (row["document_ordinal"] != ordinal or not is_int(row["document_ordinal"])
                or not is_int(row["family_list_ordinal"]) or type(row["family_name"]) is not str
                or row["query_occurrence_key"] != identity["query_occurrence_key"]
                or row["query_length_nt"] != identity["submitted_length_nt"] or not is_int(row["query_length_nt"], minimum=1)
                or type(row["identity_valid"]) is not bool or type(row["query_coordinates_valid"]) is not bool
                or row["hit_key"] in known or row["hit_key"] != capture["artifact_ref"] + row["native_json_pointer"]
                or type(row["missing"]) is not dict or type(row["issues"]) is not list
                or any(not is_text(k) or v not in RFAM_MISSING_REASONS for k, v in row["missing"].items())):
            raise ContractError(code)
        pointer = "/hits/" + row["family_name"].replace("~", "~0").replace("/", "~1") + "/" + str(row["family_list_ordinal"])
        if row["native_json_pointer"] != pointer:
            raise ContractError(code)
        if row["family_accession"] is not None and (type(row["family_accession"]) is not str or re.fullmatch(r"RF[0-9]{5}", row["family_accession"]) is None):
            raise ContractError(code)
        if row["identity_valid"] and (not row["family_name"] or row["family_accession"] is None):
            raise ContractError(code)
        native = row["native"]
        for key in ("start", "end"):
            if native[key] is not None and type(native[key]) is not int:
                raise ContractError(code)
        if native["strand"] is not None and native["strand"] not in ("+", "-"):
            raise ContractError(code)
        for key in ("score_bits", "evalue", "gc_fraction"):
            if native[key] is not None and not is_number(native[key]):
                raise ContractError(code)
        if (native["evalue"] is not None and native["evalue"] < 0
                or native["gc_fraction"] is not None and not 0 <= native["gc_fraction"] <= 1):
            raise ContractError(code)
        if row["query_coordinates_valid"]:
            start, end, strand = native["start"], native["end"], native["strand"]
            if (not is_int(start, minimum=1) or not is_int(end, minimum=1)
                    or max(start, end) > row["query_length_nt"] or strand not in ("+", "-")
                    or strand == "+" and start > end or strand == "-" and start < end
                    or row["query_interval"] != [min(start, end) - 1, max(start, end)]):
                raise ContractError(code)
        elif row["query_interval"] is not None:
            raise ContractError(code)
        if row["duplicate_of"] is not None:
            previous = known.get(row["duplicate_of"])
            if previous is None or previous["native"] != native or previous["family_accession"] != row["family_accession"]:
                raise ContractError(code)
        # This native profile cannot verify a searched-model denominator.
        # An altered saved value must not turn accession-only metadata into one.
        if row["model_metadata_ref"] is not None or row["model_length_positions"] is not None:
            raise ContractError("rfam_model_binding_unverified")
        if row["alignment_components"] is not None:
            component = validate_rfam_alignment_result(row["alignment_components"])
            if (component["hit_identity"] != {"artifact_ref": capture["artifact_ref"], "hit_key": row["hit_key"],
                    "query_occurrence_key": row["query_occurrence_key"], "family_accession": row["family_accession"]}
                    or component["query_strand"] != native["strand"]):
                raise ContractError("rfam_alignment_binding_conflict")
            if component["status"] in ("complete", "partial"):
                if (not row["query_coordinates_valid"] or component["display_query_from"] != native["start"]
                        or component["display_query_to"] != native["end"]
                        or any(a < row["query_interval"][0] or b > row["query_interval"][1]
                               for a, b in component["aligned_query_intervals"])):
                    raise ContractError("rfam_alignment_coordinate_conflict")
        for issue in row["issues"]:
            validate_issue(issue)
        known[row["hit_key"]] = row
    return sheet


def calculate_rfam_batch_components(sheet: RfamBatchSheet, *, parameters: RfamCalculationParameters) -> RfamCalculationResult:
    """Compute inspectable components; parameters are mandatory and explicit."""
    parameters = validate_rfam_parameters(parameters)
    sheet = validate_rfam_sheet(sheet)
    rows = []
    for native in sheet["hits"]:
        row = {"hit_key": native["hit_key"], "query_occurrence_key": native["query_occurrence_key"],
            "family_accession": native["family_accession"], "strand": native["native"]["strand"],
            **dict.fromkeys(CALCULATED_HIT_METRICS), "missing": {}}
        missing = row["missing"]
        if not native["identity_valid"]:
            row["family_accession"] = None
            missing.update({name: "identity_rejected" for name in CALCULATED_HIT_METRICS})
            rows.append(row)
            continue
        for name, cell in (("native_score_bits", "score_bits"), ("native_evalue", "evalue"), ("native_gc_fraction", "gc_fraction")):
            row[name] = native["native"][cell]
            if row[name] is None:
                missing[name] = native["missing"].get(name, "not_reported")
        row["query_length_nt"] = native["query_length_nt"]
        for name, cell in (("native_start_1i", "start"), ("native_end_1i", "end")):
            row[name] = native["native"][cell]
            if row[name] is None:
                missing[name] = native["missing"].get(name, "not_reported")
        if native["query_coordinates_valid"]:
            row["query_span_nt"] = native["query_interval"][1] - native["query_interval"][0]
            row["query_span_fraction"] = row["query_span_nt"] / native["query_length_nt"]
        else:
            missing.update(query_span_nt="coordinates_invalid", query_span_fraction="coordinates_invalid")
        alignment = native["alignment_components"]
        usable_alignment = alignment is not None and alignment["status"] in ("complete", "partial")
        if usable_alignment:
            intervals = alignment["aligned_model_intervals"]
            if intervals or alignment["status"] == "complete":
                row["represented_model_positions"] = union_length(intervals)
            for name in ("model_consensus_equal_count", "model_consensus_compared_count"):
                row[name] = alignment[name]
            for name in ("display_model_from", "display_model_to"):
                row[name] = alignment[name]
            compared, equal = row["model_consensus_compared_count"], row["model_consensus_equal_count"]
            if compared and equal is not None:
                row["model_consensus_equal_fraction"] = equal / compared
            elif compared == 0:
                missing["model_consensus_equal_fraction"] = "no_determinate_pairs"
        for name in ("display_model_from", "display_model_to", "represented_model_positions", "model_consensus_equal_count", "model_consensus_compared_count", "model_consensus_equal_fraction"):
            if row[name] is None and name not in missing:
                missing[name] = native["missing"].get(name, "alignment_unsupported" if usable_alignment else "alignment_not_parsed")
        row["model_length_positions"] = native["model_length_positions"]
        for name in ("model_length_positions", "model_coverage_fraction"):
            missing[name] = native["missing"].get(name, "model_length_unavailable")
        rows.append(row)
    valid = [r for r in sheet["hits"] if r["identity_valid"] and r["query_coordinates_valid"]]
    complete = sheet["population"]["reported_set_complete"]
    interval_complete = complete and len(valid) == len(sheet["hits"])
    occurrence = sheet["input"]["query_occurrence_key"]
    strands = []
    unknown_strand = any(r["native"]["strand"] is None for r in sheet["hits"])
    for strand in ("+", "-"):
        selected = [r for r in sheet["hits"] if r["native"]["strand"] == strand]
        strand_valid = [r for r in valid if r["native"]["strand"] == strand]
        intervals = [r["query_interval"] for r in strand_valid]
        total, union = sum(b - a for a, b in intervals), union_length(intervals)
        strands.append({"query_occurrence_key": occurrence, "strand": strand,
            "query_length_nt": sheet["input"]["submitted_length_nt"],
            "selected_row_count": len(selected), "valid_interval_row_count": len(strand_valid),
            "query_strand_sum_span_nt": total, "query_strand_union_span_nt": union,
            "query_strand_union_fraction": union / sheet["input"]["submitted_length_nt"],
            "query_strand_overlap_excess_nt": total - union,
            "population_complete": complete and not unknown_strand and len(selected) == len(strand_valid)})
    return {"version": "rfam_batch_calculation_v1", "sheet_digest": rfam_digest(sheet), "parameters": parameters,
        "population": {"query_occurrence_key": occurrence, "reported_row_count": len(sheet["hits"]),
            "valid_interval_row_count": len(valid), "duplicate_row_count": sum(r["duplicate_of"] is not None for r in sheet["hits"]),
            "reported_set_complete": complete, "interval_population_complete": interval_complete},
        "hits": rows, "query_strands": strands, "issues": deepcopy(sheet["issues"])}
