"""Selected overlap action controls and historical completed-action authority.

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
from .genomic_overlap_contracts import (
    Failure, NativeFileIdentity, Projection, _finite_json_copy,
    validate_genomic_overlap_record,
)
from .genomic_overlap_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    validate_genomic_overlap_fact_values,
)
from .genomic_overlap_result_worker import (
    WorkerPlan, validate_genomic_overlap_result_worker_plan,
    validate_genomic_overlap_result_worker_result,
)
from .native_genomic_overlap_capture import validate_genomic_overlap_native_capture
from .native_genomic_overlap_contracts import (
    POLICY, genomic_overlap_driver_argv, genomic_overlap_environment,
    validate_genomic_overlap_requested_job, validate_genomic_overlap_run_plan,
)
from .native_genomic_overlap_preparation import (
    WorkerCapture, WorkerExecution, _execution_fields, _validated_dependencies,
)
from .practical_execution_records import validate_receipt
from .practical_receipt_information import PracticalReceiptInformation
from .progress_records import validate_resource_observation


VERSION = "native_genomic_overlap_acquired_result_v1"


class GenomicOverlapResultIntent(TypedDict):
    version: Literal["genomic_overlap_result_intent_v1"]
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


class GenomicOverlapHandoffProof(TypedDict):
    source_record: dict
    body: dict
    assignment_snapshot: dict
    start_receipt: dict


class GenomicOverlapNativeSnapshot(TypedDict):
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


class GenomicOverlapOrigin(TypedDict):
    episode_id: str
    operation_key: str


class GenomicOverlapQualifiedFiles(TypedDict):
    sheet: NativeFileIdentity | None
    components: NativeFileIdentity | None
    projection: NativeFileIdentity | None
    diagnostics: NativeFileIdentity | None


class GenomicOverlapFactGroups(TypedDict):
    genomic_overlap_pair_metrics: list[Projection]
    genomic_overlap_saved_sheets: list[NativeFileIdentity]
    genomic_overlap_failures: list[Failure]


class GenomicOverlapAcquisitionEvidence(TypedDict):
    version: Literal["genomic_overlap_acquisition_evidence_v1"]
    sheet_file: NativeFileIdentity
    comparison_receipts: list[dict]


class GenomicOverlapResultReceipt(TypedDict):
    version: Literal["native_genomic_overlap_acquired_result_v1"]
    intent: GenomicOverlapResultIntent
    handoff_proof: GenomicOverlapHandoffProof
    original_origins: list[GenomicOverlapOrigin]
    observation: dict | None
    native: GenomicOverlapNativeSnapshot | None
    source_action_file: NativeFileIdentity | None
    writer_closure_file: NativeFileIdentity | None
    capture: dict | None
    worker_plan: WorkerPlan | None
    worker_capture: WorkerCapture | None
    worker_execution: WorkerExecution | None
    qualified_files: GenomicOverlapQualifiedFiles
    projection: Projection | None
    host_failures: list[Failure]
    facts: GenomicOverlapFactGroups
    acquisition_evidence: GenomicOverlapAcquisitionEvidence | None
    acquired_population: str | None
    delivery_complete: bool


@dataclass(frozen=True)
class GenomicOverlapResultAction:
    intent: GenomicOverlapResultIntent
    directory: Path


_READING = ContextVar("genomic_overlap_receipt_reading", default=())
_READ_CACHE = ContextVar("genomic_overlap_receipt_read_cache", default=None)
_OUTPUTS = ("sheet", "components", "projection", "diagnostics")


def require(condition, code="genomic_overlap_result_authority_conflict"):
    if not condition:
        raise ValueError(code)


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), "genomic_overlap_result_invalid_record")


def same(left, right):
    return canonical(left) == canonical(right)


def decode(raw, *, newline=False, canonical_bytes=True):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "genomic_overlap_result_duplicate_key")
            result[key] = value
        return result
    value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs))
    require(not canonical_bytes or raw == canonical(value).encode("utf-8") + (b"\n" if newline else b""),
            "genomic_overlap_result_noncanonical_control")
    return value


@contextmanager
def directory(path, *, create=False):
    value = str(path)
    pure = PurePosixPath(value)
    require(pure.is_absolute() and str(pure) == value and value != "/" and ".." not in pure.parts
            and not any(c in value for c in "\0\r\n\\"), "genomic_overlap_result_invalid_path")
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
        require(os.fstat(fd).st_uid == os.geteuid(), "genomic_overlap_result_invalid_path")
        yield fd


@contextmanager
def regular(fd, name, *, flags=os.O_RDONLY):
    require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
    handle = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        require(stat.S_ISREG(os.fstat(handle).st_mode), "genomic_overlap_result_invalid_path")
        yield handle
    finally:
        os.close(handle)


def read_control(path):
    try:
        with directory(path.parent) as fd, regular(fd, path.name) as handle, os.fdopen(os.dup(handle), "rb") as stream:
            raw = stream.read()
    except FileNotFoundError:
        return None
    return decode(raw, newline=path.name == "assignment.json" and raw.endswith(b"\n"))


def immutable(path, value):
    value = _finite_json_copy(value)
    with directory(path.parent, create=True) as fd:
        previous = read_control(path)
        if previous is not None:
            require(same(previous, value), "genomic_overlap_result_control_conflict")
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
                require(same(read_control(path), value), "genomic_overlap_result_control_conflict")
            os.fsync(fd)
        finally:
            os.unlink(temporary, dir_fd=fd)


def empty_facts() -> GenomicOverlapFactGroups:
    return {source: [] for source in FACT_SOURCES}


def empty_files() -> GenomicOverlapQualifiedFiles:
    return {role: None for role in _OUTPUTS}


def unique(rows):
    result, seen = [], set()
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


def outcome(receipt):
    refs = [row["artifact_ref"] for row in receipt["facts"][SAVED_SOURCE]]
    return {"status": "completed", "record_refs": refs, "changed_record_refs": refs,
            "result": deepcopy(receipt), "feedback": None}


def qualified_files(capture, execution):
    result = empty_files()
    if capture is None or capture["result"] is None or execution is None:
        return result
    if execution["outcome"] != "returned" or execution["returncode"] != 0:
        return result
    affected = {row["field_path"] for row in capture["failures"]}
    for role, row in zip(_OUTPUTS, capture["outputs"]):
        if row["outcome"] == "verified" and "/outputs/" + role not in affected:
            result[role] = deepcopy(row["observed"])
    return result


def closure_value(receipt):
    return {"version": "genomic_overlap_writer_closure_v1", "intent_sha256": digest(receipt["intent"]),
        "native": receipt["native"], "observation": receipt["observation"]}


class GenomicOverlapResultReceipts:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self._active = {}

    @property
    def returns(self):
        return self.owner.native_genomic_overlap_returns

    def action_directory(self, episode_id, operation_key):
        return self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id]) / "native-genomic-overlap-actions" / digest(operation_key)

    def _context(self, context, *, allow_unsaved=False):
        self.returns.authenticate(context, allow_unsaved=allow_unsaved)
        require(isinstance(context, BindingContext) and context.role == "results")
        assignment = plain(context.assignment)
        closed(assignment, ("version", "handoff_ref", "selector"))
        require(assignment["version"] == "execution_results_assignment_v1")
        validate_genomic_overlap_record("Selector", assignment["selector"])
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
        requested = validate_genomic_overlap_requested_job(target["assignment"]["requested_job"])
        require(target["request_sha256"] == digest(requested)
            and target["assignment"]["resource_id"] == target["resource_id"])
        self.store.validate_scope(target["scope"], parent_scope=plain(context.scope))
        resource = self.owner.resources.get(target["resource_id"])
        require(type(resource) is dict and resource["kind"] == "local" and same(resource["policy"], POLICY))
        reader = self.owner.job_progress_provider.targets
        require(same(reader.resources.get(target["resource_id"]), resource)
            and target["resource_id"] in reader.operations)
        reader.operations[target["resource_id"]].validate_assignment(target["assignment"])
        # Pure plan validation supplies selector/population checks with no bytes.
        selector = assignment["selector"]
        keys = [p["comparison_key"] for p in requested["native_genomic_overlap"]["request"]["comparisons"]]
        require(len(set(selector["comparison_keys"])) == len(selector["comparison_keys"])
            and [key for key in keys if key in selector["comparison_keys"]] == selector["comparison_keys"],
            "genomic_overlap_result_selector_conflict")
        require((selector["saved_sheet_file"] is None) == (selector["mode"] == "native_result"))
        for name in ("minimum_a_fraction", "minimum_b_fraction"):
            fraction = selector["parameters"][name]
            require(fraction["numerator"] <= fraction["denominator"], "genomic_overlap_result_selector_conflict")
        selected_sets = {pair[side] for pair in requested["native_genomic_overlap"]["request"]["comparisons"]
            if pair["comparison_key"] in selector["comparison_keys"] for side in ("a_set_key", "b_set_key")}
        occurrences = [(row["set_key"], row["occurrence_key"]) for row in selector["projection"]["occurrence_keys"]]
        require(len(set(occurrences)) == len(occurrences) and all(key in selected_sets for key, _ in occurrences)
            and (selector["projection"]["kind"] == "occurrence_rows" or not occurrences),
            "genomic_overlap_result_selector_conflict")
        return target

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ("execution.results.status", "execution.results.collect")
            and type(arguments) is dict and arguments == {})
        value = {"version": "genomic_overlap_result_intent_v1", "run_id": context.run_id,
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
                action = GenomicOverlapResultAction(deepcopy(intent), root)
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
        file = validate_genomic_overlap_record("NativeFileIdentity", file)
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
        closed(proof, GenomicOverlapHandoffProof.__annotations__)
        source, body, snapshot, start = (proof[name] for name in GenomicOverlapHandoffProof.__annotations__)
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
        requested = validate_genomic_overlap_requested_job(assignment["requested_job"])
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
            from .native_genomic_overlap_local import local_genomic_overlap_plan
            from .native_genomic_overlap_driver import _strict_json, _read_control, confined_file
            from .native_genomic_overlap_contracts import STARTED_FILENAME
            from .native_file_capture import capture_native_file, retained_native_file
            target = action.intent["target"]
            plan = local_genomic_overlap_plan(target["assignment"], target["execution_id"])
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
                "plan_file": self.capture_control(action, "native-plan.json", plan, "native_genomic_overlap_run_plan_v1"),
                "handle_file": self.capture_control(action, "native-handle.json", handle, "durable_systemd_native_job_v2"),
                "request_file": request_file,
                "started_marker_file": None if marker is None else self.capture_control(action,
                    "driver-started.json", marker, "native_genomic_overlap_driver_started_v1")}
            self.validate_native(value, action.intent, observation)
            immutable(path, value)
        self.validate_native(value, action.intent, observation)
        return deepcopy(value)

    def validate_native(self, value, intent, observation):
        from .native_genomic_overlap_local import _request
        from .native_lifecycle import VERSION as native_version
        closed(value, GenomicOverlapNativeSnapshot.__annotations__)
        plan = validate_genomic_overlap_run_plan(value["original_plan"])
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
            and handle.get("command") == genomic_overlap_driver_argv(plan) and handle.get("cwd") == str(root)
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
        require(hashlib.sha256(raw).hexdigest() == value["request_file"]["sha256"] == handle.get("request_sha256")
            and len(raw) == value["request_file"]["size_bytes"])
        for field, payload in (("plan_file", plan), ("handle_file", handle)):
            self.file_metadata(value[field], value=payload)
        marker = value["started_marker"]
        if marker is not None:
            closed(marker, ("plan", "started_at"))
            require(same(marker["plan"], plan) and type(marker["started_at"]) is str and bool(marker["started_at"]))
            self.file_metadata(value["started_marker_file"], value=marker)
            require(value["driver_started"] is True)
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
        """Use every explicitly received saved origin; no native or data reads."""
        selector = assignment["selector"]
        file = selector["saved_sheet_file"]
        episodes = self.returns.authenticate_received_saved_sheet(context, file)
        matches = []
        for episode_id in episodes:
            original_context = self.returns.context(episode_id)
            self.store.validate_scope(plain(original_context.scope), parent_scope=plain(context.scope))
            for receipt in self.completed_receipts(original_context):
                if (any(same(file, row) for row in receipt["facts"][SAVED_SOURCE])
                        and receipt["intent"]["target"]["handle"] == assignment["handoff_ref"]):
                    matches.append(receipt)
        require(bool(matches), "genomic_overlap_saved_handoff_conflict")
        target = matches[0]["intent"]["target"]
        require(all(same(row["intent"]["target"], target) for row in matches), "genomic_overlap_saved_target_conflict")
        return matches

    def validate_worker(self, receipt):
        """Historical shape and provenance qualification, without scientific I/O."""
        plan, capture, execution = (receipt[k] for k in ("worker_plan", "worker_capture", "worker_execution"))
        if plan is None:
            require(capture is None and execution is None)
            return
        plan = validate_genomic_overlap_result_worker_plan(plan)
        intent, selector = receipt["intent"], receipt["intent"]["assignment"]["selector"]
        require(plan["directory"] == str(self.action_directory(intent["episode_id"], intent["operation_key"]) / "worker")
            and same(plan["selector"], selector))
        if selector["mode"] == "native_result":
            native_capture = receipt["capture"]
            require(native_capture is not None)
            require(same(plan["original_plan"], receipt["native"]["original_plan"]))
            for key in ("batch", "files", "source_action_receipt_ref", "writer_closure_receipt_ref", "driver_state", "failures"):
                require(same(plan[key], native_capture[key]))
            retained = [plan["batch"], *(row["retained"] for row in plan["files"])]
        else:
            require(same(plan["sheet"]["file"], selector["saved_sheet_file"]))
            retained = [plan["sheet"]]
        for item in retained:
            if item is not None:
                file = self.file_metadata(item["file"])
                require(item["path"] == str(self.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]))
        if capture is None:
            require(execution is None)
            return
        closed(capture, WorkerCapture.__annotations__)
        closed(execution, _execution_fields(execution))
        if "dependencies" in execution:
            _validated_dependencies(execution["dependencies"])
        require(capture["version"] == "genomic_overlap_worker_capture_v1"
            and execution["version"] == "genomic_overlap_worker_execution_v1"
            and same(execution["plan_file"], capture["plan_file"]))
        self.file_metadata(capture["plan_file"], value=plan)
        self.file_metadata(capture["execution_receipt_file"], value=execution)
        require(execution["outcome"] in {"returned", "failed"})
        if execution["outcome"] == "returned":
            require(type(execution["returncode"]) is int and execution["failure"] is None
                and type(execution["metadata"]) is dict and same(execution["metadata"].get("policy"), POLICY))
            expected_cgroup = {"memory_max": POLICY["memory_bytes"], "memory_swap_max": 0,
                "runtime_max": "infinity", "kill_mode": "control-group", "oom_policy": "kill"}
            require(same(execution["metadata"].get("verified_cgroup"), expected_cgroup))
        else:
            require(execution["returncode"] is None and execution["metadata"] is None and type(execution["failure"]) is dict)
            closed(execution["failure"], ("code", "phase", "diagnostic", "operational"))
        for key in ("handle_file", "request_file", "stdout_file", "stderr_file"):
            if execution[key] is not None:
                self.file_metadata(execution[key])
        require(type(execution["source_pins"]) is list and bool(execution["source_pins"]))
        paths = []
        for pin in [*execution["source_pins"], execution["interpreter"]]:
            closed(pin, ("path", "sha256", "size_bytes"))
            require(type(pin["path"]) is str and Path(pin["path"]).is_absolute()
                and str(Path(pin["path"])) == pin["path"] and type(pin["sha256"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]) is not None
                and type(pin["size_bytes"]) is int and pin["size_bytes"] > 0)
            paths.append(pin["path"])
        require(len(paths) == len(set(paths)))
        for failure in capture["failures"]:
            validate_genomic_overlap_record("Failure", failure)
        if capture["worker_result_file"] is not None:
            self.file_metadata(capture["worker_result_file"])
        result = capture["result"]
        if result is None:
            require(capture["outputs"] == [])
        else:
            result = validate_genomic_overlap_result_worker_result(result)
            self.file_metadata(capture["worker_result_file"], value=result)
            require(result["mode"] == plan["mode"] and same(result["parameters"], selector["parameters"])
                and len(capture["outputs"]) == 4)
            for row, declaration in zip(capture["outputs"], result["outputs"]):
                validate_genomic_overlap_record("NativeFileCapture", row)
                require(same(row["declared"], declaration["declaration"]))
                observed = row["observed"]
                if observed is not None:
                    self.file_metadata(observed)
                if row["outcome"] == "verified":
                    require(observed is not None and observed["sha256"] == row["declared"]["sha256"]
                        and observed["size_bytes"] == row["declared"]["size_bytes"] and row["failure"] is None)

    def publication(self, receipt, *, originals=None):
        from .genomic_overlap_return_views import requested_genomic_overlap_sources
        intent = receipt["intent"]
        context = self.returns.context(intent["episode_id"])
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
        requested = requested_genomic_overlap_sources(schema)
        facts = empty_facts()
        projection, files = receipt["projection"], receipt["qualified_files"]
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
            if SAVED_SOURCE in requested and files["sheet"] is not None:
                facts[SAVED_SOURCE] = [deepcopy(files["sheet"])]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = self.selected_failures(receipt, issues)
        # Completion concerns captured inputs and requested delivery. A qualified
        # unavailable measurement, e.g. incompatible reference metadata, is an
        # answer; its scientific value is not an operational acceptance gate.
        complete = (intent["tool_name"] == "execution.results.collect"
            and projection is not None
            and not receipt["host_failures"]
            and (PROJECTION_SOURCE not in requested or bool(facts[PROJECTION_SOURCE]))
            and (SAVED_SOURCE not in requested or bool(facts[SAVED_SOURCE])))
        if intent["assignment"]["selector"]["mode"] == "native_result":
            complete = complete and self.original_acquisition_complete(receipt)
        else:
            # A failed intervening projection does not erase complete original
            # acquisition. All origins are authenticated; one complete witness
            # for this exact sheet and historical target suffices.
            originals = self.origins(context, intent["assignment"]) if originals is None else originals
            complete = complete and any(self.original_acquisition_complete(row) for row in originals)
        return facts, bool(complete)

    def selected_failures(self, receipt, issues):
        """Select located failure facts, preserving full private diagnostics."""
        intent = receipt["intent"]
        request = intent["target"]["assignment"]["requested_job"]["native_genomic_overlap"]["request"]
        selected = set(intent["assignment"]["selector"]["comparison_keys"])
        sets = {pair[side] for pair in request["comparisons"] if pair["comparison_key"] in selected
                for side in ("a_set_key", "b_set_key")}
        capture = receipt["capture"]
        files = [] if capture is None else capture["files"]
        artifacts = {}
        def related(spec):
            return (spec.get("comparison_key") is None or spec["comparison_key"] in selected) \
                and (spec.get("set_key") is None or spec["set_key"] in sets)
        def artifact(reference, relevant):
            artifacts.setdefault(reference, []).append(relevant)
        for spec in request["region_sets"]:
            artifact(spec["source"]["file"]["artifact_ref"], spec["set_key"] in sets)
        for row in files:
            if row["retained"] is not None:
                artifact(row["retained"]["file"]["artifact_ref"], related(row["specification"]))
        projected = set() if receipt["projection"] is None else {
            canonical(row) for row in receipt["projection"]["failures"]}
        worker_qualification = set() if receipt["worker_capture"] is None else {
            canonical(row) for row in receipt["worker_capture"]["failures"]}
        globals_ = ("/batch", "/worker", "/worker_result", "/worker_execution", "/execution", "/plan",
            "/sheet", "/components", "/projection", "/outputs", "/native", "/software", "/selector/saved_sheet_file")
        result = []
        for issue in unique(issues):
            if not related(issue):
                continue
            path = issue["field_path"] or ""
            match = re.match(r"^/(files|sets|region_sets|inputs|pairs|comparisons|reference_relations)/(0|[1-9][0-9]*)(?:/|$)", path)
            located = None
            if match is not None:
                kind, index = match[1], int(match[2])
                if kind == "files" and index < len(files):
                    located = related(files[index]["specification"])
                elif kind in {"sets", "region_sets", "inputs"} and index < len(request["region_sets"]):
                    located = request["region_sets"][index]["set_key"] in sets
                elif kind in {"pairs", "comparisons", "reference_relations"} and index < len(request["comparisons"]):
                    located = request["comparisons"][index]["comparison_key"] in selected
            if located is not None:
                if located:
                    result.append(issue)
                continue
            if issue["comparison_key"] is not None or issue["set_key"] is not None or canonical(issue) in projected:
                result.append(issue)
            elif any(path == root or path.startswith(root + "/") for root in globals_):
                result.append(issue)
            elif issue["artifact_ref"] in artifacts:
                if any(artifacts[issue["artifact_ref"]]):
                    result.append(issue)
            elif issue["stage"] == "authority" and issue["code"] == "original_attempt_mismatch":
                result.append(issue)
            elif canonical(issue) in worker_qualification or issue["stage"] == "native" and issue["code"] in {
                    "native_dependency_unavailable", "native_version_unverified", "native_nonzero_exit", "resource_limit"}:
                #434 qualification concerns this selected worker. An unlocated
                # execution failure does not imply an unrelated comparison.
                result.append(issue)
        return result

    def original_acquisition_complete(self, receipt):
        if receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation":
            context = self.returns.context(receipt["intent"]["episode_id"])
            originals = self.origins(context, receipt["intent"]["assignment"])
            return any(self.original_acquisition_complete(row) for row in originals)
        observation, capture = receipt["observation"], receipt["capture"]
        return bool(observation is not None and observation["state"] == "completed"
            and observation["returncode"] == 0 and observation["native"]["terminal"]
            and observation["native"]["quiescent"] and capture is not None
            and capture["driver_state"] == "sealed_batch" and capture["batch"] is not None
            and not capture["failures"])

    def acquisition_population(self, receipt):
        """Qualify one original acquired population, without numeric scoring."""
        evidence = receipt["acquisition_evidence"]
        original = receipt["intent"]["assignment"]["selector"]["mode"] == "native_result"
        sheet = receipt["qualified_files"]["sheet"]
        if not original or receipt["intent"]["tool_name"] != "execution.results.collect" or sheet is None:
            require(evidence is None)
            return None
        closed(evidence, GenomicOverlapAcquisitionEvidence.__annotations__)
        require(evidence["version"] == "genomic_overlap_acquisition_evidence_v1"
            and same(evidence["sheet_file"], sheet))
        self.file_metadata(sheet)
        plan, capture = receipt["native"]["original_plan"], receipt["capture"]
        keys = [row["comparison_key"] for row in plan["requested_job"]["native_genomic_overlap"]["request"]["comparisons"]]
        require(type(evidence["comparison_receipts"]) is list and
            [row.get("comparison_key") for row in evidence["comparison_receipts"]] == keys)
        identity = {**{key: plan["identity"][key] for key in
            ("run_id", "resource_id", "execution_id", "attempt_id", "operation_key")},
            "origin_episode_id": plan["identity"]["episode_id"]}
        controls = [receipt["source_action_file"]["artifact_ref"], receipt["writer_closure_file"]["artifact_ref"]]
        acquired = False
        for value in evidence["comparison_receipts"]:
            native = validate_genomic_overlap_record("NativePairReceipt", value)
            require(same(native["identity"], identity) and native["completeness_source_refs"][:2] == controls)
            comparison = native["comparison_key"]
            stdout, = [row for row in capture["files"] if row["specification"]["role"] == "overlap_stdout"
                and row["specification"]["comparison_key"] == comparison]
            captured_stdout = stdout["retained"]
            if native["stdout"] is not None:
                self.file_metadata(native["stdout"])
                require(captured_stdout is not None and same(native["stdout"], captured_stdout["file"]))
            original_stdout = (captured_stdout is not None and native["stdout"] is not None
                and (stdout["capture"] is None or stdout["capture"]["outcome"] == "verified"))
            if (native["derivation"] == "bedtools_intersect" and native["writer_closed"] is True
                    and native["capture_extent"] in {"complete", "partial"} and original_stdout):
                acquired = True
            manifests = [row["retained"]["file"]["artifact_ref"] for row in capture["files"]
                if row["specification"]["role"] == "pair_manifest"
                and row["specification"]["comparison_key"] == comparison and row["retained"] is not None
                and (row["capture"] is None or row["capture"]["outcome"] == "verified")]
            if capture["batch"] is not None:
                manifests.append(capture["batch"]["file"]["artifact_ref"])
            if (native["derivation"] == "validated_empty_input" and native["outcome"] == "not_executed"
                    and native["writer_closed"] is True and native["capture_extent"] == "complete"
                    and native["native_result_extent"] == "complete"
                    and native["completeness_basis"] == "validated_empty_input" and native["stdout"] is None
                    and receipt["native"]["driver_started"] is True
                    and any(ref in native["completeness_source_refs"][2:] for ref in manifests)):
                acquired = True
        return digest(plan["identity"]) if acquired else None

    def validate(self, receipt, intent):
        receipt = _finite_json_copy(receipt)
        closed(receipt, GenomicOverlapResultReceipt.__annotations__)
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
                capture = validate_genomic_overlap_native_capture(receipt["capture"], original_plan=receipt["native"]["original_plan"])
                self.file_metadata(receipt["source_action_file"], value=receipt["handoff_proof"]["start_receipt"])
                self.file_metadata(receipt["writer_closure_file"], value=closure_value(receipt))
                require(capture["source_action_receipt_ref"] == receipt["source_action_file"]["artifact_ref"]
                    and capture["writer_closure_receipt_ref"] == receipt["writer_closure_file"]["artifact_ref"]
                    and capture["driver_started"] is receipt["native"]["driver_started"])
            else:
                require(receipt["source_action_file"] is None and receipt["writer_closure_file"] is None)
        self.validate_worker(receipt)
        expected_files = qualified_files(receipt["worker_capture"], receipt["worker_execution"])
        require(same(receipt["qualified_files"], expected_files))
        projection = receipt["projection"]
        if expected_files["projection"] is None:
            require(projection is None)
        else:
            require(expected_files["sheet"] is not None and expected_files["components"] is not None)
            validate_genomic_overlap_record("Projection", projection)
            self.file_metadata(expected_files["projection"], value=projection)
            selector = intent["assignment"]["selector"]
            require(projection["source_sheet_sha256"] == expected_files["sheet"]["sha256"]
                and same(projection["parameters"], selector["parameters"])
                and projection["kind"] == selector["projection"]["kind"]
                and projection["measurement_fields"] == selector["projection"]["measurement_fields"]
                and all(projection["page"][key] == selector["projection"][key] for key in ("offset", "limit")))
        require(type(receipt["host_failures"]) is list)
        for row in receipt["host_failures"]:
            validate_genomic_overlap_record("Failure", row)
        closed(receipt["facts"], GenomicOverlapFactGroups.__annotations__)
        for source, rows in receipt["facts"].items():
            validate_genomic_overlap_fact_values(source, rows)
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
                ("acquisition-evidence.json", "acquisition_evidence")):
            require(same(read_control(root / name), receipt[key]))
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
        require(marker not in active, "genomic_overlap_result_cyclic_authority")
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
                closed(intent, GenomicOverlapResultIntent.__annotations__)
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
            capture = candidate.get("worker_capture")
            if type(capture) is not dict:
                continue
            identities = [item["observed"] for item in capture.get("outputs", []) if item.get("observed") is not None]
            # Malformed orphan outputs retained as diagnostics are private too.
            identities.extend(item["observed_value"] for item in capture.get("failures", [])
                if item.get("field_path") in {"/outputs/" + key for key in _OUTPUTS}
                and type(item.get("observed_value")) is dict and "artifact_ref" in item["observed_value"])
            if any(file["artifact_ref"] == reference for file in identities):
                original = self.returns.context(row["episode_id"])
                self.read_completed(episode_id=row["episode_id"], operation_key=candidate["intent"]["operation_key"],
                    scope=plain(original.scope))
                return True
        return False

    def baseline_populations(self, context, references):
        """Subtract actual frozen inherited populations, without operand grants."""
        from .episode_receipts import EpisodeReceipts
        self._context(context, allow_unsaved=True)
        receipts = EpisodeReceipts(self.store, self.owner.run_id)
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
            require(current.episode_id not in visited, "genomic_overlap_result_cyclic_authority")
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
                for file in groups[SAVED_SOURCE]:
                    if file["artifact_ref"] not in baseline:
                        continue
                    for episode_id in origins[canonical(file)]:
                        for receipt in self.completed_receipts(self.returns.context(episode_id)):
                            if any(same(file, saved) for saved in receipt["facts"][SAVED_SOURCE]):
                                population(receipt)
            current = parent
        return result


__all__ = ["GenomicOverlapResultReceipts", "GenomicOverlapResultAction", "GenomicOverlapResultReceipt", "VERSION"]
