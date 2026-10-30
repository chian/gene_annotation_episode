"""Selected chromatin action controls and historical completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Historical checks use frozen controls and Store metadata, never scientific bytes.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
from typing import Literal, TypedDict

from method_loop.identities import EpisodeRef

from .communication import plain
from .domain import identity
from .episode_bindings import BindingContext
from .execution_contracts import canonical, digest, validate_target
from .chromatin_interaction_contracts import (
    Failure, NativeFileIdentity, RequestedProjection, _finite_json,
    validate_chromatin_record,
)
from .chromatin_interaction_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    validate_chromatin_fact_values,
)
from .chromatin_interaction_result_worker import (
    validate_chromatin_result_worker_plan, validate_chromatin_result_worker_result,
    _validate_capture,
)
from .native_chromatin_interaction_capture import validate_chromatin_native_capture
from .native_chromatin_interaction_contracts import (
    POLICY, TABLE_ROLES, TABLE_NAMES, chromatin_driver_argv,
    validate_chromatin_requested_job, validate_chromatin_run_plan, _dependency_roots,
)
from .practical_execution_records import validate_receipt
from .practical_receipt_information import PracticalReceiptInformation
from .progress_records import validate_resource_observation


VERSION = "native_chromatin_interaction_acquired_result_v1"


class ChromatinInteractionResultIntent(TypedDict):
    version: Literal["chromatin_interaction_result_intent_v1"]
    run_id: str
    episode_id: str
    path: list[list[str]]
    scope: dict
    assignment: dict
    original_request_sha256: str
    operation_key: str
    tool_name: Literal["execution.results.status", "execution.results.collect"]
    arguments: dict
    target: dict


class ChromatinInteractionHandoffProof(TypedDict):
    source_record: dict
    body: dict
    assignment_snapshot: dict
    start_receipt: dict


class ChromatinInteractionNativeSnapshot(TypedDict):
    original_plan: dict
    plan_file: NativeFileIdentity
    handle: dict
    handle_file: NativeFileIdentity
    request: dict
    request_raw: str
    request_file: NativeFileIdentity
    started_marker: dict | None
    started_marker_file: NativeFileIdentity | None
    driver_started: bool | None


class ChromatinInteractionOrigin(TypedDict):
    episode_id: str
    operation_key: str


class ChromatinInteractionQualifiedFiles(TypedDict):
    sheet: NativeFileIdentity | None
    components: NativeFileIdentity | None
    projection: NativeFileIdentity | None
    diagnostics: NativeFileIdentity | None
    tables: list[dict]


class ChromatinInteractionFactGroups(TypedDict):
    chromatin_interaction_projection: list[RequestedProjection]
    chromatin_interaction_saved_sheets: list[dict]
    chromatin_interaction_failures: list[Failure]


class ChromatinInteractionSheetEvidence(TypedDict):
    version: Literal["chromatin_interaction_sheet_evidence_v1"]
    sheet_file: NativeFileIdentity
    request_sha256: str
    populations: list[dict]
    data_tables: list[dict]


class ChromatinInteractionResultReceipt(TypedDict):
    version: Literal["native_chromatin_interaction_acquired_result_v1"]
    intent: ChromatinInteractionResultIntent
    handoff_proof: ChromatinInteractionHandoffProof
    original_origins: list[ChromatinInteractionOrigin]
    observation: dict | None
    native: ChromatinInteractionNativeSnapshot | None
    source_action_file: NativeFileIdentity | None
    writer_closure_file: NativeFileIdentity | None
    capture: dict | None
    worker_plan: dict | None
    worker_capture: dict | None
    worker_execution: dict | None
    qualified_files: ChromatinInteractionQualifiedFiles
    projection: RequestedProjection | None
    host_failures: list[Failure]
    facts: ChromatinInteractionFactGroups
    sheet_evidence: ChromatinInteractionSheetEvidence | None
    acquired_population: str | None
    delivery_complete: bool


@dataclass(frozen=True)
class ChromatinInteractionResultAction:
    intent: ChromatinInteractionResultIntent
    directory: Path


_READING = ContextVar("chromatin_interaction_receipt_reading", default=())
_READ_CACHE = ContextVar("chromatin_interaction_receipt_read_cache", default=None)
_OUTPUTS = ("sheet", "components", "projection", "diagnostics")


def _finite_json_copy(value):
    _finite_json(value)
    return deepcopy(value)


def require(condition, code="chromatin_interaction_result_authority_conflict"):
    if not condition:
        raise ValueError(code)


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), "chromatin_interaction_result_invalid_record")


def same(left, right):
    return canonical(left) == canonical(right)


def decode(raw, *, newline=False, canonical_bytes=True):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "chromatin_interaction_result_duplicate_key")
            result[key] = value
        return result
    value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs))
    require(not canonical_bytes or raw == canonical(value).encode("utf-8") + (b"\n" if newline else b""),
            "chromatin_interaction_result_noncanonical_control")
    return value


@contextmanager
def directory(path, *, create=False):
    value = str(path)
    pure = PurePosixPath(value)
    require(pure.is_absolute() and str(pure) == value and value != "/" and ".." not in pure.parts
            and not any(c in value for c in "\0\r\n\\"), "chromatin_interaction_result_invalid_path")
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in pure.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        require(os.fstat(fd).st_uid == os.geteuid(), "chromatin_interaction_result_invalid_path")
        yield fd


@contextmanager
def regular(fd, name, *, flags=os.O_RDONLY):
    require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
    handle = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        require(stat.S_ISREG(os.fstat(handle).st_mode), "chromatin_interaction_result_invalid_path")
        yield handle
    finally:
        os.close(handle)


def read_control(path):
    try:
        with directory(path.parent) as fd, regular(fd, path.name) as handle, os.fdopen(os.dup(handle), "rb") as stream:
            raw = stream.read()
    except FileNotFoundError:
        return None
    value = decode(raw, newline=path.name == "assignment.json" and raw.endswith(b"\n"))
    require(type(value) is dict, "chromatin_interaction_result_invalid_record")
    return value


def immutable(path, value):
    value = _finite_json_copy(value)
    with directory(path.parent, create=True) as fd:
        previous = read_control(path)
        if previous is not None:
            require(same(previous, value), "chromatin_interaction_result_control_conflict")
            return
        temporary = "." + path.name + "." + secrets.token_hex(16) + ".writing"
        try:
            with regular(fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as handle:
                with os.fdopen(os.dup(handle), "wb") as stream:
                    stream.write(canonical(value).encode("utf-8") + (b"\n" if path.name == "assignment.json" else b""))
                    stream.flush()
                os.fchmod(handle, 0o444)
                os.fsync(handle)
            try:
                os.link(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except FileExistsError:
                require(same(read_control(path), value), "chromatin_interaction_result_control_conflict")
            os.fsync(fd)
        finally:
            os.unlink(temporary, dir_fd=fd)


def empty_facts() -> ChromatinInteractionFactGroups:
    return {source: [] for source in FACT_SOURCES}


def empty_files() -> ChromatinInteractionQualifiedFiles:
    return {**{role: None for role in _OUTPUTS}, "tables": []}


def unique(rows):
    result, seen = [], set()
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


def outcome(receipt):
    refs = list(dict.fromkeys(file["artifact_ref"] for bundle in receipt["facts"][SAVED_SOURCE]
        for file in (bundle["sheet"], *bundle["tables"])))
    return {"status": "completed", "record_refs": refs, "changed_record_refs": refs,
            "result": deepcopy(receipt), "feedback": None}


def qualified_files(capture, execution):
    result = empty_files()
    if capture is None or capture["result"] is None or execution is None:
        return result
    validate_chromatin_record("WorkerCapture", capture)
    declared = validate_chromatin_result_worker_result(capture["result"])["outputs"]
    require(len(declared) == len(capture["outputs"]))
    success = (execution["returncode"] == 0 and execution["failure"] is None
        and execution["terminal"] is True and execution["quiescent"] is True)
    for expected, row in zip(declared, capture["outputs"]):
        require(row["role"] == expected["role"] and row["table_key"] == expected["table_key"]
            and same(row["capture"]["declared"], expected["declaration"]))
        _validate_capture(row["capture"])
        file = deepcopy(row["capture"]["observed"]) if success and row["capture"]["outcome"] == "verified" else None
        if row["role"] == "table":
            result["tables"].append({"table_key": row["table_key"], "file": file})
        else:
            result[row["role"]] = file
    return result


def closure_value(receipt):
    return {"version": "chromatin_interaction_writer_closure_v1", "intent_sha256": digest(receipt["intent"]),
        "native": receipt["native"], "observation": receipt["observation"]}


class ChromatinInteractionResultReceipts:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self._active = {}

    @property
    def returns(self):
        return self.owner.native_chromatin_interaction_returns

    def action_directory(self, episode_id, operation_key):
        return self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id]) / "native-chromatin-interaction-actions" / digest(operation_key)

    def _context(self, context, *, allow_unsaved=False):
        self.returns.authenticate(context, allow_unsaved=allow_unsaved)
        require(isinstance(context, BindingContext) and context.role == "results")
        assignment = plain(context.assignment)
        closed(assignment, ("version", "handoff_ref", "selector"))
        require(assignment["version"] == "execution_results_assignment_v1")
        validate_chromatin_record("ResultSelector", assignment["selector"])
        self.store.validate_scope(plain(context.scope))
        if not allow_unsaved or self.store.db.execute("SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (context.run_id, context.episode_id)).fetchone():
            require(len(context.path) > 1)
            parent_id = EpisodeRef(context.run_id, context.path[:-1]).episode_id
            self.returns._commission(self.returns.context(parent_id), context)
        return assignment

    def _selected(self, intent):
        row = self.owner._selected_result_action(intent["episode_id"], intent["operation_key"],
            intent["tool_name"], intent["arguments"])
        require(same(json.loads(row["action"]), {"kind": "tool", "tool": intent["tool_name"], "arguments": {}}))
        return row

    def _target(self, context, assignment, target):
        target = validate_target(_finite_json_copy(target))
        require(target["run_id"] == self.owner.run_id == context.run_id and target["resource_kind"] == "local"
            and target["handle"] == assignment["handoff_ref"])
        requested = validate_chromatin_requested_job(target["assignment"]["requested_job"])
        require(target["request_sha256"] == digest(requested)
            and target["assignment"]["resource_id"] == target["resource_id"])
        self.store.validate_scope(target["scope"], parent_scope=plain(context.scope))
        resource = self.owner.resources.get(target["resource_id"])
        require(type(resource) is dict and resource["kind"] == "local" and same(resource["policy"], POLICY))
        reader = self.owner.job_progress_provider.targets
        require(same(reader.resources.get(target["resource_id"]), resource)
            and target["resource_id"] in reader.operations)
        reader.operations[target["resource_id"]].validate_assignment(target["assignment"])
        selector = assignment["selector"]
        from .chromatin_interaction_execution_information import validate_chromatin_result_selector
        request = requested["native_chromatin_interactions"]["request"]
        validate_chromatin_result_selector(selector, request=request)
        return target

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ("execution.results.status", "execution.results.collect")
            and type(arguments) is dict and arguments == {})
        value = {"version": "chromatin_interaction_result_intent_v1", "run_id": context.run_id,
            "episode_id": context.episode_id, "path": plain(context.path), "scope": plain(context.scope),
            "assignment": assignment, "original_request_sha256": digest(plain(context.request)),
            "operation_key": operation_key, "tool_name": tool_name, "arguments": {},
            "target": self._target(context, assignment, target)}
        self._selected(value)
        return value

    @asynccontextmanager
    async def locked_action(self, context, *, target, tool_name, arguments, operation_key):
        intent = self.intent(context, target, tool_name, arguments, operation_key)
        require(not self.store.db.in_transaction)
        root = self.action_directory(context.episode_id, operation_key)
        immutable(root.parent.parent / "assignment.json", {"run_id": context.run_id,
            "episode_id": context.episode_id, "assignment": plain(context.assignment), "scope": plain(context.scope)})
        with directory(root, create=True) as fd, regular(fd, ".action.lock", flags=os.O_RDWR | os.O_CREAT) as lock:
            task = asyncio.create_task(asyncio.to_thread(fcntl.flock, lock, fcntl.LOCK_EX))
            acquired = False
            try:
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    while not task.done():
                        try:
                            await asyncio.shield(task)
                        except asyncio.CancelledError:
                            pass
                    task.result()
                    acquired = True
                    raise
                acquired = True
                require(same(intent, self.intent(context, target, tool_name, arguments, operation_key)))
                immutable(root / "intent.json", intent)
                action = ChromatinInteractionResultAction(deepcopy(intent), root)
                self._active[id(action)] = action
                try:
                    yield action
                finally:
                    self._active.pop(id(action), None)
            finally:
                if acquired:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def require_action(self, action):
        require(self._active.get(id(action)) is action and action.directory == self.action_directory(
            action.intent["episode_id"], action.intent["operation_key"]))
        require(same(read_control(action.directory / "intent.json"), action.intent))
        self._selected(action.intent)

    def file_metadata(self, file, *, value=None, newline=False):
        file = validate_chromatin_record("NativeFileIdentity", file)
        metadata = self.store.get(file["artifact_ref"])
        closed(metadata, ("id", "record_type", "sha256", "size", "media_type"))
        require(metadata["record_type"] == "artifact" and metadata["id"] == file["artifact_ref"]
            == "artifact_" + file["sha256"] and metadata["sha256"] == file["sha256"]
            and type(metadata["size"]) is int and metadata["size"] == file["size_bytes"])
        if value is not None:
            raw = canonical(value).encode("utf-8") + (b"\n" if newline else b"")
            require(hashlib.sha256(raw).hexdigest() == file["sha256"] and len(raw) == file["size_bytes"])
        return file

    def _artifact_value(self, reference, value):
        metadata = self.store.get(reference)
        self.file_metadata({"artifact_ref": reference, "sha256": metadata["sha256"],
            "size_bytes": metadata["size"], "format": "application/json"}, value=value)

    def validate_handoff(self, proof, intent):
        closed(proof, ChromatinInteractionHandoffProof.__annotations__)
        source, body, snapshot, start = (proof[name] for name in ChromatinInteractionHandoffProof.__annotations__)
        practical = PracticalReceiptInformation(self.store, self.owner.run_id)
        qualified, selected = practical._qualify(body, snapshot, intent["scope"])
        require(same(qualified, body) and selected["result"] is not None)
        self._artifact_value(source["artifact_ref"], body)
        self._artifact_value(source["request_ref"], snapshot)
        payload = practical._source_payload(body, source["artifact_ref"], source["request_ref"])
        require(same(source, self.store.get(source["id"])) and source["origin"] == "tool"
            and source["record_type"] == "source" and source["id"] == identity("source", {"origin": "tool", "record": payload})
            and same({k: v for k, v in source.items() if k not in ("id", "record_type", "origin")}, payload)
            and len(practical._sources(source["accession"])) == 1)
        receipt, assignment = body["receipt"], snapshot["assignment"]
        original = self.returns.context(body["episode_id"])
        require(same(plain(original.assignment), assignment) and same(plain(original.scope), body["scope"]))
        require(len(original.path) > 1)
        self.returns._commission(self.returns.context(EpisodeRef(self.owner.run_id, original.path[:-1]).episode_id), original)
        selected_outcome = json.loads(selected["result"])
        require(selected_outcome.get("status") in ("completed", "partial")
            and same(selected_outcome.get("result"), receipt) and source["id"] in selected_outcome.get("record_refs", []))
        require(receipt["tool_name"] in ("practical.job.start", "practical.job.status", "practical.job.collect"))
        requested = validate_chromatin_requested_job(assignment["requested_job"])
        job = receipt["outcome"].get("facts", {}).get("requested_job", {})
        detail = receipt["outcome"].get("native_outcome") or {}
        key = detail.get("attempt_operation_key")
        require(type(key) is str and detail.get("attempt_id") == digest(key))
        require(job.get("requested_job_sha256") == digest(requested) and job.get("argv") == requested["argv"]
            and same(job.get("environment"), requested["environment"]) and job.get("resource_kind") == "local"
            and type(job.get("handoff")) is dict and job["execution_id"] == job["handoff"].get("execution_id")
            and job["handoff"].get("monitor_operation") == "practical.job.status"
            and job["handoff"].get("results_operation") == "practical.job.collect")
        start = validate_receipt(start)
        start_row = practical._selected(start)
        require(start_row["result"] is not None and start["tool_name"] == "practical.job.start"
            and start["operation_key"] == key and start["run_id"] == self.owner.run_id
            and start["episode_id"] == body["episode_id"] and start["assignment_sha256"] == body["assignment_sha256"])
        start_outcome = json.loads(start_row["result"])
        require(start_outcome.get("status") in ("completed", "partial") and same(start_outcome.get("result"), start))
        start_job = start["outcome"].get("facts", {}).get("requested_job", {})
        start_detail = start["outcome"].get("native_outcome") or {}
        require(start_job.get("execution_id") == job["execution_id"] and start_job.get("requested_job_sha256") == digest(requested)
            and start_detail.get("attempt_id") == detail["attempt_id"] and start_detail.get("attempt_operation_key") == key)
        expected = {"version": "execution_target_v1", "handle": source["id"], "run_id": self.owner.run_id,
            "resource_id": assignment["resource_id"], "resource_kind": "local", "execution_id": job["execution_id"],
            "request_sha256": digest(requested), "origin_episode_id": body["episode_id"],
            "assignment": assignment, "scope": body["scope"]}
        require(same(validate_target(expected), intent["target"]))
        require(job["execution_id"] == str(Path(assignment["workspace"]) / ".episode-operations" /
            digest({"run": self.owner.run_id, "episode": body["episode_id"]}) / digest(key) / "native.json"))

    def read_handoff(self, action):
        self.require_action(action)
        path = action.directory / "handoff.json"
        saved = read_control(path)
        if saved is None:
            target = action.intent["target"]
            practical = PracticalReceiptInformation(self.store, self.owner.run_id)
            body = practical.read(target["handle"], action.intent["scope"])
            source = self.store.get(target["handle"])
            snapshot = practical._artifact_json(source["request_ref"])
            key = body["receipt"]["outcome"]["native_outcome"]["attempt_operation_key"]
            prefix = f'{self.owner.run_id}:{body["episode_id"]}:'
            suffix = key.removeprefix(prefix)
            require(key.startswith(prefix) and re.fullmatch(r"0|[1-9][0-9]*", suffix) is not None)
            row = self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                (self.owner.run_id, body["episode_id"], int(suffix))).fetchone()
            require(row is not None and row["result"] is not None)
            saved = {"source_record": source, "body": body, "assignment_snapshot": snapshot,
                "start_receipt": json.loads(row["result"])["result"]}
            self.validate_handoff(saved, action.intent)
            immutable(path, saved)
        self.validate_handoff(saved, action.intent)
        return deepcopy(saved)

    def capture_control(self, action, name, value, format_name):
        from .native_file_capture import capture_native_file
        self.require_action(action)
        immutable(action.directory / name, value)
        file = capture_native_file(self.store, directory=str(action.directory),
            relative_path=name, format=format_name, media_type="application/json")
        self.file_metadata(file, value=value)
        return file

    def native_snapshot(self, action, observation):
        """Freeze authenticated original controls once, after the observation."""
        self.require_action(action)
        path = action.directory / "native-snapshot.json"
        value = read_control(path)
        if value is None:
            from .native_chromatin_interaction_local import local_chromatin_interaction_plan, _strict_json
            from .native_chromatin_interaction_driver import _read_control, confined_file
            from .native_chromatin_interaction_contracts import STARTED_FILENAME
            from .native_file_capture import capture_native_file, retained_native_file
            target = action.intent["target"]
            plan = local_chromatin_interaction_plan(target["assignment"], target["execution_id"])
            handle = _strict_json(Path(target["execution_id"]))
            request = _strict_json(Path(handle["paths"]["request"]))
            request_file = capture_native_file(self.store, directory=str(Path(target["execution_id"]).parent),
                relative_path=Path(handle["paths"]["request"]).name, format="native_local_job_request")
            request_raw = retained_native_file(self.store, request_file).read_bytes().decode("utf-8")
            started_path = confined_file(Path(plan["attempt_directory"]), STARTED_FILENAME)
            marker = _read_control(started_path) if started_path.exists() else None
            native_receipt = observation["native"].get("native_receipt")
            # A missing marker is not evidence that a driver never ran.
            never_started = (marker is None and type(native_receipt) is dict
                and native_receipt.get("execution_failure") is not None)
            value = {"original_plan": plan, "handle": handle, "request": request, "request_raw": request_raw,
                "started_marker": marker, "driver_started": True if marker is not None else False if never_started else None,
                "plan_file": self.capture_control(action, "native-plan.json", plan, "chromatin_interaction_run_plan_v1"),
                "handle_file": self.capture_control(action, "native-handle.json", handle, "durable_systemd_native_job_v2"),
                "request_file": request_file,
                "started_marker_file": None if marker is None else self.capture_control(action,
                    "driver-started.json", marker, "native_chromatin_started_v1")}
            self.validate_native(value, action.intent, observation)
            immutable(path, value)
        self.validate_native(value, action.intent, observation)
        return deepcopy(value)

    def validate_native(self, value, intent, observation):
        from .native_chromatin_interaction_local import _request
        from .native_lifecycle import VERSION as native_version
        closed(value, ChromatinInteractionNativeSnapshot.__annotations__)
        plan = validate_chromatin_run_plan(value["original_plan"])
        target, ident = intent["target"], plan["identity"]
        require(same(plan["requested_job"], target["assignment"]["requested_job"])
            and same(plan["policy"], POLICY) and ident["run_id"] == intent["run_id"]
            and ident["episode_id"] == target["origin_episode_id"]
            and ident["execution_id"] == target["execution_id"] and ident["resource_id"] == target["resource_id"]
            and ident["assignment_sha256"] == digest(target["assignment"])
            and ident["requested_job_sha256"] == target["request_sha256"]
            and ident["attempt_id"] == digest(ident["operation_key"]))
        handoff = read_control(self.action_directory(intent["episode_id"], intent["operation_key"]) / "handoff.json")
        require(handoff is not None and ident["operation_key"] == handoff["start_receipt"]["operation_key"])
        handle, request = value["handle"], value["request"]
        root = Path(target["execution_id"]).parent
        require(type(handle) is dict and handle.get("version") == native_version
            and handle.get("stage") in {"prepared", "submitting", "released"}
            and handle.get("command") == chromatin_driver_argv(plan) and handle.get("cwd") == str(root)
            and same(handle.get("metadata", {}).get("policy"), POLICY))
        paths = handle.get("paths")
        require(type(paths) is dict and {"request", "ready", "release", "status", "result", "launcher"} <= paths.keys()
            and not paths.keys() - {"request", "ready", "release", "status", "result", "launcher", "statistics", "native_events"}
            and len(set(paths.values())) == len(paths) and all(type(p) is str and Path(p).parent == root
                and str(Path(p)) == p for p in paths.values()))
        require(same(request, _request(plan, paths)))
        require(type(value["request_raw"]) is str)
        raw = value["request_raw"].encode("utf-8")
        require(same(decode(raw, canonical_bytes=False), request))
        self.file_metadata(value["request_file"])
        require(value["request_file"]["format"] == "native_local_job_request"
            and value["plan_file"]["format"] == "chromatin_interaction_run_plan_v1"
            and value["handle_file"]["format"] == native_version)
        require(hashlib.sha256(raw).hexdigest() == value["request_file"]["sha256"] == handle.get("request_sha256")
            and len(raw) == value["request_file"]["size_bytes"])
        for field, payload in (("plan_file", plan), ("handle_file", handle)):
            self.file_metadata(value[field], value=payload)
        marker = value["started_marker"]
        if marker is not None:
            closed(marker, ("plan", "started_at"))
            require(same(marker["plan"], plan) and type(marker["started_at"]) is str and bool(marker["started_at"]))
            self.file_metadata(value["started_marker_file"], value=marker)
            require(value["driver_started"] is True
                and value["started_marker_file"]["format"] == "native_chromatin_started_v1")
        else:
            require(value["started_marker_file"] is None)
            native = observation["native"].get("native_receipt")
            expected = False if type(native) is dict and native.get("execution_failure") is not None else None
            require(value["driver_started"] is expected)

    def validate_observation(self, value, intent):
        from .native_lifecycle import VERSION as native_version
        value = validate_resource_observation(value)
        native = value["native"]
        require(native.get("execution_id") == intent["target"]["execution_id"]
            and native.get("version") == native_version and type(native.get("terminal")) is bool
            and type(native.get("quiescent")) is bool and same(native.get("metadata", {}).get("policy"), POLICY))
        require(not native["terminal"] or native["quiescent"] and native["state"] == "returned")
        if native["terminal"]:
            require(type(native["metadata"].get("service_exit")) is dict
                and value["state"] in {"completed", "failed"})
        return value

    def observation(self, action):
        self.require_action(action)
        path = action.directory / "observation.json"
        value = read_control(path)
        if value is None:
            value = self.owner.job_progress_provider.targets.observe_target(action.intent["target"],
                operation_key=action.intent["operation_key"])
            value = self.validate_observation(value, action.intent)
            immutable(path, value)
        return deepcopy(self.validate_observation(value, action.intent))

    def origins(self, context, assignment):
        """Authenticate every exact received action origin, without science I/O."""
        bundle = assignment["selector"]["saved_sheet_bundle"]
        validate_chromatin_fact_values(SAVED_SOURCE, [bundle])
        origins = self.returns.authenticate_received_saved_bundle(context, bundle)
        matches = []
        require(type(origins) is tuple and bool(origins), "chromatin_saved_handoff_conflict")
        for origin in origins:
            closed(origin, ("episode_id", "operation_key"))
            row = self.read_completed(**origin, scope=plain(context.scope))
            require(any(same(bundle, saved) for saved in row["facts"][SAVED_SOURCE])
                and row["intent"]["target"]["handle"] == assignment["handoff_ref"], "chromatin_saved_handoff_conflict")
            matches.append(row)
        require(len(unique(origins)) == len(origins))
        require(all(same(row["intent"]["target"], matches[0]["intent"]["target"]) for row in matches),
            "chromatin_saved_target_conflict")
        return matches

    def validate_worker(self, receipt):
        """Qualify recorded C3 shape/pins and custody, never today's software."""
        plan, capture, execution = (receipt[k] for k in ("worker_plan", "worker_capture", "worker_execution"))
        if plan is None:
            require(capture is None and execution is None)
            return
        plan = validate_chromatin_result_worker_plan(plan)
        intent, selector = receipt["intent"], receipt["intent"]["assignment"]["selector"]
        root = self.action_directory(intent["episode_id"], intent["operation_key"]) / "worker"
        require(plan["directory"] == str(root) and same(plan["selector"], selector))
        if selector["mode"] == "native_result":
            native_capture = receipt["capture"]
            require(native_capture is not None and same(plan["original_plan"], receipt["native"]["original_plan"]))
            for key in ("bundle", "files", "source_action_receipt_ref", "writer_closure_receipt_ref", "driver_state", "failures"):
                require(same(plan[key], native_capture[key]))
            retained = [plan["bundle"], *(row["retained"] for row in plan["files"])]
        else:
            retained = [plan["sheet_bundle"]["sheet"], *plan["sheet_bundle"]["tables"]]
        for item in retained:
            if item is not None:
                file = self.file_metadata(item["file"])
                require(item["path"] == str(self.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]))
        if capture is None:
            require(execution is None)
            return
        validate_chromatin_record("WorkerCapture", capture)
        closed(execution, ("version", "plan_file", "intent", "terminal", "quiescent", "policy", "returncode",
            "metadata", "failure", "handle_file", "request_file", "stdout_file", "stderr_file"))
        require(execution["version"] == "chromatin_worker_execution_v1"
            and same(execution["plan_file"], capture["plan_file"]) and same(execution["policy"], POLICY)
            and execution["terminal"] is True and execution["quiescent"] is True)
        self.file_metadata(capture["plan_file"], value=plan)
        self.file_metadata(capture["execution_receipt_file"], value=execution)
        require(capture["plan_file"]["format"] == "chromatin_interaction_result_worker_plan_v1"
            and capture["execution_receipt_file"]["format"] == "chromatin_worker_execution_v1")
        selected = execution["intent"]
        closed(selected, ("version", "plan", "policy", "command", "environment", "source_pins", "interpreter", "dependencies"))
        require(selected["version"] == "chromatin_worker_intent_v1" and same(selected["plan"], plan)
            and same(selected["policy"], POLICY))
        require(type(selected["source_pins"]) is list and bool(selected["source_pins"])
            and type(selected["dependencies"]) is list and bool(selected["dependencies"]))
        def pin(value):
            closed(value, ("path", "sha256", "size_bytes"))
            require(type(value["path"]) is str and Path(value["path"]).is_absolute()
                and str(Path(value["path"])) == value["path"] and ".." not in Path(value["path"]).parts
                and type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
                and type(value["size_bytes"]) is int and value["size_bytes"] >= 0)
        for row in [*selected["source_pins"], selected["interpreter"]]:
            pin(row)
        paths = [p["path"] for p in selected["source_pins"]]
        require(len(paths) == len(set(paths)) and all(Path(p).is_relative_to(root / "source_snapshot") for p in paths))
        required = ("chromatin_interaction_result_worker", "chromatin_interaction_contracts", "chromatin_interaction_inputs",
            "chromatin_interaction_tables", "chromatin_interaction_calculations", "chromatin_interaction_result_views")
        require(all(str(root / "source_snapshot/gene_annotation_episode" / (name + ".py")) in paths for name in required))
        names = []
        for dependency in selected["dependencies"]:
            validate_chromatin_record("DependencyBinding", dependency)
            names.append(dependency["distribution"].lower().replace("_", "-"))
            for row in dependency["files"]:
                pin(row)
            require(len({p["path"] for p in dependency["files"]}) == len(dependency["files"]))
        require(len(names) == len(set(names)) and {"numpy", "jsonschema", "attrs", "referencing", "rpds-py", "jsonschema-specifications"} <= set(names))
        require(selected["interpreter"]["path"] == str(root / "runtime/python")
            and selected["command"] == [str(root / "runtime/python"), "-B", "-S", "-m",
                "gene_annotation_episode.chromatin_interaction_result_worker", str(root / "plan.json")])
        environment = selected["environment"]
        validate_chromatin_record("Environment", environment)
        expected = {"PYTHONPATH": os.pathsep.join([str(root / "source_snapshot"), *_dependency_roots(selected)]),
            "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
            "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip"),
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
        require(all(environment[k] == v for k, v in expected.items()) and Path(environment["PYTHONHOME"]).is_absolute())
        metadata = execution["metadata"]
        require(type(metadata) is dict and same(metadata.get("policy"), POLICY))
        if execution["failure"] is None:
            require(type(execution["returncode"]) is int)
            require(same(metadata.get("verified_cgroup"), {"memory_max": POLICY["memory_bytes"], "memory_swap_max": 0,
                "runtime_max": "infinity", "kill_mode": "control-group", "oom_policy": "kill"}))
        else:
            closed(execution["failure"], ("code", "phase", "diagnostic", "operational"))
            require(execution["returncode"] is None)
        for name in ("handle_file", "request_file", "stdout_file", "stderr_file"):
            self.file_metadata(execution[name])
        if capture["worker_result_file"] is not None:
            self.file_metadata(capture["worker_result_file"])
            require(capture["worker_result_file"]["format"] == "chromatin_interaction_result_worker_result_v1")
        result = capture["result"]
        if result is None:
            require(capture["outputs"] == [])
        else:
            result = validate_chromatin_result_worker_result(result)
            self.file_metadata(capture["worker_result_file"], value=result)
            require(result["mode"] == plan["mode"] and same(result["parameters"], selector["parameters"]))
            qualified_files(capture, execution)
            for row in capture["outputs"]:
                if row["capture"]["observed"] is not None:
                    self.file_metadata(row["capture"]["observed"])

    def sheet_evidence(self, action, receipt):
        """Read actual captured output once, then retain its compact joins."""
        from .native_file_capture import retained_native_file
        from .chromatin_interaction_result_views import project_chromatin_result, _validate_joins
        self.require_action(action)
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            return None
        path = action.directory / "sheet-evidence.json"
        evidence = read_control(path)
        if evidence is None:
            self.validate_worker(receipt)
            sheet = validate_chromatin_record("ContactSheet", decode(retained_native_file(self.store, files["sheet"]).read_bytes()))
            self.file_metadata(files["sheet"], value=sheet)
            require(same(sheet["request"], receipt["intent"]["target"]["assignment"]["requested_job"]["native_chromatin_interactions"]["request"]))
            evidence = {"version": "chromatin_interaction_sheet_evidence_v1", "sheet_file": deepcopy(files["sheet"]),
                "request_sha256": digest(sheet["request"]), "populations": [
                    {k: deepcopy(v) for k, v in p.items() if k not in ("element_anchor_rows", "pair_rows")}
                    for p in sheet["populations"]], "data_tables": deepcopy(sheet["data_tables"])}
            self.validate_sheet_evidence(receipt, evidence)
            for file in files["tables"]:
                if file["file"] is not None:
                    retained_native_file(self.store, file["file"])
            if files["components"] is not None:
                components = validate_chromatin_record("ChromatinComponents",
                    decode(retained_native_file(self.store, files["components"]).read_bytes()))
                self.file_metadata(files["components"], value=components)
                require(components["source_sheet_sha256"] == files["sheet"]["sha256"]
                    and same(components["table_identities"], [d["file"] for d in sheet["data_tables"] if d["file"] is not None])
                    and same(components["parameters"], action.intent["assignment"]["selector"]["parameters"]))
                # C2 validates all component/population/table/row joins and
                # selects the requested fields. It does not recalculate them.
                _validate_joins(sheet, components, action.intent["assignment"]["selector"])
                if files["projection"] is not None:
                    projected = project_chromatin_result(sheet, components, selector=action.intent["assignment"]["selector"])
                    actual = decode(retained_native_file(self.store, files["projection"]).read_bytes())
                    require(same(actual, projected) and same(actual, receipt["projection"]))
                    self.file_metadata(files["projection"], value=actual)
            else:
                require(files["projection"] is None and receipt["projection"] is None)
            immutable(path, evidence)
        self.validate_sheet_evidence(receipt, evidence)
        return deepcopy(evidence)

    def validate_sheet_evidence(self, receipt, evidence):
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            require(evidence is None)
            return
        closed(evidence, ChromatinInteractionSheetEvidence.__annotations__)
        request = receipt["intent"]["target"]["assignment"]["requested_job"]["native_chromatin_interactions"]["request"]
        require(evidence["version"] == "chromatin_interaction_sheet_evidence_v1"
            and same(evidence["sheet_file"], files["sheet"]) and evidence["request_sha256"] == digest(request))
        self.file_metadata(evidence["sheet_file"])
        populations, descriptors = evidence["populations"], evidence["data_tables"]
        require(type(populations) is list and type(descriptors) is list
            and [p["selected_region"] for p in populations] == request["populations"])
        keys = [d["table_key"] for d in descriptors]
        require(len(keys) == len(set(keys)) and keys == [r["table_key"] for r in files["tables"]])
        outputs = receipt["worker_capture"]["result"]["outputs"][4:]
        require(len(outputs) == len(descriptors))
        for p in populations:
            validate_chromatin_record("PopulationExtraction", p)
            chosen = [d for d in descriptors if d["population_key"] == p["population_key"]]
            require(p["population_key"] == p["selected_region"]["population_key"]
                and [d["role"] for d in chosen] == list(TABLE_ROLES)
                and p["data_table_keys"] == [d["table_key"] for d in chosen]
                and same(p["normalization"]["specification"], request["normalization"]))
        require(len(descriptors) == 5 * len(populations))
        for d, output, captured in zip(descriptors, outputs, files["tables"]):
            validate_chromatin_record("TableDescriptor", d)
            declaration = output["declaration"]
            ordinal = next(i for i, p in enumerate(populations) if p["population_key"] == d["population_key"])
            require(output["table_key"] == d["table_key"] == captured["table_key"]
                and declaration["format"] == "chromatin_contact_tables_v1:" + d["role"]
                and declaration["relative_path"] == f"tables/p{ordinal}/" + TABLE_NAMES[TABLE_ROLES.index(d["role"])])
            if d["file"] is not None:
                self.file_metadata(d["file"])
                require(d["file"]["format"] == declaration["format"])
                # A saved file lost during a new use is not a smaller bundle.
                if captured["file"] is not None:
                    require(same(d["file"], captured["file"]))
                if declaration["state"] == "present":
                    require(all(declaration[k] == d["file"][k] for k in ("sha256", "size_bytes")))
            else:
                require(captured["file"] is None and declaration["state"] == "absent")
        selector = receipt["intent"]["assignment"]["selector"]
        if selector["mode"] == "saved_sheet_recalculation":
            require(same(selector["saved_sheet_bundle"], self.evidence_bundle(evidence)))

    @staticmethod
    def evidence_bundle(evidence):
        return {"sheet": deepcopy(evidence["sheet_file"]),
            "tables": [deepcopy(d["file"]) for d in evidence["data_tables"] if d["file"] is not None]}

    def saved_bundle(self, receipt):
        evidence = receipt["sheet_evidence"]
        if evidence is None:
            return None
        self.validate_sheet_evidence(receipt, evidence)
        if any(d["file"] is not None and not same(d["file"], r["file"])
                for d, r in zip(evidence["data_tables"], receipt["qualified_files"]["tables"])):
            return None
        return self.evidence_bundle(evidence)

    def publication(self, receipt, *, originals=None):
        from .chromatin_interaction_return_views import requested_chromatin_sources
        intent = receipt["intent"]
        context = self.returns.context(intent["episode_id"])
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
        requested, facts = requested_chromatin_sources(schema), empty_facts()
        projection, bundle = receipt["projection"], self.saved_bundle(receipt)
        issues = list(receipt["host_failures"])
        for capture in (receipt["capture"], receipt["worker_capture"]):
            if capture is not None:
                issues.extend(capture["failures"])
        worker = receipt["worker_capture"]
        if worker is not None and worker["result"] is not None:
            issues.extend(worker["result"]["failures"])
        if projection is not None:
            issues.extend(projection["failures"])
        if intent["tool_name"] == "execution.results.collect":
            if PROJECTION_SOURCE in requested and projection is not None:
                facts[PROJECTION_SOURCE] = [deepcopy(projection)]
            if SAVED_SOURCE in requested and bundle is not None:
                facts[SAVED_SOURCE] = [bundle]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = self.selected_failures(receipt, issues)
        complete = (intent["tool_name"] == "execution.results.collect" and projection is not None
            and not receipt["host_failures"] and (SAVED_SOURCE not in requested or bundle is not None))
        if intent["assignment"]["selector"]["mode"] == "native_result":
            complete = complete and self.original_acquisition_complete(receipt)
        else:
            originals = self.origins(context, intent["assignment"]) if originals is None else originals
            complete = complete and any(self.original_acquisition_complete(row) for row in originals)
        return facts, bool(complete)

    def selected_failures(self, receipt, issues):
        selector = receipt["intent"]["assignment"]["selector"]
        selected = set(selector["population_keys"])
        selection = selector["projection"].get("selection", {})
        pairs = ({r["pair_key"] for r in receipt["projection"]["rows"] if "pair_key" in r}
            if receipt["projection"] is not None else
            set(selection.get("pair_keys", ())) if selection.get("by") == "keys" else None)
        request = receipt["intent"]["target"]["assignment"]["requested_job"]["native_chromatin_interactions"]["request"]
        files = [] if receipt["capture"] is None else receipt["capture"]["files"]
        result = []
        for issue in unique(issues):
            validate_chromatin_record("Failure", issue)
            if issue["population_key"] is not None and issue["population_key"] not in selected:
                continue
            if pairs is not None and issue["pair_key"] is not None and issue["pair_key"] not in pairs:
                continue
            path = issue["field_path"] or ""
            if path == "/outputs/table" and receipt["sheet_evidence"] is not None and receipt["worker_capture"] is not None:
                populations = {d["table_key"]: d["population_key"] for d in receipt["sheet_evidence"]["data_tables"]}
                affected = [r["table_key"] for r in receipt["worker_capture"]["outputs"] if r["role"] == "table"
                    and r["capture"]["outcome"] not in {"verified", "declared_absent"}]
                if affected and all(key in populations and populations[key] not in selected for key in affected):
                    continue
            match = re.match(r"^/(?:files/)?p([0-9]+)\.", path)
            if match and int(match[1]) < len(request["populations"]) and request["populations"][int(match[1])]["population_key"] not in selected:
                continue
            match = re.match(r"^/(populations|files)/(0|[1-9][0-9]*)(?:/|$)", path)
            if match:
                rows = request["populations"] if match[1] == "populations" else [r["specification"] for r in files]
                if int(match[2]) < len(rows) and rows[int(match[2])].get("population_key") not in (None, *selected):
                    continue
            result.append(issue)
        return result

    def _population_acquired(self, receipt, population, *, complete=False):
        """Actual captured bins/contact rows, or a proved empty sparse read."""
        evidence, capture = receipt["sheet_evidence"], receipt["capture"]
        if evidence is None or capture is None or receipt["native"] is None:
            return False
        obs = receipt["observation"]
        if obs is None or not obs["native"]["terminal"] or not obs["native"]["quiescent"]:
            return False
        key = population["population_key"]
        tables = {d["role"]: d for d in evidence["data_tables"] if d["population_key"] == key}
        for role in ("bins", "contacts"):
            d = tables[role]
            original, = [r for r in capture["files"] if r["specification"]["role"] == role
                and r["specification"]["population_key"] == key]
            current = next(r for r in receipt["qualified_files"]["tables"] if r["table_key"] == d["table_key"])
            if (d["file"] is None or not same(current["file"], d["file"]) or original["retained"] is None
                    or original["capture"] is None or original["capture"]["outcome"] != "verified"
                    or original["declaration_source"] not in ("bundle", "population")
                    or not same(original["retained"]["file"], d["file"])):
                return False
        read = population["read_evidence"]
        full = (population["extent"] == "complete" and all(read[k] == "complete"
            for k in ("axes_extent", "index_extent", "selected_records_extent")) and not read["failed_block_ids"])
        if complete:
            return full
        if population["raw_cell_population"]["validated_observed_row_count"] > 0:
            return population["extent"] in ("complete", "partial")
        return full and read["implicit_zero_semantics"] == "validated_sparse_absence"

    def original_acquisition_complete(self, receipt):
        if receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation":
            context = self.returns.context(receipt["intent"]["episode_id"])
            return any(self.original_acquisition_complete(row) for row in self.origins(context, receipt["intent"]["assignment"]))
        observation, capture, evidence = receipt["observation"], receipt["capture"], receipt["sheet_evidence"]
        return bool(observation is not None and observation["state"] == "completed" and observation["returncode"] == 0
            and capture is not None and capture["driver_state"] == "sealed_bundle" and capture["bundle"] is not None
            and not capture["failures"] and evidence is not None and evidence["populations"]
            and all(self._population_acquired(receipt, p, complete=True) for p in evidence["populations"]))

    def acquisition_population(self, receipt):
        self.validate_sheet_evidence(receipt, receipt["sheet_evidence"])
        if (receipt["intent"]["assignment"]["selector"]["mode"] != "native_result"
                or receipt["intent"]["tool_name"] != "execution.results.collect" or receipt["sheet_evidence"] is None):
            return None
        return digest(receipt["native"]["original_plan"]["identity"]) if any(
            self._population_acquired(receipt, p) for p in receipt["sheet_evidence"]["populations"]) else None

    def validate(self, receipt, intent):
        receipt = _finite_json_copy(receipt)
        closed(receipt, ChromatinInteractionResultReceipt.__annotations__)
        require(receipt["version"] == VERSION and same(receipt["intent"], intent))
        self.validate_handoff(receipt["handoff_proof"], intent)
        saved = intent["assignment"]["selector"]["mode"] == "saved_sheet_recalculation"
        originals = None
        require(type(receipt["original_origins"]) is list)
        if saved:
            originals = self.origins(self.returns.context(intent["episode_id"]), intent["assignment"])
            origins = [{"episode_id": row["intent"]["episode_id"], "operation_key": row["intent"]["operation_key"]}
                       for row in originals]
            require(same(receipt["original_origins"], origins)
                and all(same(row["intent"]["target"], intent["target"]) for row in originals))
            require(all(receipt[key] is None for key in ("observation", "native", "source_action_file", "writer_closure_file", "capture")))
        else:
            require(receipt["original_origins"] == [])
            self.validate_observation(receipt["observation"], intent)
            if receipt["native"] is not None:
                self.validate_native(receipt["native"], intent, receipt["observation"])
            if receipt["capture"] is not None:
                require(intent["tool_name"] == "execution.results.collect" and receipt["native"] is not None
                    and receipt["observation"]["native"]["terminal"] and receipt["observation"]["native"]["quiescent"])
                capture = validate_chromatin_native_capture(receipt["capture"], original_plan=receipt["native"]["original_plan"])
                self.file_metadata(receipt["source_action_file"], value=receipt["handoff_proof"]["start_receipt"])
                self.file_metadata(receipt["writer_closure_file"], value=closure_value(receipt))
                require(capture["source_action_receipt_ref"] == receipt["source_action_file"]["artifact_ref"]
                    and capture["writer_closure_receipt_ref"] == receipt["writer_closure_file"]["artifact_ref"]
                    and (capture["driver_state"] == "not_started") == (receipt["native"]["driver_started"] is False))
            else:
                require(receipt["source_action_file"] is None and receipt["writer_closure_file"] is None)
        self.validate_worker(receipt)
        expected_files = qualified_files(receipt["worker_capture"], receipt["worker_execution"])
        require(same(receipt["qualified_files"], expected_files))
        self.validate_sheet_evidence(receipt, receipt["sheet_evidence"])
        projection = receipt["projection"]
        if expected_files["projection"] is None:
            require(projection is None)
        else:
            require(expected_files["sheet"] is not None and expected_files["components"] is not None)
            validate_chromatin_record("RequestedProjection", projection)
            self.file_metadata(expected_files["projection"], value=projection)
            selector = intent["assignment"]["selector"]
            require(projection["source_sheet_sha256"] == expected_files["sheet"]["sha256"]
                and same(projection["parameters"], selector["parameters"])
                and projection["kind"] == selector["projection"]["kind"]
                and projection["requested_fields"] == selector["projection"]["fields"]
                and projection["population_keys"] == selector["population_keys"])
            selection = selector["projection"].get("selection", {})
            if selection.get("by") == "page":
                require(type(projection["page"]) is dict and projection["page"]["offset"] == selection["page"]["offset"]
                    and projection["page"]["returned_count"] <= selection["page"]["limit"])
            else:
                require(projection["page"] is None)
        require(type(receipt["host_failures"]) is list)
        for row in receipt["host_failures"]:
            validate_chromatin_record("Failure", row)
        closed(receipt["facts"], ChromatinInteractionFactGroups.__annotations__)
        for source, rows in receipt["facts"].items():
            validate_chromatin_fact_values(source, rows)
        facts, complete = self.publication(receipt, originals=originals)
        require(same(receipt["facts"], facts) and type(receipt["delivery_complete"]) is bool
            and receipt["delivery_complete"] == complete)
        require(receipt["acquired_population"] == self.acquisition_population(receipt))
        if intent["tool_name"] == "execution.results.status":
            require(receipt["worker_plan"] is None and receipt["worker_capture"] is None
                and receipt["capture"] is None and all(not rows for rows in receipt["facts"].values()))
        return receipt

    @staticmethod
    def match_outcome(row, receipt):
        require(row["result"] is not None)
        actual = json.loads(row["result"])
        if "pending_work_after_action" in actual:
            from .waiting import validate_pending
            validate_pending(actual.pop("pending_work_after_action"))
        require(same(actual, outcome(receipt)))

    def controls(self, intent):
        root = self.action_directory(intent["episode_id"], intent["operation_key"])
        receipt = read_control(root / "receipt.json")
        if receipt is None:
            return None
        require(same(read_control(root / "intent.json"), intent)
            and same(read_control(root / "handoff.json"), receipt["handoff_proof"]))
        for name, key in (("observation.json", "observation"), ("native-snapshot.json", "native"),
                ("capture.json", "capture"), ("worker-plan.json", "worker_plan"),
                ("worker-capture.json", "worker_capture"), ("worker-execution.json", "worker_execution"),
                ("sheet-evidence.json", "sheet_evidence")):
            require(same(read_control(root / name), receipt[key]))
        if receipt["capture"] is not None:
            require(same(read_control(root / "source-action.json"), receipt["handoff_proof"]["start_receipt"])
                and same(read_control(root / "writer-closure.json"), closure_value(receipt)))
        return self.validate(receipt, intent)

    def read_staged(self, action):
        self.require_action(action)
        receipt = self.controls(action.intent)
        row = self._selected(action.intent)
        require(receipt is not None or row["result"] is None)
        if receipt is not None and row["result"] is not None:
            self.match_outcome(row, receipt)
        return deepcopy(receipt)

    def publish(self, action, receipt):
        self.require_action(action)
        receipt = self.validate(receipt, action.intent)
        immutable(action.directory / "receipt.json", receipt)
        require(same(self.controls(action.intent), receipt))
        return deepcopy(receipt)

    def read_completed(self, *, episode_id, operation_key, scope):
        marker = (episode_id, operation_key)
        active = _READING.get()
        require(marker not in active, "chromatin_interaction_result_cyclic_authority")
        cache = _READ_CACHE.get()
        cache_token = None
        if cache is None:
            cache = {}
            cache_token = _READ_CACHE.set(cache)
        cache_key = (str(self.store.path), self.owner.run_id, episode_id, operation_key, canonical(scope))
        if cache_key in cache:
            return deepcopy(cache[cache_key])
        token = _READING.set((*active, marker))
        try:
            with self.store.read_snapshot():
                context = self.returns.context(episode_id)
                self._context(context)
                self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
                root = self.action_directory(episode_id, operation_key)
                intent = read_control(root / "intent.json")
                closed(intent, ChromatinInteractionResultIntent.__annotations__)
                require(same(intent, self.intent(context, intent["target"], "execution.results.collect", {}, operation_key)))
                manifest = {"run_id": context.run_id, "episode_id": context.episode_id,
                    "scope": plain(context.scope), "assignment": plain(context.assignment)}
                require(same(read_control(root.parent.parent / "assignment.json"), manifest))
                row = self._selected(intent)
                require(row["result"] is not None)
                receipt = self.controls(intent)
                require(receipt is not None)
                self.match_outcome(row, receipt)
                # Only one synchronous historical read shares verified origins;
                # the next public call checks current controls and runtime again.
                cache[cache_key] = deepcopy(receipt)
                return deepcopy(receipt)
        finally:
            _READING.reset(token)
            if cache_token is not None:
                _READ_CACHE.reset(cache_token)

    def completed_receipts(self, context):
        self._context(context, allow_unsaved=True)
        result = []
        rows = self.store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? ORDER BY decision_index", (self.owner.run_id, context.episode_id))
        for row in rows:
            action = json.loads(row["action"])
            if (action.get("kind") == "tool" and action.get("tool") == "execution.results.collect"
                    and row["result"] is not None and json.loads(row["result"]).get("status") == "completed"):
                result.append(self.read_completed(episode_id=context.episode_id,
                    operation_key=f'{self.owner.run_id}:{context.episode_id}:{row["decision_index"]}', scope=plain(context.scope)))
        return result

    def owns_reference(self, reference):
        """Classify private derived artifacts, without granting their use."""
        if type(reference) is not str or not reference.startswith("artifact_"):
            return False
        rows = self.store.db.execute("SELECT episode_id,result FROM runtime_actions WHERE run_id=? "
            "AND result IS NOT NULL AND json_extract(result,'$.result.version')=?", (self.owner.run_id, VERSION))
        for row in rows:
            candidate = json.loads(row["result"])["result"]
            capture = candidate.get("worker_capture") or {}
            identities = [item["capture"]["observed"] for item in capture.get("outputs", [])
                if item.get("capture", {}).get("observed") is not None]
            identities.extend(capture.get(key) for key in ("plan_file", "execution_receipt_file", "worker_result_file"))
            private = {file["artifact_ref"] for file in identities if file is not None}
            native = candidate.get("capture")
            if native is not None:
                if native.get("bundle") is not None:
                    private.add(native["bundle"]["file"]["artifact_ref"])
                for item in native.get("files", []):
                    # Original supplied operands keep their prior authority.
                    # Newly produced tables/seals/logs remain private custody.
                    if item["specification"]["role"] not in {"original_contact", "original_elements", "original_metadata"}:
                        retained = item.get("retained")
                        if retained is not None:
                            private.add(retained["file"]["artifact_ref"])
                for issue in native.get("failures", []):
                    if issue.get("artifact_ref") is not None:
                        private.add(issue["artifact_ref"])
                    private.update(issue.get("partial_artifact_refs", []))
            # Failure references are custody/provenance, never operand grants.
            for issue in capture.get("failures", []):
                if issue.get("artifact_ref") is not None:
                    private.add(issue["artifact_ref"])
                private.update(issue.get("partial_artifact_refs", []))
            if reference in private:
                original = self.returns.context(row["episode_id"])
                self.read_completed(episode_id=row["episode_id"], operation_key=candidate["intent"]["operation_key"],
                    scope=plain(original.scope))
                return True
        return False

    def baseline_populations(self, context, references):
        """Subtract actual frozen inherited populations, without operand grants."""
        from .episode_receipts import EpisodeReceipts
        self._context(context, allow_unsaved=True)
        receipts = object.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = self.store, self.store.db, self.owner.run_id
        baseline = set(receipts.known(context.episode_id, baseline=True)) & set(references)
        result, visited = set(), set()

        def population(receipt):
            if receipt["acquired_population"] is not None:
                result.add(receipt["acquired_population"])
            for origin in receipt["original_origins"]:
                row = self.read_completed(**origin, scope=plain(context.scope))
                population(row)

        current = context
        while True:
            require(current.episode_id not in visited, "chromatin_interaction_result_cyclic_authority")
            visited.add(current.episode_id)
            self.returns.authenticate(current, allow_unsaved=current is context)
            manifest = receipts.manifest(current.episode_id)
            require(same(plain(current.request)["message"].get("knowledge_inheritance"), manifest))
            parent_id = manifest["parent_episode_id"]
            if parent_id is None:
                require(len(current.path) == 1)
                break
            require("received_report_prefix" in manifest)
            parent = self.returns.context(parent_id)
            self.returns._commission(parent, current, construction=current is context)
            if parent.role in {"annotation", "scientific_process"}:
                groups, origins, _ = self.returns._received(parent, (SAVED_SOURCE,),
                    allowed=manifest["received_report_prefix"]["attempts"])
                for bundle in groups[SAVED_SOURCE]:
                    if not {f["artifact_ref"] for f in (bundle["sheet"], *bundle["tables"])} <= baseline:
                        continue
                    for origin in origins[canonical(bundle)]:
                        closed(origin, ("episode_id", "operation_key"))
                        receipt = self.read_completed(**origin, scope=plain(context.scope))
                        require(any(same(bundle, saved) for saved in receipt["facts"][SAVED_SOURCE]))
                        population(receipt)
            current = parent
        return result


__all__ = ["ChromatinInteractionResultReceipts", "ChromatinInteractionResultAction", "ChromatinInteractionResultReceipt", "VERSION"]
