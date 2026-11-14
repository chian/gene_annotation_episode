"""Selected assembly artifacts, with one shared retained-FASTA calculation.

The AppService host owns task and File custody. This pure reader checks supplied
bytes against their ContentBinding; a matching descriptor grants no custody.
Each document is its own population. Combined FASTA files, individual segments
and native aliases are never silently added together or deduplicated by label.
Native report tokens remain separate from calculations on retained sequences.
"""

from copy import deepcopy

import hashlib

from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_annotation_native import _canonical, _content, _finite_json, _validate_native

from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.phylogeny_format_contracts import _location

from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.ucsc_acquisition import _analyse, _from_document

DOCUMENT_VERSION = "bvbrc_assembly_native_document_v1"

COMPONENTS_VERSION = "bvbrc_assembly_components_v1"

REPRESENTATIONS = ("assembly_fasta", "genome_assembly_details", "sars2_assembly_details", "native_text")

_FIELDS = {"version", "representation", "content", "capture_complete", "expected_task_id",
    "parsing_state", "native_document", "issues"}

def _require(condition, code="bvbrc_assembly_document_invalid"):
    if not condition:
        raise ValueError(code)

def _issue(code, path, severity="qualification"):
    return dict(code=code, path=path, severity=severity)

def _artifact(content):
    return dict(raw_artifact_ref=content["artifact_ref"], source_ref=content["source_ref"], sha256=content["sha256"])

def _validate_fasta(value, content):
    _require(type(value) is dict and set(value) == {"version", "artifact", "encoding", "id_rule",
        "observed_record_count", "completeness", "rows"})
    _require(value["version"] == "native_fasta_record_observations_v1"
        and value["artifact"] == _artifact(content) and value["encoding"] == "utf-8"
        and value["id_rule"] == "first_whitespace_token"
        and type(value["observed_record_count"]) is int and type(value["rows"]) is list
        and value["observed_record_count"] == len(value["rows"])
        and type(value["completeness"]) is str and value["completeness"] in {"complete", "partial"})
    if value["completeness"] == "complete":
        _require(bool(value["rows"]))
    for ordinal, row in enumerate(value["rows"]):
        _require(type(row) is dict and set(row) == {
            "row_index", "raw_header", "member_label", "sequence", "source_location"}
            and type(row["row_index"]) is int and row["row_index"] == ordinal
            and all(type(row[key]) is str for key in ("raw_header", "member_label", "sequence")))
        tokens = row["raw_header"].split()
        _require(row["member_label"] == (tokens[0] if tokens else ""))
        _location(row["source_location"], artifact=value["artifact"])
        _require(0 <= row["source_location"]["byte_start_0based"]
            <= row["source_location"]["byte_end_0based_exclusive"] <= content["byte_count"])

def validate_assembly_document(value):
    """Check saved observations and their bindings without parsing native bytes."""
    try:
        _finite_json(value)
        _require(type(value) is dict and set(value) == _FIELDS and value["version"] == DOCUMENT_VERSION
            and type(value["representation"]) is str and value["representation"] in REPRESENTATIONS
            and type(value["capture_complete"]) is bool
            and type(value["expected_task_id"]) is str and bool(value["expected_task_id"])
            and type(value["parsing_state"]) is str and value["parsing_state"] in {"available", "unavailable"}
            and type(value["issues"]) is list)
        content = _content(value["content"])
        document = value["native_document"]
        _require((document is None) == (value["parsing_state"] == "unavailable"))
        for issue in value["issues"]:
            _require(type(issue) is dict and set(issue) == {"code", "path", "severity"}
                and type(issue["code"]) is str and bool(issue["code"])
                and type(issue["path"]) is str and issue["path"].startswith("/")
                and type(issue["severity"]) is str and issue["severity"] in {"qualification", "error"})
        _require((_issue("native_capture_incomplete", "/capture_complete") in value["issues"])
            is (not value["capture_complete"]))
        if document is not None and value["representation"] == "assembly_fasta":
            _validate_fasta(document, content)
            _require((document["completeness"] == "partial")
                is any(issue["severity"] == "error" for issue in value["issues"]))
        elif document is not None:
            _validate_native(document)
            if value["representation"] == "native_text":
                _require(document["kind"] == "string"
                    and hashlib.sha256(document["value"].encode("utf-8")).hexdigest() == content["sha256"]
                    and len(document["value"].encode("utf-8")) == content["byte_count"])
            else:
                _, canonical, lexical, _ = _analyse(_from_document(document))
                _require(_canonical(canonical) == _canonical(document))
                expected = [_issue(row["code"], row["pointer"]) for row in lexical]
                if document["kind"] != "object":
                    expected.append(_issue("native_assembly_details_object_required", "/native_document", "error"))
                if not value["capture_complete"]:
                    expected.append(_issue("native_capture_incomplete", "/capture_complete"))
                _require(_canonical(expected) == _canonical(value["issues"]))
        elif not any(issue["severity"] == "error" and issue["code"] in {
                "invalid_native_utf8", "invalid_native_json", "invalid_native_unicode",
                "native_document_depth_or_shape_invalid", "phylogeny_encoding_invalid",
                "phylogeny_artifact_invalid", "phylogeny_artifact_sha256_mismatch", "phylogeny_bytes_required"}
                for issue in value["issues"]):
            _require(False)
    except (RecursionError, UnicodeError, TypeError, KeyError) as error:
        raise ValueError("bvbrc_assembly_document_invalid") from error
    return deepcopy(value)
