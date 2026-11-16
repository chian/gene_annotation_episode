"""Original AppService publication-input validation and callback handoff."""
from __future__ import annotations

from .acquisition import SourceSnapshot
from .bvbrc_analysis_transport import SERVICE as TRANSPORT_SERVICE
from .bvbrc_appservice_contracts import download_request, validate_contract
from .bvbrc_appservice_service_values import _check, _same, _digest

class AppServicePublicationValidation:
    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None, publication_inputs=None):
        original = self.validate_request(request, scope)
        selector = validate_contract("ResultSelector", selector)
        inputs = validate_contract("PublicationInputs", publication_inputs)
        _check(_same(inputs["request"], original) and _same(inputs["selector"], selector),
               "publication_dependency_conflict")
        _check(isinstance(snapshot, SourceSnapshot) and snapshot.service == TRANSPORT_SERVICE
               and type(snapshot.request) is dict
               and snapshot.request.get("kind") == "download"
               and _same(snapshot.request.get("requested_byte_range"), inputs["current_operation"]["arguments"]["byte_range"])
               and "max_bytes" in snapshot.request and _same(snapshot.request["max_bytes"],
                    inputs["current_operation"]["arguments"]["max_bytes"]),
               "publication_dependency_conflict")
        current = inputs["current_snapshot"]
        content = current["content"]
        selected = current["selected_operands"]
        operation = inputs["current_operation"]
        _check(set(selected) == {"operation", "request_sha256", "arguments_sha256", "native_operands"}
               and selected["operation"] == operation["name"]
               and selected["request_sha256"] == _digest(original)
               and selected["arguments_sha256"] == _digest(operation["arguments"]),
               "publication_dependency_conflict")
        native = selected["native_operands"]
        _check(type(native) is dict and set(native) == {"request", "arguments", "selector", "call", "local_failure"}
               and _same(native["request"], original) and _same(native["selector"], selector)
               and _same(native["arguments"], operation["arguments"])
               and native["local_failure"] is None, "publication_dependency_conflict")
        call = native["call"]
        _check(_same(snapshot.request, download_request(call, arguments=operation["arguments"]))
               and snapshot.url == call["url"], "publication_dependency_conflict")
        _check(content["sha256"] == snapshot.sha256 and content["byte_count"] == len(snapshot.content)
               and current["retrieved_at"] == snapshot.retrieved_at
               and current["media_type"] == snapshot.media_type
               and _same(current["transport"], snapshot.transport), "publication_dependency_conflict")
        _check(self.publication_callback is not None, "appservice_publication_unbound")
        return self.publication_callback(snapshot, publication_inputs=inputs, operation_key=operation_key)


