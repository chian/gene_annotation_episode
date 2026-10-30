"""Custody and recovery of one originally selected finite Enrichr protocol.

The caller already owns the selected action lock and immutable main intent.
Only each HTTP invocation leaves the owning coroutine thread. An issued stage
without a retained reply is uncertain work, never permission to send it again.
"""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import re

from .acquisition import AcquisitionError, SourceSnapshot
from .api_enrichr import PROTOCOL_VERSION, QUERY, WIRE_PROFILE, _stage_shape
from .communication import plain
from .execution_contracts import canonical, digest
from .practical_execution_state import _immutable, _read


STAGE_INTENT_VERSION = "enrichr_protocol_stage_intent_v1"
FAILURE_VERSION = "enrichr_protocol_stage_failure_v1"
_MAIN_FIELDS = {"run_id", "episode_id", "name", "arguments", "assignment_sha256",
                "operation_key", "prepared", "started_at"}
_ERROR_FIELDS = ("code", "retry_after", "job_ref", "phase", "submission_outcome",
                 "diagnostic", "operational")


def _require(condition, code="enrichr_protocol_custody_conflict"):
    if not condition:
        raise ValueError(code)


def _same(left, right):
    return canonical(left) == canonical(right)


class EnrichrProtocolHost:
    def __init__(self, owner):
        self.owner = owner

    def _authority(self, context, service, intent, directory):
        owner = self.owner
        _require(context.run_id == owner.run_id and context.role == "launch_api")
        assignment = plain(context.assignment)
        _require(assignment.get("service") == "enrichr"
            and owner.services.get(assignment.get("resource_id")) is service
            and service.service == "enrichr")
        manifest_directory = owner._manifest(context, create=False)
        manifest = _read(manifest_directory / "assignment.json")
        _require(_same(manifest, {"run_id": owner.run_id, "episode_id": context.episode_id,
            "role": context.role, "assignment": assignment, "scope": plain(context.scope)}))
        _require(type(intent) is dict and set(intent) == _MAIN_FIELDS)
        original = {"run_id": owner.run_id, "episode_id": context.episode_id,
            "name": QUERY, "arguments": intent["arguments"],
            "assignment_sha256": digest(assignment), "operation_key": intent["operation_key"]}
        _require(all(_same(intent[field], value) for field, value in original.items()))
        _require(type(intent["arguments"]) is dict and type(intent["operation_key"]) is str)
        directory = Path(directory)
        expected = manifest_directory / "actions" / digest(intent["operation_key"])
        _require(directory.resolve() == expected.resolve())
        _require(_same(_read(directory / "intent.json"), intent))
        selected = owner._selected(context, QUERY, intent["arguments"], intent["operation_key"])
        action = json.loads(selected["action"])
        _require(action.get("kind") == "tool" and action.get("tool") == QUERY
            and _same(action.get("arguments"), intent["arguments"]))
        prepared = intent["prepared"]
        _require(type(prepared) is dict and prepared.get("operation") == QUERY
            and _same(prepared.get("request"), assignment.get("request")))
        length = service.protocol_length(prepared)
        _require(type(length) is int and length in (2, 3))
        stages = directory / "protocol-stages"
        if stages.exists():
            _require(stages.is_dir() and all(path.is_dir() and path.name in {
                str(ordinal) for ordinal in range(length)} for path in stages.iterdir()))
        return directory, prepared, length

    @staticmethod
    def _stage_intent(intent, ordinal, prepared, metadata, snapshots):
        return EnrichrProtocolHost._stage_intent_hashes(intent, ordinal, prepared, metadata,
            [snapshot.sha256 for snapshot in snapshots])

    @staticmethod
    def _stage_intent_hashes(intent, ordinal, prepared, metadata, content_hashes):
        return {"version": STAGE_INTENT_VERSION, "run_id": intent["run_id"],
            "episode_id": intent["episode_id"], "assignment_sha256": intent["assignment_sha256"],
            "operation_key": intent["operation_key"], "main_intent_sha256": digest(intent),
            "ordinal": ordinal, "prepared": deepcopy(prepared),
            "prior_responses": [{"ordinal": index, "snapshot_sha256": digest(saved),
                "content_sha256": content_hash}
                for index, (saved, content_hash) in enumerate(zip(metadata, content_hashes))]}

    @staticmethod
    def _raw_metadata(metadata):
        _require(type(metadata) is dict and set(metadata) == {"service", "url", "request",
            "retrieved_at", "media_type", "transport", "content_ref"})
        _require(type(metadata["transport"]) is dict and "enrichr_protocol" not in metadata["transport"])
        return metadata

    def _load_response(self, metadata):
        self._raw_metadata(metadata)
        snapshot = self.owner._load_snapshot(metadata)
        _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes
            and metadata["content_ref"] == "artifact_" + snapshot.sha256
            and type(snapshot.transport) is dict and "enrichr_protocol" not in snapshot.transport)
        return snapshot

    @staticmethod
    def _failure(intent, ordinal, prepared, metadata, error):
        return {"version": FAILURE_VERSION, "main_intent_sha256": digest(intent),
            "ordinal": ordinal, "prepared_sha256": digest(prepared),
            "snapshot_sha256": digest(metadata) if metadata is not None else None,
            "exception_type": type(error).__name__,
            "acquisition_error": ({field: deepcopy(getattr(error, field)) for field in _ERROR_FIELDS}
                if isinstance(error, AcquisitionError) else None)}

    @staticmethod
    def _read_failure(path, intent, ordinal, prepared, metadata):
        value = _read(path)
        _require(type(value) is dict and set(value) == {"version", "main_intent_sha256", "ordinal",
            "prepared_sha256", "snapshot_sha256", "exception_type", "acquisition_error"})
        _require(value["version"] == FAILURE_VERSION and type(value["ordinal"]) is int
            and value["ordinal"] == ordinal and value["main_intent_sha256"] == digest(intent)
            and value["prepared_sha256"] == digest(prepared)
            and type(value["exception_type"]) is str and bool(value["exception_type"]))
        _require(value["snapshot_sha256"] is None or type(value["snapshot_sha256"]) is str)
        if metadata is not None:
            _require(value["snapshot_sha256"] == digest(metadata))
        error = value["acquisition_error"]
        _require(error is None or type(error) is dict and set(error) == set(_ERROR_FIELDS))
        if error is not None:
            _require(type(error["code"]) is str and bool(error["code"]))
        return value

    @staticmethod
    def _diagnostic(ordinal, stage, snapshots, length, snapshot=None):
        status = snapshot.transport.get("status") if snapshot is not None else None
        return {"stage_ordinal": ordinal, "stage_code": stage["stage_code"],
            "captured_prefix_count": len(snapshots),
            "http_status": status if type(status) is int else None,
            "response_retained": snapshot is not None,
            "all_stage_responses_captured": len(snapshots) == length}

    def _raise_failure(self, failure, ordinal, stage, snapshots, length, snapshot=None):
        saved = failure["acquisition_error"] if failure is not None else None
        unknown = failure is None or saved is None or (
            failure["snapshot_sha256"] is not None and snapshot is None)
        code = "enrichr_protocol_stage_response_unknown" if unknown else saved["code"]
        aggregate = ("response_received" if snapshots else "not_sent"
            if not unknown and saved["submission_outcome"] == "not_sent" else "unknown")
        raise AcquisitionError(code,
            retry_after=saved["retry_after"] if saved is not None else None,
            phase="recovery" if unknown else saved["phase"], submission_outcome=aggregate,
            diagnostic=self._diagnostic(ordinal, stage, snapshots, length, snapshot))

    @staticmethod
    def _accepted_partial(failure, ordinal, length, snapshot):
        return snapshot is not None and EnrichrProtocolHost._accepted_partial_transport(
            failure, ordinal, length, snapshot.transport)

    @staticmethod
    def _accepted_partial_transport(failure, ordinal, length, transport):
        if failure is None or ordinal != length - 1:
            return False
        error = failure["acquisition_error"]
        return (error is not None and error["code"] == "provider_response_byte_limit"
            and type(transport.get("status")) is int and 200 <= transport["status"] < 300
            and transport.get("body_complete") is False
            and transport.get("body_capture_failure") == "provider_response_byte_limit")

    @staticmethod
    def _compose(prepared, metadata, snapshots):
        transport = deepcopy(snapshots[-1].transport)
        transport["enrichr_protocol"] = {"version": PROTOCOL_VERSION, "wire_profile": WIRE_PROFILE,
            "prepared": deepcopy(prepared), "stages": [{"ordinal": ordinal,
                "stage_code": snapshot.request["stage_code"], "snapshot": deepcopy(saved)}
                for ordinal, (saved, snapshot) in enumerate(zip(metadata, snapshots))]}
        return replace(snapshots[-1], transport=transport)

    def _request(self, service, prepared, ordinal, snapshots, length):
        try:
            return service.protocol_request(prepared, stage=ordinal, retained_responses=snapshots)
        except ValueError as error:
            if not snapshots:
                raise
            previous = snapshots[-1]
            previous_stage = service.protocol_request(prepared, stage=ordinal - 1,
                retained_responses=snapshots[:-1])
            raise AcquisitionError(str(error), phase="protocol_response",
                submission_outcome="response_received", diagnostic=self._diagnostic(
                    ordinal - 1, previous_stage, snapshots, length, previous)) from error

    async def acquire(self, context, service, intent, directory):
        directory, prepared, length = self._authority(context, service, intent, directory)
        metadata, snapshots = [], []
        for ordinal in range(length):
            stage = self._request(service, prepared, ordinal, snapshots, length)
            stage_intent = self._stage_intent(intent, ordinal, stage, metadata, snapshots)
            stage_directory = directory / "protocol-stages" / str(ordinal)
            intent_path = stage_directory / "intent.json"
            snapshot_path = stage_directory / "snapshot.json"
            failure_path = stage_directory / "failure.json"
            if intent_path.exists():
                _require(_same(_read(intent_path), stage_intent))
                saved = _read(snapshot_path) if snapshot_path.exists() else None
                failure = (self._read_failure(failure_path, intent, ordinal, stage, saved)
                    if failure_path.exists() else None)
                snapshot = self._load_response(saved) if saved is not None else None
                if snapshot is None:
                    self._raise_failure(failure, ordinal, stage, snapshots, length)
            else:
                _require(not snapshot_path.exists() and not failure_path.exists())
                _require(not any((directory / "protocol-stages" / str(later) / filename).exists()
                    for later in range(ordinal + 1, length)
                    for filename in ("intent.json", "snapshot.json", "failure.json")))
                stage_directory.mkdir(parents=True, exist_ok=True)
                _immutable(intent_path, stage_intent)
                try:
                    snapshot = await asyncio.to_thread(service.invoke, stage)
                except BaseException as error:
                    actual = getattr(error, "snapshot", None)
                    saved = self.owner._snapshot(actual) if actual is not None else None
                    failure = self._failure(intent, ordinal, stage, saved, error)
                    _immutable(failure_path, failure)
                    if saved is not None:
                        _immutable(snapshot_path, saved)
                    if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                        raise
                    snapshot = self._load_response(saved) if saved is not None else None
                    if snapshot is None:
                        self._raise_failure(failure, ordinal, stage, snapshots, length)
                else:
                    _require(isinstance(snapshot, SourceSnapshot), "enrichr_stage_response_required")
                    saved = self.owner._snapshot(snapshot)
                    _immutable(snapshot_path, saved)
                    snapshot = self._load_response(saved)
                    failure = None
            metadata.append(saved)
            snapshots.append(snapshot)
            if failure is not None and not self._accepted_partial(failure, ordinal, length, snapshot):
                self._raise_failure(failure, ordinal, stage, snapshots, length, snapshot)
            if snapshot.transport.get("body_complete") is False and failure is None:
                raise AcquisitionError("enrichr_stage_response_incomplete", phase="protocol_response",
                    submission_outcome="response_received", diagnostic=self._diagnostic(
                        ordinal, stage, snapshots, length, snapshot))
        try:
            result = self._compose(prepared, metadata, snapshots)
            self.validate(context, service, intent, directory, result)
        except ValueError as error:
            raise AcquisitionError(str(error), phase="protocol_response",
                submission_outcome="response_received", diagnostic=self._diagnostic(
                    length - 1, stage, snapshots, length, snapshots[-1])) from error
        return result

    def validate(self, context, service, intent, directory, snapshot):
        directory, prepared, length = self._authority(context, service, intent, directory)
        metadata, snapshots = [], []
        for ordinal in range(length):
            stage = self._request(service, prepared, ordinal, snapshots, length)
            stage_directory = directory / "protocol-stages" / str(ordinal)
            expected = self._stage_intent(intent, ordinal, stage, metadata, snapshots)
            _require(_same(_read(stage_directory / "intent.json"), expected))
            saved = _read(stage_directory / "snapshot.json")
            raw = self._load_response(saved)
            failure_path = stage_directory / "failure.json"
            failure = (self._read_failure(failure_path, intent, ordinal, stage, saved)
                if failure_path.exists() else None)
            metadata.append(saved)
            snapshots.append(raw)
            if failure is not None and not self._accepted_partial(failure, ordinal, length, raw):
                self._raise_failure(failure, ordinal, stage, snapshots, length, raw)
            _require(raw.transport.get("body_complete") is not False or failure is not None,
                "enrichr_stage_response_incomplete")
        expected = self._compose(prepared, metadata, snapshots)
        _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes
            and snapshot.content == expected.content)
        actual_fields, expected_fields = asdict(snapshot), asdict(expected)
        actual_fields.pop("content")
        expected_fields.pop("content")
        _require(_same(actual_fields, expected_fields))
        service.decode(prepared, expected)

    @staticmethod
    def _metadata_wire(metadata, stage, *, intermediate):
        """Check recorded wire fields without substituting response content."""
        _require(metadata["service"] == "enrichr" and type(metadata["retrieved_at"]) is str
            and type(metadata["media_type"]) is str and metadata["url"] == stage["http"]["url"]
            and _same(metadata["request"], stage))
        transport, http = metadata["transport"], stage["http"]
        wire = transport.get("request")
        _require(type(wire) is dict and wire.get("method") == http["method"]
            and wire.get("url") == http["url"] and _same(transport.get("request_policy"), {
                "timeout_seconds": http["timeout_seconds"], "automatic_redirects": False}))
        headers = wire.get("headers")
        _require(type(headers) is dict and all(type(key) is str for key in headers))
        headers = {key.lower(): value for key, value in headers.items()}
        _require(headers.get("accept") == http["accept"]
            and headers.get("content-type") == http["content_type"])
        if http["body_base64"] is None:
            _require("body_base64" not in wire and "body_sha256" not in wire)
        else:
            body = base64.b64decode(http["body_base64"], validate=True)
            _require(wire.get("body_base64") == http["body_base64"]
                and wire.get("body_sha256") == hashlib.sha256(body).hexdigest())
        _require(transport.get("effective_url", http["url"]) == http["url"]
            and type(transport.get("status")) is int and 200 <= transport["status"] < 300
            and type(transport.get("body_complete")) is bool
            and (not intermediate or transport["body_complete"]))

    def validate_closed_metadata(self, context, service, intent, directory, metadata, *, protocol_artifacts):
        """Verify original identities after the caller proves successful closure.

        This method grants no authority to skip payload verification. Its API
        caller must first authenticate the actual closed result and its frozen
        publication witness. No native payload, request or grade is read here.
        """
        directory, prepared, length = self._authority(context, service, intent, directory)
        _require(type(metadata) is dict and set(metadata) == {"service", "url", "request",
            "retrieved_at", "media_type", "transport", "content_ref"}
            and type(metadata["transport"]) is dict)
        protocol = metadata["transport"].get("enrichr_protocol")
        _require(type(protocol) is dict and set(protocol) == {"version", "wire_profile", "prepared", "stages"}
            and protocol["version"] == PROTOCOL_VERSION and protocol["wire_profile"] == WIRE_PROFILE
            and _same(protocol["prepared"], prepared) and type(protocol["stages"]) is list
            and len(protocol["stages"]) == length
            and type(protocol_artifacts) is list and len(protocol_artifacts) == length)
        codes = ["query_upload", "enrichment"] if length == 2 else [
            "query_upload", "background_upload", "enrichment"]
        saved_metadata, content_hashes = [], []
        for ordinal, (entry, artifact) in enumerate(zip(protocol["stages"], protocol_artifacts)):
            _require(type(entry) is dict and set(entry) == {"ordinal", "stage_code", "snapshot"}
                and type(entry["ordinal"]) is int and entry["ordinal"] == ordinal
                and entry["stage_code"] == codes[ordinal])
            raw = self._raw_metadata(entry["snapshot"])
            reference = raw["content_ref"]
            _require(type(reference) is str and re.fullmatch(r"artifact_[a-f0-9]{64}", reference))
            _require(type(artifact) is dict and set(artifact) == {
                "stage_ordinal", "artifact_ref", "artifact_metadata_sha256"}
                and type(artifact["stage_ordinal"]) is int and artifact["stage_ordinal"] == ordinal
                and artifact["artifact_ref"] == reference
                and artifact["artifact_metadata_sha256"] == digest(
                    self.owner.enrichr_returns._artifact_metadata(reference)))
            stage = _stage_shape(raw["request"])
            _require(stage["stage"] == ordinal and stage["stage_code"] == codes[ordinal]
                and _same(stage["request"], prepared["request"])
                and _same(stage["prior_response_sha256"], content_hashes)
                and _same(stage["http"]["timeout_seconds"], prepared["configuration"]["timeout"])
                and stage["http"]["response_byte_limit"] == prepared["configuration"]["response_byte_limit"])
            stage_directory = directory / "protocol-stages" / str(ordinal)
            _require(_same(_read(stage_directory / "snapshot.json"), raw)
                and _same(_read(stage_directory / "intent.json"), self._stage_intent_hashes(
                    intent, ordinal, stage, saved_metadata, content_hashes)))
            self._metadata_wire(raw, stage, intermediate=ordinal < length - 1)
            failure_path = stage_directory / "failure.json"
            failure = (self._read_failure(failure_path, intent, ordinal, stage, raw)
                if failure_path.exists() else None)
            _require(failure is None or self._accepted_partial_transport(
                failure, ordinal, length, raw["transport"]))
            _require(raw["transport"]["body_complete"] or failure is not None)
            saved_metadata.append(raw)
            content_hashes.append(reference.removeprefix("artifact_"))
        expected = deepcopy(saved_metadata[-1])
        expected["transport"]["enrichr_protocol"] = deepcopy(protocol)
        _require(_same(metadata, expected))


__all__ = ["EnrichrProtocolHost"]
