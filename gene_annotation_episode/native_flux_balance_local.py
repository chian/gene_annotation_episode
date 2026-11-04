"""Reserve the selected FBA start; authenticate its original local controls.

The caller authenticates the received694 input receipt and its File before
calling this adapter. These local joins neither authorize arbitrary JSON nor
grant input references. Preparation never dispatches the reserved command.
"""
import hashlib
from pathlib import Path
import re

from . import native_lifecycle as native
from .execution_contracts import canonical, digest
from .flux_balance_contracts import validate_flux_balance_record
from .local_jobs import LocalJobPolicy
from .native_flux_balance_contracts import (
    ATTEMPT_DIRECTORY_NAME, OWNER_FILENAME, POLICY, RUN_PLAN_FILENAME,
    STARTED_FILENAME, bind_flux_balance_environment, flux_balance_driver_argv,
    flux_balance_output_files, path_value, require,
    validate_flux_balance_requested_job, validate_flux_balance_run_plan,
)
from .native_flux_balance_storage import (
    confined_file, directory, immutable_bytes, read_bytes, read_json,
)


INPUT_BINDING_FILENAME = "flux-balance-input-binding.json"
_FIXED = (RUN_PLAN_FILENAME, "invoke.json", INPUT_BINDING_FILENAME,
          "native.json", "stdout.log", "stderr.log")


def _root(assignment, owner):
    return directory(assignment["workspace"]) / ".episode-operations" / digest({
        "run": owner["run_id"], "episode": owner["episode_id"]}) / digest(owner["operation_key"])


def _allocation(assignment, policy):
    require(assignment.get("resource_kind") == "local" and canonical(policy) == canonical(POLICY)
            and type(assignment.get("resource_id")) is str and bool(assignment["resource_id"]),
            "fba_original_allocation_mismatch")
    constraints = assignment.get("constraints")
    require(type(constraints) is dict and not set(constraints) - {"allocation", *POLICY},
            "fba_original_allocation_mismatch")
    require("allocation" not in constraints or canonical(constraints["allocation"]) == canonical(policy),
            "fba_original_allocation_mismatch")
    require(all(k not in constraints or canonical(constraints[k]) == canonical(v) for k, v in policy.items()),
            "fba_original_allocation_mismatch")


def _input_control(receipt, file, *, owner):
    require(type(receipt) is dict and set(receipt) == {"version", "binding", "witness_records"}
            and receipt["version"] == "flux_balance_input_binding_receipt_v1"
            and type(receipt["witness_records"]) is list, "fba_input_control_invalid")
    binding = receipt["binding"]
    require(type(binding) is dict and binding.get("version") == "flux_balance_input_binding_v1"
            and all(binding.get(key) == owner[key] for key in ("run_id", "episode_id", "assignment_sha256")),
            "fba_input_control_owner_mismatch")
    file = validate_flux_balance_record("File", file)
    raw = canonical(receipt).encode("utf-8")
    require(file["format"] == "flux_balance_input_binding_receipt_v1"
            and file["sha256"] == hashlib.sha256(raw).hexdigest() and file["size_bytes"] == len(raw)
            and file["artifact_ref"] == "artifact_" + file["sha256"], "fba_input_control_identity_mismatch")
    return file, raw


def _environment(plan):
    return (plan["environment_binding"]["realized_environment"]
            if plan["version"] == "flux_balance_run_plan_v2" else plan["requested_job"]["environment"])


def _invoke(plan, file):
    request = plan["requested_job"]
    return {"cwd": str(Path(plan["identity"]["execution_id"]).parent), "argv": request["argv"],
            "environment": request["environment"], "native_flux_balance_plan": RUN_PLAN_FILENAME,
            "native_flux_balance_input_binding_file": file}


def _request(plan, paths):
    return {"command": flux_balance_driver_argv(plan), "cwd": str(Path(plan["identity"]["execution_id"]).parent),
            "file_bytes": POLICY["scratch_bytes"], "ready_path": paths["ready"], "release_path": paths["release"],
            "result_path": paths["result"], "stdin_path": None, "env": _environment(plan)}


def _same_or_write(path, raw):
    if path.exists():
        require(read_bytes(path) == raw, "fba_original_control_conflict")
        return
    try:
        immutable_bytes(path, raw)
    except FileExistsError:
        require(read_bytes(path) == raw, "fba_original_control_conflict")


def _selected_local_controls(compiled_selection, operation_key, *, run_id, episode_id,
                             root, policy, input_binding_receipt, input_binding_file):
    require(isinstance(policy, LocalJobPolicy) and type(operation_key) is str and bool(operation_key),
            "fba_selected_start_required")
    request = validate_flux_balance_requested_job(compiled_selection["requested_job"])
    _allocation(compiled_selection, policy.to_dict())
    root = Path(path_value(str(root), absolute=True))
    handle = native.NativeJobHandle(root / "native.json")
    owner = {"run_id": run_id, "episode_id": episode_id,
             "resource_id": compiled_selection["resource_id"], "execution_id": str(handle.path),
             "attempt_id": digest(operation_key), "operation_key": operation_key,
             "requested_job_sha256": digest(request), "assignment_sha256": digest(compiled_selection)}
    require(root == _root(compiled_selection, owner), "fba_original_attempt_mismatch")
    selection = compiled_selection.get("native_flux_balance_execution")
    environment = bind_flux_balance_environment(request, execution_id=str(handle.path),
        attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME), selection=selection)
    plan = {"version": "flux_balance_run_plan_v2" if selection is not None else "flux_balance_run_plan_v1",
            "identity": owner, "requested_job": request, "attempt_directory": str(root / ATTEMPT_DIRECTORY_NAME),
            "policy": policy.to_dict(), "outputs": flux_balance_output_files(request["native_flux_balance"])}
    if selection is not None:
        plan["environment_binding"] = environment
    plan = validate_flux_balance_run_plan(plan)
    file, input_raw = _input_control(input_binding_receipt, input_binding_file, owner=owner)
    return root, handle, plan, file, input_raw


def _reserve_selected_local(compiled_selection, controls, *, policy):
    root, handle, plan, file, input_raw = controls
    directory(root, create=True)
    for name in _FIXED:
        confined_file(root, name)
    if handle.path.exists():
        require(local_flux_balance_plan(compiled_selection, str(handle.path)) == plan,
                "fba_original_attempt_mismatch")
        require(read_bytes(root / INPUT_BINDING_FILENAME) == input_raw
                and read_json(root / "invoke.json") == _invoke(plan, file), "fba_original_control_conflict")
        return handle
    attempt = root / ATTEMPT_DIRECTORY_NAME
    require(not attempt.exists() and not attempt.is_symlink(), "fba_original_attempt_unsealed")
    for path in root.iterdir():
        confined_file(root, path.name)
        if path.name in (RUN_PLAN_FILENAME, "invoke.json", INPUT_BINDING_FILENAME):
            continue
        if path.name in ("stdout.log", "stderr.log"):
            require(len(read_bytes(path)) == 0, "fba_original_attempt_unsealed")
            continue
        require(re.fullmatch(r"\.local-job-[0-9a-f]{32}\.request", path.name) is not None,
                "fba_original_attempt_unsealed")
        token = path.name.removesuffix(".request")
        paths = {name: str(root / (token + "." + name)) for name in ("ready", "release", "result")}
        require(read_json(path) == _request(plan, paths), "fba_original_attempt_mismatch")
    _same_or_write(root / RUN_PLAN_FILENAME, canonical(plan).encode("utf-8") + b"\n")
    _same_or_write(root / "invoke.json", canonical(_invoke(plan, file)).encode("utf-8") + b"\n")
    _same_or_write(root / INPUT_BINDING_FILENAME, input_raw)
    native.prepare_job(flux_balance_driver_argv(plan), cwd=root, policy=policy,
                       handle_path=handle.path, env=_environment(plan))
    local_flux_balance_plan(compiled_selection, str(handle.path))
    return handle


def prepare_selected_local_flux_balance(compiled_selection, operation_key, *, run_id, episode_id,
                                        root, policy, input_binding_receipt, input_binding_file):
    """Reserve an authenticated caller's selected action, without dispatch.

    The caller owns its actual action lock and received-input authority. Selection
    consumes the existing resource_id/resource_kind/workspace/requested_job/
    constraints fields and optional native_flux_balance_execution; the complete
    supplied record fixes assignment_sha256. No practical role or state is made.
    """
    controls = _selected_local_controls(compiled_selection, operation_key,
        run_id=run_id, episode_id=episode_id, root=root, policy=policy,
        input_binding_receipt=input_binding_receipt, input_binding_file=input_binding_file)
    return _reserve_selected_local(compiled_selection, controls, policy=policy)


def prepare_local_flux_balance(state, operation_key, *, root, policy,
                               input_binding_receipt, input_binding_file):
    """Reserve only the actual pending practical.job.start, without dispatch."""
    controls = _selected_local_controls(state.assignment, operation_key,
        run_id=state.run_id, episode_id=state.episode_id, root=root, policy=policy,
        input_binding_receipt=input_binding_receipt, input_binding_file=input_binding_file)
    with state._locked():
        pending = state._load()[4]
        require(pending is not None and pending["operation_key"] == operation_key
                and pending["tool_name"] == "practical.job.start" and pending["run_id"] == state.run_id
                and pending["episode_id"] == state.episode_id
                and pending["assignment_sha256"] == digest(state.assignment), "fba_selected_pending_start_required")
        return _reserve_selected_local(state.assignment, controls, policy=policy)


def local_flux_balance_plan(assignment, execution_id):
    """Read original reservation controls; never start, poll, collect or rebind."""
    request = validate_flux_balance_requested_job(assignment["requested_job"])
    execution = path_value(execution_id, absolute=True)
    require(execution.name == "native.json", "fba_original_attempt_mismatch")
    root = directory(execution.parent)
    plan = validate_flux_balance_run_plan(read_json(confined_file(root, RUN_PLAN_FILENAME)))
    owner = plan["identity"]
    _allocation(assignment, plan["policy"])
    require(owner["assignment_sha256"] == digest(assignment) and owner["resource_id"] == assignment["resource_id"]
            and owner["execution_id"] == execution_id and plan["requested_job"] == request
            and root == _root(assignment, owner), "fba_original_attempt_mismatch")
    selection = assignment.get("native_flux_balance_execution")
    require((selection is None and plan["version"] == "flux_balance_run_plan_v1")
            or (selection is not None and plan["version"] == "flux_balance_run_plan_v2"
                and plan["environment_binding"]["selection"] == selection), "fba_environment_selection_invalid")
    invoke = read_json(confined_file(root, "invoke.json"))
    require(type(invoke) is dict, "fba_original_control_conflict")
    input_path = confined_file(root, INPUT_BINDING_FILENAME)
    file, raw = _input_control(read_json(input_path), invoke.get("native_flux_balance_input_binding_file"), owner=owner)
    require(read_bytes(input_path) == raw and invoke == _invoke(plan, file), "fba_original_control_conflict")
    require(read_bytes(root / RUN_PLAN_FILENAME) == canonical(plan).encode("utf-8") + b"\n"
            and read_bytes(root / "invoke.json") == canonical(invoke).encode("utf-8") + b"\n",
            "fba_original_control_conflict")
    original = read_json(confined_file(root, "native.json"))
    require(type(original) is dict and original.get("version") == native.VERSION
            and original.get("stage") in ("prepared", "submitting", "released")
            and original.get("command") == flux_balance_driver_argv(plan) and original.get("cwd") == str(root)
            and type(original.get("metadata")) is dict
            and canonical(original.get("metadata", {}).get("policy")) == canonical(plan["policy"]),
            "fba_original_attempt_mismatch")
    paths = original.get("paths")
    required = {"request", "ready", "release", "status", "result", "launcher"}
    require(type(paths) is dict and required <= set(paths) and not set(paths) - required - {"statistics", "native_events"}
            and all(type(p) is str and str(path_value(p, absolute=True)) == p and Path(p).parent == root
                    for p in paths.values()) and len(set(paths.values())) == len(paths), "fba_original_attempt_mismatch")
    require(not {str(root / name) for name in _FIXED}.intersection(paths.values()), "fba_original_attempt_mismatch")
    for path in paths.values():
        confined_file(root, Path(path).name)
    for role in ("stdout", "stderr"):
        require(original.get(role) == str(root / (role + ".log")), "fba_original_attempt_mismatch")
        confined_file(root, role + ".log")
    require(hashlib.sha256(read_bytes(paths["request"])).hexdigest() == original.get("request_sha256")
            and read_json(paths["request"]) == _request(plan, paths), "fba_original_attempt_mismatch")
    attempt = root / ATTEMPT_DIRECTORY_NAME
    if attempt.exists() or attempt.is_symlink():
        directory(attempt)
        owner_file = confined_file(attempt, OWNER_FILENAME)
        started = confined_file(attempt, STARTED_FILENAME)
        if owner_file.exists():
            require(read_json(owner_file) == plan, "fba_original_attempt_mismatch")
        if started.exists():
            value = read_json(started)
            keys = {"plan_sha256", "started_at"} | ({"environment_observation_sha256"}
                if plan["version"] == "flux_balance_run_plan_v2" else set())
            require(owner_file.exists() and type(value) is dict and set(value) == keys
                    and value["plan_sha256"] == digest(plan) and type(value["started_at"]) is str
                    and bool(value["started_at"]), "fba_original_attempt_mismatch")
            if plan["version"] == "flux_balance_run_plan_v2":
                require(type(value["environment_observation_sha256"]) is str
                        and re.fullmatch(r"[0-9a-f]{64}", value["environment_observation_sha256"]) is not None,
                        "fba_original_attempt_mismatch")
    return plan


__all__ = ["prepare_local_flux_balance", "prepare_selected_local_flux_balance", "local_flux_balance_plan"]
