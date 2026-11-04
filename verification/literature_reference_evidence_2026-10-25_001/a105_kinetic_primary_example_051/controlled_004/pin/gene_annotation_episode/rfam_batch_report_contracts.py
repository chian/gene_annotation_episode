"""Closed native cmscan-report contracts, separate from the Rfam JSON schema.

All coordinates in native cells are one-based inclusive; represented intervals
and paired positions are zero-based, half-open/physical. Unknown RF accessions,
model releases and full-model lengths are never inferred from model names or
display endpoints. See REPORT_METRIC_DEFINITIONS for each numerical meaning.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from .domain import ContractError, validate_schema
from .rfam_batch_table import (
    RFAM_BATCH_TABLE_ISSUE_CODES, RfamBatchFileInputIdentity,
    RfamBatchTableCapture, RfamBatchTableIssue, RfamReportMembership,
)

REPORT_FORMAT = "rfam_cmscan_batch_report_1_1_5"
REPORT_PARSE_VERSION = "rfam_batch_report_parse_result_v1"
REPORT_SHEET_VERSION = "rfam_batch_report_sheet_v1"
REPORT_CALCULATION_VERSION = "rfam_batch_report_calculation_v1"
REPORT_CORRESPONDENCE_VERSION = "rfam_batch_report_correspondence_v1"
RFAM_ALIGNMENT_COUNT_FIELDS = (
    "model_consensus_compared_count", "model_consensus_equal_count", "query_insert_count",
    "model_delete_count", "truncated_model_count_5p", "truncated_model_count_3p",
    "local_end_model_omitted_count", "local_end_query_count")
RFAM_HIT_METRICS = (
    "native_score_bits", "native_evalue", "native_gc_fraction", "native_start_1i", "native_end_1i",
    "query_length_nt", "query_span_nt", "query_span_fraction", "display_model_from", "display_model_to",
    "represented_model_positions", "model_length_positions", "model_coverage_fraction",
    "model_consensus_equal_count", "model_consensus_compared_count", "model_consensus_equal_fraction")
RFAM_QUERY_STRAND_METRICS = (
    "query_length_nt", "selected_row_count", "valid_interval_row_count", "query_strand_sum_span_nt",
    "query_strand_union_span_nt", "query_strand_union_fraction", "query_strand_overlap_excess_nt")
RFAM_METRIC_UNITS = dict(zip(RFAM_HIT_METRICS, (
    "bits", "expected_hits", "fraction", "nt_position_1i", "nt_position_1i", "nt", "nt", "fraction",
    "model_position_1i", "model_position_1i", "model_positions", "model_positions", "fraction",
    "comparisons", "comparisons", "fraction"))) | dict(zip(RFAM_QUERY_STRAND_METRICS, (
    "nt", "rows", "rows", "nt", "nt", "fraction", "nt")))
RFAM_MISSING_REASONS = frozenset("""
not_reported invalid_native_value identity_rejected coordinates_invalid
alignment_not_parsed alignment_missing alignment_unsupported alignment_conflict
model_length_unavailable model_binding_unverified model_metadata_conflict
no_determinate_pairs partial_body format_unverified
""".split())
RFAM_REPORT_ISSUE_CODES = RFAM_BATCH_TABLE_ISSUE_CODES | frozenset("""
rfam_report_row_invalid rfam_report_cell_invalid rfam_report_cell_conflict
rfam_report_rank_ambiguous rfam_report_summary_missing rfam_report_alignment_missing
rfam_report_summary_unmatched rfam_report_display_invalid
rfam_report_display_model_conflict rfam_report_display_query_conflict
rfam_report_coordinates_invalid rfam_report_native_header_unsupported
rfam_alignment_missing rfam_alignment_invalid rfam_alignment_unsupported
rfam_alignment_query_conflict rfam_alignment_coordinate_conflict
rfam_alignment_correspondence_unrepresented
""".split())
RFAM_REPORT_MISSING_REASONS = RFAM_MISSING_REASONS | {"native_cell_conflict", "ambiguous_rank"}
RFAM_REPORT_HIT_METRICS = (*RFAM_HIT_METRICS,
    "native_bias_bits", "native_alignment_accuracy", "native_rank",
    "native_model_from_1i", "native_model_to_1i", "native_model_span_positions",
    "represented_query_positions", "query_insert_count", "model_delete_count",
    "truncated_model_count_5p", "truncated_model_count_3p",
    "local_end_model_omitted_count", "local_end_query_count")
RFAM_REPORT_METRICS = {"hit": RFAM_REPORT_HIT_METRICS, "query_strand": RFAM_QUERY_STRAND_METRICS}
RFAM_REPORT_METRIC_UNITS = {**RFAM_METRIC_UNITS,
    "native_bias_bits": "bits", "native_alignment_accuracy": "fraction", "native_rank": "rank",
    "native_model_from_1i": "model_position_1i", "native_model_to_1i": "model_position_1i",
    "native_model_span_positions": "model_positions", "represented_query_positions": "nt",
    "query_insert_count": "nt", "model_delete_count": "model_positions",
    "truncated_model_count_5p": "model_positions", "truncated_model_count_3p": "model_positions",
    "local_end_model_omitted_count": "model_positions", "local_end_query_count": "nt"}
def _object(properties):
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}


_ROWS = {"oneOf": [
    _object({"offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1}}),
    _object({"record_keys": {"type": "array", "minItems": 1, "uniqueItems": True,
                             "items": {"type": "string", "minLength": 1}}})]}
RFAM_REPORT_PROJECTION_SCHEMA = {"oneOf": [
    _object({"family": {"const": family}, "rows": _ROWS,
        "metrics": {"type": "array", "minItems": 1, "uniqueItems": True,
                    "items": {"enum": list(metrics)}}})
    for family, metrics in RFAM_REPORT_METRICS.items()]}


class RfamReportSourceLine(TypedDict):
    line: int
    text: str


class RfamReportDisplayBlock(TypedDict):
    source_lines: list[RfamReportSourceLine]
    model_line: int
    query_line: int
    model_from: int
    model_to: int
    query_from: int | None
    query_to: int | None
    model_text: str
    query_text: str
    nc: str | None
    cs: str | None
    match: str | None
    pp: str | None
    rf: str | None


class RfamBatchReportCorrespondence(TypedDict):
    version: str
    status: Literal["complete", "partial", "invalid", "unsupported"]
    display_model_from: int | None
    display_model_to: int | None
    display_query_from: int | None
    display_query_to: int | None
    segments: list[dict]
    paired_positions: list[dict]
    aligned_model_intervals: list[list[int]]
    aligned_query_intervals: list[list[int]]
    posterior_segments: list[dict]
    model_consensus_compared_count: int | None
    model_consensus_equal_count: int | None
    query_insert_count: int | None
    model_delete_count: int | None
    truncated_model_count_5p: int | None
    truncated_model_count_3p: int | None
    local_end_model_omitted_count: int | None
    local_end_query_count: int | None
    blocks: list[RfamReportDisplayBlock]
    issues: list[RfamBatchTableIssue]


class RfamReportNativeCells(TypedDict):
    rank: int | None
    inclusion: str | None
    evalue: float | None
    score: float | None
    bias: float | None
    model_type: str | None
    model_from: int | None
    model_to: int | None
    query_from: int | None
    query_to: int | None
    model_boundary: str | None
    query_boundary: str | None
    accuracy: float | None
    truncation: str | None
    gc: float | None


class RfamReportRawCells(TypedDict):
    score: dict[str, str]
    alignment: dict[str, str]


class RfamBatchReportHit(TypedDict):
    hit_key: str
    query_occurrence_key: str | None
    native_query_name: str
    model_name: str | None
    family_accession: str | None
    strand: str | None
    query_header_line: int
    score_line: int | None
    alignment_header_line: int | None
    alignment_summary_line: int | None
    native: RfamReportNativeCells
    raw_cells: RfamReportRawCells
    source_lines: list[RfamReportSourceLine]
    correspondence: RfamBatchReportCorrespondence | None
    missing: dict[str, str]
    issues: list[RfamBatchTableIssue]


class RfamBatchReportSheet(TypedDict):
    schema_version: str
    capture: RfamBatchTableCapture
    input_identity: RfamBatchFileInputIdentity
    membership: RfamReportMembership
    hits: list[RfamBatchReportHit]
    population_complete: bool
    issues: list[RfamBatchTableIssue]


class RfamBatchReportParseResult(TypedDict):
    version: str
    status: Literal["complete", "partial", "rejected", "unsupported"]
    format: str
    sheet: RfamBatchReportSheet | None
    issues: list[RfamBatchTableIssue]


_HIT_CALC_IDENTITY = {"hit_key": str, "query_occurrence_key": str | None,
    "native_query_name": str, "model_name": str | None, "family_accession": str | None,
    "strand": str | None, "missing": dict[str, str]}
RfamBatchReportHitCalculation = TypedDict("RfamBatchReportHitCalculation", {
    **_HIT_CALC_IDENTITY, **{name: float | int | None for name in RFAM_REPORT_HIT_METRICS}})
RfamBatchReportQueryStrandCalculation = TypedDict("RfamBatchReportQueryStrandCalculation", {
    "query_occurrence_key": str, "strand": str, "population_complete": bool,
    "missing": dict[str, str], **{name: float | int | None for name in RFAM_QUERY_STRAND_METRICS}})


class RfamBatchReportCalculation(TypedDict):
    version: str
    sheet_digest: str
    parameters: dict
    hits: list[RfamBatchReportHitCalculation]
    query_strands: list[RfamBatchReportQueryStrandCalculation]
    population_complete: bool
    issues: list[RfamBatchTableIssue]


def report_issue(code, *, field=None, native_query_name=None, source_line=None, severity="error"):
    if code not in RFAM_REPORT_ISSUE_CODES:
        raise ContractError("rfam_sheet_invalid")
    return dict(code=code, severity=severity, field=field,
                native_query_name=native_query_name, source_line=source_line)


def validate_rfam_report_projection(value):
    from .rfam_batch_contracts import finite_json_copy, is_int
    value = finite_json_copy(value, code="rfam_projection_invalid")
    try:
        validate_schema(value, RFAM_REPORT_PROJECTION_SCHEMA)
    except (ContractError, TypeError) as error:
        raise ContractError("rfam_projection_invalid") from error
    if "offset" in value["rows"] and (not is_int(value["rows"]["offset"])
            or not is_int(value["rows"]["limit"], minimum=1)):
        raise ContractError("rfam_projection_invalid")
    return value


def _validate_issues(items, code):
    from .rfam_batch_contracts import closed_object, is_int, is_text
    if type(items) is not list:
        raise ContractError(code)
    for item in items:
        closed_object(item, RfamBatchTableIssue.__annotations__, code=code)
        if (item["code"] not in RFAM_REPORT_ISSUE_CODES or item["severity"] not in {"error", "warning"}
                or any(item[k] is not None and not is_text(item[k]) for k in ("field", "native_query_name"))
                or item["source_line"] is not None and not is_int(item["source_line"], minimum=1)):
            raise ContractError(code)


def _validate_lines(lines, code):
    from .rfam_batch_contracts import closed_object, is_int
    if type(lines) is not list:
        raise ContractError(code)
    previous = 0
    result = {}
    for row in lines:
        closed_object(row, RfamReportSourceLine.__annotations__, code=code)
        if (not is_int(row["line"], minimum=previous + 1) or type(row["text"]) is not str
                or not row["text"].isascii() or any(c in row["text"] for c in "\x00\r\n")):
            raise ContractError(code)
        previous = row["line"]
        result[row["line"]] = row["text"]
    return result


def _validate_correspondence(value, hit, query, source, code):
    from .rfam_batch_contracts import closed_object, is_int, is_number
    closed_object(value, RfamBatchReportCorrespondence.__annotations__, code=code)
    if (value["version"] != REPORT_CORRESPONDENCE_VERSION
            or value["status"] not in {"complete", "partial", "invalid", "unsupported"}):
        raise ContractError(code)
    _validate_issues(value["issues"], code)
    for field in RFAM_ALIGNMENT_COUNT_FIELDS:
        if value[field] is not None and not is_int(value[field]):
            raise ContractError(code)
    for field in ("display_model_from", "display_model_to", "display_query_from", "display_query_to"):
        if value[field] is not None and not is_int(value[field], minimum=1):
            raise ContractError(code)
    arrays = ("segments", "paired_positions", "aligned_model_intervals", "aligned_query_intervals", "posterior_segments", "blocks")
    if any(type(value[k]) is not list for k in arrays):
        raise ContractError(code)
    for block in value["blocks"]:
        closed_object(block, RfamReportDisplayBlock.__annotations__, code=code)
        retained = _validate_lines(block["source_lines"], code)
        if any(source.get(n) != text for n, text in retained.items()):
            raise ContractError(code)
        if (any(not is_int(block[k], minimum=1) or block[k] not in retained for k in ("model_line", "query_line"))
                or block["model_line"] >= block["query_line"]
                or not is_int(block["model_from"], minimum=1) or not is_int(block["model_to"])
                or any(block[k] is not None and not is_int(block[k], minimum=1) for k in ("query_from", "query_to"))
                or (block["query_from"] is None) != (block["query_to"] is None)
                or any(type(block[k]) is not str for k in ("model_text", "query_text"))
                or len(block["model_text"]) != len(block["query_text"])
                or any(block[k] is not None and (type(block[k]) is not str or len(block[k]) != len(block["model_text"]))
                       for k in ("nc", "cs", "match", "pp", "rf"))):
            raise ContractError(code)

    def interval(row, nullable=False):
        if nullable and row is None:
            return
        if (type(row) is not list or len(row) != 2 or not all(is_int(x) for x in row) or row[0] >= row[1]):
            raise ContractError(code)

    for field in ("aligned_model_intervals", "aligned_query_intervals"):
        previous = -1
        for row in value[field]:
            interval(row)
            if row[0] <= previous:
                raise ContractError(code)
            previous = row[1]
    if value["status"] in {"invalid", "unsupported"}:
        if (any(value[k] is not None for k in (*RFAM_ALIGNMENT_COUNT_FIELDS, "display_model_from",
                "display_model_to", "display_query_from", "display_query_to"))
                or any(value[k] for k in arrays if k != "blocks")):
            raise ContractError(code)
        return
    if (query is None or not value["blocks"] or any(value[k] is None for k in RFAM_ALIGNMENT_COUNT_FIELDS)
            or value["display_query_from"] != hit["native"]["query_from"]
            or value["display_query_to"] != hit["native"]["query_to"]
            or value["display_model_from"] != value["blocks"][0]["model_from"]
            or value["display_model_to"] != value["blocks"][-1]["model_to"]
            or value["display_model_from"] + value["truncated_model_count_5p"] != hit["native"]["model_from"]
            or value["display_model_to"] - value["truncated_model_count_3p"] != hit["native"]["model_to"]
            or value["status"] == "complete" and value["issues"]):
        raise ContractError(code)
    segment_counts = {k: 0 for k in ("query_insert_count", "model_delete_count", "local_end_model_omitted_count", "local_end_query_count")}
    for segment in value["segments"]:
        closed_object(segment, ("kind", "model_interval", "query_interval", "model_text", "query_text",
            "model_count", "query_count", "correspondence_represented"), code=code)
        if (segment["kind"] not in {"match", "query_insertion", "model_deletion", "local_end", "truncated_model"}
                or any(not is_int(segment[k]) for k in ("model_count", "query_count"))
                or any(type(segment[k]) is not str for k in ("model_text", "query_text"))
                or type(segment["correspondence_represented"]) is not bool
                or segment["correspondence_represented"] != (segment["kind"] in {"match", "query_insertion", "model_deletion"})):
            raise ContractError(code)
        for axis in ("model", "query"):
            bound = segment[axis + "_interval"]
            interval(bound, nullable=True)
            if segment[axis + "_count"] != (0 if bound is None else bound[1] - bound[0]):
                raise ContractError(code)
        if segment["kind"] == "query_insertion":
            segment_counts["query_insert_count"] += segment["query_count"]
        elif segment["kind"] == "model_deletion":
            segment_counts["model_delete_count"] += segment["model_count"]
        elif segment["kind"] == "local_end":
            segment_counts["local_end_model_omitted_count"] += segment["model_count"]
            segment_counts["local_end_query_count"] += segment["query_count"]
    if any(value[k] != count for k, count in segment_counts.items()):
        raise ContractError(code)
    previous_model = previous_query = None
    compared = equal = 0
    complement = str.maketrans("ACGURYSWKMBDHVN", "UGCAYRSWMKVHDBN")
    for pair in value["paired_positions"]:
        closed_object(pair, ("model_position", "query_position", "consensus_symbol", "query_symbol"), code=code)
        mpos, qpos = pair["model_position"], pair["query_position"]
        if (not is_int(mpos) or not is_int(qpos) or qpos >= query["submitted_length_nt"]
                or previous_model is not None and mpos <= previous_model
                or previous_query is not None and (qpos <= previous_query if hit["strand"] == "+" else qpos >= previous_query)
                or any(type(pair[k]) is not str or len(pair[k]) != 1 or pair[k].upper().replace("T", "U") not in "ACGURYSWKMBDHVN"
                       for k in ("consensus_symbol", "query_symbol"))
                or not any(a <= mpos < b for a, b in value["aligned_model_intervals"])
                or not any(a <= qpos < b for a, b in value["aligned_query_intervals"])):
            raise ContractError(code)
        expected = query["submitted_sequence"][qpos].upper().replace("T", "U")
        if hit["strand"] == "-":
            expected = expected.translate(complement)
        mchar, qchar = pair["consensus_symbol"].upper().replace("T", "U"), pair["query_symbol"].upper().replace("T", "U")
        if qchar != expected:
            raise ContractError(code)
        if mchar in "ACGU" and qchar in "ACGU":
            compared += 1
            equal += mchar == qchar
        previous_model, previous_query = mpos, qpos
    if compared != value["model_consensus_compared_count"] or equal != value["model_consensus_equal_count"]:
        raise ContractError(code)
    for row in value["posterior_segments"]:
        closed_object(row, ("query_interval", "code", "lower_bound", "upper_bound", "meaning"), code=code)
        interval(row["query_interval"])
        if (row["code"] not in tuple("0123456789*") or row["meaning"] not in {"residue_placement_bin", "span_mean_placement_bin"}
                or any(not is_number(row[k]) for k in ("lower_bound", "upper_bound"))):
            raise ContractError(code)
        digit = int(row["code"]) if row["code"] != "*" else None
        bounds = (.95, 1.) if digit is None else (0., .05) if digit == 0 else ((2 * digit - 1) / 20, (2 * digit + 1) / 20)
        if (row["lower_bound"], row["upper_bound"]) != bounds:
            raise ContractError(code)


def validate_rfam_report_sheet(sheet) -> dict:
    """Authenticate saved schema and associations; no raw parsing or I/O.

The custody consumer authenticates source/file digests against retained bytes.
This validator checks the closed saved graph and its internal relationships.
"""
    import hashlib
    import re
    from collections import Counter
    from .rfam_batch_contracts import closed_object, finite_json_copy, is_int, is_number, is_sha256, is_text
    from .rfam_batch_table import RfamBatchFileQuery, _report_membership
    code = "rfam_sheet_invalid"
    sheet = finite_json_copy(sheet, code=code)
    closed_object(sheet, RfamBatchReportSheet.__annotations__, code=code)
    if sheet["schema_version"] != REPORT_SHEET_VERSION or type(sheet["population_complete"]) is not bool or type(sheet["hits"]) is not list:
        raise ContractError(code)
    _validate_issues(sheet["issues"], code)
    identity, capture = sheet["input_identity"], sheet["capture"]
    closed_object(identity, RfamBatchFileInputIdentity.__annotations__, code=code)
    closed_object(capture, RfamBatchTableCapture.__annotations__, code=code)
    if (identity["version"] != "rfam_batch_file_input_v1" or not is_int(identity["submitted_file_bytes"], minimum=1)
            or not is_sha256(identity["submitted_file_sha256"]) or not is_text(identity["filename"])
            or identity["header_transform"] not in {"generated_unique_headers", "unchanged_unique_headers"}
            or not is_text(identity["submission_source_ref"]) or not is_text(identity["expected_job_id"])
            or re.fullmatch(r"infernal_cmscan-[A-Za-z0-9_-]+", identity["expected_job_id"]) is None
            or type(identity["queries"]) is not list or not identity["queries"]
            or capture["representation"] != "out" or type(capture["body_complete"]) is not bool
            or not is_sha256(capture["source_sha256"])
            or any(not is_text(capture[k]) for k in ("source_ref", "artifact_ref"))
            or capture["http_status"] not in (None, 200)
            or capture["evidence_kind"] not in {"native_response", "official_documentation_example", "synthetic_fixture"}
            or capture["evidence_kind"] == "native_response" and capture["http_status"] != 200
            or capture["request_job_id"] != identity["expected_job_id"]
            or capture["request_file_sha256"] != identity["submitted_file_sha256"]
            or capture["submission_source_ref"] != identity["submission_source_ref"]):
        raise ContractError(code)
    names, keys = {}, set()
    for ordinal, query in enumerate(identity["queries"]):
        closed_object(query, RfamBatchFileQuery.__annotations__, code=code)
        sequence = query["submitted_sequence"]
        if (query["selected_occurrence_ordinal"] != ordinal or type(query["selected_occurrence_ordinal"]) is not int
                or any(not is_text(query[k]) for k in ("native_query_name", "query_occurrence_key", "subject_ref", "original_input_ref"))
                or any(c.isspace() for c in query["native_query_name"])
                or query["native_query_name"] in names or query["query_occurrence_key"] in keys
                or query["original_record_ordinal"] is not None and not is_int(query["original_record_ordinal"])
                or query["original_header"] is not None and type(query["original_header"]) is not str
                or type(sequence) is not str or re.fullmatch(r"[ACGTURYSWKMBDHVNacgturyswkmbdhvn]+", sequence) is None
                or not is_int(query["submitted_length_nt"], minimum=1) or query["submitted_length_nt"] != len(sequence)
                or query["submitted_sequence_sha256"] != hashlib.sha256(sequence.encode("ascii")).hexdigest()
                or query["input_to_submitted_transform"] not in {"unchanged", "registered_view", "feature_segments"}
                or query["input_coordinate_mapping_ref"] is not None and not is_text(query["input_coordinate_mapping_ref"])
                or query["input_to_submitted_transform"] != "unchanged" and query["input_coordinate_mapping_ref"] is None):
            raise ContractError(code)
        names[query["native_query_name"]] = query
        keys.add(query["query_occurrence_key"])
    try:
        membership = _report_membership(sheet["membership"])
    except ValueError as error:
        raise ContractError(code) from error
    if any(membership[k] != capture[k] for k in ("artifact_ref", "source_sha256", "request_job_id")):
        raise ContractError(code)
    occurrences = Counter(q["native_query_name"] for q in membership["queries"])
    by_line = {q["query_header_line"]: q for q in membership["queries"]}
    if len(by_line) != len(membership["queries"]):
        raise ContractError(code)
    seen, previous = set(), 0
    for hit in sheet["hits"]:
        closed_object(hit, RfamBatchReportHit.__annotations__, code=code)
        closed_object(hit["native"], RfamReportNativeCells.__annotations__, code=code)
        closed_object(hit["raw_cells"], RfamReportRawCells.__annotations__, code=code)
        source = _validate_lines(hit["source_lines"], code)
        _validate_issues(hit["issues"], code)
        origin = hit["score_line"] or hit["alignment_summary_line"]
        row = by_line.get(hit["query_header_line"])
        if (not is_int(origin, minimum=previous + 1) or hit["hit_key"] in seen
                or hit["hit_key"] != capture["artifact_ref"] + "/lines/" + str(origin)
                or row is None or row["native_query_name"] != hit["native_query_name"]
                or hit["family_accession"] is not None
                or hit["model_name"] is not None and not is_text(hit["model_name"])
                or hit["strand"] is not None and hit["strand"] not in {"+", "-"}
                or any(hit[k] is not None and (not is_int(hit[k], minimum=1) or hit[k] not in source)
                       for k in ("score_line", "alignment_header_line", "alignment_summary_line"))
                or type(hit["missing"]) is not dict or any(not is_text(k) or v not in RFAM_REPORT_MISSING_REASONS for k, v in hit["missing"].items())):
            raise ContractError(code)
        previous = origin
        seen.add(hit["hit_key"])
        query = names.get(hit["native_query_name"])
        if query is not None and (occurrences[hit["native_query_name"]] != 1 or query["submitted_length_nt"] != row["length_nt"]):
            query = None
        sequence_conflict = any(i["code"] in {"rfam_alignment_query_conflict", "rfam_report_display_query_conflict"}
                                for i in hit["issues"])
        if hit["query_occurrence_key"] != (None if query is None or sequence_conflict else query["query_occurrence_key"]):
            raise ContractError(code)
        for raw in hit["raw_cells"].values():
            if type(raw) is not dict or any(type(v) is not str for v in raw.values()):
                raise ContractError(code)
        for key, value in hit["native"].items():
            if value is None:
                if key not in hit["missing"]:
                    raise ContractError(code)
                continue
            if key in {"rank", "model_from", "model_to", "query_from", "query_to"}:
                if not is_int(value, minimum=1):
                    raise ContractError(code)
            elif key in {"score", "evalue", "bias", "accuracy", "gc"}:
                if not is_number(value) or key == "evalue" and value < 0 or key in {"accuracy", "gc"} and not 0 <= value <= 1:
                    raise ContractError(code)
            elif type(value) is not str:
                raise ContractError(code)
        if hit["correspondence"] is not None:
            _validate_correspondence(hit["correspondence"], hit, query, source, code)
    if sheet["population_complete"]:
        if (not membership["complete"] or not capture["body_complete"] or set(occurrences) != set(names)
                or any(n != 1 for n in occurrences.values())
                or any(q["length_nt"] != names[q["native_query_name"]]["submitted_length_nt"] for q in membership["queries"])
                or any(q["reported_hit_count"] != sum(h["native_query_name"] == q["native_query_name"] for h in sheet["hits"])
                       for q in membership["queries"])):
            raise ContractError(code)
    return sheet


def validate_rfam_report_calculation(calculation, *, sheet) -> dict:
    """Validate saved calculation identity/schema without invoking calculators."""
    from .rfam_batch_contracts import closed_object, finite_json_copy, is_int, is_number, rfam_digest, validate_rfam_parameters
    sheet = validate_rfam_report_sheet(sheet)
    code = "rfam_calculation_invalid"
    calculation = finite_json_copy(calculation, code=code)
    closed_object(calculation, RfamBatchReportCalculation.__annotations__, code=code)
    if (calculation["version"] != REPORT_CALCULATION_VERSION or calculation["sheet_digest"] != rfam_digest(sheet)
            or calculation["population_complete"] != sheet["population_complete"]
            or type(calculation["population_complete"]) is not bool
            or type(calculation["hits"]) is not list or len(calculation["hits"]) != len(sheet["hits"])
            or type(calculation["query_strands"]) is not list):
        raise ContractError(code)
    validate_rfam_parameters(calculation["parameters"])
    _validate_issues(calculation["issues"], code)
    if calculation["issues"] != sheet["issues"]:
        raise ContractError(code)

    def metrics(row, fields):
        if type(row["missing"]) is not dict or set(row["missing"]) != {k for k in fields if row[k] is None}:
            raise ContractError(code)
        for key in fields:
            value = row[key]
            if value is not None and (not is_number(value) or key not in {"native_score_bits", "native_bias_bits"} and value < 0
                    or RFAM_REPORT_METRIC_UNITS[key] == "fraction" and value > 1):
                raise ContractError(code)
            if value is not None and RFAM_REPORT_METRIC_UNITS[key] not in {"bits", "expected_hits", "fraction"} and not is_int(value):
                raise ContractError(code)
        if any(v not in RFAM_REPORT_MISSING_REASONS for v in row["missing"].values()):
            raise ContractError(code)

    for row, hit in zip(calculation["hits"], sheet["hits"]):
        closed_object(row, RfamBatchReportHitCalculation.__annotations__, code=code)
        if any(row[k] != hit[k] for k in _HIT_CALC_IDENTITY if k != "missing"):
            raise ContractError(code)
        metrics(row, RFAM_REPORT_HIT_METRICS)
        if row["model_length_positions"] is not None or row["model_coverage_fraction"] is not None:
            raise ContractError(code)
        if hit["query_occurrence_key"] is None and any(row[k] is not None for k in RFAM_REPORT_HIT_METRICS):
            raise ContractError(code)
        if hit["query_occurrence_key"] is not None:
            for metric, (native_field, _) in _NATIVE.items():
                expected_value = None if native_field in hit["missing"] else hit["native"][native_field]
                if row[metric] != expected_value:
                    raise ContractError(code)
            query = next(q for q in sheet["input_identity"]["queries"] if q["query_occurrence_key"] == hit["query_occurrence_key"])
            if row["query_length_nt"] != query["submitted_length_nt"]:
                raise ContractError(code)
            correspondence = hit["correspondence"]
            if correspondence is not None and correspondence["status"] in {"complete", "partial"}:
                if any(row[k] != correspondence[k] for k in (*RFAM_ALIGNMENT_COUNT_FIELDS, "display_model_from", "display_model_to")):
                    raise ContractError(code)
    expected = [(q, strand) for q in sheet["input_identity"]["queries"] for strand in ("+", "-")]
    if len(calculation["query_strands"]) != len(expected):
        raise ContractError(code)
    for row, (query, strand) in zip(calculation["query_strands"], expected):
        closed_object(row, RfamBatchReportQueryStrandCalculation.__annotations__, code=code)
        metrics(row, RFAM_QUERY_STRAND_METRICS)
        if (row["query_occurrence_key"] != query["query_occurrence_key"] or row["strand"] != strand
                or row["query_length_nt"] != query["submitted_length_nt"] or type(row["population_complete"]) is not bool
                or row["population_complete"] and not sheet["population_complete"]
                or not row["population_complete"] and row["query_strand_union_fraction"] is not None):
            raise ContractError(code)
    return calculation


# Documentation of ordinary calculator fields, not an interpreted scoring DSL.
# Every quantity refers to all retained reported rows; independent evidence or
# annotation probability is never inferred. Missing identity invalidates every
# attributed metric. Native rounding remains in the retained source strings.
_NATIVE = {
    "native_rank": ("rank", "Native reported hit order (ordinal, not confidence)"),
    "native_score_bits": ("score", "Native score; printed to 0.1 bits"),
    "native_evalue": ("evalue", "Native expected hits; printed to 2 significant figures"),
    "native_bias_bits": ("bias", "Native signed bias quantity; printed to 0.1 bits"),
    "native_gc_fraction": ("gc", "Native GC fraction; printed to 0.01"),
    "native_alignment_accuracy": ("accuracy", "Native mean posterior alignment accuracy; printed to 0.01"),
    "native_start_1i": ("query_from", "Native first query position in alignment orientation"),
    "native_end_1i": ("query_to", "Native final query position in alignment orientation"),
    "native_model_from_1i": ("model_from", "Native first emitted model position"),
    "native_model_to_1i": ("model_to", "Native final emitted model position")}
REPORT_METRIC_DEFINITIONS = {}
for _name, (_input, _meaning) in _NATIVE.items():
    REPORT_METRIC_DEFINITIONS[_name] = dict(inputs=["hit.native." + _input], meaning=_meaning,
        formula="native cell", unit=RFAM_REPORT_METRIC_UNITS[_name], denominator=None,
        population="one reported hit bound to its original selected query occurrence",
        coordinates="one-based inclusive" if "1i" in _name else None,
        uncertainty="native displayed precision only; no sampling uncertainty supplied",
        missing="null on missing, malformed or contradictory cell", kind="native")
REPORT_METRIC_DEFINITIONS["native_gc_fraction"].update(
    denominator="physical query hit span in nucleotides",
    formula="native gc cell: Infernal sum of C/G fractional symbol counts divided by hit span; no recomputation",
    meaning="Infernal GC fraction of hit; ambiguity weight distributed equally among possible bases by esl_abc_FCount")
REPORT_METRIC_DEFINITIONS["native_alignment_accuracy"].update(
    denominator="aligned query residues (native mean posterior placement probability)",
    meaning="Native alignment mean posterior placement probability, not annotation probability; PP bins cannot recover full precision")
_DERIVED = {
    "query_length_nt": (["input_identity.queries.submitted_length_nt"], "exact original submitted occurrence length", None),
    "query_span_nt": (["native.query_from", "native.query_to"], "abs(query_to-query_from)+1", None),
    "query_span_fraction": (["query_span_nt", "query_length_nt"], "query_span_nt/query_length_nt", "original query_length_nt"),
    "native_model_span_positions": (["native.model_from", "native.model_to"], "model_to-model_from+1", None),
    "display_model_from": (["correspondence.display_model_from"], "saved display endpoint, includes explicit shorthand span", None),
    "display_model_to": (["correspondence.display_model_to"], "saved display endpoint, includes explicit shorthand span", None),
    "represented_model_positions": (["correspondence.aligned_model_intervals"], "sum(end-start) of represented model interval union", None),
    "represented_query_positions": (["correspondence.aligned_query_intervals"], "sum(end-start) of represented query interval union", None),
    "model_length_positions": ([], "unavailable: requires separately established full model metadata", None),
    "model_coverage_fraction": ([], "unavailable: no full model length supplied", "full model length (unavailable)"),
    "model_consensus_equal_fraction": (["model_consensus_equal_count", "model_consensus_compared_count"], "equal/compared; case-insensitive canonical A/C/G/U with T=U", "canonical paired positions only"),
    "selected_row_count": (["hits.query_occurrence_key", "hits.strand"], "number of retained reported rows per original occurrence and strand", None),
    "valid_interval_row_count": (["hits.native.query_from", "hits.native.query_to"], "number of rows with validated query intervals per occurrence and strand", None),
    "query_strand_sum_span_nt": (["hits.query_span_nt"], "sum query spans retaining duplicate multiplicity", None),
    "query_strand_union_span_nt": (["hits.native.query_from", "hits.native.query_to"], "length of physical coordinate union per original occurrence and strand", None),
    "query_strand_union_fraction": (["query_strand_union_span_nt", "query_length_nt"], "union/query_length_nt; null unless reported population and geometry complete", "original query_length_nt"),
    "query_strand_overlap_excess_nt": (["query_strand_sum_span_nt", "query_strand_union_span_nt"], "sum-union; repeated coordinate multiplicity, not independent evidence", None)}
for _name in RFAM_ALIGNMENT_COUNT_FIELDS:
    _DERIVED[_name] = (["correspondence." + _name], {
        "model_consensus_equal_count": "count canonical paired letters equal after case/T-U normalization",
        "model_consensus_compared_count": "count pairs with both letters canonical A/C/G/U after T-U normalization",
        "query_insert_count": "explicit query residues opposite model insertion dots",
        "model_delete_count": "explicit model positions opposite query deletion dashes",
        "truncated_model_count_5p": "native 5-prime shorthand omitted model count",
        "truncated_model_count_3p": "native 3-prime shorthand omitted model count",
        "local_end_model_omitted_count": "native local-end shorthand omitted model count",
        "local_end_query_count": "native local-end shorthand unrepresented query count"}[_name], None)
for _name, (_inputs, _formula, _denominator) in _DERIVED.items():
    REPORT_METRIC_DEFINITIONS[_name] = dict(inputs=_inputs, meaning=_formula, formula=_formula,
        unit=RFAM_REPORT_METRIC_UNITS[_name], denominator=_denominator,
        population="all reported rows separately per original query occurrence and strand" if _name in RFAM_QUERY_STRAND_METRICS else "one reported hit bound to its original selected query occurrence",
        coordinates="physical zero-based half-open intervals; native/display endpoints one-based inclusive",
        uncertainty="none supplied; posterior placement bins retained separately",
        missing="null when required inputs invalid/absent; no pairs yields null ratio; complete zero-hit populations yield zero",
        kind="derived" if _inputs else "unavailable")
