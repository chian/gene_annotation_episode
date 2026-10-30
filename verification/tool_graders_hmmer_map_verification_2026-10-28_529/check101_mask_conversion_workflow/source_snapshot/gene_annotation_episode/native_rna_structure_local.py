"""Reserve and authenticate RNA work through the existing local lifecycle."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from . import native_lifecycle as native
from .execution_contracts import digest
from .native_rna_structure_contracts import (ATTEMPT_DIRECTORY_NAME, OWNER_FILENAME, POLICY,
    RUN_PLAN_FILENAME, validate_rna_structure_requested_job, validate_rna_structure_run_plan)
from .native_rna_structure_driver import _directory, confined_file, _strict_json
from .practical_execution_state import _immutable, _read


def _command(root):
    return [sys.executable, "-B", "-m", "gene_annotation_episode.native_rna_structure_driver", str(root / RUN_PLAN_FILENAME)]


def _environment(root):
    return {"PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(root), "TMP": str(root), "TEMP": str(root), "XDG_CACHE_HOME": str(root / "cache"),
        "PIP_CACHE_DIR": str(root / "cache" / "pip")}


def _expected_root(assignment, identity):
    return _directory(assignment["workspace"]) / ".episode-operations" / digest({
        "run": identity["run_id"], "episode": identity["episode_id"]}) / digest(identity["operation_key"])


def _invoke(request, attempt):
    return {"cwd": str(attempt), "argv": request["argv"], "environment": request["environment"],
        "native_rna_structure_plan": RUN_PLAN_FILENAME}


def prepare_local_rna_structure(state, operation_key: str, *, root: Path, policy):
    """Reserve the selected command and immutable plan. Never start native work."""
    request = validate_rna_structure_requested_job(state.assignment["requested_job"])
    root = _directory(root)
    if policy.to_dict() != POLICY:
        raise ValueError("rna_original_attempt_mismatch")
    if state.assignment.get("resource_kind") != "local":
        raise ValueError("rna_original_attempt_mismatch")
    handle = native.NativeJobHandle(root / "native.json")
    plan = validate_rna_structure_run_plan({"version": "native_rna_structure_run_plan_v1", "identity": {
        "run_id": state.run_id, "episode_id": state.episode_id, "resource_id": state.assignment.get("resource_id"),
        "execution_id": str(handle.path), "attempt_id": digest(operation_key), "operation_key": operation_key,
        "requested_job_sha256": digest(request)}, "requested_job": request,
        "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME), "policy": policy.to_dict()})
    if root != _expected_root(state.assignment, plan["identity"]):
        raise ValueError("rna_original_attempt_mismatch")
    root.mkdir(parents=True, exist_ok=True)
    for name in (RUN_PLAN_FILENAME, "invoke.json", "native.json", "stdout.log", "stderr.log"):
        confined_file(root, name)
    _immutable(root / RUN_PLAN_FILENAME, plan)
    _immutable(root / "invoke.json", _invoke(request, Path(plan["attempt_directory"])))
    if not handle.path.exists():
        native.prepare_job(_command(root), cwd=root, policy=policy, handle_path=handle.path,
            env=_environment(root))
    local_rna_structure_plan(state.assignment, str(handle.path))
    return handle


def local_rna_structure_plan(assignment: dict, execution_id: str) -> dict:
    """Read only the exact saved plan/reservation, checking its original custody."""
    request = validate_rna_structure_requested_job(assignment["requested_job"])
    if type(execution_id) is not str or not Path(execution_id).is_absolute() or Path(execution_id).name != "native.json":
        raise ValueError("rna_original_attempt_mismatch")
    handle_path = Path(execution_id)
    root = _directory(handle_path.parent)
    for name in (RUN_PLAN_FILENAME, "invoke.json", "native.json", "stdout.log", "stderr.log"):
        confined_file(root, name)
    plan = validate_rna_structure_run_plan(_read(root / RUN_PLAN_FILENAME))
    owner = plan["identity"]
    original = native.NativeJobHandle(handle_path).read()
    if (assignment.get("resource_kind") != "local" or assignment.get("resource_id") != owner["resource_id"]
            or plan["requested_job"] != request or owner["execution_id"] != execution_id
            or root != _expected_root(assignment, owner) or original.get("command") != _command(root)
            or original.get("cwd") != str(root) or original.get("metadata", {}).get("policy") != plan["policy"]
            or _read(root / "invoke.json") != _invoke(request, Path(plan["attempt_directory"]))):
        raise ValueError("rna_original_attempt_mismatch")
    paths = original.get("paths")
    if type(paths) is not dict or not {"request", "ready", "release", "status", "result", "launcher"} <= paths.keys():
        raise ValueError("rna_original_attempt_mismatch")
    for path in paths.values():
        if type(path) is not str or not Path(path).is_relative_to(root):
            raise ValueError("rna_output_path_conflict")
        confined_file(root, str(Path(path).relative_to(root)))
    for name in ("stdout", "stderr"):
        if original.get(name) != str(root / (name + ".log")):
            raise ValueError("rna_original_attempt_mismatch")
    raw = Path(paths["request"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != original.get("request_sha256"):
        raise ValueError("rna_original_attempt_mismatch")
    expected = {"command": _command(root), "cwd": str(root), "file_bytes": POLICY["scratch_bytes"],
        "ready_path": paths["ready"], "release_path": paths["release"], "result_path": paths["result"],
        "stdin_path": None, "env": _environment(root)}
    if _strict_json(paths["request"]) != expected:
        raise ValueError("rna_original_attempt_mismatch")
    attempt_owner = confined_file(Path(plan["attempt_directory"]), OWNER_FILENAME)
    if attempt_owner.exists() and _read(attempt_owner) != plan:
        raise ValueError("rna_original_attempt_mismatch")
    return plan
