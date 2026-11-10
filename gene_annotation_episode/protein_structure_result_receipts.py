"""Immutable protein result controls and original completed-action proof.

This module reads compact saved records, never scientific artifact bytes.  Its
writer lock covers the selected host operation; private replay is deliberately
separate from authority established by a committed runtime collect outcome.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
from typing import Literal, TypeAlias, TypedDict

from jsonschema import Draft202012Validator, validators

from .communication import plain
from .domain import RECORD_SCHEMAS, identity
from .episode_bindings import BindingContext
from .execution_contracts import canonical, digest, validate_target
from .native_protein_structure_acquisition import (
    ProteinStructureCapture, CapturedManifestFile,
    qualify_protein_structure_target_plan,
)
from .native_protein_structure_contracts import (
    NATIVE_FORMATS, POLICY, NativeProteinBundle,
    validate_protein_structure_bundle, validate_protein_structure_requested_job,
)
from .native_protein_structure_preparation import (
    PreparedProteinWorker, ProteinWorkerDiagnostic, ProteinWorkerExecution,
    ProteinWorkerFailure, ValidatedProteinWorker,
)
from .practical_receipt_information import PracticalReceiptInformation
from .practical_execution_records import validate_receipt
from .progress_records import RESOURCE_OBSERVATION_SCHEMA, validate_resource_observation
from .protein_structure_authority import ProteinFactGroups
from .protein_structure_contracts import (
    ArtifactRef, FileIdentity, ResultCustody, Sha256, StructuredIssue, issue,
    protein_structure_schema_definitions, same, validate_file_identity,
    validate_saved_sheet_descriptor, validate_structure_sequence_descriptor,
)
from .protein_structure_publication import protein_structure_source_payload
from .protein_structure_result_views import (
    ProjectionCalculation, validate_protein_structure_failure_return,
    validate_protein_structure_projection_result,
)
from .protein_structure_result_worker import (
    validate_protein_structure_result_worker_plan,
    validate_protein_structure_result_worker_result,
)
from .protein_structure_selection import validate_protein_structure_result_selector


ResourceObservation: TypeAlias = dict


class ProteinResultIntent(TypedDict):
    version: Literal["protein_structure_result_intent_v1"]
    run_id: str
    episode_id: str
    path: list[list[str]]
    scope: dict
    assignment: dict
    original_request_sha256: Sha256
    operation_key: str
    tool_name: Literal["execution.results.status", "execution.results.collect"]
    arguments: dict
    target: dict


class ProteinQualifiedFiles(TypedDict):
    native_file: FileIdentity | None
    sequence_file: FileIdentity | None
    residue_map_file: FileIdentity | None
    sheet_file: FileIdentity | None
    original_components_file: FileIdentity | None
    components_file: FileIdentity | None


class ProteinHandoffProof(TypedDict):
    source_record: dict
    body: dict
    assignment_snapshot: dict


class TerminalProteinHandoffProof(ProteinHandoffProof):
    start_receipt: dict


class ProteinResultBody(TypedDict):
    version: Literal["protein_structure_result_body_v1"]
    intent: ProteinResultIntent
    handoff_proof: ProteinHandoffProof | TerminalProteinHandoffProof | None
    observation: ResourceObservation | None
    observation_origin: Literal["selected_native_observation", "original_saved_observation", "not_observed"]
    original_custody: ResultCustody | None
    capture: ProteinStructureCapture | None
    bundle: NativeProteinBundle | None
    worker: ValidatedProteinWorker | None
    qualified_files: ProteinQualifiedFiles
    calculation: ProjectionCalculation | None
    issues: list[StructuredIssue]
    native_success: bool
    capture_complete: bool


class SelectionAccounting(TypedDict):
    projection_ids: list[str]
    failed_projection_ids: list[str]
    saved_sheet: Literal["not_requested", "published", "unavailable"]
    sequence: Literal["not_requested", "published", "unavailable"]


class ProteinResultPublication(TypedDict):
    version: Literal["protein_structure_result_publication_v1"]
    body_sha256: Sha256
    result_receipt_key: str
    custody: ResultCustody | None
    source_record: dict | None
    reference_records: list[dict]
    facts: ProteinFactGroups
    accounting: SelectionAccounting
    record_refs: list[str]
    family_artifact_refs: list[ArtifactRef]
    delivery_complete: bool


class ProteinResultReceipt(TypedDict):
    version: Literal["native_protein_structure_acquired_result_v1"]
    body: ProteinResultBody
    publication: ProteinResultPublication


@dataclass(frozen=True, init=False)
class ProteinResultAction:
    intent: ProteinResultIntent
    directory: Path
    capture_directory: Path
    worker_directory: Path


_FACTS = tuple(ProteinFactGroups.__annotations__)
_PROJECTION, _SAVED, _SEQUENCE, _FAILURE = _FACTS
_OUTPUTS = {"native_result_file": "native-result.json", "sheet_file": "sheet.json",
            "components_file": "components.json"}
_DIAGNOSTICS = (*_OUTPUTS.values(), "worker-result.json")
_CONTROL_NAMES = ("intent.json", "handoff-proof.json", "observation.json", "body.json",
                  "publication.json", "receipt.json")
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, value: type(value) is int)
    .redefine("number", lambda _, value: type(value) in (int, float)
              and (type(value) is int or math.isfinite(value))))
_DEFS = protein_structure_schema_definitions()
_ISSUE = _STRICT({"$defs": _DEFS, "$ref": "#/$defs/StructuredIssue"})
_CUSTODY = _STRICT({"$defs": _DEFS, "$ref": "#/$defs/ResultCustody"})
_OBSERVATION = _STRICT(RESOURCE_OBSERVATION_SCHEMA)
_READING = ContextVar("protein_result_receipt_read_stack", default=())


def _require(condition, code="original_commission_mismatch"):
    if not condition:
        raise ValueError(code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields), "invalid_schema")


def _json(value):
    """Detach strict JSON without allowing bool counts or tuple coercion."""
    def check(item):
        if type(item) is dict:
            _require(all(type(key) is str and "\0" not in key for key in item), "invalid_schema")
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif type(item) is str:
            _require("\0" not in item, "invalid_schema")
        elif type(item) is float:
            _require(math.isfinite(item), "invalid_schema")
        else:
            _require(item is None or type(item) in (bool, int), "invalid_schema")
    check(value)
    return json.loads(canonical(value))


def _decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, "invalid_schema")
            value[key] = item
        return value
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
        _json(value)
        _require(raw == canonical(value).encode("utf-8"), "invalid_schema")
        return value
    except (UnicodeError, ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error


def _path(value):
    _require(type(value) is str and value and not any(c in value for c in "\0\n\r\\"), "invalid_output_path")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts
             and value != "/", "invalid_output_path")
    return path


@contextmanager
def _directory(path, *, create=False):
    """Pin every path component; never follow a control-directory symlink."""
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in _path(str(path)).parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        _require(os.fstat(fd).st_uid == os.geteuid(), "invalid_output_path")
        yield fd


@contextmanager
def _regular(directory_fd, name, *, flags=os.O_RDONLY):
    _require(type(name) is str and name not in ("", ".", "..") and "/" not in name, "invalid_output_path")
    fd = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    try:
        _require(stat.S_ISREG(os.fstat(fd).st_mode) and os.fstat(fd).st_uid == os.geteuid(), "invalid_output_path")
        yield fd
    finally:
        os.close(fd)


def _read(fd, name):
    try:
        with _regular(fd, name) as control, os.fdopen(os.dup(control), "rb") as stream:
            raw = stream.read()
            # This one existing shared file is written by
            # ExecutionEpisodes._result_directory with a single trailing LF.
            # Earlier direct-host receipts used canonical bytes without it.
            if name == "assignment.json" and raw.endswith(b"\n"):
                raw = raw[:-1]
            return _decode(raw)
    except FileNotFoundError:
        return None


def _immutable(fd, name, value):
    previous = _read(fd, name)
    if previous is not None:
        _require(same(previous, value))
        return
    temporary = "." + name + "." + secrets.token_hex(16) + ".writing"
    try:
        with _regular(fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as out:
            with os.fdopen(os.dup(out), "wb") as stream:
                payload = canonical(value).encode("utf-8")
                if name == "assignment.json":
                    payload += b"\n"
                stream.write(payload)
                stream.flush()
                os.fchmod(out, 0o444)
                os.fsync(out)
        try:
            os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        except FileExistsError:
            _require(same(_read(fd, name), value))
        os.fsync(fd)
    finally:
        os.unlink(temporary, dir_fd=fd)


async def _drain(task):
    """Keep ownership until the thread returns, including repeated cancellation."""
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()


def _receipt_key(intent):
    return "protein_structure_result_receipt:" + digest({key: intent[key]
        for key in ("run_id", "episode_id", "operation_key")})


def _outcome(receipt):
    references = receipt["publication"]["record_refs"]
    return {"status": "completed", "record_refs": references, "changed_record_refs": references,
            "result": receipt, "feedback": None}


class ProteinResultReceipts:
    def __init__(self, owner):
        # The host is constructed before owner.native_protein_structure_returns.
        self.owner = owner
        self._active = {}

    @property
    def _returns(self):
        return self.owner.native_protein_structure_returns

    @property
    def _store(self):
        return self.owner.store

    def action_directory(self, *, episode_id: str, operation_key: str) -> Path:
        return (self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id])
                / "native-protein-structure-actions" / digest(operation_key))

    def _assignment(self, context):
        _require(isinstance(context, BindingContext) and context.run_id == self.owner.run_id
                 and context.role == "results")
        assignment = _json(plain(context.assignment))
        _closed(assignment, ("version", "handoff_ref", "selector"))
        _require(assignment["version"] == "execution_results_assignment_v1")
        _require(type(assignment["handoff_ref"]) is str and bool(assignment["handoff_ref"]), "invalid_schema")
        validate_protein_structure_result_selector(assignment["selector"])
        self._store.validate_scope(plain(context.scope))
        return assignment

    def _selected(self, intent, *, completed=False):
        key = intent["operation_key"]
        prefix = f'{self.owner.run_id}:{intent["episode_id"]}:'
        _require(type(key) is str and key.startswith(prefix)
                 and re.fullmatch(r"0|[1-9][0-9]*", key[len(prefix):]) is not None)
        row = self.owner._selected_result_action(intent["episode_id"], key,
            intent["tool_name"], intent["arguments"])
        action = json.loads(row["action"])
        _require(same(action, {"kind": "tool", "tool": intent["tool_name"], "arguments": {}}))
        if completed:
            _require(intent["tool_name"] == "execution.results.collect" and row["result"] is not None)
        return row

    def _intent(self, context, target, tool_name, arguments, operation_key):
        self._returns.authenticate(context)
        assignment = self._assignment(context)
        target = validate_target(_json(target))
        _require(tool_name in ("execution.results.status", "execution.results.collect")
                 and type(arguments) is dict and not arguments, "invalid_schema")
        _require(target["run_id"] == context.run_id and target["handle"] == assignment["handoff_ref"]
                 and target["resource_kind"] == "local")
        request = validate_protein_structure_requested_job(target["assignment"]["requested_job"])
        _require(target["request_sha256"] == digest(request)
                 and target["assignment"]["resource_id"] == target["resource_id"])
        self._store.validate_scope(target["scope"], parent_scope=plain(context.scope))
        validate_protein_structure_result_selector(assignment["selector"],
            request=request["native_protein_structure"]["request"])
        intent = {"version": "protein_structure_result_intent_v1", "run_id": context.run_id,
            "episode_id": context.episode_id, "path": plain(context.path), "scope": plain(context.scope),
            "assignment": assignment, "original_request_sha256": digest(plain(context.request)),
            "operation_key": operation_key, "tool_name": tool_name, "arguments": {}, "target": target}
        self._selected(intent)
        return intent

    def _manifest(self, context):
        return {"run_id": context.run_id, "episode_id": context.episode_id,
                "assignment": plain(context.assignment), "scope": plain(context.scope)}

    @asynccontextmanager
    async def locked_action(self, context, *, target, tool_name, arguments, operation_key):
        intent = self._intent(context, target, tool_name, arguments, operation_key)
        _require(not self._store.db.in_transaction, "original_commission_mismatch")
        directory = self.action_directory(episode_id=context.episode_id, operation_key=operation_key)
        try:
            with _directory(directory.parent.parent, create=True) as root_fd:
                _immutable(root_fd, "assignment.json", self._manifest(context))
            with _directory(directory, create=True) as fd, \
                    _regular(fd, ".action.lock", flags=os.O_RDWR | os.O_CREAT) as lock_fd:
                task = asyncio.create_task(asyncio.to_thread(fcntl.flock, lock_fd, fcntl.LOCK_EX))
                acquired = False
                action = None
                try:
                    try:
                        await asyncio.shield(task)
                        acquired = True
                    except asyncio.CancelledError:
                        await _drain(task)
                        acquired = True
                        raise
                    _require(not self._store.db.in_transaction)
                    _require(same(intent, self._intent(context, target, tool_name, arguments, operation_key)))
                    selected = self._selected(intent)
                    if selected["result"] is not None:
                        _require(_read(fd, "receipt.json") is not None)
                    if _read(fd, "intent.json") is None:
                        _require(all(_read(fd, name) is None for name in _CONTROL_NAMES[1:]))
                    _immutable(fd, "intent.json", intent)
                    for child in (directory / "capture", directory / "worker"):
                        try:
                            with _directory(child):
                                pass
                        except FileNotFoundError:
                            pass
                    action = object.__new__(ProteinResultAction)
                    for key, value in {"intent": deepcopy(intent), "directory": directory,
                            "capture_directory": directory / "capture", "worker_directory": directory / "worker"}.items():
                        object.__setattr__(action, key, value)
                    self._active[id(action)] = (action, fd, deepcopy(intent), lock_fd)
                    self.require_action(action)
                    yield action
                finally:
                    if action is not None:
                        self._active.pop(id(action), None)
                    if acquired:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except OSError as error:
            raise ValueError("invalid_output_path") from error

    def require_action(self, action: ProteinResultAction) -> None:
        entry = self._active.get(id(action))
        _require(type(action) is ProteinResultAction and entry is not None and entry[0] is action)
        _, fd, intent, lock_fd = entry
        expected = self.action_directory(episode_id=intent["episode_id"], operation_key=intent["operation_key"])
        _require(same(action.intent, intent) and action.directory == expected
                 and action.capture_directory == expected / "capture" and action.worker_directory == expected / "worker")
        try:
            with _directory(expected) as current:
                a, b = os.fstat(fd), os.fstat(current)
                _require((a.st_dev, a.st_ino) == (b.st_dev, b.st_ino), "invalid_output_path")
                with _regular(current, ".action.lock") as selected_lock:
                    a, b = os.fstat(lock_fd), os.fstat(selected_lock)
                    _require((a.st_dev, a.st_ino) == (b.st_dev, b.st_ino), "invalid_output_path")
        except OSError as error:
            raise ValueError("invalid_output_path") from error
        _require(same(_read(fd, "intent.json"), intent))
        self._selected(intent)

    def _fd(self, action):
        self.require_action(action)
        return self._active[id(action)][1]

    def _artifact(self, reference, *, value=None):
        _require(type(reference) is str and re.fullmatch(r"artifact_[a-f0-9]{64}", reference) is not None,
                 "invalid_schema")
        record = self._store.get(reference)
        _closed(record, ("id", "record_type", "sha256", "size", "media_type"))
        _require(record["record_type"] == "artifact" and record["id"] == reference
                 and reference == "artifact_" + record["sha256"]
                 and type(record["size"]) is int and record["size"] >= 0
                 and type(record["media_type"]) is str and bool(record["media_type"]), "conflicting_identity")
        if value is not None:
            _require(record["sha256"] == digest(value)
                     and record["size"] == len(canonical(value).encode("utf-8")), "input_digest_mismatch")
        return record

    def _file(self, file):
        file = validate_file_identity(file)
        metadata = self._artifact(file["artifact_ref"])
        _require(metadata["sha256"] == file["sha256"] and metadata["size"] == file["byte_length"],
                 "input_digest_mismatch")
        return file

    def _record(self, record, kind, *, payload=None):
        _require(type(record) is dict and record.get("record_type") == kind and record.get("origin") == "tool",
                 "conflicting_identity")
        body = {k: v for k, v in record.items() if k not in ("id", "record_type", "origin")}
        _require(_STRICT(RECORD_SCHEMAS[kind]).is_valid(body), "invalid_schema")
        _require(record["id"] == identity(kind, {"origin": "tool", "record": body})
                 and same(self._store.get(record["id"]), record), "conflicting_identity")
        if payload is not None:
            _require(same(body, payload), "conflicting_identity")
        return body

    def validate_handoff_proof(self, proof: ProteinHandoffProof | TerminalProteinHandoffProof, *, intent: ProteinResultIntent) -> None:
        from .terminal_scientific_evidence import is_terminal_target, validate_terminal_handoff
        if is_terminal_target(intent['target']):
            validate_terminal_handoff(proof, intent, self._store, self.owner.run_id)
            return
        _closed(proof, ProteinHandoffProof.__annotations__)
        _json(proof)
        source, body, snapshot = (proof[name] for name in ProteinHandoffProof.__annotations__)
        practical = PracticalReceiptInformation(self._store, self.owner.run_id)
        qualified, selected = practical._qualify(body, snapshot, intent["scope"])
        _require(same(qualified, body) and selected["result"] is not None)
        self._artifact(source["artifact_ref"], value=body)
        self._artifact(source["request_ref"], value=snapshot)
        self._record(source, "source", payload=practical._source_payload(body,
            source["artifact_ref"], source["request_ref"]))
        _require(len(practical._sources(source["accession"])) == 1)
        receipt, assignment = body["receipt"], snapshot["assignment"]
        original = self._returns.context(body["episode_id"])
        _require(same(plain(original.assignment), assignment) and same(plain(original.scope), body["scope"]))
        _require(same(json.loads(selected["action"]), {"kind": "tool", "tool": receipt["tool_name"],
            "arguments": receipt["arguments"]}))
        outcome = json.loads(selected["result"])
        _require(outcome.get("status") in ("completed", "partial")
                 and same(outcome.get("result"), receipt) and source["id"] in outcome.get("record_refs", []))
        _require(receipt["tool_name"] in ("practical.job.start", "practical.job.status", "practical.job.collect"))
        requested = validate_protein_structure_requested_job(assignment["requested_job"])
        job = receipt["outcome"]["facts"].get("requested_job")
        _require(type(job) is dict and type(job.get("handoff")) is dict)
        _require(job["requested_job_sha256"] == digest(requested) and job["argv"] == requested["argv"]
                 and same(job["environment"], requested["environment"])
                 and job["resource_kind"] == assignment["resource_kind"] == "local"
                 and job["execution_id"] == job["handoff"].get("execution_id")
                 and job["handoff"].get("monitor_operation") == "practical.job.status"
                 and job["handoff"].get("results_operation") == "practical.job.collect")
        detail = receipt["outcome"].get("native_outcome") or {}
        key = detail.get("attempt_operation_key")
        _require(type(key) is str and bool(key) and detail.get("attempt_id") == digest(key))
        prefix = f'{self.owner.run_id}:{body["episode_id"]}:'
        _require(key.startswith(prefix) and re.fullmatch(r"0|[1-9][0-9]*", key[len(prefix):]) is not None)
        attempt = self._store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND decision_index=?", (self.owner.run_id, body["episode_id"], int(key[len(prefix):]))).fetchone()
        _require(attempt is not None and attempt["result"] is not None)
        attempt_outcome = json.loads(attempt["result"])
        _require(attempt_outcome.get("status") in ("completed", "partial"))
        attempt_receipt = validate_receipt(attempt_outcome.get("result"))
        _require(attempt_receipt["tool_name"] == "practical.job.start" and attempt_receipt["operation_key"] == key
                 and attempt_receipt["run_id"] == self.owner.run_id and attempt_receipt["episode_id"] == body["episode_id"]
                 and attempt_receipt["assignment_sha256"] == body["assignment_sha256"]
                 and same(json.loads(attempt["action"]), {"kind": "tool", "tool": "practical.job.start",
                     "arguments": attempt_receipt["arguments"]}))
        attempt_job = attempt_receipt["outcome"].get("facts", {}).get("requested_job", {})
        attempt_detail = attempt_receipt["outcome"].get("native_outcome") or {}
        _require(attempt_job.get("execution_id") == job["execution_id"]
                 and attempt_job.get("requested_job_sha256") == digest(requested)
                 and attempt_detail.get("attempt_operation_key") == key
                 and attempt_detail.get("attempt_id") == detail["attempt_id"])
        root = Path(assignment["workspace"]) / ".episode-operations" / digest({
            "run": self.owner.run_id, "episode": body["episode_id"]}) / digest(key)
        _require(job["execution_id"] == str(root / "native.json"))
        expected = {"version": "execution_target_v1", "handle": source["id"], "run_id": self.owner.run_id,
            "resource_id": assignment["resource_id"], "resource_kind": "local",
            "execution_id": job["execution_id"], "request_sha256": digest(requested),
            "origin_episode_id": body["episode_id"], "assignment": assignment, "scope": body["scope"]}
        _require(same(validate_target(expected), intent["target"])
                 and intent["assignment"]["handoff_ref"] == source["id"])

    def read_handoff_proof(self, action, *, context, target) -> ProteinHandoffProof | TerminalProteinHandoffProof:
        fd = self._fd(action)
        _require(same(action.intent, self._intent(context, target, action.intent["tool_name"], {},
            action.intent["operation_key"])))
        proof = _read(fd, "handoff-proof.json")
        if proof is None:
            selector = action.intent["assignment"]["selector"]
            if selector["acquisition"] == "retained_sheet_only":
                descriptor = selector["saved_sheet"]
                self._returns.authenticate_received_saved_sheet(context, descriptor, required_use="recalculate")
                custody = descriptor["custody"]
                original = self.read_completed(episode_id=custody["result_episode_id"],
                    operation_key=custody["result_operation_key"], scope=plain(context.scope))
                _require(same(original["publication"]["custody"], custody))
                proof = original["body"]["handoff_proof"]
                _require(proof is not None)
            else:
                from .terminal_scientific_evidence import is_terminal_target, read_terminal_handoff
                if is_terminal_target(target):
                    proof = read_terminal_handoff(self._store, self.owner.run_id, target, context.scope)
                    self.validate_handoff_proof(proof, intent=action.intent)
                    _immutable(fd, 'handoff-proof.json', proof)
                    return deepcopy(proof)
                practical = PracticalReceiptInformation(self._store, self.owner.run_id)
                body = practical.read(target["handle"], context.scope)
                source = self._store.get(target["handle"])
                snapshot = json.loads(self._store.get_artifact(source["request_ref"]))
                proof = {"source_record": source, "body": body, "assignment_snapshot": snapshot}
            self.validate_handoff_proof(proof, intent=action.intent)
            _immutable(fd, "handoff-proof.json", proof)
        self.validate_handoff_proof(proof, intent=action.intent)
        return deepcopy(proof)

    def read_observation(self, action) -> ResourceObservation | None:
        observation = _read(self._fd(action), "observation.json")
        if observation is not None:
            _require(_OBSERVATION.is_valid(observation), "invalid_schema")
            observation = validate_resource_observation(observation)
        return deepcopy(observation)

    def record_observation(self, action, *, observation) -> ResourceObservation:
        fd = self._fd(action)
        observation = _json(observation)
        _require(_OBSERVATION.is_valid(observation), "invalid_schema")
        observation = validate_resource_observation(observation)
        from .terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
        if is_terminal_target(action.intent['target']):
            validate_terminal_observation(observation, action.intent, self._store, self.owner.run_id)
        _immutable(fd, "observation.json", observation)
        return deepcopy(observation)

    def _issues(self, values):
        _require(type(values) is list and all(_ISSUE.is_valid(row) for row in values), "invalid_schema")

    def _capture(self, capture, bundle, intent):
        _closed(capture, ProteinStructureCapture.__annotations__)
        _require(capture["version"] == "native_protein_structure_capture_v1"
                 and type(capture["bundle_validated"]) is bool and type(capture["capture_complete"]) is bool
                 and type(capture["files"]) is list, "invalid_schema")
        self._issues(capture["failures"])
        plan = capture["original_plan"]
        if plan is not None:
            qualify_protein_structure_target_plan(intent["target"], plan)
        file = capture["bundle_file"]
        if file is not None:
            self._file(file)
            _require(file["format"] == "native_protein_structure_bundle_v1" and plan is not None)
        if not capture["bundle_validated"]:
            _require(bundle is None and not capture["capture_complete"] and not capture["files"]
                     and len(capture["failures"]) == 1)
            failure = capture["failures"][0]
            _require(same(failure, issue(failure["code"], stage="capture",
                field="request" if plan is None else "manifest")))
            return
        _require(plan is not None and file is not None and bundle is not None)
        validate_protein_structure_bundle(bundle, plan=plan)
        self._artifact(file["artifact_ref"], value=bundle)
        _require(len(capture["files"]) == len(bundle["files"]))
        failures = []
        for index, (row, declared) in enumerate(zip(capture["files"], bundle["files"])):
            _closed(row, CapturedManifestFile.__annotations__)
            _require(type(row["manifest_index_0based"]) is int and row["manifest_index_0based"] == index
                     and same(row["declared"], declared))
            observed = row["observed"]
            if declared["state"] == "absent":
                expected, problem = "declared_absent", None
                _require(observed is None)
            elif observed is None:
                expected, problem = "unavailable", issue("capture_incomplete", stage="capture",
                    field="manifest", artifact_role=declared["role"])
            else:
                self._file(observed)
                _require(observed["format"] == declared["format"])
                matched = all(observed[key] == declared[key] for key in ("sha256", "byte_length"))
                expected = "verified" if matched else "digest_mismatch"
                problem = None if matched else issue("input_digest_mismatch", stage="capture",
                    field="manifest", artifact_role=declared["role"])
                if matched and declared["role"] == "run_plan":
                    self._artifact(observed["artifact_ref"], value=plan)
                if matched and declared["role"] == "worker_input":
                    job = plan["requested_job"]["native_protein_structure"]
                    worker_input = {"version": "protein_structure_worker_input_v1", "request": job["request"],
                        "software": job["software"], "files": [{"input_id": item["input_id"], "role": item["role"],
                            "file_identity": item["file_identity"], "path": str(Path(plan["attempt_directory"]) /
                                item["staged_relative_path"])} for item in job["inputs"]]}
                    self._artifact(observed["artifact_ref"], value=worker_input)
            _require(row["outcome"] == expected and same(row["issue"], problem))
            if problem is not None:
                failures.append(problem)
        _require(same(failures, capture["failures"]) and capture["capture_complete"] == (not failures))

    @staticmethod
    def _verified(capture, role):
        return [] if capture is None else [row["observed"] for row in capture["files"]
            if row["outcome"] == "verified" and row["declared"]["role"] == role]

    def _worker(self, worker, body, original):
        _closed(worker, ValidatedProteinWorker.__annotations__)
        prepared, plan, execution, result = (worker[name] for name in ValidatedProteinWorker.__annotations__)
        _closed(prepared, PreparedProteinWorker.__annotations__)
        _require(prepared["version"] == "protein_structure_prepared_worker_v1")
        validate_protein_structure_result_worker_plan(plan)
        intent = body["intent"]
        directory = self.action_directory(episode_id=intent["episode_id"], operation_key=intent["operation_key"])
        _require(plan["directory"] == str(directory / "worker"))
        self._artifact(prepared["plan_artifact_ref"], value=plan)
        self._artifact(prepared["execution_receipt_artifact_ref"], value=execution)
        saved = intent["assignment"]["selector"]["acquisition"] == "retained_sheet_only"
        _require(plan["mode"] == ("saved_sheet_recalculation" if saved else "original_native_result"))
        if saved:
            _require(original is not None)
            descriptor = intent["assignment"]["selector"]["saved_sheet"]
            _require(same(plan["sheet"]["file_identity"], descriptor["sheet_file"])
                     and same(plan["original_components"]["file_identity"], descriptor["original_components_file"])
                     and same(plan["parameters"], intent["assignment"]["selector"]["parameters"]))
            inputs = [plan["sheet"], plan["original_components"]]
        else:
            _require(body["bundle"] is not None)
            job = body["bundle"]["requested_job"]["native_protein_structure"]
            _require(same(plan["expected_request"], job["request"]) and same(plan["expected_software"], job["software"]))
            actual = self._verified(body["capture"], "native_result")
            _require(len(actual) <= 1)
            _require(same(None if plan["native_result"] is None else plan["native_result"]["file_identity"],
                          actual[0] if actual else None))
            inputs = [] if plan["native_result"] is None else [plan["native_result"]]
        for row in inputs:
            file = self._file(row["file_identity"])
            _require(row["path"] == str(self._store.path / "artifacts" / file["sha256"][:2] / file["sha256"]))
        _closed(execution, ProteinWorkerExecution.__annotations__)
        _require(execution["version"] == "protein_structure_worker_execution_v1"
                 and execution["outcome"] in ("returned", "failed"))
        if execution["outcome"] == "returned":
            meta = execution["metadata"]
            _require(type(execution["returncode"]) is int and type(meta) is dict and execution["failure"] is None)
            _require(type(meta.get("native_returncode")) is int
                     and meta["native_returncode"] == execution["returncode"]
                     and type(meta.get("service_exit")) is dict and same(meta.get("policy"), POLICY))
            enforcement = meta.get("enforcement", {})
            _require(enforcement.get("memory") == "systemd_cgroup_v2_memory_max"
                     and enforcement.get("swap") == "systemd_memory_swap_max_zero")
            cgroup = meta.get("verified_cgroup", {})
            _require(type(cgroup.get("memory_max")) is int and cgroup["memory_max"] == POLICY["memory_bytes"]
                     and type(cgroup.get("memory_swap_max")) is int and cgroup["memory_swap_max"] == 0)
            _require(execution["handle_artifact_ref"] is not None)
        else:
            _require(execution["returncode"] is None and execution["metadata"] is None)
            failure = execution["failure"]
            _closed(failure, ProteinWorkerFailure.__annotations__)
            _require(type(failure["code"]) is str and bool(failure["code"])
                     and failure["code"] not in {"local_job_execution_unknown", "local_job_not_collectable",
                         "local_job_cancelled", "local_job_stop_unconfirmed", "local_job_cleanup_requires_quiescent_unit"})
            _require(failure["phase"] is None or type(failure["phase"]) is str)
            _require(all(failure[name] is None or type(failure[name]) is dict for name in ("diagnostic", "operational")))
        for field in ("stdout_artifact_ref", "stderr_artifact_ref", "handle_artifact_ref"):
            if execution[field] is not None:
                self._artifact(execution[field])
        _require(type(prepared["diagnostic_files"]) is list)
        diagnostics = {}
        for row in prepared["diagnostic_files"]:
            _closed(row, ProteinWorkerDiagnostic.__annotations__)
            _require(row["filename"] in _DIAGNOSTICS and row["filename"] not in diagnostics)
            self._artifact(row["artifact_ref"])
            diagnostics[row["filename"]] = row["artifact_ref"]
        _require(list(diagnostics) == [name for name in _DIAGNOSTICS if name in diagnostics])
        self._issues(prepared["issues"])
        for problem in prepared["issues"]:
            _require(problem["stage"] in ("capture", "native")
                     and problem["field"] in ("manifest", "receipt", "returncode")
                     and problem["artifact_role"] in (None, "native_result", "stdout", "stderr")
                     and same(problem, issue(problem["code"], stage=problem["stage"],
                         field=problem["field"], artifact_role=problem["artifact_role"])))
        execution_issue = None
        if execution["outcome"] == "failed":
            execution_issue = issue("resource_budget_exceeded" if execution["failure"]["code"] ==
                "local_job_resource_limit" else "native_process_failed", stage="native", field="receipt")
        elif execution["returncode"] != 0:
            execution_issue = issue("native_process_failed", stage="native", field="returncode")
        elif "worker-result.json" not in diagnostics:
            execution_issue = issue("native_result_missing", stage="capture", field="manifest")
        if execution_issue is not None:
            _require(result is None and any(same(execution_issue, problem) for problem in prepared["issues"]))
        qualified = prepared["worker_result_artifact_ref"]
        if result is None:
            _require(qualified is None and bool(prepared["issues"]))
            return
        validate_protein_structure_result_worker_result(result)
        _require(not prepared["issues"] and qualified == diagnostics.get("worker-result.json")
                 and result["mode"] == plan["mode"] and execution["outcome"] == "returned"
                 and execution["returncode"] == 0)
        operation = "compare" if saved else plan["expected_request"]["operation"]
        _require(result["operation"] == operation)
        self._artifact(qualified, value=result)
        for field, filename in _OUTPUTS.items():
            if result[field] is not None:
                self._file(result[field]["file_identity"])
                _require(result[field]["file_identity"]["artifact_ref"] == diagnostics.get(filename))
        if not saved and result["native_result_file"] is not None:
            _require(plan["native_result"] is not None and same(result["native_result_file"]["file_identity"],
                plan["native_result"]["file_identity"]))
        if saved and result["sheet_file"] is not None:
            _require(same(result["sheet_file"]["file_identity"], plan["sheet"]["file_identity"]))

    def _qualified(self, body, original):
        files = body["qualified_files"]
        _closed(files, ProteinQualifiedFiles.__annotations__)
        for file in files.values():
            if file is not None:
                self._file(file)
        worker = body["worker"]
        result = None if worker is None else worker["result"]
        if result is None:
            _require(all(file is None for file in files.values()) and body["calculation"] is None)
            return
        saved = body["intent"]["assignment"]["selector"]["acquisition"] == "retained_sheet_only"
        operation = result["operation"]
        if saved:
            _require(files["sequence_file"] is None and files["residue_map_file"] is None)
            if files["components_file"] is not None:
                _require(original is not None and result["sheet_file"] is not None and result["components_file"] is not None)
                for field in ("native_file", "sheet_file", "original_components_file"):
                    _require(same(files[field], original["body"]["qualified_files"][field]))
                _require(files["sheet_file"] is not None and files["original_components_file"] is not None
                         and same(files["sheet_file"], result["sheet_file"]["file_identity"])
                         and same(files["components_file"], result["components_file"]["file_identity"]))
            else:
                _require(all(file is None for file in files.values()))
        else:
            for name, field in (("native_file", "native_result_file"), ("sheet_file", "sheet_file"),
                                ("components_file", "components_file")):
                if files[name] is not None:
                    _require(result[field] is not None and same(files[name], result[field]["file_identity"]))
            if operation == "compare":
                _require(files["sequence_file"] is None and files["residue_map_file"] is None)
                if files["sheet_file"] is None:
                    _require(files["native_file"] is None and files["components_file"] is None
                             and files["original_components_file"] is None)
                else:
                    _require(files["native_file"] is not None and files["components_file"] is not None
                             and same(files["components_file"], files["original_components_file"]))
            else:
                _require(all(files[name] is None for name in ("sheet_file", "components_file", "original_components_file")))
                if operation == "inspect":
                    _require(files["sequence_file"] is None and files["residue_map_file"] is None)
                else:
                    _require((files["sequence_file"] is None) == (files["residue_map_file"] is None))
                    if files["sequence_file"] is not None:
                        _require(files["native_file"] is not None)
                        for field, role in (("sequence_file", "sequence"), ("residue_map_file", "residue_map")):
                            _require(any(same(files[field], candidate) for candidate in self._verified(body["capture"], role)))
        calculation = body["calculation"]
        if calculation is not None:
            _closed(calculation, ProjectionCalculation.__annotations__)
            _require(type(calculation["calculation_id"]) is str and bool(calculation["calculation_id"])
                     and type(calculation["input_numerical_sha256"]) is str
                     and re.fullmatch(r"[a-f0-9]{64}", calculation["input_numerical_sha256"]) is not None
                     and files["components_file"] is not None
                     and same(calculation["components_file"], files["components_file"]))
        _require((files["components_file"] is None) == (calculation is None))

    def _body(self, body, intent, *, active):
        _closed(body, ProteinResultBody.__annotations__)
        _require(body["version"] == "protein_structure_result_body_v1" and same(body["intent"], intent)
                 and type(body["native_success"]) is bool and type(body["capture_complete"]) is bool)
        self._issues(body["issues"])
        proof, observation = body["handoff_proof"], body["observation"]
        if proof is not None:
            self.validate_handoff_proof(proof, intent=intent)
        if observation is not None:
            _require(_OBSERVATION.is_valid(observation), "invalid_schema")
            validate_resource_observation(observation)
            from .terminal_scientific_evidence import is_terminal_target, validate_terminal_observation
            if is_terminal_target(intent['target']):
                validate_terminal_observation(observation, intent, self._store, self.owner.run_id)
        _require(body["observation_origin"] in ("selected_native_observation", "original_saved_observation", "not_observed"))
        _require((observation is None) == (body["observation_origin"] == "not_observed"))
        saved = intent["assignment"]["selector"]["acquisition"] == "retained_sheet_only"
        original = None
        if saved and body["original_custody"] is not None:
            descriptor = intent["assignment"]["selector"]["saved_sheet"]
            custody = descriptor["custody"]
            _require(same(body["original_custody"], custody))
            original = self._read_completed(episode_id=custody["result_episode_id"],
                operation_key=custody["result_operation_key"], scope=intent["scope"], active=active)
            _require(same(original["publication"]["custody"], custody)
                     and any(same(descriptor, candidate) for candidate in original["publication"]["facts"][_SAVED]))
            # The original receipt proves the operand existed; the frozen
            # delivery independently proves this assignment actually received
            # its exact descriptor and recalculate grant. This port is metadata
            # only and never calls the operand byte validators.
            context = self._returns.context(intent["episode_id"])
            received = self._returns.authenticate_received_saved_sheet(context, descriptor, required_use="recalculate")
            _require(same(received["custody"], custody)
                     and same(received["sheet_file"], descriptor["sheet_file"])
                     and same(received["original_components_file"], descriptor["original_components_file"]))
            for name in ("handoff_proof", "capture", "bundle"):
                if body[name] is not None:
                    _require(same(body[name], original["body"][name]))
            if observation is not None:
                _require(body["observation_origin"] == "original_saved_observation"
                         and same(observation, original["body"]["observation"]))
        elif saved:
            _require(body["capture"] is None and body["bundle"] is None and body["worker"] is None)
        else:
            _require(body["original_custody"] is None)
            if observation is not None:
                _require(body["observation_origin"] == "selected_native_observation")
        if proof is None:
            _require(body["capture"] is None and body["bundle"] is None and body["worker"] is None)
        if body["capture"] is not None:
            self._capture(body["capture"], body["bundle"], intent)
            from .terminal_scientific_evidence import is_terminal_target
            if is_terminal_target(intent['target']):
                from .native_protein_structure_acquisition import _validate_terminal_capture_files
                command_proof = proof['start_receipt']['outcome']['native_outcome']['scientific_command_proof']
                _require(same(body['capture']['original_plan'], command_proof['original_plan']))
                _validate_terminal_capture_files(body['capture'], command_proof)
        else:
            _require(body["bundle"] is None and body["worker"] is None)
        bundle = body["bundle"]
        _require(body["native_success"] == (bundle is not None and bundle["returncode"] == 0
                 and bundle["native_status"] == "complete"))
        _require(body["capture_complete"] == (body["capture"] is not None and body["capture"]["capture_complete"]))
        if bundle is not None:
            from .terminal_scientific_evidence import is_terminal_target
            if is_terminal_target(intent['target']):
                command_proof = proof['start_receipt']['outcome']['native_outcome']['scientific_command_proof']
                _require(same(bundle['identity'], command_proof['original_plan']['identity']))
            else:
                detail = proof["body"]["receipt"]["outcome"]["native_outcome"]
                _require(bundle["identity"]["operation_key"] == detail["attempt_operation_key"]
                         and bundle["identity"]["attempt_id"] == detail["attempt_id"])
        if body["worker"] is not None:
            self._worker(body["worker"], body, original)
        self._qualified(body, original)
        return original

    def _descriptors(self, facts, body, publication, original):
        selector = body["intent"]["assignment"]["selector"]
        files, custody = body["qualified_files"], publication["custody"]
        saved = selector["acquisition"] == "retained_sheet_only"
        descriptors = list(facts[_SEQUENCE])
        for projection in facts[_PROJECTION]:
            if projection["family"] == "extracted_sequence" and projection["delivery"]["kind"] == "values":
                descriptors.extend(cell["value"] for row in projection["delivery"]["rows"] for cell in row["values"]
                    if cell["field"] == "descriptor" and cell["value"] is not None)
        _require(len(facts[_SAVED]) <= 1 and len(facts[_SEQUENCE]) <= 1)
        refs = {}
        for record in publication["reference_records"]:
            self._record(record, "reference")
            _require(record["id"] not in refs)
            refs[record["id"]] = record
        used = set()
        for descriptor in descriptors:
            validate_structure_sequence_descriptor(descriptor)
            _require(not saved and bool(selector["sequence_allowed_uses"])
                     and descriptor["allowed_uses"] == selector["sequence_allowed_uses"]
                     and same(descriptor["custody"], custody)
                     and same(descriptor["sequence_file"], files["sequence_file"])
                     and same(descriptor["residue_map_file"], files["residue_map_file"]))
            request = body["bundle"]["requested_job"]["native_protein_structure"]["request"]
            _require(request["operation"] == "extract_sequence" and same(request["selection"], descriptor["selection"])
                     and same(descriptor["structure_file"], request["selection"]["file_identity"])
                     and any(same(descriptor["structure_file"], file) for file in self._verified(body["capture"], "single_structure")))
            record = refs.get(descriptor["reference_ref"])
            _require(record is not None)
            expected = {"reference_type": "protein", "source_ref": custody["source_ref"],
                "accession": "structure_sequence_" + descriptor["residue_map_file"]["sha256"],
                "label": "Structure-derived protein sequence", "sequence_ref": descriptor["sequence_file"]["artifact_ref"],
                "molecule": "protein", "length": descriptor["sequence_length"], "term_refs": [], "context_refs": [], "anchor": None}
            self._record(record, "reference", payload=expected)
            _require(descriptor["sequence_length"] == descriptor["sequence_file"]["byte_length"])
            used.add(record["id"])
        _require(set(refs) == used)
        for descriptor in facts[_SAVED]:
            validate_saved_sheet_descriptor(descriptor)
            _require(selector["return_saved_sheet"] and descriptor["allowed_uses"] == ["recalculate", "select_projection", "use_transform"])
            if saved:
                _require(original is not None and same(descriptor, selector["saved_sheet"]))
            else:
                _require(same(descriptor["custody"], custody)
                         and same(descriptor["sheet_file"], files["sheet_file"])
                         and same(descriptor["original_components_file"], files["original_components_file"])
                         and descriptor["original_mode"] == body["bundle"]["requested_job"]["native_protein_structure"]["request"]["parameters"]["mode"])

    def _publication(self, publication, body, original):
        _closed(publication, ProteinResultPublication.__annotations__)
        _require(publication["version"] == "protein_structure_result_publication_v1"
                 and publication["body_sha256"] == digest(body)
                 and publication["result_receipt_key"] == _receipt_key(body["intent"])
                 and type(publication["delivery_complete"]) is bool)
        _closed(publication["facts"], ProteinFactGroups.__annotations__)
        _require(all(type(rows) is list for rows in publication["facts"].values())
                 and type(publication["reference_records"]) is list and type(publication["record_refs"]) is list)
        facts, intent = publication["facts"], body["intent"]
        source, custody = publication["source_record"], publication["custody"]
        saved = intent["assignment"]["selector"]["acquisition"] == "retained_sheet_only"
        if source is not None:
            _require(body["handoff_proof"] is not None and body["bundle"] is not None and custody is not None)
            if saved:
                _require(original is not None and same(source, original["publication"]["source_record"]))
                self._record(source, "source")
            else:
                worker = body["worker"]
                payload = protein_structure_source_payload(bundle=body["bundle"], capture=body["capture"],
                    worker_result=None if worker is None else worker["result"])
                self._record(source, "source", payload=payload)
            expected = {"run_id": intent["run_id"], "result_episode_id": intent["episode_id"],
                "result_operation_key": intent["operation_key"], "result_receipt_key": _receipt_key(intent),
                "handoff_ref": intent["assignment"]["handoff_ref"], "source_ref": source["id"],
                "bundle_artifact_ref": body["capture"]["bundle_file"]["artifact_ref"],
                "original_request_sha256": intent["original_request_sha256"]}
            _require(_CUSTODY.is_valid(custody) and same(custody, expected)
                     and publication["record_refs"] == [source["id"]])
        else:
            _require(custody is None and not publication["record_refs"] and not publication["reference_records"])
            _require(not facts[_PROJECTION] and not facts[_SAVED] and not facts[_SEQUENCE])
        selector = intent["assignment"]["selector"]
        selected = {row["projection_id"]: row for row in selector["projections"]}
        success, failed = [], []
        for row in facts[_PROJECTION]:
            validate_protein_structure_projection_result(row)
            key = row["projection_id"]
            _require(key in selected and key not in success and same(row["selection"], selected[key])
                     and row["family"] == selected[key]["family"] and same(row["custody"], custody)
                     and same(row["calculation"], body["calculation"]))
            success.append(key)
            if row["delivery"]["kind"] == "artifact":
                self._file(row["delivery"]["table_file"])
        for row in facts[_FAILURE]:
            validate_protein_structure_failure_return(row)
            _require(same(row["custody"], custody)
                     and any(same(row["issue"], problem) for problem in body["issues"]))
            key = row["projection_id"]
            if key is not None:
                _require(key in selected and key not in failed and key not in success
                         and row["issue"]["stage"] == "projection" and row["issue"]["field"] == "projection_fields")
                failed.append(key)
        _require(success == [key for key in selected if key in success]
                 and failed == [key for key in selected if key in failed])
        self._descriptors(facts, body, publication, original)
        accounting = publication["accounting"]
        _closed(accounting, SelectionAccounting.__annotations__)
        status = intent["tool_name"] == "execution.results.status"
        expected = {"projection_ids": success, "failed_projection_ids": failed,
            "saved_sheet": "not_requested" if status or not selector["return_saved_sheet"] else (
                "published" if facts[_SAVED] else "unavailable"),
            "sequence": "not_requested" if status or not selector["sequence_allowed_uses"] else (
                "published" if facts[_SEQUENCE] else "unavailable")}
        _require(same(accounting, expected))
        accounted = set(success) | set(failed) == set(selected)
        for field, role in (("saved_sheet", None), ("sequence", "sequence")):
            if expected[field] == "unavailable":
                present = any(row["projection_id"] is None and same(row["issue"], issue("selected_field_unavailable",
                    stage="projection", field="descriptor", artifact_role=role)) for row in facts[_FAILURE])
                _require(present)
        worker = body["worker"]
        qualified = worker is not None and worker["result"] is not None
        complete = not status and source is not None and qualified and accounted
        if saved:
            complete = complete and original is not None and all(body["qualified_files"][name] is not None
                for name in ("sheet_file", "original_components_file", "components_file"))
        else:
            complete = complete and body["capture_complete"]
        _require(publication["delivery_complete"] == bool(complete))
        if status:
            _require(all(not rows for rows in facts.values()) and not publication["record_refs"]
                     and not publication["reference_records"] and source is None and custody is None
                     and body["worker"] is None and body["calculation"] is None)
        self._family(publication, body)

    def _family(self, publication, body):
        refs = publication["family_artifact_refs"]
        _require(type(refs) is list and refs == list(dict.fromkeys(refs)), "invalid_schema")
        for ref in refs:
            self._artifact(ref)
        prefix = []
        capture = body["capture"]
        if capture is not None:
            if capture["bundle_file"] is not None:
                prefix.append(capture["bundle_file"]["artifact_ref"])
            prefix.extend(row["observed"]["artifact_ref"] for row in capture["files"] if row["observed"] is not None)
        worker = body["worker"]
        if worker is not None:
            prepared, execution = worker["prepared"], worker["execution"]
            prefix.extend(prepared[key] for key in ("plan_artifact_ref", "execution_receipt_artifact_ref", "worker_result_artifact_ref")
                if prepared[key] is not None)
            prefix.extend(row["artifact_ref"] for row in prepared["diagnostic_files"])
            prefix.extend(execution[key] for key in ("stdout_artifact_ref", "stderr_artifact_ref", "handle_artifact_ref")
                if execution[key] is not None)
        prefix = list(dict.fromkeys(prefix))
        _require(refs[:len(prefix)] == prefix)
        suffix = [file["artifact_ref"] for file in body["qualified_files"].values() if file is not None]
        suffix.extend(row["delivery"]["table_file"]["artifact_ref"] for row in publication["facts"][_PROJECTION]
            if row["delivery"]["kind"] == "artifact")
        # Lifecycle control identities have no extra authority record. Their
        # original order is frozen in the publication and runtime outcome. Only
        # existing artifact metadata is read here, including after byte loss.
        cursor = len(prefix)
        seen = set(prefix)
        for ref in suffix:
            if ref not in seen:
                _require(ref in refs[cursor:])
                cursor = refs.index(ref, cursor) + 1
                seen.add(ref)
        if worker is None:
            _require(refs == list(dict.fromkeys([*prefix, *suffix])))

    def _validate(self, receipt, intent, *, active=()):
        receipt = _json(receipt)
        _closed(receipt, ProteinResultReceipt.__annotations__)
        _require(receipt["version"] == "native_protein_structure_acquired_result_v1")
        original = self._body(receipt["body"], intent, active=active)
        self._publication(receipt["publication"], receipt["body"], original)
        return receipt

    def _controls(self, fd, intent, *, active=()):
        receipt = _read(fd, "receipt.json")
        if receipt is None:
            return None
        _require(same(_read(fd, "intent.json"), intent)
                 and same(_read(fd, "body.json"), receipt.get("body"))
                 and same(_read(fd, "publication.json"), receipt.get("publication")))
        receipt = self._validate(receipt, intent, active=active)
        _require(same(_read(fd, "handoff-proof.json"), receipt["body"]["handoff_proof"])
                 and same(_read(fd, "observation.json"), receipt["body"]["observation"]))
        return receipt

    def read_staged(self, action: ProteinResultAction) -> ProteinResultReceipt | None:
        fd = self._fd(action)
        receipt = self._controls(fd, action.intent, active=((action.intent["episode_id"], action.intent["operation_key"]),))
        row = self._selected(action.intent)
        _require(receipt is not None or row["result"] is None)
        if receipt is not None:
            if row["result"] is not None:
                self._match_outcome(row, receipt)
        return deepcopy(receipt)

    def publish(self, action, *, body, publication) -> ProteinResultReceipt:
        fd = self._fd(action)
        receipt = self._validate({"version": "native_protein_structure_acquired_result_v1",
            "body": body, "publication": publication}, action.intent,
            active=((action.intent["episode_id"], action.intent["operation_key"]),))
        _require(same(_read(fd, "handoff-proof.json"), body["handoff_proof"])
                 and same(_read(fd, "observation.json"), body["observation"]))
        selected = self._selected(action.intent)
        if selected["result"] is not None:
            self._match_outcome(selected, receipt)
        _immutable(fd, "body.json", receipt["body"])
        _immutable(fd, "publication.json", receipt["publication"])
        _immutable(fd, "receipt.json", receipt)
        return deepcopy(receipt)

    @staticmethod
    def _match_outcome(row, receipt):
        _require(row["result"] is not None)
        outcome = json.loads(row["result"])
        if "pending_work_after_action" in outcome:
            from .waiting import validate_pending
            validate_pending(outcome.pop("pending_work_after_action"))
        _require(same(outcome, _outcome(receipt)))

    def _read_completed(self, *, episode_id, operation_key, scope, active):
        active = tuple(dict.fromkeys((*_READING.get(), *active)))
        marker = (episode_id, operation_key)
        _require(marker not in active)
        token = _READING.set((*active, marker))
        try:
            return self._completed(episode_id=episode_id, operation_key=operation_key, scope=scope, active=active)
        finally:
            _READING.reset(token)

    def _completed(self, *, episode_id, operation_key, scope, active):
        marker = (episode_id, operation_key)
        _require(marker not in active)
        context = self._returns.context(episode_id)
        self._assignment(context)
        self._store.validate_scope(scope)
        self._store.validate_scope(plain(context.scope), parent_scope=scope)
        directory = self.action_directory(episode_id=episode_id, operation_key=operation_key)
        # A loose file never substitutes for the selected completed runtime row.
        selected = self._selected({"episode_id": episode_id, "operation_key": operation_key,
            "tool_name": "execution.results.collect", "arguments": {}}, completed=True)
        try:
            with _directory(directory.parent.parent) as root_fd:
                _require(same(_read(root_fd, "assignment.json"), self._manifest(context)))
            with _directory(directory) as fd:
                intent = _read(fd, "intent.json")
                _closed(intent, ProteinResultIntent.__annotations__)
                expected = self._intent(context, intent["target"], "execution.results.collect", {}, operation_key)
                _require(same(intent, expected))
                receipt = self._controls(fd, expected, active=(*active, marker))
                _require(receipt is not None)
        except OSError as error:
            raise ValueError("invalid_output_path") from error
        self._match_outcome(selected, receipt)
        return deepcopy(receipt)

    def read_completed(self, *, episode_id: str, operation_key: str, scope: dict) -> ProteinResultReceipt:
        return self._read_completed(episode_id=episode_id, operation_key=operation_key,
            scope=plain(scope), active=())

    def completed_receipts(self, context) -> list[ProteinResultReceipt]:
        self._returns.authenticate(context, allow_unsaved=True)
        self._assignment(context)
        rows = self._store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? ORDER BY decision_index", (self.owner.run_id, context.episode_id))
        result = []
        for row in rows:
            action = json.loads(row["action"])
            if action.get("kind") != "tool" or action.get("tool") != "execution.results.collect" or row["result"] is None:
                continue
            outcome = json.loads(row["result"])
            if outcome.get("status") != "completed":
                continue
            result.append(self.read_completed(episode_id=context.episode_id,
                operation_key=f'{self.owner.run_id}:{context.episode_id}:{row["decision_index"]}', scope=plain(context.scope)))
        return result

    def owns_reference(self, reference: str) -> bool:
        """Classify existing provenance across runs, without granting access."""
        if type(reference) is not str:
            return False
        try:
            record = self._store.get(reference)
        except ValueError:
            return False
        kind = record.get("record_type")
        if kind == "source":
            return record.get("provider") == "episode.execution_result" and record.get("version") == "native_protein_structure_bundle_v1"
        if kind == "reference":
            source = self._store.get(record["source_ref"])
            return source.get("provider") == "episode.execution_result" and source.get("version") == "native_protein_structure_bundle_v1"
        if kind != "artifact":
            return False
        table = self._store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_actions'").fetchone()
        if table is not None:
            for row in self._store.db.execute("SELECT result FROM runtime_actions WHERE result IS NOT NULL"):
                outcome = json.loads(row[0])
                receipt = outcome.get("result")
                if type(receipt) is not dict or receipt.get("version") != "native_protein_structure_acquired_result_v1":
                    continue
                publication = receipt.get("publication")
                if type(publication) is dict and publication.get("version") == "protein_structure_result_publication_v1" \
                        and reference in publication.get("family_artifact_refs", []):
                    return True
        # Ordinary source provenance is also sufficient classification; it
        # supplies no authorization and does not expand any received grant.
        for row in self._store.db.execute("SELECT data FROM records WHERE record_type='source' "
                "AND json_extract(data,'$.provider')='episode.execution_result' "
                "AND json_extract(data,'$.version')='native_protein_structure_bundle_v1'"):
            source = json.loads(row[0])
            if reference == source.get("artifact_ref") or reference in source.get("auxiliary_artifact_refs", []):
                return True
        return False


__all__ = ["ProteinResultIntent", "ProteinQualifiedFiles", "ProteinHandoffProof", "ProteinResultBody",
           "SelectionAccounting", "ProteinResultPublication", "ProteinResultReceipt", "ResourceObservation",
           "ProteinResultAction", "ProteinResultReceipts"]
