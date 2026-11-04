"""Closed Rfam native-result contracts. No acquisition or scientific execution.

Numerical meanings are specific to the retained remote JSON representation.
Native bit scores, E-values and reported GC are observations, never annotation
probabilities. Artifact custody is the caller's responsibility; these pure
validators check the supplied identities and numerical relationships.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from typing import Literal, TypedDict

from .domain import ContractError, validate_schema
from .execution_contracts import canonical


RFAM_ISSUE_CODES = frozenset("""
rfam_request_invalid rfam_subject_out_of_scope rfam_sequence_invalid
rfam_original_handle_required rfam_original_handle_conflict
rfam_job_identity_invalid rfam_result_url_identity_conflict
rfam_original_submission_already_exists rfam_response_unknown
rfam_transport_error rfam_response_body_incomplete rfam_redirect_not_followed
rfam_http_error rfam_status_unknown rfam_job_not_found
rfam_json_invalid rfam_json_duplicate_key rfam_result_object_required
rfam_result_job_identity_conflict rfam_result_sequence_identity_absent
rfam_result_sequence_identity_not_string rfam_result_sequence_identity_empty
rfam_result_sequence_identity_not_ascii rfam_result_sequence_identity_conflict
rfam_result_hits_representation rfam_result_hit_count_conflict
rfam_multiple_sequences_schema_unestablished rfam_text_format_unverified
rfam_hit_object_required rfam_hit_family_identity_conflict
rfam_hit_accession_invalid rfam_hit_coordinate_invalid
rfam_hit_coordinate_out_of_bounds rfam_hit_strand_invalid
rfam_hit_strand_coordinate_conflict rfam_hit_numeric_invalid
rfam_alignment_missing rfam_alignment_invalid rfam_alignment_unsupported
rfam_alignment_query_conflict rfam_alignment_coordinate_conflict
rfam_model_binding_unverified rfam_model_metadata_conflict
rfam_projection_invalid rfam_projection_reference_conflict
rfam_capture_invalid rfam_source_identity_conflict rfam_input_identity_invalid
rfam_sheet_invalid rfam_calculation_invalid rfam_parameters_invalid
rfam_result_timestamp_invalid rfam_alignment_binding_conflict
rfam_alignment_correspondence_unrepresented
rfam_requires_api_execution_episode
rfam_report_batch_request_required
""".split())
RFAM_MISSING_REASONS = frozenset("""
not_reported invalid_native_value identity_rejected coordinates_invalid
alignment_not_parsed alignment_missing alignment_unsupported alignment_conflict
model_length_unavailable model_binding_unverified model_metadata_conflict
no_determinate_pairs partial_body format_unverified
""".split())
RFAM_ISSUE_SCOPES = frozenset(("document", "row", "cell", "alignment", "metadata", "projection"))
RFAM_ALIGNMENT_FIELDS = ("nc", "ss", "hit_seq", "match", "user_seq", "pp")
RFAM_ALIGNMENT_COUNT_FIELDS = (
    "model_consensus_compared_count", "model_consensus_equal_count",
    "query_insert_count", "model_delete_count", "truncated_model_count_5p",
    "truncated_model_count_3p", "local_end_model_omitted_count", "local_end_query_count")
RFAM_ALIGNMENT_RESULT_FIELDS = frozenset((
    "version", "artifact_ref", "hit_key", "hit_identity", "query_strand", "status",
    "raw_alignment_ref", "display_model_from", "display_model_to",
    "display_query_from", "display_query_to", "segments", "paired_positions",
    "aligned_model_intervals", "aligned_query_intervals", "posterior_segments",
    "issues", *RFAM_ALIGNMENT_COUNT_FIELDS))

RFAM_HIT_METRICS = (
    "native_score_bits", "native_evalue", "native_gc_fraction",
    "native_start_1i", "native_end_1i", "query_length_nt", "query_span_nt",
    "query_span_fraction", "display_model_from", "display_model_to",
    "represented_model_positions", "model_length_positions", "model_coverage_fraction",
    "model_consensus_equal_count", "model_consensus_compared_count",
    "model_consensus_equal_fraction")
RFAM_QUERY_STRAND_METRICS = (
    "query_length_nt", "selected_row_count", "valid_interval_row_count", "query_strand_sum_span_nt",
    "query_strand_union_span_nt", "query_strand_union_fraction",
    "query_strand_overlap_excess_nt")
RFAM_TABLE_HIT_METRICS = (*RFAM_HIT_METRICS, "native_bias_bits",
    "native_model_from_1i", "native_model_to_1i", "native_model_span_positions", "native_model_span_fraction")
RFAM_METRICS = {"hit": RFAM_HIT_METRICS, "query_strand": RFAM_QUERY_STRAND_METRICS}
RFAM_METRIC_UNITS = {
    "native_score_bits": "bits", "native_evalue": "expected_hits",
    "native_gc_fraction": "fraction", "native_start_1i": "nt_position_1i",
    "native_end_1i": "nt_position_1i", "query_length_nt": "nt",
    "query_span_nt": "nt", "query_span_fraction": "fraction",
    "display_model_from": "model_position_1i", "display_model_to": "model_position_1i",
    "represented_model_positions": "model_positions", "model_length_positions": "model_positions",
    "model_coverage_fraction": "fraction", "model_consensus_equal_count": "comparisons",
    "model_consensus_compared_count": "comparisons", "model_consensus_equal_fraction": "fraction",
    "selected_row_count": "rows", "valid_interval_row_count": "rows",
    "query_strand_sum_span_nt": "nt", "query_strand_union_span_nt": "nt",
    "query_strand_union_fraction": "fraction", "query_strand_overlap_excess_nt": "nt",
    "native_bias_bits": "bits", "native_model_from_1i": "model_position_1i",
    "native_model_to_1i": "model_position_1i", "native_model_span_positions": "model_positions",
    "native_model_span_fraction": "fraction"}
RFAM_CALCULATION_PARAMETERS = {
    "version": "rfam_batch_parameters_v1", "hit_population": "all_reported",
    "strand_policy": "separate", "duplicate_policy": "retain_rows_union_coordinates",
    "consensus_comparison": "canonical_nt_tu_equivalent"}
PARAMETERS = RFAM_CALCULATION_PARAMETERS


class Issue(TypedDict):
    code: str
    scope: str
    hit_key: str | None
    field: str | None
    source_pointer: str | None


class RfamHitIdentity(TypedDict):
    artifact_ref: str
    hit_key: str
    query_occurrence_key: str
    family_accession: str


class RfamBatchInputIdentity(TypedDict):
    version: str
    query_occurrence_key: str
    subject_ref: str
    original_input_ref: str
    original_record_ordinal: int | None
    original_header: str | None
    submitted_sequence: str
    submitted_sequence_sha256: str
    submitted_length_nt: int
    input_to_submitted_transform: str
    input_coordinate_mapping_ref: str | None
    expected_job_id: str
    submission_source_ref: str


class RfamArtifactCapture(TypedDict):
    artifact_ref: str
    source_ref: str
    source_sha256: str
    evidence_kind: Literal["native_response", "official_documentation_example", "synthetic_fixture"]
    representation: Literal["json", "tblout", "out"]
    http_status: int | None
    body_complete: bool
    request_job_id: str
    request_sequence_sha256: str


class RfamAlignmentResult(TypedDict):
    version: str
    artifact_ref: str
    hit_key: str
    hit_identity: RfamHitIdentity
    query_strand: str
    status: str
    raw_alignment_ref: dict
    display_model_from: int | None
    display_model_to: int | None
    display_query_from: int | None
    display_query_to: int | None
    segments: list[dict]
    paired_positions: list[dict]
    aligned_model_intervals: list[list[int]]
    aligned_query_intervals: list[list[int]]
    model_consensus_compared_count: int | None
    model_consensus_equal_count: int | None
    query_insert_count: int | None
    model_delete_count: int | None
    truncated_model_count_5p: int | None
    truncated_model_count_3p: int | None
    local_end_model_omitted_count: int | None
    local_end_query_count: int | None
    posterior_segments: list[dict]
    issues: list[Issue]


class RfamAlignmentComponents(TypedDict):
    version: str
    artifact_ref: str
    source_sha256: str
    rows: list[RfamAlignmentResult]


class RfamModelMetadataBundle(TypedDict):
    version: str
    records: list[dict]
    bindings: list[dict]


class RfamBatchSheet(TypedDict):
    schema_version: str
    source: RfamArtifactCapture
    input: RfamBatchInputIdentity
    job: dict
    format_metadata: dict
    population: dict
    hits: list[dict]
    model_metadata: RfamModelMetadataBundle | None
    issues: list[Issue]


class RfamParseResult(TypedDict):
    version: str
    status: str
    format: str
    sheet: RfamBatchSheet | None
    issues: list[Issue]


class RfamCalculationParameters(TypedDict):
    version: str
    hit_population: str
    strand_policy: str
    duplicate_policy: str
    consensus_comparison: str


class RfamCalculationResult(TypedDict):
    version: str
    sheet_digest: str
    parameters: RfamCalculationParameters
    population: dict
    hits: list[dict]
    query_strands: list[dict]
    issues: list[Issue]


class RfamSelectedProjection(TypedDict):
    version: str
    source_ref: str
    sheet_ref: str
    calculation_ref: str
    family: str
    selection: dict
    available_row_count: int
    selected_row_count: int
    more_rows: bool
    population_complete: bool
    rows: list[dict]


def finite_json_copy(value, *, code="rfam_request_invalid"):
    def check(v):
        if v is None or type(v) in (str, int, bool):
            return
        if type(v) is float and math.isfinite(v):
            return
        if type(v) is list:
            for child in v:
                check(child)
            return
        if type(v) is dict and all(type(k) is str for k in v):
            for child in v.values():
                check(child)
            return
        raise ContractError(code)
    check(value)
    return deepcopy(value)


def rfam_digest(value):
    return hashlib.sha256(canonical(finite_json_copy(value)).encode("utf-8")).hexdigest()


def closed_object(value, fields, *, code):
    if type(value) is not dict or set(value) != set(fields):
        raise ContractError(code)
    return value


def is_text(value):
    return type(value) is str and bool(value) and "\x00" not in value


def is_sha256(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def is_number(value):
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def is_int(value, *, minimum=0):
    return type(value) is int and value >= minimum


def make_issue(code, scope="document", *, hit_key=None, field=None, source_pointer=None):
    result = dict(code=code, scope=scope, hit_key=hit_key, field=field, source_pointer=source_pointer)
    validate_issue(result)
    return result


def validate_issue(value):
    closed_object(value, Issue.__annotations__, code="rfam_request_invalid")
    if value["code"] not in RFAM_ISSUE_CODES or value["scope"] not in RFAM_ISSUE_SCOPES:
        raise ContractError("rfam_request_invalid")
    if any(value[key] is not None and not is_text(value[key]) for key in ("hit_key", "field", "source_pointer")):
        raise ContractError("rfam_request_invalid")
    return deepcopy(value)


def json_pointer_token(value):
    return value.replace("~", "~0").replace("/", "~1")


def query_strand_record_key(query_occurrence_key, strand):
    if not is_text(query_occurrence_key) or strand not in ("+", "-"):
        raise ContractError("rfam_projection_reference_conflict")
    return canonical([query_occurrence_key, strand])


def validate_rfam_input_identity(value):
    code = "rfam_input_identity_invalid"
    value = finite_json_copy(value, code=code)
    closed_object(value, RfamBatchInputIdentity.__annotations__, code=code)
    if value["version"] != "rfam_batch_input_identity_v1":
        raise ContractError(code)
    for key in ("query_occurrence_key", "subject_ref", "original_input_ref", "submission_source_ref"):
        if not is_text(value[key]):
            raise ContractError(code)
    for key in ("original_header", "input_coordinate_mapping_ref"):
        if value[key] is not None and (type(value[key]) is not str or "\x00" in value[key]):
            raise ContractError(code)
    if value["original_record_ordinal"] is not None and not is_int(value["original_record_ordinal"]):
        raise ContractError(code)
    sequence = value["submitted_sequence"]
    if type(sequence) is not str or not sequence or re.fullmatch(r"[ACGTURYSWKMBDHVNacgturyswkmbdhvn]+", sequence) is None:
        raise ContractError("rfam_sequence_invalid")
    if (not is_int(value["submitted_length_nt"], minimum=1) or len(sequence) != value["submitted_length_nt"]
            or hashlib.sha256(sequence.encode("ascii")).hexdigest() != value["submitted_sequence_sha256"]):
        raise ContractError(code)
    if value["input_to_submitted_transform"] not in ("unchanged", "registered_view", "feature_segments"):
        raise ContractError(code)
    if (type(value["expected_job_id"]) is not str
            or re.fullmatch(r"infernal_cmscan-[A-Za-z0-9_-]+", value["expected_job_id"]) is None):
        raise ContractError("rfam_job_identity_invalid")
    return value


def validate_rfam_capture(value):
    code = "rfam_capture_invalid"
    value = finite_json_copy(value, code=code)
    closed_object(value, RfamArtifactCapture.__annotations__, code=code)
    if (any(not is_text(value[key]) for key in ("artifact_ref", "source_ref", "request_job_id"))
            or not is_sha256(value["source_sha256"]) or not is_sha256(value["request_sequence_sha256"])
            or value["representation"] not in ("json", "tblout", "out")
            or value["evidence_kind"] not in ("native_response", "official_documentation_example", "synthetic_fixture")
            or value["http_status"] is not None and (not is_int(value["http_status"], minimum=100) or value["http_status"] > 599)
            or type(value["body_complete"]) is not bool):
        raise ContractError(code)
    return value


def validate_rfam_hit_identity(value):
    value = finite_json_copy(value, code="rfam_alignment_binding_conflict")
    closed_object(value, RfamHitIdentity.__annotations__, code="rfam_alignment_binding_conflict")
    if (any(not is_text(v) for v in value.values())
            or not value["hit_key"].startswith(value["artifact_ref"] + "/hits/")
            or re.fullmatch(r"RF[0-9]{5}", value["family_accession"]) is None):
        raise ContractError("rfam_alignment_binding_conflict")
    return value


def validate_rfam_alignment_result(value):
    """Check the supplied component record, not the native display grammar."""
    code = "rfam_alignment_invalid"
    value = finite_json_copy(value, code=code)
    closed_object(value, RFAM_ALIGNMENT_RESULT_FIELDS, code=code)
    identity = validate_rfam_hit_identity(value["hit_identity"])
    if (value["version"] != "rfam_alignment_components_v1"
            or value["status"] not in ("complete", "partial", "unsupported", "invalid")
            or value["query_strand"] not in ("+", "-")
            or value["artifact_ref"] != identity["artifact_ref"] or value["hit_key"] != identity["hit_key"]):
        raise ContractError(code)
    pointer = value["hit_key"][len(value["artifact_ref"]):] + "/alignment"
    if value["raw_alignment_ref"] != {"artifact_ref": value["artifact_ref"], "json_pointer": pointer}:
        raise ContractError("rfam_alignment_binding_conflict")
    for field in RFAM_ALIGNMENT_COUNT_FIELDS:
        if value[field] is not None and not is_int(value[field]):
            raise ContractError(code)
    for field in ("display_model_from", "display_model_to", "display_query_from", "display_query_to"):
        if value[field] is not None and not is_int(value[field], minimum=1):
            raise ContractError(code)

    def interval(v, *, nullable=False):
        if nullable and v is None:
            return
        if (type(v) is not list or len(v) != 2 or not all(is_int(x) for x in v)
                or v[0] >= v[1]):
            raise ContractError(code)

    for field in ("aligned_model_intervals", "aligned_query_intervals", "segments", "paired_positions", "posterior_segments", "issues"):
        if type(value[field]) is not list:
            raise ContractError(code)
    for field in ("aligned_model_intervals", "aligned_query_intervals"):
        for v in value[field]:
            interval(v)
    for row in value["segments"]:
        closed_object(row, ("kind", "model_interval", "query_interval", "model_text", "query_text",
            "model_count", "query_count", "correspondence_represented"), code=code)
        if (row["kind"] not in ("match", "query_insertion", "model_deletion", "local_end", "truncated_model", "unresolved")
                or type(row["correspondence_represented"]) is not bool
                or any(row[k] is not None and type(row[k]) is not str for k in ("model_text", "query_text"))
                or any(row[k] is not None and not is_int(row[k]) for k in ("model_count", "query_count"))):
            raise ContractError(code)
        for k in ("model_interval", "query_interval"):
            interval(row[k], nullable=True)
    pairs, model_positions, query_positions = set(), set(), set()
    previous_model = previous_query = None
    for row in value["paired_positions"]:
        closed_object(row, ("model_position", "query_position", "consensus_symbol", "query_symbol"), code=code)
        if (not is_int(row["model_position"]) or not is_int(row["query_position"])
                or any(type(row[k]) is not str or len(row[k]) != 1 for k in ("consensus_symbol", "query_symbol"))):
            raise ContractError(code)
        pair = (row["model_position"], row["query_position"])
        if (pair in pairs or pair[0] in model_positions or pair[1] in query_positions
                or previous_model is not None and pair[0] <= previous_model
                or previous_query is not None and (pair[1] <= previous_query if value["query_strand"] == "+" else pair[1] >= previous_query)):
            raise ContractError(code)
        pairs.add(pair)
        model_positions.add(pair[0])
        query_positions.add(pair[1])
        previous_model, previous_query = pair
        if any(not any(a <= row[position] < b for a, b in value[field])
               for position, field in (("model_position", "aligned_model_intervals"), ("query_position", "aligned_query_intervals"))):
            raise ContractError(code)
    determinate = [(r["consensus_symbol"].upper().replace("T", "U"), r["query_symbol"].upper().replace("T", "U"))
                   for r in value["paired_positions"]]
    determinate = [(a, b) for a, b in determinate if a in "ACGU" and b in "ACGU"]
    if (value["model_consensus_compared_count"] is not None
            and value["model_consensus_compared_count"] != len(determinate)):
        raise ContractError(code)
    if (value["model_consensus_equal_count"] is not None
            and value["model_consensus_equal_count"] != sum(a == b for a, b in determinate)):
        raise ContractError(code)
    for row in value["posterior_segments"]:
        closed_object(row, ("query_interval", "code", "lower_bound", "upper_bound", "meaning"), code=code)
        interval(row["query_interval"])
        if (row["code"] not in tuple("0123456789*")
                or not is_number(row["lower_bound"]) or not is_number(row["upper_bound"])
                or not 0 <= row["lower_bound"] <= row["upper_bound"] <= 1
                or row["meaning"] not in ("residue_placement_bin", "span_mean_placement_bin")):
            raise ContractError(code)
        digit = int(row["code"]) if row["code"] != "*" else None
        bounds = (.95, 1.) if digit is None else (0., .05) if digit == 0 else ((2 * digit - 1) / 20, (2 * digit + 1) / 20)
        if (row["lower_bound"], row["upper_bound"]) != bounds:
            raise ContractError(code)
    for issue in value["issues"]:
        validate_issue(issue)
        if issue["hit_key"] not in (None, value["hit_key"]):
            raise ContractError("rfam_alignment_binding_conflict")
    return value


def _object(properties):
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}


_TEXT = {"type": "string", "minLength": 1}
_ROWS = {"oneOf": [
    _object({"offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1}}),
    _object({"record_keys": {"type": "array", "minItems": 1, "uniqueItems": True, "items": _TEXT}})]}
RFAM_PROJECTION_SCHEMA = {"oneOf": [
    _object({"family": {"const": family}, "rows": _ROWS,
        "metrics": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"enum": list(metrics)}}})
    for family, metrics in RFAM_METRICS.items()]}
RFAM_TABLE_PROJECTION_SCHEMA = {"oneOf": [
    _object({"family": {"const": family}, "rows": _ROWS,
        "metrics": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"enum": list(metrics)}}})
    for family, metrics in {"hit": RFAM_TABLE_HIT_METRICS, "query_strand": RFAM_QUERY_STRAND_METRICS}.items()]}
RFAM_SINGLE_REQUEST_SCHEMA = _object({"version": {"const": "rfam_batch_request_v1"},
    "mode": {"const": "single_sequence"}, "subject_ref": _TEXT})
RFAM_FILE_REQUEST_SCHEMA = _object({"version": {"const": "rfam_batch_request_v2"},
    "mode": {"const": "sequence_batch"},
    "subject_refs": {"type": "array", "minItems": 1, "items": _TEXT}})
RFAM_BATCH_REQUEST_SCHEMA = {"oneOf": [RFAM_SINGLE_REQUEST_SCHEMA, RFAM_FILE_REQUEST_SCHEMA]}
RFAM_LEGACY_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"enum": ["rfam_batch_result_selector_v1", "rfam_batch_result_selector_v2"]},
    "representation": {"enum": ["json", "tblout", "out"]},
    "model_metadata_ref": {"type": ["string", "null"], "minLength": 1},
    "projection": {"anyOf": [RFAM_PROJECTION_SCHEMA, RFAM_TABLE_PROJECTION_SCHEMA, {"type": "null"}]}})
from .rfam_batch_report_contracts import RFAM_REPORT_PROJECTION_SCHEMA
RFAM_REPORT_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": "rfam_batch_result_selector_v3"},
    "representation": {"const": "out"},
    "model_metadata_ref": {"type": "null"},
    "projection": {"anyOf": [RFAM_REPORT_PROJECTION_SCHEMA, {"type": "null"}]}})
RFAM_BATCH_RESULT_SELECTOR_SCHEMA = {"oneOf": [
    RFAM_LEGACY_RESULT_SELECTOR_SCHEMA, RFAM_REPORT_RESULT_SELECTOR_SCHEMA]}
REQUEST_SCHEMA = RFAM_BATCH_REQUEST_SCHEMA
SELECTOR_SCHEMA = RFAM_BATCH_RESULT_SELECTOR_SCHEMA


def _validate_projection(value, schema):
    value = finite_json_copy(value, code="rfam_projection_invalid")
    try:
        validate_schema(value, schema)
    except (ContractError, TypeError) as error:
        raise ContractError("rfam_projection_invalid") from error
    if "offset" in value["rows"] and (not is_int(value["rows"]["offset"])
            or not is_int(value["rows"]["limit"], minimum=1)):
        raise ContractError("rfam_projection_invalid")
    return value


def validate_rfam_projection(value):
    return _validate_projection(value, RFAM_PROJECTION_SCHEMA)


def validate_rfam_table_projection(value):
    return _validate_projection(value, RFAM_TABLE_PROJECTION_SCHEMA)


def validate_rfam_result_selector(value):
    value = finite_json_copy(value, code="rfam_projection_invalid")
    try:
        validate_schema(value, RFAM_BATCH_RESULT_SELECTOR_SCHEMA)
    except (ContractError, TypeError) as error:
        raise ContractError("rfam_projection_invalid") from error
    if value["version"] == "rfam_batch_result_selector_v3":
        if value["projection"] is not None:
            from .rfam_batch_report_contracts import validate_rfam_report_projection
            validate_rfam_report_projection(value["projection"])
        return value
    if value["projection"] is not None:
        validator = (validate_rfam_table_projection if value["version"] == "rfam_batch_result_selector_v2"
                     and value["representation"] == "tblout" else validate_rfam_projection)
        validator(value["projection"])
    numeric_format = value["representation"] == "json" or (
        value["version"] == "rfam_batch_result_selector_v2" and value["representation"] == "tblout")
    if not numeric_format and (value["projection"] is not None or value["model_metadata_ref"] is not None):
        raise ContractError("rfam_text_format_unverified")
    return value


def validate_rfam_parameters(value):
    value = finite_json_copy(value, code="rfam_parameters_invalid")
    if value != RFAM_CALCULATION_PARAMETERS:
        raise ContractError("rfam_parameters_invalid")
    return value
