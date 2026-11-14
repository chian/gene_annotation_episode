"""One selected UniProt record or result page; no automatic pagination."""
from __future__ import annotations

import json

from .acquisition import uniprot_pagination
from .api_services import (event, object_schema, publish_existing_acquisition,
                           validate_service_configuration, validate_value)


TEXT = {"type": "string", "minLength": 1}
SIZE = {"type": "integer", "minimum": 1, "maximum": 500}
EMPTY = object_schema({})


class UniProtService:
    service = "uniprot"
    request_schema = object_schema({"operation": {"enum": ["record", "search"]},
        "accession": TEXT, "query": TEXT, "size": SIZE, "cursor": TEXT}, ["operation"])
    selector_schema = object_schema({"cursor": TEXT, "size": SIZE})

    def __init__(self, tool_registry, configuration=None, *, client=None):
        self.configuration = validate_service_configuration(self.service, configuration or {})
        self.tools = tool_registry
        self.client = client if client is not None else tool_registry.clients

    def validate_request(self, request, scope):
        request = validate_value(request, self.request_schema, "uniprot_request_invalid")
        operation = request["operation"]
        required = {"operation", "accession"} if operation == "record" else {"operation", "query"}
        allowed = required if operation == "record" else required | {"size", "cursor"}
        if not required <= set(request) or set(request) - allowed:
            raise ValueError("uniprot_request_fields_conflict")
        for name in ("accession", "query", "cursor"):
            if name in request and not request[name].strip():
                raise ValueError("uniprot_request_invalid")
        if scope is not None:
            self.tools.store.validate_scope(scope)
        return request

    def _selector(self, request, selector):
        selector = validate_value(selector or {}, self.selector_schema, "uniprot_selector_invalid")
        if request["operation"] == "record" and selector:
            raise ValueError("uniprot_record_selector_must_be_empty")
        if "cursor" in selector and not selector["cursor"].strip():
            raise ValueError("uniprot_selector_invalid")
        return selector

    def capabilities(self):
        return [{"name": "api.uniprot." + operation,
                 "description": "Obtain the assigned UniProt record or one assigned search page. "
                    "Retain the actual reference subjects, native response and returned continuation.",
                 "input_schema": EMPTY} for operation in ("record", "search")]

    def launch_catalog(self, request):
        request = self.validate_request(request, None)
        return [row for row in self.capabilities()
                if row["name"] == "api.uniprot." + request["operation"]]

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
        if name not in {"api.uniprot." + request["operation"], "api.uniprot.collect"}:
            raise ValueError("uniprot_operation_not_available")
        if name != "api.uniprot.collect" and selector:
            raise ValueError("uniprot_launch_selector_not_permitted")
        native = ({"accession": request["accession"]} if request["operation"] == "record" else
                  {"query": request["query"], "size": request.get("size", 10),
                   **({"cursor": request["cursor"]} if "cursor" in request else {})})
        native.update(selector)
        return {"operation": name, "mutates_remote": False, "request": request,
                "native_operation": request["operation"], "native_arguments": native,
                "cache_original": name == "api.uniprot.collect" and not selector}

    def invoke(self, prepared):
        if prepared.get("cache_original"):
            raise ValueError("uniprot_cached_result_requires_retained_response")
        function = (self.client.uniprot_record if prepared["native_operation"] == "record"
                    else self.client.uniprot_search)
        return function(**prepared["native_arguments"])

    def decode(self, prepared, snapshot):
        if snapshot is None or snapshot.service != "uniprot":
            raise ValueError("uniprot_response_required")
        status = snapshot.transport.get("status", snapshot.transport.get("response", {}).get("status"))
        if status is not None and (type(status) is not int or not 200 <= status < 300):
            raise ValueError("uniprot_http_response_not_successful")
        for key in ("accession", "query", "size", "cursor"):
            if key in snapshot.request and snapshot.request[key] != prepared["native_arguments"].get(key):
                raise ValueError("uniprot_response_request_conflict_" + key)
        body = json.loads(snapshot.content)
        if not isinstance(body, dict):
            raise ValueError("uniprot_response_invalid")
        if prepared["native_operation"] == "search":
            rows = body.get("results")
            if not isinstance(rows, list):
                raise ValueError("uniprot_search_results_required")
            facts = {"returned_count": len(rows), **uniprot_pagination(snapshot)}
        else:
            accession = body.get("primaryAccession")
            if not isinstance(accession, str) or not accession:
                raise ValueError("uniprot_record_accession_required")
            facts = {"returned_count": 1, "accession": accession}
        return event("response", "completed", native_handle={}, handoff_ready=True,
                     result_available=True, facts=facts)

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None):
        prepared = self.prepare("api.uniprot.collect", request, {}, scope=scope,
                                previous_events=[], selector=selector)
        self.decode(prepared, snapshot)
        return publish_existing_acquisition(self.tools,
            "public.uniprot." + request["operation"], prepared["native_arguments"],
            snapshot, scope, operation_key)

    def prepare_observation(self, request, handle, *, scope):
        self.validate_request(request, scope)
        return None
