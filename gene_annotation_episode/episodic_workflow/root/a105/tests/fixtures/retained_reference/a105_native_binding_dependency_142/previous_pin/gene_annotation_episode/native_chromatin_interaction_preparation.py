"""Explicit source/dependency freezing and one ordinary bounded result worker.

This is local execution staging and byte custody. The owning result host alone
admits received scientific facts, validates delivery, and applies credit.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import fcntl
import importlib
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import stat
import sys

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_file_capture import capture_native_file, capture_declared_native_files, retained_native_file, NativeFileCaptureError
from .chromatin_interaction_contracts import validate_chromatin_record
from .native_chromatin_interaction_contracts import POLICY, DRIVER_MODULE, HIC_READER_MODULE, canonical, digest, require, failure, unique_failures, validate_chromatin_software, _dependency_roots, selected_chromatin_formats
from .native_chromatin_interaction_driver import _regular, _directory, _writing, _immutable, _read_control, file_identity, confined_file, decode_json
from .chromatin_interaction_result_worker import (
    PLAN_VERSION, RESULT_VERSION, validate_chromatin_result_worker_plan, validate_chromatin_result_worker_result,
)

WORKER_MODULE = "gene_annotation_episode.chromatin_interaction_result_worker"
_PACKAGES = {"numpy": "numpy", "h5py": "h5py", "jsonschema": "jsonschema", "attrs": "attr",
    "referencing": "referencing", "rpds-py": "rpds", "jsonschema-specifications": "jsonschema_specifications"}
_OPTIONAL_SCHEMA_PACKAGES = {"typing-extensions": "typing_extensions", "idna": "idna", "jsonpointer": "jsonpointer",
    "fqdn": "fqdn", "rfc3987": "rfc3987", "rfc3986-validator": "rfc3986_validator",
    "rfc3987-syntax": "rfc3987_syntax", "rfc3339-validator": "rfc3339_validator", "webcolors": "webcolors",
    "uri-template": "uri_template", "isoduration": "isoduration", "lark": "lark", "arrow": "arrow",
    "python-dateutil": "dateutil", "six": "six"}


def build_native_chromatin_worker_plan(*, directory, original_plan, bundle, files, selector,
        source_action_receipt_ref, writer_closure_receipt_ref, driver_state, failures):
    return validate_chromatin_result_worker_plan({"version": PLAN_VERSION, "mode": "native_result", "directory": directory,
        "original_plan": original_plan, "bundle": bundle, "files": files, "selector": selector,
        "source_action_receipt_ref": source_action_receipt_ref, "writer_closure_receipt_ref": writer_closure_receipt_ref,
        "driver_state": driver_state, "failures": failures})


def build_saved_chromatin_worker_plan(*, directory, sheet_bundle, selector):
    return validate_chromatin_result_worker_plan({"version": PLAN_VERSION, "mode": "saved_sheet_recalculation",
        "directory": directory, "sheet_bundle": sheet_bundle, "selector": selector})


def _source_closure(module_root, modules):
    root, paths, pending = Path(module_root), {}, list(modules) + ["gene_annotation_episode.__init__"]
    while pending:
        name = pending.pop()
        if name in paths:
            continue
        path = root / (name.replace(".", "/") + ".py")
        if not path.is_file() and (root / name.replace(".", "/") / "__init__.py").is_file():
            name += ".__init__"
            path = root / (name.replace(".", "/") + ".py")
        require(path.is_file(), "native_dependency_unavailable")
        paths[name] = path
        package = name.rsplit(".", 1)[0]
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")[:len(package.split(".")) - node.level + 1]
                    imported = ".".join([*base, *([node.module] if node.module else [])])
                else:
                    imported = node.module or ""
                if imported.startswith("gene_annotation_episode."):
                    pending.append(imported)
                elif imported == "gene_annotation_episode" and node.module is None:
                    pending.extend(imported + "." + alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                pending.extend(a.name for a in node.names if a.name.startswith("gene_annotation_episode."))
    return paths


def _copy_exact(source, destination, *, executable=False):
    identity = file_identity(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(file_identity(destination) == identity and not destination.stat().st_mode & 0o222)
    else:
        with _regular(source) as original, _writing(destination) as target:
            shutil.copyfileobj(original, target, length=1024 * 1024)
        if executable:
            destination.chmod(0o555)
    require(file_identity(destination) == identity)
    return {"path": str(destination), **identity}


def _dependency_bindings(*, native_input, supported_formats=None):
    result = []
    formats = selected_chromatin_formats(supported_formats)
    need_hdf5 = native_input and "cooler_hdf5_v3" in formats
    selected = {name: module for name, module in _PACKAGES.items() if name != "h5py" or need_hdf5}
    for module in selected.values():
        importlib.import_module(module)
    # jsonschema imports optional format helpers at import time. Pin whichever
    # helpers this selected environment actually loaded, without installing or
    # enabling a different dependency or a format-checking mode.
    selected.update({name: module for name, module in _OPTIONAL_SCHEMA_PACKAGES.items() if module in sys.modules})
    for distribution, module_name in selected.items():
        module = importlib.import_module(module_name)
        installed = importlib.metadata.distribution(distribution)
        files = []
        for entry in installed.files or ():
            path = Path(installed.locate_file(entry)).resolve(strict=True)
            if path.suffix in (".pyc", ".pyo") or not path.is_file():
                continue
            files.append({"path": str(path), **file_identity(path)})
        require(bool(files), "native_dependency_unavailable")
        result.append({"distribution": distribution, "version": installed.version,
            "package_root": str(Path(module.__file__).resolve(strict=True).parent),
            "files": sorted({r["path"]: r for r in files}.values(), key=lambda r: r["path"])})
    return result


def freeze_chromatin_software_binding(*, module_root: str, snapshot_directory: str,
        python_executable: str | None = None, supported_formats=("cooler_hdf5_v3",)) -> dict:
    """Explicit preparation under the selected interpreter; never installs it.

    Call within an existing bounded local job with desired dependency import
    precedence already selected. The returned source root contains immutable
    actual implementation bytes; installed package files are pinned separately.
    """
    formats = selected_chromatin_formats(supported_formats)
    selected = python_executable or sys.executable
    require(os.path.samefile(selected, "/proc/self/exe"), "native_dependency_unavailable")
    target = _directory(snapshot_directory)
    target.mkdir(parents=True, exist_ok=True)
    entry_modules = [DRIVER_MODULE, WORKER_MODULE]
    if "hic_binary_v9" in formats:
        entry_modules.append(HIC_READER_MODULE)
    modules = _source_closure(module_root, entry_modules)
    implementation = []
    policy = LocalJobPolicy(**POLICY)
    for name, source in sorted(modules.items()):
        check_scratch_budget(target, policy, additional_bytes=source.stat().st_size)
        pin = _copy_exact(source, target / (name.replace(".", "/") + ".py"))
        implementation.append({"module": name, "sha256": pin["sha256"]})
    software = {"python_executable": selected,
        "python_sha256": file_identity(Path(selected).resolve(strict=True))["sha256"],
        "python_version": platform.python_version(), "module_root": str(target), "driver_module": DRIVER_MODULE,
        "implementation_files": implementation,
        "dependencies": _dependency_bindings(native_input=True, supported_formats=formats)}
    if "hic_binary_v9" in formats:
        from .native_chromatin_hic_runtime import capture_hic_native_runtime
        software["native_runtime"] = capture_hic_native_runtime(file_identity=file_identity)
    return validate_chromatin_software(software, supported_formats=formats)


def _snapshot(plan, policy):
    directory = Path(plan["directory"])
    module_root = Path(__file__).resolve().parents[1]
    modules = _source_closure(module_root, [WORKER_MODULE])
    pins = []
    for name, source in sorted(modules.items()):
        check_scratch_budget(directory, policy, additional_bytes=source.stat().st_size)
        pins.append(_copy_exact(source, directory / "source_snapshot" / (name.replace(".", "/") + ".py")))
    binary = Path(sys.executable).resolve(strict=True)
    check_scratch_budget(directory, policy, additional_bytes=binary.stat().st_size)
    interpreter = _copy_exact(binary, directory / "runtime/python", executable=True)
    dependencies = _dependency_bindings(native_input=False)
    roots = _dependency_roots({"dependencies": dependencies})
    environment = {"PYTHONPATH": os.pathsep.join([str(directory / "source_snapshot"), *roots]),
        "PYTHONHOME": str(Path(sys.base_prefix).resolve(strict=True)), "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory / "tmp"), "TMP": str(directory / "tmp"),
        "TEMP": str(directory / "tmp"), "XDG_CACHE_HOME": str(directory / "cache"),
        "PIP_CACHE_DIR": str(directory / "cache/pip"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    for name in ("tmp", "cache/pip"):
        (directory / name).mkdir(parents=True, exist_ok=True)
    return {"version": "chromatin_worker_intent_v1", "plan": plan, "policy": POLICY,
        "command": [interpreter["path"], "-B", "-S", "-m", WORKER_MODULE, str(directory / "plan.json")],
        "environment": environment, "source_pins": pins, "interpreter": interpreter, "dependencies": dependencies}


def _verify_pins(intent):
    pins = [*intent["source_pins"], intent["interpreter"], *(pin for row in intent["dependencies"] for pin in row["files"])]
    for pin in pins:
        require(file_identity(pin["path"]) == {k: pin[k] for k in ("sha256", "size_bytes")}, "native_dependency_unavailable")


def _capture(store, directory, name, format):
    return capture_native_file(store, directory=str(directory), relative_path=name, format=format)


def _optional_capture(store, directory, name, format):
    try:
        return _capture(store, directory, name, format)
    except NativeFileCaptureError as error:
        if error.code != "capture_file_unavailable":
            raise
        return None


def _check_handle(handle, intent):
    body = handle.read()
    require(body["command"] == intent["command"] and body["cwd"] == intent["plan"]["directory"]
        and body["metadata"]["policy"] == POLICY and body["stage"] in ("prepared", "submitting", "released"))
    with _regular(body["paths"]["request"]) as stream:
        request = decode_json(stream.read())
    require(file_identity(body["paths"]["request"])["sha256"] == body["request_sha256"])
    require(request == {"command": intent["command"], "cwd": body["cwd"], "file_bytes": POLICY["scratch_bytes"],
        "ready_path": body["paths"]["ready"], "release_path": body["paths"]["release"],
        "result_path": body["paths"]["result"], "stdin_path": None, "env": intent["environment"]})
    return body


def validate_prepared_chromatin_worker(store, value, *, plan):
    """Read saved custody records only; no producer/source refresh or execution."""
    plan = validate_chromatin_result_worker_plan(plan)
    value = validate_chromatin_record("WorkerCapture", value)
    stored_plan = _read_control(retained_native_file(store, value["plan_file"]))
    require(stored_plan == plan)
    execution = _read_control(retained_native_file(store, value["execution_receipt_file"]))
    require(execution["plan_file"] == value["plan_file"] and execution["intent"]["plan"] == plan
        and execution["terminal"] is True and execution["quiescent"] is True and execution["policy"] == POLICY)
    if value["result"] is not None:
        result = validate_chromatin_result_worker_result(_read_control(retained_native_file(store, value["worker_result_file"])))
        require(result == value["result"] and result["mode"] == plan["mode"] and result["parameters"] == plan["selector"]["parameters"])
        require(len(result["outputs"]) == len(value["outputs"]))
        for declared, captured in zip(result["outputs"], value["outputs"]):
            require(captured["role"] == declared["role"] and captured["table_key"] == declared["table_key"]
                and captured["capture"]["declared"] == declared["declaration"])
            if captured["capture"]["observed"] is not None:
                retained_native_file(store, captured["capture"]["observed"])
    else:
        require(value["outputs"] == [])
    return value


def prepare_chromatin_result_worker(store, *, plan, policy):
    plan = validate_chromatin_result_worker_plan(plan)
    require(type(policy) is LocalJobPolicy and policy.to_dict() == POLICY)
    directory = _directory(plan["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = confined_file(directory, ".preparation.lock")
    with os.fdopen(os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), "a+b") as lock:
        require(stat.S_ISREG(os.fstat(lock.fileno()).st_mode), "invalid_output_path")
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = confined_file(directory, "prepared.json")
        if saved.exists():
            return validate_prepared_chromatin_worker(store, _read_control(saved), plan=plan)
        _immutable(directory / "plan.json", plan)
        intent_path = directory / "intent.json"
        if intent_path.exists():
            intent = _read_control(intent_path)
            require(intent["plan"] == plan and intent["policy"] == POLICY)
        else:
            require(not (directory / "worker.handle.json").exists())
            inputs = ([plan["sheet_bundle"]["sheet"], *plan["sheet_bundle"]["tables"]] if plan["mode"] != "native_result" else
                [plan["bundle"], *(r["retained"] for r in plan["files"])])
            for retained in inputs:
                if retained is not None:
                    require(str(retained_native_file(store, retained["file"])) == retained["path"])
            intent = _snapshot(plan, policy)
            _immutable(intent_path, intent)
        plan_file = _capture(store, directory, "plan.json", PLAN_VERSION)
        handle = native.NativeJobHandle(directory / "worker.handle.json")
        execution_path = directory / "execution.json"
        if not execution_path.exists():
            _verify_pins(intent)
            if not handle.path.exists():
                native.prepare_job(intent["command"], cwd=directory, policy=policy, handle_path=handle.path,
                    stdout_path=directory / "worker.stdout", stderr_path=directory / "worker.stderr", env=intent["environment"])
            _check_handle(handle, intent)
            native.resume_start(handle)
            outcome, problem = None, None
            try:
                outcome = native.wait_job(handle)
            except AcquisitionError as error:
                view = native.status(handle)
                if not view["terminal"] or not view["quiescent"]:
                    raise
                problem = {"code": error.code, "phase": error.phase, "diagnostic": error.diagnostic, "operational": error.operational}
            view = native.status(handle)
            require(view["terminal"] and view["quiescent"])
            _verify_pins(intent)
            body = _check_handle(handle, intent)
            execution = {"version": "chromatin_worker_execution_v1", "plan_file": plan_file, "intent": intent,
                "terminal": True, "quiescent": True, "policy": POLICY, "returncode": outcome.returncode if outcome else None,
                "metadata": view["metadata"], "failure": problem,
                "handle_file": _capture(store, directory, "worker.handle.json", native.VERSION),
                "request_file": _capture(store, directory, Path(body["paths"]["request"]).name, "native_local_job_request"),
                "stdout_file": _capture(store, directory, "worker.stdout", "native_worker_stdout"),
                "stderr_file": _capture(store, directory, "worker.stderr", "native_worker_stderr")}
            _immutable(execution_path, execution)
        execution_file = _capture(store, directory, "execution.json", "chromatin_worker_execution_v1")
        execution = _read_control(execution_path)
        problems = []
        if execution["failure"] is not None or execution["returncode"] != 0:
            problems.append(failure("resource_limit" if execution["failure"] and execution["failure"]["code"] == "local_job_resource_limit"
                else "native_nonzero_exit", "execution", requirement="original_native_outcome"))
        result_file = _optional_capture(store, directory, "worker-result.json", RESULT_VERSION)
        result, outputs = None, []
        if result_file is not None:
            try:
                result = validate_chromatin_result_worker_result(_read_control(retained_native_file(store, result_file)))
                require(result["mode"] == plan["mode"] and result["parameters"] == plan["selector"]["parameters"])
            except ValueError:
                problems.append(failure("original_attempt_mismatch", "capture", artifact_ref=result_file["artifact_ref"]))
                result = None
        else:
            problems.append(failure("requested_field_unavailable", "capture", field_path="/worker_result", requirement="requested_selected_field"))
        if result is not None:
            captures = capture_declared_native_files(store, directory=str(directory), declarations=[r["declaration"] for r in result["outputs"]])
            outputs = [{"role": row["role"], "table_key": row["table_key"], "capture": capture} for row, capture in zip(result["outputs"], captures)]
            for row in outputs:
                if row["capture"]["outcome"] not in ("verified", "declared_absent"):
                    problems.append(failure("artifact_digest_mismatch" if row["capture"]["outcome"] == "digest_mismatch" else "input_unavailable",
                        "capture", field_path="/outputs/" + row["role"]))
        value = {"version": "chromatin_interaction_worker_capture_v1", "plan_file": plan_file,
            "execution_receipt_file": execution_file, "worker_result_file": result_file, "result": result,
            "outputs": outputs, "failures": unique_failures(problems)}
        value = validate_prepared_chromatin_worker(store, value, plan=plan)
        _immutable(saved, value)
        return value
