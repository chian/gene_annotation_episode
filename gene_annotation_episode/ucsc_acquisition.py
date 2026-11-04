"""Pure UCSC request and retained-response contracts.

The host owns HTTP, original bytes, Source publication and receipts.  Native
objects with duplicate members and numbers that cannot survive an ordinary JSON
round trip use an explicit document tree; no member or numeric token is chosen,
rounded or replaced.  This module performs no I/O or scientific interpretation.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import re
from urllib.parse import urlencode, urlsplit

from jsonschema import Draft202012Validator, validators

from .acquisition import SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from .domain import canonical


TOOL = "public.ucsc.request"
VERSION = "ucsc_acquisition_result_v1"
VALUE_VERSION = "ucsc_acquisition_value_v1"
ORIGIN = "https://api.genome.ucsc.edu"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_ITEMS_OUTPUT = 1_000_000
# Larger integers remain exact native tokens rather than relying on consumers'
# IEEE-754 integer precision.  This changes representation, never data coverage.
MAX_SAFE_INTEGER = 2 ** 53 - 1
_PATHS = {
    "ucsc_genomes": "/list/ucscGenomes",
    "genark_genomes": "/list/genarkGenomes",
    "public_hubs": "/list/publicHubs",
    "hub_genomes": "/list/hubGenomes",
    "tracks": "/list/tracks",
    "chromosomes": "/list/chromosomes",
    "schema": "/list/schema",
    "track": "/getData/track",
    "sequence": "/getData/sequence",
}
OPERATIONS = tuple(_PATHS)


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
ARGUMENTS_SCHEMA = deepcopy(_ARGUMENTS)
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
        .redefine("integer", lambda _, value: type(value) is int)
        .redefine("number", lambda _, value: type(value) is int
            or type(value) is float and math.isfinite(value)))
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}", re.ASCII)
_ARTIFACT = re.compile(r"artifact_[a-f0-9]{64}", re.ASCII)


def _require(condition, code="ucsc_value_invalid"):
    if not condition:
        raise ValueError(code)


def _plain(value):
    if type(value) is dict:
        for key, child in value.items():
            _require(type(key) is str)
            key.encode("utf-8")
            _plain(child)
    elif type(value) is list:
        for child in value:
            _plain(child)
    elif type(value) is str:
        value.encode("utf-8")
    else:
        _require(type(value) in (type(None), bool, int, float))
        if type(value) is float:
            _require(math.isfinite(value))


def _validated(value, schema):
    try:
        _plain(value)
        _require(_STRICT(schema).is_valid(value))
    except (TypeError, KeyError, OverflowError, RecursionError, UnicodeError) as error:
        raise ValueError("ucsc_value_invalid") from error
    return deepcopy(value)


def _same(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        right, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _literal(value):
    _require(type(value) is str and bool(value) and value == value.strip()
        and not any(ord(c) < 32 or ord(c) == 127 for c in value), "ucsc_literal_invalid")
    value.encode("utf-8")


def _hub_url(value):
    _literal(value)
    try:
        parsed = urlsplit(value)
        _require(parsed.scheme in {"http", "https"} and bool(parsed.hostname)
            and parsed.username is None and parsed.password is None and not parsed.fragment
            and not any(c.isspace() for c in value), "ucsc_hub_url_invalid")
        _require(parsed.port is None or 1 <= parsed.port <= 65535, "ucsc_hub_url_invalid")
    except (ValueError, UnicodeError) as error:
        raise ValueError("ucsc_hub_url_invalid") from error


def validate_ucsc_arguments(arguments):
    value = _validated(arguments, _ARGUMENTS)
    for name in ("genome", "track", "chrom"):
        if value.get(name) is not None:
            _literal(value[name])
    if value.get("track") is not None:
        _require("," not in value["track"], "ucsc_single_track_required")
    if value.get("hub_url") is not None:
        _hub_url(value["hub_url"])
    if value["operation"] in {"track", "sequence"}:
        _require(value["end"] > value["start"], "ucsc_half_open_interval_invalid")
    return value


def ucsc_request_spec(arguments):
    """One fixed GET.  Null optional operands mean native parameter omission."""
    arguments = validate_ucsc_arguments(arguments)
    params = {}
    for supplied, native in (("genome", "genome"), ("hub_url", "hubUrl"),
            ("track", "track"), ("chrom", "chrom"), ("start", "start"), ("end", "end"),
            ("max_items_output", "maxItemsOutput")):
        if supplied in arguments and arguments[supplied] is not None:
            params[native] = arguments[supplied]
    for supplied, native in (("track_leaves_only", "trackLeavesOnly"),
            ("json_output_arrays", "jsonOutputArrays"), ("rev_comp", "revComp")):
        if arguments.get(supplied) is True:
            params[native] = 1
    return {"service": "ucsc", "url": ORIGIN + _PATHS[arguments["operation"]],
        "params": params, "media_type": "application/json",
        "max_bytes": arguments["max_bytes"], "follow_redirects": False}


def _address(arguments):
    spec = ucsc_request_spec(arguments)
    return spec["url"] + ("?" + urlencode(spec["params"]) if spec["params"] else "")


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


def ucsc_result_schema():
    return deepcopy(_RESULT)


def ucsc_value_schema():
    return deepcopy(_VALUE)


def _issue(code, pointer):
    return {"code": code, "pointer": pointer}


def _unique_issues(issues):
    result, seen = [], set()
    for row in issues:
        key = row["code"], row["pointer"]
        if key not in seen:
            result.append(row)
            seen.add(key)
    return result


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


def _parse(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return None, "decode_failed", "invalid_native_utf8", None, None, []
    def constant(_token):
        raise ValueError("non_json_constant")
    try:
        node = json.loads(text, parse_int=_NumberToken, parse_float=_NumberToken,
            object_pairs_hook=_Members, parse_constant=constant)
    except (ValueError, RecursionError, OverflowError):
        return None, "decode_failed", "invalid_native_json", None, None, []
    try:
        native, document, issues, required = _analyse(node)
    except (UnicodeError, RecursionError):
        return None, "decode_failed", "invalid_native_unicode", None, None, []
    return (node, "json_document", None, None, document, issues) if required else (
        node, "json", None, native, None, [])


def _from_plain(value):
    # Native record parsers may retain dict subclasses, such as Biopython's
    # defaultdict structured comments. Preserve their existing members without
    # invoking a default factory or leaving an opaque mapping in the tree.
    if isinstance(value, dict):
        return _Members([(name, _from_plain(child)) for name, child in value.items()])
    if type(value) is list:
        return [_from_plain(child) for child in value]
    if type(value) in (int, float):
        return _NumberToken(json.dumps(value, allow_nan=False))
    return value


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


def _field(node, name, document, *, base=None):
    root = base if base is not None else "/native_document" if document else "/native_json"
    if not isinstance(node, _Members):
        return "unavailable", None, None
    matches = [(index, child) for index, (key, child) in enumerate(node.pairs) if key == name]
    if not matches:
        return "missing", None, None
    if len(matches) != 1:
        return "ambiguous", None, root
    index, value = matches[0]
    pointer = (root + "/members/" + str(index) + "/value" if document else
        root + "/" + name.replace("~", "~0").replace("/", "~1"))
    return "null" if value is None else "present", value, pointer


def _identity(node, key, document):
    state, value, pointer = _field(node, key, document)
    if state == "present" and (type(value) is not str or not value):
        state = "invalid"
    return {"state": state, "value": value if state == "present" else None,
        "pointer": pointer, "basis": "unavailable" if state == "unavailable" else "field_value"}


def _boolean(node, key, document):
    state, value, pointer = _field(node, key, document)
    if state == "present" and type(value) is not bool:
        state = "invalid"
    return {"state": state, "value": value if state == "present" else None, "pointer": pointer}


def _small_integer(value):
    if (not isinstance(value, _NumberToken) or not value.integer
            or len(value.token.lstrip("-")) > 16):
        return None
    number = int(value.token)
    return number if abs(number) <= MAX_SAFE_INTEGER else None


def _nonnegative_integer(value):
    return isinstance(value, _NumberToken) and value.integer and (
        not value.token.startswith("-") or not value.token[1:].strip("0"))


def _count(node, key, document, meaning):
    state, value, pointer = _field(node, key, document)
    number, token = None, value.token if isinstance(value, _NumberToken) else None
    if state == "present":
        if not _nonnegative_integer(value):
            state = "invalid"
        else:
            number = _small_integer(value)
            if number is None:
                state = "token_only"
    return {"state": state, "value": number, "number_token": token,
        "pointer": pointer, "meaning": meaning}


def _integer_equals(value, expected):
    if not _nonnegative_integer(value):
        return False
    token = value.token
    return ("0" if not token.lstrip("-0") else token) == str(expected)


def _response_issues(response, arguments):
    issues = []
    for key in ("http_status", "body_complete", "reported_retained_bytes", "response_byte_limit"):
        if response[key] is None:
            issues.append(_issue("transport_metadata_unavailable", "/response/" + key))
    status = response["http_status"]
    if status is not None and not 200 <= status < 300:
        issues.append(_issue("http_not_success", "/response/http_status"))
        if 300 <= status < 400:
            issues.append(_issue("http_redirect", "/response/http_status"))
    if response["body_complete"] is not True:
        issues.append(_issue("response_incomplete", "/response/body_complete"))
    retained, observed, declared = (response[key] for key in
        ("retained_bytes", "observed_body_bytes", "declared_body_bytes"))
    for key, conflict in (
            ("reported_retained_bytes", response["reported_retained_bytes"] not in (None, retained)),
            ("response_byte_limit", response["response_byte_limit"] not in (None, arguments["max_bytes"])),
            ("observed_body_bytes", observed is not None and (observed < retained or
                response["body_complete"] is True and observed != retained)),
            ("declared_body_bytes", response["body_complete"] is True and declared is not None and declared != retained),
            ("body_complete", response["body_complete"] is True and response["capture_failure"] is not None)):
        if conflict:
            issues.append(_issue("transport_count_conflict", "/response/" + key))
    if response["body_complete"] is True and observed is None:
        issues.append(_issue("transport_metadata_unavailable", "/response/observed_body_bytes"))
    if response["capture_failure"] is not None:
        issues.append(_issue("response_capture_failure", "/response/capture_failure"))
    if response["capture_failure"] == "provider_response_byte_limit" or (
            observed is not None and observed > arguments["max_bytes"]):
        issues.append(_issue("response_byte_limit_exceeded", "/response/observed_body_bytes"))
    if response["content_type"] is not None:
        mime = response["content_type"].split(";", 1)[0].strip().lower()
        if mime != "application/json" and not mime.endswith("+json"):
            issues.append(_issue("content_type_mismatch", "/response/content_type"))
    return issues


def _column_issues(columns, base, document):
    issues = []
    for index, row in enumerate(columns):
        location = base + ("/items/" if document else "/") + str(index)
        if not isinstance(row, _Members):
            issues.append(_issue("native_column_context_invalid", location))
            continue
        for name in ("name", "sqlType", "jsonType"):
            state, value, pointer = _field(row, name, document, base=location)
            if state != "present" or type(value) is not str or not value:
                issues.append(_issue("native_column_context_invalid", pointer or location))
    return issues


def _qualify(node, arguments, response, *, document, unavailable=False):
    """Qualify native fields without selecting an ambiguous member or a query."""
    operation = arguments["operation"]
    root = "/native_document" if document else "/native_json"
    identities = {key: _identity(node, native, document) for key, native in
        (("genome", "genome"), ("hub_url", "hubUrl"), ("track", "track"), ("chrom", "chrom"))}
    reported_orientation = _boolean(node, "revComp", document)
    cap_field = _boolean(node, "maxItemsLimit", document)
    cap = {"state": {"missing": "not_reported", "present": "reached" if cap_field["value"] else "not_reached",
        "null": "invalid", "invalid": "invalid", "ambiguous": "ambiguous", "unavailable": "unavailable"}[cap_field["state"]],
        "native_value": cap_field["value"], "pointer": cap_field["pointer"]}
    track_type = _identity(node, "type" if operation == "schema" else "trackType", document)
    kind = track_type["value"].split()[0] if track_type["state"] == "present" and track_type["value"].split() else None
    count_scope_qualified = operation == "schema" and any(
        _boolean(node, name, document)["value"] is True for name in ("splitTable", "protectedData"))
    item_meaning = ("bigwig_valid_covered_bases" if operation == "schema" and kind == "bigWig" else
        "whole_track_records" if operation == "schema" and kind in {
            "bed", "genePred", "psl", "rmsk", "altGraphX", "barChart", "chain", "ctgPos",
            "expRatio", "factorSource", "gvf", "interact", "netAlign", "peptideMapping", "pgSnp",
            "narrowPeak", "wig", "wigMaf", "bigBed", "bigGenePred", "bigNarrowPeak", "bigPsl",
            "bigMaf", "bigChain", "bigLolly", "bigMethyl", "bigBarChart", "bigInteract", "bigDbSnp", "bigNet"}
        else "native_count_unspecified")
    if count_scope_qualified:
        item_meaning = "native_count_unspecified"
    counts = {name: _count(node, name, document, meaning) for name, meaning in (
        ("itemsReturned", "returned_items"),
        ("totalAssemblies", "genark_registry_assemblies" if operation == "genark_genomes" else "native_count_unspecified"),
        ("itemCount", item_meaning), ("chromCount", "returned_chromosomes" if operation == "chromosomes"
            else "native_count_unspecified"))}
    profile = {"reported_identity": identities, "native_counts": counts, "native_item_cap": cap,
        "native_orientation": {"requested": ("reverse_complement" if arguments["rev_comp"] else "forward")
            if operation == "sequence" else None, "reported": reported_orientation},
        "native_response_state": "unavailable" if unavailable else "data"}
    issues, invalid, sequence = [], False, None
    if unavailable:
        return profile, issues, True, None
    if not isinstance(node, _Members):
        profile["native_response_state"] = "invalid"
        return profile, [_issue("json_root_not_object", root)], True, None
    error_state, error, error_pointer = _field(node, "error", document)
    status_state, native_status, status_pointer = _field(node, "statusCode", document)
    status_number = _small_integer(native_status)
    message_state, message, message_pointer = _field(node, "statusMessage", document)
    error_envelope = (status_number is not None and status_number >= 400 or
        error_state != "missing" and (status_state != "missing" or message_state != "missing"
            or response["http_status"] is not None and response["http_status"] >= 400))
    if error_envelope:
        profile["native_response_state"] = "error"
        issues.append(_issue("native_error_response", error_pointer or status_pointer or root))
        if (error_state != "present" or type(error) is not str
                or status_state != "present" or status_number is None or not 100 <= status_number <= 599
                or message_state != "present" or type(message) is not str):
            issues.append(_issue("native_error_shape_invalid", root))
        if status_number is not None and response["http_status"] not in (None, status_number):
            issues.append(_issue("native_status_conflict", status_pointer))
        return profile, issues, False, None

    def container(name, expected):
        nonlocal invalid
        state, value, pointer = _field(node, name, document)
        if state != "present":
            issues.append(_issue("native_container_ambiguous" if state == "ambiguous" else "native_container_missing",
                pointer or root))
            invalid = True
            return None
        if not isinstance(value, expected):
            issues.append(_issue("native_container_invalid", pointer))
            invalid = True
            return None
        return value

    data = None
    if operation in {"ucsc_genomes", "genark_genomes", "hub_genomes", "chromosomes"}:
        data = container({"ucsc_genomes": "ucscGenomes", "genark_genomes": "genarkGenomes",
            "hub_genomes": "genomes", "chromosomes": "chromosomes"}[operation], _Members)
    elif operation == "public_hubs":
        data = container("publicHubs", list)
    elif operation == "tracks":
        data = container(arguments["genome"], _Members)
        if data is not None and identities["genome"]["state"] == "missing":
            identities["genome"] = {"state": "present", "value": arguments["genome"],
                "pointer": _field(node, arguments["genome"], document)[2], "basis": "object_member_name"}
    elif operation == "schema":
        data = container("columnTypes", list)
        if data is not None:
            issues.extend(_column_issues(data, _field(node, "columnTypes", document)[2], document))
    elif operation == "track":
        data = container(arguments["track"], list)
        if data is not None and identities["track"]["state"] == "missing":
            identities["track"] = {"state": "present", "value": arguments["track"],
                "pointer": _field(node, arguments["track"], document)[2], "basis": "object_member_name"}

    for key, required in (("genome", operation in {"tracks", "chromosomes", "schema", "track", "sequence"}),
            ("hub_url", arguments.get("hub_url") is not None),
            ("track", operation in {"schema", "track"} or operation == "chromosomes" and arguments["track"] is not None),
            ("chrom", operation in {"track", "sequence"})):
        expected = arguments.get(key)
        field = identities[key]
        if field["state"] == "missing":
            if required:
                issues.append(_issue("native_identity_missing", root))
        elif field["state"] != "present":
            if required or field["state"] != "unavailable":
                issues.append(_issue("native_identity_ambiguous" if field["state"] == "ambiguous" else "native_identity_invalid",
                    field["pointer"] or root))
        elif expected is not None and field["value"] != expected:
            issues.append(_issue("native_identity_differs_from_request", field["pointer"]))

    for name, field in counts.items():
        if field["state"] in {"null", "invalid", "ambiguous"}:
            issues.append(_issue("native_count_invalid", field["pointer"] or root))
    if count_scope_qualified and counts["itemCount"]["state"] != "missing":
        issues.append(_issue("native_count_scope_qualified", counts["itemCount"]["pointer"] or root))
    if cap["state"] == "reached":
        issues.append(_issue("native_item_cap_reached", cap["pointer"]))
    elif cap["state"] in {"invalid", "ambiguous"}:
        issues.append(_issue("native_item_cap_invalid", cap["pointer"] or root))
    if response["http_status"] == 206 and cap["state"] != "reached":
        issues.append(_issue("native_item_cap_signal_missing", "/response/http_status"))

    counted = (len(data.pairs) if isinstance(data, _Members) else len(data) if isinstance(data, list) else None)
    count_name = "itemsReturned" if operation in {"genark_genomes", "track"} else "chromCount" if operation == "chromosomes" else None
    if count_name is not None and counted is not None:
        state, value, pointer = _field(node, count_name, document)
        if state == "present" and _nonnegative_integer(value) and not _integer_equals(value, counted):
            issues.append(_issue("native_count_conflict", pointer))
    if operation in {"genark_genomes", "track"}:
        field = counts["itemsReturned"]
        if field["state"] in {"present", "token_only"} and (
                field["value"] is None or field["value"] > arguments["max_items_output"]):
            issues.append(_issue("native_count_exceeds_requested_cap", field["pointer"]))

    if operation == "track" and isinstance(data, list):
        data_pointer = _field(node, arguments["track"], document)[2]
        columns = None
        if arguments["json_output_arrays"]:
            state, column_map, pointer = _field(node, "columnTypes", document)
            if state == "present" and isinstance(column_map, _Members):
                state, columns, pointer = _field(column_map, arguments["track"], document, base=pointer)
            if state != "present" or not isinstance(columns, list):
                columns = None
                issues.append(_issue("native_column_context_missing", pointer or root))
            else:
                issues.extend(_column_issues(columns, pointer, document))
        for index, row in enumerate(data):
            pointer = data_pointer + ("/items/" if document else "/") + str(index)
            if not isinstance(row, list if arguments["json_output_arrays"] else _Members):
                issues.append(_issue("native_row_shape_invalid", pointer))
            elif arguments["json_output_arrays"] and columns is not None and len(row) != len(columns):
                issues.append(_issue("native_column_arity_conflict", pointer))
            elif arguments["json_output_arrays"] and columns is not None:
                for column_index, (cell, column) in enumerate(zip(row, columns)):
                    state, declared, _ = _field(column, "jsonType", document)
                    matches = {"string": type(cell) is str, "number": isinstance(cell, _NumberToken),
                        "double": isinstance(cell, _NumberToken), "boolean": type(cell) is bool,
                        "null": cell is None, "array": isinstance(cell, list), "object": isinstance(cell, _Members)}
                    # Native SQL nulls remain null even for a named scalar type.
                    # Unknown native type names are retained without coercion.
                    if (cell is not None and state == "present" and type(declared) is str
                            and declared in matches and not matches[declared]):
                        issues.append(_issue("native_column_type_conflict",
                            pointer + ("/items/" if document else "/") + str(column_index)))
    if operation == "public_hubs" and isinstance(data, list):
        pointer = _field(node, "publicHubs", document)[2]
        for index, row in enumerate(data):
            location = pointer + ("/items/" if document else "/") + str(index)
            if not isinstance(row, _Members):
                issues.append(_issue("native_row_shape_invalid", location))
            else:
                state, url, url_pointer = _field(row, "hubUrl", document, base=location)
                if state != "present" or type(url) is not str or not url:
                    issues.append(_issue("native_identity_missing" if state == "missing" else "native_identity_invalid",
                        url_pointer or location))
    if operation in {"ucsc_genomes", "genark_genomes", "hub_genomes"} and isinstance(data, _Members):
        field = {"ucsc_genomes": "ucscGenomes", "genark_genomes": "genarkGenomes", "hub_genomes": "genomes"}[operation]
        pointer = _field(node, field, document)[2]
        for index, (name, row) in enumerate(data.pairs):
            location = (pointer + "/members/" + str(index) + "/value" if document else
                pointer + "/" + name.replace("~", "~0").replace("/", "~1"))
            if not isinstance(row, _Members):
                issues.append(_issue("native_row_shape_invalid", location))
    if operation == "chromosomes" and isinstance(data, _Members):
        pointer = _field(node, "chromosomes", document)[2]
        for index, (name, size) in enumerate(data.pairs):
            if not _nonnegative_integer(size):
                location = (pointer + "/members/" + str(index) + "/value" if document else
                    pointer + "/" + name.replace("~", "~0").replace("/", "~1"))
                issues.append(_issue("native_count_invalid", location))

    interval_ok = True
    if operation in {"track", "sequence"}:
        for key in ("start", "end"):
            state, value, pointer = _field(node, key, document)
            if state == "missing":
                issues.append(_issue("native_interval_missing", root))
                interval_ok = False
            elif state != "present" or not _nonnegative_integer(value):
                issues.append(_issue("native_interval_invalid", pointer or root))
                interval_ok = False
            elif not _integer_equals(value, arguments[key]):
                issues.append(_issue("native_interval_differs_from_request", pointer))
                interval_ok = False
    if operation == "sequence":
        orientation = reported_orientation
        orientation_ok = orientation["state"] == "missing" and not arguments["rev_comp"] or (
            orientation["state"] == "present" and orientation["value"] is arguments["rev_comp"])
        if not orientation_ok:
            issues.append(_issue("native_orientation_missing" if orientation["state"] == "missing" else
                "native_orientation_differs_from_request" if orientation["state"] == "present" else "native_orientation_invalid",
                orientation["pointer"] or root))
        state, dna, pointer = _field(node, "dna", document)
        dna_ok = state == "present" and type(dna) is str and bool(dna) and not set(dna) - set("ACGTRYSWKMBDHVNacgtryswkmbdhvn")
        if not dna_ok:
            issues.append(_issue("native_sequence_missing" if state == "missing" else "native_sequence_invalid", pointer or root))
        elif len(dna) != arguments["end"] - arguments["start"]:
            issues.append(_issue("native_sequence_length_conflict", pointer))
            dna_ok = False
        identity_ok = all(identities[key]["state"] == "present" and identities[key]["value"] == arguments[key]
            for key in ("genome", "chrom")) and (arguments["hub_url"] is None or
                identities["hub_url"]["state"] == "present" and identities["hub_url"]["value"] == arguments["hub_url"])
        if interval_ok and orientation_ok and dna_ok and identity_ok:
            sequence = {"genome": identities["genome"]["value"], "chrom": identities["chrom"]["value"],
                "hub_url": identities["hub_url"]["value"] if identities["hub_url"]["state"] == "present" else None,
                "start": arguments["start"], "end": arguments["end"], "rev_comp": arguments["rev_comp"],
                "dna": dna, "length": len(dna), "dna_pointer": pointer + ("/value" if document else "")}
    if invalid:
        profile["native_response_state"] = "invalid"
    return profile, issues, invalid, sequence


def _state(native_issues, invalid):
    qualifications = {"native_duplicate_member", "native_number_token_required", "native_error_response",
        "native_item_cap_reached", "native_count_scope_qualified"}
    return "invalid" if invalid else "partial" if any(row["code"] not in qualifications for row in native_issues) else "complete"


def _snapshot_response(snapshot, arguments, artifact_ref):
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "ucsc_snapshot_invalid")
    _plain(snapshot.request)
    _require(_same(snapshot.request, arguments), "ucsc_snapshot_selected_request_conflict")
    _require(type(snapshot.transport) is dict, "ucsc_snapshot_transport_invalid")
    transport = deepcopy(snapshot.transport)
    # The actual HTTP owner supplies ordered header tuples; retained JSON
    # provenance supplies arrays. Normalize only this transport field locally,
    # leaving the original snapshot and native response bytes untouched.
    if type(transport.get("header_items")) is list:
        transport["header_items"] = [list(pair) if type(pair) is tuple else pair
            for pair in transport["header_items"]]
    _plain(transport)
    spec = ucsc_request_spec(arguments)
    address = _address(arguments)
    request = transport.get("request")
    _require(type(request) is dict and request.get("method") == "GET" and request.get("url") == address
        and not {"body_base64", "body_sha256"}.intersection(request), "ucsc_snapshot_request_conflict")
    _require(snapshot.service == "ucsc" and snapshot.url in (spec["url"], address)
        and snapshot.media_type == spec["media_type"], "ucsc_snapshot_request_conflict")
    _require(transport.get("effective_url", address) == address, "ucsc_snapshot_effective_url_conflict")
    policy = transport.get("request_policy")
    timeout = policy.get("timeout_seconds") if type(policy) is dict else None
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    _require(type(policy) is dict and policy.get("automatic_redirects") is False
        and valid_timeout,
        "ucsc_snapshot_transport_policy_conflict")
    _require(len(snapshot.content) <= arguments["max_bytes"], "ucsc_snapshot_byte_limit_conflict")
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(), "ucsc_artifact_identity_conflict")
    def observed(key, kind, minimum=None, maximum=None):
        value = transport.get(key)
        return value if type(value) is kind and (minimum is None or value >= minimum) and (
            maximum is None or value <= maximum) else None
    headers = transport.get("headers")
    def header(name):
        value = headers.get(name) if type(headers) is dict else None
        return value if type(value) is str else None
    return {"request_url": address, "media_type": snapshot.media_type,
        "http_status": observed("status", int, 100, 599), "content_type": header("content-type"),
        "body_complete": observed("body_complete", bool), "retained_bytes": len(snapshot.content),
        "reported_retained_bytes": observed("retained_body_bytes", int, 0),
        "observed_body_bytes": observed("observed_body_bytes", int, 0),
        "declared_body_bytes": observed("declared_body_bytes", int, 0),
        "response_byte_limit": observed("response_byte_limit", int, 0),
        "capture_failure": observed("body_capture_failure", str), "retry_after": header("retry-after"),
        "timeout_seconds": timeout, "automatic_redirects": False}


def _ucsc_content(snapshot, *, arguments, artifact_ref):
    response = _snapshot_response(snapshot, arguments, artifact_ref)
    node, parse_state, error, native, document, parse_issues = _parse(snapshot.content)
    profile, native_issues, invalid, _ = _qualify(node, arguments, response,
        document=parse_state == "json_document", unavailable=parse_state == "decode_failed")
    if error is not None:
        parse_issues = [_issue(error, "/raw_artifact_ref")]
    return {"operation": TOOL, "service": "ucsc",
        "raw_artifact_ref": artifact_ref, "requested": arguments,
        "response": response, "parse_state": parse_state, "decode_error": error,
        "native_json": native, "native_document": document,
        "representation_state": _state(parse_issues + native_issues, invalid),
        "population_coverage": "selected_response_only", **profile,
        "issues": _unique_issues(_response_issues(response, arguments) + parse_issues + native_issues)}


def _validate_ucsc_content(value):
    arguments = validate_ucsc_arguments(value["requested"])
    _require(_ARTIFACT.fullmatch(value["raw_artifact_ref"]) is not None)
    _require(value["response"]["request_url"] == _address(arguments), "ucsc_result_request_conflict")
    _require(value["response"]["retained_bytes"] <= arguments["max_bytes"])
    try:
        valid_timeout = math.isfinite(value["response"]["timeout_seconds"]) and value["response"]["timeout_seconds"] > 0
    except OverflowError:
        valid_timeout = False
    _require(valid_timeout and value["response"]["automatic_redirects"] is False,
        "ucsc_result_transport_policy_conflict")
    state, error = value["parse_state"], value["decode_error"]
    if state == "decode_failed":
        _require(error is not None and value["native_json"] is None and value["native_document"] is None)
        node, parse_issues = None, [_issue(error, "/raw_artifact_ref")]
    else:
        _require(error is None)
        if state == "json":
            _require(value["native_document"] is None)
            node = _from_plain(value["native_json"])
        else:
            _require(value["native_json"] is None and value["native_document"] is not None)
            node = _from_document(value["native_document"])
        native, document, parse_issues, required = _analyse(node)
        _require(required is (state == "json_document"), "ucsc_native_representation_conflict")
        _require(_same(document, value["native_document"]) if required else _same(native, value["native_json"]))
    profile, native_issues, invalid, _ = _qualify(node, arguments, value["response"],
        document=state == "json_document", unavailable=state == "decode_failed")
    _require(all(_same(value[key], expected) for key, expected in profile.items()), "ucsc_native_qualification_conflict")
    _require(value["representation_state"] == _state(parse_issues + native_issues, invalid))
    _require(_same(value["issues"], _unique_issues(_response_issues(value["response"], arguments) + parse_issues + native_issues)))
    return value


def ucsc_value(snapshot, *, arguments, artifact_ref):
    arguments = validate_ucsc_arguments(arguments)
    content = _ucsc_content(snapshot, arguments=arguments, artifact_ref=artifact_ref)
    return validate_ucsc_value({"version": VALUE_VERSION, **content,
        "observed_transfer": {key: deepcopy(snapshot.transport.get(key)) for key in
            ("declared_body_bytes", "body_capture_failure")}})


def validate_ucsc_value(value):
    value = _validate_ucsc_content(_validated(value, _VALUE))
    for raw_key, response_key, kind in (("declared_body_bytes", "declared_body_bytes", int),
            ("body_capture_failure", "capture_failure", str)):
        raw = value["observed_transfer"][raw_key]
        expected = raw if type(raw) is kind and (kind is not int or raw >= 0) else None
        _require(_same(value["response"][response_key], expected), "ucsc_transfer_metadata_conflict")
    return value


def ucsc_result(snapshot, *, arguments, source_ref, artifact_ref):
    arguments = validate_ucsc_arguments(arguments)
    _require(type(source_ref) is str and _SOURCE.fullmatch(source_ref) is not None, "ucsc_source_reference_invalid")
    content = _ucsc_content(snapshot, arguments=arguments, artifact_ref=artifact_ref)
    return validate_ucsc_result({"version": VERSION, "source_ref": source_ref, **content})


def validate_ucsc_result(value):
    value = _validated(value, _RESULT)
    _require(_SOURCE.fullmatch(value["source_ref"]) is not None)
    return _validate_ucsc_content(value)


def ucsc_result_from_value(value, *, source_ref):
    value = validate_ucsc_value(value)
    value.pop("observed_transfer")
    value.update(version=VERSION, source_ref=source_ref)
    return validate_ucsc_result(value)


def ucsc_sequence_interval(value):
    """Actual selected DNA interval for the host's existing reference importer.

    This supplies no target scope, inferred chromosome mapping or new record.
    Missing/ambiguous identities, unexpected orientation and capture failures
    remain unavailable; their exact native document is retained in the result.
    """
    value = validate_ucsc_result(value)
    if (value["requested"]["operation"] != "sequence" or value["parse_state"] == "decode_failed"
            or value["representation_state"] != "complete" or value["native_response_state"] != "data"
            or value["native_item_cap"]["state"] in {"reached", "invalid", "ambiguous"}
            or _response_issues(value["response"], value["requested"])):
        return None
    document = value["parse_state"] == "json_document"
    node = _from_document(value["native_document"]) if document else _from_plain(value["native_json"])
    _, _, _, sequence = _qualify(node, value["requested"], value["response"], document=document)
    return None if sequence is None else {**sequence, "source_ref": value["source_ref"],
        "raw_artifact_ref": value["raw_artifact_ref"]}


UCSC_FAILURE_CODES = tuple("ucsc_" + code for code in ISSUE_CODES) + (
    "ucsc_request_conflict", "ucsc_selected_request_conflict", "invalid_tool_input",
    "data_acquisition_failed", "data_acquisition_publication_incomplete")


def ucsc_receipt_schema():
    return acquisition_receipt_schema(failure_codes=UCSC_FAILURE_CODES)


def validate_ucsc_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=UCSC_FAILURE_CODES,
        invalid_code="ucsc_receipt_invalid")


def failed_ucsc_receipt(code, *, source_ref=None):
    return validate_ucsc_receipt(dict(acquired=False, source_ref=source_ref, data_ref=None, failure_code=code))


def _receipt_transfer_failure(value):
    response, arguments = value["response"], value["requested"]
    status = response["http_status"]
    if status is None:
        return "transport_metadata_unavailable"
    if not 200 <= status < 300:
        return "http_redirect" if 300 <= status < 400 else "http_not_success"
    if response["body_complete"] is not True:
        return "response_incomplete"
    declared, failure = (value["observed_transfer"][key] for key in
        ("declared_body_bytes", "body_capture_failure"))
    if (declared is not None and (type(declared) is not int or declared < 0)
            or failure is not None and type(failure) is not str):
        return "transport_metadata_unavailable"
    if any(response[key] is None for key in (
            "reported_retained_bytes", "observed_body_bytes", "response_byte_limit")):
        return "transport_metadata_unavailable"
    if response["capture_failure"] is not None:
        return ("response_byte_limit_exceeded" if response["capture_failure"] == "provider_response_byte_limit"
            else "response_capture_failure")
    retained = response["retained_bytes"]
    if (response["reported_retained_bytes"] != retained or response["observed_body_bytes"] != retained
            or response["declared_body_bytes"] not in (None, retained)
            or response["response_byte_limit"] != arguments["max_bytes"]):
        return "transport_count_conflict"
    if retained > arguments["max_bytes"]:
        return "response_byte_limit_exceeded"
    return None


def _receipt_native_failure(value):
    if value["parse_state"] == "decode_failed":
        return value["decode_error"]
    document = value["parse_state"] == "json_document"
    node = _from_document(value["native_document"]) if document else _from_plain(value["native_json"])
    profile, issues, _, _ = _qualify(node, value["requested"], value["response"], document=document)
    if profile["native_response_state"] == "error":
        return "native_error_response"
    # A cap bounds the selected response. These native qualifications neither
    # establish a complete matching population nor invalidate literal data.
    qualified = {"native_item_cap_reached", "native_count_scope_qualified"}
    return next((issue["code"] for issue in issues if issue["code"] not in qualified), None)


def ucsc_receipt(value, *, source_ref):
    value = validate_ucsc_value(value)
    failure = _receipt_transfer_failure(value) or _receipt_native_failure(value)
    if failure is not None:
        return failed_ucsc_receipt("ucsc_" + failure, source_ref=source_ref)
    return validate_ucsc_receipt(dict(acquired=True, source_ref=source_ref,
        data_ref=value["raw_artifact_ref"], failure_code=None))


def _failure_witness(snapshot, failure_code):
    schema = _object({"version": {"const": "ucsc_acquisition_failure_witness_v1"},
        "observed_snapshot_service": {"type": "string"}, "observed_snapshot_url": {"type": "string"},
        "failure_code": {"enum": list(UCSC_FAILURE_CODES)}})
    return _validated(dict(version="ucsc_acquisition_failure_witness_v1",
        observed_snapshot_service=snapshot.service, observed_snapshot_url=snapshot.url,
        failure_code=failure_code), schema)


def publish_ucsc_request(registry, arguments, snapshot):
    """Retain one entity; optional Reference publication grants no operand."""
    arguments = validate_ucsc_arguments(arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "ucsc_snapshot_invalid")
    artifact_ref = "artifact_" + hashlib.sha256(snapshot.content).hexdigest()
    value, failure = None, None
    try:
        value = ucsc_value(snapshot, arguments=snapshot.request, artifact_ref=artifact_ref)
    except ValueError:
        failure = "ucsc_request_conflict"
        evidence = _failure_witness(snapshot, failure)
    else:
        evidence = value
        if not _same(value["requested"], arguments):
            failure = "ucsc_selected_request_conflict"
    private_ref = registry.store.artifact(canonical(evidence), "application/json")
    captured = replace(snapshot, url=value["response"]["request_url"]) if value is not None and failure is None else snapshot
    source = registry._source("ucsc", None, snapshot=captured, accession=None, software_version=None,
        auxiliary_artifact_refs=[private_ref])
    _require(source["artifact_ref"] == artifact_ref, "ucsc_artifact_identity_conflict")
    receipt = (failed_ucsc_receipt(failure, source_ref=source["id"]) if failure else
        ucsc_receipt(value, source_ref=source["id"]))
    if receipt["acquired"] and arguments["operation"] == "sequence":
        registry._publish_ucsc_sequence_reference(ucsc_result_from_value(value,
            source_ref=source["id"]), source)
    return receipt, [source["id"], *([artifact_ref] if receipt["acquired"] else [])]


__all__ = ["TOOL", "VERSION", "VALUE_VERSION", "ORIGIN", "MAX_RESPONSE_BYTES", "MAX_ITEMS_OUTPUT", "OPERATIONS",
    "ARGUMENTS_SCHEMA", "ISSUE_CODES", "validate_ucsc_arguments", "ucsc_request_spec",
    "ucsc_result_schema", "ucsc_result", "validate_ucsc_result", "ucsc_sequence_interval",
    "ucsc_value", "validate_ucsc_value", "ucsc_value_schema", "ucsc_result_from_value", "UCSC_FAILURE_CODES",
    "ucsc_receipt_schema", "ucsc_receipt", "validate_ucsc_receipt", "failed_ucsc_receipt", "publish_ucsc_request"]
