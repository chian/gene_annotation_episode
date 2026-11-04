"""Run one finite FBA result worker under the existing native boundary.

The selected action owns a common scratch root. Numerical output and immutable
adapter controls are separate siblings beneath that root; native scratch
accounting covers both. This adapter neither authenticates episode commissions
nor performs scientific parsing/calculation in the host.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import sys

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .execution_contracts import canonical, digest
from .flux_balance_contracts import validate_flux_balance_record
from .flux_balance_worker_contracts import (OUTPUTS, PLAN_VERSION, RESULT_VERSION,
    validate_flux_balance_worker_plan, validate_flux_balance_worker_result)
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_file_capture import (NativeFileCaptureError, capture_native_file,
    capture_declared_native_files, retained_native_file)
from .native_flux_balance_contracts import (ATTEMPT_DIRECTORY_NAME, POLICY,
    flux_balance_environment, path_value, validate_flux_balance_software)
from .native_flux_balance_storage import (_directory_fd, confined_file, decode_json,
    directory, file_pin, immutable_bytes, read_bytes)


__all__ = ["prepare_flux_balance_result_worker", "validate_prepared_flux_balance_worker",
    "validate_flux_balance_worker_execution"]

WORKER_MODULE = "gene_annotation_episode.flux_balance_result_worker"
EXECUTION_VERSION = "flux_balance_worker_execution_v1"
CAPTURE_VERSION = "flux_balance_worker_capture_v1"
_INTENT_VERSION = "flux_balance_worker_intent_v1"
_SELECTED_INTENT_VERSION = "flux_balance_worker_intent_v2"
_CONTROL_NAMES = ("plan.json", "intent.json", "worker.handle.json", "worker.stdout",
    "worker.stderr", "execution.json", "capture.json", ".preparation.lock")
_CGROUP = {"memory_max": POLICY["memory_bytes"], "memory_swap_max": 0,
    "runtime_max": "infinity", "kill_mode": "control-group", "oom_policy": "kill"}


def _require(condition, code):
    if not condition:
        raise ValueError("fba_preparation_" + code)


def _same(left, right):
    return canonical(left) == canonical(right)


def _json(raw):
    value = decode_json(raw)
    canonical(value)
    return value


def _issue(code, field):
    return validate_flux_balance_record("Issue", {"code": code, "stage": "capture", "field": field,
        "detail_file": None, "source_row_index": None, "reaction_position": None,
        "metabolite_position": None, "variable_position": None, "constraint_position": None})


def _unique(values):
    result, seen = [], set()
    for value in values:
        key = canonical(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _file(value, format_=None):
    value = validate_flux_balance_record("File", value)
    _require(value["artifact_ref"] == "artifact_" + value["sha256"]
        and (format_ is None or value["format"] == format_), "file_invalid")
    return value


def _pin(value):
    _require(type(value) is dict and set(value) == {"path", "sha256", "size_bytes"}, "pin_invalid")
    path_value(value["path"], absolute=True)
    _file({"artifact_ref": "artifact_" + str(value["sha256"]), "sha256": value["sha256"],
        "size_bytes": value["size_bytes"], "format": "runtime_file"})
    return value


def _paths(value):
    if type(value) is dict:
        for name, child in value.items():
            if name == "path" and type(child) is str and child.startswith("/"):
                yield child
            elif name in ("python_home", "module_root", "attempt_directory") and type(child) is str:
                yield child
            elif name == "dependency_roots" and type(child) is list:
                yield from child
            else:
                yield from _paths(child)
    elif type(value) is list:
        for child in value:
            yield from _paths(child)


def _overlap(left, right):
    left, right = Path(left), Path(right)
    return left == right or left in right.parents or right in left.parents


def _layout(plan):
    output = Path(path_value(plan["directory"], absolute=True))
    root = Path(path_value(plan["directory"] + ".execution", absolute=True))
    common = Path(path_value(str(output.parent), absolute=True))
    selected = (list(_paths(plan["original_plan"])) + list(_paths(plan["capture"]))
        if plan["mode"] == "native_result" else [plan["sheet"]["path"]])
    _require(not any(_overlap(common, path) for path in selected), "directory_overlap")
    _require(output.parent == root.parent == common and not _overlap(root, output), "directory_overlap")
    return common, root, output


@contextmanager
def _locked(root):
    with _directory_fd(root) as parent:
        fd = os.open(".preparation.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600, dir_fd=parent)
    try:
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "lock_invalid")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _read_control(root, name):
    path = confined_file(root, name)
    try:
        value = _json(read_bytes(path))
    except FileNotFoundError:
        return None
    _require(type(value) is dict, "control_invalid")
    return value


def _immutable(root, name, value):
    path = confined_file(root, name)
    raw = canonical(value).encode("utf-8") + b"\n"
    if path.exists():
        _require(read_bytes(path) == raw, "control_conflict")
        return
    try:
        immutable_bytes(path, raw)
    except FileExistsError:
        _require(read_bytes(path) == raw, "control_conflict")


def _dependency_roots(rows):
    # Existing production dependency definition and import-root interpretation.
    from .native_atac_differential_contracts import _dependency_roots as roots
    return roots({"dependencies": rows})


def _environment(root, common, home, dependencies):
    return {"PYTHONPATH": os.pathsep.join([str(root / "source_snapshot"), *_dependency_roots(dependencies)]),
        "PYTHONHOME": home, "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(common), "TMP": str(common), "TEMP": str(common),
        "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip"),
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}


def _selected_source_pins(software, root):
    selected_root = Path(software["module_root"])
    result = []
    for pin in sorted(software["implementation_files"], key=lambda row: row["path"]):
        try:
            relative = Path(pin["path"]).relative_to(selected_root)
        except ValueError as error:
            raise ValueError("fba_preparation_selected_source_root_invalid") from error
        _require(relative.parts and ".." not in relative.parts, "selected_source_root_invalid")
        result.append({**pin, "path": str(root / "source_snapshot" / relative)})
    _require({str(root / "source_snapshot" / "gene_annotation_episode" / name)
              for name in ("__init__.py", "flux_balance_result_worker.py")}
             <= {pin["path"] for pin in result}, "selected_worker_source_missing")
    return result


def _selected_environment(root, software):
    environment = flux_balance_environment(software,
        attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME), lifecycle_directory=str(root))
    # The selected application bytes are copied unchanged; dependency and
    # interpreter-home identities remain the explicitly selected originals.
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(root / "source_snapshot"), *software["dependency_roots"]])
    return environment


def _selected_snapshot(plan, policy, software):
    from .native_atac_differential_preparation import _source_closure, _copy_exact
    software = validate_flux_balance_software(software)
    common, root, _ = _layout(plan)
    originals = [software["python"], *software["implementation_files"],
        *software["runtime_files"], *software["solver_runtime_files"]]
    _require(not any(_overlap(common, pin["path"]) for pin in originals)
        and not any(_overlap(common, path) for path in
            (software["python_home"], software["module_root"], *software["dependency_roots"])),
        "runtime_directory_overlap")
    for pin in originals:
        _require(_same(file_pin(pin["path"]), pin), "runtime_changed")
    sources = _source_closure(Path(software["module_root"]), [WORKER_MODULE])
    _require({str(path) for path in sources.values()}
        <= {pin["path"] for pin in software["implementation_files"]}, "selected_source_closure_incomplete")
    pins = _selected_source_pins(software, root)
    for original, expected in zip(sorted(software["implementation_files"], key=lambda row: row["path"]), pins):
        check_scratch_budget(common, policy, additional_bytes=original["size_bytes"])
        copied = _copy_exact(Path(original["path"]), Path(expected["path"]))
        _require(_same(copied, expected), "runtime_changed")
    check_scratch_budget(common, policy, additional_bytes=software["python"]["size_bytes"])
    interpreter = _copy_exact(Path(software["python"]["path"]), root / "runtime/python", executable=True)
    _require(_same(interpreter, {**software["python"], "path": str(root / "runtime/python")}), "runtime_changed")
    directory(root / ATTEMPT_DIRECTORY_NAME / "cache/pip", create=True)
    return {"version": _SELECTED_INTENT_VERSION, "plan": deepcopy(plan), "execution_directory": str(root),
        "policy": deepcopy(POLICY), "command": [interpreter["path"], "-B", "-S", "-m", WORKER_MODULE,
            str(root / "plan.json")], "environment": _selected_environment(root, software),
        "source_pins": pins, "interpreter": interpreter, "software": software}


def _snapshot(plan, policy, *, software=None):
    if software is not None:
        return _selected_snapshot(plan, policy, software)
    from .native_atac_differential_preparation import _source_closure, _dependencies, _copy_exact
    common, root, _ = _layout(plan)
    sources = _source_closure(Path(__file__).resolve().parents[1], [WORKER_MODULE])
    binary = Path(sys.executable).resolve(strict=True)
    home = Path(sys.base_prefix).resolve(strict=True)
    dependencies = _dependencies()
    _require(not any(_overlap(common, p) for p in [str(binary), str(home), *map(str, sources.values()),
        *[pin["path"] for row in dependencies for pin in row["files"]]]), "runtime_directory_overlap")
    pins = []
    for name, source in sorted(sources.items()):
        check_scratch_budget(common, policy, additional_bytes=source.stat().st_size)
        destination = confined_file(root, "source_snapshot/" + name.replace(".", "/") + ".py", create_parents=True)
        pins.append(_copy_exact(source, destination))
    check_scratch_budget(common, policy, additional_bytes=binary.stat().st_size)
    destination = confined_file(root, "runtime/python", create_parents=True)
    interpreter = _copy_exact(binary, destination, executable=True)
    stdlib = home / "lib" / ("python%d.%d" % sys.version_info[:2])
    runtime_files = [file_pin(path) for path in sorted(stdlib.rglob("*")) if path.is_file()
        and not any(part in ("site-packages", "dist-packages", "__pycache__") for part in path.relative_to(stdlib).parts)
        and path.suffix not in (".pyc", ".pyo")]
    _require(runtime_files, "stdlib_missing")
    directory(root / "cache/pip", create=True)
    return {"version": _INTENT_VERSION, "plan": deepcopy(plan), "execution_directory": str(root),
        "policy": deepcopy(POLICY), "command": [interpreter["path"], "-B", "-S", "-m", WORKER_MODULE,
            str(root / "plan.json")], "environment": _environment(root, common, str(home), dependencies),
        "source_pins": pins, "interpreter": interpreter, "dependencies": dependencies,
        "python_version": sys.version, "python_home": str(home), "runtime_files": runtime_files}


def _all_pins(intent):
    if intent["version"] == _SELECTED_INTENT_VERSION:
        return [*intent["source_pins"], intent["interpreter"],
            *intent["software"]["runtime_files"], *intent["software"]["solver_runtime_files"]]
    return [*intent["source_pins"], intent["interpreter"], *intent["runtime_files"],
        *(pin for row in intent["dependencies"] for pin in row["files"])]


def _validate_selected_intent(value, plan):
    _require(type(value) is dict and set(value) == {"version", "plan", "execution_directory", "policy",
        "command", "environment", "source_pins", "interpreter", "software"}
        and value["version"] == _SELECTED_INTENT_VERSION
        and _same(value["plan"], plan) and _same(value["policy"], POLICY), "intent_mismatch")
    software = validate_flux_balance_software(value["software"])
    _, root, _ = _layout(plan)
    _require(value["execution_directory"] == str(root) and value["command"] ==
        [str(root / "runtime/python"), "-B", "-S", "-m", WORKER_MODULE, str(root / "plan.json")], "intent_mismatch")
    _require(_same(value["source_pins"], _selected_source_pins(software, root))
        and _same(value["interpreter"], {**software["python"], "path": str(root / "runtime/python")}),
        "selected_runtime_mismatch")
    pins = [_pin(pin) for pin in _all_pins(value)]
    _require(len({pin["path"] for pin in pins}) == len(pins), "duplicate_pin")
    _require(_same(value["environment"], _selected_environment(root, software)), "environment_mismatch")
    return value


def _validate_intent(value, plan, *, software=None):
    if software is not None:
        selected = validate_flux_balance_software(software)
        _require(type(value) is dict and value.get("version") == _SELECTED_INTENT_VERSION
            and _same(value.get("software"), selected), "selected_software_mismatch")
    if type(value) is dict and value.get("version") == _SELECTED_INTENT_VERSION:
        return _validate_selected_intent(value, plan)
    _require(type(value) is dict and set(value) == {"version", "plan", "execution_directory", "policy",
        "command", "environment", "source_pins", "interpreter", "dependencies", "python_version",
        "python_home", "runtime_files"} and value["version"] == _INTENT_VERSION
        and _same(value["plan"], plan) and _same(value["policy"], POLICY), "intent_mismatch")
    common, root, _ = _layout(plan)
    path_value(value["python_home"], absolute=True)
    _require(type(value["python_version"]) is str and bool(value["python_version"]), "runtime_invalid")
    _require(value["execution_directory"] == str(root) and value["command"] ==
        [str(root / "runtime/python"), "-B", "-S", "-m", WORKER_MODULE, str(root / "plan.json")], "intent_mismatch")
    for field in ("source_pins", "runtime_files", "dependencies"):
        _require(type(value[field]) is list and bool(value[field]), "runtime_missing")
    names = []
    for row in value["dependencies"]:
        _require(type(row) is dict and set(row) == {"distribution", "version", "package_root", "files"}
            and all(type(row[k]) is str and bool(row[k]) for k in ("distribution", "version", "package_root"))
            and type(row["files"]) is list and bool(row["files"]), "dependency_invalid")
        path_value(row["package_root"], absolute=True)
        names.append(row["distribution"])
    _require(len(names) == len(set(names)), "dependency_invalid")
    pins = [_pin(pin) for pin in _all_pins(value)]
    _require(len({p["path"] for p in pins}) == len(pins), "duplicate_pin")
    source_root = root / "source_snapshot"
    _require(all(Path(p["path"]).is_relative_to(source_root) for p in value["source_pins"])
        and str(source_root / "gene_annotation_episode/flux_balance_result_worker.py") in
            {p["path"] for p in value["source_pins"]}
        and str(source_root / "gene_annotation_episode/__init__.py") in {p["path"] for p in value["source_pins"]}
        and value["interpreter"]["path"] == str(root / "runtime/python"), "source_missing")
    _require(all(Path(p["path"]).is_relative_to(Path(value["python_home"]) / "lib")
        for p in value["runtime_files"]), "runtime_invalid")
    _require(_same(value["environment"], _environment(root, common, value["python_home"], value["dependencies"])),
        "environment_mismatch")
    return value


def _verify_pins(intent):
    for pin in _all_pins(intent):
        _require(_same(file_pin(pin["path"]), pin), "runtime_changed")


def _controls(body, request, intent):
    common, root, output = _layout(intent["plan"])
    _require(type(body) is dict and body.get("version") == native.VERSION
        and body.get("stage") in ("prepared", "submitting", "released")
        and body.get("command") == intent["command"] and body.get("cwd") == str(common)
        and type(body.get("metadata")) is dict and _same(body["metadata"].get("policy"), POLICY)
        and body.get("stdout") == str(root / "worker.stdout") and body.get("stderr") == str(root / "worker.stderr"),
        "handle_mismatch")
    paths = body.get("paths")
    keys = {"request", "ready", "release", "status", "result", "launcher"}
    _require(type(paths) is dict and set(paths) == keys and all(type(p) is str for p in paths.values()), "handle_paths_invalid")
    for path in paths.values():
        path_value(path, absolute=True)
    token = Path(paths["request"]).name.removesuffix(".request")
    _require(re.fullmatch(r"\.local-job-[0-9a-f]{32}", token) is not None
        and paths == {name: str(common / (token + "." + name)) for name in keys}, "handle_paths_invalid")
    fixed = {str(root / name) for name in _CONTROL_NAMES} | {str(root), str(output)}
    _require(len(set(paths.values())) == len(paths) and not fixed.intersection(paths.values()), "handle_paths_invalid")
    expected = {"command": intent["command"], "cwd": str(common), "file_bytes": POLICY["scratch_bytes"],
        "ready_path": paths["ready"], "release_path": paths["release"], "result_path": paths["result"],
        "stdin_path": None, "env": intent["environment"]}
    _require(_same(request, expected), "request_mismatch")
    return body


def validate_flux_balance_worker_execution(value, *, plan, plan_file):
    """Validate original frozen execution records without current runtime I/O."""
    plan = validate_flux_balance_worker_plan(plan)
    _file(plan_file, PLAN_VERSION)
    _require(type(value) is dict and set(value) == {"version", "plan_file", "intent", "terminal", "quiescent",
        "policy", "returncode", "metadata", "failure", "handle_file", "request_file", "stdout_file", "stderr_file",
        "handle", "request", "request_raw"} and value["version"] == EXECUTION_VERSION
        and _same(value["plan_file"], plan_file) and value["terminal"] is True and value["quiescent"] is True
        and _same(value["policy"], POLICY), "execution_mismatch")
    for name, format_ in (("plan_file", PLAN_VERSION), ("handle_file", native.VERSION),
            ("request_file", "native_local_job_request"), ("stdout_file", "native_worker_stdout"),
            ("stderr_file", "native_worker_stderr")):
        _file(value[name], format_)
    intent = _validate_intent(value["intent"], plan)
    body = _controls(value["handle"], value["request"], intent)
    _require(type(value["request_raw"]) is str, "request_mismatch")
    raw = value["request_raw"].encode("utf-8")
    _require(_same(_json(raw), value["request"]) and hashlib.sha256(raw).hexdigest() ==
        body.get("request_sha256") == value["request_file"]["sha256"]
        and len(raw) == value["request_file"]["size_bytes"], "request_mismatch")
    meta = value["metadata"]
    _require(type(meta) is dict and _same(meta.get("policy"), POLICY) and type(meta.get("service_exit")) is dict
        and _same(meta.get("verified_cgroup"), _CGROUP), "allocation_mismatch")
    if value["failure"] is None:
        _require(type(value["returncode"]) is int and _same(meta.get("native_returncode"), value["returncode"]), "exit_mismatch")
    else:
        failure = value["failure"]
        _require(value["returncode"] is None and type(failure) is dict
            and set(failure) == {"code", "phase", "diagnostic", "operational"}
            and type(failure["code"]) is str and bool(failure["code"]), "exit_mismatch")
    canonical(value)
    return deepcopy(value)


def _retained_json(store, file, format_=None):
    return _json(read_bytes(retained_native_file(store, _file(file, format_))))


def validate_prepared_flux_balance_worker(store, value, *, plan):
    """Validate retained controls and output identities; never recalculate."""
    plan = validate_flux_balance_worker_plan(plan)
    _layout(plan)
    _require(type(value) is dict and set(value) == {"version", "plan_file", "execution_receipt_file",
        "worker_result_file", "result", "outputs", "failures"} and value["version"] == CAPTURE_VERSION,
        "capture_mismatch")
    _require(_same(_retained_json(store, value["plan_file"], PLAN_VERSION), plan), "plan_mismatch")
    execution = _retained_json(store, value["execution_receipt_file"], EXECUTION_VERSION)
    validate_flux_balance_worker_execution(execution, plan=plan, plan_file=value["plan_file"])
    _require(_same(_retained_json(store, execution["handle_file"], native.VERSION), execution["handle"]), "handle_mismatch")
    _require(read_bytes(retained_native_file(store, execution["request_file"])).decode("utf-8") == execution["request_raw"],
        "request_mismatch")
    for name in ("stdout_file", "stderr_file"):
        retained_native_file(store, execution[name])
    result = value["result"]
    if result is None:
        _require(value["outputs"] == [], "outputs_mismatch")
        if value["worker_result_file"] is not None:
            retained_native_file(store, _file(value["worker_result_file"], RESULT_VERSION))
    else:
        result = validate_flux_balance_worker_result(result)
        _require(_same(_retained_json(store, value["worker_result_file"], RESULT_VERSION), result)
            and result["plan_sha256"] == digest(plan) and result["mode"] == plan["mode"]
            and _same(result["selector"], plan["selector"]), "result_mismatch")
        _require(type(value["outputs"]) is list and len(value["outputs"]) == len(OUTPUTS), "outputs_mismatch")
        for declared, row in zip(result["outputs"], value["outputs"]):
            _require(type(row) is dict and set(row) == {"declared", "observed", "outcome", "failure"}
                and _same(row["declared"], declared["declaration"]), "outputs_mismatch")
            observed, declaration = row["observed"], row["declared"]
            if observed is not None:
                retained_native_file(store, _file(observed))
            equal = observed is not None and all(_same(observed[k], declaration[k]) for k in ("sha256", "size_bytes", "format"))
            _require((row["outcome"] == "verified" and declaration["state"] == "present" and equal and row["failure"] is None)
                or (row["outcome"] == "declared_absent" and declaration["state"] == "absent" and observed is None and row["failure"] is None)
                or (row["outcome"] == "unavailable" and declaration["state"] == "present" and observed is None and row["failure"] == "capture_file_unavailable")
                or (row["outcome"] == "digest_mismatch" and declaration["state"] == "present" and observed is not None and not equal
                    and row["failure"] == "capture_file_digest_mismatch"), "outputs_mismatch")
    _require(type(value["failures"]) is list, "failures_invalid")
    for issue in value["failures"]:
        checked = validate_flux_balance_record("Issue", issue)
        _require(checked["stage"] == "capture" and type(checked["field"]) is str
            and checked["field"].startswith("/worker/") and checked["code"] in
                ("binding_unavailable", "artifact_missing", "artifact_identity_conflict", "schema_invalid")
            and checked["detail_file"] is None and all(checked[k] is None for k in
                ("source_row_index", "reaction_position", "metabolite_position", "variable_position", "constraint_position")),
            "failures_invalid")
    canonical(value)
    return deepcopy(value)


def _capture(store, root, name, format_):
    return capture_native_file(store, directory=str(root), relative_path=name, format=format_)


def _validate_live_controls(handle, intent):
    common, root, _ = _layout(intent["plan"])
    body = _json(read_bytes(confined_file(root, "worker.handle.json")))
    _require(type(body) is dict and type(body.get("paths")) is dict
        and set(body["paths"]) == {"request", "ready", "release", "status", "result", "launcher"}
        and all(type(p) is str for p in body["paths"].values()), "handle_paths_invalid")
    for path in body["paths"].values():
        path_value(path, absolute=True)
        _require(Path(path).parent == common, "handle_paths_invalid")
        confined_file(common, Path(path).name)
    raw = read_bytes(confined_file(common, Path(body["paths"]["request"]).name))
    _controls(body, _json(raw), intent)
    _require(hashlib.sha256(raw).hexdigest() == body.get("request_sha256"), "request_mismatch")
    return body, raw


def prepare_flux_balance_result_worker(store, *, plan, policy, software=None):
    """Prepare, execute and capture this one finite selected worker operation."""
    plan = validate_flux_balance_worker_plan(plan)
    _require(type(policy) is LocalJobPolicy and _same(policy.to_dict(), POLICY), "policy_mismatch")
    if software is not None:
        software = validate_flux_balance_software(software)
    common, root, output = _layout(plan)
    directory(common, create=True)
    directory(root, create=True)
    for name in _CONTROL_NAMES:
        confined_file(root, name)
    with _locked(root):
        saved = _read_control(root, "capture.json")
        if saved is not None:
            if software is None:
                return validate_prepared_flux_balance_worker(store, saved, plan=plan)
            saved = validate_prepared_flux_balance_worker(store, saved, plan=plan)
            execution = _retained_json(store, saved["execution_receipt_file"], EXECUTION_VERSION)
            _validate_intent(execution["intent"], plan, software=software)
            return saved
        _immutable(root, "plan.json", plan)
        intent = _read_control(root, "intent.json")
        if intent is None:
            _require(not (root / "worker.handle.json").exists(), "unowned_handle")
            if output.exists() or output.is_symlink():
                directory(output)
                _require(not any(output.iterdir()), "unsealed_output")
            intent = (_validate_intent(_snapshot(plan, policy), plan) if software is None else
                _validate_intent(_snapshot(plan, policy, software=software), plan, software=software))
            _immutable(root, "intent.json", intent)
        else:
            intent = (_validate_intent(intent, plan) if software is None else
                _validate_intent(intent, plan, software=software))
        plan_file = _capture(store, root, "plan.json", PLAN_VERSION)
        execution = _read_control(root, "execution.json")
        handle = native.NativeJobHandle(root / "worker.handle.json")
        if execution is None:
            if not handle.path.exists():
                if output.exists() or output.is_symlink():
                    directory(output)
                    _require(not any(output.iterdir()), "unsealed_output")
                _require(not any(path.name.startswith(".local-job-") for path in common.iterdir()),
                    "unsealed_native_controls")
            _verify_pins(intent)
            if not handle.path.exists():
                native.prepare_job(intent["command"], cwd=common, policy=policy, handle_path=handle.path,
                    stdout_path=root / "worker.stdout", stderr_path=root / "worker.stderr", env=intent["environment"])
            _validate_live_controls(handle, intent)
            native.resume_start(handle)
            result, failure = None, None
            try:
                result = native.wait_job(handle)
            except AcquisitionError as error:
                view = native.status(handle)
                if not view["terminal"] or not view["quiescent"]:
                    raise
                failure = {"code": error.code, "phase": error.phase, "diagnostic": error.diagnostic, "operational": error.operational}
            view = native.status(handle)
            _require(view["terminal"] and view["quiescent"], "worker_not_closed")
            _verify_pins(intent)
            body, raw = _validate_live_controls(handle, intent)
            execution = {"version": EXECUTION_VERSION, "plan_file": plan_file, "intent": intent,
                "terminal": True, "quiescent": True, "policy": deepcopy(POLICY),
                "returncode": result.returncode if result is not None else None, "metadata": view["metadata"],
                "failure": failure, "handle_file": _capture(store, root, "worker.handle.json", native.VERSION),
                "request_file": _capture(store, common, Path(body["paths"]["request"]).name, "native_local_job_request"),
                "stdout_file": _capture(store, root, "worker.stdout", "native_worker_stdout"),
                "stderr_file": _capture(store, root, "worker.stderr", "native_worker_stderr"),
                "handle": body, "request": _json(raw), "request_raw": raw.decode("utf-8")}
            validate_flux_balance_worker_execution(execution, plan=plan, plan_file=plan_file)
            _immutable(root, "execution.json", execution)
        else:
            validate_flux_balance_worker_execution(execution, plan=plan, plan_file=plan_file)
        execution_file = _capture(store, root, "execution.json", EXECUTION_VERSION)
        failures, result, result_file, outputs = [], None, None, []
        if execution["failure"] is not None or execution["returncode"] != 0:
            failures.append(_issue("binding_unavailable", "/worker/execution"))
        try:
            result_file = _capture(store, output, "worker-result.json", RESULT_VERSION)
            result = validate_flux_balance_worker_result(_retained_json(store, result_file, RESULT_VERSION))
            _require(result["plan_sha256"] == digest(plan) and result["mode"] == plan["mode"]
                and _same(result["selector"], plan["selector"]), "result_mismatch")
        except NativeFileCaptureError as error:
            if error.code != "capture_file_unavailable":
                raise
            failures.append(_issue("artifact_missing", "/worker/result"))
        except (ValueError, KeyError, TypeError, UnicodeError, OverflowError, RecursionError) as error:
            result = None
            failures.append(_issue("artifact_identity_conflict" if str(error) == "fba_preparation_result_mismatch"
                else "schema_invalid", "/worker/result"))
        if result is not None:
            outputs = capture_declared_native_files(store, directory=str(output),
                declarations=[row["declaration"] for row in result["outputs"]])
            for spec, captured in zip(OUTPUTS, outputs):
                if captured["outcome"] not in ("verified", "declared_absent"):
                    failures.append(_issue("artifact_identity_conflict" if captured["outcome"] == "digest_mismatch"
                        else "artifact_missing", "/worker/outputs/" + spec[0]))
        value = validate_prepared_flux_balance_worker(store, {"version": CAPTURE_VERSION,
            "plan_file": plan_file, "execution_receipt_file": execution_file, "worker_result_file": result_file,
            "result": result, "outputs": outputs, "failures": _unique(failures)}, plan=plan)
        _immutable(root, "capture.json", value)
        return value
