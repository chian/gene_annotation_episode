"""Reserve and authenticate one selected overlap action without dispatching it."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import native_lifecycle as native
from .execution_contracts import digest
from .local_jobs import LocalJobPolicy
from .native_genomic_overlap_contracts import (
    ATTEMPT_DIRECTORY_NAME, OWNER_FILENAME, POLICY, RUN_PLAN_FILENAME,
    STARTED_FILENAME, genomic_overlap_driver_argv, genomic_overlap_environment,
    validate_genomic_overlap_requested_job, validate_genomic_overlap_run_plan,
)
from .native_genomic_overlap_driver import (
    _directory, _immutable, _read_control, _regular, _require, _strict_json,
    confined_file,
)


def _root(assignment, identity):
    return _directory(assignment["workspace"]) / ".episode-operations" / digest({
        "run": identity["run_id"], "episode": identity["episode_id"]}) / digest(identity["operation_key"])


def _allocation(assignment, policy):
    _require(assignment.get("resource_kind") == "local" and policy == POLICY and
        type(assignment.get("resource_id")) is str and bool(assignment["resource_id"]),
        "original_attempt_mismatch")
    constraints = assignment.get("constraints")
    _require(type(constraints) is dict and not set(constraints) - {
        "allocation", "memory_bytes", "scratch_bytes", "wall_seconds"}, "original_attempt_mismatch")
    _require("allocation" not in constraints or digest(constraints["allocation"]) == digest(policy),
        "original_attempt_mismatch")
    _require(all(key not in constraints or digest(constraints[key]) == digest(value)
        for key, value in policy.items()), "original_attempt_mismatch")


def _environment(plan):
    return genomic_overlap_environment(plan["requested_job"]["native_genomic_overlap"],
        attempt_directory=plan["attempt_directory"])


def _invoke(plan):
    request = plan["requested_job"]
    return {"cwd": str(Path(plan["identity"]["execution_id"]).parent),
        "argv": request["argv"], "environment": request["environment"],
        "native_genomic_overlap_plan": RUN_PLAN_FILENAME}


def _request(plan, paths):
    return {"command": genomic_overlap_driver_argv(plan),
        "cwd": str(Path(plan["identity"]["execution_id"]).parent),
        "file_bytes": POLICY["scratch_bytes"], "ready_path": paths["ready"],
        "release_path": paths["release"], "result_path": paths["result"],
        "stdin_path": None, "env": _environment(plan)}


def _no_dispatch(root, plan):
    """Qualify only the narrow prepare_job-before-handle-publication crash."""
    _require(not Path(plan["attempt_directory"]).exists(), "unsealed_native_attempt")
    for path in root.iterdir():
        confined_file(root, path.name)
        if path.name in {RUN_PLAN_FILENAME, "invoke.json"}:
            continue
        if path.name in {"stdout.log", "stderr.log"}:
            _require(path.stat().st_size == 0, "unsealed_native_attempt")
            continue
        # A request alone cannot dispatch: prepare_job publishes the handle
        # last and start_prepared requires that handle. Retain orphan requests.
        _require(path.name.startswith(".local-job-") and path.name.endswith(".request"),
            "unsealed_native_attempt")
        request = _strict_json(path)
        token = path.name.removesuffix(".request")
        paths = {key: str(root / (token + "." + key)) for key in
            ("ready", "release", "result")}
        _require(request == _request(plan, paths), "original_attempt_mismatch")


def prepare_local_genomic_overlap(state, operation_key: str, *, root: Path,
    policy: LocalJobPolicy) -> native.NativeJobHandle:
    """Freeze the exact pending start intent. Only the existing host dispatches."""
    _require(isinstance(policy, LocalJobPolicy), "original_attempt_mismatch")
    _require(type(operation_key) is str and bool(operation_key), "original_attempt_mismatch")
    request = validate_genomic_overlap_requested_job(state.assignment["requested_job"])
    _allocation(state.assignment, policy.to_dict())
    root = _directory(root)
    handle = native.NativeJobHandle(root / "native.json")
    plan = validate_genomic_overlap_run_plan({"version": "native_genomic_overlap_run_plan_v1",
        "identity": {"run_id": state.run_id, "episode_id": state.episode_id,
            "resource_id": state.assignment["resource_id"], "execution_id": str(handle.path),
            "attempt_id": digest(operation_key), "operation_key": operation_key,
            "requested_job_sha256": digest(request), "assignment_sha256": digest(state.assignment)},
        "requested_job": request, "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME),
        "policy": policy.to_dict()})
    _require(root == _root(state.assignment, plan["identity"]), "original_attempt_mismatch")
    # Reading the actual durable state, under its existing lock, prevents a
    # public helper call or a completed/different action from reserving work.
    with state._locked():
        pending = state._load()[4]
        _require(pending is not None and pending["operation_key"] == operation_key and
            pending["tool_name"] == "practical.job.start" and
            pending["run_id"] == state.run_id and pending["episode_id"] == state.episode_id and
            pending["assignment_sha256"] == plan["identity"]["assignment_sha256"],
            "selected_pending_start_required")
        root.mkdir(parents=True, exist_ok=True)
        _directory(root)
        for name in (RUN_PLAN_FILENAME, "invoke.json", "native.json", "stdout.log", "stderr.log"):
            confined_file(root, name)
        if handle.path.exists():
            original = local_genomic_overlap_plan(state.assignment, str(handle.path))
            _require(original == plan, "original_attempt_mismatch")
            return handle
        for name, expected in ((RUN_PLAN_FILENAME, plan), ("invoke.json", _invoke(plan))):
            path = confined_file(root, name)
            if path.exists():
                _require(_read_control(path) == expected, "original_attempt_mismatch")
        _no_dispatch(root, plan)
        _immutable(root / RUN_PLAN_FILENAME, plan)
        _immutable(root / "invoke.json", _invoke(plan))
        native.prepare_job(genomic_overlap_driver_argv(plan), cwd=root, policy=policy,
            handle_path=handle.path, env=_environment(plan))
        local_genomic_overlap_plan(state.assignment, str(handle.path))
        return handle


def local_genomic_overlap_plan(assignment: dict, execution_id: str) -> dict:
    """Read and qualify the original reservation; never start, poll or collect."""
    request = validate_genomic_overlap_requested_job(assignment["requested_job"])
    _require(type(execution_id) is str and Path(execution_id).is_absolute() and
        str(Path(execution_id)) == execution_id and Path(execution_id).name == "native.json",
        "original_attempt_mismatch")
    root = _directory(Path(execution_id).parent)
    for name in (RUN_PLAN_FILENAME, "invoke.json", "native.json", "stdout.log", "stderr.log"):
        confined_file(root, name)
    plan = validate_genomic_overlap_run_plan(_read_control(root / RUN_PLAN_FILENAME))
    identity = plan["identity"]
    _allocation(assignment, plan["policy"])
    _require(identity["assignment_sha256"] == digest(assignment) and
        identity["resource_id"] == assignment["resource_id"] and
        plan["requested_job"] == request and identity["requested_job_sha256"] == digest(request) and
        identity["execution_id"] == execution_id and
        identity["attempt_id"] == digest(identity["operation_key"]) and
        root == _root(assignment, identity), "original_attempt_mismatch")
    original = _strict_json(root / "native.json")
    _require(type(original) is dict and type(original.get("metadata")) is dict,
        "original_attempt_mismatch")
    _require(original.get("version") == native.VERSION and
        original.get("stage") in {"prepared", "submitting", "released"} and
        original.get("command") == genomic_overlap_driver_argv(plan) and original.get("cwd") == str(root) and
        digest(original["metadata"].get("policy")) == digest(plan["policy"]) and
        _read_control(root / "invoke.json") == _invoke(plan), "original_attempt_mismatch")
    paths = original.get("paths")
    required = {"request", "ready", "release", "status", "result", "launcher"}
    _require(type(paths) is dict and required <= paths.keys() and
        not paths.keys() - required - {"statistics", "native_events"}, "original_attempt_mismatch")
    _require(all(type(path) is str and Path(path).parent == root and str(Path(path)) == path
        for path in paths.values()) and len(set(paths.values())) == len(paths), "original_attempt_mismatch")
    fixed = {str(root / name) for name in ("native.json", "invoke.json", RUN_PLAN_FILENAME,
        "stdout.log", "stderr.log")}
    _require(not fixed.intersection(paths.values()), "original_attempt_mismatch")
    for path in paths.values():
        confined_file(root, Path(path).name)
    for role in ("statistics", "native_events"):
        _require((role in paths) == (role in original), "original_attempt_mismatch")
    for role in ("stdout", "stderr"):
        _require(original.get(role) == str(root / (role + ".log")), "original_attempt_mismatch")
    with _regular(paths["request"]) as stream:
        raw = stream.read()
    _require(hashlib.sha256(raw).hexdigest() == original.get("request_sha256") and
        digest(_strict_json(paths["request"])) == digest(_request(plan, paths)), "original_attempt_mismatch")
    attempt = _directory(plan["attempt_directory"])
    owner = confined_file(attempt, OWNER_FILENAME)
    started = confined_file(attempt, STARTED_FILENAME)
    if owner.exists():
        _require(_read_control(owner) == plan, "original_attempt_mismatch")
    if started.exists():
        value = _read_control(started)
        _require(owner.exists() and type(value) is dict and set(value) == {"plan", "started_at"} and
            value["plan"] == plan, "original_attempt_mismatch")
    return plan


__all__ = ["prepare_local_genomic_overlap", "local_genomic_overlap_plan"]
