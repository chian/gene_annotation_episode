"""Closed supplied-input boundaries for the existing MinHash numerical sheet.

These functions validate copied structures and associations only. References,
digests and JSON pointers do not prove source custody, artifact contents or
remote parameter equivalence. The host authenticates those facts. No parser,
calculator, service, store, acquisition or execution is invoked here.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re


_SELECTOR_VERSION = "bvbrc_minhash_result_selector_v2"
_INPUTS_VERSION = "bvbrc_minhash_publication_inputs_v1"
_METADATA_FIELDS = ("kmer_length", "query_length", "reference_length", "alphabet_size")
_OPERANDS = ("query", "max_pvalue", "max_distance", "max_hits", "include_reference",
             "include_representative", "bacterial", "viral")
_SOURCE_PATTERN = r"source_[a-f0-9]{24,64}"
_ARTIFACT_PATTERN = r"artifact_[a-f0-9]{64}"
_GENOME_PATTERN = r"[0-9]+\.[0-9]+"
_POINTER_PATTERN = r"(?:/(?:[^~]|~[01])*)*"


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _metadata_schema():
    evidence = _object({
        "field": {"type": "string", "enum": list(_METADATA_FIELDS)},
        "source_ref": {"type": "string", "pattern": "^" + _SOURCE_PATTERN + r"(?![\s\S])",
                       "format": "reference", "x-reference-namespace": "source"},
        "artifact_ref": {"type": "string", "pattern": "^" + _ARTIFACT_PATTERN + r"(?![\s\S])"},
        "record_path": {"type": "string", "pattern": "^" + _POINTER_PATTERN + r"(?![\s\S])"},
    })
    metadata = _object({
        "row_index": {"type": "integer", "minimum": 0},
        "genome_id": {"type": "string", "pattern": "^" + _GENOME_PATTERN + r"(?![\s\S])"},
        **{name: {"type": ["integer", "null"], "minimum": 1} for name in _METADATA_FIELDS},
        "provenance": _object({
            "kind": {"const": "explicit_retained_pair_inputs"},
            "query_mode": {"type": "string", "enum": ["genome", "fasta"]},
            "query_operand": {"type": "string", "minLength": 1, "pattern": r"\S"},
            "native_parameter_equivalence": {"const": "unestablished"},
            "fields": {"type": "array", "items": evidence},
        }),
    })
    metadata["allOf"] = []
    for name in _METADATA_FIELDS:
        match = {"type": "object", "properties": {"field": {"const": name}},
                 "required": ["field"]}
        metadata["allOf"].append({
            "if": {"properties": {name: {"type": "null"}}},
            "then": {"properties": {"provenance": {"properties": {
                "fields": {"not": {"contains": match}}}}}},
            "else": {"properties": {"provenance": {"properties": {
                "fields": {"contains": match, "minContains": 1, "maxContains": 1}}}}},
        })
    return metadata


def minhash_result_selector_schema() -> dict:
    """Return a detached closed schema for legacy {} or the supplied V2 selector."""
    reference = {"type": "string", "pattern": "^" + _SOURCE_PATTERN + r"(?![\s\S])",
                 "format": "reference", "x-reference-namespace": "execution_result"}
    selected = _object({
        "version": {"const": _SELECTOR_VERSION},
        "mode": {"type": "string", "enum": ["native_result", "saved_sheet"]},
        "saved_result_ref": {"anyOf": [{"type": "null"}, reference]},
        "pair_metadata": {"type": "array", "items": _metadata_schema()},
    })
    selected["allOf"] = [{
        "if": {"properties": {"mode": {"const": "native_result"}}},
        "then": {"properties": {"saved_result_ref": {"type": "null"}}},
        "else": {"properties": {"saved_result_ref": reference}},
    }]
    return deepcopy({"oneOf": [_object({}), selected]})


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _fields(value, names, code):
    _require(type(value) is dict and set(value) == set(names), code)


def _matches(value, pattern):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def _finite_json(value, code):
    active = set()

    def visit(item):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return
        if kind is float:
            _require(math.isfinite(item), code)
            return
        _require(kind in (dict, list) and id(item) not in active, code)
        active.add(id(item))
        try:
            if kind is dict:
                _require(all(type(key) is str for key in item), code)
                for child in item.values():
                    visit(child)
            else:
                for child in item:
                    visit(child)
        finally:
            active.remove(id(item))

    try:
        visit(value)
    except RecursionError as exc:
        raise ValueError(code) from exc


def _same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _pair_metadata(value, code):
    _require(type(value) is list, code)
    for record in value:
        _fields(record, ("row_index", "genome_id", *_METADATA_FIELDS, "provenance"), code)
        _require(type(record["row_index"]) is int and record["row_index"] >= 0, code)
        _require(_matches(record["genome_id"], _GENOME_PATTERN), code)
        for name in _METADATA_FIELDS:
            scalar = record[name]
            _require(scalar is None or type(scalar) is int and scalar > 0, code)
        provenance = record["provenance"]
        _fields(provenance, ("kind", "query_mode", "query_operand",
                            "native_parameter_equivalence", "fields"), code)
        _require(provenance["kind"] == "explicit_retained_pair_inputs", code)
        _require(provenance["query_mode"] in ("genome", "fasta"), code)
        _require(type(provenance["query_operand"]) is str
                 and bool(provenance["query_operand"].strip()), code)
        _require(provenance["native_parameter_equivalence"] == "unestablished", code)
        evidence = provenance["fields"]
        _require(type(evidence) is list, code)
        fields = []
        for item in evidence:
            _fields(item, ("field", "source_ref", "artifact_ref", "record_path"), code)
            _require(item["field"] in _METADATA_FIELDS, code)
            _require(_matches(item["source_ref"], _SOURCE_PATTERN), code)
            _require(_matches(item["artifact_ref"], _ARTIFACT_PATTERN), code)
            _require(_matches(item["record_path"], _POINTER_PATTERN), code)
            fields.append(item["field"])
        _require(len(fields) == len(set(fields)), code)
        _require(set(fields) == {name for name in _METADATA_FIELDS if record[name] is not None}, code)


def _selector(value, code):
    _finite_json(value, code)
    _require(type(value) is dict, code)
    if not value:
        return
    _fields(value, ("version", "mode", "saved_result_ref", "pair_metadata"), code)
    _require(value["version"] == _SELECTOR_VERSION, code)
    _require(value["mode"] in ("native_result", "saved_sheet"), code)
    if value["mode"] == "native_result":
        _require(value["saved_result_ref"] is None, code)
    else:
        _require(_matches(value["saved_result_ref"], _SOURCE_PATTERN), code)
    _pair_metadata(value["pair_metadata"], code)


def validate_minhash_result_selector(value) -> dict:
    """Validate shape only; retain all original list occurrences and raw types."""
    _selector(value, "minhash_result_selector_invalid")
    return deepcopy(value)


def _request_query(request, code):
    # The service remains the authority for native invocation parameters. Here
    # the complete service-request shape distinguishes it from an RPC envelope.
    _finite_json(request, code)
    _fields(request, ("mode", *_OPERANDS), code)
    _require(request["mode"] in ("genome", "fasta"), code)
    _require(type(request["query"]) is str and bool(request["query"].strip()), code)


def _query_associations(records, request):
    for record in records:
        provenance = record["provenance"]
        _require(provenance["query_mode"] == request["mode"]
                 and provenance["query_operand"] == request["query"],
                 "minhash_metadata_query_conflict")


def validate_minhash_pair_metadata(value, *, request) -> list[dict]:
    """Check explicit inputs and query association, without joining native rows."""
    code = "minhash_pair_metadata_invalid"
    _finite_json(value, code)
    _pair_metadata(value, code)
    _request_query(request, code)
    _query_associations(value, request)
    return deepcopy(value)


def _artifact_digest(reference, digest, code):
    _require(_matches(reference, _ARTIFACT_PATTERN)
             and _matches(digest, r"[a-f0-9]{64}")
             and reference == "artifact_" + digest, code)


def _saved_result(value, *, request, source_ref, code):
    _fields(value, ("source_ref", "native_artifact_ref", "native_sha256",
                    "grading_artifact_ref", "grading_sha256", "sheet", "original_components"), code)
    _require(value["source_ref"] == source_ref, code)
    _artifact_digest(value["native_artifact_ref"], value["native_sha256"], code)
    _artifact_digest(value["grading_artifact_ref"], value["grading_sha256"], code)
    sheet, components = value["sheet"], value["original_components"]
    # These are copies of the existing common contracts, not a new sheet. The
    # host authenticates the original publication and its full saved contents.
    _fields(sheet, ("schema", "mode", "request", "provenance", "native_result", "rows", "search_metadata"), code)
    _require(sheet["schema"] == "bvbrc_minhash_sheet_v1"
             and sheet["mode"] == request["mode"], code)
    rpc = sheet["request"]
    _fields(rpc, ("version", "id", "method", "params"), code)
    _require(rpc["version"] == "1.1" and type(rpc["id"]) is str and bool(rpc["id"]), code)
    _require(rpc["method"] == f"Minhash.compute_genome_distance_for_{request['mode']}2"
             and _same(rpc["params"], [request[name] for name in _OPERANDS]), code)
    _require(type(sheet["provenance"]) in (dict, list), code)
    _fields(sheet["search_metadata"], ("population_size", "reference_release", "truncated",
                                       "kmer_length", "hash_seed", "sketch_size"), code)
    _require(all(item is None for item in sheet["search_metadata"].values()), code)
    _fields(components, ("schema", "rows", "diagnostics"), code)
    _require(components["schema"] == "bvbrc_minhash_components_v1", code)
    _require(type(sheet["native_result"]) is list and type(sheet["rows"]) is list
             and type(components["rows"]) is list and type(components["diagnostics"]) is list, code)
    _require(len(sheet["native_result"]) == len(sheet["rows"]) == len(components["rows"]), code)


def validate_minhash_publication_inputs(value, *, request, selector) -> dict:
    """Validate a frozen V2 envelope; custody and byte verification stay in host.

    Legacy {} selection has no publication-input envelope. Each supplied nonnull
    field has exactly one binding keyed by its original metadata-list position.
    Binding order and duplicate pair candidates are preserved, never coalesced.
    """
    code = "minhash_publication_inputs_conflict"
    _finite_json(value, code)
    _selector(selector, code)
    _require(bool(selector), code)
    _request_query(request, code)
    _fields(value, ("version", "selector", "pair_metadata", "metadata_bindings", "saved_result"), code)
    _require(value["version"] == _INPUTS_VERSION and _same(value["selector"], selector), code)
    _pair_metadata(value["pair_metadata"], code)
    _require(_same(value["pair_metadata"], selector["pair_metadata"]), code)
    records = value["pair_metadata"]
    _query_associations(records, request)
    _require(type(value["metadata_bindings"]) is list, code)
    bound = set()
    for binding in value["metadata_bindings"]:
        _fields(binding, ("pair_metadata_index", "source_ref", "artifact_ref", "artifact_sha256",
                          "field", "record_path", "value"), code)
        index, field = binding["pair_metadata_index"], binding["field"]
        _require(type(index) is int and 0 <= index < len(records), code)
        _require(type(field) is str and field in _METADATA_FIELDS, code)
        _require((index, field) not in bound, code)
        record = records[index]
        _require(record[field] is not None and _same(binding["value"], record[field]), code)
        evidence = next(item for item in record["provenance"]["fields"] if item["field"] == field)
        _require(all(_same(binding[name], evidence[name])
                     for name in ("source_ref", "artifact_ref", "record_path")), code)
        _artifact_digest(binding["artifact_ref"], binding["artifact_sha256"], code)
        bound.add((index, field))
    _require(bound == {(index, name) for index, record in enumerate(records)
                       for name in _METADATA_FIELDS if record[name] is not None}, code)
    if selector["mode"] == "native_result":
        _require(value["saved_result"] is None, code)
    else:
        _saved_result(value["saved_result"], request=request,
                      source_ref=selector["saved_result_ref"], code=code)
    return deepcopy(value)


__all__ = ["minhash_result_selector_schema", "validate_minhash_result_selector",
           "validate_minhash_pair_metadata", "validate_minhash_publication_inputs"]
