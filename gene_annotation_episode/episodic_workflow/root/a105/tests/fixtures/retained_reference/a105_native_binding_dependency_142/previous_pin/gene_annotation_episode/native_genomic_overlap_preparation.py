"""One bounded retained-result calculation and its immutable custody handoff.

The selected-action owner supplies authority and owns episode publication. This
module executes one finite worker through native_lifecycle, retains its actual
outcome, and checks byte/schema/selection joins. It never calculates intervals.
"""
from __future__ import annotations

import ast
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import site
import stat
import sys
from typing import Literal, TypedDict

from . import native_lifecycle
from .acquisition import AcquisitionError
from .genomic_overlap_contracts import _finite_json_copy, validate_genomic_overlap_record
from .genomic_overlap_inputs import _failure, _unique_issues
from .genomic_overlap_result_worker import (
    validate_genomic_overlap_result_worker_plan,
    validate_genomic_overlap_result_worker_result,
)
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_file_capture import (
    NativeFileCaptureError, capture_declared_native_files, capture_native_file,
    retained_native_file,
)


class WorkerExecution(TypedDict):
    version: Literal["genomic_overlap_worker_execution_v1"]
    plan_file: dict
    outcome: Literal["returned", "failed"]
    returncode: int | None
    metadata: dict | None
    failure: dict | None
    handle_file: dict | None
    request_file: dict | None
    stdout_file: dict | None
    stderr_file: dict | None
    source_pins: list[dict]
    interpreter: dict


class WorkerCapture(TypedDict):
    version: Literal["genomic_overlap_worker_capture_v1"]
    plan_file: dict
    execution_receipt_file: dict
    worker_result_file: dict | None
    result: dict | None
    outputs: list[dict]
    failures: list[dict]


_POLICY = {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
_MODULE = "gene_annotation_episode.genomic_overlap_result_worker"
_PLAN = "genomic_overlap_result_worker_plan_v1"
_EXECUTION = "genomic_overlap_worker_execution_v1"
_RESULT = "genomic_overlap_result_worker_result_v1"
_OUTPUTS = (("sheet", "sheet.json", "genomic_region_overlap_sheet_v1"),
            ("components", "components.json", "genomic_region_overlap_components_v1"),
            ("projection", "projection.json", "genomic_overlap_projection_v1"),
            ("diagnostics", "diagnostics.json", "genomic_overlap_result_diagnostics_v1"))
_CONTROLS = {"handle_file": ("worker.handle.json", native_lifecycle.VERSION),
             "request_file": (None, "native_local_job_request"),
             "stdout_file": ("worker.stdout", "native_worker_stdout"),
             "stderr_file": ("worker.stderr", "native_worker_stderr")}
_UNFINISHED = {"local_job_execution_unknown", "local_job_not_collectable", "local_job_cancelled",
               "local_job_stop_unconfirmed", "local_job_cleanup_requires_quiescent_unit"}
_REQUIRED_SOURCES = {"__init__", "genomic_overlap_result_worker", "genomic_overlap_contracts",
    "genomic_overlap_inputs", "genomic_overlap_calculations", "genomic_overlap_result_views",
    "native_genomic_overlap_contracts"}


def _require(condition, code="genomic_overlap_preparation_invalid_record"):
    if not condition:
        raise ValueError(code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields))


def _canonical(value):
    return json.dumps(_finite_json_copy(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _decode(raw, *, canonical=True):
    def pairs(rows):
        result = {}
        for key, value in rows:
            _require(key not in result, "genomic_overlap_preparation_duplicate_key")
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError("genomic_overlap_preparation_nonfinite_json")
    try:
        value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                                            parse_constant=nonfinite))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("genomic_overlap_preparation_invalid_json") from error
    _require(not canonical or raw == _canonical(value), "genomic_overlap_preparation_noncanonical_json")
    return value


def _same(a, b):
    return _canonical(a) == _canonical(b)


def _path(value):
    _require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"),
             "genomic_overlap_preparation_invalid_path")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts
             and value != "/" and not value.startswith("//"), "genomic_overlap_preparation_invalid_path")
    return path


@contextmanager
def _directory(value, *, create=False):
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, fd)
        for part in _path(str(value)).parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        yield fd


@contextmanager
def _regular(fd, name, *, flags=os.O_RDONLY):
    _require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
    item = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        _require(stat.S_ISREG(os.fstat(item).st_mode), "genomic_overlap_preparation_invalid_path")
        yield item
    finally:
        os.close(item)


def _read(fd, name):
    try:
        with _regular(fd, name) as item, os.fdopen(os.dup(item), "rb") as stream:
            return stream.read()
    except FileNotFoundError:
        return None


def _immutable(fd, name, value):
    raw = _canonical(value)
    old = _read(fd, name)
    if old is not None:
        _require(old == raw, "genomic_overlap_preparation_intent_conflict")
        return
    temporary = "." + name + "." + secrets.token_hex(16) + ".writing"
    try:
        with _regular(fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as item:
            with os.fdopen(os.dup(item), "wb") as stream:
                stream.write(raw)
                stream.flush()
            os.fchmod(item, 0o444)
            os.fsync(item)
        try:
            os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        except FileExistsError:
            _require(_read(fd, name) == raw, "genomic_overlap_preparation_intent_conflict")
        os.fsync(fd)
    finally:
        os.unlink(temporary, dir_fd=fd)


def build_native_genomic_overlap_worker_plan(*, directory: str, original_plan: dict,
        batch: dict | None, files: list[dict], selector: dict, source_action_receipt_ref: str,
        writer_closure_receipt_ref: str, driver_state: str, failures: list[dict]) -> dict:
    return validate_genomic_overlap_result_worker_plan({"version": _PLAN, "mode": "native_result",
        "directory": directory, "original_plan": original_plan, "batch": batch, "files": files,
        "selector": selector, "source_action_receipt_ref": source_action_receipt_ref,
        "writer_closure_receipt_ref": writer_closure_receipt_ref,
        "driver_state": driver_state, "failures": failures})


def build_saved_genomic_overlap_worker_plan(*, directory: str, sheet: dict, selector: dict) -> dict:
    return validate_genomic_overlap_result_worker_plan({"version": _PLAN,
        "mode": "saved_sheet_recalculation", "directory": directory, "sheet": sheet, "selector": selector})


def _identity(value, format_name):
    value = validate_genomic_overlap_record("NativeFileIdentity", value)
    _require(value["format"] == format_name, "genomic_overlap_preparation_format_binding")
    return value


def _stored(store, identity, format_name, *, canonical=True):
    _identity(identity, format_name)
    return _decode(retained_native_file(store, identity).read_bytes(), canonical=canonical)


def _capture(store, directory, name, format_name):
    return capture_native_file(store, directory=str(directory), relative_path=name, format=format_name)


def _optional_capture(store, directory, name, format_name):
    try:
        return _capture(store, directory, name, format_name)
    except NativeFileCaptureError as error:
        if error.code != "capture_file_unavailable":
            raise
        return None


def _inputs(store, plan):
    rows = ([plan["sheet"]] if plan["mode"] == "saved_sheet_recalculation" else
            [plan["batch"], *(row["retained"] for row in plan["files"])])
    for row in rows:
        if row is not None:
            _require(str(retained_native_file(store, row["file"])) == row["path"],
                     "genomic_overlap_preparation_retained_path_binding")


def _source_closure():
    """Resolve the actual imported project modules, including their imports."""
    pending, modules = [_MODULE, "gene_annotation_episode"], {}
    while pending:
        name = pending.pop()
        if name in modules:
            continue
        module = importlib.import_module(name)
        source = Path(module.__file__).resolve(strict=True)
        _require(source.suffix == ".py", "genomic_overlap_preparation_source_unavailable")
        modules[name] = source
        tree = ast.parse(source.read_bytes(), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported = (importlib.util.resolve_name("." * node.level + (node.module or ""),
                            module.__package__) if node.level else node.module)
                if imported and imported.startswith("gene_annotation_episode."):
                    pending.append(imported)
            elif isinstance(node, ast.Import):
                pending.extend(alias.name for alias in node.names
                    if alias.name.startswith("gene_annotation_episode."))
    return modules


def _stage(store, identity, target, policy, directory, *, executable=False):
    """Stage verified custody bytes into a private inode, preserving Store modes.

    This is execution staging, not artifact acquisition or registration. The
    native_file_capture helper owns the custody copy and complete verification.
    """
    source = retained_native_file(store, identity)
    check_scratch_budget(Path(directory), policy, additional_bytes=identity["size_bytes"])
    with _directory(str(target.parent), create=True) as parent:
        try:
            with _regular(parent, target.name) as existing, os.fdopen(os.dup(existing), "rb") as stream:
                digest, size = hashlib.sha256(), 0
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk); size += len(chunk)
                _require((digest.hexdigest(), size) == (identity["sha256"], identity["size_bytes"]),
                         "genomic_overlap_preparation_snapshot_conflict")
                _require(os.fstat(existing).st_mode & 0o222 == 0, "genomic_overlap_preparation_snapshot_mutable")
                return
        except FileNotFoundError:
            pass
        temporary = "." + target.name + "." + secrets.token_hex(16) + ".writing"
        try:
            with _regular(parent, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as item:
                digest, size = hashlib.sha256(), 0
                with source.open("rb") as original, os.fdopen(os.dup(item), "wb") as output:
                    for chunk in iter(lambda: original.read(1024 * 1024), b""):
                        digest.update(chunk); size += len(chunk)
                        output.write(chunk)
                    output.flush()
                _require((digest.hexdigest(), size) == (identity["sha256"], identity["size_bytes"]),
                         "genomic_overlap_preparation_snapshot_conflict")
                os.fchmod(item, 0o555 if executable else 0o444)
                os.fsync(item)
            os.link(temporary, target.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.fsync(parent)
        finally:
            os.unlink(temporary, dir_fd=parent)


def _environment(directory, dependency_paths, runtime_root):
    return {"PYTHONPATH": os.pathsep.join([directory + "/source_snapshot", *dependency_paths]),
        "PYTHONHOME": runtime_root, "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": directory, "TMP": directory, "TEMP": directory,
        "XDG_CACHE_HOME": directory + "/cache", "PIP_CACHE_DIR": directory + "/cache/pip",
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}


def _snapshot(store, plan, policy):
    directory = plan["directory"]
    root = Path(directory) / "source_snapshot"
    pins = []
    for name, source in sorted(_source_closure().items()):
        relative = Path(*name.split("."))
        relative = relative / "__init__.py" if source.name == "__init__.py" else relative.with_suffix(".py")
        identity = _capture(store, source.parent, source.name, "python_source")
        target = root / relative
        _stage(store, identity, target, policy, directory)
        pins.append({"path": str(target), "sha256": identity["sha256"], "size_bytes": identity["size_bytes"]})
    binary = Path(sys.executable).resolve(strict=True)
    identity = _capture(store, binary.parent, binary.name, "python_interpreter")
    target = Path(directory) / "runtime" / "python"
    _stage(store, identity, target, policy, directory, executable=True)
    interpreter = {"path": str(target), "sha256": identity["sha256"], "size_bytes": identity["size_bytes"]}
    for path in sorted([p for p in root.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)
    target.parent.chmod(0o555)
    # External packages/stdlib remain the explicitly recorded existing runtime;
    # they are not represented as snapshotted project source.
    user_site = Path(site.getusersitepackages()).resolve()
    dependencies = sorted({str(Path(p).resolve(strict=True)) for p in sys.path if p and
        any(part in ("site-packages", "dist-packages") for part in Path(p).parts)
        and not Path(p).resolve().is_relative_to(user_site)})
    environment = _environment(directory, dependencies, str(Path(sys.base_prefix).resolve(strict=True)))
    return {"version": "genomic_overlap_worker_intent_v1", "plan": plan, "policy": deepcopy(_POLICY),
        "command": [interpreter["path"], "-B", "-S", "-m", _MODULE, directory + "/plan.json"],
        "environment": environment, "source_pins": sorted(pins, key=lambda row: row["path"]),
        "interpreter": interpreter}


def _pins(execution, plan):
    root = PurePosixPath(plan["directory"]) / "source_snapshot"
    paths = []
    for pin in [*execution["source_pins"], execution["interpreter"]]:
        _closed(pin, ("path", "sha256", "size_bytes"))
        _path(pin["path"])
        _require(type(pin["sha256"]) is str and re.fullmatch(r"[a-f0-9]{64}", pin["sha256"]) is not None
                 and type(pin["size_bytes"]) is int and pin["size_bytes"] > 0)
    for pin in execution["source_pins"]:
        path = PurePosixPath(pin["path"])
        _require(root in path.parents and path.suffix == ".py")
        paths.append(pin["path"])
    _require(paths == sorted(set(paths)) and {str(root / "gene_annotation_episode" / (name + ".py"))
        for name in _REQUIRED_SOURCES}.issubset(paths))
    _require(execution["interpreter"]["path"] == plan["directory"] + "/runtime/python")


def _verify_snapshot(store, plan, intent):
    """Pending recovery checks its original snapshot, never today's sources."""
    _pins(intent, plan)
    for pin in [*intent["source_pins"], intent["interpreter"]]:
        path = Path(pin["path"])
        identity = _capture(store, path.parent, path.name,
            "python_interpreter" if pin == intent["interpreter"] else "python_source")
        _require(all(identity[key] == pin[key] for key in ("sha256", "size_bytes")),
                 "genomic_overlap_preparation_snapshot_conflict")
        with _directory(str(path.parent)) as parent, _regular(parent, path.name) as item:
            _require(os.fstat(item).st_mode & 0o222 == 0, "genomic_overlap_preparation_snapshot_mutable")


def _check_handle(body, request, request_raw, plan, execution):
    _closed(body, ("version", "unit", "command", "cwd", "stdout", "stderr", "paths", "metadata", "stage",
                   "started_at", "started_monotonic_ns", "boot_id", "request_sha256"))
    directory = plan["directory"]
    _require(body["version"] == native_lifecycle.VERSION and body["stage"] in ("prepared", "submitting", "released"))
    _require(type(body["unit"]) is str and re.fullmatch(r"gene-local-job-[a-f0-9]{32}\.service", body["unit"]) is not None)
    command = [execution["interpreter"]["path"], "-B", "-S", "-m", _MODULE, directory + "/plan.json"]
    _require(body["command"] == command and body["cwd"] == directory and
        body["stdout"] == directory + "/worker.stdout" and body["stderr"] == directory + "/worker.stderr",
        "genomic_overlap_preparation_execution_binding")
    _closed(body["paths"], ("request", "ready", "release", "status", "result", "launcher"))
    path = _path(body["paths"]["request"])
    _require(path.parent == PurePosixPath(directory) and
        re.fullmatch(r"\.local-job-[a-f0-9]{32}\.request", path.name) is not None)
    prefix = str(path)[:-len("request")]
    _require(all(body["paths"][name] == prefix + name for name in body["paths"]))
    _require(hashlib.sha256(request_raw).hexdigest() == body["request_sha256"],
             "genomic_overlap_preparation_request_digest")
    env = request.get("env") if type(request) is dict else None
    _require(type(env) is dict and type(env.get("PYTHONPATH")) is str and type(env.get("PYTHONHOME")) is str)
    paths = env["PYTHONPATH"].split(os.pathsep)
    _require(paths[0] == directory + "/source_snapshot" and len(set(paths)) == len(paths))
    for item in paths[1:]:
        path = _path(item)
        _require(path.name in ("site-packages", "dist-packages") and ".local" not in path.parts)
    _path(env["PYTHONHOME"])
    _require(_same(env, _environment(directory, paths[1:], env["PYTHONHOME"])))
    expected = {"command": command, "cwd": directory, "file_bytes": _POLICY["scratch_bytes"],
        "ready_path": body["paths"]["ready"], "release_path": body["paths"]["release"],
        "result_path": body["paths"]["result"], "stdin_path": None, "env": env}
    _require(_same(request, expected), "genomic_overlap_preparation_execution_binding")
    meta = body["metadata"]
    _require(type(meta) is dict and meta.get("native_lifecycle_version") == native_lifecycle.VERSION and
        _same(meta.get("policy"), _POLICY) and _same(meta.get("enforcement"), native_lifecycle._metadata(
            LocalJobPolicy(**_POLICY))["enforcement"]), "genomic_overlap_preparation_allocation_binding")
    if body["stage"] == "released":
        expected = {"memory_max": _POLICY["memory_bytes"], "memory_swap_max": 0,
                    "runtime_max": "infinity", "kill_mode": "control-group", "oom_policy": "kill"}
        _require(_same(meta.get("verified_cgroup"), expected), "genomic_overlap_preparation_allocation_binding")
    if body["stage"] == "prepared":
        _require(all(body[name] is None for name in ("started_at", "started_monotonic_ns", "boot_id")))
    else:
        _require(type(body["started_monotonic_ns"]) is int and body["started_monotonic_ns"] >= 0
            and type(body["started_at"]) is str and type(body["boot_id"]) is str)


def _live_handle(fd, plan, intent):
    raw = _read(fd, "worker.handle.json")
    _require(raw is not None)
    body = _decode(raw, canonical=False)
    _require(type(body) is dict and type(body.get("paths")) is dict)
    path = _path(body["paths"].get("request"))
    _require(path.parent == PurePosixPath(plan["directory"]) and
        re.fullmatch(r"\.local-job-[a-f0-9]{32}\.request", path.name) is not None)
    request_raw = _read(fd, path.name)
    _require(request_raw is not None, "genomic_overlap_preparation_request_missing")
    request = _decode(request_raw, canonical=False)
    _check_handle(body, request, request_raw, plan, intent)
    _require(_same(request["env"], intent["environment"]) and _same(body["command"], intent["command"]),
             "genomic_overlap_preparation_intent_conflict")
    return body


def _validate_execution(store, execution, plan, plan_file):
    _closed(execution, WorkerExecution.__annotations__)
    _finite_json_copy(execution)
    _require(execution["version"] == _EXECUTION and execution["outcome"] in ("returned", "failed")
        and _same(execution["plan_file"], plan_file), "genomic_overlap_preparation_execution_binding")
    _require(type(execution["source_pins"]) is list)
    _pins(execution, plan)
    if execution["outcome"] == "returned":
        _require(type(execution["returncode"]) is int and type(execution["metadata"]) is dict
            and execution["failure"] is None and execution["handle_file"] is not None)
        meta = execution["metadata"]
        _require(type(meta.get("native_returncode")) is int and meta["native_returncode"] == execution["returncode"]
            and type(meta.get("service_exit")) is dict and _same(meta.get("policy"), _POLICY))
    else:
        _require(execution["returncode"] is None and execution["metadata"] is None)
        failure = execution["failure"]
        _closed(failure, ("code", "phase", "diagnostic", "operational"))
        _require(type(failure["code"]) is str
            and (failure["phase"] is None or type(failure["phase"]) is str)
            and all(failure[name] is None or type(failure[name]) is dict for name in ("diagnostic", "operational")))
        if failure["code"] in _UNFINISHED:
            raise AcquisitionError(failure["code"], phase=failure["phase"],
                diagnostic=deepcopy(failure["diagnostic"]), operational=deepcopy(failure["operational"]))
        meta = failure["operational"]
        # This is the retained proof produced by lifecycle collection, not a
        # new attempt to infer today's service state. Creation qualified it.
        if execution["handle_file"] is not None and not (type(meta) is dict and type(meta.get("service_exit")) is dict):
            raise AcquisitionError("local_job_execution_unknown", phase="local_execution", operational=deepcopy(meta))
        if execution["handle_file"] is None:
            _require(failure["phase"] == "local_preflight" and type(meta) is dict and
                (failure["code"] == "local_job_boundary_unavailable" and meta.get("reason") == "user_systemd_required"
                 or failure["code"] == "local_job_resource_limit" and meta.get("evidence", {}).get("stage") == "staged_inputs"))
    for field, (_, format_name) in _CONTROLS.items():
        if execution[field] is not None:
            _identity(execution[field], format_name)
            retained_native_file(store, execution[field])
    if execution["handle_file"] is not None:
        _require(execution["request_file"] is not None)
        body = _stored(store, execution["handle_file"], native_lifecycle.VERSION, canonical=False)
        request_raw = retained_native_file(store, execution["request_file"]).read_bytes()
        request = _decode(request_raw, canonical=False)
        _check_handle(body, request, request_raw, plan, execution)
        _require(execution["request_file"]["sha256"] == body["request_sha256"])
        _require(type(meta) is dict and all(_same(meta.get(key), value) for key, value in body["metadata"].items()),
                 "genomic_overlap_preparation_execution_binding")
        if execution["outcome"] == "returned":
            _require(body["stage"] == "released")
    else:
        _require(execution["request_file"] is None)
    return execution


def _execution(store, plan_file, execution_file):
    plan = validate_genomic_overlap_result_worker_plan(_stored(store, plan_file, _PLAN))
    value = _stored(store, execution_file, _EXECUTION)
    return plan, _validate_execution(store, value, plan, plan_file)


def _issue(code, role, *, identity=None, observed=None, expected=None, stage="capture"):
    return _failure(code, stage, artifact_ref=identity["artifact_ref"] if identity else None,
        field_path="/outputs/" + role if role in {r[0] for r in _OUTPUTS} else "/" + role,
        expected_value=expected, observed_value=observed,
        partial_artifact_refs=[identity["artifact_ref"]] if identity else [],
        requirement="matching_file_identity" if code in ("artifact_digest_mismatch", "original_attempt_mismatch")
                    else "requested_selected_field" if code == "requested_field_unavailable"
                    else "original_native_output")


def _result(store, identity, plan):
    result = validate_genomic_overlap_result_worker_result(_stored(store, identity, _RESULT))
    _require(result["mode"] == plan["mode"] and _same(result["parameters"], plan["selector"]["parameters"]),
             "genomic_overlap_preparation_result_binding")
    return result


def _diagnostics(value, plan):
    _closed(value, ("version", "mode", "sets", "pairs", "failures"))
    _require(value["version"] == "genomic_overlap_result_diagnostics_v1" and value["mode"] == plan["mode"])
    _require(all(type(value[key]) is list for key in ("sets", "pairs", "failures")))
    for row in value["failures"]:
        validate_genomic_overlap_record("Failure", row)
    request = None if plan["mode"] != "native_result" else plan["original_plan"]["requested_job"]["native_genomic_overlap"]["request"]
    _require(len(value["sets"]) == (len(request["region_sets"]) if request else 0)
        and len(value["pairs"]) == (len(request["comparisons"]) if request else 0))
    for index, row in enumerate(value["sets"]):
        _closed(row, ("set_key", "set_position", "basis", "original_file", "parsed_file", "result_extent", "failures"))
        _require(row["set_key"] == request["region_sets"][index]["set_key"] and type(row["set_position"]) is int
            and row["set_position"] == index and row["basis"] in ("retained_parsed_set", "reparsed_retained_original", "unavailable"))
        for name in ("original_file", "parsed_file"):
            if row[name] is not None:
                validate_genomic_overlap_record("NativeFileIdentity", row[name])
    for index, row in enumerate(value["pairs"]):
        _closed(row, ("comparison_key", "manifest_origin", "manifest_file", "batch_pair_index", "result_extent", "failures"))
        _require(row["comparison_key"] == request["comparisons"][index]["comparison_key"]
            and row["manifest_origin"] in ("batch", "pair", "none"))
        if row["manifest_origin"] == "batch":
            _require(type(row["batch_pair_index"]) is int and row["batch_pair_index"] == index and plan["batch"] is not None
                and row["manifest_file"] == plan["batch"]["file"])
        else:
            _require(row["batch_pair_index"] is None and (row["manifest_file"] is None) == (row["manifest_origin"] == "none"))
        if row["manifest_file"] is not None:
            validate_genomic_overlap_record("NativeFileIdentity", row["manifest_file"])
    for row in [*value["sets"], *value["pairs"]]:
        _require(row["result_extent"] in ("complete", "partial", "unavailable") and type(row["failures"]) is list)
        for failure in row["failures"]:
            validate_genomic_overlap_record("Failure", failure)


def _projection(value, plan):
    selector, selected = plan["selector"], plan["selector"]["projection"]
    _require(value["kind"] == selected["kind"] and value["measurement_fields"] == selected["measurement_fields"]
        and value["page"]["offset"] == selected["offset"] and value["page"]["limit"] == selected["limit"],
        "genomic_overlap_preparation_projection_binding")
    field = {"pair_metrics": "pair_rows", "set_metrics": "set_rows", "occurrence_rows": "occurrence_rows"}[value["kind"]]
    _require(all(not value[name] for name in ("pair_rows", "set_rows", "occurrence_rows") if name != field))
    rows, page = value[field], value["page"]
    _require(page["returned_rows"] == len(rows) == min(page["limit"], max(0, page["total_rows"] - page["offset"])))
    for row in rows:
        _require(set(row["measurements"]) == set(selected["measurement_fields"]))
        if field != "set_rows":
            _require(row["comparison_key"] in selector["comparison_keys"])
        if field == "occurrence_rows" and selected["occurrence_keys"]:
            _require({"set_key": row["set_key"], "occurrence_key": row["occurrence_key"]} in selected["occurrence_keys"])
    if field == "pair_rows":
        keys = selector["comparison_keys"]
        _require(page["total_rows"] == len(keys) and [row["comparison_key"] for row in rows]
            == keys[page["offset"]:page["offset"] + page["limit"]])
    _require([row["comparison_key"] for row in value["reference_relations"]] == selector["comparison_keys"])


def _output_issues(store, outputs, result, plan):
    failures = []
    for row, (role, _, format_name) in zip(outputs, _OUTPUTS):
        capture = validate_genomic_overlap_record("NativeFileCapture", row)
        declaration, observed = capture["declared"], capture["observed"]
        outcome = capture["outcome"]
        if observed is not None:
            _identity(observed, format_name)
            retained_native_file(store, observed)
        equal = observed is not None and all(observed[k] == declaration[k] for k in ("format", "sha256", "size_bytes"))
        _require((outcome == "verified" and declaration["state"] == "present" and equal and capture["failure"] is None)
            or (outcome == "declared_absent" and declaration["state"] == "absent" and observed is None and capture["failure"] is None)
            or (outcome == "unavailable" and declaration["state"] == "present" and observed is None and capture["failure"] == "capture_file_unavailable")
            or (outcome == "digest_mismatch" and declaration["state"] == "present" and observed is not None and not equal
                and capture["failure"] == "capture_file_digest_mismatch"))
        if outcome != "verified":
            failures.append(_issue("artifact_digest_mismatch" if outcome == "digest_mismatch" else "requested_field_unavailable",
                role, identity=observed, observed=capture, expected=declaration))
            continue
        try:
            value = _stored(store, observed, format_name)
            if role == "diagnostics":
                _diagnostics(value, plan)
                _require(_same(value["failures"], result["failures"]))
            else:
                validate_genomic_overlap_record({"sheet": "Sheet", "components": "Components", "projection": "Projection"}[role], value)
                if role == "sheet":
                    _require(observed["sha256"] == result["source_sheet_sha256"])
                    if plan["mode"] == "saved_sheet_recalculation":
                        _require(all(observed[key] == plan["sheet"]["file"][key] for key in ("sha256", "size_bytes")))
                    else:
                        _require(_same(value["request"], plan["original_plan"]["requested_job"]["native_genomic_overlap"]["request"]))
                else:
                    _require(value["source_sheet_sha256"] == result["source_sheet_sha256"]
                        and _same(value["parameters"], plan["selector"]["parameters"]))
                if role == "projection":
                    _projection(value, plan)
        except NativeFileCaptureError:
            raise
        except ValueError:
            failures.append(_issue("native_output_malformed", role, identity=observed, observed=observed, stage="parse"))
    affected = {failure["field_path"] for failure in failures}
    for dependent, dependencies in (("components", ("sheet",)), ("projection", ("sheet", "components"))):
        for dependency in dependencies:
            if "/outputs/" + dependency in affected:
                row = outputs[next(i for i, output in enumerate(_OUTPUTS) if output[0] == dependency)]
                failures.append(_issue("requested_field_unavailable", dependent, identity=row["observed"],
                    expected=dependency, observed=row, stage="project" if dependent == "projection" else "calculate"))
    return failures


def _execution_issues(execution):
    if execution["outcome"] == "failed":
        code = "resource_limit" if execution["failure"]["code"] == "local_job_resource_limit" else "native_output_unavailable"
        return [_issue(code, "execution", observed=execution["failure"], stage="native")]
    if execution["returncode"] != 0:
        return [_issue("native_nonzero_exit", "execution", observed=execution["returncode"], stage="native")]
    return []


def capture_genomic_overlap_worker_outputs(store, *, directory: str, plan_file: dict,
        execution_receipt_file: dict) -> dict:
    plan, execution = _execution(store, plan_file, execution_receipt_file)
    _require(directory == plan["directory"], "genomic_overlap_preparation_directory_binding")
    failures = _execution_issues(execution)
    result_file = _optional_capture(store, directory, "worker-result.json", _RESULT)
    result = None
    if result_file is None:
        failures.append(_issue("native_output_unavailable", "worker_result"))
    else:
        try:
            result = _result(store, result_file, plan)
        except NativeFileCaptureError:
            raise
        except ValueError:
            failures.append(_issue("native_output_malformed", "worker_result", identity=result_file,
                                   observed=result_file, stage="parse"))
    outputs = []
    if result is not None:
        outputs = capture_declared_native_files(store, directory=directory,
            declarations=[row["declaration"] for row in result["outputs"]])
        failures.extend(_output_issues(store, outputs, result, plan))
    else:
        result = None
        for role, filename, format_name in _OUTPUTS:
            identity = _optional_capture(store, directory, filename, format_name)
            if identity is not None:
                failures.append(_issue("requested_field_unavailable", role, identity=identity, observed=identity))
    value = {"version": "genomic_overlap_worker_capture_v1", "plan_file": deepcopy(plan_file),
        "execution_receipt_file": deepcopy(execution_receipt_file), "worker_result_file": result_file,
        "result": result, "outputs": outputs, "failures": _unique_issues(failures)}
    return validate_prepared_genomic_overlap_worker(store, value, plan=plan)


def validate_prepared_genomic_overlap_worker(store, value: object, *, plan: dict) -> dict:
    """Validate retained records only; never probe, recapture, or rerun work."""
    plan = validate_genomic_overlap_result_worker_plan(plan)
    value = _finite_json_copy(value)
    _closed(value, WorkerCapture.__annotations__)
    _require(value["version"] == "genomic_overlap_worker_capture_v1")
    stored_plan, execution = _execution(store, value["plan_file"], value["execution_receipt_file"])
    _require(_same(stored_plan, plan), "genomic_overlap_preparation_plan_binding")
    _require(type(value["failures"]) is list and type(value["outputs"]) is list)
    for failure in value["failures"]:
        validate_genomic_overlap_record("Failure", failure)
    required = _execution_issues(execution)
    result_file = value["worker_result_file"]
    result = None
    if result_file is None:
        required.append(_issue("native_output_unavailable", "worker_result"))
    else:
        try:
            result = _result(store, result_file, plan)
        except NativeFileCaptureError:
            raise
        except ValueError:
            required.append(_issue("native_output_malformed", "worker_result", identity=result_file,
                                   observed=result_file, stage="parse"))
    if value["result"] is None:
        _require(value["outputs"] == [] and result is None)
        # Diagnostic identities carry their actual format/SHA/size. Their
        # original capture list is not reconstructed by probing fixed paths.
        for role, _, format_name in _OUTPUTS:
            rows = [failure for failure in value["failures"] if failure["field_path"] == "/outputs/" + role]
            _require(len(rows) <= 1)
            if rows:
                identity = _identity(rows[0]["observed_value"], format_name)
                retained_native_file(store, identity)
                required.append(_issue("requested_field_unavailable", role, identity=identity, observed=identity))
    else:
        _require(result is not None and _same(result, value["result"]))
        _require(len(value["outputs"]) == 4 and all(_same(row["declared"], declaration["declaration"])
            for row, declaration in zip(value["outputs"], result["outputs"])))
        required.extend(_output_issues(store, value["outputs"], result, plan))
    _require(_same(_unique_issues(required), value["failures"]), "genomic_overlap_preparation_failure_binding")
    return value


def _run(fd, plan, intent, policy):
    directory = Path(plan["directory"])
    handle = native_lifecycle.NativeJobHandle(directory / "worker.handle.json")
    try:
        if _read(fd, "worker.handle.json") is None:
            for name in ("worker.stdout", "worker.stderr"):
                _require(_read(fd, name) is None, "genomic_overlap_preparation_unowned_output")
            native_lifecycle.prepare_job(intent["command"], cwd=directory, policy=policy,
                handle_path=handle.path, stdout_path=directory / "worker.stdout",
                stderr_path=directory / "worker.stderr", env=intent["environment"])
            _live_handle(fd, plan, intent)
            native_lifecycle.start_prepared(handle)
        else:
            _live_handle(fd, plan, intent)
            native_lifecycle.resume_start(handle)
        result = native_lifecycle.wait_job(handle)
        # Use the lifecycle's terminal/quiescence definition before capture.
        view = native_lifecycle.status(handle)
        if not view["terminal"] or not view["quiescent"]:
            raise AcquisitionError("local_job_execution_unknown", phase="local_execution", operational=view["metadata"])
        return {"outcome": "returned", "returncode": result.returncode,
                "metadata": deepcopy(result.metadata), "failure": None}
    except AcquisitionError as error:
        if error.code in _UNFINISHED:
            raise
        if _read(fd, "worker.handle.json") is not None:
            view = native_lifecycle.status(handle)
            if not view["terminal"] or not view["quiescent"]:
                raise
            # A startup error with no terminal operational evidence is not
            # converted into a made-up terminal worker receipt.
            if not isinstance(error.operational, dict) or not isinstance(error.operational.get("service_exit"), dict):
                raise AcquisitionError("local_job_execution_unknown", phase="local_execution",
                                       operational=deepcopy(error.operational)) from error
        return {"outcome": "failed", "returncode": None, "metadata": None,
            "failure": {"code": error.code, "phase": error.phase,
                "diagnostic": deepcopy(error.diagnostic), "operational": deepcopy(error.operational)}}


def prepare_genomic_overlap_worker(store, *, plan: dict, policy: LocalJobPolicy) -> dict:
    plan = validate_genomic_overlap_result_worker_plan(plan)
    _require(type(policy) is LocalJobPolicy and _same(policy.to_dict(), _POLICY),
             "genomic_overlap_preparation_allocation_binding")
    with _directory(plan["directory"], create=True) as fd:
        _require(os.fstat(fd).st_uid == os.geteuid(), "genomic_overlap_preparation_invalid_path")
        with _regular(fd, ".preparation.lock", flags=os.O_RDWR | os.O_CREAT) as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            saved = _read(fd, "prepared.json")
            if saved is not None:
                return validate_prepared_genomic_overlap_worker(store, _decode(saved), plan=plan)
            _immutable(fd, "plan.json", plan)
            intent_raw = _read(fd, "intent.json")
            if intent_raw is None:
                _require(_read(fd, "worker.handle.json") is None, "genomic_overlap_preparation_intent_conflict")
                _inputs(store, plan)
                intent = _snapshot(store, plan, policy)
                _immutable(fd, "intent.json", intent)
            else:
                intent = _decode(intent_raw)
                _require(_same(intent["plan"], plan) and _same(intent["policy"], _POLICY),
                         "genomic_overlap_preparation_intent_conflict")
            plan_file = _capture(store, plan["directory"], "plan.json", _PLAN)
            completed = _read(fd, "execution.json")
            if completed is None:
                _verify_snapshot(store, plan, intent)
                execution = {"version": _EXECUTION, "plan_file": plan_file,
                    **_run(fd, plan, intent, policy), "source_pins": deepcopy(intent["source_pins"]),
                    "interpreter": deepcopy(intent["interpreter"])}
                body = _live_handle(fd, plan, intent) if _read(fd, "worker.handle.json") is not None else None
                for field, (filename, format_name) in _CONTROLS.items():
                    name = PurePosixPath(body["paths"]["request"]).name if field == "request_file" and body else filename
                    execution[field] = _optional_capture(store, plan["directory"], name, format_name) if name else None
                _validate_execution(store, execution, plan, plan_file)
                _immutable(fd, "execution.json", execution)
            execution_file = _capture(store, plan["directory"], "execution.json", _EXECUTION)
            value = capture_genomic_overlap_worker_outputs(store, directory=plan["directory"],
                plan_file=plan_file, execution_receipt_file=execution_file)
            _immutable(fd, "prepared.json", value)
            return value


__all__ = ["build_native_genomic_overlap_worker_plan", "build_saved_genomic_overlap_worker_plan",
    "prepare_genomic_overlap_worker", "validate_prepared_genomic_overlap_worker",
    "capture_genomic_overlap_worker_outputs"]
