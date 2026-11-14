"""Pure UCSC request and retained-response contracts.

The host owns HTTP, original bytes, Source publication and receipts.  Native
objects with duplicate members and numbers that cannot survive an ordinary JSON
round trip use an explicit document tree; no member or numeric token is chosen,
rounded or replaced.  This module performs no I/O or scientific interpretation.
"""

from copy import deepcopy

import hashlib

import json

import math

import re

TOOL = "public.ucsc.request"

VERSION = "ucsc_acquisition_result_v1"

VALUE_VERSION = "ucsc_acquisition_value_v1"

MAX_RESPONSE_BYTES = 8 * 1024 * 1024

MAX_ITEMS_OUTPUT = 1_000_000

MAX_SAFE_INTEGER = 2 ** 53 - 1

def _object(properties):
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}

_NAME = {"type": "string", "minLength": 1}

_OPTIONAL_NAME = {"type": ["string", "null"], "minLength": 1}

_BYTES = {"type": "integer", "minimum": 1, "maximum": MAX_RESPONSE_BYTES}

_ITEMS = {"type": "integer", "minimum": 1, "maximum": MAX_ITEMS_OUTPUT}

_POSITION = {"type": "integer", "minimum": 0}

_ASSEMBLY = {"genome": _NAME, "hub_url": _OPTIONAL_NAME}

_OPERANDS = {
    "ucsc_genomes": {},
    "genark_genomes": {"genome": _OPTIONAL_NAME, "max_items_output": _ITEMS},
    "public_hubs": {},
    "hub_genomes": {"hub_url": _NAME},
    "tracks": {**_ASSEMBLY, "track_leaves_only": {"type": "boolean"}},
    "chromosomes": {**_ASSEMBLY, "track": _OPTIONAL_NAME},
    "schema": {**_ASSEMBLY, "track": _NAME},
    "track": {**_ASSEMBLY, "track": _NAME, "chrom": _NAME,
        "start": _POSITION, "end": _POSITION, "max_items_output": _ITEMS,
        "json_output_arrays": {"type": "boolean"}},
    "sequence": {**_ASSEMBLY, "chrom": _NAME, "start": _POSITION,
        "end": _POSITION, "rev_comp": {"type": "boolean"}},
}

_ARGUMENTS = {"oneOf": [_object({"operation": {"const": name},
    **deepcopy(fields), "max_bytes": deepcopy(_BYTES)}) for name, fields in _OPERANDS.items()]}

_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)

def _require(condition, code="ucsc_value_invalid"):
    if not condition:
        raise ValueError(code)

_COUNT = {"type": ["integer", "null"], "minimum": 0}

_TEXT_OR_NULL = {"type": ["string", "null"]}

_RESPONSE = _object({
    "request_url": {"type": "string"}, "media_type": _NAME,
    "http_status": {"type": ["integer", "null"], "minimum": 100, "maximum": 599},
    "content_type": _TEXT_OR_NULL, "body_complete": {"type": ["boolean", "null"]},
    "retained_bytes": {"type": "integer", "minimum": 0},
    "reported_retained_bytes": _COUNT, "observed_body_bytes": _COUNT,
    "declared_body_bytes": _COUNT, "response_byte_limit": _COUNT,
    "capture_failure": _TEXT_OR_NULL, "retry_after": _TEXT_OR_NULL,
    "timeout_seconds": {"type": "number", "exclusiveMinimum": 0},
    "automatic_redirects": {"const": False},
})

_NATIVE_JSON = {"anyOf": [{"type": "null"}, {"type": "boolean"}, {"type": "number"},
    {"type": "string"}, {"type": "array", "items": {"$ref": "#/$defs/NativeJSON"}},
    {"type": "object", "additionalProperties": {"$ref": "#/$defs/NativeJSON"}}]}

_NODE_REF = {"$ref": "#/$defs/NativeDocument"}

_DOCUMENT = {"oneOf": [
    _object({"kind": {"const": "object"}, "members": {"type": "array", "items":
        _object({"name": {"type": "string"}, "value": _NODE_REF})}}),
    _object({"kind": {"const": "array"}, "items": {"type": "array", "items": _NODE_REF}}),
    _object({"kind": {"const": "number"}, "token": {"type": "string"}}),
    _object({"kind": {"const": "string"}, "value": {"type": "string"}}),
    _object({"kind": {"const": "boolean"}, "value": {"type": "boolean"}}),
    _object({"kind": {"const": "null"}, "value": {"type": "null"}}),
]}

_FIELD_STATES = ["unavailable", "missing", "null", "ambiguous", "invalid", "present"]

_IDENTITY = _object({"state": {"enum": _FIELD_STATES}, "value": _TEXT_OR_NULL,
    "pointer": _TEXT_OR_NULL, "basis": {"enum": ["field_value", "object_member_name", "unavailable"]}})

_BOOLEAN_FIELD = _object({"state": {"enum": _FIELD_STATES},
    "value": {"type": ["boolean", "null"]}, "pointer": _TEXT_OR_NULL})

_COUNT_FIELD = _object({"state": {"enum": _FIELD_STATES + ["token_only"]},
    "value": _COUNT, "number_token": _TEXT_OR_NULL, "pointer": _TEXT_OR_NULL,
    "meaning": {"enum": ["returned_items", "genark_registry_assemblies", "returned_chromosomes",
        "whole_track_records", "bigwig_valid_covered_bases", "native_count_unspecified"]}})

_CAP = _object({"state": {"enum": ["unavailable", "not_reported", "ambiguous", "invalid", "reached", "not_reached"]},
    "native_value": {"type": ["boolean", "null"]}, "pointer": _TEXT_OR_NULL})

ISSUE_CODES = (
    "transport_metadata_unavailable", "transport_count_conflict", "http_not_success", "http_redirect",
    "response_incomplete", "response_byte_limit_exceeded", "response_capture_failure", "content_type_mismatch",
    "invalid_native_utf8", "invalid_native_json", "invalid_native_unicode", "native_duplicate_member",
    "native_number_token_required", "json_root_not_object", "native_error_response", "native_error_shape_invalid",
    "native_status_conflict", "native_container_missing", "native_container_ambiguous", "native_container_invalid",
    "native_row_shape_invalid", "native_column_context_missing", "native_column_context_invalid",
    "native_column_arity_conflict", "native_column_type_conflict",
    "native_identity_missing", "native_identity_invalid", "native_identity_ambiguous", "native_identity_differs_from_request",
    "native_interval_missing", "native_interval_invalid", "native_interval_differs_from_request",
    "native_orientation_missing", "native_orientation_invalid", "native_orientation_differs_from_request",
    "native_sequence_missing", "native_sequence_invalid", "native_sequence_length_conflict",
    "native_count_invalid", "native_count_conflict", "native_count_exceeds_requested_cap", "native_count_scope_qualified",
    "native_item_cap_reached", "native_item_cap_invalid", "native_item_cap_signal_missing",
)

_ISSUE = _object({"code": {"enum": list(ISSUE_CODES)}, "pointer": {"type": "string"}})

_RESULT = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {
    "NativeJSON": _NATIVE_JSON, "NativeDocument": _DOCUMENT}, **_object({
        "version": {"const": VERSION}, "operation": {"const": TOOL}, "service": {"const": "ucsc"},
        "source_ref": {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$",
            "format": "reference", "x-reference-namespace": "source"},
        "raw_artifact_ref": {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$",
            "format": "reference", "x-reference-namespace": "artifact"},
        "requested": _ARGUMENTS, "response": _RESPONSE,
        "parse_state": {"enum": ["json", "json_document", "decode_failed"]},
        "decode_error": {"enum": [None, "invalid_native_utf8", "invalid_native_json", "invalid_native_unicode"]},
        "native_json": {"$ref": "#/$defs/NativeJSON"},
        "native_document": {"anyOf": [{"type": "null"}, _NODE_REF]},
        "representation_state": {"enum": ["complete", "partial", "invalid"]},
        "population_coverage": {"const": "selected_response_only"},
        "native_response_state": {"enum": ["data", "error", "invalid", "unavailable"]},
        "reported_identity": _object({name: _IDENTITY for name in ("genome", "hub_url", "track", "chrom")}),
        "native_counts": _object({name: _COUNT_FIELD for name in ("itemsReturned", "totalAssemblies", "itemCount", "chromCount")}),
        "native_item_cap": _CAP,
        "native_orientation": _object({"requested": {"enum": [None, "forward", "reverse_complement"]},
            "reported": _BOOLEAN_FIELD}),
        "issues": {"type": "array", "uniqueItems": True, "items": _ISSUE},
    })}

_RESULT["$id"] = "urn:gene-annotation:ucsc-acquisition:" + hashlib.sha256(json.dumps(
    _RESULT, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

_VALUE = deepcopy(_RESULT)

_VALUE.pop("$id")

_VALUE["properties"].pop("source_ref")

_VALUE["required"].remove("source_ref")

_VALUE["properties"]["version"] = {"const": VALUE_VERSION}

_VALUE["properties"]["observed_transfer"] = _object({
    "declared_body_bytes": {"$ref": "#/$defs/NativeJSON"},
    "body_capture_failure": {"$ref": "#/$defs/NativeJSON"}})

_VALUE["required"].append("observed_transfer")

_VALUE["$id"] = "urn:gene-annotation:ucsc-acquisition-value:" + hashlib.sha256(json.dumps(
    _VALUE, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _issue(code, pointer):
    return {"code": code, "pointer": pointer}

class _Members:
    def __init__(self, pairs):
        self.pairs = pairs

class _NumberToken:
    def __init__(self, token):
        self.token = token
        self.integer = "." not in token and "e" not in token.lower()

def _number_value(number):
    token = number.token
    try:
        if number.integer:
            if len(token.lstrip("-")) > 16:
                return None, False
            value = int(token)
            return (value, True) if abs(value) <= MAX_SAFE_INTEGER and str(value) == token else (None, False)
        value = float(token)
        if math.isfinite(value) and json.dumps(value, allow_nan=False) == token:
            return value, True
    except (ValueError, OverflowError):
        pass
    return None, False

def _analyse(node, pointer="/native_document"):
    """Return one reversible native representation, with exact token locations."""
    if isinstance(node, _Members):
        native, members, issues, names, required = {}, [], [], set(), False
        for index, (name, child) in enumerate(node.pairs):
            name.encode("utf-8")
            location = pointer + "/members/" + str(index)
            value, document, child_issues, child_required = _analyse(child, location + "/value")
            members.append({"name": name, "value": document})
            issues.extend(child_issues)
            required |= child_required
            if name in names:
                required = True
                issues.append(_issue("native_duplicate_member", location))
            else:
                native[name] = value
                names.add(name)
        return native, {"kind": "object", "members": members}, issues, required
    if isinstance(node, list):
        native, items, issues, required = [], [], [], False
        for index, child in enumerate(node):
            value, document, child_issues, child_required = _analyse(child, pointer + "/items/" + str(index))
            native.append(value)
            items.append(document)
            issues.extend(child_issues)
            required |= child_required
        return native, {"kind": "array", "items": items}, issues, required
    if isinstance(node, _NumberToken):
        value, safe = _number_value(node)
        return value, {"kind": "number", "token": node.token}, ([] if safe else [
            _issue("native_number_token_required", pointer)]), not safe
    if isinstance(node, str):
        node.encode("utf-8")
        return node, {"kind": "string", "value": node}, [], False
    if type(node) is bool:
        return node, {"kind": "boolean", "value": node}, [], False
    _require(node is None)
    return None, {"kind": "null", "value": None}, [], False

def _from_document(value):
    kind = value["kind"]
    if kind == "object":
        return _Members([(row["name"], _from_document(row["value"])) for row in value["members"]])
    if kind == "array":
        return [_from_document(row) for row in value["items"]]
    if kind == "number":
        _require(_NUMBER.fullmatch(value["token"]) is not None, "ucsc_native_number_token_invalid")
        return _NumberToken(value["token"])
    return value["value"]
