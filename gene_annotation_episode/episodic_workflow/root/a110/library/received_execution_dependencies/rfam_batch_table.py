from __future__ import annotations
from copy import deepcopy
import math
import re
from typing import Literal, TypedDict
RFAM_BATCH_TABLE_ISSUE_CODES = frozenset('\nrfam_batch_input_invalid rfam_batch_submitted_content_invalid\nrfam_batch_submitted_file_conflict rfam_batch_fasta_invalid\nrfam_batch_native_name_ambiguous rfam_batch_occurrence_key_ambiguous\nrfam_batch_fasta_membership_conflict rfam_batch_sequence_conflict\nrfam_batch_header_transform_conflict rfam_batch_capture_invalid\nrfam_batch_source_identity_conflict rfam_batch_result_job_conflict\nrfam_batch_result_file_conflict rfam_batch_submission_source_conflict\nrfam_batch_http_error rfam_batch_representation_unsupported\nrfam_batch_native_text_unsupported rfam_batch_table_format_unsupported\nrfam_batch_native_program_unsupported rfam_batch_native_version_unsupported\nrfam_batch_native_mode_unsupported rfam_batch_native_query_file_conflict\nrfam_batch_native_profile_incomplete rfam_batch_native_table_incomplete\nrfam_batch_foreign_native_query rfam_batch_model_metadata_invalid\nrfam_batch_model_provenance_unverified rfam_batch_report_invalid\nrfam_batch_report_job_conflict rfam_batch_report_profile_unsupported\nrfam_batch_report_query_file_conflict rfam_batch_report_incomplete\nrfam_batch_report_query_invalid rfam_batch_report_count_invalid\nrfam_batch_report_count_duplicate rfam_batch_report_query_unclosed\nrfam_batch_report_close_unmatched rfam_batch_report_name_ambiguous\nrfam_batch_report_foreign_query rfam_batch_report_query_missing\nrfam_batch_report_length_conflict rfam_batch_report_count_conflict\nrfam_batch_report_population_incomplete\n'.split())

class RfamBatchFileQuery(TypedDict):
    query_occurrence_key: str
    subject_ref: str
    original_input_ref: str
    original_record_ordinal: int | None
    original_header: str | None
    selected_occurrence_ordinal: int
    native_query_name: str
    submitted_sequence: str
    submitted_sequence_sha256: str
    submitted_length_nt: int
    input_to_submitted_transform: str
    input_coordinate_mapping_ref: str | None

class RfamBatchFileInputIdentity(TypedDict):
    version: Literal['rfam_batch_file_input_v1']
    expected_job_id: str
    submission_source_ref: str
    submitted_file_sha256: str
    submitted_file_bytes: int
    filename: str
    header_transform: Literal['generated_unique_headers', 'unchanged_unique_headers']
    queries: list[RfamBatchFileQuery]

class RfamBatchTableCapture(TypedDict):
    artifact_ref: str
    source_ref: str
    source_sha256: str
    evidence_kind: Literal['native_response', 'official_documentation_example', 'synthetic_fixture']
    representation: Literal['tblout', 'out']
    http_status: int | None
    body_complete: bool
    request_job_id: str
    request_file_sha256: str
    submission_source_ref: str

class RfamBatchTableIssue(TypedDict):
    code: str
    severity: Literal['error', 'warning']
    field: str | None
    native_query_name: str | None
    source_line: int | None

class RfamBatchOccurrenceBinding(TypedDict):
    sequence_metadata_index: int
    native_query_name: str
    query_occurrence_key: str
    selected_occurrence_ordinal: int

class RfamBatchQueryPopulation(TypedDict):
    query_occurrence_key: str
    submitted_length_nt: int
    membership_basis: Literal['frozen_complete_input', 'native_report', 'both']
    reported_row_count: int | None
    reported_set_complete: bool

class RfamBatchTableParseResult(TypedDict):
    version: Literal['rfam_batch_tblout_parse_result_v1']
    status: Literal['complete', 'partial', 'rejected', 'unsupported']
    format: str
    capture: dict | None
    input_identity: dict | None
    supplied_model_metadata: dict | None
    sheet: dict | None
    occurrence_bindings: list[RfamBatchOccurrenceBinding]
    query_population: list[RfamBatchQueryPopulation]
    issues: list[RfamBatchTableIssue]

class RfamReportQueryMembership(TypedDict):
    native_query_name: str
    query_header_line: int
    length_nt: int
    reported_hit_count: int | None
    reported_hit_count_line: int | None
    close_marker_line: int | None

class RfamReportMembership(TypedDict):
    source_sha256: str | None
    artifact_ref: str | None
    request_job_id: str | None
    complete: bool
    queries: list[RfamReportQueryMembership]
    issues: list[RfamBatchTableIssue]

def _text(value):
    return type(value) is str and bool(value.strip()) and ('\x00' not in value)

def _integer(value, minimum=0):
    return type(value) is int and value >= minimum

def _sha256(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None

def _job(value):
    return type(value) is str and re.fullmatch('infernal_cmscan-[A-Za-z0-9_-]+', value) is not None

def _finite(value, code):
    if value is None or type(value) in (str, int, bool):
        return deepcopy(value)
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_finite(item, code) for item in value]
    if type(value) is dict and all((type(key) is str for key in value)):
        return {key: _finite(item, code) for key, item in value.items()}
    raise ValueError(code)

def _closed(value, fields, code):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(code)

def _report_membership(value):
    code = 'rfam_batch_report_invalid'
    value = _finite(value, code)
    _closed(value, RfamReportMembership.__annotations__, code)
    if not _sha256(value['source_sha256']) or not _text(value['artifact_ref']) or (not _job(value['request_job_id'])) or (type(value['complete']) is not bool) or (type(value['queries']) is not list) or (type(value['issues']) is not list):
        raise ValueError(code)
    for issue in value['issues']:
        _closed(issue, RfamBatchTableIssue.__annotations__, code)
        if not _text(issue['code']) or issue['code'] not in RFAM_BATCH_TABLE_ISSUE_CODES or issue['severity'] not in ('error', 'warning') or any((issue[key] is not None and (not _text(issue[key])) for key in ('field', 'native_query_name'))) or (issue['source_line'] is not None and (not _integer(issue['source_line'], 1))):
            raise ValueError(code)
    for query in value['queries']:
        _closed(query, RfamReportQueryMembership.__annotations__, code)
        if not _text(query['native_query_name']) or not _integer(query['query_header_line'], 1) or (not _integer(query['length_nt'], 1)) or (query['reported_hit_count'] is not None and (not _integer(query['reported_hit_count']))) or any((query[key] is not None and (not _integer(query[key], 1)) for key in ('reported_hit_count_line', 'close_marker_line'))) or ((query['reported_hit_count'] is None) != (query['reported_hit_count_line'] is None)) or (query['reported_hit_count_line'] is not None and query['reported_hit_count_line'] <= query['query_header_line']) or (query['close_marker_line'] is not None and query['close_marker_line'] <= query['query_header_line']) or (query['close_marker_line'] is not None and query['reported_hit_count_line'] is not None and (query['close_marker_line'] <= query['reported_hit_count_line'])):
            raise ValueError(code)
    if value['complete'] and (value['issues'] or not value['queries'] or any((q['reported_hit_count'] is None or q['close_marker_line'] is None for q in value['queries']))):
        raise ValueError(code)
    return value
