"""Literal EMDB entry metadata from one caller-selected bounded HTTP reply.

These pure records preserve native JSON and response qualifications. They do
not acquire maps, select a reconstruction, interpret citations or confer Source
permission. The ordinary acquisition host retains and authenticates the bytes.
"""
from copy import deepcopy
import hashlib
import json
import math
import re
from urllib.parse import quote

from jsonschema import Draft202012Validator, validators

from .acquisition import SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt


SERVICE = "emdb"
ENTRY_ROOT = "https://www.ebi.ac.uk/emdb/api/entry/"
VERSION = "emdb_entry_result_v1"
ISSUE_CODES = (
    "invalid_native_json", "response_not_object", "native_entry_id_missing",
    "native_entry_id_null", "native_entry_id_invalid", "native_entry_id_differs_from_request",
    "http_not_success", "response_incomplete", "transport_metadata_unavailable",
)
ISSUE_POINTERS = (
    "", "/emdb_id", "/transport/status", "/transport/headers/content-type",
    "/transport/body_complete", "/transport/observed_body_bytes", "/transport/declared_body_bytes",
    "/transport/retained_body_bytes", "/transport/response_byte_limit",
)
EMDB_FAILURE_CODES = (
    "invalid_tool_input", "data_acquisition_failed", "data_acquisition_publication_incomplete",
    "emdb_request_conflict", "emdb_saved_outcome_conflict", *("emdb_" + code for code in ISSUE_CODES),
)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


EMDB_ENTRY_ARGUMENTS_SCHEMA = _object({
    "entry_id": {"type": "string", "pattern": "^EMD-[0-9]+$"},
    "max_bytes": {"type": "integer", "minimum": 1},
})
_NATIVE_JSON = {"anyOf": [{"type": "null"}, {"type": "boolean"}, {"type": "number"},
    {"type": "string"}, {"type": "array", "items": {"$ref": "#/$defs/NativeJSON"}},
    {"type": "object", "additionalProperties": {"$ref": "#/$defs/NativeJSON"}}]}
_RESPONSE = _object({
    "http_status": {"type": ["integer", "null"], "minimum": 100, "maximum": 599},
    "content_type": {"type": ["string", "null"]},
    "body_complete": {"type": ["boolean", "null"]},
    "retained_bytes": {"type": "integer", "minimum": 0},
    "observed_body_bytes": {"type": ["integer", "null"], "minimum": 0},
    "declared_body_bytes": {"type": ["integer", "null"], "minimum": 0},
})
_RESULT = {"$defs": {"NativeJSON": _NATIVE_JSON}, **_object({
    "version": {"const": VERSION},
    "source_ref": {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$",
        "format": "reference", "x-reference-namespace": "source"},
    "raw_artifact_ref": {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$",
        "format": "reference", "x-reference-namespace": "artifact"},
    "requested": deepcopy(EMDB_ENTRY_ARGUMENTS_SCHEMA),
    "response": _RESPONSE,
    "parse_state": {"enum": ["object", "non_object", "decode_failed"]},
    "native_json": {"$ref": "#/$defs/NativeJSON"},
    "issues": {"type": "array", "uniqueItems": True, "items": _object({
        "code": {"enum": list(ISSUE_CODES)}, "pointer": {"enum": list(ISSUE_POINTERS)}})},
})}
_RESULT["$id"] = "urn:gene-annotation:emdb-entry:" + hashlib.sha256(
    json.dumps(_RESULT, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
EMDB_ENTRY_RESULT_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object", "$defs": deepcopy(_RESULT["$defs"]), "allOf": [deepcopy(_RESULT)]}
EMDB_ENTRY_RESULT_SCHEMA["$id"] = "urn:gene-annotation:emdb-entry:" + hashlib.sha256(
    json.dumps(EMDB_ENTRY_RESULT_SCHEMA, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, value: type(value) is int)
    .redefine("number", lambda _, value: type(value) is int or type(value) is float and math.isfinite(value)))


def _require(condition, code="emdb_value_invalid"):
    if not condition:
        raise ValueError(code)


def _finite_json(value):
    if type(value) is dict:
        _require(all(type(key) is str for key in value))
        for key, child in value.items():
            key.encode("utf-8")
            _finite_json(child)
    elif type(value) is list:
        for child in value:
            _finite_json(child)
    elif type(value) is float:
        _require(math.isfinite(value))
    elif type(value) is str:
        value.encode("utf-8")
    else:
        _require(type(value) in (type(None), bool, int))


def _validated(value, schema):
    try:
        _finite_json(value)
        _require(_STRICT(schema).is_valid(value))
    except (TypeError, KeyError, IndexError, OverflowError, RecursionError, UnicodeError) as error:
        raise ValueError("emdb_value_invalid") from error
    return deepcopy(value)


def validate_emdb_entry_arguments(value):
    value = _validated(value, EMDB_ENTRY_ARGUMENTS_SCHEMA)
    _require(re.fullmatch(r"EMD-[0-9]+", value["entry_id"], re.ASCII) is not None)
    return value


def emdb_entry_url(entry_id):
    _require(type(entry_id) is str and re.fullmatch(r"EMD-[0-9]+", entry_id, re.ASCII) is not None)
    return ENTRY_ROOT + quote(entry_id, safe="")


def _issue(code, pointer=""):
    return {"code": code, "pointer": pointer}


def _response(snapshot, arguments):
    url = emdb_entry_url(arguments["entry_id"])
    _require(isinstance(snapshot, SourceSnapshot) and snapshot.service == SERVICE
        and type(snapshot.content) is bytes and snapshot.url == url
        and type(snapshot.request) is dict
        and validate_emdb_entry_arguments(snapshot.request) == arguments,
        "emdb_snapshot_request_conflict")
    _require(len(snapshot.content) <= arguments["max_bytes"], "emdb_snapshot_byte_limit_conflict")
    metadata = snapshot.transport
    _require(type(metadata) is dict, "emdb_transport_invalid")
    request = metadata.get("request")
    _require(type(request) is dict and request.get("method") == "GET" and request.get("url") == url,
        "emdb_snapshot_request_conflict")
    policy = metadata.get("request_policy")
    timeout = policy.get("timeout_seconds") if type(policy) is dict else None
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    _require(type(policy) is dict and policy.get("automatic_redirects") is False and valid_timeout,
        "emdb_snapshot_transport_policy_conflict")
    issues = []
    status = metadata.get("status")
    if type(status) is not int or not 100 <= status <= 599:
        status = None
        issues.append(_issue("transport_metadata_unavailable", "/transport/status"))
    elif not 200 <= status < 300:
        issues.append(_issue("http_not_success", "/transport/status"))
    headers = metadata.get("headers")
    content_type = headers.get("content-type") if type(headers) is dict else None
    if content_type is not None and type(content_type) is not str:
        content_type = None
        issues.append(_issue("transport_metadata_unavailable", "/transport/headers/content-type"))
    complete = metadata.get("body_complete")
    if type(complete) is not bool:
        complete = None
        issues.append(_issue("transport_metadata_unavailable", "/transport/body_complete"))
    if complete is not True:
        issues.append(_issue("response_incomplete", "/transport/body_complete"))
    counts = {}
    for field in ("observed_body_bytes", "declared_body_bytes"):
        value = metadata.get(field)
        if value is not None and (type(value) is not int or value < 0):
            value = None
            issues.append(_issue("transport_metadata_unavailable", "/transport/" + field))
        counts[field] = value
    for field, expected in (("retained_body_bytes", len(snapshot.content)),
            ("response_byte_limit", arguments["max_bytes"])):
        if type(metadata.get(field)) is not int or metadata[field] != expected:
            issues.append(_issue("transport_metadata_unavailable", "/transport/" + field))
    return {"http_status": status, "content_type": content_type, "body_complete": complete,
        "retained_bytes": len(snapshot.content), **counts}, issues


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "emdb_invalid_native_json")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("emdb_invalid_native_json")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    _finite_json(value)
    return value


def _native_issues(native, state, arguments):
    if state == "decode_failed":
        return [_issue("invalid_native_json")]
    if state == "non_object":
        return [_issue("response_not_object")]
    if "emdb_id" not in native:
        return [_issue("native_entry_id_missing", "/emdb_id")]
    value = native["emdb_id"]
    if value is None:
        return [_issue("native_entry_id_null", "/emdb_id")]
    if type(value) is not str or not value:
        return [_issue("native_entry_id_invalid", "/emdb_id")]
    if value != arguments["entry_id"]:
        return [_issue("native_entry_id_differs_from_request", "/emdb_id")]
    return []


def emdb_entry_result(snapshot, *, arguments, source_ref, artifact_ref):
    arguments = validate_emdb_entry_arguments(arguments)
    response, issues = _response(snapshot, arguments)
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(),
        "emdb_artifact_identity_conflict")
    try:
        native = _decode(snapshot.content)
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        native, state = None, "decode_failed"
    else:
        state = "object" if type(native) is dict else "non_object"
    issues.extend(_native_issues(native, state, arguments))
    return validate_emdb_entry_result({"version": VERSION, "source_ref": source_ref,
        "raw_artifact_ref": artifact_ref, "requested": arguments, "response": response,
        "parse_state": state, "native_json": native, "issues": issues})


def _validate_response_issues(value, native_issues):
    response = value["response"]
    pairs = {(issue["code"], issue["pointer"]) for issue in value["issues"]}
    status = response["http_status"]
    _require((("http_not_success", "/transport/status") in pairs)
        == (status is not None and not 200 <= status < 300))
    _require((("response_incomplete", "/transport/body_complete") in pairs)
        == (response["body_complete"] is not True))
    fields = {"http_status": "status", "content_type": "headers/content-type",
        "body_complete": "body_complete", "observed_body_bytes": "observed_body_bytes",
        "declared_body_bytes": "declared_body_bytes"}
    for field in ("http_status", "body_complete"):
        if response[field] is None:
            _require(("transport_metadata_unavailable", "/transport/" + fields[field]) in pairs)
    native_pairs = {(issue["code"], issue["pointer"]) for issue in native_issues}
    allowed = native_pairs | {("http_not_success", "/transport/status"),
        ("response_incomplete", "/transport/body_complete"),
        ("transport_metadata_unavailable", "/transport/retained_body_bytes"),
        ("transport_metadata_unavailable", "/transport/response_byte_limit")}
    allowed.update(("transport_metadata_unavailable", "/transport/" + pointer) for pointer in fields.values())
    _require(native_pairs <= pairs <= allowed)
    for field, pointer in fields.items():
        if ("transport_metadata_unavailable", "/transport/" + pointer) in pairs:
            _require(response[field] is None)


def validate_emdb_entry_result(value):
    value = _validated(value, EMDB_ENTRY_RESULT_SCHEMA)
    _require(re.fullmatch(r"source_[a-f0-9]{24,64}", value["source_ref"], re.ASCII) is not None
        and re.fullmatch(r"artifact_[a-f0-9]{64}", value["raw_artifact_ref"], re.ASCII) is not None)
    arguments = validate_emdb_entry_arguments(value["requested"])
    native, state = value["native_json"], value["parse_state"]
    _require((state == "object") == (type(native) is dict))
    _require(state != "decode_failed" or native is None)
    _require(value["response"]["retained_bytes"] <= arguments["max_bytes"])
    _validate_response_issues(value, _native_issues(native, state, arguments))
    return value


def emdb_receipt_schema():
    return acquisition_receipt_schema(failure_codes=EMDB_FAILURE_CODES)


def validate_emdb_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=EMDB_FAILURE_CODES,
        invalid_code="emdb_receipt_invalid")


def failed_emdb_receipt(code, *, source_ref=None):
    return validate_emdb_receipt(dict(acquired=False, source_ref=source_ref,
        data_ref=None, failure_code=code))


def emdb_entry_receipt(value):
    """Confirm the selected native entry identity and complete transfer only."""
    value = validate_emdb_entry_result(value)
    codes = {row["code"] for row in value["issues"]}
    for code in ("http_not_success", "transport_metadata_unavailable", "response_incomplete",
            *ISSUE_CODES[:6]):
        if code in codes:
            return failed_emdb_receipt("emdb_" + code, source_ref=value["source_ref"])
    response = value["response"]
    if any(response[key] is not None and response[key] != response["retained_bytes"]
            for key in ("observed_body_bytes", "declared_body_bytes")):
        return failed_emdb_receipt("emdb_response_incomplete", source_ref=value["source_ref"])
    return validate_emdb_receipt(dict(acquired=True, source_ref=value["source_ref"],
        data_ref=value["raw_artifact_ref"], failure_code=None))


def publish_emdb_entry_receipt(registry, arguments, snapshot):
    arguments = validate_emdb_entry_arguments(arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes,
        "emdb_snapshot_required")
    # Custody preserves the literal response even when its selected-request join
    # fails. A failed response never exposes its primary entity as acquired data.
    source = registry._source(SERVICE, None, snapshot=snapshot, accession=arguments["entry_id"],
        software_version=None)
    try:
        value = emdb_entry_result(snapshot, arguments=arguments,
            source_ref=source["id"], artifact_ref=source["artifact_ref"])
    except ValueError:
        receipt = failed_emdb_receipt("emdb_request_conflict", source_ref=source["id"])
    else:
        receipt = emdb_entry_receipt(value)
    return receipt, [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]


__all__ = ["SERVICE", "ENTRY_ROOT", "EMDB_ENTRY_ARGUMENTS_SCHEMA", "EMDB_ENTRY_RESULT_SCHEMA",
    "emdb_entry_url", "validate_emdb_entry_arguments", "emdb_entry_result", "validate_emdb_entry_result",
    "EMDB_FAILURE_CODES", "emdb_receipt_schema", "validate_emdb_receipt", "failed_emdb_receipt",
    "emdb_entry_receipt", "publish_emdb_entry_receipt"]
