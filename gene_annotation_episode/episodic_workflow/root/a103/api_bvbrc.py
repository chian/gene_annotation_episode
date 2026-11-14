"""Selected BV-BRC public data requests; no private workflow or target inference.

The Data API returns a page immediately. It has no remote job to submit or poll.
BV-BRC's computational AppService is a different, authenticated interface and is
not advertised by this provider. Its official endpoint was observed rejecting a
request without an authorization header; that does not make jobs available here.

Protocol: https://www.bv-brc.org/api/doc/
Implementation: https://github.com/BV-BRC/BV-BRC-API
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import re
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from .acquisition import AcquisitionError, SourceSnapshot
from .bvbrc_data_query import DATA_QUERY_SCHEMA, encode_native_query, validate_data_query
from .bvbrc_data_schema import schema as data_schema
from .domain import ContractError, canonical, identity, obj, validate_schema


SERVICE = "bvbrc_data"
DEFAULT_BASE_URL = "https://www.bv-brc.org/api"
COLLECTIONS = ("genome", "genome_feature", "protein_family_ref")
FIELD = {"type": "string", "pattern": r"^[A-Za-z_][A-Za-z0-9_]*$"}
SCALAR = {"type": ["string", "number", "boolean"]}
FILTER = obj({
    "field": FIELD,
    "operator": {"enum": ["eq", "ne", "gt", "lt", "in"]},
    "value": {"type": ["string", "number", "boolean", "array"],
              "items": SCALAR, "minItems": 1},
})
SORT = obj({"field": FIELD, "direction": {"enum": ["asc", "desc"]}})
REQUEST_SCHEMA = obj({
    "collection": {"enum": list(COLLECTIONS)},
    "filters": {"type": "array", "items": FILTER},
    "fields": {"type": "array", "items": FIELD, "uniqueItems": True},
    "sort": {"type": "array", "items": SORT},
    "limit": {"type": "integer", "minimum": 1, "default": 25},
    "offset": {"type": "integer", "minimum": 0, "default": 0},
}, required=["collection", "filters"])
SELECTOR_SCHEMA = obj({
    "offset": {"type": "integer", "minimum": 0},
    "limit": {"type": "integer", "minimum": 1},
}, required=[])
EMPTY_ARGUMENTS = obj({})
QUERY_OPERATION = "api.bvbrc.query"
RESULT_OPERATION = "api.bvbrc.result"
DATA_QUERY_OPERATION = "api.bvbrc.data.query"
DATA_RESULT_OPERATION = "api.bvbrc.data.result"
_CONTENT_RANGE = re.compile(r"^items\s+(\d+)-(\d+)/(\d+|\*)$", re.I)
_SECRET_HEADERS = {"authorization", "proxy-authorization", "cookie", "set-cookie"}


def _embedded_schema(definition: dict) -> dict:
    """Expand local references before nesting under a host assignment schema.

    A JSON Pointer beginning at ``#`` resolves against the outer document, not
    a nested schema's own $defs. These finite records have no recursive types.
    """
    definitions = definition.get("$defs", {})

    def expand(value):
        if isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                if not reference.startswith("#/$defs/"):
                    raise ValueError("bvbrc_nonlocal_schema_reference")
                return expand(definitions[reference.removeprefix("#/$defs/")])
            return {key: expand(child) for key, child in value.items()
                    if key not in {"$defs", "$schema"}}
        if isinstance(value, list):
            return [expand(child) for child in value]
        return value

    return expand(definition)


def _data_request(request) -> bool:
    return isinstance(request, dict) and request.get("version") == "bvbrc_data_request_v2"


def _validated_request(request: dict) -> dict:
    validate_schema(request, REQUEST_SCHEMA)
    for condition in request["filters"]:
        operator, value = condition["operator"], condition["value"]
        if (operator == "in") != isinstance(value, list):
            raise ContractError("bvbrc_filter_value_shape_mismatch")
        if operator in {"gt", "lt"} and type(value) is bool:
            raise ContractError("bvbrc_ordered_filter_requires_number_or_string")
    # Original assignments retain omission semantics; defaults belong to the
    # actual prepared native request rather than rewriting the commission.
    return deepcopy(request)


def _effective_request(request: dict, selector: dict | None = None) -> dict:
    result = _validated_request(request)
    result.setdefault("fields", [])
    result.setdefault("sort", [])
    result.setdefault("offset", 0)
    result.setdefault("limit", 25)
    if selector is not None:
        validate_schema(selector, SELECTOR_SCHEMA)
        result.update(deepcopy(selector))
    return result


def _base_url(value: str) -> str:
    if not isinstance(value, str):
        raise ContractError("bvbrc_invalid_base_url")
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment):
        raise ContractError("bvbrc_invalid_base_url")
    return value.rstrip("/")


def _literal(value: Any) -> str:
    text = ("true" if value else "false") if type(value) is bool else str(value)
    return urllib.parse.quote(text, safe="")


def request_url(base_url: str, request: dict) -> str:
    """Encode fields/values, retaining actual RQL operator delimiters."""
    request = _effective_request(request)
    expressions = []
    for condition in request["filters"]:
        field, operator, value = (condition[key] for key in ("field", "operator", "value"))
        operand = "(" + ",".join(_literal(item) for item in value) + ")" if operator == "in" else _literal(value)
        expressions.append(f"{operator}({urllib.parse.quote(field, safe='')},{operand})")
    if request["fields"]:
        expressions.append("select(" + ",".join(request["fields"]) + ")")
    if request["sort"]:
        expressions.append("sort(" + ",".join(
            ("+" if item["direction"] == "asc" else "-") + item["field"]
            for item in request["sort"]) + ")")
    expressions.append(f"limit({request['limit']},{request['offset']})")
    return _base_url(base_url) + "/" + request["collection"] + "/?" + "&".join(expressions)


def _header_items(headers) -> list[list[str]]:
    return [[name, "<redacted>" if name.lower() in _SECRET_HEADERS else value]
            for name, value in (headers or {}).items()]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


class BVBRCDataClient:
    """One explicit public GET per query, with no retry or pagination loop."""

    def __init__(self, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 90):
        self.base_url = _base_url(base_url)
        if (type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0):
            raise ContractError("bvbrc_invalid_timeout")
        self.timeout = timeout

    def query(self, request: dict) -> SourceSnapshot:
        request = _effective_request(request)
        address = request_url(self.base_url, request)
        headers = {"User-Agent": "gene-annotation-episode/0.2", "Accept": "application/json"}
        return self._query_once(request, address, headers)

    def query_prepared(self, prepared: dict) -> SourceSnapshot:
        """Execute the selected, persisted v2 GET without compiling another query.

        The host owns preparation and recovery. This method sends one request;
        it neither selects a query nor retries, follows redirects or pages.
        """
        from .bvbrc_data_schema import validate
        prepared = validate('PreparedQuery', prepared)
        native = prepared['native_request']
        address = native['url']
        expected_prefix = self.base_url + '/' + prepared['effective_request']['collection'] + '/?'
        if (prepared['query_population']['base_url'] != self.base_url
                or not address.startswith(expected_prefix)
                or urllib.parse.urlsplit(address).fragment):
            raise ContractError('bvbrc_prepared_endpoint_conflict')
        headers = {item['name']: item['value'] for item in native['headers']}
        if len(headers) != len(native['headers']):
            raise ContractError('bvbrc_prepared_header_conflict')
        return self._query_once(prepared['effective_request'], address, headers,
            prepared_native=native)

    def _query_once(self, request, address, headers, *, prepared_native=None):
        native_request = urllib.request.Request(address, headers=headers, method='GET')
        recorded_request = {"method": "GET", "url": address, "headers": deepcopy(headers)}
        if prepared_native is not None:
            recorded_request['body'] = prepared_native['body']
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(native_request, timeout=self.timeout) as response:
                items = _header_items(response.headers)
                transport = {"status": response.status, "headers": {k.lower(): v for k, v in items},
                    "header_items": items, "effective_url": response.geturl(),
                    "request": deepcopy(recorded_request),
                    "representation": "http_response_bytes", "automatic_redirects": False}
                try:
                    content = response.read()
                except Exception as error:
                    transport.update(body_complete=False, body_capture_error=type(error).__name__)
                    snapshot = SourceSnapshot(SERVICE, address, request,
                        datetime.now(timezone.utc).isoformat(), getattr(error, "partial", b""),
                        response.headers.get("content-type", "application/octet-stream"), transport)
                    raise AcquisitionError("provider_response_body_incomplete", snapshot=snapshot,
                        phase="http_response") from error
                transport['body_complete'] = True
                return SourceSnapshot(SERVICE, address, request,
                    datetime.now(timezone.utc).isoformat(), content,
                    response.headers.get("content-type", "application/octet-stream"), transport)
        except urllib.error.HTTPError as error:
            items = _header_items(error.headers)
            transport = {"status": error.code, "headers": {k.lower(): v for k, v in items},
                "header_items": items, "effective_url": error.geturl(),
                "request": deepcopy(recorded_request),
                "representation": "http_error_response_bytes", "automatic_redirects": False,
                "body_complete": True}
            try:
                content = error.read()
            except Exception as capture_error:
                content = getattr(capture_error, "partial", b"")
                transport.update(body_complete=False, body_capture_error=type(capture_error).__name__)
            finally:
                error.close()
            snapshot = SourceSnapshot(SERVICE, address, request,
                datetime.now(timezone.utc).isoformat(), content,
                (error.headers or {}).get("content-type", "application/octet-stream"), transport)
            delay = (error.headers or {}).get("retry-after")
            raise AcquisitionError("provider_redirect_not_followed" if 300 <= error.code < 400
                else "provider_http_" + str(error.code), snapshot=snapshot, phase="http_response",
                retry_after=float(delay) if delay and delay.isdigit() else None) from error
        except (urllib.error.URLError, TimeoutError) as error:
            timeout = isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError)
            reason = getattr(error, "reason", error)
            raise AcquisitionError("provider_request_timeout" if timeout
                else "provider_connection_failed", phase="http_request",
                diagnostic={"exception_type": type(error).__name__,
                    "reason_type": type(reason).__name__, "message": str(reason)}) from error


def _headers(snapshot: SourceSnapshot) -> dict:
    values = {}
    for source in (snapshot.transport, snapshot.transport.get("response", {})):
        for key, value in source.get("header_items", []):
            values[key.lower()] = value
        for key, value in source.get("headers", {}).items():
            values[key.lower()] = value
    return values


def _parse(snapshot: SourceSnapshot, request: dict) -> tuple[list[dict], dict]:
    if snapshot.service != SERVICE:
        raise ContractError("bvbrc_response_service_mismatch")
    if canonical(_effective_request(snapshot.request)) != canonical(_effective_request(request)):
        raise ContractError("bvbrc_response_request_mismatch")
    if snapshot.transport.get("body_complete") is False:
        raise ContractError("bvbrc_response_body_incomplete")
    status = snapshot.transport.get("status", snapshot.transport.get("response", {}).get("status"))
    if type(status) is int and status >= 300:
        raise ContractError("provider_http_" + str(status))
    try:
        rows = json.loads(snapshot.content)
        canonical(rows)
    except (ValueError, UnicodeDecodeError) as error:
        raise ContractError("bvbrc_invalid_json_response") from error
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ContractError("bvbrc_expected_native_row_array")
    headers = _headers(snapshot)
    native_range = headers.get("content-range")
    match = _CONTENT_RANGE.fullmatch(native_range) if isinstance(native_range, str) else None
    total = int(match[3]) if match is not None and match[3] != "*" else None
    offset, limit = request["offset"], request["limit"]
    # The observed server sent "items 0-2/..." for TWO rows. Do not interpret
    # that range end as inclusive or use it to skip the next actual row.
    next_offset = offset + len(rows) if rows and (total is None or offset + len(rows) < total) else None
    page = {"collection": request["collection"], "requested_offset": offset,
        "requested_limit": limit, "returned_count": len(rows), "content_range": native_range,
        "reported_total": total, "next_offset": next_offset,
        "observed_at": snapshot.retrieved_at, "http_status": status}
    return rows, page


class BVBRCDataService:
    service = SERVICE
    request_schema = {"oneOf": [deepcopy(REQUEST_SCHEMA), _embedded_schema(DATA_QUERY_SCHEMA)]}
    selector_schema = {"oneOf": [deepcopy(SELECTOR_SCHEMA), _embedded_schema(data_schema("ResultSelector"))]}

    def __init__(self, tool_registry, configuration=None, *, client=None):
        self.tools = tool_registry
        configuration = dict(configuration or {})
        if set(configuration) - {"kind", "service", "base_url", "timeout"}:
            raise ContractError("bvbrc_unsupported_configuration")
        if configuration.get("kind", "api") != "api" or configuration.get("service", SERVICE) != SERVICE:
            raise ContractError("bvbrc_configuration_service_mismatch")
        self.configuration = configuration
        # Validate configuration even when a test/caller supplies a transport.
        default_client = BVBRCDataClient(base_url=configuration.get("base_url", DEFAULT_BASE_URL),
            timeout=configuration.get("timeout", 90))
        self.client = default_client if client is None else client

    def validate_request(self, request, scope):
        if self.tools is not None and scope is not None:
            self.tools.store.validate_scope(scope)
        return validate_data_query(request) if _data_request(request) else _validated_request(request)

    def capabilities(self):
        return [{"name": QUERY_OPERATION,
            "description": "Retrieve one assigned public BV-BRC genome, feature or protein-family data page. Preserve its native subjects and source labels; no target-function judgment or remote job is created.",
            "input_schema": deepcopy(EMPTY_ARGUMENTS)},
            {"name": DATA_QUERY_OPERATION,
            "description": "Execute one assigned typed BV-BRC Data API v2 page, count or field-facet GET. Preserve the exact native request, complete response and population qualifications; no remote job or automatic next page is created.",
            "input_schema": deepcopy(EMPTY_ARGUMENTS)}]

    def launch_catalog(self, request):
        if _data_request(request):
            validate_data_query(request)
            name = DATA_QUERY_OPERATION
        else:
            _validated_request(request)
            name = QUERY_OPERATION
        return [row for row in self.capabilities() if row["name"] == name]

    def result_catalog(self, request, selector):
        if _data_request(request):
            from .bvbrc_data_views import validate_data_result_selector
            validate_data_result_selector(selector, request=request)
            name = DATA_RESULT_OPERATION
        else:
            _effective_request(request, selector)
            name = RESULT_OPERATION
        return [row for row in self.result_capabilities() if row["name"] == name]

    @staticmethod
    def result_capabilities():
        """Declared selected-page operation without inventing a data query."""
        return [{"name": RESULT_OPERATION,
            "description": "Acquire the selected BV-BRC page under the original filters and fields. Reuse the actual initial response for that same page; a different offset or limit makes one new request.",
            "input_schema": deepcopy(EMPTY_ARGUMENTS)},
            {"name": DATA_RESULT_OPERATION,
            "description": "Retain the assigned BV-BRC v2 result and its complete numerical sheet, deterministic components and explicitly selected supplied-page joins. Reuse the original native request's response; only an explicit changed row page makes one GET.",
            "input_schema": deepcopy(EMPTY_ARGUMENTS)}]

    def prepare(self, name, request, arguments, *, scope, previous_events,
                handle=None, selector=None):
        original = self.validate_request(request, scope)
        validate_schema(arguments, EMPTY_ARGUMENTS)
        if name not in {QUERY_OPERATION, RESULT_OPERATION, DATA_QUERY_OPERATION, DATA_RESULT_OPERATION}:
            raise ContractError("bvbrc_unknown_operation")
        if _data_request(original) != (name in {DATA_QUERY_OPERATION, DATA_RESULT_OPERATION}):
            raise ContractError("bvbrc_operation_request_version_conflict")
        if handle not in (None, {}):
            raise ContractError("bvbrc_data_has_no_remote_job_handle")
        if _data_request(original):
            page = None
            if name == DATA_RESULT_OPERATION:
                from .bvbrc_data_views import validate_data_result_selector
                page = validate_data_result_selector(selector, request=original)["page"]
            endpoint = self.configuration.get("base_url", DEFAULT_BASE_URL)
            prepared_query = encode_native_query(original, base_url=endpoint, page_selector=page)
            result = {"operation": name, "mutates_remote": False,
                "request": deepcopy(prepared_query["effective_request"]), "prepared_query": prepared_query}
            if name == DATA_RESULT_OPERATION:
                original_query = (prepared_query if page is None else
                    encode_native_query(original, base_url=endpoint))
                result["cache_original"] = (canonical(prepared_query["native_request"])
                    == canonical(original_query["native_request"]))
            return result
        effective = _effective_request(original, selector if name == RESULT_OPERATION else None)
        result = {"operation": name, "mutates_remote": False, "request": effective}
        if name == RESULT_OPERATION:
            result["cache_original"] = canonical(effective) == canonical(_effective_request(original))
        return result

    def invoke(self, prepared):
        if prepared.get("cache_original"):
            raise ContractError("bvbrc_original_response_required")
        if prepared.get("operation") in {DATA_QUERY_OPERATION, DATA_RESULT_OPERATION}:
            return self.client.query_prepared(prepared["prepared_query"])
        return self.client.query(prepared["request"])

    def decode(self, prepared, snapshot):
        event = {"kind": "response", "state": "failed", "native_handle": {},
            "handoff_ready": False, "result_available": False, "facts": {}, "failure_code": None}
        if snapshot is None:
            event["failure_code"] = "bvbrc_response_required"
            return event
        if prepared.get("operation") in {DATA_QUERY_OPERATION, DATA_RESULT_OPERATION}:
            from .bvbrc_data_readers import parse_data_snapshot
            parsed = parse_data_snapshot(snapshot, prepared=prepared["prepared_query"])
            sheet = parsed["sheet"]
            # State describes the immediate native operation. Its independent
            # parse/projection qualifications do not invent a remote job state.
            event.update(state="completed" if sheet is not None else "failed",
                handoff_ready=sheet is not None,
                result_available=sheet is not None or prepared["operation"] == DATA_RESULT_OPERATION,
                failure_code=parsed["failures"][0]["code"] if parsed["failures"] else None,
                facts={"collection": prepared["request"]["collection"],
                    "mode": prepared["request"]["mode"], "parse_status": parsed["status"],
                    "qualification": None if sheet is None else sheet["qualification"],
                    "page": None if sheet is None else sheet["page"]})
            return event
        try:
            _, page = _parse(snapshot, prepared["request"])
        except ContractError as error:
            event["failure_code"] = str(error)
            return event
        event.update(state="completed", handoff_ready=True, result_available=True, facts=page)
        return event

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None, publication_inputs=None):
        original = self.validate_request(request, scope)
        if _data_request(original):
            from .bvbrc_data_publication import publish_bvbrc_data
            if handle not in (None, {}):
                raise ContractError("bvbrc_data_has_no_remote_job_handle")
            if isinstance(publication_inputs, dict) and isinstance(publication_inputs.get("prepared"), dict):
                population = publication_inputs["prepared"].get("query_population")
                if isinstance(population, dict) and population.get("base_url") != _base_url(
                        self.configuration.get("base_url", DEFAULT_BASE_URL)):
                    raise ContractError("bvbrc_prepared_endpoint_conflict")
            return publish_bvbrc_data(self.tools, request=original, selector=selector,
                snapshot=snapshot, publication_inputs=publication_inputs, scope=scope,
                operation_key=operation_key)
        effective = _effective_request(original, selector)
        rows, page = _parse(snapshot, effective)
        store = self.tools.store
        with store.transaction():
            artifact = store.artifact(snapshot.content, snapshot.media_type)
            request_ref = store.artifact(canonical({"request": snapshot.request,
                "transport": snapshot.transport}), "application/json")
            body = {"provider": SERVICE, "accession": None, "uri": snapshot.url,
                "artifact_ref": artifact, "text_ref": None, "request_ref": request_ref,
                "version": None, "retrieved_at": snapshot.retrieved_at}
            source_ref = identity("source", {"origin": "external", "record": body})
            try:
                store.get(source_ref)
                existed = True
            except ContractError as error:
                if str(error) != "unknown_reference":
                    raise
                existed = False
            source = store.put("source", body, origin="external")
        # These are the source's rows, including native feature/genome identities,
        # missing fields and coordinates. No target observation is inferred.
        return {"status": "completed", "operation_ref": identity("operation", {
            "key": operation_key, "service": SERVICE, "request": effective,
            "snapshot_sha256": snapshot.sha256}),
            "record_refs": [source["id"]], "changed_record_refs": [] if existed else [source["id"]],
            "result": {"source_ref": source["id"], "raw_artifact_ref": artifact,
                "collection": effective["collection"], "rows": rows, "pagination": page},
            "feedback": None}

    def prepare_observation(self, request, handle, *, scope):
        self.validate_request(request, scope)
        if handle not in (None, {}):
            raise ContractError("bvbrc_data_has_no_remote_job_handle")
        return None
