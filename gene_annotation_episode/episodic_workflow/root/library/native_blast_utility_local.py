"""Reserve and qualify one selected local BLAST utility attempt.

The ordinary practical episode and native lifecycle own selection and dispatch.
Reading or preparing this reservation never starts, retries, or grades work.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

import gene_annotation_episode.native_lifecycle as native
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_contracts import (_path, validate_native_blast_utility_requested_job, validate_native_blast_utility_plan)
from gene_annotation_episode.episodic_workflow.root.library.native_blast_contracts import native_blast_digest
from gene_annotation_episode.episodic_workflow.root.library.native_infernal_driver import _confined_file, _read_json
from gene_annotation_episode.immutable_json_records import _immutable, _read

PLAN_NAME = "blast-utility-plan.json"
ATTEMPT_NAME = "blast-utility-attempt"
OWNER_NAME = ".native-blast-utility-owner.json"


def _directory(value):
    _path(value, absolute=True)
    path = Path(value)
    if path.resolve() != path:
        raise ValueError("native_blast_utility_original_directory_path_escape")
    return path


def _command(root):
    return [sys.executable, "-m", "gene_annotation_episode.episodic_workflow.root.library.native_blast_utility_driver", str(root / PLAN_NAME)]


def _environment(root):
    return {"PYTHONPATH": str(Path(__file__).resolve().parents[4]),
        "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(root), "TMP": str(root),
        "TEMP": str(root), "XDG_CACHE_HOME": str(root / "cache")}


def _owned_environment(root, original):
    """Join the retained owner record; do not authenticate a currently live job."""
    code = "native_blast_utility_original_driver_request_conflict"
    metadata = original.get("metadata")
    workflow = metadata.get("whole_workflow_budget") if type(metadata) is dict else None
    fields = {"version", "window_id", "unit", "slice", "environment_bounds", "run_directory",
        "driver_cgroup", "slice_cgroup", "boot_id", "supervisor_pid", "supervisor_start_ticks",
        "command", "disk_bandwidth_enforced", "memory_peak_scope"}
    if (type(workflow) is not dict or set(workflow) != fields
            or workflow["version"] != "whole_workflow_budget_v2"
            or type(workflow["window_id"]) is not str
            or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", workflow["window_id"]) is None):
        raise ValueError(code)
    key = workflow["window_id"].replace("-", "")
    unit, slice_ = "gene-episode-workflow-" + key + ".service", "geneepisodewindow" + key + ".slice"
    bounds = workflow["environment_bounds"]
    if (workflow["unit"] != unit or workflow["slice"] != slice_
            or type(bounds) is not dict or set(bounds) != {"cpu_percent", "memory_bytes", "swap_bytes"}
            or any(type(v) is not int for v in bounds.values())
            or bounds["cpu_percent"] <= 0 or bounds["memory_bytes"] <= 0 or bounds["swap_bytes"] < 0
            or type(workflow["run_directory"]) is not str
            or type(workflow["slice_cgroup"]) is not str
            or not workflow["slice_cgroup"].startswith("/")
            or ".." in Path(workflow["slice_cgroup"]).parts
            or Path(workflow["slice_cgroup"]).name != slice_
            or workflow["driver_cgroup"] != workflow["slice_cgroup"] + "/" + unit
            or type(workflow["boot_id"]) is not str or not workflow["boot_id"]
            or type(workflow["supervisor_pid"]) is not int or workflow["supervisor_pid"] <= 0
            or type(workflow["supervisor_start_ticks"]) is not str
            or not workflow["supervisor_start_ticks"].isdigit()
            or type(workflow["command"]) is not list or not workflow["command"]
            or any(type(item) is not str for item in workflow["command"])
            or workflow["disk_bandwidth_enforced"] is not False
            or type(workflow["memory_peak_scope"]) is not str
            or workflow["memory_peak_scope"] not in {"this_workflow", "slice_lifetime_upper_bound"}):
        raise ValueError(code)
    directory = _directory(workflow["run_directory"])
    if not root.is_relative_to(directory):
        raise ValueError(code)
    recorded = _read_json(_confined_file(directory, "workflow-budget.json"))
    if native_blast_digest(recorded) != native_blast_digest(workflow):
        raise ValueError(code)
    return {**_environment(root),
        "GENE_EPISODE_WORKFLOW_BUDGET_FILE": str(directory / "workflow-budget.json"),
        "GENE_EPISODE_WORKFLOW_SLOT": workflow["window_id"]}


def _invoke(request, attempt):
    return {"cwd": str(attempt), "argv": request["argv"], "environment": request["environment"],
        "native_blast_utility_plan": PLAN_NAME}


def _root(assignment, owner):
    return (_directory(assignment["workspace"]) / ".episode-operations" /
        native_blast_digest({"run": owner["run_id"], "episode": owner["episode_id"]}) /
        native_blast_digest(owner["operation_key"]))


def _resource(assignment):
    if assignment.get("resource_kind") != "local":
        raise ValueError("native_blast_utility_local_resource_required")
    resource = assignment.get("resource_id")
    if type(resource) is not str or not resource or "\0" in resource:
        raise ValueError("native_blast_utility_resource_identity_required")
    return resource


def _policy(assignment, policy):
    constraints = assignment.get("constraints", {})
    if ("allocation" in constraints and constraints["allocation"] != policy
            or any(key in constraints and constraints[key] != value for key, value in policy.items())):
        raise ValueError("native_blast_utility_original_allocation_conflict")


def prepare_local_blast_utility(state, operation_key, *, root, policy):
    """Persist the exact reservation without starting its producer."""
    if not isinstance(policy, LocalJobPolicy):
        raise TypeError("local_job_policy_required")
    if policy.memory_bytes > 5 * 1024 ** 3:
        raise ValueError("native_blast_utility_current_allocation_conflict")
    request = validate_native_blast_utility_requested_job(state.assignment["requested_job"])
    root = _directory(str(root))
    handle = native.NativeJobHandle(root / "native.json")
    attempt = root / ATTEMPT_NAME
    plan = validate_native_blast_utility_plan({"version": "native_blast_utility_run_plan_v1", "identity": {
        "run_id": state.run_id, "episode_id": state.episode_id,
        "resource_id": _resource(state.assignment), "execution_id": str(handle.path),
        "attempt_id": native_blast_digest(operation_key), "operation_key": operation_key,
        "requested_job_sha256": native_blast_digest(request)}, "requested_job": request,
        "attempt_directory": str(attempt), "policy": policy.to_dict()})
    _policy(state.assignment, plan["policy"])
    if root != _root(state.assignment, plan["identity"]):
        raise ValueError("native_blast_utility_original_attempt_directory_conflict")
    for name in (PLAN_NAME, "invoke.json", "native.json"):
        _confined_file(root, name)
    reserved = (root / PLAN_NAME).exists() or (root / "invoke.json").exists()
    if not handle.path.exists() and (reserved or attempt.exists()):
        raise ValueError("native_blast_utility_missing_reservation_execution_uncertain")
    _immutable(root / PLAN_NAME, plan)
    _immutable(root / "invoke.json", _invoke(request, attempt))
    if not handle.path.exists():
        native.prepare_job(_command(root), cwd=root, policy=policy,
            handle_path=handle.path, env=_environment(root))
    local_blast_utility_plan(state.assignment, str(handle.path))
    return handle


def local_blast_utility_plan(assignment, execution_id):
    """Qualify all original command, owner, environment and allocation ports."""
    request = validate_native_blast_utility_requested_job(assignment["requested_job"])
    resource = _resource(assignment)
    _path(execution_id, absolute=True)
    handle = Path(execution_id)
    if handle.name != "native.json":
        raise ValueError("native_blast_utility_original_attempt_conflict")
    root = _directory(str(handle.parent))
    for name in ("native.json", PLAN_NAME, "invoke.json"):
        _confined_file(root, name)
    plan = validate_native_blast_utility_plan(_read(root / PLAN_NAME))
    owner, original = plan["identity"], native.NativeJobHandle(handle).read()
    _policy(assignment, plan["policy"])
    if (plan["requested_job"] != request or owner["execution_id"] != str(handle)
            or owner["resource_id"] != resource or root != _root(assignment, owner)
            or owner["attempt_id"] != native_blast_digest(owner["operation_key"])
            or original.get("command") != _command(root) or original.get("cwd") != str(root)
            or original.get("metadata", {}).get("policy") != plan["policy"]
            or plan["attempt_directory"] != str(root / ATTEMPT_NAME)
            or _read(root / "invoke.json") != _invoke(request, Path(plan["attempt_directory"]))):
        raise ValueError("native_blast_utility_original_attempt_conflict")
    paths = original.get("paths", {})
    required = {"request", "ready", "release", "status", "result", "launcher"}
    if type(paths) is not dict or not required <= paths.keys():
        raise ValueError("native_blast_utility_original_driver_request_conflict")
    for value in paths.values():
        if type(value) is not str or not Path(value).is_relative_to(root):
            raise ValueError("native_blast_utility_original_driver_path_conflict")
        _confined_file(root, str(Path(value).relative_to(root)))
    if len(set(paths.values())) != len(paths):
        raise ValueError("native_blast_utility_original_driver_path_conflict")
    for role in ("stdout", "stderr"):
        if original.get(role) != str(root / (role + ".log")):
            raise ValueError("native_blast_utility_original_driver_path_conflict")
        _confined_file(root, role + ".log")
    path = Path(paths["request"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != original.get("request_sha256"):
        raise ValueError("native_blast_utility_original_driver_request_digest_conflict")
    expected = {"command": original["command"], "cwd": str(root),
        "file_bytes": plan["policy"]["scratch_bytes"], "ready_path": paths["ready"],
        "release_path": paths["release"], "result_path": paths["result"],
        "stdin_path": None, "env": _owned_environment(root, original)}
    if _read_json(path) != expected:
        raise ValueError("native_blast_utility_original_driver_request_conflict")
    # Keep the reservation qualification before this last, separate owner check.
    # Acquisition can therefore retain an invalid native owner as a typed
    # custody failure without accepting a different reservation or command.
    try:
        owner_path = _confined_file(Path(plan["attempt_directory"]), OWNER_NAME)
        if owner_path.exists() and _read_json(owner_path) != plan:
            raise ValueError("owner_conflict")
    except (OSError, ValueError) as error:
        raise ValueError("native_blast_utility_original_attempt_owner_conflict") from error
    return plan


__all__ = ["prepare_local_blast_utility", "local_blast_utility_plan"]
