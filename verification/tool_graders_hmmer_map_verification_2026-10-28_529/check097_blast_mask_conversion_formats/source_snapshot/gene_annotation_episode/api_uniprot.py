"""One selected UniProt record or result page; no automatic pagination."""
from __future__ import annotations

from copy import deepcopy

from .api_services import (event, object_schema, publish_existing_acquisition,
                           validate_service_configuration, validate_value)
from .uniprot_native import normalize_query_uniprot, parse_uniprot_native


TEXT = {"type": "string", "minLength": 1}
SIZE = {"type": "integer", "minimum": 1, "maximum": 500}
EMPTY = object_schema({})


def uniprot_page_metadata(parsed):
    """Existing page-result keys projected from the already parsed page."""
    page = parsed["page"]
    return {"next_cursor": page["next_cursor"], "total_results": page["total_results"]["value"],
            "release": page["release"]["value"], "release_date": page["release_date"]["value"],
            "pagination_metadata_available": page["pagination_metadata_available"]}


def parse_uniprot_snapshot(snapshot, *, request):
    """Validate actual response custody before applying the pure native reader.

    The native parser receives a caller-supplied request. It cannot establish
    that the transport actually used that request; this adapter checks that
    separate relationship, without guessing missing request operands/status.
    """
    if snapshot is None or snapshot.service != "uniprot":
        raise ValueError("uniprot_response_required")
    if not isinstance(snapshot.request, dict):
        raise ValueError("uniprot_response_request_required")
    expected = {key: value for key, value in request.items() if key != "operation"}
    for key in ("accession", "query", "size", "cursor"):
        if key in expected and key not in snapshot.request:
            raise ValueError("uniprot_response_request_missing_" + key)
        if key in snapshot.request and (key not in expected or
                type(snapshot.request[key]) is not type(expected[key]) or
                snapshot.request[key] != expected[key]):
            raise ValueError("uniprot_response_request_conflict_" + key)
    if (set(snapshot.request) - (set(expected) | {"format"}) or
            snapshot.request.get("format", "json") != "json"):
        raise ValueError("uniprot_response_request_invalid")
    transport = snapshot.transport
    if not isinstance(transport, dict):
        raise ValueError("uniprot_response_transport_invalid")
    response = transport.get("response")
    if response is not None and not isinstance(response, dict):
        raise ValueError("uniprot_response_transport_invalid")
    response = response or {}
    for status in (transport.get("status"), response.get("status")):
        if status is not None and (type(status) is not int or not 200 <= status < 300):
            raise ValueError("uniprot_http_response_not_successful")
    if response.get("request_method") not in (None, "GET"):
        raise ValueError("uniprot_response_request_method_conflict")
    headers = response.get("headers", transport.get("headers"))
    if headers is not None and not isinstance(headers, dict):
        raise ValueError("uniprot_response_headers_invalid")
    return parse_uniprot_native(snapshot.content, request=request, response_headers=headers)


class UniProtService:
    service = "uniprot"
    request_schema = object_schema({"operation": {"enum": ["record", "search", "query_uniprot"]},
        "accession": TEXT, "query": TEXT, "size": SIZE, "cursor": TEXT,
        "endpoint": TEXT, "max_results": {"anyOf": [SIZE, {"type": "null"}]}}, ["operation"])
    selector_schema = object_schema({"cursor": TEXT, "size": SIZE})

    def __init__(self, tool_registry, configuration=None, *, client=None):
        self.configuration = validate_service_configuration(self.service, configuration or {})
        self.tools = tool_registry
        self.client = client if client is not None else tool_registry.clients

    def validate_request(self, request, scope):
        request = validate_value(request, self.request_schema, "uniprot_request_invalid")
        operation = request["operation"]
        required = {"operation", {"record": "accession", "search": "query",
                                  "query_uniprot": "endpoint"}[operation]}
        allowed = required | ({"size", "cursor"} if operation == "search" else
                              {"max_results"} if operation == "query_uniprot" else set())
        if not required <= set(request) or set(request) - allowed:
            raise ValueError("uniprot_request_fields_conflict")
        for name in ("accession", "query", "cursor"):
            if name in request and not request[name].strip():
                raise ValueError("uniprot_request_invalid")
        if operation == "query_uniprot":
            normalize_query_uniprot(request["endpoint"], max_results=request.get("max_results"))
        if scope is not None:
            self.tools.store.validate_scope(scope)
        return request

    @staticmethod
    def _canonical_request(request):
        if request["operation"] == "query_uniprot":
            return normalize_query_uniprot(request["endpoint"],
                                           max_results=request.get("max_results"))
        return {**deepcopy(request), **({"size": request.get("size", 10)}
                                     if request["operation"] == "search" else {})}

    @staticmethod
    def _launch_name(request):
        return ("query_uniprot" if request["operation"] == "query_uniprot"
                else "api.uniprot." + request["operation"])

    def _selector(self, request, selector):
        selector = validate_value(selector or {}, self.selector_schema, "uniprot_selector_invalid")
        if self._canonical_request(request)["operation"] == "record" and selector:
            raise ValueError("uniprot_record_selector_must_be_empty")
        if "cursor" in selector and not selector["cursor"].strip():
            raise ValueError("uniprot_selector_invalid")
        return selector

    def capabilities(self):
        records = [{"name": "api.uniprot." + operation,
                 "description": "Obtain the assigned UniProt record or one assigned search page. "
                    "Retain the actual reference subjects, native response and returned continuation.",
                 "input_schema": EMPTY} for operation in ("record", "search")]
        records.append({"name": "query_uniprot", "description":
            "Retrieve the assigned UniProtKB JSON record or one selected JSON search page "
            "from its explicit endpoint, retaining complete native data and source associations.",
            "input_schema": EMPTY, "instructions":
            "Commission this operation through the configured UniProt API resource with "
            "request.operation=query_uniprot and the original endpoint. Endpoint and optional "
            "max_results are immutable service-request operands; the selected action has empty "
            "arguments. Supported endpoints are /uniprotkb/{accession} (optionally .json or "
            "format=json) and /uniprotkb/search?query=... with optional size, cursor and "
            "format=json; relative paths and https://rest.uniprot.org are accepted. A supplied "
            "max_results of 1..500 selects a search page size and must agree with any URL size. "
            "Omission or null leaves the explicit URL size or the existing default of 10. "
            "A record endpoint accepts no non-null max_results. Preserve the exact accession, "
            "decoded query and opaque cursor. Each selection makes one existing client call; "
            "api.uniprot.collect with an empty selector publishes its retained response, and "
            "an explicit cursor/size selector requests one page of that same query. Invalid "
            "rows and field issues remain visible alongside valid native rows. Source "
            "annotations describe the retrieved entries, not the investigated target. "
            "Other datasets, formats, parameters, streaming and ID mapping are unsupported "
            "in this contract; no natural-language query generation or page traversal is provided."})
        return records

    def launch_catalog(self, request):
        request = self.validate_request(request, None)
        return [row for row in self.capabilities()
                if row["name"] == self._launch_name(request)]

    def result_catalog(self, request, selector):
        request = self.validate_request(request, None)
        self._selector(request, selector)
        return self.result_capabilities()

    @staticmethod
    def result_capabilities():
        """Declared result acquisition; this neither selects nor reads a page."""
        return [{"name": "api.uniprot.collect", "description":
            "Publish the retained original UniProt response, or obtain the explicitly selected "
            "cursor page of the original query. No automatic page traversal or target annotation.",
            "input_schema": EMPTY}]

    def prepare(self, name, request, arguments, *, scope, previous_events,
                handle=None, selector=None):
        request = self.validate_request(request, scope)
        validate_value(arguments, EMPTY, "uniprot_operation_arguments_invalid")
        selector = self._selector(request, selector)
        if name not in {self._launch_name(request), "api.uniprot.collect"}:
            raise ValueError("uniprot_operation_not_available")
        if name != "api.uniprot.collect" and selector:
            raise ValueError("uniprot_launch_selector_not_permitted")
        canonical = self._canonical_request(request)
        native = {key: value for key, value in canonical.items() if key != "operation"}
        native.update(selector)
        return {"operation": name, "mutates_remote": False, "request": request,
                "native_operation": canonical["operation"], "native_arguments": native,
                "cache_original": name == "api.uniprot.collect" and not selector}

    def invoke(self, prepared):
        if prepared.get("cache_original"):
            raise ValueError("uniprot_cached_result_requires_retained_response")
        function = (self.client.uniprot_record if prepared["native_operation"] == "record"
                    else self.client.uniprot_search)
        return function(**prepared["native_arguments"])

    def decode(self, prepared, snapshot):
        parsed = parse_uniprot_snapshot(snapshot, request={"operation": prepared["native_operation"],
                                                        **prepared["native_arguments"]})
        page = parsed["page"]
        if page["projection_state"] == "invalid" or (
                prepared["native_operation"] == "record" and not parsed["records"]):
            code = next((issue["code"] for issue in parsed["issues"]
                         if issue["effect"] in {"page_unusable", "record_unpublishable"}),
                        "response_invalid")
            raise ValueError("uniprot_" + code)
        if prepared["native_operation"] == "search":
            facts = {"returned_count": page["native_record_count"], **uniprot_page_metadata(parsed)}
        else:
            facts = {"returned_count": 1,
                     "accession": parsed["records"][0]["identity"]["primary_accession"]}
        facts.update(projection_state=page["projection_state"],
                     projection_issues=deepcopy(parsed["issues"]),
                     http_status=snapshot.transport.get("status",
                         (snapshot.transport.get("response") or {}).get("status")))
        return event("response", "completed", native_handle={}, handoff_ready=True,
                     result_available=True, facts=facts)

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None):
        prepared = self.prepare("api.uniprot.collect", request, {}, scope=scope,
                                previous_events=[], selector=selector)
        self.decode(prepared, snapshot)
        return publish_existing_acquisition(self.tools,
            "public.uniprot." + prepared["native_operation"], prepared["native_arguments"],
            snapshot, scope, operation_key)

    def prepare_observation(self, request, handle, *, scope):
        self.validate_request(request, scope)
        return None
