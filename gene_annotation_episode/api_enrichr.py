"""Finite Enrichr HTTP stages and publication of their retained native table.

The API episode owns selected intents, stage retention and original-action
authentication. This adapter supplies deterministic wire requests and makes one
HTTP call per invocation; it never chooses a retry or calculates enrichment.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import math
from urllib.parse import urlencode, urlsplit

from .acquisition import AcquisitionError, SourceSnapshot
from .api_services import (APIServicePrimitive, event, object_schema,
                           publish_existing_acquisition, validate_value)
from .boundary_validation import parse_json_object
from .enrichr_contracts import (ENRICHR_REQUEST_SCHEMA, ENRICHR_SELECTOR_SCHEMA,
    calculate_enrichr_components, parse_enrichr_response, project_enrichr_return,
    validate_enrichr_request, validate_enrichr_selector)


PREPARED_VERSION = "enrichr_prepared_protocol_v1"
STAGE_VERSION = "enrichr_http_stage_v1"
PROTOCOL_VERSION = "enrichr_protocol_snapshot_v1"
WIRE_PROFILE = "enrichr_direct_http_v1"
EMPTY = object_schema({})
QUERY = "api.enrichr.query"
RESULT = "api.enrichr.result"
_CONFIG_FIELDS = {"kind", "service", "protocol_profile", "base_url", "timeout",
                  "response_byte_limit"}
_PREPARED_FIELDS = {"version", "operation", "request", "configuration",
                    "mutates_remote", "cache_original"}
_STAGE_FIELDS = {"version", "operation", "request", "stage", "stage_code", "http",
                 "prior_response_sha256"}
_HTTP_FIELDS = {"method", "url", "body_base64", "content_type", "accept",
                "timeout_seconds", "response_byte_limit", "follow_redirects"}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError("enrichr_finite_json_required") from error


def _same(left, right):
    return _canonical(left) == _canonical(right)


def _positive(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def validate_enrichr_configuration(configuration):
    """Validate the exact selected API root; no route/default is substituted."""
    _require(type(configuration) is dict and set(configuration) == _CONFIG_FIELDS,
             "enrichr_configuration_invalid")
    _canonical(configuration)
    value = deepcopy(configuration)
    _require(value["kind"] == "api" and value["service"] == "enrichr"
        and value["protocol_profile"] in ("standard_enrichr_v1", "speedrichr_v1")
        and type(value["base_url"]) is str and value["base_url"]
        and value["base_url"] == value["base_url"].strip()
        and not any(character in value["base_url"] for character in "\r\n\t")
        and not value["base_url"].endswith("/")
        and _positive(value["timeout"])
        and type(value["response_byte_limit"]) is int and value["response_byte_limit"] > 0,
        "enrichr_configuration_invalid")
    try:
        address = urlsplit(value["base_url"])
        valid = (address.scheme in ("http", "https") and bool(address.hostname)
            and address.username is None and address.password is None
            and not address.query and not address.fragment)
        address.port
    except ValueError as error:
        raise ValueError("enrichr_configuration_invalid") from error
    _require(valid, "enrichr_configuration_invalid")
    return value


def _prepared(value, *, query_only=False):
    _require(type(value) is dict and set(value) == _PREPARED_FIELDS
        and value["version"] == PREPARED_VERSION and value["operation"] in (QUERY, RESULT),
        "enrichr_prepared_invalid")
    request = validate_enrichr_request(value["request"])
    query = value["operation"] == QUERY
    _require(type(value["mutates_remote"]) is bool and value["mutates_remote"] == query
        and type(value["cache_original"]) is bool and value["cache_original"] != query
        and (not query_only or query), "enrichr_prepared_invalid")
    if query:
        configuration = validate_enrichr_configuration(value["configuration"])
        _require(configuration["protocol_profile"] == request["protocol_profile"],
                 "enrichr_configuration_profile_conflict")
    else:
        _require(value["configuration"] is None, "enrichr_prepared_invalid")
        configuration = None
    return {**deepcopy(value), "request": request, "configuration": configuration}


def _multipart(request):
    """The documented addList multipart fields, with no filename or mapping."""
    boundary = "enrichr-" + hashlib.sha256(_canonical(request)).hexdigest()
    fields = (("list", "\n".join(request["genes"])),
              ("description", request["description"]))
    chunks = []
    for name, value in fields:
        content = value.encode("utf-8")
        _require(("--" + boundary).encode() not in content,
                 "enrichr_multipart_boundary_conflict")
        chunks.append(("--" + boundary + '\r\nContent-Disposition: form-data; name="'
            + name + '"\r\n\r\n').encode() + content + b"\r\n")
    return b"".join(chunks) + ("--" + boundary + "--\r\n").encode(), (
        "multipart/form-data; boundary=" + boundary)


def _native_id(snapshot, key):
    try:
        value = parse_json_object(snapshot.content.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("enrichr_upload_response_invalid_json") from error
    _require(key in value, "enrichr_upload_id_missing")
    native_id = value[key]
    if key == "userListId":
        valid = type(native_id) is int and native_id >= 0
    else:
        valid = type(native_id) is str and bool(native_id)
        if valid:
            try:
                native_id.encode("utf-8")
            except UnicodeError:
                valid = False
    _require(valid, "enrichr_upload_id_invalid")
    return native_id


def _length(prepared):
    return 3 if prepared["request"]["background"]["policy"] == "supplied" else 2


def _stage(prepared, ordinal, prefix):
    request, configuration = prepared["request"], prepared["configuration"]
    base = configuration["base_url"]
    body, content_type = None, None
    if ordinal == 0:
        code, method, url = "query_upload", "POST", base + "/addList"
        body, content_type = _multipart(request)
    elif ordinal == 1 and _length(prepared) == 3:
        code, method, url = "background_upload", "POST", base + "/addbackground"
        body = urlencode({"background": "\n".join(request["background"]["genes"])}).encode()
        content_type = "application/x-www-form-urlencoded"
    else:
        code = "enrichment"
        arguments = {"userListId": _native_id(prefix[0], "userListId")}
        if _length(prepared) == 3:
            arguments["backgroundid"] = _native_id(prefix[1], "backgroundid")
            arguments["backgroundType"] = request["library"]
            method, url = "POST", base + "/backgroundenrich"
            body = urlencode(arguments).encode()
            content_type = "application/x-www-form-urlencoded"
        else:
            arguments["backgroundType"] = request["library"]
            method, url = "GET", base + "/enrich?" + urlencode(arguments)
    return {"version": STAGE_VERSION, "operation": QUERY, "request": deepcopy(request),
        "stage": ordinal, "stage_code": code, "prior_response_sha256": [s.sha256 for s in prefix],
        "http": {"method": method, "url": url,
            "body_base64": base64.b64encode(body).decode("ascii") if body is not None else None,
            "content_type": content_type, "accept": "application/json",
            "timeout_seconds": configuration["timeout"],
            "response_byte_limit": configuration["response_byte_limit"], "follow_redirects": False}}


def _stage_shape(value):
    _require(type(value) is dict and set(value) == _STAGE_FIELDS
        and value["version"] == STAGE_VERSION and value["operation"] == QUERY
        and type(value["stage"]) is int and 0 <= value["stage"] <= 2
        and value["stage_code"] in ("query_upload", "background_upload", "enrichment")
        and type(value["prior_response_sha256"]) is list
        and len(value["prior_response_sha256"]) == value["stage"], "enrichr_stage_invalid")
    validate_enrichr_request(value["request"])
    for digest in value["prior_response_sha256"]:
        _require(type(digest) is str and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest), "enrichr_stage_invalid")
    http = value["http"]
    _require(type(http) is dict and set(http) == _HTTP_FIELDS
        and http["method"] in ("GET", "POST") and type(http["url"]) is str
        and http["accept"] == "application/json" and http["follow_redirects"] is False
        and _positive(http["timeout_seconds"]) and type(http["response_byte_limit"]) is int
        and http["response_byte_limit"] > 0, "enrichr_stage_invalid")
    body = http["body_base64"]
    if body is None:
        _require(http["method"] == "GET" and http["content_type"] is None,
                 "enrichr_stage_invalid")
    else:
        _require(type(body) is str and http["method"] == "POST"
            and type(http["content_type"]) is str and bool(http["content_type"]),
            "enrichr_stage_invalid")
        try:
            base64.b64decode(body, validate=True)
        except (ValueError, TypeError) as error:
            raise ValueError("enrichr_stage_invalid") from error
    _canonical(value)
    return deepcopy(value)


def _response(snapshot, expected, *, intermediate):
    _require(isinstance(snapshot, SourceSnapshot) and snapshot.service == "enrichr"
        and type(snapshot.content) is bytes and _same(snapshot.request, expected)
        and snapshot.url == expected["http"]["url"], "enrichr_stage_response_conflict")
    transport = snapshot.transport
    _require(type(transport) is dict and "enrichr_protocol" not in transport,
             "enrichr_stage_response_conflict")
    wire = transport.get("request")
    http = expected["http"]
    _require(type(wire) is dict and wire.get("method") == http["method"]
        and wire.get("url") == http["url"]
        and _same(transport.get("request_policy"), {"timeout_seconds": http["timeout_seconds"],
                                                  "automatic_redirects": False}),
        "enrichr_stage_transport_conflict")
    headers = wire.get("headers")
    _require(type(headers) is dict and all(type(key) is str for key in headers),
             "enrichr_stage_transport_conflict")
    headers = {key.lower(): value for key, value in headers.items()}
    _require(headers.get("accept") == http["accept"]
        and headers.get("content-type") == http["content_type"],
        "enrichr_stage_transport_conflict")
    if http["body_base64"] is None:
        _require("body_base64" not in wire and "body_sha256" not in wire,
                 "enrichr_stage_transport_conflict")
    else:
        body = base64.b64decode(http["body_base64"], validate=True)
        _require(wire.get("body_base64") == http["body_base64"]
            and wire.get("body_sha256") == hashlib.sha256(body).hexdigest(),
            "enrichr_stage_transport_conflict")
    _require(transport.get("effective_url", http["url"]) == http["url"],
             "enrichr_stage_transport_conflict")
    status = transport.get("status")
    _require(type(status) is int and 200 <= status < 300, "enrichr_stage_http_failed")
    _require(type(transport.get("body_complete")) is bool, "enrichr_stage_capture_state_missing")
    if intermediate:
        _require(transport["body_complete"], "enrichr_intermediate_response_incomplete")


class EnrichrService(APIServicePrimitive):
    service = "enrichr"
    request_schema = ENRICHR_REQUEST_SCHEMA
    selector_schema = ENRICHR_SELECTOR_SCHEMA

    def __init__(self, tool_registry, configuration, *, client=None):
        self.configuration = validate_enrichr_configuration(configuration)
        self.tools = tool_registry
        self.client = client if client is not None else tool_registry.clients

    def validate_request(self, request, scope):
        return validate_enrichr_request(request)

    @staticmethod
    def capabilities():
        return [{"name": QUERY, "description": "Run the assigned finite Enrichr protocol with "
            "literal genes, library, background and identifier policy; retain each actual reply.",
            "input_schema": EMPTY}]

    @staticmethod
    def result_capabilities():
        return [{"name": RESULT, "description": "Publish one selected local row window from the "
            "retained Enrichr response body, preserving native statistics and qualifiers.",
            "input_schema": EMPTY}]

    def launch_catalog(self, request):
        self.validate_request(request, None)
        return self.capabilities()

    def result_catalog(self, request, selector):
        self.validate_request(request, None)
        validate_enrichr_selector(selector)
        return self.result_capabilities()

    def prepare(self, name, request, arguments, *, scope, previous_events,
                handle=None, selector=None):
        request = self.validate_request(request, scope)
        validate_value(arguments, EMPTY, "enrichr_operation_arguments_invalid")
        _require(name in (QUERY, RESULT), "enrichr_operation_not_available")
        if name == QUERY:
            _require(selector is None or selector == {}, "enrichr_launch_selector_not_permitted")
            configuration = self.configuration
            _require(configuration["protocol_profile"] == request["protocol_profile"],
                     "enrichr_configuration_profile_conflict")
        else:
            validate_enrichr_selector(selector)
            configuration = None  # Original configuration comes from retained protocol evidence.
        return _prepared({"version": PREPARED_VERSION, "operation": name,
            "request": request, "configuration": deepcopy(configuration),
            "mutates_remote": name == QUERY, "cache_original": name == RESULT})

    def protocol_length(self, prepared):
        return _length(_prepared(prepared, query_only=True))

    def protocol_request(self, prepared, *, stage, retained_responses):
        prepared = _prepared(prepared, query_only=True)
        _require(type(stage) is int and 0 <= stage < _length(prepared)
            and type(retained_responses) is list and len(retained_responses) == stage,
            "enrichr_protocol_prefix_invalid")
        prefix = []
        for ordinal, snapshot in enumerate(retained_responses):
            expected = _stage(prepared, ordinal, prefix)
            _response(snapshot, expected, intermediate=True)
            # Even background-upload selection requires the actual preceding list ID.
            _native_id(snapshot, "userListId" if ordinal == 0 else "backgroundid")
            prefix.append(snapshot)
        return _stage(prepared, stage, prefix)

    def invoke(self, prepared):
        prepared = _stage_shape(prepared)
        http = prepared["http"]
        body = (base64.b64decode(http["body_base64"], validate=True)
                if http["body_base64"] is not None else None)
        try:
            snapshot = self.client._http("enrichr", http["url"], {}, "application/json",
                body=body, content_type=http["content_type"], accept=http["accept"],
                max_bytes=http["response_byte_limit"], timeout_seconds=http["timeout_seconds"],
                follow_redirects=False)
        except AcquisitionError as error:
            if error.snapshot is None:
                raise
            raise AcquisitionError(error.code, retry_after=error.retry_after, job_ref=error.job_ref,
                snapshot=replace(error.snapshot, request=deepcopy(prepared)), phase=error.phase,
                submission_outcome=error.submission_outcome, diagnostic=error.diagnostic,
                operational=error.operational) from error
        return replace(snapshot, request=deepcopy(prepared))

    def _protocol(self, snapshot, request):
        _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.transport) is dict,
                 "enrichr_protocol_snapshot_required")
        protocol = snapshot.transport.get("enrichr_protocol")
        _require(type(protocol) is dict and set(protocol) == {"version", "wire_profile", "prepared", "stages"}
            and protocol["version"] == PROTOCOL_VERSION and protocol["wire_profile"] == WIRE_PROFILE,
            "enrichr_protocol_snapshot_invalid")
        prepared = _prepared(protocol["prepared"], query_only=True)
        _require(_same(prepared["request"], validate_enrichr_request(request)),
                 "enrichr_protocol_request_conflict")
        stages = protocol["stages"]
        _require(type(stages) is list and len(stages) == _length(prepared),
                 "enrichr_protocol_snapshot_invalid")
        prefix = []
        for ordinal, entry in enumerate(stages):
            _require(type(entry) is dict and set(entry) == {"ordinal", "stage_code", "snapshot"}
                and type(entry["ordinal"]) is int and entry["ordinal"] == ordinal,
                "enrichr_protocol_snapshot_invalid")
            metadata = deepcopy(entry["snapshot"])
            _require(type(metadata) is dict and set(metadata) == {
                "service", "url", "request", "retrieved_at", "media_type", "transport", "content_ref"},
                "enrichr_protocol_snapshot_invalid")
            content_ref = metadata.pop("content_ref")
            raw = SourceSnapshot(content=self.tools.store.get_artifact(content_ref), **metadata)
            _require(content_ref == "artifact_" + raw.sha256, "enrichr_protocol_byte_identity_conflict")
            expected = self.protocol_request(prepared, stage=ordinal, retained_responses=prefix)
            _require(entry["stage_code"] == expected["stage_code"], "enrichr_protocol_stage_conflict")
            _response(raw, expected, intermediate=ordinal < len(stages) - 1)
            prefix.append(raw)
        raw_final = prefix[-1]
        actual = asdict(snapshot)
        actual["transport"].pop("enrichr_protocol")
        original = asdict(raw_final)
        actual_content, original_content = actual.pop("content"), original.pop("content")
        _require(type(actual_content) is bytes and actual_content == original_content
            and _same(actual, original), "enrichr_protocol_final_response_conflict")
        return prepared, raw_final

    def decode(self, prepared, snapshot):
        prepared = _prepared(prepared)
        original, final = self._protocol(snapshot, prepared["request"])
        if prepared["operation"] == QUERY:
            _require(_same(prepared, original), "enrichr_protocol_prepared_conflict")
        return event("response", "completed", native_handle={}, handoff_ready=True,
            result_available=True, facts={"protocol_profile": original["request"]["protocol_profile"],
                "protocol_stage_count": _length(original), "http_status": final.transport["status"],
                "response_complete": final.transport["body_complete"],
                "native_response_retained": True})

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None):
        request = validate_enrichr_request(request)
        selector = validate_enrichr_selector(selector)

        def publisher():
            _, final = self._protocol(snapshot, request)
            media_type = final.transport.get("headers", {}).get("content-type", final.media_type)
            sheet = parse_enrichr_response(final.content, request=request,
                response_complete=final.transport["body_complete"], media_type=media_type)
            components = calculate_enrichr_components(sheet, selector=selector)
            source = self.tools._source("enrichr", {}, snapshot=snapshot,
                tool_grading={"version": "enrichr_grade_v1", "sheet": sheet, "components": components})
            source_ref = source["id"]
            result = {"source_ref": source_ref,
                      **project_enrichr_return(components, source_ref=source_ref)}
            errors = []
            if not sheet["response"]["complete"]:
                errors.append({"code": "response_incomplete"})
            if sheet["response"]["state"] != "decoded":
                errors.append({"code": sheet["response"]["failure_code"]})
            if sheet["table"]["state"] in ("missing", "invalid", "unavailable"):
                errors.append({"code": "native_table_" + sheet["table"]["state"]})
            for row in components["rows"]:
                for code in ("malformed_row", "unexpected_native_width", "invalid_term", "invalid_overlap"):
                    if code in row["qualification_codes"]:
                        errors.append({"code": code, "row_ordinal": row["ordinal"]})
                for name, cell in row["statistics"].items():
                    if cell["state"] in ("invalid", "unrepresentable", "nonfinite"):
                        errors.append({"code": "native_cell_unavailable", "row_ordinal": row["ordinal"],
                                       "field": name})
            if errors:
                result["projection_errors"] = errors
            return result, [source_ref]

        return publish_existing_acquisition(self.tools, "enrichr.result",
            {"request": request, "selector": selector}, snapshot, scope, operation_key,
            publisher=publisher)

    def prepare_observation(self, request, handle, *, scope):
        self.validate_request(request, scope)
        return None
