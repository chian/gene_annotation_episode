"""Pure occurrence bindings for the observed Rfam Infernal batch table.

The native row grammar and numerical cells belong to infernal_search_inputs;
saved sheets are recalculated by infernal_search_grader. This adapter validates
the complete submitted FASTA and supplied custody, and adds the input population
that a hit-only table cannot enumerate. It performs no acquisition or execution.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import math
import re
from typing import Literal, TypedDict

from .infernal_search_inputs import populate_infernal_search_sheet


RFAM_BATCH_TABLE_FORMAT = "infernal_tblout_1_cmscan_1_1_5"
RFAM_BATCH_TABLE_ISSUE_CODES = frozenset("""
rfam_batch_input_invalid rfam_batch_submitted_content_invalid
rfam_batch_submitted_file_conflict rfam_batch_fasta_invalid
rfam_batch_native_name_ambiguous rfam_batch_occurrence_key_ambiguous
rfam_batch_fasta_membership_conflict rfam_batch_sequence_conflict
rfam_batch_header_transform_conflict rfam_batch_capture_invalid
rfam_batch_source_identity_conflict rfam_batch_result_job_conflict
rfam_batch_result_file_conflict rfam_batch_submission_source_conflict
rfam_batch_http_error rfam_batch_representation_unsupported
rfam_batch_native_text_unsupported rfam_batch_table_format_unsupported
rfam_batch_native_program_unsupported rfam_batch_native_version_unsupported
rfam_batch_native_mode_unsupported rfam_batch_native_query_file_conflict
rfam_batch_native_profile_incomplete rfam_batch_native_table_incomplete
rfam_batch_foreign_native_query rfam_batch_model_metadata_invalid
rfam_batch_model_provenance_unverified rfam_batch_report_invalid
rfam_batch_report_job_conflict rfam_batch_report_profile_unsupported
rfam_batch_report_query_file_conflict rfam_batch_report_incomplete
rfam_batch_report_query_invalid rfam_batch_report_count_invalid
rfam_batch_report_count_duplicate rfam_batch_report_query_unclosed
rfam_batch_report_close_unmatched rfam_batch_report_name_ambiguous
rfam_batch_report_foreign_query rfam_batch_report_query_missing
rfam_batch_report_length_conflict rfam_batch_report_count_conflict
rfam_batch_report_population_incomplete
""".split())


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
    version: Literal["rfam_batch_file_input_v1"]
    expected_job_id: str
    submission_source_ref: str
    submitted_file_sha256: str
    submitted_file_bytes: int
    filename: str
    header_transform: Literal["generated_unique_headers", "unchanged_unique_headers"]
    queries: list[RfamBatchFileQuery]


class RfamBatchTableCapture(TypedDict):
    artifact_ref: str
    source_ref: str
    source_sha256: str
    evidence_kind: Literal["native_response", "official_documentation_example", "synthetic_fixture"]
    representation: Literal["tblout", "out"]
    http_status: int | None
    body_complete: bool
    request_job_id: str
    request_file_sha256: str
    submission_source_ref: str


class RfamBatchTableIssue(TypedDict):
    code: str
    severity: Literal["error", "warning"]
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
    membership_basis: Literal["frozen_complete_input", "native_report", "both"]
    reported_row_count: int | None
    reported_set_complete: bool


class RfamBatchTableParseResult(TypedDict):
    version: Literal["rfam_batch_tblout_parse_result_v1"]
    status: Literal["complete", "partial", "rejected", "unsupported"]
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


_HEADER = ("target name accession query name accession mdl mdl from mdl to seq from "
           "seq to strand trunc pass gc bias score E-value inc description of target")
_NUCLEOTIDES = re.compile(r"[ACGTURYSWKMBDHVNacgturyswkmbdhvn]+")


def _text(value):
    return type(value) is str and bool(value.strip()) and "\x00" not in value


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _sha256(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _job(value):
    return type(value) is str and re.fullmatch(r"infernal_cmscan-[A-Za-z0-9_-]+", value) is not None


def _finite(value, code):
    if value is None or type(value) in (str, int, bool):
        return deepcopy(value)
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_finite(item, code) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _finite(item, code) for key, item in value.items()}
    raise ValueError(code)


def _closed(value, fields, code):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(code)


def _issue(code, *, severity="error", field=None, native_query_name=None, source_line=None):
    assert code in RFAM_BATCH_TABLE_ISSUE_CODES
    return {"code": code, "severity": severity, "field": field,
            "native_query_name": native_query_name, "source_line": source_line}


def _fasta(content):
    if type(content) is not bytes or not content:
        raise ValueError("rfam_batch_submitted_content_invalid")
    try:
        text = content.decode("ascii")
    except UnicodeError as error:
        raise ValueError("rfam_batch_submitted_content_invalid") from error
    # Newlines may be LF or CRLF. Do not remove sequence whitespace, change case,
    # translate T/U, or accept unheaded auto-generated names.
    if any(ord(c) < 32 and c not in "\r\n\t" or ord(c) == 127 for c in text) or "\r" in text.replace("\r\n", ""):
        raise ValueError("rfam_batch_fasta_invalid")
    records = []
    current = None
    for line in text.splitlines():
        if line.startswith(">"):
            header = line[1:]
            if not header.split():
                raise ValueError("rfam_batch_fasta_invalid")
            current = {"header": header, "name": header.split()[0], "parts": []}
            records.append(current)
        elif line:
            if current is None or _NUCLEOTIDES.fullmatch(line) is None:
                raise ValueError("rfam_batch_fasta_invalid")
            current["parts"].append(line)
    if not records or any(not record["parts"] for record in records):
        raise ValueError("rfam_batch_fasta_invalid")
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        raise ValueError("rfam_batch_native_name_ambiguous")
    return [{"header": r["header"], "name": r["name"], "sequence": "".join(r["parts"])} for r in records]


def validate_rfam_batch_file_input(input_identity, *, submitted_content: bytes) -> None:
    """Validate a complete ordered manifest against the actual submitted bytes.

    Original-reference custody and coordinate-map contents are supplied by the
    caller. This validator checks their declarations; it never opens those refs.
    Non-identity coordinate transforms require an explicit mapping reference.
    """
    code = "rfam_batch_input_invalid"
    identity = _finite(input_identity, code)
    _closed(identity, RfamBatchFileInputIdentity.__annotations__, code)
    if (identity["version"] != "rfam_batch_file_input_v1"
            or not _job(identity["expected_job_id"])
            or not _text(identity["submission_source_ref"])
            or not _sha256(identity["submitted_file_sha256"])
            or not _integer(identity["submitted_file_bytes"], 1)
            or not _text(identity["filename"]) or any(c in identity["filename"] for c in "/\\\r\n")
            or identity["header_transform"] not in ("generated_unique_headers", "unchanged_unique_headers")
            or type(identity["queries"]) is not list or not identity["queries"]):
        raise ValueError(code)
    records = _fasta(submitted_content)
    if (len(submitted_content) != identity["submitted_file_bytes"]
            or hashlib.sha256(submitted_content).hexdigest() != identity["submitted_file_sha256"]):
        raise ValueError("rfam_batch_submitted_file_conflict")
    if len(records) != len(identity["queries"]):
        raise ValueError("rfam_batch_fasta_membership_conflict")
    keys, names = set(), set()
    for ordinal, (query, record) in enumerate(zip(identity["queries"], records)):
        _closed(query, RfamBatchFileQuery.__annotations__, code)
        if (any(not _text(query[key]) for key in ("query_occurrence_key", "subject_ref", "original_input_ref"))
                or query["original_record_ordinal"] is not None and not _integer(query["original_record_ordinal"])
                or query["original_header"] is not None and (type(query["original_header"]) is not str
                    or any(c in query["original_header"] for c in "\x00\r\n"))
                or not _integer(query["selected_occurrence_ordinal"]) or query["selected_occurrence_ordinal"] != ordinal
                or not _text(query["native_query_name"]) or not query["native_query_name"].isascii()
                or any(c.isspace() for c in query["native_query_name"])
                or query["input_to_submitted_transform"] not in ("unchanged", "registered_view", "feature_segments")
                or query["input_coordinate_mapping_ref"] is not None and not _text(query["input_coordinate_mapping_ref"])
                or query["input_to_submitted_transform"] != "unchanged" and query["input_coordinate_mapping_ref"] is None):
            raise ValueError(code)
        if query["query_occurrence_key"] in keys:
            raise ValueError("rfam_batch_occurrence_key_ambiguous")
        if query["native_query_name"] in names:
            raise ValueError("rfam_batch_native_name_ambiguous")
        keys.add(query["query_occurrence_key"])
        names.add(query["native_query_name"])
        if query["native_query_name"] != record["name"]:
            raise ValueError("rfam_batch_fasta_membership_conflict")
        sequence = query["submitted_sequence"]
        if (type(sequence) is not str or _NUCLEOTIDES.fullmatch(sequence) is None
                or sequence != record["sequence"] or not _integer(query["submitted_length_nt"], 1)
                or len(sequence) != query["submitted_length_nt"] or not _sha256(query["submitted_sequence_sha256"])
                or hashlib.sha256(sequence.encode("ascii")).hexdigest() != query["submitted_sequence_sha256"]):
            raise ValueError("rfam_batch_sequence_conflict")
        if (identity["header_transform"] == "unchanged_unique_headers" and query["original_header"] is not None
                and query["original_header"] != record["header"]):
            raise ValueError("rfam_batch_header_transform_conflict")


def _capture(value, content):
    code = "rfam_batch_capture_invalid"
    value = _finite(value, code)
    _closed(value, RfamBatchTableCapture.__annotations__, code)
    if (any(not _text(value[key]) for key in ("artifact_ref", "source_ref", "submission_source_ref"))
            or not _sha256(value["source_sha256"]) or not _sha256(value["request_file_sha256"])
            or not _job(value["request_job_id"])
            or value["representation"] not in ("tblout", "out")
            or value["evidence_kind"] not in ("native_response", "official_documentation_example", "synthetic_fixture")
            or value["http_status"] is not None and (not _integer(value["http_status"], 100) or value["http_status"] > 599)
            or type(value["body_complete"]) is not bool):
        raise ValueError(code)
    if type(content) is not bytes or hashlib.sha256(content).hexdigest() != value["source_sha256"]:
        raise ValueError("rfam_batch_source_identity_conflict")
    if value["http_status"] not in (None, 200) or value["evidence_kind"] == "native_response" and value["http_status"] is None:
        raise ValueError("rfam_batch_http_error")
    return value


def _result(status, issues, *, capture=None, identity=None, metadata=None, sheet=None,
            bindings=None, population=None, recognized=False):
    from .rfam_batch_infernal import rfam_parse_envelope
    return rfam_parse_envelope(representation="tblout", status=status,
        format=RFAM_BATCH_TABLE_FORMAT if recognized else "unrecognized", sheet=sheet, issues=issues)


def _report_membership(value):
    code = "rfam_batch_report_invalid"
    value = _finite(value, code)
    _closed(value, RfamReportMembership.__annotations__, code)
    if (not _sha256(value["source_sha256"]) or not _text(value["artifact_ref"])
            or not _job(value["request_job_id"]) or type(value["complete"]) is not bool
            or type(value["queries"]) is not list or type(value["issues"]) is not list):
        raise ValueError(code)
    for issue in value["issues"]:
        _closed(issue, RfamBatchTableIssue.__annotations__, code)
        if (not _text(issue["code"]) or issue["code"] not in RFAM_BATCH_TABLE_ISSUE_CODES or issue["severity"] not in ("error", "warning")
                or any(issue[key] is not None and not _text(issue[key]) for key in ("field", "native_query_name"))
                or issue["source_line"] is not None and not _integer(issue["source_line"], 1)):
            raise ValueError(code)
    for query in value["queries"]:
        _closed(query, RfamReportQueryMembership.__annotations__, code)
        if (not _text(query["native_query_name"]) or not _integer(query["query_header_line"], 1)
                or not _integer(query["length_nt"], 1)
                or query["reported_hit_count"] is not None and not _integer(query["reported_hit_count"])
                or any(query[key] is not None and not _integer(query[key], 1)
                       for key in ("reported_hit_count_line", "close_marker_line"))
                or (query["reported_hit_count"] is None) != (query["reported_hit_count_line"] is None)
                or query["reported_hit_count_line"] is not None and query["reported_hit_count_line"] <= query["query_header_line"]
                or query["close_marker_line"] is not None and query["close_marker_line"] <= query["query_header_line"]
                or query["close_marker_line"] is not None and query["reported_hit_count_line"] is not None
                    and query["close_marker_line"] <= query["reported_hit_count_line"]):
            raise ValueError(code)
    if value["complete"] and (value["issues"] or not value["queries"] or any(
            q["reported_hit_count"] is None or q["close_marker_line"] is None for q in value["queries"])):
        raise ValueError(code)
    return value


def _join_report(report, identity, counts, table_complete, issues):
    """Return names with agreeing source membership and population qualification."""
    if report is None:
        return set(), table_complete
    try:
        report = _report_membership(report)
    except ValueError as error:
        issues.append(_issue(str(error), field="report_membership"))
        return set(), False
    issues.extend(deepcopy(report["issues"]))
    if report["request_job_id"] != identity["expected_job_id"]:
        issues.append(_issue("rfam_batch_report_job_conflict", field="report_membership.request_job_id"))
        return set(), False
    if any(issue["code"] in {"rfam_batch_report_query_file_conflict", "rfam_batch_report_profile_unsupported"}
           for issue in report["issues"]):
        return set(), False
    supplied = {q["native_query_name"]: q for q in identity["queries"]}
    occurrences = Counter(q["native_query_name"] for q in report["queries"])
    agreed = set()
    conflict = bool(report["issues"])
    for query in report["queries"]:
        name = query["native_query_name"]
        detail = {"native_query_name": name, "source_line": query["query_header_line"]}
        if occurrences[name] != 1:
            issues.append(_issue("rfam_batch_report_name_ambiguous", **detail))
            conflict = True
        elif name not in supplied:
            issues.append(_issue("rfam_batch_report_foreign_query", **detail))
            conflict = True
        elif query["length_nt"] != supplied[name]["submitted_length_nt"]:
            issues.append(_issue("rfam_batch_report_length_conflict", field="length_nt", **detail))
            conflict = True
        else:
            agreed.add(name)
            count = query["reported_hit_count"]
            # A partial table can have fewer rows; it can never have more than
            # the complete query's explicitly reported count.
            if count is not None and (counts[name] > count or table_complete and counts[name] != count):
                issues.append(_issue("rfam_batch_report_count_conflict", field="reported_hit_count",
                    native_query_name=name, source_line=query["reported_hit_count_line"]))
                conflict = True
    for name in supplied.keys() - occurrences.keys():
        issues.append(_issue("rfam_batch_report_query_missing", native_query_name=name))
        conflict = True
    if not report["complete"]:
        issues.append(_issue("rfam_batch_report_population_incomplete", field="report_membership", severity="warning"))
    return agreed, table_complete and report["complete"] and not conflict


def populate_rfam_batch_tblout_sheet(content: bytes, *, input_identity, capture,
        submitted_content: bytes, report_membership=None, model_metadata=None) -> RfamBatchTableParseResult:
    """Bind the actual Infernal sheet to every original selected occurrence.

    Row counts count retained native row representations, never independent
    evidence. With incomplete native populations, an unseen query has a null
    count; a positive observed count is retained as partial. Zero means no
    reported rows under the original settings, not biological absence.
    """
    identity = checked_capture = metadata = None
    issues = []
    try:
        validate_rfam_batch_file_input(input_identity, submitted_content=submitted_content)
        identity = deepcopy(input_identity)
        checked_capture = _capture(capture, content)
        for field, expected, code in (
                ("request_job_id", identity["expected_job_id"], "rfam_batch_result_job_conflict"),
                ("request_file_sha256", identity["submitted_file_sha256"], "rfam_batch_result_file_conflict"),
                ("submission_source_ref", identity["submission_source_ref"], "rfam_batch_submission_source_conflict")):
            if checked_capture[field] != expected:
                raise ValueError(code)
    except ValueError as error:
        return _result("rejected", [_issue(str(error))], capture=checked_capture, identity=identity)
    common = {"capture": checked_capture, "identity": identity}
    if model_metadata is not None:
        try:
            metadata = _finite(model_metadata, "rfam_batch_model_metadata_invalid")
            if type(metadata) is not dict:
                raise ValueError("rfam_batch_model_metadata_invalid")
        except ValueError:
            metadata = None
            issues.append(_issue("rfam_batch_model_metadata_invalid", field="supplied_model_metadata"))
        else:
            issues.append(_issue("rfam_batch_model_provenance_unverified", severity="warning", field="supplied_model_metadata"))
    common["metadata"] = metadata
    if checked_capture["representation"] != "tblout":
        return _result("unsupported", [*issues, _issue("rfam_batch_representation_unsupported")], **common)
    try:
        text = content.decode("ascii")
        if "\x00" in text:
            raise ValueError
    except (UnicodeError, ValueError):
        return _result("unsupported", [*issues, _issue("rfam_batch_native_text_unsupported")], **common)
    lines = text.splitlines()
    markers = [index for index, line in enumerate(lines) if line.strip() == "# [ok]"]
    terminal = len(markers) == 1 and not any(line.strip() for line in lines[markers[0] + 1:])
    native_complete = checked_capture["body_complete"] and terminal
    # The observed footer, not an HTTP EOF by itself, establishes that the
    # native stream is complete. Native rows are parsed only by the shared reader.
    sheet = populate_infernal_search_sheet(
        [{"artifact_id": checked_capture["artifact_ref"], "format": "infernal_tblout", "table_format": 1,
          "complete": native_complete, "content": text}],
        operation={"program": "cmscan", "native_version": "1.1.5", "settings": {}},
        sequence_metadata=[{"name": q["native_query_name"], "length": q["submitted_length_nt"],
            "sequence": q["submitted_sequence"], "artifact_id": checked_capture["artifact_ref"]}
            for q in identity["queries"]], model_metadata=None)
    artifact = sheet["artifacts"][0]
    fields = artifact["footer"]["fields"]
    supported = True
    headers = [" ".join(h["text"].lstrip().lstrip("#").split()) for h in artifact["headers"]]
    if artifact["observed_table_format"] != 1 or _HEADER not in headers:
        issues.append(_issue("rfam_batch_table_format_unsupported", field="native_table_header"))
        supported = False
    profile_complete = True
    for field, expected, code in (("Program", "cmscan", "rfam_batch_native_program_unsupported"),
            ("Version", "1.1.5", "rfam_batch_native_version_unsupported"),
            ("Pipeline mode", "SCAN", "rfam_batch_native_mode_unsupported")):
        declarations = fields.get(field, [])
        values = {row["value"].split()[0] if field == "Version" and row["value"] else row["value"] for row in declarations}
        if not values:
            issues.append(_issue("rfam_batch_native_profile_incomplete", severity="warning", field=field))
            profile_complete = False
        elif values != {expected}:
            issues.append(_issue(code, field=field, source_line=declarations[0]["line"]))
            supported = False
    filenames = fields.get("Query file", [])
    if filenames and {row["value"] for row in filenames} != {identity["expected_job_id"] + ".sequence"}:
        issues.append(_issue("rfam_batch_native_query_file_conflict", field="Query file", source_line=filenames[0]["line"]))
        return _result("rejected", issues, **common)
    if not filenames:
        issues.append(_issue("rfam_batch_native_profile_incomplete", severity="warning", field="Query file"))
        profile_complete = False
    if not supported:
        return _result("unsupported", issues, **common)
    if not native_complete:
        issues.append(_issue("rfam_batch_native_table_incomplete", severity="warning", field="native_completion"))
    bindings = [{"sequence_metadata_index": index, "native_query_name": q["native_query_name"],
        "query_occurrence_key": q["query_occurrence_key"], "selected_occurrence_ordinal": q["selected_occurrence_ordinal"]}
        for index, q in enumerate(identity["queries"])]
    names = {q["native_query_name"] for q in identity["queries"]}
    counts = Counter(hit["native_query_name"] for hit in sheet["hits"])
    foreign = False
    for hit in sheet["hits"]:
        if hit["native_query_name"] not in names:
            issues.append(_issue("rfam_batch_foreign_native_query", native_query_name=hit["native_query_name"],
                source_line=hit["locator"]["line"]))
            foreign = True
    population_complete = native_complete and profile_complete and artifact["retained_population_complete"] and not foreign
    report_names, population_complete = _join_report(report_membership, identity, counts, population_complete, issues)
    population = [{"query_occurrence_key": q["query_occurrence_key"], "submitted_length_nt": q["submitted_length_nt"],
        "membership_basis": "both" if q["native_query_name"] in report_names else "frozen_complete_input",
        "reported_row_count": counts[q["native_query_name"]] if counts[q["native_query_name"]] or population_complete else None,
        "reported_set_complete": population_complete} for q in identity["queries"]]
    from .rfam_batch_infernal import populate_rfam_table_cells
    sheet = populate_rfam_table_cells(sheet=sheet, capture=checked_capture, input_identity=identity,
        supplied_model_metadata=metadata, occurrence_bindings=bindings, query_population=population,
        issues=issues, content=content, report_membership=report_membership)
    return _result("partial" if issues or sheet["status"] != "available" else "complete", issues,
        sheet=sheet, bindings=bindings, population=population, recognized=True, **common)


def parse_rfam_report_membership(content: bytes, *, capture: dict) -> RfamReportMembership:
    """Extract source-located query population facts, without parsing alignments."""
    result = {"source_sha256": None, "artifact_ref": None, "request_job_id": None,
              "complete": False, "queries": [], "issues": []}
    issues = result["issues"]
    try:
        capture = _capture(capture, content)
    except ValueError as error:
        issues.append(_issue(str(error)))
        return result
    result.update({key: capture[key] for key in ("source_sha256", "artifact_ref", "request_job_id")})
    if capture["representation"] != "out":
        issues.append(_issue("rfam_batch_representation_unsupported", field="representation"))
        return result
    try:
        text = content.decode("ascii")
        if "\x00" in text:
            raise ValueError
    except (UnicodeError, ValueError):
        issues.append(_issue("rfam_batch_native_text_unsupported"))
        return result
    lines = text.splitlines()
    programs = [match.group(1) for line in lines if (match := re.match(r"^#\s*(\S+)\s+::", line))]
    versions = [match.group(1) for line in lines if (match := re.match(r"^#\s*INFERNAL\s+(\S+)", line))]
    if programs != ["cmscan"] or versions != ["1.1.5"]:
        issues.append(_issue("rfam_batch_report_profile_unsupported"))
    filenames = [(number, match.group(1).strip()) for number, line in enumerate(lines, 1)
                 if (match := re.match(r"^#\s*query sequence file:\s*(.*)$", line))]
    if not filenames or {name for _, name in filenames} != {capture["request_job_id"] + ".sequence"}:
        issues.append(_issue("rfam_batch_report_query_file_conflict", field="query sequence file",
            source_line=filenames[0][0] if filenames else None))
    current = None
    count_seen = False
    markers = []
    for number, line in enumerate(lines, 1):
        if line.startswith("Query:"):
            if current is not None:
                issues.append(_issue("rfam_batch_report_query_unclosed", native_query_name=current["native_query_name"],
                    source_line=current["query_header_line"]))
            current, count_seen = None, False
            match = re.fullmatch(r"Query:\s+(\S+)\s+\[L=([0-9]+)\]\s*", line)
            try:
                length = int(match.group(2)) if match else 0
            except ValueError:
                length = 0
            if length < 1:
                issues.append(_issue("rfam_batch_report_query_invalid", source_line=number))
                continue
            current = {"native_query_name": match.group(1), "query_header_line": number,
                "length_nt": length, "reported_hit_count": None,
                "reported_hit_count_line": None, "close_marker_line": None}
            result["queries"].append(current)
        elif line.startswith("Total CM hits reported:"):
            match = re.fullmatch(r"Total CM hits reported:\s+([0-9]+)(?:\s+.*)?", line)
            try:
                count = int(match.group(1)) if match else None
            except ValueError:
                count = None
            if current is None or count is None:
                issues.append(_issue("rfam_batch_report_count_invalid", source_line=number))
            elif count_seen:
                current.update(reported_hit_count=None, reported_hit_count_line=None)
                issues.append(_issue("rfam_batch_report_count_duplicate", native_query_name=current["native_query_name"], source_line=number))
            else:
                current.update(reported_hit_count=count, reported_hit_count_line=number)
            count_seen = True
        elif line.strip() == "//":
            if current is None:
                issues.append(_issue("rfam_batch_report_close_unmatched", source_line=number))
            else:
                current["close_marker_line"] = number
                if current["reported_hit_count"] is None:
                    issues.append(_issue("rfam_batch_report_count_invalid", native_query_name=current["native_query_name"], source_line=number))
                current = None
        elif line.strip() == "[ok]":
            markers.append(number)
    if current is not None:
        issues.append(_issue("rfam_batch_report_query_unclosed", native_query_name=current["native_query_name"],
            source_line=current["query_header_line"]))
    names = Counter(query["native_query_name"] for query in result["queries"])
    for query in result["queries"]:
        if names[query["native_query_name"]] > 1:
            issues.append(_issue("rfam_batch_report_name_ambiguous", native_query_name=query["native_query_name"],
                source_line=query["query_header_line"]))
    terminal = len(markers) == 1 and not any(line.strip() for line in lines[markers[0]:])
    if not capture["body_complete"] or not terminal or not result["queries"]:
        issues.append(_issue("rfam_batch_report_incomplete", severity="warning"))
    result["complete"] = not issues
    return result


__all__ = ["RfamBatchFileInputIdentity", "RfamBatchFileQuery", "RfamBatchTableCapture",
    "RfamBatchTableIssue", "RfamBatchTableParseResult", "RfamReportMembership",
    "RFAM_BATCH_TABLE_FORMAT", "RFAM_BATCH_TABLE_ISSUE_CODES", "validate_rfam_batch_file_input",
    "populate_rfam_batch_tblout_sheet", "parse_rfam_report_membership"]
