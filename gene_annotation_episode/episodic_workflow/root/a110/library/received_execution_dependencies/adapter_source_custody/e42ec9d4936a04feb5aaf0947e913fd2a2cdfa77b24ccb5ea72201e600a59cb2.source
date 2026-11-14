"""Literal observations from the retained HA conversion producer's artifacts.

The native TSV reports the selected HSP, not every hit. Its query names and
original sequence headers remain separate. Aligned FASTA uses the existing
alignment reader and numerical authority; offsets are staged residue offsets,
not a claim of biological HA numbering or a particular reference release.
"""
from __future__ import annotations

from copy import deepcopy
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import math
import re

from .bvbrc_annotation_native import _canonical, _content, _finite_json, _issue
from .phylogeny_format_contracts import _location, validate_alignment_document
from .phylogeny_formats import parse_aligned_fasta
from .phylogeny_calculators import alignment_components, ungapped_coordinate_map


DOCUMENT_VERSION = "bvbrc_influenza_ha_native_document_v1"
COMPONENTS_VERSION = "bvbrc_influenza_ha_components_v1"
REPRESENTATIONS = ("sequence_annotation_tsv", "result_alignment_fasta")
HEADER = ("QueryId", "Virus Type", "Segment", "Subtype", "Bitscore", "E-value",
    "Warning Messages", "Sequence Name")
_FIELDS = {"version", "representation", "content", "capture_complete", "expected_task_id",
    "parsing_state", "native_document", "issues"}
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z", re.ASCII)


def _require(condition, code="bvbrc_influenza_ha_document_invalid"):
    if not condition:
        raise ValueError(code)


def _artifact(content):
    return dict(raw_artifact_ref=content["artifact_ref"], source_ref=content["source_ref"], sha256=content["sha256"])


def _table(raw, content):
    try:
        text = raw.decode("utf-8")
        text.encode("utf-8")
    except UnicodeError:
        return None, [_issue("invalid_native_utf8", "/native_document", severity="error")]
    # csv.DictWriter in the pinned producer uses Excel TSV quoting and CRLF.
    # Source boundaries include quoted embedded newlines and the record ending.
    lines = [match.group() for match in re.finditer(r"[^\r\n]*(?:\r\n|\r|\n|$)", text)
        if match.start() < len(text)]
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    reader = csv.reader(io.StringIO(text, newline=""), delimiter="\t", strict=True)
    rows, header, issues, previous = [], None, [], 0
    try:
        for cells in reader:
            end = reader.line_num
            if header is None:
                header = cells
                if header != list(HEADER):
                    issues.append(_issue("ha_annotation_header_conflict", "/native_document/header", severity="error"))
            else:
                row_index = len(rows)
                rows.append(dict(row_index=row_index, cells=cells, source_location=dict(
                    artifact=_artifact(content), byte_start_0based=offsets[previous],
                    byte_end_0based_exclusive=offsets[end], line_start_1based=previous + 1,
                    line_end_1based_inclusive=end, xml_path=None)))
                if len(cells) != len(HEADER):
                    issues.append(_issue("ha_annotation_record_width_conflict",
                        "/native_document/rows/" + str(row_index), severity="error"))
            previous = end
    except csv.Error:
        issues.append(_issue("ha_annotation_tsv_syntax_invalid", "/native_document/rows", severity="error"))
    if header is None:
        issues.append(_issue("ha_annotation_header_missing", "/native_document/header", severity="error"))
    return dict(header=header, rows=rows, raw_text=text,
        completeness="partial" if issues else "complete"), issues


def parse_influenza_ha_artifact(raw, *, content, representation, capture_complete, expected_task_id):
    """Read an explicitly selected artifact without opening paths or running science."""
    content = _content(content)
    _require(type(raw) is bytes and len(raw) == content["byte_count"]
        and hashlib.sha256(raw).hexdigest() == content["sha256"], "bvbrc_influenza_ha_bytes_conflict")
    _require(type(representation) is str and representation in REPRESENTATIONS
        and type(capture_complete) is bool and type(expected_task_id) is str and bool(expected_task_id),
        "bvbrc_influenza_ha_request_invalid")
    if representation == "sequence_annotation_tsv":
        native, issues = _table(raw, content)
    else:
        parsed = parse_aligned_fasta(raw, artifact=_artifact(content),
            id_rule="first_whitespace_token", encoding="utf-8")
        native = parsed["value"]
        issues = [_issue(row["code"], "/native_document" + row["path"], severity=row["severity"])
            for row in parsed["diagnostics"]]
        if native is not None and not capture_complete:
            native["completeness"] = "truncated"
    if not capture_complete:
        issues.append(_issue("native_capture_incomplete", "/capture_complete"))
    return validate_influenza_ha_document(dict(version=DOCUMENT_VERSION, representation=representation,
        content=content, capture_complete=capture_complete, expected_task_id=expected_task_id,
        parsing_state="unavailable" if native is None else "available", native_document=native, issues=issues))


def validate_influenza_ha_document(value):
    """Validate retained observations without re-reading or re-parsing native bytes."""
    _finite_json(value)
    _require(type(value) is dict and set(value) == _FIELDS and value["version"] == DOCUMENT_VERSION
        and type(value["representation"]) is str and value["representation"] in REPRESENTATIONS
        and type(value["capture_complete"]) is bool and type(value["expected_task_id"]) is str
        and bool(value["expected_task_id"]) and value["parsing_state"] in {"available", "unavailable"}
        and type(value["issues"]) is list)
    content, native = _content(value["content"]), value["native_document"]
    _require((native is None) == (value["parsing_state"] == "unavailable"))
    for issue in value["issues"]:
        _require(type(issue) is dict and set(issue) == {"code", "path", "severity"}
            and type(issue["code"]) is str and bool(issue["code"])
            and type(issue["path"]) is str and issue["path"].startswith("/")
            and type(issue["severity"]) is str and issue["severity"] in {"qualification", "error"})
    _require((_issue("native_capture_incomplete", "/capture_complete") in value["issues"])
        is (not value["capture_complete"]))
    if native is None:
        _require(any(issue["severity"] == "error" for issue in value["issues"]))
    elif value["representation"] == "result_alignment_fasta":
        validate_alignment_document(native)
        _require(native["artifact"] == _artifact(content) and native["encoding"] == "utf-8"
            and (value["capture_complete"] or native["completeness"] == "truncated"))
    else:
        _require(type(native) is dict and set(native) == {"header", "rows", "raw_text", "completeness"}
            and (native["header"] is None or type(native["header"]) is list
                and all(type(cell) is str for cell in native["header"]))
            and type(native["rows"]) is list and type(native["raw_text"]) is str
            and native["completeness"] in {"complete", "partial"})
        encoded = native["raw_text"].encode("utf-8")
        _require(len(encoded) == content["byte_count"] and hashlib.sha256(encoded).hexdigest() == content["sha256"])
        _require((native["completeness"] == "partial") is any(issue["severity"] == "error" for issue in value["issues"]))
        if native["completeness"] == "complete":
            _require(native["header"] == list(HEADER))
        previous = 0
        for ordinal, row in enumerate(native["rows"]):
            _require(type(row) is dict and set(row) == {"row_index", "cells", "source_location"}
                and type(row["row_index"]) is int and row["row_index"] == ordinal
                and type(row["cells"]) is list and all(type(cell) is str for cell in row["cells"]))
            _location(row["source_location"], artifact=_artifact(content))
            start, end = (row["source_location"][key] for key in ("byte_start_0based", "byte_end_0based_exclusive"))
            _require(type(start) is int and type(end) is int and previous <= start <= end <= content["byte_count"])
            previous = end
            _require(native["completeness"] != "complete" or len(row["cells"]) == len(HEADER))
    if native is not None and value["representation"] == "result_alignment_fasta":
        for row in native["rows"]:
            location = row["source_location"]
            _require(type(location["byte_start_0based"]) is int and type(location["byte_end_0based_exclusive"]) is int
                and 0 <= location["byte_start_0based"] <= location["byte_end_0based_exclusive"] <= content["byte_count"])
    return deepcopy(value)


def _score(token, unit, ordinal, field):
    state, value = "invalid", None
    if token == "N/A":
        state = "native_missing"
    elif _NUMBER.fullmatch(token):
        try:
            exact = Decimal(token)
            observed = float(exact)
            if math.isfinite(observed) and not (observed == 0 and exact != 0):
                state, value = "available", observed
            else:
                state = "not_represented_as_finite_binary64"
        except (InvalidOperation, ValueError, OverflowError):
            pass
    return dict(raw_token=token, value=value, state=state, unit=unit, origin="native_reported",
        row_index=ordinal, field=field, population="producer_selected_best_hsp_only",
        uncertainty=None, denominator=None)


def annotation_rows(document):
    """Return usable literal records in occurrence order; never collapse IDs."""
    native = document["native_document"]
    if document["representation"] != "sequence_annotation_tsv" or native is None or native["header"] != list(HEADER):
        return []
    return [dict(row_index=row["row_index"], fields=dict(zip(HEADER, row["cells"], strict=True)),
        source_location=deepcopy(row["source_location"])) for row in native["rows"] if len(row["cells"]) == len(HEADER)]


def calculate_influenza_ha_components(document, *, alignment_selection):
    """Use shared alignment arithmetic once; retain selected native HSP tokens."""
    document = validate_influenza_ha_document(document)
    native, representation = document["native_document"], document["representation"]
    issues, rows = deepcopy(document["issues"]), annotation_rows(document)
    result = dict(version=COMPONENTS_VERSION, document_sha256=hashlib.sha256(_canonical(document)).hexdigest(),
        representation=representation, status="partial" if issues else "complete", native_scores=[],
        alignment_selection=deepcopy(alignment_selection), alignment_population=None,
        alignment_components=None, ungapped_coordinates=None, query_reference_correspondence=None,
        definitions=dict(score_population="Producer-selected HSP with minimum E-value strictly below 0.1; TSV is not all BLAST hits.",
            score_values="Native lexical tokens retained, including N/A and binary64 underflow; E-value is not a subtype correctness probability.",
            coordinate_authority="phylogeny_calculators.ungapped_coordinate_map",
            alignment_authority="phylogeny_calculators.alignment_components",
            coordinates="Zero-based alignment columns and zero-based staged nongap offsets; dash has null residue offset. No biological HA numbering or reference-release identity is inferred.",
            reference_identity="Caller-selected row occurrences in this retained output; header labels alone do not establish the external Burke reference release."), issues=issues)
    for row in rows:
        fields, ordinal = row["fields"], row["row_index"]
        scores = dict(row_index=ordinal, query_id=fields["QueryId"],
            original_sequence_name=fields["Sequence Name"],
            bitscore=_score(fields["Bitscore"], "bits", ordinal, "Bitscore"),
            evalue=_score(fields["E-value"], "expected_random_hits", ordinal, "E-value"))
        result["native_scores"].append(scores)
        for name in ("bitscore", "evalue"):
            if scores[name]["state"] in {"invalid", "not_represented_as_finite_binary64"}:
                result["issues"].append(_issue("ha_native_score_" + scores[name]["state"],
                    "/native_scores/" + str(len(result["native_scores"]) - 1) + "/" + name, severity="error"))
                result["status"] = "partial"
    if representation != "result_alignment_fasta" or native is None:
        return result
    _require(type(alignment_selection) is dict, "bvbrc_influenza_ha_alignment_selection_required")
    query, references = alignment_selection["query_row_index"], alignment_selection["reference_row_indices"]
    if any(index >= len(native["rows"]) for index in [query, *references]):
        result["issues"].append(_issue("ha_selected_alignment_row_missing", "/alignment_selection", severity="error"))
        result["status"] = "partial"
        return result
    population = dict(population_id=native["alignment_id"] + "/retained_artifact",
        alignment_id=native["alignment_id"], row_indices=list(range(len(native["rows"]))),
        columns_0based=list(range(native["observed_column_count"] if native["observed_column_count"] is not None
            else max((len(row["sequence"]) for row in native["rows"]), default=0))),
        completeness=native["completeness"], evidence=[dict(content=deepcopy(document["content"]), pointer="")])
    result["alignment_population"] = population
    result["alignment_components"] = alignment_components(native, population=population, alphabet="protein",
        case_policy=alignment_selection["case_policy"], pairs=tuple((query, reference) for reference in references))
    maps = list(ungapped_coordinate_map(native, row_indices=tuple(population["row_indices"])))
    result["ungapped_coordinates"] = maps
    offsets = {(row["row_index"], row["column_0based"]): row["ungapped_position_0based"] for row in maps}
    correspondences = []
    for reference in references:
        for column in population["columns_0based"]:
            query_symbol = native["rows"][query]["sequence"][column:column + 1] or None
            reference_symbol = native["rows"][reference]["sequence"][column:column + 1] or None
            correspondences.append(dict(query_row_index=query, reference_row_index=reference,
                column_0based=column, query_symbol=query_symbol, reference_symbol=reference_symbol,
                query_ungapped_position_0based=offsets.get((query, column)),
                reference_ungapped_position_0based=offsets.get((reference, column)),
                state="unobserved" if query_symbol is None or reference_symbol is None else "observed"))
    result["query_reference_correspondence"] = correspondences
    if native["completeness"] != "complete":
        result["status"] = "partial"
    return result


__all__ = ["DOCUMENT_VERSION", "COMPONENTS_VERSION", "REPRESENTATIONS", "HEADER",
    "parse_influenza_ha_artifact", "validate_influenza_ha_document", "annotation_rows",
    "calculate_influenza_ha_components"]
