"""Store-free parsing and saved calculation of captured MUSCLE alignment data.

The host authenticates the selected input, original native handle and capture
Source. This worker verifies supplied file pins, retains the unchanged neutral
documents and delegates all scientific calculation to the existing authority.
It publishes no Source, grants no reference and never starts native software.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator, validators

from . import native_flux_balance_storage as storage
from . import protein_conservation_result_contracts as contracts
from .native_file_capture import _identity
from .phylogeny_formats import parse_aligned_fasta
from .phylogeny_format_contracts import validate_alignment_document
from .phylogeny_calculators import literal_site_conservation
from .phylogeny_calculation_contracts import validate_literal_site_conservation_components


REQUEST_VERSION = "protein_conservation_result_request_v1"
OUTPUT_VERSION = "protein_conservation_result_output_v1"
CONTEXT_VERSION = "protein_conservation_result_context_v1"
ALIGNMENT_FORMAT = "phylogeny_alignment_document_v1"
POPULATION_FORMAT = "phylogeny_alignment_population_v1"
COMPONENTS_FORMAT = "literal_site_conservation_v1"
_FILES = {"alignment": ("alignment.json", ALIGNMENT_FORMAT),
    "population": ("population.json", POPULATION_FORMAT),
    "components": ("components.json", COMPONENTS_FORMAT),
    "context": ("context.json", CONTEXT_VERSION),
    "value": ("value.json", contracts.PACKET_VERSION)}
_SOURCE = r"^source_[0-9a-f]{24,64}$"
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _checker, value: type(value) is int)
    .redefine("number", lambda _checker, value: type(value) is int or
        type(value) is float and math.isfinite(value))
    .redefine("array", lambda _checker, value: type(value) is list)
    .redefine("object", lambda _checker, value: type(value) is dict))


def _require(condition, code):
    if not condition:
        raise ValueError("protein_conservation_result_" + code)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def _nullable(schema):
    return {"anyOf": [{"type": "null"}, schema]}


def _schema_parts():
    definitions = contracts.conservation_result_schema()["$defs"]
    integer = {"type": "integer", "minimum": 0}
    path = {"type": "string", "minLength": 1}
    file = _object({"artifact_ref": {"type": "string", "pattern": "^artifact_[0-9a-f]{64}$"},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "size_bytes": integer, "format": {"type": "string", "minLength": 1}})
    saved_file = _object({"path": path, "file": file})
    source = {"type": "string", "pattern": _SOURCE}
    input_file = _object({"path": path, "file": file, "source_ref": _nullable(source)})
    capture = _object({"state": {"enum": ["complete", "truncated"]},
        "byte_start_0based": {"const": 0}, "byte_end_0based_exclusive": integer,
        "original_size_bytes": _nullable(integer)})
    aligned_file = _object({"path": path, "file": file, "source_ref": source,
        "capture": capture})
    saved = _object({"alignment": _nullable(saved_file), "context": saved_file})
    properties = {"version": {"const": REQUEST_VERSION},
        "mode": {"enum": ["parse", "calculate_saved"]}, "input": _nullable(input_file),
        "alignment_file": _nullable(aligned_file),
        "native_execution": _nullable({"$ref": "#/$defs/NativeExecution"}),
        "native_issues": _nullable(deepcopy(definitions["Context"]["properties"]["issues"])),
        "saved": _nullable(saved), "population_request": {"$ref": "#/$defs/PopulationRequest"},
        "selection": {"$ref": "#/$defs/Selection"}}
    return definitions, properties


def protein_conservation_result_request_schema():
    definitions, properties = _schema_parts()
    schema = _object(properties)
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": definitions})
    schema["oneOf"] = [
        {"properties": {"mode": {"const": "parse"}, "input": {"type": "object"},
            "native_execution": {"type": "object"}, "native_issues": {"type": "array"},
            "saved": {"type": "null"}}},
        {"properties": {"mode": {"const": "calculate_saved"}, "input": {"type": "null"},
            "alignment_file": {"type": "null"}, "native_execution": {"type": "null"},
            "native_issues": {"type": "null"}, "saved": {"type": "object"}}}]
    return schema


def protein_conservation_result_output_schema():
    declaration = _object({"relative_path": {"type": "string", "minLength": 1},
        "format": {"type": "string", "minLength": 1},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "size_bytes": {"type": "integer", "minimum": 0}})
    properties = {"version": {"const": OUTPUT_VERSION}, "mode": {"enum": ["parse", "calculate_saved"]}}
    for key, (name, format) in _FILES.items():
        item = deepcopy(declaration)
        item["properties"]["relative_path"] = {"const": name}
        item["properties"]["format"] = {"const": format}
        properties[key] = _nullable(item) if key in {"alignment", "population", "components"} else item
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **_object(properties),
        "allOf": [{"if": {"properties": {"mode": {"const": "calculate_saved"}}},
            "then": {"properties": {"alignment": {"type": "null"}}}},
            {"if": {"properties": {"components": {"type": "object"}}},
                "then": {"properties": {"population": {"type": "object"}}}}]}


def _validate(value, schema, code):
    try:
        valid = _STRICT(schema).is_valid(value)
    except (TypeError, ValueError, RecursionError):
        valid = False
    _require(valid, code)
    return deepcopy(value)


def _file(value, format):
    _require(type(value) is dict and set(value) == {"path", "file"}, "file_descriptor_invalid")
    identity = _identity(value["file"])
    path = value["path"]
    _require(type(path) is str and Path(path).is_absolute() and str(Path(path)) == path
        and ".." not in Path(path).parts and "\0" not in path, "file_path_invalid")
    _require(identity["format"] == format, "file_format_conflict")
    return identity


def _capture(value, size):
    original = value["original_size_bytes"]
    _require(type(value["byte_start_0based"]) is int and value["byte_start_0based"] == 0
        and value["byte_end_0based_exclusive"] == size
        and (original is None or original >= size), "capture_extent_conflict")
    _require(value["state"] != "complete" or original is None or original == size,
        "capture_extent_conflict")
    return {"state": value["state"], "retained_size_bytes": size, "original_size_bytes": original}


def validate_protein_conservation_result_request(value):
    value = _validate(value, protein_conservation_result_request_schema(), "request_invalid")
    if value["mode"] == "parse":
        selected = value["input"]
        _file({key: selected[key] for key in ("path", "file")}, "fasta")
        native = value["native_execution"]
        _require(native["parser_status"] == "not_parsed", "parser_state_conflict")
        if native["state"] == "completed":
            _require(type(native["returncode"]) is int and native["returncode"] == 0,
                "native_state_conflict")
        elif native["state"] == "failed":
            _require(native["returncode"] is None or native["returncode"] != 0, "native_state_conflict")
        elif native["state"] == "not_attempted":
            _require(native["returncode"] is None, "native_state_conflict")
        _require((native["alphabet"]["value"] is not None) == (native["alphabet"]["state"] == "reported"),
            "native_alphabet_conflict")
        captured = value["alignment_file"]
        if captured is None:
            _require(native["output_capture"]["retained_size_bytes"] is None
                and native["output_capture"]["state"] in ("missing", "unknown"), "output_capture_conflict")
        else:
            identity = _file({key: captured[key] for key in ("path", "file")}, "aligned_fasta")
            _require(native["output_capture"] == _capture(captured["capture"], identity["size_bytes"]),
                "output_capture_conflict")
    else:
        _file(value["saved"]["context"], CONTEXT_VERSION)
        if value["saved"]["alignment"] is not None:
            _file(value["saved"]["alignment"], ALIGNMENT_FORMAT)
    return value


def _read(descriptor):
    try:
        raw = storage.read_bytes(descriptor["path"])
    except OSError as error:
        raise ValueError("protein_conservation_result_file_unavailable") from error
    identity = descriptor["file"]
    _require(len(raw) == identity["size_bytes"]
        and hashlib.sha256(raw).hexdigest() == identity["sha256"], "file_identity_conflict")
    return raw


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("utf-8") + b"\n"


def _issue(code, path, *, phase="input_headers", severity="qualification", evidence=()):
    return {"code": code, "phase": phase, "path": path, "severity": severity,
        "evidence_refs": list(evidence)}


def _input_record(descriptor, raw):
    """Inventory original header occurrences only, without sequence decoding."""
    records, issues, current = [], [], None
    for match in re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", raw):
        if match.start() == len(raw):
            break
        line = match.group().rstrip(b"\r\n")
        if line.startswith(b">"):
            if current is not None:
                current["byte_end"] = match.start()
            codes = []
            try:
                header = line[1:].decode("utf-8")
            except UnicodeError:
                header = ""
                codes.append("input_header_encoding_invalid")
            if not header.split() and not codes:
                codes.append("input_header_missing")
            current = {"record_ordinal": len(records), "byte_start": match.start(),
                "byte_end": len(raw), "header": header,
                "status": "incompatible" if codes else "available", "issues": codes}
            records.append(current)
        elif current is None and line.strip() and "input_fasta_header_missing" not in issues:
            issues.append("input_fasta_header_missing")
    if not records:
        issues.append("input_headers_unavailable")
    source = descriptor["source_ref"]
    return {"selection": {"namespace": "artifact" if source is None else "source",
            "reference": descriptor["file"]["artifact_ref"] if source is None else source, "format": "fasta"},
        "file": deepcopy(descriptor["file"]), "source_ref": source,
        "capture": {"state": "complete", "retained_size_bytes": len(raw), "original_size_bytes": len(raw)},
        "records_state": "unavailable" if not records else "partial" if issues or
            any(row["status"] != "available" for row in records) else "available",
        "records": records, "issues": issues}


def _associations(input_record, alignment):
    rows = [] if alignment is None else alignment["rows"]
    complete = input_record["records_state"] == "available"
    available = alignment is not None and (complete or
        any(row["status"] == "available" for row in input_record["records"]))
    by_label, output_counts = {}, {}
    for record in input_record["records"]:
        if record["status"] == "available":
            by_label.setdefault(record["header"], []).append(record["record_ordinal"])
    for row in rows:
        output_counts[row["raw_header"]] = output_counts.get(row["raw_header"], 0) + 1
    associations, seen = [], set()
    for row in rows:
        candidates = by_label.get(row["raw_header"], []) if available else []
        state = ("unavailable_input_records" if not available or not candidates and not complete
            else "unmatched_output_label" if not candidates
            else "ambiguous_label_match" if not complete or len(candidates) > 1 or output_counts[row["raw_header"]] > 1
            else "unique_label_match")
        associations.append({"output_row_index": row["row_index"],
            "input_record_ordinals": deepcopy(candidates), "state": state})
        seen.update(candidates)
    return {"state": "unavailable" if not available else input_record["records_state"],
        "rows": associations, "unmatched_input_record_ordinals": None if not available or not complete else
            [row["record_ordinal"] for row in input_record["records"] if row["record_ordinal"] not in seen]}


def _metadata(alignment):
    return None if alignment is None else {key: deepcopy(value) for key, value in alignment.items() if key != "rows"}


def _context_schema():
    public = contracts.conservation_result_schema()
    context = public["$defs"]["Context"]["properties"]
    fields = {key: deepcopy(context[key]) for key in
        ("input", "native_execution", "alignment", "row_associations", "issues")}
    return {"$defs": public["$defs"], **_object({"version": {"const": CONTEXT_VERSION}, **fields})}


def _saved_context(saved):
    context = _validate(storage.decode_json(_read(saved["context"])), _context_schema(), "saved_context_invalid")
    original = saved["alignment"]
    _require((original is None) == (context["alignment"] is None), "saved_alignment_presence_conflict")
    alignment = None if original is None else validate_alignment_document(storage.decode_json(_read(original)))
    _require(_json_bytes(_metadata(alignment)) == _json_bytes(context["alignment"]),
        "saved_alignment_metadata_conflict")
    if alignment is not None:
        artifact = alignment["artifact"]
        _require(re.fullmatch(_SOURCE, artifact["source_ref"]) is not None
            and artifact["raw_artifact_ref"] == "artifact_" + artifact["sha256"],
            "saved_capture_identity_conflict")
    return context, alignment


def _parse(request):
    input_raw = _read(request["input"])
    captured = request["alignment_file"]
    raw = None if captured is None else _read(captured)
    input_record = _input_record(request["input"], input_raw)
    native = deepcopy(request["native_execution"])
    issues = deepcopy(request["native_issues"])
    issues.extend(_issue(code, "/input", evidence=[input_record["file"]["artifact_ref"]])
        for code in input_record["issues"])
    for row in input_record["records"]:
        issues.extend(_issue(code, "/input/records/" + str(row["record_ordinal"]),
            evidence=[input_record["file"]["artifact_ref"]]) for code in row["issues"])
    if captured is None:
        alignment = None
        native["parser_status"] = "not_parsed"
        issues.append(_issue("protein_conservation_native_output_missing", "/alignment",
            phase="native_capture", severity="error"))
    else:
        parsed = parse_aligned_fasta(raw, artifact={"raw_artifact_ref": captured["file"]["artifact_ref"],
            "source_ref": captured["source_ref"], "sha256": captured["file"]["sha256"]},
            id_rule="first_whitespace_token", encoding="utf-8")
        alignment = None if parsed["value"] is None else validate_alignment_document(parsed["value"])
        native["parser_status"] = parsed["status"]
        issues.extend(deepcopy(parsed["diagnostics"]))
        if captured["capture"]["state"] == "truncated":
            issues.append(_issue("protein_conservation_output_capture_truncated", "/native_execution/output_capture",
                phase="native_capture", evidence=[captured["file"]["artifact_ref"]]))
    context = {"version": CONTEXT_VERSION, "input": input_record, "native_execution": native,
        "alignment": _metadata(alignment), "row_associations": _associations(input_record, alignment),
        "issues": issues}
    return context, alignment


def _evidence(context):
    """Use the host-authenticated capture Source's actual primary File.

    When aligned bytes exist, captured.source_ref's artifact_ref must equal
    captured.file.artifact_ref. The host authenticates that real field join;
    saved context preserves the same original pair, without a Source alias.
    """
    alignment = context["alignment"]
    if alignment is None:
        return []
    artifact = alignment["artifact"]
    size = context["native_execution"]["output_capture"]["retained_size_bytes"]
    _require(type(size) is int and size >= 0, "saved_capture_extent_conflict")
    return [{"content": {"source_ref": artifact["source_ref"], "artifact_field": "artifact_ref",
        "artifact_ref": artifact["raw_artifact_ref"], "sha256": artifact["sha256"], "byte_count": size},
        "pointer": ""}]


def _retained_extent(context, alignment):
    if alignment is None:
        return
    artifact = alignment["artifact"]
    size = context["native_execution"]["output_capture"]["retained_size_bytes"]
    _require(re.fullmatch(_SOURCE, artifact["source_ref"]) is not None
        and artifact["raw_artifact_ref"] == "artifact_" + artifact["sha256"]
        and type(size) is int and size >= 0, "capture_identity_conflict")
    for row in alignment["rows"]:
        location = row["source_location"]
        start, end = location["byte_start_0based"], location["byte_end_0based_exclusive"]
        _require(type(start) is int and type(end) is int and 0 <= start < end <= size,
            "capture_row_extent_conflict")


def _public(context, alignment, population_request, population, components, selection):
    return contracts.conservation_public_value(alignment=alignment, population_request=population_request,
        population=population, components=components, input_record=context["input"],
        native_execution=context["native_execution"], associations=context["row_associations"],
        selection=selection, issues=context["issues"])


def _write(root, key, value):
    name, format = _FILES[key]
    storage.immutable_bytes(root / name, _json_bytes(value))
    pin = storage.file_pin(root / name)
    return {"relative_path": name, "format": format, "sha256": pin["sha256"], "size_bytes": pin["size_bytes"]}


def run_protein_conservation_result(request, *, output_directory):
    """Retain observed documents before the sole selected calculator call."""
    request = validate_protein_conservation_result_request(request)
    root = storage.directory(Path(output_directory))
    for name, _ in _FILES.values():
        _require(not storage.confined_file(root, name).exists(), "output_already_exists")
    context, alignment = (_parse(request) if request["mode"] == "parse" else _saved_context(request["saved"]))
    context = _validate(context, _context_schema(), "context_invalid")
    _retained_extent(context, alignment)
    result = {"version": OUTPUT_VERSION, "mode": request["mode"], "alignment": None,
        "population": None, "components": None, "context": None, "value": None}
    if request["mode"] == "parse" and alignment is not None:
        result["alignment"] = _write(root, "alignment", alignment)
    result["context"] = _write(root, "context", context)
    bound = contracts.bind_conservation_population(request["population_request"], alignment=alignment,
        evidence=_evidence(context))
    population = bound["population"]
    if population is not None:
        result["population"] = _write(root, "population", population)
    # Validate the actual complete native/header relationships before math.
    # This source-free view has explicitly unavailable calculated components.
    _public(context, alignment, request["population_request"], population, None, request["selection"])
    selected_sites = request["selection"]["sites"]["columns_0based"]
    if population is not None and selected_sites is not None:
        _require(all(column in population["columns_0based"] for column in selected_sites),
            "selection_outside_retained_sites")
    components = None
    if alignment is not None and population is not None:
        components = literal_site_conservation(alignment, population=population)
        components = validate_literal_site_conservation_components(components, alignment=alignment, population=population)
        result["components"] = _write(root, "components", components)
    value = _public(context, alignment, request["population_request"], population, components, request["selection"])
    result["value"] = _write(root, "value", value)
    return _validate(result, protein_conservation_result_output_schema(), "output_invalid")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("result")
    args = parser.parse_args(argv)
    payload = storage.read_json(args.request)
    _require(type(payload) is dict and set(payload) == {"operation", "arguments"}
        and payload["operation"] == "protein_conservation_result", "worker_payload_invalid")
    _require(type(payload["arguments"]) is dict and set(payload["arguments"]) == {"request"},
        "worker_arguments_invalid")
    result = Path(args.result)
    _require(result.name not in {name for name, _ in _FILES.values()}, "worker_result_path_conflict")
    _require(not result.exists() and not result.is_symlink(), "worker_result_already_exists")
    try:
        output = run_protein_conservation_result(payload["arguments"]["request"], output_directory=result.parent)
    except ValueError as error:
        storage.immutable_bytes(result, _json_bytes({"code": str(error), "exception_type": "ValueError"}))
        return 2
    storage.immutable_bytes(result, _json_bytes(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
