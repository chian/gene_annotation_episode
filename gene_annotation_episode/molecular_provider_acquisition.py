"""Pure contracts for explicitly selected molecular-provider responses.

Acquisition, original-byte custody and episode permissions belong to the host.
These functions neither invoke clients nor infer biological/scientific scores.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import re
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

from jsonschema import Draft202012Validator, validators

from .acquisition import SourceSnapshot
from .boundary_validation import ModelOutputError, parse_json_value
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from .domain import canonical


VERSION = "molecular_provider_result_v1"
VALUE_VERSION = "molecular_provider_value_v1"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_SERVICES = {"public.string.network": "string", "public.kegg.reaction": "kegg",
    "public.reactome.record": "reactome", "public.quickgo.term": "quickgo",
    "public.pubchem.compound": "pubchem", "public.hpa.gene": "hpa"}
OPERATIONS = tuple(_SERVICES)


def _object(properties):
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}


_LIMIT = {"type": "integer", "minimum": 1, "maximum": MAX_RESPONSE_BYTES}
_ARGUMENTS = {
    "public.string.network": _object({
        "string_ids": {"type": "array", "minItems": 2, "maxItems": 20,
            "uniqueItems": True, "items": {"type": "string",
                "pattern": "^[1-9][0-9]*\\.[A-Za-z0-9_][A-Za-z0-9_.:-]*$"}},
        "taxon_id": {"type": "integer", "minimum": 1},
        "required_score": {"type": "integer", "minimum": 0, "maximum": 1000},
        "max_bytes": deepcopy(_LIMIT)}),
    "public.kegg.reaction": _object({
        "reaction_id": {"type": "string", "pattern": "^R[0-9]{5}$"},
        "max_bytes": deepcopy(_LIMIT)}),
    "public.reactome.record": _object({
        "stable_id": {"type": "string", "pattern": "^R-[A-Z]{3}-[0-9]+$"},
        "max_bytes": deepcopy(_LIMIT)}),
    "public.quickgo.term": _object({
        "term_id": {"type": "string", "pattern": "^GO:[0-9]{7}$"},
        "max_bytes": deepcopy(_LIMIT)}),
    "public.pubchem.compound": _object({
        "cid": {"type": "integer", "minimum": 1},
        "max_bytes": deepcopy(_LIMIT)}),
    "public.hpa.gene": _object({
        "gene_id": {"type": "string", "pattern": "^ENSG[0-9]{11}$"},
        "max_bytes": deepcopy(_LIMIT)}),
}
PROVIDER_ARGUMENTS_SCHEMAS = deepcopy(_ARGUMENTS)
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
        .redefine("integer", lambda _, value: type(value) is int)
        .redefine("number", lambda _, value: type(value) is int
            or type(value) is float and math.isfinite(value)))


def _require(condition, code="molecular_provider_value_invalid"):
    if not condition:
        raise ValueError(code)


def _plain(value):
    """Reject Python-only values before schema validation or JSON coercion."""
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
        raise ValueError("molecular_provider_value_invalid") from error
    return deepcopy(value)


def validate_provider_arguments(operation, value):
    _require(type(operation) is str and operation in _ARGUMENTS,
        "molecular_provider_operation_unknown")
    value = _validated(value, _ARGUMENTS[operation])
    if operation == "public.string.network":
        for identifier in value["string_ids"]:
            _require(re.fullmatch(r"[1-9][0-9]*\.[A-Za-z0-9_][A-Za-z0-9_.:-]*",
                identifier, re.ASCII) is not None)
            _require(identifier.split(".", 1)[0] == str(value["taxon_id"]),
                "molecular_provider_requested_taxon_conflict")
    elif operation != "public.pubchem.compound":
        key = {"public.kegg.reaction": "reaction_id", "public.reactome.record": "stable_id",
            "public.quickgo.term": "term_id", "public.hpa.gene": "gene_id"}[operation]
        _require(re.fullmatch(_ARGUMENTS[operation]["properties"][key]["pattern"],
            value[key], re.ASCII) is not None)
    return value


def provider_request_spec(operation, arguments, *, string_caller_identity=None):
    arguments = validate_provider_arguments(operation, arguments)
    params, media_type = {}, "application/json"
    if operation == "public.string.network":
        _require(type(string_caller_identity) is str and bool(string_caller_identity)
            and string_caller_identity == string_caller_identity.strip()
            and not any(ord(character) < 32 or ord(character) == 127
                for character in string_caller_identity), "string_caller_identity_required")
        string_caller_identity.encode("utf-8")
        url = "https://version-12-5.string-db.org/api/json/network"
        params = {"identifiers": "\r".join(arguments["string_ids"]),
            "species": arguments["taxon_id"], "required_score": arguments["required_score"],
            "network_type": "functional", "add_nodes": 0,
            "caller_identity": string_caller_identity}
    elif operation == "public.kegg.reaction":
        url = "https://rest.kegg.jp/get/rn:" + arguments["reaction_id"]
        media_type = "text/plain"
    elif operation == "public.reactome.record":
        url = "https://reactome.org/ContentService/data/query/" + arguments["stable_id"]
    elif operation == "public.pubchem.compound":
        url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/" + str(arguments["cid"]) + "/JSON"
    elif operation == "public.hpa.gene":
        url = "https://www.proteinatlas.org/" + arguments["gene_id"] + ".json"
    else:
        url = "https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/" + quote(
            arguments["term_id"], safe="")
    return {"service": _SERVICES[operation], "url": url, "params": params,
        "media_type": media_type, "max_bytes": arguments["max_bytes"],
        "follow_redirects": False}


def _request_spec_from_url(operation, arguments, request_url):
    _require(type(request_url) is str, "molecular_provider_snapshot_request_conflict")
    caller = None
    if operation == "public.string.network":
        pairs = parse_qsl(urlsplit(request_url).query, keep_blank_values=True)
        values = [value for key, value in pairs if key == "caller_identity"]
        _require(len(values) == 1, "molecular_provider_snapshot_request_conflict")
        caller = values[0]
    spec = provider_request_spec(operation, arguments, string_caller_identity=caller)
    address = spec["url"] + ("?" + urlencode(spec["params"], doseq=True) if spec["params"] else "")
    _require(request_url == address, "molecular_provider_snapshot_request_conflict")
    return spec


_COUNT = {"type": ["integer", "null"], "minimum": 0}
_RESPONSE = _object({
    "request_url": {"type": "string"},
    "media_type": {"type": "string", "minLength": 1},
    "http_status": {"type": ["integer", "null"], "minimum": 100, "maximum": 599},
    "content_type": {"type": ["string", "null"]},
    "body_complete": {"type": ["boolean", "null"]},
    "retained_bytes": {"type": "integer", "minimum": 0},
    "reported_retained_bytes": deepcopy(_COUNT),
    "observed_body_bytes": deepcopy(_COUNT),
    "declared_body_bytes": deepcopy(_COUNT),
    "response_byte_limit": deepcopy(_COUNT),
    "capture_failure": {"type": ["string", "null"]},
})
_LINE = _object({"line_number": {"type": "integer", "minimum": 1}, "text": {"type": "string"}})
_BLOCK = _object({"field": {"type": ["string", "null"]},
    "lines": {"type": "array", "minItems": 1, "items": _LINE}})
_NATIVE_JSON = {"anyOf": [{"type": "null"}, {"type": "boolean"}, {"type": "number"},
    {"type": "string"}, {"type": "array", "items": {"$ref": "#/$defs/NativeJSON"}},
    {"type": "object", "additionalProperties": {"$ref": "#/$defs/NativeJSON"}}]}
ISSUE_CODES = (
    "transport_metadata_unavailable", "transport_count_conflict", "http_not_success", "http_redirect",
    "response_incomplete", "response_byte_limit_exceeded", "response_capture_failure",
    "content_type_mismatch", "invalid_native_utf8", "invalid_native_json",
    "json_root_not_array", "json_root_not_object", "native_results_missing", "native_results_not_array",
    "native_row_not_object", "native_id_missing", "native_id_invalid", "native_id_differs_from_request",
    "native_taxon_invalid", "native_taxon_differs_from_request", "native_edge_outside_request",
    "kegg_orphan_continuation", "kegg_invalid_field_line", "kegg_entry_count",
    "kegg_terminator_count", "kegg_trailing_data",
)
_ISSUE = _object({"code": {"enum": list(ISSUE_CODES)}, "pointer": {"type": "string"},
    "line_number": {"type": ["integer", "null"], "minimum": 1}})
_RESULT = {"$schema": "https://json-schema.org/draft/2020-12/schema",
    "$defs": {"NativeJSON": _NATIVE_JSON}, **_object({
        "version": {"const": VERSION}, "operation": {"enum": list(OPERATIONS)},
        "service": {"enum": list(_SERVICES.values())},
        "source_ref": {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$",
            "format": "reference", "x-reference-namespace": "source"},
        "raw_artifact_ref": {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$",
            "format": "reference", "x-reference-namespace": "artifact"},
        "requested": {"anyOf": list(deepcopy(_ARGUMENTS).values())}, "response": _RESPONSE,
        "parse_state": {"enum": ["json", "kegg_text", "decode_failed"]},
        "decode_error": {"enum": [None, "invalid_native_utf8", "invalid_native_json"]},
        "representation_state": {"enum": ["complete", "partial", "invalid"]},
        "population_coverage": {"const": "selected_response_only"},
        "native_json": {"$ref": "#/$defs/NativeJSON"},
        "native_text": {"type": ["string", "null"]},
        "native_fields": {"type": "array", "items": _BLOCK},
        "issues": {"type": "array", "uniqueItems": True, "items": _ISSUE},
    })}
_RESULT["allOf"] = [{"if": {"properties": {"operation": {"const": operation}}},
    "then": {"properties": {"requested": deepcopy(schema),
        "service": {"const": _SERVICES[operation]}}}} for operation, schema in _ARGUMENTS.items()]
_RESULT["$id"] = "urn:gene-annotation:molecular-provider:" + hashlib.sha256(
    json.dumps(_RESULT, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

# The private evidence has no invented Source identity. The legacy schema above
# remains literal; a real Source is attached only by its existing public wrapper.
_VALUE = deepcopy(_RESULT)
_VALUE.pop("$id")
_VALUE["properties"].pop("source_ref")
_VALUE["required"].remove("source_ref")
_VALUE["properties"]["version"] = {"const": VALUE_VERSION}
_VALUE["properties"]["observed_transfer"] = _object({
    "declared_body_bytes": {"$ref": "#/$defs/NativeJSON"},
    "body_capture_failure": {"$ref": "#/$defs/NativeJSON"}})
_VALUE["required"].append("observed_transfer")
_VALUE["$id"] = "urn:gene-annotation:molecular-provider-value:" + hashlib.sha256(
    json.dumps(_VALUE, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def provider_result_schema():
    return deepcopy(_RESULT)


def provider_value_schema():
    return deepcopy(_VALUE)


def _issue(code, pointer="", line_number=None):
    return {"code": code, "pointer": pointer, "line_number": line_number}


def _response_issues(operation, response, arguments):
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
    conflicts = []
    if response["reported_retained_bytes"] not in (None, retained):
        conflicts.append("reported_retained_bytes")
    if response["response_byte_limit"] not in (None, arguments["max_bytes"]):
        conflicts.append("response_byte_limit")
    if observed is not None and (observed < retained
            or response["body_complete"] is True and observed != retained):
        conflicts.append("observed_body_bytes")
    if response["body_complete"] is True:
        if observed is None:
            issues.append(_issue("transport_metadata_unavailable", "/response/observed_body_bytes"))
        if declared is not None and declared != retained:
            conflicts.append("declared_body_bytes")
        if response["capture_failure"] is not None:
            conflicts.append("body_complete")
    issues.extend(_issue("transport_count_conflict", "/response/" + key) for key in conflicts)
    if response["capture_failure"] is not None:
        issues.append(_issue("response_capture_failure", "/response/capture_failure"))
    if response["capture_failure"] == "provider_response_byte_limit" or (
            observed is not None and observed > arguments["max_bytes"]):
        issues.append(_issue("response_byte_limit_exceeded", "/response/observed_body_bytes"))
    content_type = response["content_type"]
    if content_type is not None:
        mime = content_type.split(";", 1)[0].strip().lower()
        expected = "text/plain" if operation == "public.kegg.reaction" else "application/json"
        if not (mime == expected or expected == "application/json" and mime.endswith("+json")):
            issues.append(_issue("content_type_mismatch", "/response/content_type"))
    return issues


def _kegg_fields(text):
    blocks, issues = [], []
    # KEGG line identities use CR/LF separators, not Unicode text separators.
    lines = [line for line in re.findall(r"[^\r\n]*(?:\r\n|\r|\n|$)", text) if line]
    for ordinal, original in enumerate(lines, 1):
        line = original.rstrip("\r\n")
        label = line[:12].rstrip(" ")
        item = {"line_number": ordinal, "text": original}
        if line == "///":
            blocks.append({"field": "///", "lines": [item]})
        elif line[:12] == " " * 12 and blocks and blocks[-1]["field"] not in (None, "///"):
            blocks[-1]["lines"].append(item)
        else:
            valid = len(line) >= 12 and re.fullmatch(r"[A-Z][A-Z0-9_]*", label, re.ASCII) is not None
            blocks.append({"field": label if valid else None, "lines": [item]})
            if not valid:
                issues.append(_issue("kegg_orphan_continuation" if line.startswith(" " * 12)
                    else "kegg_invalid_field_line", "/native_text", ordinal))
    return blocks, issues


def _identity_issues(row, key, expected, pointer):
    if key not in row:
        return [_issue("native_id_missing", pointer + "/" + key)]
    value = row[key]
    if type(value) is not str or not value:
        return [_issue("native_id_invalid", pointer + "/" + key)]
    return [] if value == expected else [_issue("native_id_differs_from_request", pointer + "/" + key)]


def _native_json(text):
    native = parse_json_value(text)

    def check_float(token):
        # The shared strict parser rejects overflow but float() can silently
        # turn a nonzero native token into zero. Validate those original tokens
        # without changing the shared model parser or inventing a native value.
        mantissa = token.lower().partition("e")[0]
        _require(float(token) != 0 or not any(character in "123456789" for character in mantissa),
            "molecular_provider_native_number_underflow")
        return None

    json.loads(text, parse_float=check_float, parse_int=lambda _token: None,
        object_pairs_hook=lambda _pairs: None)
    return native


def _native_qualification(operation, arguments, state, decode_error, native, text, fields):
    if state == "decode_failed":
        return "invalid", [_issue(decode_error)]
    issues = []
    if operation == "public.kegg.reaction":
        parsed, issues = _kegg_fields(text)
        _require(fields == parsed)
        entries = [block for block in fields if block["field"] == "ENTRY"]
        ends = [block for block in fields if block["field"] == "///"]
        if len(entries) != 1:
            issues.append(_issue("kegg_entry_count", "/native_fields"))
        for block in entries:
            tokens = block["lines"][0]["text"][12:].split()
            if not tokens:
                issues.append(_issue("native_id_missing", "/native_text", block["lines"][0]["line_number"]))
            elif tokens[0] != arguments["reaction_id"]:
                issues.append(_issue("native_id_differs_from_request", "/native_text",
                    block["lines"][0]["line_number"]))
        if len(ends) != 1:
            issues.append(_issue("kegg_terminator_count", "/native_fields"))
        elif fields[-1]["field"] != "///":
            issues.append(_issue("kegg_trailing_data", "/native_fields"))
        return ("complete" if not issues else "partial" if entries else "invalid"), issues
    expected_array = operation == "public.string.network"
    if not isinstance(native, list if expected_array else dict):
        return "invalid", [_issue("json_root_not_array" if expected_array else "json_root_not_object", "/native_json")]
    if operation == "public.reactome.record":
        issues.extend(_identity_issues(native, "stId", arguments["stable_id"], "/native_json"))
    elif operation == "public.hpa.gene":
        issues.extend(_identity_issues(native, "Ensembl", arguments["gene_id"], "/native_json"))
    elif operation == "public.quickgo.term":
        if "results" not in native:
            return "invalid", [_issue("native_results_missing", "/native_json/results")]
        if type(native["results"]) is not list:
            return "invalid", [_issue("native_results_not_array", "/native_json/results")]
        for index, row in enumerate(native["results"]):
            pointer = "/native_json/results/" + str(index)
            if type(row) is not dict:
                issues.append(_issue("native_row_not_object", pointer))
            else:
                issues.extend(_identity_issues(row, "id", arguments["term_id"], pointer))
    elif operation == "public.pubchem.compound":
        pointer = "/native_json/PC_Compounds"
        if "PC_Compounds" not in native:
            return "invalid", [_issue("native_results_missing", pointer)]
        if type(native["PC_Compounds"]) is not list:
            return "invalid", [_issue("native_results_not_array", pointer)]
        for index, row in enumerate(native["PC_Compounds"]):
            location = pointer + "/" + str(index)
            if type(row) is not dict:
                issues.append(_issue("native_row_not_object", location))
                continue
            owner = row
            for key in ("id", "id", "cid"):
                location += "/" + key
                if key not in owner:
                    issues.append(_issue("native_id_missing", location))
                    break
                value = owner[key]
                if key == "cid":
                    if type(value) is not int or value < 1:
                        issues.append(_issue("native_id_invalid", location))
                    elif value != arguments["cid"]:
                        issues.append(_issue("native_id_differs_from_request", location))
                elif type(value) is not dict:
                    issues.append(_issue("native_id_invalid", location))
                    break
                else:
                    owner = value
    else:
        for index, row in enumerate(native):
            pointer = "/native_json/" + str(index)
            if type(row) is not dict:
                issues.append(_issue("native_row_not_object", pointer))
                continue
            for key in ("stringId_A", "stringId_B"):
                if key not in row:
                    issues.append(_issue("native_id_missing", pointer + "/" + key))
                elif type(row[key]) is not str or not row[key]:
                    issues.append(_issue("native_id_invalid", pointer + "/" + key))
                elif row[key] not in arguments["string_ids"]:
                    issues.append(_issue("native_edge_outside_request", pointer + "/" + key))
            if type(row.get("ncbiTaxonId")) is not int:
                issues.append(_issue("native_taxon_invalid", pointer + "/ncbiTaxonId"))
            elif row["ncbiTaxonId"] != arguments["taxon_id"]:
                issues.append(_issue("native_taxon_differs_from_request", pointer + "/ncbiTaxonId"))
    return ("partial" if issues else "complete"), issues


def _provider_content(operation, snapshot, *, artifact_ref):
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes,
        "molecular_provider_snapshot_invalid")
    arguments = validate_provider_arguments(operation, snapshot.request)
    _require(type(snapshot.transport) is dict, "molecular_provider_transport_invalid")
    transport = snapshot.transport
    request = transport.get("request")
    _require(type(request) is dict and request.get("method") == "GET",
        "molecular_provider_snapshot_request_conflict")
    spec = _request_spec_from_url(operation, arguments, request.get("url"))
    _require(snapshot.service == spec["service"] and snapshot.url in (spec["url"], request["url"]),
        "molecular_provider_snapshot_request_conflict")
    policy = transport.get("request_policy")
    timeout = policy.get("timeout_seconds") if type(policy) is dict else None
    try:
        valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    _require(type(policy) is dict and policy.get("automatic_redirects") is False and valid_timeout,
        "molecular_provider_snapshot_transport_policy_conflict")
    _require(len(snapshot.content) <= arguments["max_bytes"], "molecular_provider_snapshot_byte_limit_conflict")
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(),
        "molecular_provider_artifact_identity_conflict")
    def observed(key, kind, minimum=None, maximum=None):
        value = transport.get(key)
        return value if type(value) is kind and (minimum is None or value >= minimum) and (
            maximum is None or value <= maximum) else None
    headers = transport.get("headers")
    content_type = headers.get("content-type") if type(headers) is dict else None
    response = {"request_url": request["url"], "media_type": snapshot.media_type,
        "http_status": observed("status", int, 100, 599),
        "content_type": content_type if type(content_type) is str else None,
        "body_complete": observed("body_complete", bool), "retained_bytes": len(snapshot.content),
        "reported_retained_bytes": observed("retained_body_bytes", int, 0),
        "observed_body_bytes": observed("observed_body_bytes", int, 0),
        "declared_body_bytes": observed("declared_body_bytes", int, 0),
        "response_byte_limit": observed("response_byte_limit", int, 0),
        "capture_failure": observed("body_capture_failure", str)}
    native, text, fields, decode_error = None, None, [], None
    try:
        decoded = snapshot.content.decode("utf-8")
    except UnicodeError:
        state, decode_error = "decode_failed", "invalid_native_utf8"
    else:
        if operation == "public.kegg.reaction":
            state, text = "kegg_text", decoded
            fields, _ = _kegg_fields(text)
        else:
            try:
                native = _native_json(decoded)
                _plain(native)
            except (ModelOutputError, ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
                state, decode_error, native = "decode_failed", "invalid_native_json", None
            else:
                state = "json"
    representation, native_issues = _native_qualification(operation, arguments, state,
        decode_error, native, text, fields)
    return {"operation": operation,
        "service": spec["service"], "raw_artifact_ref": artifact_ref,
        "requested": arguments, "response": response, "parse_state": state,
        "decode_error": decode_error, "representation_state": representation,
        "population_coverage": "selected_response_only", "native_json": native,
        "native_text": text, "native_fields": fields,
        "issues": _response_issues(operation, response, arguments) + native_issues}


def provider_value(operation, snapshot, *, artifact_ref):
    content = _provider_content(operation, snapshot, artifact_ref=artifact_ref)
    return validate_provider_value({"version": VALUE_VERSION, **content,
        "observed_transfer": {key: deepcopy(snapshot.transport.get(key)) for key in
            ("declared_body_bytes", "body_capture_failure")}})


def _validate_provider_content(value):
    operation = value["operation"]
    arguments = validate_provider_arguments(operation, value["requested"])
    _request_spec_from_url(operation, arguments, value["response"]["request_url"])
    if (operation == "public.hpa.gene" and value["response"]["http_status"] == 200
            and value["response"]["body_complete"] is True):
        _require(value["response"]["media_type"] == "application/json",
            "molecular_provider_snapshot_request_conflict")
    _require(re.fullmatch(r"artifact_[a-f0-9]{64}", value["raw_artifact_ref"], re.ASCII) is not None)
    _require(value["response"]["retained_bytes"] <= arguments["max_bytes"])
    state = value["parse_state"]
    if state == "decode_failed":
        _require(value["decode_error"] is not None and value["native_json"] is None
            and value["native_text"] is None and not value["native_fields"])
        _require(operation != "public.kegg.reaction" or value["decode_error"] == "invalid_native_utf8")
    elif operation == "public.kegg.reaction":
        _require(state == "kegg_text" and value["decode_error"] is None
            and value["native_json"] is None and type(value["native_text"]) is str)
        _require(len(value["native_text"].encode("utf-8")) == value["response"]["retained_bytes"])
        _require("artifact_" + hashlib.sha256(value["native_text"].encode("utf-8")).hexdigest()
            == value["raw_artifact_ref"], "molecular_provider_artifact_identity_conflict")
    else:
        _require(state == "json" and value["decode_error"] is None
            and value["native_text"] is None and not value["native_fields"])
    representation, native_issues = _native_qualification(operation, arguments, state,
        value["decode_error"], value["native_json"], value["native_text"], value["native_fields"])
    _require(value["representation_state"] == representation)
    _require(value["issues"] == _response_issues(operation, value["response"], arguments) + native_issues)
    return value


def validate_provider_value(value):
    value = _validate_provider_content(_validated(value, _VALUE))
    for raw_key, response_key, kind in (("declared_body_bytes", "declared_body_bytes", int),
            ("body_capture_failure", "capture_failure", str)):
        observed = value["observed_transfer"][raw_key]
        expected = observed if type(observed) is kind and (kind is not int or observed >= 0) else None
        _require(canonical(value["response"][response_key]) == canonical(expected))
    return value


def validate_provider_result(value):
    value = _validated(value, _RESULT)
    _require(re.fullmatch(r"source_[a-f0-9]{24,64}", value["source_ref"], re.ASCII) is not None)
    return _validate_provider_content(value)


def provider_result_from_value(value, *, source_ref):
    value = validate_provider_value(value)
    value.pop("observed_transfer")
    value.update(version=VERSION, source_ref=source_ref)
    return validate_provider_result(value)


def provider_result(operation, snapshot, *, source_ref, artifact_ref):
    content = _provider_content(operation, snapshot, artifact_ref=artifact_ref)
    return validate_provider_result({"version": VERSION, "source_ref": source_ref, **content})


PROVIDER_FAILURE_CODES = tuple("molecular_provider_" + code for code in ISSUE_CODES) + (
    "molecular_provider_request_conflict", "molecular_provider_selected_request_conflict",
    "molecular_provider_empty_lookup", "invalid_tool_input", "data_acquisition_failed",
    "data_acquisition_publication_incomplete")


def provider_receipt_schema():
    return acquisition_receipt_schema(failure_codes=PROVIDER_FAILURE_CODES)


def validate_provider_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=PROVIDER_FAILURE_CODES,
        invalid_code="molecular_provider_receipt_invalid")


def failed_provider_receipt(code, *, source_ref=None):
    return validate_provider_receipt(dict(acquired=False, source_ref=source_ref,
        data_ref=None, failure_code=code))


def _receipt_response_failure(value):
    response, arguments = value["response"], value["requested"]
    status = response["http_status"]
    if status is None:
        return "transport_metadata_unavailable"
    if not 200 <= status < 300:
        return "http_redirect" if 300 <= status < 400 else "http_not_success"
    if value["operation"] == "public.hpa.gene" and status != 200:
        return "http_not_success"
    if response["body_complete"] is not True:
        return "response_incomplete"
    declared, capture_failure = (value["observed_transfer"][key] for key in
        ("declared_body_bytes", "body_capture_failure"))
    if (declared is not None and (type(declared) is not int or declared < 0)
            or capture_failure is not None and type(capture_failure) is not str):
        return "transport_metadata_unavailable"
    if any(response[key] is None for key in (
            "reported_retained_bytes", "observed_body_bytes", "response_byte_limit")):
        return "transport_metadata_unavailable"
    if response["capture_failure"] is not None:
        return ("response_byte_limit_exceeded" if response["capture_failure"] == "provider_response_byte_limit"
            else "response_capture_failure")
    count = response["retained_bytes"]
    if (response["reported_retained_bytes"] != count or response["observed_body_bytes"] != count
            or response["declared_body_bytes"] not in (None, count)
            or response["response_byte_limit"] != arguments["max_bytes"]):
        return "transport_count_conflict"
    if count > arguments["max_bytes"]:
        return "response_byte_limit_exceeded"
    return None


def _receipt_native_failure(value):
    operation, arguments, native = value["operation"], value["requested"], value["native_json"]
    # This invokes the same native identity/parser authority as the legacy DTO.
    # MIME is a retained qualification, not an identity or transfer assertion.
    _, issues = _native_qualification(operation, arguments, value["parse_state"],
        value["decode_error"], native, value["native_text"], value["native_fields"])
    for issue in issues:
        if operation == "public.string.network" and issue["code"] == "native_taxon_invalid":
            index = int(issue["pointer"].split("/")[2])
            taxon = native[index].get("ncbiTaxonId")
            if type(taxon) is str and taxon == str(arguments["taxon_id"]):
                continue
        return issue["code"]
    if operation == "public.quickgo.term" and not native["results"]:
        return "empty_lookup"
    if operation == "public.pubchem.compound" and not native["PC_Compounds"]:
        return "empty_lookup"
    return None


def provider_receipt(value, *, source_ref):
    """Confirm the requested acquisition, retaining native qualifications separately."""
    value = validate_provider_value(value)
    failure = _receipt_response_failure(value) or _receipt_native_failure(value)
    if failure is not None:
        return failed_provider_receipt("molecular_provider_" + failure, source_ref=source_ref)
    return validate_provider_receipt(dict(acquired=True, source_ref=source_ref,
        data_ref=value["raw_artifact_ref"], failure_code=None))


def _failure_witness(snapshot, failure_code):
    schema = _object({"version": {"const": "molecular_provider_failure_witness_v1"},
        "observed_snapshot_service": {"type": "string"},
        "observed_snapshot_url": {"type": "string"},
        "failure_code": {"enum": list(PROVIDER_FAILURE_CODES)}})
    return _validated(dict(version="molecular_provider_failure_witness_v1",
        observed_snapshot_service=snapshot.service, observed_snapshot_url=snapshot.url,
        failure_code=failure_code), schema)


def publish_molecular_provider_request(registry, operation, arguments, snapshot):
    """Retain the literal response and private Value before publishing its confirmation."""
    arguments = validate_provider_arguments(operation, arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes,
        "molecular_provider_snapshot_invalid")
    artifact_ref = "artifact_" + hashlib.sha256(snapshot.content).hexdigest()
    value, failure, auxiliary = None, None, []
    try:
        value = provider_value(operation, snapshot, artifact_ref=artifact_ref)
    except ValueError:
        failure = "molecular_provider_request_conflict"
        auxiliary.append(registry.store.artifact(canonical(_failure_witness(snapshot, failure)),
            "application/json"))
    else:
        auxiliary.append(registry.store.artifact(canonical(value), "application/json"))
        if canonical(value["requested"]) != canonical(arguments):
            failure = "molecular_provider_selected_request_conflict"
    # A full wire URI is substituted only after both observed and selected
    # requests authenticate. A contradiction keeps the literal captured URI.
    captured = (replace(snapshot, url=value["response"]["request_url"])
        if value is not None and failure is None else snapshot)
    observed = snapshot.request if type(snapshot.request) is dict else {}
    key = {"public.kegg.reaction": "reaction_id", "public.reactome.record": "stable_id",
        "public.quickgo.term": "term_id"}.get(operation)
    accession = observed.get(key) if key is not None else None
    if operation == "public.pubchem.compound" and type(observed.get("cid")) is int and observed["cid"] > 0:
        accession = str(observed["cid"])
    if operation == "public.hpa.gene":
        accession = (value["native_json"]["Ensembl"] if value is not None and failure is None
            and _receipt_response_failure(value) is None and _receipt_native_failure(value) is None
            else None)
    if type(accession) is not str:
        accession = None
    source = registry._source(_SERVICES[operation], None, snapshot=captured,
        accession=accession, software_version=None, auxiliary_artifact_refs=auxiliary)
    _require(source["artifact_ref"] == artifact_ref, "molecular_provider_artifact_identity_conflict")
    receipt = (failed_provider_receipt(failure, source_ref=source["id"]) if failure else
        provider_receipt(value, source_ref=source["id"]))
    return receipt, [source["id"], *([artifact_ref] if receipt["acquired"] else [])]


__all__ = ["VERSION", "VALUE_VERSION", "MAX_RESPONSE_BYTES", "OPERATIONS", "PROVIDER_ARGUMENTS_SCHEMAS",
    "validate_provider_arguments", "provider_request_spec", "provider_result",
    "validate_provider_result", "provider_result_schema", "provider_value", "validate_provider_value",
    "provider_value_schema", "provider_result_from_value", "PROVIDER_FAILURE_CODES", "provider_receipt_schema",
    "validate_provider_receipt", "failed_provider_receipt", "provider_receipt", "publish_molecular_provider_request"]
