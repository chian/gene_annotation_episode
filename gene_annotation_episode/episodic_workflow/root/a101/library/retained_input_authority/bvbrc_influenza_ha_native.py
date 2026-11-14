"""Literal observations from the retained HA conversion producer's artifacts.

The native TSV reports the selected HSP, not every hit. Its query names and
original sequence headers remain separate. Aligned FASTA uses the existing
alignment reader and numerical authority; offsets are staged residue offsets,
not a claim of biological HA numbering or a particular reference release.
"""

from __future__ import annotations

from copy import deepcopy

import hashlib

from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_annotation_native import _content, _finite_json, _issue

from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.phylogeny_format_contracts import _location, validate_alignment_document

DOCUMENT_VERSION = "bvbrc_influenza_ha_native_document_v1"

COMPONENTS_VERSION = "bvbrc_influenza_ha_components_v1"

REPRESENTATIONS = ("sequence_annotation_tsv", "result_alignment_fasta")

HEADER = ("QueryId", "Virus Type", "Segment", "Subtype", "Bitscore", "E-value",
    "Warning Messages", "Sequence Name")

_FIELDS = {"version", "representation", "content", "capture_complete", "expected_task_id",
    "parsing_state", "native_document", "issues"}

def _require(condition, code="bvbrc_influenza_ha_document_invalid"):
    if not condition:
        raise ValueError(code)

def _artifact(content):
    return dict(raw_artifact_ref=content["artifact_ref"], source_ref=content["source_ref"], sha256=content["sha256"])

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

def annotation_rows(document):
    """Return usable literal records in occurrence order; never collapse IDs."""
    native = document["native_document"]
    if document["representation"] != "sequence_annotation_tsv" or native is None or native["header"] != list(HEADER):
        return []
    return [dict(row_index=row["row_index"], fields=dict(zip(HEADER, row["cells"], strict=True)),
        source_location=deepcopy(row["source_location"])) for row in native["rows"] if len(row["cells"]) == len(HEADER)]
