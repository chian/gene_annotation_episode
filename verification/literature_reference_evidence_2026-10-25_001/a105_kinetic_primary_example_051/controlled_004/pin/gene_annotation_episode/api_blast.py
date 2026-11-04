"""Individually selected NCBI BLAST requests and native result publication.

No operation runs RemoteSearches.search/collect, sleeps, polls or resubmits.
"""
from __future__ import annotations

import hashlib
import re

from . import blast_search as blast
from .acquisition import AcquisitionError
from .api_services import (event, object_schema, publish_existing_acquisition,
                           validate_service_configuration, validate_value)


TEXT = {"type": "string", "minLength": 1}
EMPTY = object_schema({})


class NCBIBlastService:
    service = "ncbi_blast"
    request_schema = object_schema({"subject_ref": TEXT,
        "program": {"enum": list(blast.PROGRAM_UNITS)}, "database": TEXT,
        "hitlist_size": {"type": "integer", "minimum": 1}},
        ["subject_ref", "program", "database"])
    selector_schema = EMPTY

    def __init__(self, tool_registry, configuration=None, *, client=None):
        self.configuration = validate_service_configuration(self.service, configuration or {})
        self.tools = tool_registry
        self.client = client if client is not None else tool_registry.clients

    def validate_request(self, request, scope):
        request = validate_value(request, self.request_schema, "blast_request_invalid")
        if not request["database"].strip():
            raise ValueError("blast_database_required")
        if scope is not None:
            self._operand(request, scope)
        return request

    def _operand(self, request, scope):
        row = self.tools._check_sequence_operand(request["subject_ref"], scope)
        model = "protein" if blast.PROGRAM_UNITS[request["program"]][0] == "aa" else "dna"
        sequence = self.tools._sequence(row["id"], molecule_model=model)
        return row["id"], sequence

    @staticmethod
    def _handle(handle):
        if (not isinstance(handle, dict) or not isinstance(handle.get("rid"), str)
                or re.fullmatch(r"[A-Za-z0-9_-]+", handle["rid"]) is None):
            raise ValueError("blast_original_handle_required")
        return dict(handle)

    def capabilities(self):
        return [{"name": "api.blast." + operation, "description": description,
                 "input_schema": EMPTY,
                 "configuration": {"ncbi_contact_configured": bool(getattr(self.client, "ncbi_email", None)),
                    "provider_rate_state_configured": getattr(self.client, "access_dir", None) is not None}}
                for operation, description in (
            ("prepare", "Resolve and validate the assigned BLAST sequence and settings locally. No HTTP request."),
            ("submit", "Submit the original assigned BLAST search once and retain its native RID/RTOE response."),
            ("status", "Obtain one status response for the original BLAST RID. No waiting or polling loop."))]

    def launch_catalog(self, request):
        self.validate_request(request, None)
        return self.capabilities()

    def result_catalog(self, request, selector):
        self.validate_request(request, None)
        validate_value(selector or {}, EMPTY, "blast_result_selector_must_be_empty")
        return self.result_capabilities()

    @staticmethod
    def result_capabilities():
        """Native result contracts, independent of a submitted query."""
        return [{"name": "api.blast.status", "description":
            "Observe the original RID once to decide whether result retrieval is useful. "
            "This response supplies protocol status, not scientific result rows.",
            "input_schema": EMPTY},
            {"name": "api.blast.fetch", "description":
            "Fetch one native JSON2 result response for the original RID. Preserve all native "
            "HSP scores and subjects; this does not assign function or poll for readiness.",
            "input_schema": EMPTY}]

    def prepare(self, name, request, arguments, *, scope, previous_events,
                handle=None, selector=None):
        request = self.validate_request(request, scope)
        validate_value(arguments, EMPTY, "blast_operation_arguments_invalid")
        validate_value(selector or {}, EMPTY, "blast_result_selector_must_be_empty")
        operation = name.removeprefix("api.blast.")
        if name != "api.blast." + operation or operation not in {"prepare", "submit", "status", "fetch"}:
            raise ValueError("blast_operation_not_available")
        subject, sequence = self._operand(request, scope)
        native = {"program": request["program"], "database": request["database"],
                  "hitlist_size": request.get("hitlist_size", 50)}
        if operation in {"prepare", "submit"}:
            native["query_fasta"] = f">{subject}\n{sequence}"
        if operation == "submit" and any(
                row.get("name") == "api.blast.submit" and
                (row.get("event", {}).get("native_handle") or {}).get("rid")
                for row in previous_events):
            raise ValueError("blast_original_submission_already_recorded")
        if operation in {"status", "fetch"}:
            handle = self._handle(handle)
            native["rid"] = handle["rid"]
            for row in previous_events:
                previous = row.get("event", {}).get("native_handle") or {}
                if previous.get("rid") and previous["rid"] != handle["rid"]:
                    raise ValueError("blast_original_handle_conflict")
        return {"operation": name, "mutates_remote": operation == "submit",
                "request": request, "native_operation": operation,
                "native_arguments": native, "query_length": len(sequence),
                "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
                "native_handle": handle if operation in {"status", "fetch"} else None}

    def invoke(self, prepared):
        operation = prepared["native_operation"]
        if operation == "prepare":
            return None
        # PublicClients.blast performs one HTTP request and returns spacing
        # feedback; unlike RemoteSearches it neither waits nor polls.
        return self.client.blast(operation, **prepared["native_arguments"])

    def _limits(self, action, rid=None):
        facts = {"contact_minimum_seconds": 10, "same_rid_status_minimum_seconds": 60,
                 "contact_configured": bool(getattr(self.client, "ncbi_email", None))}
        if hasattr(self.client, "blast_delay"):
            try:
                facts["earliest_request_after_seconds"] = self.client.blast_delay(action, rid)
            except AcquisitionError as error:
                facts["earliest_request_after_seconds"] = None
                facts["rate_information_unavailable"] = error.code
        return facts

    def decode(self, prepared, snapshot):
        operation = prepared["native_operation"]
        if operation == "prepare":
            if snapshot is not None:
                raise ValueError("blast_local_preparation_has_no_response")
            return event("preparation", "completed", facts={
                "query_length": prepared["query_length"],
                "program": prepared["request"]["program"],
                "database": prepared["request"]["database"], **self._limits("submit")})
        if snapshot is None or snapshot.service != "ncbi_blast":
            raise ValueError("blast_native_response_required")
        status = snapshot.transport.get("status")
        if status is not None and (type(status) is not int or not 200 <= status < 300):
            raise ValueError("blast_http_response_not_successful")
        self._response_request(prepared, snapshot)
        if operation == "submit":
            rid, rtoe = blast.submission(snapshot.content)
            return event("job", "submitted", native_handle={"rid": rid, "rtoe_seconds": rtoe},
                handoff_ready=True, facts={"native_state": "accepted", "rtoe_seconds": rtoe,
                                          **self._limits("status", rid)})
        handle = self._handle(prepared["native_handle"])
        if snapshot.request.get("rid") not in (None, handle["rid"]):
            raise ValueError("blast_response_rid_conflict")
        if operation == "status":
            native = blast.status(snapshot.content)
            state = {"WAITING": "submitted", "READY": "completed", "FAILED": "failed",
                     "UNKNOWN": "unknown"}[native["status"]]
            return event("job", state, native_handle=handle,
                handoff_ready=native["status"] in {"WAITING", "READY"},
                result_available=native["status"] == "READY",
                facts={"native_state": native["status"], "has_hits": native["has_hits"],
                       **self._limits("status", handle["rid"])},
                failure_code="blast_" + native["status"].lower()
                    if native["status"] in {"FAILED", "UNKNOWN"} else None)
        parsed = blast.document(snapshot.content)
        blast.validate_identity(parsed, {"algorithm": prepared["request"]["program"],
            "subject_ref": prepared["request"]["subject_ref"],
            "query_length": prepared["query_length"]})
        return event("response", "completed", native_handle=handle, handoff_ready=True,
            result_available=True, facts={"native_state": "READY",
                "native_hit_count": len(parsed["search"].get("hits", [])),
                "program": parsed["report"]["program"], **self._limits("fetch", handle["rid"])})

    @staticmethod
    def _response_request(prepared, snapshot):
        expected = {"action": prepared["native_operation"],
                    **{key: value for key, value in prepared["native_arguments"].items()
                       if key != "query_fasta"}}
        if "query_fasta" in prepared["native_arguments"]:
            expected["query_sha256"] = hashlib.sha256(
                prepared["native_arguments"]["query_fasta"].encode()).hexdigest()
        for key in ("action", "rid", "program", "database", "hitlist_size", "query_sha256"):
            if key in snapshot.request and snapshot.request[key] is not None and snapshot.request[key] != expected.get(key):
                raise ValueError("blast_response_request_conflict_" + key)

    def publish(self, request, selector, snapshot, scope, operation_key, *,
                submission_snapshot=None, handle=None):
        prepared = self.prepare("api.blast.fetch", request, {}, scope=scope,
                                previous_events=[], handle=handle, selector=selector)
        self.decode(prepared, snapshot)
        if submission_snapshot is None:
            raise ValueError("blast_original_submission_response_required")
        if submission_snapshot.service != "ncbi_blast":
            raise ValueError("blast_original_submission_provider_conflict")
        submitted = self.prepare("api.blast.submit", request, {}, scope=scope,
                                 previous_events=[])
        self._response_request(submitted, submission_snapshot)
        rid, _ = blast.submission(submission_snapshot.content)
        if rid != handle["rid"]:
            raise ValueError("blast_original_submission_identity_conflict")
        native_request = {"provider": "blast", "subject_ref": request["subject_ref"],
            "algorithm": request["program"], "database": request["database"],
            "parameters": {"hitlist_size": request.get("hitlist_size", 50)},
            "query_length": prepared["query_length"],
            "sequence_sha256": prepared["sequence_sha256"]}
        return publish_existing_acquisition(self.tools, "ncbi_blast.result", request,
            snapshot, scope, operation_key, publisher=lambda: self.tools._import_blast(
                snapshot, submission_snapshot=submission_snapshot, request=native_request,
                native_handle=handle))

    def prepare_observation(self, request, handle, *, scope):
        self.validate_request(request, scope)
        if not handle or not handle.get("rid"):
            return None
        return self.prepare("api.blast.status", request, {}, scope=scope,
                            previous_events=[], handle=handle)
