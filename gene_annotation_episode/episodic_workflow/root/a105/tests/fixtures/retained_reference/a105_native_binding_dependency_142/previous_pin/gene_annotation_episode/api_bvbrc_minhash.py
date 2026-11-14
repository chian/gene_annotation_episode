"""Selected direct Minhash RPC and publication of its original response.

Tools do tasks. Episodes are problem solving processes. This primitive makes
one selected native call; the existing API executor owns its intent, receipt,
recovery and requested return. No job, polling loop or metadata acquisition is
invented for an immediate response. Numerical readers and calculators remain
separate, and publication replay preserves their original saved outputs.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json

from .acquisition import SourceSnapshot
from .api_services import event, publish_existing_acquisition
from .bvbrc_analysis_protocol import decode_rpc_response, prepare_rpc_request
from .bvbrc_analysis_transport import BVBRCAnalysisClient, SERVICE as TRANSPORT_SERVICE
from .bvbrc_minhash_grader import (
    METHODS, calculate_minhash_components, parse_minhash_result,
)
from .domain import ContractError, canonical, identity, obj, validate_schema
from .tool_grading_artifacts import retain_tool_grading


SERVICE = "bvbrc_minhash"
GRADING_SCHEMA = "bvbrc_minhash_grading_v1"
LAUNCH_OPERATIONS = {mode: "api.bvbrc.minhash." + mode for mode in METHODS}
RESULT_OPERATION = "api.bvbrc.minhash.result"
NATIVE_ARGUMENTS = (
    "query", "max_pvalue", "max_distance", "max_hits", "include_reference",
    "include_representative", "bacterial", "viral",
)
REQUEST_SCHEMA = obj({
    "mode": {"enum": ["genome", "fasta"]},
    "query": {"type": "string", "minLength": 1},
    "max_pvalue": {"type": "number", "minimum": 0, "maximum": 1},
    "max_distance": {"type": "number", "minimum": 0, "maximum": 1},
    "max_hits": {"type": "integer", "minimum": 0},
    **{field: {"type": "integer"} for field in NATIVE_ARGUMENTS[4:]},
})
EMPTY = obj({})


def _request(request):
    validate_schema(request, REQUEST_SCHEMA)
    # C1 validates original native numeric types and exact argument arity.
    # The assigned FASTA operand is a Workspace path, not a UUID or local file.
    if request["mode"] == "fasta":
        path = request["query"]
        parts = path.split("/")
        if (not path.startswith("/") or len(parts) < 4
                or any(part in ("", ".", "..") for part in parts[1:])
                or any(char in path for char in "\r\n\x00")):
            raise ContractError("bvbrc_minhash_workspace_fasta_path_required")
    rpc = prepare_rpc_request(METHODS[request["mode"]],
        [request[field] for field in NATIVE_ARGUMENTS],
        request_id=identity("minhash_rpc", request))
    return deepcopy(request), rpc


def _rpc_bytes(request):
    # This is the transport's exact deterministic JSON encoding, checked
    # against its recorded sent-body digest before retaining these bytes.
    return json.dumps(request, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


class BVBRCMinhashService:
    service = SERVICE
    request_schema = deepcopy(REQUEST_SCHEMA)
    selector_schema = deepcopy(EMPTY)

    def __init__(self, tool_registry, configuration=None, *, client=None):
        if not isinstance(configuration, dict):
            raise ContractError("bvbrc_minhash_configuration_required")
        allowed = {"kind", "service", "endpoint", "timeout", "authorization_env",
                   "authorization_origins"}
        if (set(configuration) - allowed or "endpoint" not in configuration
                or configuration.get("kind", "api") != "api"
                or configuration.get("service", SERVICE) != SERVICE):
            raise ContractError("bvbrc_minhash_configuration_invalid")
        # Validate endpoint, timeout and authorization configuration even when
        # a test/caller supplies the primitive client. Construction sends nothing.
        configured = BVBRCAnalysisClient({"Minhash": configuration["endpoint"]},
            timeout=configuration.get("timeout", 90),
            authorization_env=configuration.get("authorization_env"),
            authorization_origins=configuration.get("authorization_origins", ()))
        self.tools = tool_registry
        self.configuration = deepcopy(configuration)
        self.client = configured if client is None else client

    def validate_request(self, request, scope):
        original, _ = _request(request)
        if scope is not None:
            self.tools.store.validate_scope(scope)
        return original

    @staticmethod
    def capabilities():
        return [{"name": LAUNCH_OPERATIONS[mode], "description":
            "Execute the assigned direct BV-BRC Minhash " + mode + " distance RPC once. "
            "Preserve all eight supplied native arguments and the complete immediate response; "
            "the correlation ID is not a remote idempotency key and no AppService job is created.",
            "input_schema": deepcopy(EMPTY)} for mode in METHODS]

    def launch_catalog(self, request):
        original = self.validate_request(request, None)
        return [row for row in self.capabilities()
                if row["name"] == LAUNCH_OPERATIONS[original["mode"]]]

    def result_catalog(self, request, selector):
        self.validate_request(request, None)
        validate_schema(selector, self.selector_schema)
        return self.result_capabilities()

    @staticmethod
    def result_capabilities():
        return [{"name": RESULT_OPERATION, "description":
            "Publish the original retained BV-BRC Minhash response with its complete numerical "
            "sheet and deterministic components. No new RPC or metadata request is made. Native "
            "distance, p-value and shared-hash fraction retain their meanings; distance/p-value "
            "recomputation requires separately received actual metadata and remains unavailable here.",
            "input_schema": deepcopy(EMPTY)}]

    def prepare(self, name, request, arguments, *, scope, previous_events,
                handle=None, selector=None):
        original = self.validate_request(request, scope)
        _, rpc = _request(original)
        validate_schema(arguments, EMPTY)
        if handle not in (None, {}):
            raise ContractError("bvbrc_minhash_has_no_remote_job_handle")
        if name not in {LAUNCH_OPERATIONS[original["mode"]], RESULT_OPERATION}:
            raise ContractError("bvbrc_minhash_operation_not_available")
        result = name == RESULT_OPERATION
        if result or selector is not None:
            validate_schema(selector, self.selector_schema)
        return {"operation": name, "request": original, "rpc_request": rpc,
            "mutates_remote": not result, "cache_original": result}

    def _prepared(self, prepared):
        if not isinstance(prepared, dict):
            raise ContractError("bvbrc_minhash_prepared_request_required")
        expected = self.prepare(prepared.get("operation"), prepared.get("request"), {},
            scope=None, previous_events=[], selector=(
                {} if prepared.get("operation") == RESULT_OPERATION else None))
        if canonical(prepared) != canonical(expected):
            raise ContractError("bvbrc_minhash_prepared_request_conflict")
        return expected

    def invoke(self, prepared):
        prepared = self._prepared(prepared)
        if prepared["cache_original"]:
            raise ContractError("bvbrc_minhash_original_response_required")
        return self.client.rpc(prepared["rpc_request"])

    def _native_response(self, prepared, snapshot):
        prepared = self._prepared(prepared)
        if not isinstance(snapshot, SourceSnapshot):
            raise ContractError("bvbrc_minhash_response_required")
        if snapshot.service != TRANSPORT_SERVICE:
            raise ContractError("bvbrc_minhash_response_service_mismatch")
        if (not isinstance(snapshot.request, dict) or snapshot.request.get("kind") != "rpc"
                or set(snapshot.request) != {"kind", "rpc"}):
            raise ContractError("bvbrc_minhash_rpc_response_required")
        rpc = prepared["rpc_request"]
        if canonical(snapshot.request["rpc"]) != canonical(rpc):
            raise ContractError("bvbrc_minhash_response_request_mismatch")
        if snapshot.url != self.configuration["endpoint"]:
            raise ContractError("bvbrc_minhash_response_endpoint_mismatch")
        transport = snapshot.transport
        if not isinstance(transport, dict) or transport.get("body_complete") is not True:
            raise ContractError("bvbrc_minhash_response_body_incomplete")
        sent = transport.get("request")
        native_bytes = _rpc_bytes(rpc)
        if (not isinstance(sent, dict) or sent.get("method") != "POST"
                or sent.get("url") != snapshot.url
                or type(sent.get("body_bytes")) is not int
                or sent["body_bytes"] != len(native_bytes)
                or sent.get("body_sha256") != hashlib.sha256(native_bytes).hexdigest()):
            raise ContractError("bvbrc_minhash_transport_request_mismatch")
        decoded = decode_rpc_response(snapshot.content, method=rpc["method"],
            request_id=rpc["id"], http_status=transport.get("status"))
        if decoded["status"] != "ok":
            raise ContractError(decoded["diagnostics"][0]["code"],
                detail={"diagnostics": decoded["diagnostics"]})
        if not isinstance(decoded["value"], list):
            raise ContractError("bvbrc_minhash_native_result_array_required")
        return decoded["value"]

    def decode(self, prepared, snapshot):
        try:
            value = self._native_response(prepared, snapshot)
        except (ValueError, KeyError, TypeError) as error:
            return event("response", "failed", native_handle={}, failure_code=str(error))
        return event("response", "completed", native_handle={}, handoff_ready=True,
            result_available=True, facts={"mode": prepared["request"]["mode"],
                "returned_row_count": len(value), "population_size": None, "truncated": None})

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None):
        prepared = self.prepare(RESULT_OPERATION, request, {}, scope=scope,
            previous_events=[], handle=handle, selector=selector)
        if not isinstance(snapshot, SourceSnapshot):
            raise ContractError("bvbrc_minhash_response_required")
        # Include response metadata absent from the generic publication key.
        # The helper checks replay BEFORE this callback can parse or calculate.
        arguments = {"request": prepared["request"], "rpc_request": prepared["rpc_request"],
            "selector": {}, "response": {"service": snapshot.service, "url": snapshot.url,
                "retrieved_at": snapshot.retrieved_at, "media_type": snapshot.media_type}}

        def publish_original():
            value = self._native_response(prepared, snapshot)
            parsed = parse_minhash_result(value, mode=prepared["request"]["mode"],
                request=prepared["rpc_request"], provenance={"service": snapshot.service,
                    "url": snapshot.url, "retrieved_at": snapshot.retrieved_at,
                    "response_sha256": snapshot.sha256})
            grading = {"schema": GRADING_SCHEMA, "request": prepared["request"],
                "rpc_request": prepared["rpc_request"], "selector": {},
                "parse_status": parsed["status"], "sheet": parsed["sheet"],
                "components": calculate_minhash_components(parsed["sheet"]),
                "diagnostics": parsed["diagnostics"]}
            store = self.tools.store
            raw_ref = store.artifact(snapshot.content, snapshot.media_type)
            snapshot_record = asdict(snapshot)
            snapshot_record.pop("content")
            snapshot_record.update(content_ref=raw_ref, sha256=snapshot.sha256,
                rpc_request_artifact_ref=store.artifact(
                    _rpc_bytes(prepared["rpc_request"]), "application/json"))
            request_ref = store.artifact(canonical(snapshot_record), "application/json")
            grading_ref = retain_tool_grading(store, provider=SERVICE,
                native_artifact_ref=raw_ref, grading=grading)
            source = store.put("source", {"provider": SERVICE, "accession": None,
                "uri": snapshot.url, "artifact_ref": raw_ref, "text_ref": None,
                "request_ref": request_ref, "version": None,
                "retrieved_at": snapshot.retrieved_at,
                "auxiliary_artifact_refs": [grading_ref]}, origin="external")
            self.tools._written.append(source["id"])
            result = {"source_ref": source["id"], "raw_artifact_ref": raw_ref,
                "grading_artifact_ref": grading_ref, "parse_status": parsed["status"]}
            if parsed["status"] != "ok":
                result["projection_errors"] = [deepcopy(issue) for issue in parsed["diagnostics"]
                    if issue["severity"] == "error"]
            return result, [source["id"]]

        return publish_existing_acquisition(self.tools, RESULT_OPERATION, arguments,
            snapshot, scope, operation_key, publisher=publish_original)

    def prepare_observation(self, request, handle, *, scope):
        self.validate_request(request, scope)
        if handle not in (None, {}):
            raise ContractError("bvbrc_minhash_has_no_remote_job_handle")
        return None


__all__ = ["BVBRCMinhashService", "SERVICE", "GRADING_SCHEMA", "REQUEST_SCHEMA",
           "LAUNCH_OPERATIONS", "RESULT_OPERATION"]
