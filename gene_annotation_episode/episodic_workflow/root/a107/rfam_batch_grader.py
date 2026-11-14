"""Common-calculator delegate and unchanged saved-v1 JSON validation helpers."""
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


def calculate_rfam_batch_components(sheet: RfamBatchSheet, *, parameters: RfamCalculationParameters) -> dict:
    """Delegate new calculations; explicit legacy conversion is a separate API."""
    from . import infernal_search_grader
    from .rfam_batch_infernal import select_rfam_common_sheet
    validate_rfam_parameters(parameters)
    sheet = select_rfam_common_sheet(sheet, representation="json")
    return infernal_search_grader.calculate_infernal_search_scores(sheet, parameters={"hit_scope": "reported"})
