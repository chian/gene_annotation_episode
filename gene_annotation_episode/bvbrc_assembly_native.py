"""Selected assembly artifacts, with one shared retained-FASTA calculation.

The AppService host owns task and File custody. This pure reader checks supplied
bytes against their ContentBinding; a matching descriptor grants no custody.
Each document is its own population. Combined FASTA files, individual segments
and native aliases are never silently added together or deduplicated by label.
Native report tokens remain separate from calculations on retained sequences.
"""
from copy import deepcopy
import hashlib
import re

from .bvbrc_annotation_native import (
    _canonical, _content, _field, _finite_json, _integer, _validate_native,
)
from .phylogeny_format_contracts import _location
from .phylogeny_formats import read_fasta_records
from .sequence_composition_grader import (
    build_sequence_composition_sheet, calculate_sequence_composition_scores,
)
from .ucsc_acquisition import MAX_SAFE_INTEGER, _analyse, _from_document, _parse


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


def parse_assembly_artifact(raw, *, content, representation, capture_complete, expected_task_id):
    """Extract the selected native representation, never an inferred genome."""
    content = _content(content)
    _require(type(raw) is bytes and len(raw) == content["byte_count"]
        and hashlib.sha256(raw).hexdigest() == content["sha256"], "bvbrc_assembly_bytes_conflict")
    _require(type(representation) is str and representation in REPRESENTATIONS
        and type(capture_complete) is bool and type(expected_task_id) is str and bool(expected_task_id),
        "bvbrc_assembly_request_invalid")
    document, issues = None, []
    if representation == "assembly_fasta":
        parsed = read_fasta_records(raw, artifact=_artifact(content),
            id_rule="first_whitespace_token", encoding="utf-8")
        document = parsed["value"]
        issues = [_issue(row["code"], "/native_document" + row["path"], row["severity"])
            for row in parsed["diagnostics"]]
    elif representation == "native_text":
        try:
            document = dict(kind="string", value=raw.decode("utf-8"))
            document["value"].encode("utf-8")
        except UnicodeError:
            document = None
            issues.append(_issue("invalid_native_utf8", "/native_document", "error"))
    else:
        node, _, error, _, _, _ = _parse(raw)
        if error is None:
            _, document, lexical, _ = _analyse(node)
            issues = [_issue(row["code"], row["pointer"]) for row in lexical]
            try:
                _validate_native(document)
            except (ValueError, RecursionError, UnicodeError):
                document, error = None, "native_document_depth_or_shape_invalid"
        if error is not None:
            issues.append(_issue(error, "/native_document", "error"))
        elif document["kind"] != "object":
            issues.append(_issue("native_assembly_details_object_required", "/native_document", "error"))
    if not capture_complete:
        issues.append(_issue("native_capture_incomplete", "/capture_complete"))
    result = dict(version=DOCUMENT_VERSION, representation=representation, content=content,
        capture_complete=capture_complete, expected_task_id=expected_task_id,
        parsing_state="unavailable" if document is None else "available", native_document=document, issues=issues)
    return validate_assembly_document(result)


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


def _reported_fields(document):
    native, representation = document["native_document"], document["representation"]
    if native is None or native.get("kind") != "object":
        return []
    if representation == "sars2_assembly_details":
        paths = [(["total_ns"], "nt"), (["n_blocks"], "runs")]
    elif representation == "genome_assembly_details":
        paths = [(["contig_filtering", key], unit) for key, unit in (
            ("total contigs", "contigs"), ("num contigs above thresholds", "contigs"),
            ("num contigs below thresholds", "contigs"), ("total length of good contigs", "nt"))]
    else:
        return []
    rows = []
    for path, unit in paths:
        node, selected = native, None
        pointer = "/native_document"
        for depth, member in enumerate(path):
            selected = _field(node, member, pointer)
            if depth != len(path) - 1:
                if selected["state"] != "present" or selected["value"]["kind"] != "object":
                    selected = dict(state="parent_" + (selected["state"] if selected["state"] != "present" else "incompatible"),
                        path=selected["path"], value=None)
                    break
            node, pointer = selected["value"], selected["path"]
        integer = _integer(selected["value"]) if selected["state"] == "present" else None
        if integer is not None and integer > MAX_SAFE_INTEGER:
            integer = None
        rows.append(dict(members=path, state=selected["state"], source_pointer=selected["path"],
            native_value=deepcopy(selected["value"]),
            integer_value=integer, integer_state=("available" if integer is not None else
                "not_represented_as_safe_integer" if selected["state"] == "present" else selected["state"]),
            unit=unit, population="native_reported_population_not_replaced_by_retained_sequence_counts"))
    return rows


def calculate_assembly_components(document):
    """One numerical authority for the three assembly services' FASTA values.

    Counts/composition delegate to the existing sequence authority. Contiguity
    uses the complete retained document's lengths, with exact integer crossing
    of half the bases. Missing/invalid/truncated populations have no N50. Runs
    of N/n are counted within each original record, never across record joins.
    """
    document = validate_assembly_document(document)
    native = document["native_document"]
    records = None if document["representation"] != "assembly_fasta" or native is None else []
    complete = bool(records is not None and document["capture_complete"] and native["completeness"] == "complete")
    for row in native["rows"] if records is not None else []:
        sheet = build_sequence_composition_sheet(row["sequence"], molecule="dna")
        components = calculate_sequence_composition_scores(sheet, quality_thresholds=())
        complete = complete and sheet["status"] == "complete"
        spans = [[match.start(), match.end()] for match in re.finditer(r"[Nn]+", row["sequence"])]
        records.append(dict(record_ordinal=row["row_index"], member_label=row["member_label"],
            composition=dict(sheet=sheet, components=components), n_run_intervals_0based=spans,
            n_run_count=len(spans)))
    lengths = None if records is None else [row["composition"]["components"]["length"] for row in records]
    retained_total = None if lengths is None else sum(lengths)
    n50 = l50 = crossing = None
    if complete and retained_total:
        cumulative = 0
        for rank, ordinal in enumerate(sorted(range(len(lengths)), key=lambda index: (-lengths[index], index)), 1):
            cumulative += lengths[ordinal]
            if 2 * cumulative >= retained_total:
                n50, l50, crossing = lengths[ordinal], rank, ordinal
                break
    return dict(version=COMPONENTS_VERSION, document_sha256=hashlib.sha256(_canonical(document)).hexdigest(),
        representation=document["representation"], status="partial" if document["issues"] or records is not None and not complete else "complete",
        population=dict(scope="one_selected_retained_artifact", complete_artifact_population=complete if records is not None else None,
            observed_record_count=None if records is None else len(records), intended_genome_completeness=None),
        records=records, retained_symbol_total=retained_total,
        total_length_nt=retained_total if complete else None, n50_nt=n50, l50=l50,
        n50_crossing_record_ordinal=crossing,
        n_count=sum(row["composition"]["components"]["symbol_counts"].get("N", 0) for row in records) if complete else None,
        n_block_count=sum(row["n_run_count"] for row in records) if complete else None,
        native_reported_fields=_reported_fields(document),
        definitions=dict(composition_authority="sequence_composition_grader",
            contiguity_authority="bvbrc_assembly_native.calculate_assembly_components",
            n50="Descending retained lengths; first length whose cumulative bases satisfy 2*cumulative >= total; null for unresolved or zero-base populations.",
            n_runs="Maximal nonempty N/n spans within each original sequence occurrence, zero-based half-open.",
            population="No summation across combined, per-segment or alias files; no genome completeness, sequence accuracy or annotation-confidence inference."),
        issues=deepcopy(document["issues"]))


__all__ = ["DOCUMENT_VERSION", "COMPONENTS_VERSION", "REPRESENTATIONS", "parse_assembly_artifact",
    "validate_assembly_document", "calculate_assembly_components"]
