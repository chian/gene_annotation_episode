"""Selected atac action controls and historical completed-action authority.

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
from .native_file_capture import NativeFileIdentity, _identity
from .atac_differential_result_contracts import validate_atac_result_record
from .atac_differential_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    validate_atac_fact_values,
)
from .atac_differential_result_worker import (
    validate_atac_result_worker_plan, validate_atac_result_worker_result,
)
from .native_atac_differential_capture import validate_atac_native_capture
from .native_atac_differential_contracts import (
    POLICY, atac_driver_argv,
    validate_atac_requested_job, validate_atac_run_plan, _dependency_roots,
)
from .practical_execution_records import validate_receipt
from .practical_receipt_information import PracticalReceiptInformation
from .progress_records import validate_resource_observation


VERSION = "native_atac_differential_acquired_result_v1"


class AtacDifferentialResultIntent(TypedDict):
    version: Literal["atac_differential_result_intent_v1"]
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


class AtacDifferentialHandoffProof(TypedDict):
    source_record: dict
    body: dict
    assignment_snapshot: dict
    start_receipt: dict


class AtacDifferentialNativeSnapshot(TypedDict):
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


class AtacDifferentialOrigin(TypedDict):
    episode_id: str
    operation_key: str


class AtacDifferentialQualifiedFiles(TypedDict):
    sheet: NativeFileIdentity | None
    calculations: NativeFileIdentity | None
    projection: NativeFileIdentity | None
    diagnostics: NativeFileIdentity | None
    tables: list[dict]
    calculated_tables: list[dict]


class AtacDifferentialFactGroups(TypedDict):
    atac_differential_projection: list[dict]
    atac_differential_saved_sheets: list[dict]
    atac_differential_failures: list[dict]


class AtacDifferentialSheetEvidence(TypedDict):
    version: Literal["atac_differential_sheet_evidence_v1"]
    sheet_file: NativeFileIdentity
    request_sha256: str
    original_identity: dict
    reference: dict
    samples: list[dict]
    conditions: list[dict]
    callpeak_bindings: list[dict]
    comparison: dict
    bam_references: list[dict]
    depth_selection: dict
    parsed_extents: list[dict]
    raw_tables: list[dict]
    calculations: dict | None
    projection_file: NativeFileIdentity | None
    native_record_population: bool
    private_refs: list[str]


class AtacDifferentialResultReceipt(TypedDict):
    version: Literal["native_atac_differential_acquired_result_v1"]
    intent: AtacDifferentialResultIntent
    handoff_proof: AtacDifferentialHandoffProof
    original_origins: list[AtacDifferentialOrigin]
    observation: dict | None
    native: AtacDifferentialNativeSnapshot | None
    source_action_file: NativeFileIdentity | None
    writer_closure_file: NativeFileIdentity | None
    capture: dict | None
    worker_plan: dict | None
    worker_capture: dict | None
    worker_execution: dict | None
    qualified_files: AtacDifferentialQualifiedFiles
    projection: dict | None
    host_failures: list[dict]
    facts: AtacDifferentialFactGroups
    sheet_evidence: AtacDifferentialSheetEvidence | None
    acquired_population: str | None
    delivery_complete: bool


@dataclass(frozen=True)
class AtacDifferentialResultAction:
    intent: AtacDifferentialResultIntent
    directory: Path


_READING = ContextVar("atac_differential_receipt_reading", default=())
_READ_CACHE = ContextVar("atac_differential_receipt_read_cache", default=None)
_OUTPUTS = ("sheet", "calculations", "projection", "diagnostics")
_TRACK_ROLES = ("signal1", "background1", "signal2", "background2")


def _finite_json_copy(value):
    canonical(value)  # Reject NaN/infinity; controls are ordinary finite JSON.
    return deepcopy(value)


def require(condition, code="atac_differential_result_authority_conflict"):
    if not condition:
        raise ValueError(code)


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), "atac_differential_result_invalid_record")


def same(left, right):
    return canonical(left) == canonical(right)


def artifact_references(value):
    """Locate artifact identities in validated nested controls and measurements.

    Software dependency objects are part of the control records. They are not
    the reference-string dependencies used by Store scientific records.
    """
    if isinstance(value, dict):
        for child in value.values():
            yield from artifact_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from artifact_references(child)
    elif type(value) is str and re.fullmatch(r"artifact_[0-9a-f]{64}", value):
        yield value


def decode(raw, *, newline=False, canonical_bytes=True):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "atac_differential_result_duplicate_key")
            result[key] = value
        return result
    value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs))
    require(not canonical_bytes or raw == canonical(value).encode("utf-8") + (b"\n" if newline else b""),
            "atac_differential_result_noncanonical_control")
    return value


@contextmanager
def directory(path, *, create=False):
    value = str(path)
    pure = PurePosixPath(value)
    require(pure.is_absolute() and str(pure) == value and value != "/" and ".." not in pure.parts
            and not any(c in value for c in "\0\r\n\\"), "atac_differential_result_invalid_path")
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
        require(os.fstat(fd).st_uid == os.geteuid(), "atac_differential_result_invalid_path")
        yield fd


@contextmanager
def regular(fd, name, *, flags=os.O_RDONLY):
    require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
    handle = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        require(stat.S_ISREG(os.fstat(handle).st_mode), "atac_differential_result_invalid_path")
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
    require(type(value) is dict, "atac_differential_result_invalid_record")
    return value


def immutable(path, value):
    value = _finite_json_copy(value)
    with directory(path.parent, create=True) as fd:
        previous = read_control(path)
        if previous is not None:
            require(same(previous, value), "atac_differential_result_control_conflict")
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
                require(same(read_control(path), value), "atac_differential_result_control_conflict")
            os.fsync(fd)
        finally:
            os.unlink(temporary, dir_fd=fd)


def empty_facts() -> AtacDifferentialFactGroups:
    return {source: [] for source in FACT_SOURCES}


def empty_files() -> AtacDifferentialQualifiedFiles:
    return {**{role: None for role in _OUTPUTS}, "tables": [], "calculated_tables": []}


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
        for file in (bundle["sheet"], *(r["file"] for r in bundle["tables"]))))
    return {"status": "completed", "record_refs": refs, "changed_record_refs": refs,
            "result": deepcopy(receipt), "feedback": None}


def qualified_files(capture, execution):
    result = empty_files()
    if capture is None or capture["result"] is None or execution is None:
        return result
    validate_atac_result_record("WorkerCapture", capture)
    declared = validate_atac_result_worker_result(capture["result"])["outputs"]
    require(len(declared) == len(capture["outputs"]))
    success = (execution["returncode"] == 0 and execution["failure"] is None
        and execution["terminal"] is True and execution["quiescent"] is True)
    for expected, row in zip(declared, capture["outputs"]):
        require(row["role"] == expected["role"] and row["table_key"] == expected["table_key"]
            and same(row["capture"]["declared"], expected["declaration"]))
        file = deepcopy(row["capture"]["observed"]) if success and row["capture"]["outcome"] == "verified" else None
        if row["role"] == "track_table":
            result["tables"].append({"table_key": row["table_key"], "file": file})
        elif row["role"] in {"partitions", "components", "regions"}:
            result["calculated_tables"].append({"table_key": row["table_key"], "role": row["role"], "file": file})
        else:
            require(row["role"] in _OUTPUTS)
            result[row["role"]] = file
    return result


def closure_value(receipt):
    return {"version": "atac_differential_writer_closure_v1", "intent_sha256": digest(receipt["intent"]),
        "native": receipt["native"], "observation": receipt["observation"]}


class AtacDifferentialResultReceipts:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self._active = {}

    @property
    def returns(self):
        return self.owner.atac_returns

    def action_directory(self, episode_id, operation_key):
        return self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id]) / "native-atac-interaction-actions" / digest(operation_key)

    def _context(self, context, *, allow_unsaved=False):
        self.returns.authenticate(context, allow_unsaved=allow_unsaved)
        require(isinstance(context, BindingContext) and context.role == "results")
        assignment = plain(context.assignment)
        closed(assignment, ("version", "handoff_ref", "selector"))
        require(assignment["version"] == "execution_results_assignment_v1")
        validate_atac_result_record("ResultSelector", assignment["selector"])
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

    def _target(self, context, assignment, target, *, current_binding=False):
        target = validate_target(_finite_json_copy(target))
        require(target["run_id"] == self.owner.run_id == context.run_id and target["resource_kind"] == "local"
            and target["handle"] == assignment["handoff_ref"])
        requested = validate_atac_requested_job(target["assignment"]["requested_job"])
        require(target["request_sha256"] == digest(requested)
            and target["assignment"]["resource_id"] == target["resource_id"])
        self.store.validate_scope(target["scope"], parent_scope=plain(context.scope))
        if current_binding:
            resource = self.owner.resources.get(target["resource_id"])
            require(type(resource) is dict and resource["kind"] == "local" and same(resource["policy"], POLICY))
            reader = self.owner.job_progress_provider.targets
            require(same(reader.resources.get(target["resource_id"]), resource)
                and target["resource_id"] in reader.operations)
            reader.operations[target["resource_id"]].validate_assignment(target["assignment"])
        selector = assignment["selector"]
        from .atac_differential_execution_information import validate_atac_result_selector
        request = requested["native_atac_differential"]["request"]
        validate_atac_result_selector(selector, request=request)
        return target

    def intent(self, context, target, tool_name, arguments, operation_key):
        assignment = self._context(context)
        require(tool_name in ("execution.results.status", "execution.results.collect")
            and type(arguments) is dict and arguments == {})
        original = read_control(self.action_directory(context.episode_id, operation_key) / "intent.json")
        value = {"version": "atac_differential_result_intent_v1", "run_id": context.run_id,
            "episode_id": context.episode_id, "path": plain(context.path), "scope": plain(context.scope),
            "assignment": assignment, "original_request_sha256": digest(plain(context.request)),
            "operation_key": operation_key, "tool_name": tool_name, "arguments": {},
            "target": self._target(context, assignment, target, current_binding=(original is None
                and assignment["selector"]["mode"] == "native_result"))}
        self._selected(value)
        if original is not None:
            require(same(original, value), "atac_differential_result_control_conflict")
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
                action = AtacDifferentialResultAction(deepcopy(intent), root)
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
        file = _identity(file)
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
        closed(proof, AtacDifferentialHandoffProof.__annotations__)
        source, body, snapshot, start = (proof[name] for name in AtacDifferentialHandoffProof.__annotations__)
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
        require(original.role == "launch_local" and len(original.path) > 2)
        launch = self.returns.context(EpisodeRef(self.owner.run_id, original.path[:-1]).episode_id)
        require(launch.role == "launch")
        self.returns._commission(launch, original)
        self.returns._commission(self.returns.context(EpisodeRef(self.owner.run_id, launch.path[:-1]).episode_id), launch)
        self.validate_launch_selection(plain(launch.assignment), assignment)
        selected_outcome = json.loads(selected["result"])
        require(selected_outcome.get("status") in ("completed", "partial")
            and same(selected_outcome.get("result"), receipt) and source["id"] in selected_outcome.get("record_refs", []))
        require(receipt["tool_name"] in ("practical.job.start", "practical.job.status", "practical.job.collect"))
        requested = validate_atac_requested_job(assignment["requested_job"])
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

    @staticmethod
    def validate_launch_selection(launch, selected):
        """Check the original permitted choice without today's resource catalog."""
        from .launch_instructions import retain_inherited_selection
        require(launch.get("version") == "execution_launch_assignment_v1"
            and type(launch.get("requests")) is dict and type(launch.get("constraints")) is dict)
        resource = selected["resource_id"]
        require(resource in launch["requests"])
        expected = {**launch["requests"][resource], "resource_id": resource}
        retain_inherited_selection(launch.get("launch_instructions"), selected.get("launch_instructions"))
        retain_inherited_selection(expected.get("launch_instructions"), selected.get("launch_instructions"))
        require(same({k: v for k, v in expected.items() if k != "launch_instructions"},
            {k: v for k, v in selected.items() if k != "launch_instructions"}))
        constraints = launch["constraints"]
        require(("allowed_resource_ids" not in constraints or resource in constraints["allowed_resource_ids"])
            and ("allowed_kinds" not in constraints or "local" in constraints["allowed_kinds"])
            and constraints.get("resource_id", resource) == resource
            and constraints.get("kind", "local") == "local")
        for key, value in constraints.items():
            if key not in {"allowed_resource_ids", "allowed_kinds", "resource_id", "kind"}:
                require(same(selected["constraints"].get(key), value))

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
            from .native_atac_differential_local import local_atac_differential_plan, _strict_json
            from .native_atac_differential_driver import _read_control, confined_file
            from .native_atac_differential_contracts import STARTED_FILENAME
            from .native_file_capture import capture_native_file, retained_native_file
            target = action.intent["target"]
            plan = local_atac_differential_plan(target["assignment"], target["execution_id"])
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
                "plan_file": self.capture_control(action, "native-plan.json", plan, "atac_differential_run_plan_v1"),
                "handle_file": self.capture_control(action, "native-handle.json", handle, "durable_systemd_native_job_v2"),
                "request_file": request_file,
                "started_marker_file": None if marker is None else self.capture_control(action,
                    "driver-started.json", marker, "native_atac_started_v1")}
            self.validate_native(value, action.intent, observation)
            immutable(path, value)
        self.validate_native(value, action.intent, observation)
        return deepcopy(value)

    def validate_native(self, value, intent, observation):
        from .native_atac_differential_local import _request
        from .native_lifecycle import VERSION as native_version
        closed(value, AtacDifferentialNativeSnapshot.__annotations__)
        plan = validate_atac_run_plan(value["original_plan"])
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
            and handle.get("command") == atac_driver_argv(plan) and handle.get("cwd") == str(root)
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
            and value["plan_file"]["format"] == "atac_differential_run_plan_v1"
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
                and value["started_marker_file"]["format"] == "native_atac_started_v1")
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
        validate_atac_fact_values(SAVED_SOURCE, [bundle])
        origins = self.returns.authenticate_received_saved_bundle(context, bundle)
        matches = []
        require(type(origins) is tuple and bool(origins), "atac_saved_handoff_conflict")
        for origin in origins:
            closed(origin, ("episode_id", "operation_key"))
            row = self.read_completed(**origin, scope=plain(context.scope))
            require(any(same(bundle, saved) for saved in row["facts"][SAVED_SOURCE])
                and row["intent"]["target"]["handle"] == assignment["handoff_ref"], "atac_saved_handoff_conflict")
            matches.append(row)
        require(len(unique(origins)) == len(origins))
        require(all(same(row["intent"]["target"], matches[0]["intent"]["target"]) for row in matches),
            "atac_saved_target_conflict")
        return matches

    def validate_worker(self, receipt, *, verify_control_bytes=False):
        """Bind the saved finite worker to the selected plan, without reexecution."""
        plan, capture, execution = (receipt[k] for k in ("worker_plan", "worker_capture", "worker_execution"))
        if plan is None:
            require(capture is None and execution is None)
            return
        plan = validate_atac_result_worker_plan(plan)
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
            expected = {"sheet": plan["sheet_bundle"]["sheet"]["file"], "tables": [
                {"track_key": row["track_key"], "file": row["file"]} for row in plan["sheet_bundle"]["tables"]]}
            require(same(expected, selector["saved_sheet_bundle"]))
        for item in retained:
            if item is not None:
                file = self.file_metadata(item["file"])
                require(item["path"] == str(self.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]))
        if capture is None:
            require(execution is None)
            return
        validate_atac_result_record("WorkerCapture", capture)
        closed(execution, ("version", "plan_file", "intent", "terminal", "quiescent", "policy", "returncode",
            "metadata", "failure", "handle_file", "request_file", "stdout_file", "stderr_file"))
        require(execution["version"] == "atac_worker_execution_v1"
            and same(execution["plan_file"], capture["plan_file"]) and same(execution["policy"], POLICY)
            and execution["terminal"] is True and execution["quiescent"] is True)
        self.file_metadata(capture["plan_file"], value=plan)
        self.file_metadata(capture["execution_receipt_file"], value=execution)
        require(capture["plan_file"]["format"] == "atac_differential_worker_plan_v1"
            and capture["execution_receipt_file"]["format"] == "atac_worker_execution_v1")
        selected = execution["intent"]
        closed(selected, ("version", "plan", "policy", "command", "environment", "source_pins", "interpreter", "dependencies"))
        require(selected["version"] == "atac_worker_intent_v1" and same(selected["plan"], plan)
            and same(selected["policy"], POLICY))
        require(type(selected["source_pins"]) is list and bool(selected["source_pins"])
            and type(selected["dependencies"]) is list)

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
        required = ("atac_differential_result_worker", "atac_differential_contracts", "atac_differential_inputs",
            "atac_differential_sheet", "atac_differential_calculations", "atac_differential_scores",
            "atac_differential_calculation_inputs", "atac_reference_observations", "atac_differential_result_views")
        require(all(str(root / "source_snapshot/gene_annotation_episode" / (name + ".py")) in paths for name in required))
        names = []
        for dependency in selected["dependencies"]:
            closed(dependency, ("distribution", "version", "package_root", "files"))
            require(type(dependency["distribution"]) is str and bool(dependency["distribution"])
                and type(dependency["version"]) is str and bool(dependency["version"])
                and type(dependency["package_root"]) is str and Path(dependency["package_root"]).is_absolute()
                and type(dependency["files"]) is list and bool(dependency["files"]))
            names.append(dependency["distribution"].lower().replace("_", "-"))
            for row in dependency["files"]:
                pin(row)
            require(len({p["path"] for p in dependency["files"]}) == len(dependency["files"]))
        require(len(names) == len(set(names))
            and {"jsonschema", "attrs", "referencing", "rpds-py", "jsonschema-specifications"} <= set(names))
        require(selected["interpreter"]["path"] == str(root / "runtime/python")
            and selected["command"] == [str(root / "runtime/python"), "-B", "-S", "-m",
                "gene_annotation_episode.atac_differential_result_worker", str(root / "plan.json")])
        environment = selected["environment"]
        require(type(environment) is dict and all(type(k) is str and type(v) is str for k, v in environment.items()))
        expected = {"PYTHONPATH": os.pathsep.join([str(root / "source_snapshot"), *_dependency_roots(selected)]),
            "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
            "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip")}
        require(all(environment.get(k) == v for k, v in expected.items())
            and type(environment.get("PYTHONHOME")) is str and Path(environment["PYTHONHOME"]).is_absolute())
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
        if verify_control_bytes:
            from .native_file_capture import retained_native_file
            from .native_lifecycle import VERSION as native_version
            handle = decode(retained_native_file(self.store, execution["handle_file"]).read_bytes(), canonical_bytes=False)
            raw = retained_native_file(self.store, execution["request_file"]).read_bytes()
            request = decode(raw, canonical_bytes=False)
            require(handle["version"] == native_version and handle["command"] == selected["command"]
                and handle["cwd"] == str(root) and same(handle["metadata"]["policy"], POLICY)
                and handle["stage"] in {"prepared", "submitting", "released"}
                and handle["request_sha256"] == hashlib.sha256(raw).hexdigest())
            paths = handle["paths"]
            require(len(set(paths.values())) == len(paths) and all(Path(path).parent == root for path in paths.values()))
            require(same(request, {"command": selected["command"], "cwd": str(root),
                "file_bytes": POLICY["scratch_bytes"], "ready_path": paths["ready"],
                "release_path": paths["release"], "result_path": paths["result"], "stdin_path": None,
                "env": selected["environment"]}))
        if capture["worker_result_file"] is not None:
            self.file_metadata(capture["worker_result_file"])
            require(capture["worker_result_file"]["format"] == "atac_differential_worker_result_v1")
        result = capture["result"]
        if result is None:
            require(capture["outputs"] == [])
        else:
            result = validate_atac_result_worker_result(result)
            self.file_metadata(capture["worker_result_file"], value=result)
            require(result["mode"] == plan["mode"] and same(result["parameters"], selector["parameters"]))
            from .atac_differential_result_worker import worker_output_specs
            specs = worker_output_specs(plan)
            require(len(specs) == len(result["outputs"]))
            for spec, row in zip(specs, result["outputs"]):
                require(row["role"] == spec["role"] and row["table_key"] == spec["table_key"]
                    and row["declaration"]["relative_path"] == spec["relative_path"]
                    and row["declaration"]["format"] == spec["format"])
            qualified_files(capture, execution)
            for row in capture["outputs"]:
                if row["capture"]["observed"] is not None:
                    self.file_metadata(row["capture"]["observed"])

    @staticmethod
    def _raw_file(table):
        return {"artifact_ref": table["artifact_ref"], "sha256": table["sha256"],
            "size_bytes": table["byte_count"], "format": table["format"]}

    def _calculated_rows(self, manifest):
        """Read a supplied retained table; this projects and never recalculates."""
        from .native_file_capture import retained_native_file
        kind = {"partitions": "Partition", "components": "Component", "regions": "Region"}[manifest["role"]]
        path = retained_native_file(self.store, manifest["file"])
        count = 0
        with path.open("rb") as stream:
            for line in stream:
                require(line.endswith(b"\n"), "atac_result_unsealed_calculated_row")
                row = validate_atac_result_record(kind, decode(line, newline=True))
                count += 1
                yield row
        require(count == manifest["row_count"], "atac_result_calculated_row_count_conflict")
        retained_native_file(self.store, manifest["file"])

    @staticmethod
    def _extent_record(group, report):
        return {"group": group, "binding_key": report["binding_key"],
            "artifact": deepcopy(report["artifact"]), "state": deepcopy(report["state"]),
            "parsed_sha256": report["parsed_sha256"], "parsed_byte_count": report["parsed_byte_count"],
            "data_row_count": report["data_row_count"], "readable_data_row_count": report["readable_data_row_count"],
            "malformed_data_row_count": report["malformed_data_row_count"],
            "reported_numbers": deepcopy(report.get("reported_numbers"))}

    def sheet_evidence(self, action, receipt):
        """Freeze native joins and exact numerical output identities once."""
        from .native_file_capture import retained_native_file
        from .atac_differential_result_views import project_atac_result
        from .native_atac_differential_contracts import producer_ref, validate_atac_command_seal
        self.require_action(action)
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            return None
        path = action.directory / "sheet-evidence.json"
        evidence = read_control(path)
        if evidence is None:
            self.validate_worker(receipt, verify_control_bytes=True)
            sheet = validate_atac_result_record("NativeSheet", decode(retained_native_file(self.store, files["sheet"]).read_bytes()))
            self.file_metadata(files["sheet"], value=sheet)
            requested = receipt["intent"]["target"]["assignment"]["requested_job"]["native_atac_differential"]["request"]
            require(all(same(sheet[key], requested[key]) for key in ("reference", "samples", "conditions")))
            require(sheet["comparison"]["comparison_key"] == requested["comparison_key"])
            saved = receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation"
            if saved:
                originals = self.origins(self.returns.context(action.intent["episode_id"]), action.intent["assignment"])
                identity = deepcopy(originals[0]["sheet_evidence"]["original_identity"])
                require(all(same(row["sheet_evidence"]["original_identity"], identity) for row in originals))
            else:
                plan = receipt["native"]["original_plan"]
                identity = deepcopy(plan["identity"])
                captured = {row["specification"]["file_key"]: row for row in receipt["capture"]["files"]}
                for ordinal, run in enumerate(sheet["callpeak_bindings"]):
                    step = "callpeak" + str(ordinal + 1)
                    source = captured[step + ".seal"]["retained"]
                    require(run["run_key"] == step and run["producer_ref"] == producer_ref(plan, step))
                    require(run["condition_id"] == requested["conditions"][ordinal]["condition_id"]
                        and run["sample_ids"] == requested["conditions"][ordinal]["sample_ids"]
                        and run["treatment_input_refs"] == [requested["inputs"][ordinal]["file"]["artifact_ref"]]
                        and run["reference_id"] == requested["reference"]["reference_id"])
                    if source is not None and captured[step + ".seal"]["outcome"] == "verified":
                        seal = validate_atac_command_seal(decode(retained_native_file(self.store, source["file"]).read_bytes()),
                            plan=plan, step_key=step)
                        require(run["selected_argv"] == seal["argv"])
                    roles = {"peaks_xls": "peaks_xls", "narrowpeak": "narrowpeak", "summits": "summits",
                        "signal_track": "signal", "background_track": "background"}
                    for role, suffix in roles.items():
                        retained = captured[step + "." + suffix]["retained"]
                        require(run["artifact_roles"][role] == (None if retained is None else retained["file"]["artifact_ref"]))
                require(len(sheet["callpeak_bindings"]) == 2)
            raw_tables = [{"track_key": track["binding"]["track_key"], "table": deepcopy(track["rows"])}
                for track in sheet["tracks"] if type(track["rows"]) is dict]
            qualified_raw = {row["table_key"]: row["file"] for row in files["tables"]}
            for row in raw_tables:
                original = self._raw_file(row["table"])
                if same(qualified_raw.get(row["track_key"]), original):
                    retained_native_file(self.store, original)
                else:
                    require(saved)
            calculations = None
            if files["calculations"] is not None:
                calculations = validate_atac_result_record("Calculations",
                    decode(retained_native_file(self.store, files["calculations"]).read_bytes()))
                self.file_metadata(files["calculations"], value=calculations)
                selected = receipt["intent"]["assignment"]["selector"]
                require(calculations["comparison_key"] == sheet["comparison"]["comparison_key"]
                    and calculations["reference_id"] == sheet["reference"]["reference_id"]
                    and calculations["condition_ids"] == [r["condition_id"] for r in sheet["conditions"]]
                    and same(calculations["parameters"], selected["parameters"])
                    and same(calculations["selected_intervals"], selected["intervals"])
                    and same(calculations["summary"]["depth_selection"], sheet["depth_selection"]))
                manifests = {row["table_key"]: row for row in calculations["tables"]}
                if files["projection"] is not None:
                    kind = selected["projection"]["kind"]
                    kwargs = {}
                    if kind in {"interval_components", "derived_regions"}:
                        key = "components" if kind == "interval_components" else "regions"
                        kwargs["component_rows" if key == "components" else "region_rows"] = (
                            self._calculated_rows(manifests[key]) if key in manifests else None)
                    actual = decode(retained_native_file(self.store, files["projection"]).read_bytes())
                    require(same(project_atac_result(sheet, calculations, selector=selected, **kwargs), actual)
                        and same(actual, receipt["projection"]))
                    self.file_metadata(files["projection"], value=actual)
            else:
                require(receipt["projection"] is None)
            extents = [self._extent_record(group, report) for group in
                ("tracks", "peaks_xls", "narrowpeaks", "summits", "native_differential", "bam_references")
                for report in sheet[group]]
            evidence = {"version": "atac_differential_sheet_evidence_v1", "sheet_file": deepcopy(files["sheet"]),
                "request_sha256": digest(requested), "original_identity": identity,
                **{k: deepcopy(sheet[k]) for k in ("reference", "samples", "conditions", "callpeak_bindings",
                    "comparison", "bam_references", "depth_selection")},
                "parsed_extents": extents, "raw_tables": raw_tables, "calculations": calculations,
                "projection_file": deepcopy(files["projection"]), "native_record_population": False,
                "private_refs": sorted(set(self.store._refs(sheet)) | set(self.store._refs(calculations or {})))}
            evidence["native_record_population"] = self._has_native_population(receipt, evidence)
            self.validate_sheet_evidence(receipt, evidence)
            immutable(path, evidence)
        self.validate_sheet_evidence(receipt, evidence)
        return deepcopy(evidence)

    def validate_sheet_evidence(self, receipt, evidence):
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            require(evidence is None)
            return
        closed(evidence, AtacDifferentialSheetEvidence.__annotations__)
        request = receipt["intent"]["target"]["assignment"]["requested_job"]["native_atac_differential"]["request"]
        require(evidence["version"] == "atac_differential_sheet_evidence_v1"
            and same(evidence["sheet_file"], files["sheet"]) and evidence["request_sha256"] == digest(request)
            and all(same(evidence[key], request[key]) for key in ("reference", "samples", "conditions"))
            and evidence["comparison"]["comparison_key"] == request["comparison_key"])
        self.file_metadata(evidence["sheet_file"])
        saved = receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation"
        identity = evidence["original_identity"]
        require(identity["execution_id"] == receipt["intent"]["target"]["execution_id"]
            and identity["requested_job_sha256"] == receipt["intent"]["target"]["request_sha256"])
        if not saved:
            require(same(identity, receipt["native"]["original_plan"]["identity"]))
        require(type(evidence["raw_tables"]) is list and type(evidence["parsed_extents"]) is list
            and type(evidence["private_refs"]) is list and evidence["private_refs"] == sorted(set(evidence["private_refs"])))
        keys = [row["track_key"] for row in evidence["raw_tables"]]
        track_keys = [evidence["comparison"]["track_keys"][role] for role in _TRACK_ROLES]
        require(len(keys) == len(set(keys)) and keys == [key for key in track_keys if key in keys])
        qualified = {row["table_key"]: row["file"] for row in files["tables"]}
        from .atac_differential_contracts import validate_atac_retained_track_table
        for row in evidence["raw_tables"]:
            closed(row, ("track_key", "table"))
            validate_atac_retained_track_table(row["table"])
            file = self._raw_file(row["table"])
            self.file_metadata(file)
            require(row["track_key"] in qualified)
            if not same(file, qualified[row["track_key"]]):
                # A saved source may disappear or fail its late identity
                # check. Preserve its original manifest; a newly retained
                # corrupt/prefix copy cannot become that source identity.
                calculations = evidence["calculations"]
                require(saved and calculations is not None
                    and any(state["track_key"] == row["track_key"] and not state["exhausted"]
                        for state in calculations["stream_states"])
                    and any(problem["code"] in {"calculation_stream_failed", "saved_attachment_unavailable", "artifact_digest_mismatch"}
                        for problem in calculations["failures"]))
            matching = [record for record in evidence["parsed_extents"] if record["group"] == "tracks"
                and record["binding_key"] == row["track_key"]]
            require(len(matching) == 1 and row["table"]["source_artifact_ref"] == matching[0]["artifact"]["artifact_ref"]
                and row["table"]["row_count"] == matching[0]["readable_data_row_count"])
        calculations = evidence["calculations"]
        require((calculations is None) == (files["calculations"] is None)
            and same(evidence["projection_file"], files["projection"]))
        if calculations is not None:
            validate_atac_result_record("Calculations", calculations)
            self.file_metadata(files["calculations"], value=calculations)
            selector = receipt["intent"]["assignment"]["selector"]
            require(same(calculations["parameters"], selector["parameters"])
                and same(calculations["selected_intervals"], selector["intervals"])
                and calculations["comparison_key"] == selector["comparison_key"]
                and calculations["reference_id"] == evidence["reference"]["reference_id"]
                and calculations["condition_ids"] == [row["condition_id"] for row in evidence["conditions"]]
                and same(calculations["summary"]["depth_selection"], evidence["depth_selection"]))
            captured = {row["table_key"]: row["file"] for row in files["calculated_tables"]}
            require(len({row["table_key"] for row in calculations["tables"]}) == len(calculations["tables"]))
            for table in calculations["tables"]:
                validate_atac_result_record("CalculatedTable", table)
                self.file_metadata(table["file"])
                require(table["table_key"] in captured)
                if captured[table["table_key"]] is not None:
                    require(same(captured[table["table_key"]], table["file"]))
                expected = {"partitions": track_keys,
                    "components": ["partitions"], "regions": ["components"]}[table["role"]]
                require(table["source_table_keys"] == expected)
        require(type(evidence["native_record_population"]) is bool
            and evidence["native_record_population"] == self._has_native_population(receipt, evidence))
        if saved:
            require(same(receipt["intent"]["assignment"]["selector"]["saved_sheet_bundle"], self.evidence_bundle(evidence)))

    @classmethod
    def evidence_bundle(cls, evidence):
        return {"sheet": deepcopy(evidence["sheet_file"]), "tables": [
            {"track_key": row["track_key"], "file": cls._raw_file(row["table"])} for row in evidence["raw_tables"]]}

    def saved_bundle(self, receipt):
        evidence = receipt["sheet_evidence"]
        if evidence is None:
            return None
        self.validate_sheet_evidence(receipt, evidence)
        qualified = {row["table_key"]: row["file"] for row in receipt["qualified_files"]["tables"]}
        bundle = self.evidence_bundle(evidence)
        if any(not same(row["file"], qualified.get(row["track_key"])) for row in bundle["tables"]):
            return None
        return validate_atac_result_record("SavedSheetBundle", bundle)

    def publication(self, receipt, *, originals=None):
        from .atac_differential_return_views import requested_atac_sources
        intent = receipt["intent"]
        context = self.returns.context(intent["episode_id"])
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
        requested, facts = requested_atac_sources(schema), empty_facts()
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
        issues = unique(issues)
        for issue in issues:
            validate_atac_result_record("Failure", issue)
        collecting = intent["tool_name"] == "execution.results.collect"
        if collecting:
            if PROJECTION_SOURCE in requested and projection is not None:
                facts[PROJECTION_SOURCE] = [deepcopy(projection)]
            if SAVED_SOURCE in requested and bundle is not None:
                facts[SAVED_SOURCE] = [bundle]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = deepcopy(issues)
        # Delivery is evaluated against THIS requested result. The original
        # native outcome is preserved; it is not a saved-calculation veto.
        complete = (collecting and projection is not None and receipt["sheet_evidence"] is not None
            and (SAVED_SOURCE not in requested or bundle is not None))
        if complete:
            complete = self.requested_projection_complete(receipt)
        return facts, bool(complete)

    @staticmethod
    def requested_projection_complete(receipt):
        projection = receipt["projection"]
        if projection is None or projection["row_extent"] != "complete":
            return False
        if any(row["code"] in {"requested_field_unavailable", "return_authority_mismatch"}
                for row in projection["failures"]):
            return False
        kind = projection["kind"]
        if kind != "summary":
            total, window = projection["total_rows"], projection["row_window"]
            if total is None or len(projection["rows"]) != min(window["limit"], max(0, total - window["offset"])):
                return False
        evidence = receipt["sheet_evidence"]
        calculations = None if evidence is None else evidence["calculations"]
        if calculations is None:
            return False
        # Native row requests can succeed while an unrelated derived stream
        # failed. Summary/components/regions include those requested streams.
        if kind in {"summary", "interval_components", "derived_regions"}:
            if any(row["code"] == "calculation_stream_failed" for row in calculations["failures"]):
                return False
            if any(not row["exhausted"] for row in calculations["stream_states"]):
                return False
            wanted = {"summary": {"partitions", "components", "regions"},
                "interval_components": {"components"}, "derived_regions": {"regions"}}[kind]
            if any(table["extent"] != "complete" for table in calculations["tables"] if table["role"] in wanted):
                return False
        return True

    @staticmethod
    def _has_native_population(receipt, evidence):
        """Actual native numerical records, or a verified complete empty output."""
        if (receipt["intent"]["assignment"]["selector"]["mode"] != "native_result"
                or receipt["capture"] is None or receipt["native"] is None or receipt["observation"] is None):
            return False
        observation = receipt["observation"]["native"]
        if not observation["terminal"] or not observation["quiescent"]:
            return False
        files = receipt["capture"]["files"]
        for report in evidence["parsed_extents"]:
            if report["group"] not in {"tracks", "peaks_xls", "narrowpeaks", "summits", "native_differential"}:
                continue
            artifact, state = report["artifact"], report["state"]
            matching = [row for row in files if row["retained"] is not None
                and row["retained"]["file"]["artifact_ref"] == artifact["artifact_ref"]
                and row["specification"]["format"] == artifact["format"]]
            if (state["availability"] != "present" or state["identity"] != "verified"
                    or not any(row["outcome"] == "verified" for row in matching)):
                continue
            if report["readable_data_row_count"] > 0:
                return True
            if report["group"] == "peaks_xls" and report["reported_numbers"] is not None:
                if any(row["state"] == "present" and row["value"] is not None
                        for key, row in report["reported_numbers"].items()
                        if key.startswith("treatment_") and key.endswith(("tags", "fragments"))):
                    return True
            if (report["data_row_count"] == 0 and state["output_extent"] == "complete"
                    and state["format"] == "compatible" and artifact["producer_outcome"] == "succeeded"
                    and artifact["writer_closed"] is True):
                return True
        return False

    def acquisition_population(self, receipt):
        self.validate_sheet_evidence(receipt, receipt["sheet_evidence"])
        if (receipt["intent"]["assignment"]["selector"]["mode"] != "native_result"
                or receipt["intent"]["tool_name"] != "execution.results.collect" or receipt["sheet_evidence"] is None):
            return None
        return (digest(receipt["native"]["original_plan"]["identity"])
            if receipt["sheet_evidence"]["native_record_population"] else None)

    def validate(self, receipt, intent):
        receipt = _finite_json_copy(receipt)
        closed(receipt, AtacDifferentialResultReceipt.__annotations__)
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
                capture = validate_atac_native_capture(receipt["capture"], original_plan=receipt["native"]["original_plan"])
                self.file_metadata(receipt["source_action_file"], value=receipt["handoff_proof"]["start_receipt"])
                self.file_metadata(receipt["writer_closure_file"], value=closure_value(receipt))
                require(capture["source_action_receipt_ref"] == receipt["source_action_file"]["artifact_ref"]
                    and capture["writer_closure_receipt_ref"] == receipt["writer_closure_file"]["artifact_ref"]
                    and (receipt["native"]["driver_started"] is not False or capture["driver_state"] in {"not_run", "unknown"}))
            else:
                require(receipt["source_action_file"] is None and receipt["writer_closure_file"] is None)
        self.validate_worker(receipt)
        expected_files = qualified_files(receipt["worker_capture"], receipt["worker_execution"])
        require(same(receipt["qualified_files"], expected_files))
        self.validate_sheet_evidence(receipt, receipt["sheet_evidence"])
        projection = receipt["projection"]
        if projection is not None:
            require(expected_files["projection"] is not None and expected_files["sheet"] is not None
                and expected_files["calculations"] is not None and receipt["sheet_evidence"] is not None)
            validate_atac_result_record("RequestedProjection", projection)
            self.file_metadata(expected_files["projection"], value=projection)
            selector = intent["assignment"]["selector"]
            evidence = receipt["sheet_evidence"]
            require(projection["comparison_key"] == selector["comparison_key"]
                and projection["reference_id"] == evidence["reference"]["reference_id"]
                and projection["condition_ids"] == [row["condition_id"] for row in evidence["conditions"]]
                and same(projection["selected_intervals"], selector["intervals"])
                and same(projection["parameters"], selector["parameters"])
                and projection["kind"] == selector["projection"]["kind"]
                and same(projection["row_window"], selector["projection"]["row_window"]))
        else:
            require(expected_files["projection"] is None or expected_files["sheet"] is None
                or expected_files["calculations"] is None)
        require(type(receipt["host_failures"]) is list)
        for row in receipt["host_failures"]:
            validate_atac_result_record("Failure", row)
        closed(receipt["facts"], AtacDifferentialFactGroups.__annotations__)
        for source, rows in receipt["facts"].items():
            validate_atac_fact_values(source, rows)
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
        require(marker not in active, "atac_differential_result_cyclic_authority")
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
                closed(intent, AtacDifferentialResultIntent.__annotations__)
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
        """Protect private refs, including refs mentioned only in failures/metadata."""
        if type(reference) is not str or not reference.startswith("artifact_"):
            return False
        rows = self.store.db.execute("SELECT episode_id,result FROM runtime_actions WHERE run_id=? "
            "AND result IS NOT NULL AND json_extract(result,'$.result.version')=?", (self.owner.run_id, VERSION))
        for row in rows:
            candidate = json.loads(row["result"])["result"]
            request = candidate["intent"]["target"]["assignment"]["requested_job"]["native_atac_differential"]["request"]
            # Previously supplied BAMs retain their original received authority;
            # newly mentioned/derived outputs acquire no generic Store access.
            original = {item["file"]["artifact_ref"] for item in request["inputs"]}
            private = set(artifact_references(candidate)) - original
            if reference in private:
                context = self.returns.context(row["episode_id"])
                self.read_completed(episode_id=row["episode_id"], operation_key=candidate["intent"]["operation_key"],
                    scope=plain(context.scope))
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
            require(current.episode_id not in visited, "atac_differential_result_cyclic_authority")
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
                    if not {f["artifact_ref"] for f in (bundle["sheet"], *(row["file"] for row in bundle["tables"]))} <= baseline:
                        continue
                    for origin in origins[canonical(bundle)]:
                        closed(origin, ("episode_id", "operation_key"))
                        receipt = self.read_completed(**origin, scope=plain(context.scope))
                        require(any(same(bundle, saved) for saved in receipt["facts"][SAVED_SOURCE]))
                        population(receipt)
            current = parent
        return result


__all__ = ["AtacDifferentialResultReceipts", "AtacDifferentialResultAction", "AtacDifferentialResultReceipt", "VERSION"]
