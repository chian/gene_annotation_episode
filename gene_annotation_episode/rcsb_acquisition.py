"""Literal selected RCSB acquisitions, without parsing coordinates or scoring.

The caller publishes the original HTTP entity and owns actual Source/File
permission. These pure helpers validate operands and project selected native
metadata; an identifier or File-shaped value does not establish authority.
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
from .protein_structure_contracts import validate_file_identity


ENTRY_FIELDS = ("rcsb_id", "rcsb_entry_container_identifiers", "rcsb_entry_info", "exptl", "cell", "symmetry", "struct")
FILE_FORMATS = {"pdb_3x_text": "pdb", "pdbx_mmcif_text": "cif"}
DATA_ROOT = "https://data.rcsb.org/rest/v1/core/entry/"
FILE_ROOT = "https://files.rcsb.org/download/"
SERVICE = "rcsb_pdb"
_ID = {"type": "string", "pattern": "^[A-Za-z0-9_]+$"}
_COUNT = {"type": "integer", "minimum": 0}
_SOURCE = {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$", "format": "reference", "x-reference-namespace": "source"}
_ARTIFACT = {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$", "format": "reference", "x-reference-namespace": "artifact"}
ISSUE_CODES = ("invalid_native_json", "response_not_object", "native_entry_id_missing", "native_entry_id_null",
    "native_entry_id_invalid", "native_entry_id_differs_from_request", "selected_field_missing",
    "http_not_success", "response_incomplete", "transport_metadata_unavailable")


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _owned(schema):
    resource = deepcopy(schema)
    resource["$id"] = "urn:gene-annotation:rcsb:" + hashlib.sha256(
        json.dumps(resource, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    document = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
        "$defs": deepcopy(resource.get("$defs", {})), "allOf": [resource]}
    document["$id"] = "urn:gene-annotation:rcsb:" + hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return document


RCSB_ENTRY_ARGUMENTS_SCHEMA = _object(dict(entry_id=deepcopy(_ID),
    fields=dict(type="array", items={"enum": list(ENTRY_FIELDS)}, uniqueItems=True),
    max_bytes=dict(type="integer", minimum=1)))
RCSB_FILE_ARGUMENTS_SCHEMA = _object(dict(entry_id=deepcopy(_ID),
    file_format={"enum": list(FILE_FORMATS)}, max_bytes=dict(type="integer", minimum=1)))
_JSON = {"anyOf": [{"type": "null"}, {"type": "boolean"}, {"type": "number"}, {"type": "string"},
    {"type": "array", "items": {"$ref": "#/$defs/NativeJSON"}},
    {"type": "object", "additionalProperties": {"$ref": "#/$defs/NativeJSON"}}]}
_RESPONSE = _object(dict(http_status={"type": ["integer", "null"], "minimum": 100, "maximum": 599},
    content_type={"type": ["string", "null"]}, body_complete={"type": ["boolean", "null"]},
    retained_bytes=deepcopy(_COUNT), observed_body_bytes={"type": ["integer", "null"], "minimum": 0},
    declared_body_bytes={"type": ["integer", "null"], "minimum": 0}))
_ISSUES = dict(type="array", items=_object(dict(code={"enum": list(ISSUE_CODES)}, field={"enum": [*ENTRY_FIELDS, None]})))
_FILE = _object(dict(artifact_ref=deepcopy(_ARTIFACT), sha256=dict(type="string", pattern="^[a-f0-9]{64}$"),
    byte_length=deepcopy(_COUNT), format={"enum": list(FILE_FORMATS)}))
RCSB_ENTRY_RESULT_SCHEMA = _owned({"$defs": {"NativeJSON": _JSON}, **_object(dict(
    version={"const": "rcsb_entry_result_v1"}, source_ref=deepcopy(_SOURCE), raw_artifact_ref=deepcopy(_ARTIFACT),
    requested=deepcopy(RCSB_ENTRY_ARGUMENTS_SCHEMA), response=deepcopy(_RESPONSE),
    parse_state={"enum": ["object", "non_object", "decode_failed"]},
    observed_identity=_object(dict(native_entry_id={"type": ["string", "null"]},
        state={"enum": ["present", "native_null", "missing", "invalid", "unavailable"]},
        relation={"enum": ["exact_literal_match", "different_literal", "unknown"]})),
    values=dict(type="array", items=_object(dict(field={"enum": list(ENTRY_FIELDS)},
        state={"enum": ["present", "native_null", "missing", "unavailable"]}, value={"$ref": "#/$defs/NativeJSON"}))),
    issues=deepcopy(_ISSUES)))})
RCSB_FILE_RESULT_SCHEMA = _object(dict(version={"const": "rcsb_file_result_v1"}, source_ref=deepcopy(_SOURCE),
    file=deepcopy(_FILE), requested=deepcopy(RCSB_FILE_ARGUMENTS_SCHEMA), response=deepcopy(_RESPONSE),
    observed_identity=_object(dict(native_entry_id={"type": "null"}, state={"const": "not_parsed"})),
    issues=deepcopy(_ISSUES)))
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, value: type(value) is int)
    .redefine("number", lambda _, value: type(value) is int or type(value) is float and math.isfinite(value)))


def _require(condition, code="rcsb_value_invalid"):
    if not condition:
        raise ValueError(code)


def _plain(value):
    if type(value) is dict:
        _require(all(type(key) is str for key in value))
        for child in value.values():
            _plain(child)
    elif type(value) is list:
        for child in value:
            _plain(child)
    elif type(value) is float:
        _require(math.isfinite(value))
    else:
        _require(type(value) in (str, int, bool, type(None)))
    if type(value) is str:
        value.encode("utf-8")


def _validated(value, schema):
    try:
        _plain(value)
        _require(_STRICT(schema).is_valid(value))
    except (TypeError, KeyError, IndexError, OverflowError, RecursionError, UnicodeError) as error:
        raise ValueError("rcsb_value_invalid") from error
    return deepcopy(value)


def validate_rcsb_entry_arguments(arguments):
    arguments = _validated(arguments, RCSB_ENTRY_ARGUMENTS_SCHEMA)
    _require(re.fullmatch(r"[A-Za-z0-9_]+", arguments["entry_id"], re.ASCII) is not None)
    return arguments


def validate_rcsb_file_arguments(arguments):
    arguments = _validated(arguments, RCSB_FILE_ARGUMENTS_SCHEMA)
    _require(re.fullmatch(r"[A-Za-z0-9_]+", arguments["entry_id"], re.ASCII) is not None)
    return arguments


def rcsb_entry_url(entry_id):
    return DATA_ROOT + quote(entry_id, safe="")


def rcsb_file_url(entry_id, file_format):
    return FILE_ROOT + quote(entry_id, safe="") + "." + FILE_FORMATS[file_format]


def _issue(code, field=None):
    return dict(code=code, field=field)


def _response(snapshot, arguments, url):
    validator = validate_rcsb_file_arguments if "file_format" in arguments else validate_rcsb_entry_arguments
    _require(isinstance(snapshot, SourceSnapshot) and snapshot.service == SERVICE
        and type(snapshot.content) is bytes and snapshot.url == url
        and type(snapshot.request) is dict and validator(snapshot.request) == arguments,
        "rcsb_snapshot_request_conflict")
    _require(len(snapshot.content) <= arguments["max_bytes"], "rcsb_snapshot_byte_limit_conflict")
    metadata = snapshot.transport
    _require(type(metadata) is dict, "rcsb_transport_invalid")
    request = metadata.get("request")
    _require(type(request) is dict and request.get("method") == "GET" and request.get("url") == url,
        "rcsb_snapshot_request_conflict")
    issues = []
    headers = metadata.get("headers")
    content_type = headers.get("content-type") if type(headers) is dict else None
    if content_type is not None and type(content_type) is not str:
        content_type = None
        issues.append(_issue("transport_metadata_unavailable"))
    status = metadata.get("status")
    if type(status) is not int or not 100 <= status <= 599:
        status = None
        issues.append(_issue("transport_metadata_unavailable"))
    elif not 200 <= status < 300:
        issues.append(_issue("http_not_success"))
    complete = metadata.get("body_complete")
    if type(complete) is not bool:
        complete = None
        issues.append(_issue("transport_metadata_unavailable"))
    if complete is not True:
        issues.append(_issue("response_incomplete"))
    counts = {}
    for field in ("observed_body_bytes", "declared_body_bytes"):
        value = metadata.get(field)
        if value is not None and (type(value) is not int or value < 0):
            value = None
            issues.append(_issue("transport_metadata_unavailable"))
        counts[field] = value
    if (metadata.get("retained_body_bytes") != len(snapshot.content)
            or type(metadata.get("retained_body_bytes")) is not int
            or metadata.get("response_byte_limit") != arguments["max_bytes"]
            or type(metadata.get("response_byte_limit")) is not int):
        issues.append(_issue("transport_metadata_unavailable"))
    response = dict(http_status=status, content_type=content_type, body_complete=complete,
        retained_bytes=len(snapshot.content), **counts)
    return response, list({(row["code"], row["field"]): row for row in issues}.values())


def _decode(raw):
    def pairs(items):
        result = {}
        for name, value in items:
            _require(name not in result, "invalid_native_json")
            result[name] = value
        return result
    def nonfinite(value):
        raise ValueError("invalid_native_json")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    _plain(value)
    return value


def _artifact(snapshot, artifact_ref):
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(), "rcsb_artifact_identity_conflict")
    return artifact_ref


def rcsb_entry_result(snapshot, *, arguments, source_ref, artifact_ref):
    arguments = validate_rcsb_entry_arguments(arguments)
    response, issues = _response(snapshot, arguments, rcsb_entry_url(arguments["entry_id"]))
    artifact_ref = _artifact(snapshot, artifact_ref)
    try:
        native = _decode(snapshot.content)
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        native, parse_state = None, "decode_failed"
        issues.append(_issue("invalid_native_json"))
    else:
        parse_state = "object" if type(native) is dict else "non_object"
        if parse_state != "object":
            issues.append(_issue("response_not_object"))
    observed = dict(native_entry_id=None, state="unavailable", relation="unknown")
    if parse_state == "object":
        if "rcsb_id" not in native:
            observed["state"] = "missing"
            issues.append(_issue("native_entry_id_missing", "rcsb_id"))
        elif native["rcsb_id"] is None:
            observed["state"] = "native_null"
            issues.append(_issue("native_entry_id_null", "rcsb_id"))
        elif type(native["rcsb_id"]) is not str or not native["rcsb_id"]:
            observed["state"] = "invalid"
            issues.append(_issue("native_entry_id_invalid", "rcsb_id"))
        else:
            observed.update(native_entry_id=native["rcsb_id"], state="present",
                relation="exact_literal_match" if native["rcsb_id"] == arguments["entry_id"] else "different_literal")
            if observed["relation"] == "different_literal":
                issues.append(_issue("native_entry_id_differs_from_request", "rcsb_id"))
    values = []
    for field in arguments["fields"]:
        if parse_state != "object":
            state, value = "unavailable", None
        elif field not in native:
            state, value = "missing", None
            issues.append(_issue("selected_field_missing", field))
        else:
            value = native[field]
            state = "native_null" if value is None else "present"
        values.append(dict(field=field, state=state, value=deepcopy(value)))
    return validate_rcsb_entry_result(dict(version="rcsb_entry_result_v1", source_ref=source_ref,
        raw_artifact_ref=artifact_ref, requested=arguments, response=response, parse_state=parse_state,
        observed_identity=observed, values=values, issues=issues))


def rcsb_file_result(snapshot, *, arguments, source_ref, artifact_ref):
    arguments = validate_rcsb_file_arguments(arguments)
    response, issues = _response(snapshot, arguments, rcsb_file_url(arguments["entry_id"], arguments["file_format"]))
    artifact_ref = _artifact(snapshot, artifact_ref)
    file = dict(artifact_ref=artifact_ref, sha256=hashlib.sha256(snapshot.content).hexdigest(),
        byte_length=len(snapshot.content), format=arguments["file_format"])
    validate_file_identity(file)
    return validate_rcsb_file_result(dict(version="rcsb_file_result_v1", source_ref=source_ref, file=file,
        requested=arguments, observed_identity=dict(native_entry_id=None, state="not_parsed"), response=response, issues=issues))


def validate_rcsb_entry_result(value):
    value = _validated(value, RCSB_ENTRY_RESULT_SCHEMA)
    validate_rcsb_entry_arguments(value["requested"])
    _require([row["field"] for row in value["values"]] == value["requested"]["fields"])
    for row in value["values"]:
        _require((row["state"] == "present") == (row["value"] is not None))
        _require(value["parse_state"] == "object" or row["state"] == "unavailable")
    identity = value["observed_identity"]
    _require((identity["state"] == "present") == (identity["native_entry_id"] is not None))
    _require((value["parse_state"] != "object") == (identity["state"] == "unavailable"))
    _require(identity["state"] != "present" or bool(identity["native_entry_id"]))
    expected = ("exact_literal_match" if identity["native_entry_id"] == value["requested"]["entry_id"] else "different_literal")
    _require(identity["relation"] == (expected if identity["state"] == "present" else "unknown"))
    return value


def validate_rcsb_file_result(value):
    value = _validated(value, RCSB_FILE_RESULT_SCHEMA)
    validate_rcsb_file_arguments(value["requested"])
    validate_file_identity(value["file"])
    _require(value["file"]["format"] == value["requested"]["file_format"]
        and value["file"]["byte_length"] == value["response"]["retained_bytes"])
    return value


RCSB_FAILURE_CODES = tuple("rcsb_" + code for code in ISSUE_CODES) + (
    "rcsb_selected_field_unavailable", "rcsb_request_conflict", "invalid_tool_input",
    "data_acquisition_failed", "data_acquisition_publication_incomplete")


def rcsb_receipt_schema():
    return acquisition_receipt_schema(failure_codes=RCSB_FAILURE_CODES)


def validate_rcsb_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=RCSB_FAILURE_CODES,
        invalid_code="rcsb_receipt_invalid")


def failed_rcsb_receipt(code, *, source_ref=None):
    return validate_rcsb_receipt(dict(acquired=False, source_ref=source_ref,
        data_ref=None, failure_code=code))


def _receipt_response_failure(value):
    response = value["response"]
    if response["http_status"] is None:
        return "rcsb_transport_metadata_unavailable"
    if not 200 <= response["http_status"] < 300:
        return "rcsb_http_not_success"
    if response["body_complete"] is None or response["observed_body_bytes"] is None:
        return "rcsb_transport_metadata_unavailable"
    if (response["body_complete"] is not True
            or response["retained_bytes"] > value["requested"]["max_bytes"]
            or response["observed_body_bytes"] != response["retained_bytes"]
            or response["declared_body_bytes"] is not None
            and response["declared_body_bytes"] != response["retained_bytes"]):
        return "rcsb_response_incomplete"
    # The legacy DTO also carries transport qualifications that cannot be
    # reconstructed from its projected response fields, such as a bad limit.
    codes = {row["code"] for row in value["issues"]}
    for code in ("http_not_success", "transport_metadata_unavailable", "response_incomplete"):
        if code in codes:
            return "rcsb_" + code
    return None


def rcsb_entry_receipt(legacy):
    """Confirm the literal native entry and requested field availability."""
    value = validate_rcsb_entry_result(legacy)
    failure = _receipt_response_failure(value)
    if failure is None:
        if value["parse_state"] == "decode_failed":
            failure = "rcsb_invalid_native_json"
        elif value["parse_state"] != "object":
            failure = "rcsb_response_not_object"
        else:
            observed = value["observed_identity"]
            if observed["state"] != "present":
                failure = "rcsb_native_entry_id_" + {
                    "missing": "missing", "native_null": "null", "invalid": "invalid"}[observed["state"]]
            elif (observed["native_entry_id"] != value["requested"]["entry_id"]
                    or observed["relation"] != "exact_literal_match"):
                failure = "rcsb_native_entry_id_differs_from_request"
            else:
                for row in value["values"]:
                    if row["state"] not in {"present", "native_null"}:
                        failure = ("rcsb_selected_field_missing" if row["state"] == "missing"
                            else "rcsb_selected_field_unavailable")
                        break
                    if row["field"] == "rcsb_id" and row["value"] != observed["native_entry_id"]:
                        failure = "rcsb_request_conflict"
                        break
    if failure is None and value["issues"]:
        failure = "rcsb_" + value["issues"][0]["code"]
    if failure is not None:
        return failed_rcsb_receipt(failure, source_ref=value["source_ref"])
    return validate_rcsb_receipt(dict(acquired=True, source_ref=value["source_ref"],
        data_ref=value["raw_artifact_ref"], failure_code=None))


def rcsb_file_receipt(legacy):
    """Confirm the selected transfer, without parsing structure identity."""
    value = validate_rcsb_file_result(legacy)
    failure = _receipt_response_failure(value)
    if failure is None and value["issues"]:
        failure = "rcsb_" + value["issues"][0]["code"]
    if failure is not None:
        return failed_rcsb_receipt(failure, source_ref=value["source_ref"])
    return validate_rcsb_receipt(dict(acquired=True, source_ref=value["source_ref"],
        data_ref=value["file"]["artifact_ref"], failure_code=None))


def publish_rcsb_request(registry, operation, arguments, snapshot):
    _require(type(operation) is str and operation in {"public.rcsb.entry", "public.rcsb.file"},
        "rcsb_operation_invalid")
    entry = operation == "public.rcsb.entry"
    arguments = (validate_rcsb_entry_arguments if entry else validate_rcsb_file_arguments)(arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes,
        "rcsb_snapshot_required")
    # Publish actual response custody before a request/identity qualification.
    # accession retains the supplied request label, never a parsed file identity.
    source = registry._source(SERVICE, None, snapshot=snapshot,
        accession=arguments["entry_id"], software_version=None)
    try:
        value = (rcsb_entry_result if entry else rcsb_file_result)(snapshot, arguments=arguments,
            source_ref=source["id"], artifact_ref=source["artifact_ref"])
    except ValueError:
        receipt = failed_rcsb_receipt("rcsb_request_conflict", source_ref=source["id"])
    else:
        receipt = (rcsb_entry_receipt if entry else rcsb_file_receipt)(value)
    return receipt, [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]


__all__ = ["ENTRY_FIELDS", "FILE_FORMATS", "RCSB_ENTRY_ARGUMENTS_SCHEMA", "RCSB_FILE_ARGUMENTS_SCHEMA",
    "RCSB_ENTRY_RESULT_SCHEMA", "RCSB_FILE_RESULT_SCHEMA", "validate_rcsb_entry_arguments", "validate_rcsb_file_arguments",
    "validate_rcsb_entry_result", "validate_rcsb_file_result", "rcsb_entry_result", "rcsb_file_result",
    "RCSB_FAILURE_CODES", "rcsb_receipt_schema", "validate_rcsb_receipt", "failed_rcsb_receipt",
    "rcsb_entry_receipt", "rcsb_file_receipt", "publish_rcsb_request"]
