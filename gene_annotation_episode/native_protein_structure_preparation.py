"""Execute one selected retained-result worker and preserve its byte custody.

The caller owns input authority, publication and episode observations. This
adapter owns one existing native reservation. A diagnostic artifact is never a
grant to use scientific values; only the qualified worker manifest names usable
outputs, subject to the worker's unchanged scientific state and issues.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import fcntl
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import sys
from typing import Literal, TypedDict, get_args

from . import native_lifecycle
from .acquisition import AcquisitionError
from .domain import ContractError
from .execution_contracts import canonical
from .local_jobs import LocalJobPolicy
from .materials import artifact_file
from .native_protein_structure_acquisition import (
    decode_protein_structure_json, retained_protein_structure_file,
)
from .protein_structure_contracts import (
    ArtifactRef, IssueCode, StructuredIssue, issue, same, validate_file_identity,
)
from .protein_structure_result_worker import (
    ProteinResultWorkerPlan, ProteinResultWorkerResult,
    validate_protein_structure_result_worker_plan,
    validate_protein_structure_result_worker_result,
)


class ProteinWorkerDiagnostic(TypedDict):
    filename: Literal["native-result.json", "sheet.json", "components.json", "worker-result.json"]
    artifact_ref: ArtifactRef


class ProteinWorkerFailure(TypedDict):
    code: str
    phase: str | None
    diagnostic: dict | None
    operational: dict | None


class ProteinWorkerExecution(TypedDict):
    version: Literal["protein_structure_worker_execution_v1"]
    outcome: Literal["returned", "failed"]
    returncode: int | None
    metadata: dict | None
    failure: ProteinWorkerFailure | None
    stdout_artifact_ref: ArtifactRef | None
    stderr_artifact_ref: ArtifactRef | None
    handle_artifact_ref: ArtifactRef | None


class PreparedProteinWorker(TypedDict):
    version: Literal["protein_structure_prepared_worker_v1"]
    plan_artifact_ref: ArtifactRef
    execution_receipt_artifact_ref: ArtifactRef
    worker_result_artifact_ref: ArtifactRef | None
    diagnostic_files: list[ProteinWorkerDiagnostic]
    issues: list[StructuredIssue]


class ValidatedProteinWorker(TypedDict):
    prepared: PreparedProteinWorker
    plan: ProteinResultWorkerPlan
    execution: ProteinWorkerExecution
    result: ProteinResultWorkerResult | None


_POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
_PACKAGE_ROOT = str(Path(__file__).resolve().parents[1])
_MODULE = "gene_annotation_episode.protein_structure_result_worker"
_OUTPUTS = {"native_result_file": "native-result.json", "sheet_file": "sheet.json",
            "components_file": "components.json"}
_FILENAMES = (*_OUTPUTS.values(), "worker-result.json")
_CODES = frozenset(get_args(IssueCode))
_UNFINISHED = {"local_job_execution_unknown", "local_job_not_collectable", "local_job_cancelled",
               "local_job_stop_unconfirmed", "local_job_cleanup_requires_quiescent_unit"}


def _require(condition, code="invalid_schema"):
    if not condition:
        raise ValueError(code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields))


def _json(value):
    """Reject Python-only shapes rather than silently canonicalizing them."""
    try:
        detached = decode_protein_structure_json(canonical(value).encode("utf-8"), canonical_bytes=True)
        _require(same(value, detached))
        return detached
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error


def _path(value):
    _require(type(value) is str and value and not any(c in value for c in "\0\n\r\\"), "invalid_output_path")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts and value != "/",
             "invalid_output_path")
    return path


@contextmanager
def _directory(directory, *, create=False):
    """Pin every directory component without following symlinks."""
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in _path(str(directory)).parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        yield fd


@contextmanager
def _regular(directory_fd, name, *, flags=os.O_RDONLY):
    _require(type(name) is str and name not in ("", ".", "..") and "/" not in name, "invalid_output_path")
    fd = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    try:
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "invalid_output_path")
        yield fd
    finally:
        os.close(fd)


def _read(directory_fd, name):
    try:
        with _regular(directory_fd, name) as fd, os.fdopen(os.dup(fd), "rb") as stream:
            return stream.read()
    except FileNotFoundError:
        return None


def _immutable(directory_fd, name, value):
    raw = canonical(value).encode("utf-8")
    old = _read(directory_fd, name)
    if old is not None:
        _require(old == raw, "original_commission_mismatch")
        return
    temporary = "." + name + "." + secrets.token_hex(16) + ".writing"
    try:
        with _regular(directory_fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as fd:
            with os.fdopen(os.dup(fd), "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fchmod(fd, 0o444)
                os.fsync(fd)
        try:
            os.link(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
        except FileExistsError:
            _require(_read(directory_fd, name) == raw, "original_commission_mismatch")
        os.fsync(directory_fd)
    finally:
        os.unlink(temporary, dir_fd=directory_fd)


def _artifact_ref(value):
    _require(type(value) is str and re.fullmatch(r"artifact_[a-f0-9]{64}", value) is not None)


def _retained(store, ref):
    _artifact_ref(ref)
    try:
        row = store._require(ref, {"artifact"})
    except ContractError as error:
        raise ValueError("retained_artifact_missing" if str(error) in ("unknown_reference", "unknown_artifact")
                         else "invalid_schema") from error
    identity = {"artifact_ref": ref, "sha256": row.get("sha256"), "byte_length": row.get("size"), "format": "text"}
    validate_file_identity(identity)
    path = store.path / "artifacts" / identity["sha256"][:2] / identity["sha256"]
    try:
        with _directory(path.parent) as parent, _regular(parent, path.name):
            # Reject known symlinks/nonregular paths before the shared retained
            # lookup opens bytes. The Store content address is authoritative.
            return retained_protein_structure_file(store, identity)
    except FileNotFoundError as error:
        raise ValueError("retained_artifact_missing") from error
    except OSError as error:
        raise ValueError("invalid_output_path") from error


def _stored_json(store, ref, *, canonical_bytes=True):
    return decode_protein_structure_json(_retained(store, ref).read_bytes(), canonical_bytes=canonical_bytes)


def _inputs(store, plan):
    rows = ([plan["native_result"]] if plan["mode"] == "original_native_result"
            else [plan["sheet"], plan["original_components"]])
    for row in rows:
        if row is not None:
            path = _retained(store, row["file_identity"]["artifact_ref"])
            _require(str(path) == row["path"], "invalid_output_path")
            retained_protein_structure_file(store, row["file_identity"])


def _environment(plan, package_root):
    directory = plan["directory"]
    _path(package_root)
    # The shared native launcher deliberately sets these three to cwd. Record
    # their actual values, not an override it would subsequently discard.
    return {"PYTHONPATH": package_root, "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": directory, "TMP": directory, "TEMP": directory,
            "XDG_CACHE_HOME": directory + "/cache", "PIP_CACHE_DIR": directory + "/cache/pip",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}


def _configured_environment(plan, environment):
    from .native_protein_structure_contracts import _environment as validate_environment
    _require(type(environment) is dict
        and all(type(key) is str and type(value) is str for key, value in environment.items()))
    directory = plan["directory"]
    controls = {"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": directory, "TMP": directory, "TEMP": directory,
        "XDG_CACHE_HOME": directory + "/cache", "PIP_CACHE_DIR": directory + "/cache/pip"}
    _require(all(key not in environment or environment[key] == value for key, value in controls.items()),
        "invalid_output_path")
    selected = {key: value for key, value in environment.items() if key not in controls}
    validate_environment(selected)
    return {**selected, **controls}


def _intent(plan, *, executable=sys.executable, package_root=_PACKAGE_ROOT, environment=None):
    _path(executable)
    if environment is None:
        selected = _environment(plan, package_root)
    else:
        _require(type(environment) is dict)
        _require(package_root is None or environment.get("PYTHONPATH") == package_root,
            "original_commission_mismatch")
        selected = _configured_environment(plan, environment)
    return {"plan": deepcopy(plan), "policy": deepcopy(_POLICY),
            "command": [executable, "-B", "-m", _MODULE, plan["directory"] + "/plan.json"],
            "environment": selected}


def _check_handle(body, request, intent):
    """Check original reservation operands; no lifecycle observation or I/O."""
    _closed(body, ("version", "unit", "command", "cwd", "stdout", "stderr", "paths", "metadata", "stage",
                   "started_at", "started_monotonic_ns", "boot_id", "request_sha256"))
    _json(body)
    _require(body["version"] == native_lifecycle.VERSION and body["stage"] in ("prepared", "submitting", "released"))
    _require(type(body["unit"]) is str and re.fullmatch(r"gene-local-job-[a-f0-9]{32}\.service", body["unit"]) is not None)
    directory = intent["plan"]["directory"]
    _require(same(body["command"], intent["command"]) and body["cwd"] == directory
             and body["stdout"] == directory + "/worker.stdout"
             and body["stderr"] == directory + "/worker.stderr", "original_commission_mismatch")
    _closed(body["paths"], ("request", "ready", "release", "status", "result", "launcher"))
    stem = _path(body["paths"]["request"])
    _require(stem.parent == PurePosixPath(directory)
             and re.fullmatch(r"\.local-job-[a-f0-9]{32}\.request", stem.name) is not None, "invalid_output_path")
    prefix = str(stem)[:-len("request")]
    _require(all(body["paths"][name] == prefix + name for name in body["paths"]), "invalid_output_path")
    _require(type(body["request_sha256"]) is str
             and re.fullmatch(r"[a-f0-9]{64}", body["request_sha256"]) is not None)
    meta = body["metadata"]
    _require(type(meta) is dict and meta.get("native_lifecycle_version") == native_lifecycle.VERSION
             and same(meta.get("policy"), intent["policy"]), "original_commission_mismatch")
    enforcement = meta.get("enforcement", {})
    _require(type(enforcement) is dict and enforcement.get("memory") == "systemd_cgroup_v2_memory_max"
             and enforcement.get("swap") == "systemd_memory_swap_max_zero", "original_commission_mismatch")
    if body["stage"] == "released":
        cgroup = meta.get("verified_cgroup", {})
        _require(type(cgroup) is dict and cgroup.get("memory_max") == _POLICY["memory_bytes"]
                 and type(cgroup.get("memory_max")) is int
                 and cgroup.get("memory_swap_max") == 0 and type(cgroup.get("memory_swap_max")) is int, "original_commission_mismatch")
    if body["stage"] == "prepared":
        _require(all(body[name] is None for name in ("started_at", "started_monotonic_ns", "boot_id")))
    else:
        _require(type(body["started_monotonic_ns"]) is int and body["started_monotonic_ns"] >= 0
                 and type(body["started_at"]) is str and type(body["boot_id"]) is str)
    expected = {"command": intent["command"], "cwd": directory, "file_bytes": _POLICY["scratch_bytes"],
                "ready_path": body["paths"]["ready"], "release_path": body["paths"]["release"],
                "result_path": body["paths"]["result"], "stdin_path": None, "env": intent["environment"]}
    _require(same(request, expected), "original_commission_mismatch")


def _live_handle(directory_fd, intent):
    raw = _read(directory_fd, "worker.handle.json")
    _require(raw is not None, "capture_incomplete")
    body = decode_protein_structure_json(raw)
    # Validate path shape before opening any named request file.
    _require(type(body) is dict and type(body.get("paths")) is dict)
    request_path = body["paths"].get("request")
    request = _path(request_path)
    _require(request.parent == PurePosixPath(intent["plan"]["directory"])
             and re.fullmatch(r"\.local-job-[a-f0-9]{32}\.request", request.name) is not None, "invalid_output_path")
    request_raw = _read(directory_fd, request.name)
    _require(request_raw is not None, "retained_artifact_missing")
    _require(hashlib.sha256(request_raw).hexdigest() == body.get("request_sha256"), "input_digest_mismatch")
    _check_handle(body, decode_protein_structure_json(request_raw), intent)
    return body


def _retained_handle(store, ref, plan):
    body = _stored_json(store, ref, canonical_bytes=False)
    _require(type(body) is dict and type(body.get("request_sha256")) is str)
    request_ref = "artifact_" + body["request_sha256"]
    request = _stored_json(store, request_ref, canonical_bytes=False)
    _require(type(request) is dict and type(request.get("env")) is dict
             and type(body.get("command")) is list and len(body["command"]) == 5)
    # The original immutable intent is itself retained. Thus retained-only
    # validation can survive relocation of the caller's Python/package root.
    intent = _intent(plan, executable=body["command"][0], package_root=None, environment=request["env"])
    _check_handle(body, request, intent)
    intent_ref = "artifact_" + hashlib.sha256(canonical(intent).encode("utf-8")).hexdigest()
    _require(same(_stored_json(store, intent_ref), intent), "original_commission_mismatch")
    return body


def _host_issue(code, *, field="manifest", artifact_role=None, stage="capture"):
    return issue(code, stage=stage, field=field, artifact_role=artifact_role)


def _capture(store, directory_fd, filename):
    with _regular(directory_fd, filename) as fd:
        ref = artifact_file(store, Path("/proc/self/fd") / str(fd))
    _retained(store, ref)
    return ref


def _optional_capture(store, directory_fd, filename, issues, *, field="manifest", role=None):
    try:
        return _capture(store, directory_fd, filename)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        code = str(error) if str(error) in _CODES else "invalid_output_path"
        issues.append(_host_issue(code, field=field, artifact_role=role))
        return None


def _execution_issue(execution):
    if execution["outcome"] == "failed":
        code = "resource_budget_exceeded" if execution["failure"]["code"] == "local_job_resource_limit" else "native_process_failed"
        return _host_issue(code, field="receipt", stage="native")
    if execution["returncode"] != 0:
        return _host_issue("native_process_failed", field="returncode", stage="native")
    return None


def _qualify(store, diagnostics, execution, plan):
    """Only the three fixed output identities can qualify a worker manifest."""
    failure = _execution_issue(execution)
    if failure is not None:
        return None, [failure]
    ref = diagnostics.get("worker-result.json")
    if ref is None:
        return None, [_host_issue("native_result_missing")]
    try:
        result = validate_protein_structure_result_worker_result(_stored_json(store, ref))
        operation = plan["expected_request"]["operation"] if plan["mode"] == "original_native_result" else "compare"
        _require(result["mode"] == plan["mode"] and result["operation"] == operation, "original_commission_mismatch")
    except ValueError as error:
        code = str(error) if str(error) in _CODES else "invalid_schema"
        return None, [_host_issue(code)]
    issues = []
    for field, filename in _OUTPUTS.items():
        output = result[field]
        if output is None:
            continue
        role = "native_result" if field == "native_result_file" else None
        observed = diagnostics.get(filename)
        if observed is None:
            issues.append(_host_issue("capture_incomplete", artifact_role=role))
        elif observed != output["file_identity"]["artifact_ref"]:
            issues.append(_host_issue("input_digest_mismatch", artifact_role=role))
        else:
            try:
                retained_protein_structure_file(store, output["file_identity"])
            except ValueError as error:
                issues.append(_host_issue(str(error) if str(error) in _CODES else "invalid_schema", artifact_role=role))
    return (None if issues else result), issues


def _validate_execution(store, execution, plan):
    _closed(execution, ProteinWorkerExecution.__annotations__)
    _json(execution)
    _require(execution["version"] == "protein_structure_worker_execution_v1")
    _require(execution["outcome"] in ("returned", "failed"))
    if execution["outcome"] == "returned":
        _require(type(execution["returncode"]) is int and type(execution["metadata"]) is dict
                 and execution["failure"] is None)
        meta = execution["metadata"]
        _require(type(meta.get("native_returncode")) is int
                 and meta["native_returncode"] == execution["returncode"]
                 and type(meta.get("service_exit")) is dict
                 and same(meta.get("policy"), _POLICY))
    else:
        _require(execution["returncode"] is None and execution["metadata"] is None)
        failure = execution["failure"]
        _closed(failure, ProteinWorkerFailure.__annotations__)
        _require(type(failure["code"]) is str and bool(failure["code"]) and failure["code"] not in _UNFINISHED)
        _require(failure["phase"] is None or type(failure["phase"]) is str)
        _require(all(failure[name] is None or type(failure[name]) is dict for name in ("diagnostic", "operational")))
    for name in ("stdout_artifact_ref", "stderr_artifact_ref", "handle_artifact_ref"):
        if execution[name] is not None:
            _retained(store, execution[name])
    if execution["handle_artifact_ref"] is not None:
        body = _retained_handle(store, execution["handle_artifact_ref"], plan)
        meta = execution["metadata"] if execution["outcome"] == "returned" else execution["failure"]["operational"]
        if execution["outcome"] == "returned":
            _require(body["stage"] == "released", "original_commission_mismatch")
        if meta is not None:
            _require(all(same(meta.get(key), value) for key, value in body["metadata"].items()), "original_commission_mismatch")
    else:
        _require(execution["outcome"] == "failed")


def validate_prepared_protein_structure_worker(
    store, prepared: PreparedProteinWorker, *, plan: ProteinResultWorkerPlan
) -> ValidatedProteinWorker:
    """Validate retained custody only, without original paths, fit or dispatch."""
    plan = validate_protein_structure_result_worker_plan(plan)
    _closed(prepared, PreparedProteinWorker.__annotations__)
    _json(prepared)
    _require(prepared["version"] == "protein_structure_prepared_worker_v1")
    stored_plan = validate_protein_structure_result_worker_plan(_stored_json(store, prepared["plan_artifact_ref"]))
    _require(same(stored_plan, plan), "original_commission_mismatch")
    _inputs(store, stored_plan)
    execution = _stored_json(store, prepared["execution_receipt_artifact_ref"])
    _validate_execution(store, execution, stored_plan)
    _require(type(prepared["diagnostic_files"]) is list and type(prepared["issues"]) is list)
    diagnostics = {}
    for row in prepared["diagnostic_files"]:
        _closed(row, ProteinWorkerDiagnostic.__annotations__)
        _require(type(row["filename"]) is str and row["filename"] in _FILENAMES
                 and row["filename"] not in diagnostics)
        _retained(store, row["artifact_ref"])
        diagnostics[row["filename"]] = row["artifact_ref"]
    _require(list(diagnostics) == [name for name in _FILENAMES if name in diagnostics])
    # Host issues have these exact constrained meanings. Scientific issues are
    # preserved inside the worker result, never copied into this host list.
    for row in prepared["issues"]:
        _require(type(row) is dict and type(row.get("code")) is str and row["code"] in _CODES)
        _require(row.get("stage") in ("capture", "native") and row.get("field") in ("manifest", "receipt", "returncode")
                 and row.get("artifact_role") in (None, "native_result", "stdout", "stderr"))
        _require(same(row, _host_issue(row["code"], field=row["field"],
                     artifact_role=row["artifact_role"], stage=row["stage"])))
    result, required_issues = _qualify(store, diagnostics, execution, stored_plan)
    _require(all(any(same(required, actual) for actual in prepared["issues"]) for required in required_issues))
    qualified = prepared["worker_result_artifact_ref"]
    if qualified is not None:
        _artifact_ref(qualified)
        _require(not prepared["issues"] and result is not None
                 and qualified == diagnostics.get("worker-result.json"), "conflicting_identity")
    else:
        _require(bool(prepared["issues"]), "conflicting_identity")
        result = None
    return deepcopy({"prepared": prepared, "plan": stored_plan, "execution": execution, "result": result})


def _run(directory_fd, intent, policy, *, cancel_event=None):
    directory = Path(intent["plan"]["directory"])
    handle = native_lifecycle.NativeJobHandle(directory / "worker.handle.json")
    try:
        if _read(directory_fd, "worker.handle.json") is None:
            for name in ("worker.stdout", "worker.stderr"):
                _read(directory_fd, name)  # Reject symlink/nonregular control reuse.
            handle = native_lifecycle.prepare_job(intent["command"], cwd=directory, policy=policy,
                handle_path=handle.path, stdout_path=directory / "worker.stdout",
                stderr_path=directory / "worker.stderr", env=intent["environment"])
            _live_handle(directory_fd, intent)
            if cancel_event is None:
                native_lifecycle.start_prepared(handle)
            else:
                native_lifecycle.start_prepared(handle, cancel_event=cancel_event)
        else:
            _live_handle(directory_fd, intent)
            if cancel_event is None:
                native_lifecycle.resume_start(handle)
            else:
                native_lifecycle.resume_start(handle, cancel_event=cancel_event)
        result = (native_lifecycle.wait_job(handle) if cancel_event is None else
            native_lifecycle.wait_job(handle, cancel_event=cancel_event))
        execution = {"version": "protein_structure_worker_execution_v1", "outcome": "returned",
            "returncode": result.returncode, "metadata": deepcopy(result.metadata), "failure": None}
    except AcquisitionError as error:
        if error.code in _UNFINISHED:
            raise
        if _read(directory_fd, "worker.handle.json") is not None:
            # A failed observation of released/submitting work is not evidence
            # of a terminal failure. Preserve the original handle for recovery.
            if not native_lifecycle.status(handle)["terminal"]:
                raise
        execution = {"version": "protein_structure_worker_execution_v1", "outcome": "failed",
            "returncode": None, "metadata": None, "failure": {"code": error.code, "phase": error.phase,
                "diagnostic": deepcopy(error.diagnostic), "operational": deepcopy(error.operational)}}
    except (KeyboardInterrupt, asyncio.CancelledError):
        if _read(directory_fd, "worker.handle.json") is not None and not native_lifecycle.status(handle)["quiescent"]:
            native_lifecycle.cancel(handle)
        raise
    return execution


def _finish(store, directory_fd, plan, intent, execution):
    issues = []
    body = None
    if _read(directory_fd, "worker.handle.json") is not None:
        body = _live_handle(directory_fd, intent)
        # Keep the original request addressable through request_sha256. Preserve
        # all actual completion/control bytes as artifacts as well as on disk.
        for name in body["paths"].values():
            ref = _optional_capture(store, directory_fd, PurePosixPath(name).name, issues, field="receipt")
            if name == body["paths"]["request"]:
                _require(ref == "artifact_" + body["request_sha256"], "input_digest_mismatch")
    for field, filename, role in (("stdout_artifact_ref", "worker.stdout", "stdout"),
                                   ("stderr_artifact_ref", "worker.stderr", "stderr"),
                                   ("handle_artifact_ref", "worker.handle.json", None)):
        execution[field] = _optional_capture(store, directory_fd, filename, issues, field="receipt", role=role)
        if execution[field] is None and (body is not None or execution["outcome"] == "returned"):
            issues.append(_host_issue("capture_incomplete", field="receipt", artifact_role=role))
    diagnostics = []
    for filename in _FILENAMES:
        ref = _optional_capture(store, directory_fd, filename, issues,
            role="native_result" if filename == "native-result.json" else None)
        if ref is not None:
            diagnostics.append({"filename": filename, "artifact_ref": ref})
    result, qualification_issues = _qualify(store, {row["filename"]: row["artifact_ref"] for row in diagnostics}, execution, plan)
    issues.extend(qualification_issues)
    prepared = {"version": "protein_structure_prepared_worker_v1",
        "plan_artifact_ref": store.artifact(canonical(plan), "application/json"),
        "execution_receipt_artifact_ref": store.artifact(canonical(execution), "application/json"),
        "worker_result_artifact_ref": (next(row["artifact_ref"] for row in diagnostics if row["filename"] == "worker-result.json")
                                       if result is not None and not issues else None),
        "diagnostic_files": diagnostics, "issues": issues}
    validate_prepared_protein_structure_worker(store, prepared, plan=plan)
    _immutable(directory_fd, "prepared.json", prepared)
    return deepcopy(prepared)


def prepare_protein_structure_worker(
    store, *, plan: ProteinResultWorkerPlan, policy: LocalJobPolicy,
    executable=None, package_root=None, environment=None, cancel_event=None,
) -> PreparedProteinWorker:
    """Prepare/execute once, or recover that exact reservation and retained result."""
    plan = validate_protein_structure_result_worker_plan(plan)
    _require(type(policy) is LocalJobPolicy and same(policy.to_dict(), _POLICY), "resource_budget_exceeded")
    _inputs(store, plan)
    if executable is None and package_root is None and environment is None:
        intent = _intent(plan)
    else:
        selected_executable = sys.executable if executable is None else executable
        selected_root = (_PACKAGE_ROOT if package_root is None else package_root) if environment is None else package_root
        intent = _intent(plan, executable=selected_executable, package_root=selected_root, environment=environment)
    try:
        with _directory(plan["directory"], create=True) as directory_fd:
            _require(os.fstat(directory_fd).st_uid == os.geteuid(), "invalid_output_path")
            with _regular(directory_fd, ".preparation.lock", flags=os.O_RDWR | os.O_CREAT) as lock_fd:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                old_intent = _read(directory_fd, "intent.json")
                if old_intent is None:
                    _require(_read(directory_fd, "prepared.json") is None
                             and _read(directory_fd, "worker.handle.json") is None, "original_commission_mismatch")
                _immutable(directory_fd, "intent.json", intent)
                saved = _read(directory_fd, "prepared.json")
                if saved is not None:
                    prepared = decode_protein_structure_json(saved, canonical_bytes=True)
                    return validate_prepared_protein_structure_worker(store, prepared, plan=plan)["prepared"]
                _immutable(directory_fd, "plan.json", plan)
                # No source/observation is created: these are custody artifacts.
                store.artifact(canonical(intent), "application/json")
                for name in ("tmp", "cache"):
                    with _directory(plan["directory"] + "/" + name, create=True):
                        pass
                execution = (_run(directory_fd, intent, policy) if cancel_event is None else
                    _run(directory_fd, intent, policy, cancel_event=cancel_event))
                return _finish(store, directory_fd, plan, intent, execution)
    except OSError as error:
        raise ValueError("invalid_output_path") from error


__all__ = ["ProteinWorkerDiagnostic", "ProteinWorkerExecution", "PreparedProteinWorker", "ValidatedProteinWorker",
           "prepare_protein_structure_worker", "validate_prepared_protein_structure_worker"]
