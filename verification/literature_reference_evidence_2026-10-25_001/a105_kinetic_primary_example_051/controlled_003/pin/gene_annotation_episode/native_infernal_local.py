"""Bind a selected Infernal producer to the existing local native lifecycle.

Preparation reserves the original command and never starts work. The practical
resource episode selects start/recovery/status through the shared lifecycle.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from . import native_lifecycle as native
from .native_infernal_contracts import native_infernal_digest, validate_native_infernal_requested_job
from .native_infernal_driver import _absolute_directory, _confined_file, _read_json, _validate_plan
from .practical_execution_state import _immutable, _read


def _command(root):
    return [sys.executable, "-m", "gene_annotation_episode.native_infernal_driver",
        str(root / "infernal-plan.json")]


def _driver_environment(root):
    return {"PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(root),
        "XDG_CACHE_HOME": str(root / "cache")}


def _invoke(request, attempt):
    return {"cwd": str(attempt), "argv": request["argv"], "environment": request["environment"],
        "native_infernal_plan": "infernal-plan.json"}


def _expected_root(assignment, identity):
    workspace = _absolute_directory(assignment["workspace"])
    return workspace / ".episode-operations" / native_infernal_digest({
        "run": identity["run_id"], "episode": identity["episode_id"]}) / native_infernal_digest(identity["operation_key"])


def prepare_local_infernal(state, operation_key, *, root, policy):
    """Create or qualify one immutable local reservation, without dispatch."""
    request = validate_native_infernal_requested_job(state.assignment["requested_job"])
    root = _absolute_directory(str(root))
    handle = native.NativeJobHandle(root / "native.json")
    attempt = root / "infernal-attempt"
    resource_id = state.assignment.get("resource_id")
    if type(resource_id) is not str or not resource_id:
        raise ValueError("native_infernal_resource_identity_required")
    if state.assignment.get("resource_kind") != "local":
        raise ValueError("native_infernal_local_resource_required")
    plan = _validate_plan({"version": "native_infernal_run_plan_v1", "identity": {
        "run_id": state.run_id, "episode_id": state.episode_id, "resource_id": resource_id,
        "execution_id": str(handle.path), "attempt_id": native_infernal_digest(operation_key),
        "operation_key": operation_key, "requested_job_sha256": native_infernal_digest(request)},
        "requested_job": request, "attempt_directory": str(attempt), "policy": policy.to_dict()})
    if root != _expected_root(state.assignment, plan["identity"]):
        raise ValueError("native_infernal_original_attempt_directory_conflict")
    for name in ("infernal-plan.json", "invoke.json", "native.json"):
        _confined_file(root, name)
    _immutable(root / "infernal-plan.json", plan)
    _immutable(root / "invoke.json", _invoke(request, attempt))
    if not handle.path.exists():
        native.prepare_job(_command(root), cwd=root, policy=policy,
            handle_path=handle.path, env=_driver_environment(root))
    # Repeated construction checks the actual original reservation. It cannot
    # silently reuse a handle whose command, environment or allocation changed.
    local_infernal_plan(state.assignment, str(handle.path))
    return handle


def local_infernal_plan(assignment, execution_id):
    """Qualify the original selected plan, identity and native reservation."""
    request = validate_native_infernal_requested_job(assignment["requested_job"])
    if (type(execution_id) is not str or not Path(execution_id).is_absolute()
            or Path(execution_id).name != "native.json"):
        raise ValueError("native_infernal_original_attempt_conflict")
    handle = Path(execution_id)
    root = _absolute_directory(str(handle.parent))
    for name in ("native.json", "infernal-plan.json", "invoke.json"):
        _confined_file(root, name)
    plan = _validate_plan(_read(root / "infernal-plan.json"))
    owner = plan["identity"]
    original = native.NativeJobHandle(handle).read()
    if (plan["requested_job"] != request or assignment.get("resource_kind") != "local"
            or owner["execution_id"] != str(handle)
            or owner["resource_id"] != assignment.get("resource_id")
            or root != _expected_root(assignment, owner)
            or original.get("command") != _command(root)
            or original.get("cwd") != str(root)
            or original.get("metadata", {}).get("policy") != plan["policy"]
            or plan["attempt_directory"] != str(root / "infernal-attempt")
            or _read(root / "invoke.json") != _invoke(request, Path(plan["attempt_directory"]))):
        raise ValueError("native_infernal_original_attempt_conflict")
    paths = original.get("paths", {})
    if type(paths) is not dict or "request" not in paths:
        raise ValueError("native_infernal_original_driver_request_conflict")
    for value in paths.values():
        if type(value) is not str or not Path(value).is_relative_to(root):
            raise ValueError("native_infernal_original_driver_path_conflict")
        _confined_file(root, str(Path(value).relative_to(root)))
    for role in ("stdout", "stderr"):
        if original.get(role) != str(root / (role + ".log")):
            raise ValueError("native_infernal_original_driver_path_conflict")
        _confined_file(root, role + ".log")
    native_request_path = Path(paths["request"])
    raw = native_request_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != original.get("request_sha256"):
        raise ValueError("native_infernal_original_driver_request_digest_conflict")
    native_request = _read_json(native_request_path)
    expected = {"command": _command(root), "cwd": str(root), "file_bytes": plan["policy"]["scratch_bytes"],
        "ready_path": paths.get("ready"), "release_path": paths.get("release"),
        "result_path": paths.get("result"), "stdin_path": None, "env": _driver_environment(root)}
    if native_request != expected:
        raise ValueError("native_infernal_original_driver_request_conflict")
    attempt = Path(plan["attempt_directory"])
    owner_path = _confined_file(attempt, ".native-infernal-owner.json")
    if owner_path.exists() and _read_json(owner_path, sealed=True) != plan:
        raise ValueError("native_infernal_original_attempt_owner_conflict")
    return plan


__all__ = ["prepare_local_infernal", "local_infernal_plan"]
