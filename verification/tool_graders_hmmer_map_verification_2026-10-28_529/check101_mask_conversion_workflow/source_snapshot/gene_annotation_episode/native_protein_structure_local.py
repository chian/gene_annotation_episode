"""Reserve/read the exact selected local job through the shared native lifecycle."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import native_lifecycle as native
from .execution_contracts import digest
from .local_jobs import LocalJobPolicy
from .protein_structure_contracts import same
from .native_protein_structure_contracts import (
    ATTEMPT_DIRECTORY_NAME, OWNER_FILENAME, POLICY, RUN_PLAN_FILENAME,
    _require, driver_argv, validate_protein_structure_requested_job,
    validate_protein_structure_run_plan, realized_environment,
)
from .native_protein_structure_driver import _directory, confined_file, _strict_json, _immutable


def _root(assignment, identity):
    return _directory(assignment["workspace"]) / ".episode-operations" / digest({
        "run": identity["run_id"], "episode": identity["episode_id"]}) / digest(identity["operation_key"])


def _environment(plan):
    job = plan["requested_job"]["native_protein_structure"]
    environment = realized_environment(job, plan["attempt_directory"])
    # This is the currently bound implementation path, not a replacement
    # interpreter. The original explicit PYTHONPATH, if selected, is retained.
    environment.setdefault("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
    return environment


def _invoke(request, attempt):
    return {"cwd": str(attempt), "argv": request["argv"], "environment": request["environment"],
        "native_protein_structure_plan": RUN_PLAN_FILENAME}


def _allocation(assignment, policy):
    _require(assignment.get("resource_kind") == "local" and same(policy, POLICY), "original_commission_mismatch")
    constraints = assignment.get("constraints", {})
    _require("allocation" not in constraints or same(constraints["allocation"], policy), "original_commission_mismatch")
    _require(all(k not in constraints or same(constraints[k], v) for k, v in policy.items()), "original_commission_mismatch")


def prepare_local_protein_structure(state, operation_key: str, *, root: Path,
                                    policy: LocalJobPolicy) -> native.NativeJobHandle:
    """Reserve only. The owning episode must select the existing start action."""
    _require(isinstance(policy, LocalJobPolicy))
    request = validate_protein_structure_requested_job(state.assignment["requested_job"])
    root = _directory(root)
    _allocation(state.assignment, policy.to_dict())
    handle = native.NativeJobHandle(root / "native.json")
    plan = validate_protein_structure_run_plan({"version": "native_protein_structure_run_plan_v1", "identity": {
        "run_id": state.run_id, "episode_id": state.episode_id, "resource_id": state.assignment.get("resource_id"),
        "execution_id": str(handle.path), "attempt_id": digest(operation_key), "operation_key": operation_key,
        "requested_job_sha256": digest(request)}, "requested_job": request,
        "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME), "policy": policy.to_dict()})
    _require(root == _root(state.assignment, plan["identity"]), "original_commission_mismatch")
    root.mkdir(parents=True, exist_ok=True)
    for name in (RUN_PLAN_FILENAME, "invoke.json", "native.json", "stdout.log", "stderr.log"):
        confined_file(root, name)
    reserved = (root / RUN_PLAN_FILENAME).exists() or (root / "invoke.json").exists()
    _require(handle.path.exists() or not (reserved or Path(plan["attempt_directory"]).exists()), "native_process_failed")
    _immutable(root / RUN_PLAN_FILENAME, plan)
    _immutable(root / "invoke.json", _invoke(request, Path(plan["attempt_directory"])))
    if not handle.path.exists():
        native.prepare_job(driver_argv(plan), cwd=root, policy=policy, handle_path=handle.path, env=_environment(plan))
    local_protein_structure_plan(state.assignment, str(handle.path))
    return handle


def local_protein_structure_plan(assignment: dict, execution_id: str) -> dict:
    """Read/qualify the original reservation; never launch or recover by retry."""
    request = validate_protein_structure_requested_job(assignment["requested_job"])
    _require(type(execution_id) is str and Path(execution_id).is_absolute() and Path(execution_id).name == "native.json", "original_commission_mismatch")
    root = _directory(Path(execution_id).parent)
    for name in (RUN_PLAN_FILENAME, "invoke.json", "native.json", "stdout.log", "stderr.log"):
        confined_file(root, name)
    plan = validate_protein_structure_run_plan(_strict_json(root / RUN_PLAN_FILENAME))
    owner = plan["identity"]
    original = native.NativeJobHandle(Path(execution_id)).read()
    _allocation(assignment, plan["policy"])
    _require(same(plan["requested_job"], request) and owner["execution_id"] == execution_id and
        owner["resource_id"] == assignment.get("resource_id") and root == _root(assignment, owner) and
        original.get("command") == driver_argv(plan) and original.get("cwd") == str(root) and
        same(original.get("metadata", {}).get("policy"), plan["policy"]) and
        same(_strict_json(root / "invoke.json"), _invoke(request, Path(plan["attempt_directory"]))), "original_commission_mismatch")
    paths = original.get("paths")
    _require(type(paths) is dict and {"request", "ready", "release", "status", "result", "launcher"} <= paths.keys(), "original_commission_mismatch")
    _require(len(set(paths.values())) == len(paths), "invalid_output_path")
    for path in paths.values():
        _require(type(path) is str and Path(path).is_relative_to(root), "invalid_output_path")
        confined_file(root, str(Path(path).relative_to(root)))
    for role in ("stdout", "stderr"):
        _require(original.get(role) == str(root / (role + ".log")), "original_commission_mismatch")
    raw = Path(paths["request"]).read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == original.get("request_sha256"), "input_digest_mismatch")
    expected = {"command": driver_argv(plan), "cwd": str(root), "file_bytes": POLICY["scratch_bytes"],
        "ready_path": paths["ready"], "release_path": paths["release"], "result_path": paths["result"],
        "stdin_path": None, "env": _environment(plan)}
    _require(same(_strict_json(paths["request"]), expected), "original_commission_mismatch")
    owner_file = confined_file(Path(plan["attempt_directory"]), OWNER_FILENAME)
    if owner_file.exists():
        _require(same(_strict_json(owner_file), plan), "original_commission_mismatch")
    return plan
