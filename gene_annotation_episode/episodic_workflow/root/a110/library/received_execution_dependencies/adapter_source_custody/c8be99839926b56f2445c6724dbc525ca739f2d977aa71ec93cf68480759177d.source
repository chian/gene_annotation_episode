"""Retained SubspeciesClassification tables with literal native row custody.

The AppService host authenticates the task and File. This reader preserves
every row and cell, including blank, duplicate and malformed observations.
Native confidence, identity, coverage and E-value tokens are never rescaled.
"""
from copy import deepcopy
import hashlib

from .bvbrc_annotation_native import _canonical, _content, _finite_json


DOCUMENT_VERSION = "bvbrc_subspecies_native_document_v1"
COMPONENTS_VERSION = "bvbrc_subspecies_components_v1"
REPRESENTATIONS = ("classification_summary", "cladinator_results", "rota_result", "rota_error")
_DOCUMENT_FIELDS = {"version", "representation", "content", "capture_complete", "expected_task_id",
    "parsing_state", "native_document", "issues"}


def _require(condition, code="bvbrc_subspecies_document_invalid"):
    if not condition:
        raise ValueError(code)


def _issue(code, path, severity="qualification"):
    return dict(code=code, path=path, severity=severity)


def _line(raw, ordinal, start):
    ending = "\r\n" if raw.endswith(b"\r\n") else "\n" if raw.endswith(b"\n") else "\r" if raw.endswith(b"\r") else ""
    text = raw.decode("utf-8")
    literal = text[:-len(ending)] if ending else text
    return dict(raw_line=literal, cells=literal.split("\t"), line_ending=ending,
        source_location=dict(byte_start_0based=start, byte_end_0based_exclusive=start + len(raw),
            line_1based=ordinal + 1))


def _table_issues(native, representation):
    issues = []
    header = native["header"]
    if header is None:
        return [_issue("native_table_header_missing", "/native_document/header", "error")]
    names = header["cells"]
    if representation == "classification_summary" and names != ["Query Identifier", "Clade Classification"]:
        issues.append(_issue("native_summary_header_incompatible", "/native_document/header", "error"))
    if representation == "cladinator_results":
        for name in ("Query", "Assignment"):
            if names.count(name) != 1:
                issues.append(_issue("native_cladinator_column_missing_or_ambiguous", "/native_document/header", "error"))
    if representation in {"rota_result", "rota_error"}:
        issues.append(_issue("native_rota_column_schema_unverified", "/native_document/header"))
    if len(set(names)) != len(names):
        issues.append(_issue("native_table_duplicate_column_names", "/native_document/header"))
    for ordinal, row in enumerate(native["rows"]):
        if len(row["cells"]) != len(names):
            issues.append(_issue("native_table_row_width_conflict", "/native_document/rows/" + str(ordinal), "error"))
        if row["raw_line"] == "":
            issues.append(_issue("native_table_blank_row", "/native_document/rows/" + str(ordinal)))
        if representation == "classification_summary" and names == ["Query Identifier", "Clade Classification"]:
            required = (0, 1)
        elif representation == "cladinator_results":
            required = tuple(index for index, name in enumerate(names) if name in {"Query", "Assignment"})
        else:
            required = (0, 2) if representation == "rota_result" else (0,)
        if any(index < len(row["cells"]) and row["cells"][index] == "" for index in required):
            issues.append(_issue("native_query_or_classification_empty", "/native_document/rows/" + str(ordinal)))
    if representation == "rota_error" and native["rows"]:
        issues.append(_issue("native_rota_errors_reported", "/native_document/rows"))
    return issues


def parse_subspecies_artifact(raw, *, content, representation, capture_complete, expected_task_id):
    content = _content(content)
    _require(type(raw) is bytes and len(raw) == content["byte_count"]
        and hashlib.sha256(raw).hexdigest() == content["sha256"], "bvbrc_subspecies_bytes_conflict")
    _require(type(representation) is str and representation in REPRESENTATIONS
        and type(capture_complete) is bool and type(expected_task_id) is str and bool(expected_task_id))
    native, issues = None, []
    try:
        raw.decode("utf-8")
        lines, start = [], 0
        for ordinal, line in enumerate(raw.splitlines(keepends=True)):
            lines.append(_line(line, ordinal, start))
            start += len(line)
        header, rows = (lines[0], lines[1:]) if lines else (None, [])
        for ordinal, row in enumerate(rows):
            row["row_ordinal"] = ordinal
        native = dict(delimiter="\t", encoding="utf-8", header=header, rows=rows)
        issues = _table_issues(native, representation)
    except UnicodeError:
        issues.append(_issue("invalid_native_utf8", "/native_document", "error"))
    if not capture_complete:
        issues.append(_issue("native_capture_incomplete", "/capture_complete"))
    return validate_subspecies_document(dict(version=DOCUMENT_VERSION, representation=representation,
        content=content, capture_complete=capture_complete, expected_task_id=expected_task_id,
        parsing_state="unavailable" if native is None else "available", native_document=native, issues=issues))


def validate_subspecies_document(value):
    """Validate saved observations without native I/O or numerical work."""
    _finite_json(value)
    _require(type(value) is dict and set(value) == _DOCUMENT_FIELDS and value["version"] == DOCUMENT_VERSION
        and type(value["representation"]) is str and value["representation"] in REPRESENTATIONS
        and type(value["capture_complete"]) is bool
        and type(value["expected_task_id"]) is str and bool(value["expected_task_id"])
        and value["parsing_state"] in {"available", "unavailable"} and type(value["issues"]) is list)
    content = _content(value["content"])
    native = value["native_document"]
    _require((native is None) == (value["parsing_state"] == "unavailable"))
    expected = []
    if native is None:
        expected.append(_issue("invalid_native_utf8", "/native_document", "error"))
    else:
        _require(type(native) is dict and set(native) == {"delimiter", "encoding", "header", "rows"}
            and native["delimiter"] == "\t" and native["encoding"] == "utf-8" and type(native["rows"]) is list)
        _require(native["header"] is not None or native["rows"] == [])
        start = 0
        digest = hashlib.sha256()
        physical = ([] if native["header"] is None else [native["header"]]) + native["rows"]
        for ordinal, row in enumerate(physical):
            fields = {"raw_line", "cells", "line_ending", "source_location"} | ({"row_ordinal"} if ordinal else set())
            _require(type(row) is dict and set(row) == fields and type(row["raw_line"]) is str
                and "\r" not in row["raw_line"] and "\n" not in row["raw_line"]
                and row["cells"] == row["raw_line"].split("\t")
                and row["line_ending"] in {"", "\n", "\r", "\r\n"})
            if ordinal:
                _require(type(row["row_ordinal"]) is int and row["row_ordinal"] == ordinal - 1)
            _require(ordinal == len(physical) - 1 or row["line_ending"] != "")
            raw = (row["raw_line"] + row["line_ending"]).encode("utf-8")
            _require(row["source_location"] == dict(byte_start_0based=start,
                byte_end_0based_exclusive=start + len(raw), line_1based=ordinal + 1))
            digest.update(raw)
            start += len(raw)
        _require(start == content["byte_count"] and digest.hexdigest() == content["sha256"],
            "bvbrc_subspecies_saved_bytes_conflict")
        expected.extend(_table_issues(native, value["representation"]))
    if not value["capture_complete"]:
        expected.append(_issue("native_capture_incomplete", "/capture_complete"))
    _require(_canonical(value["issues"]) == _canonical(expected))
    return deepcopy(value)


def _cell(row, positions):
    if not positions:
        return dict(state="column_missing", column_ordinals=[], tokens=[])
    tokens = [row["cells"][index] if index < len(row["cells"]) else None for index in positions]
    state = ("column_ambiguous" if len(positions) > 1 else "cell_missing" if tokens[0] is None
        else "stored_empty" if tokens[0] == "" else "available")
    return dict(state=state, column_ordinals=positions, tokens=tokens)


def calculate_subspecies_components(document):
    """One authority for counts and semantic column associations, without inference."""
    document = validate_subspecies_document(document)
    native, representation = document["native_document"], document["representation"]
    names = [] if native is None or native["header"] is None else native["header"]["cells"]
    fields = {"classification_summary": {"query": "Query Identifier", "classification": "Clade Classification"},
        "cladinator_results": {"query": "Query", "classification": "Assignment", "confidence": "Confidence"},
        "rota_result": {"query": 0, "classification": 2},
        "rota_error": {"query": 0}}[representation]
    positions = {key: ([name] if type(name) is int and name < len(names) else []
        if type(name) is int else [index for index, observed in enumerate(names) if observed == name])
        for key, name in fields.items()}
    rows = None if native is None else [dict(row_ordinal=row["row_ordinal"],
        fields={name: _cell(row, indices) for name, indices in positions.items()}) for row in native["rows"]]
    return dict(version=COMPONENTS_VERSION, document_sha256=hashlib.sha256(_canonical(document)).hexdigest(),
        representation=representation, status="partial" if document["issues"] else "complete",
        population=dict(scope="one_selected_retained_artifact", observed_row_count=None if rows is None else len(rows),
            complete_artifact_population=document["capture_complete"] and not document["issues"] if rows is not None else None,
            intended_query_population_complete=None), rows=rows,
        definitions=dict(authority="bvbrc_subspecies_native.calculate_subspecies_components",
            identity="Exact reported table tokens; no inverse of producer header cleaning or cross-file identity join is inferred.",
            classification="Native reported assignment or genotype; empty, missing and ambiguous cells remain distinct.",
            confidence="Native Confidence token, without an assumed probability scale or threshold.",
            other_columns="Remaining rotavirus columns retain their native header labels and tokens without inferred units, numerical conversion or a claimed verified schema.",
            population="Rows include duplicates, errors and malformed observations. Summary output may already have collapsed repeated cleaned queries in the native producer; intended input coverage is unknown."),
        issues=deepcopy(document["issues"]))


__all__ = ["DOCUMENT_VERSION", "COMPONENTS_VERSION", "REPRESENTATIONS", "parse_subspecies_artifact",
    "validate_subspecies_document", "calculate_subspecies_components"]
