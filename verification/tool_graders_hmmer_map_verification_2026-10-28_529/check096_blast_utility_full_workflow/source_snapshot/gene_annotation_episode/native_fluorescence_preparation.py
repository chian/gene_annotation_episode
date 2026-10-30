"""One bounded, durable fluorescence result-worker reservation and capture.

The host freezes the real finite worker closure and resumes its original native
handle. Historical validation authenticates saved controls without requiring
today's interpreter, scientific inputs, or producer directory.
"""
from copy import deepcopy
import ast
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import sys

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .fluorescence_execution_common import canonical, closed, digest, identity, require, same, unique, validate_failure
from .fluorescence_result_contracts import (OUTPUTS, PLAN_VERSION, RESULT_VERSION, failure,
    validate_file, validate_path, validate_fluorescence_worker_plan, validate_fluorescence_worker_result)
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_fluorescence_contracts import POLICY
from .native_fluorescence_storage import directory, file_pin, immutable_json, read_json, regular, decode_json
from .native_file_capture import NativeFileCaptureError, capture_native_file, capture_declared_native_files, retained_native_file
from .native_atac_differential_preparation import _source_closure, _copy_exact

WORKER_MODULE = "gene_annotation_episode.fluorescence_result_worker"
INTENT_VERSION = "fluorescence_worker_intent_v1"
EXECUTION_VERSION = "fluorescence_worker_execution_v1"
CAPTURE_VERSION = "fluorescence_worker_capture_v1"


def build_native_fluorescence_worker_plan(*, directory, original_plan, capture, selector):
    return validate_fluorescence_worker_plan(dict(version=PLAN_VERSION, mode="native_result", directory=directory,
        original_plan=original_plan, capture=capture, selector=selector))


def build_saved_fluorescence_worker_plan(*, directory, sheet, selector):
    return validate_fluorescence_worker_plan(dict(version=PLAN_VERSION, mode="saved_sheet_recalculation",
        directory=directory, sheet=sheet, selector=selector))


def _dependencies(sources):
    """Discover the actual pure closure; no fixed scientific package selector.

    This worker currently imports stdlib only. A future external import needs
    an explicit pinned dependency binding before it can be executed here.
    """
    stdlib = sys.stdlib_module_names | {"__future__"}
    for path in sources.values():
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import) else
                [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else [])
            for name in names:
                require(name.split(".")[0] in stdlib or name.startswith("gene_annotation_episode."),
                        "fluorescence_worker_dependency_unbound")
    return []


def _environment(root, home, dependencies):
    roots = []
    for row in dependencies:
        path = str(Path(row["package_root"]).parent)
        if path not in roots:
            roots.append(path)
    return dict(PYTHONPATH=os.pathsep.join([str(root / "source_snapshot"), *roots]), PYTHONHOME=home,
        PYTHONNOUSERSITE="1", PYTHONSAFEPATH="1", PYTHONDONTWRITEBYTECODE="1",
        TMPDIR=str(root), TMP=str(root), TEMP=str(root), XDG_CACHE_HOME=str(root / "cache"),
        PIP_CACHE_DIR=str(root / "cache/pip"))


def _snapshot(plan, policy):
    root = Path(plan["directory"])
    sources = _source_closure(Path(__file__).resolve().parents[1], [WORKER_MODULE])
    dependencies = _dependencies(sources)
    pins = []
    for name, source in sorted(sources.items()):
        check_scratch_budget(root, policy, additional_bytes=source.stat().st_size)
        pins.append(_copy_exact(source, root / "source_snapshot" / (name.replace(".", "/") + ".py")))
    binary = Path(sys.executable).resolve(strict=True)
    check_scratch_budget(root, policy, additional_bytes=binary.stat().st_size)
    interpreter = _copy_exact(binary, root / "runtime/python", executable=True)
    home = Path(sys.base_prefix).resolve(strict=True)
    stdlib = home / "lib" / ("python%d.%d" % sys.version_info[:2])
    runtime_files = [file_pin(path) for path in sorted(stdlib.rglob("*")) if path.is_file()
        and not any(part in ("site-packages", "dist-packages", "__pycache__") for part in path.relative_to(stdlib).parts)
        and path.suffix not in (".pyc", ".pyo")]
    require(runtime_files, "fluorescence_worker_stdlib_missing")
    (root / "cache/pip").mkdir(parents=True, exist_ok=True)
    return dict(version=INTENT_VERSION, plan=plan, policy=deepcopy(POLICY),
        command=[interpreter["path"], "-B", "-S", "-m", WORKER_MODULE, str(root / "plan.json")],
        environment=_environment(root, str(home), dependencies), source_pins=pins, interpreter=interpreter,
        dependencies=dependencies, python_version=sys.version, python_home=str(home), runtime_files=runtime_files)


def _pin(value):
    closed(value, ("path", "sha256", "size_bytes"))
    validate_path(value["path"])
    validate_file(dict(artifact_ref="artifact_" + str(value["sha256"]), sha256=value["sha256"],
        size_bytes=value["size_bytes"], format="runtime_file"))


def _validate_intent(intent, plan):
    closed(intent, ("version", "plan", "policy", "command", "environment", "source_pins", "interpreter",
        "dependencies", "python_version", "python_home", "runtime_files"))
    require(intent["version"] == INTENT_VERSION and same(intent["plan"], plan) and same(intent["policy"], POLICY),
            "worker_execution_mismatch")
    root = Path(plan["directory"])
    require(intent["command"] == [str(root / "runtime/python"), "-B", "-S", "-m", WORKER_MODULE, str(root / "plan.json")],
            "worker_execution_mismatch")
    require(type(intent["source_pins"]) is list and intent["source_pins"] and type(intent["runtime_files"]) is list
        and intent["runtime_files"] and type(intent["dependencies"]) is list, "worker_execution_mismatch")
    validate_path(intent["python_home"])
    require(type(intent["python_version"]) is str and bool(intent["python_version"]), "worker_execution_mismatch")
    distributions = set()
    for row in intent["dependencies"]:
        closed(row, ("distribution", "version", "package_root", "files"))
        require(type(row["distribution"]) is str and row["distribution"] and type(row["version"]) is str and row["version"]
            and type(row["files"]) is list and row["files"], "worker_execution_mismatch")
        name = re.sub(r"[-_.]+", "-", row["distribution"]).lower()
        require(name not in distributions, "worker_execution_mismatch")
        distributions.add(name)
        validate_path(row["package_root"])
        require(any(Path(pin["path"]).is_relative_to(row["package_root"]) for pin in row["files"]), "worker_execution_mismatch")
    pins = [*intent["source_pins"], intent["interpreter"], *intent["runtime_files"],
        *(pin for row in intent["dependencies"] for pin in row["files"])]
    for pin in pins:
        _pin(pin)
    require(len({pin["path"] for pin in pins}) == len(pins), "worker_execution_mismatch")
    require(intent["interpreter"]["path"] == str(root / "runtime/python"), "worker_execution_mismatch")
    source_root = root / "source_snapshot"
    require(all(Path(pin["path"]).is_relative_to(source_root) and Path(pin["path"]).suffix == ".py" for pin in intent["source_pins"])
        and str(source_root / "gene_annotation_episode/fluorescence_result_worker.py") in {pin["path"] for pin in intent["source_pins"]},
        "worker_execution_mismatch")
    require(all(Path(pin["path"]).is_relative_to(Path(intent["python_home"]) / "lib") for pin in intent["runtime_files"])
        and same(intent["environment"], _environment(root, intent["python_home"], intent["dependencies"])), "worker_execution_mismatch")
    return deepcopy(intent)


def _verify_pins(intent):
    for pin in [*intent["source_pins"], intent["interpreter"], *intent["runtime_files"],
            *(pin for row in intent["dependencies"] for pin in row["files"])]:
        require(same(file_pin(pin["path"]), pin), "worker_execution_mismatch")


def _capture(store, root, name, format_):
    return capture_native_file(store, directory=str(root), relative_path=name, format=format_)


def _controls(body, request, intent):
    root = Path(intent["plan"]["directory"])
    closed(body, ("version", "unit", "command", "cwd", "stdout", "stderr", "paths", "metadata", "stage",
        "started_at", "started_monotonic_ns", "boot_id", "request_sha256"))
    require(body["version"] == native.VERSION and same(body["command"], intent["command"])
        and body["cwd"] == str(root) and body["stage"] in ("prepared", "submitting", "released")
        and body["stdout"] == str(root / "worker.stdout") and body["stderr"] == str(root / "worker.stderr"),
        "worker_execution_mismatch")
    require(type(body["unit"]) is str and re.fullmatch(r"gene-local-job-[0-9a-f]{32}\.service", body["unit"])
        and type(body["request_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", body["request_sha256"]), "worker_execution_mismatch")
    metadata = body["metadata"]
    base = native._metadata(LocalJobPolicy(**POLICY))
    require(type(metadata) is dict and same({key: metadata.get(key) for key in base}, base)
        and set(metadata) <= set(base) | {"verified_cgroup"}, "worker_execution_mismatch")
    paths = body["paths"]
    closed(paths, ("request", "ready", "release", "status", "result", "launcher"))
    require(all(type(path) is str and Path(path).parent == root and str(Path(path)) == path for path in paths.values()),
            "worker_execution_mismatch")
    request_name = Path(paths["request"]).name
    require(re.fullmatch(r"\.local-job-[0-9a-f]{32}\.request", request_name), "worker_execution_mismatch")
    token = request_name.removesuffix(".request")
    require(all(path == str(root / (token + "." + name)) for name, path in paths.items()), "worker_execution_mismatch")
    require(same(request, dict(command=intent["command"], cwd=str(root), file_bytes=POLICY["scratch_bytes"],
        ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"], stdin_path=None,
        env=intent["environment"])), "worker_execution_mismatch")
    if body["stage"] == "prepared":
        require(all(body[name] is None for name in ("started_at", "started_monotonic_ns", "boot_id")), "worker_execution_mismatch")
    else:
        require(type(body["started_at"]) is str and bool(body["started_at"])
            and type(body["started_monotonic_ns"]) is int and body["started_monotonic_ns"] >= 0
            and type(body["boot_id"]) is str and bool(body["boot_id"]), "worker_execution_mismatch")
    return body


def validate_fluorescence_worker_execution(execution, *, plan, plan_file):
    plan = validate_fluorescence_worker_plan(plan)
    closed(execution, ("version", "plan_file", "intent", "terminal", "quiescent", "policy", "returncode",
        "metadata", "failure", "handle_file", "request_file", "stdout_file", "stderr_file", "handle", "request", "request_raw"))
    require(execution["version"] == EXECUTION_VERSION and same(execution["plan_file"], plan_file)
        and same(plan_file, identity(canonical(plan) + b"\n", format=PLAN_VERSION))
        and execution["terminal"] is True and execution["quiescent"] is True and same(execution["policy"], POLICY),
        "worker_execution_mismatch")
    intent = _validate_intent(execution["intent"], plan)
    body = _controls(execution["handle"], execution["request"], intent)
    require(type(execution["request_raw"]) is str, "worker_execution_mismatch")
    raw = execution["request_raw"].encode("utf-8")
    require(same(decode_json(raw), execution["request"]) and hashlib.sha256(raw).hexdigest() == body["request_sha256"]
        == execution["request_file"]["sha256"] and len(raw) == execution["request_file"]["size_bytes"], "worker_execution_mismatch")
    formats = dict(plan_file=PLAN_VERSION, handle_file=native.VERSION, request_file="native_local_job_request",
        stdout_file="native_worker_stdout", stderr_file="native_worker_stderr")
    for name, format_ in formats.items():
        require(validate_file(execution[name])["format"] == format_, "worker_execution_mismatch")
    meta = execution["metadata"]
    expected_limits = {"memory_max": POLICY["memory_bytes"], "memory_swap_max": 0,
        "runtime_max": "infinity", "kill_mode": "control-group", "oom_policy": "kill"}
    require(type(meta) is dict and same(meta.get("policy"), POLICY) and type(meta.get("service_exit")) is dict
        and same(meta.get("verified_cgroup"), expected_limits) and same(body["metadata"].get("verified_cgroup"), expected_limits)
        and all(same(meta.get(key), value) for key, value in body["metadata"].items())
        and meta.get("duration_measure") == "systemd_service_wall_seconds", "worker_execution_mismatch")
    if execution["failure"] is None:
        require(type(execution["returncode"]) is int and meta.get("native_returncode") == execution["returncode"]
            and body["stage"] == "released", "worker_execution_mismatch")
    else:
        closed(execution["failure"], ("code", "phase", "diagnostic", "operational"))
        problem = execution["failure"]
        require(execution["returncode"] is None and all(type(problem[key]) is str and problem[key] for key in ("code", "phase"))
            and type(problem["operational"]) is dict and (problem["diagnostic"] is None or type(problem["diagnostic"]) is dict),
            "worker_execution_mismatch")
    canonical(execution)
    return deepcopy(execution)


def _validate_result_plan(result, plan):
    result = validate_fluorescence_worker_result(result)
    expected = ([row["source"]["file"] for row in plan["original_plan"]["requested_job"]["native_fluorescence"]["inputs"]]
        if plan["mode"] == "native_result" else [plan["sheet"]["file"]])
    require(result["plan_sha256"] == digest(plan) and same(result["selector"], plan["selector"])
        and result["mode"] == plan["mode"] and same(result["input_identities"], expected), "worker_execution_mismatch")
    return result


def validate_prepared_fluorescence_worker(store, value, *, plan):
    plan = validate_fluorescence_worker_plan(plan)
    closed(value, ("version", "plan_file", "execution_receipt_file", "worker_result_file", "result", "outputs", "failures"))
    require(value["version"] == CAPTURE_VERSION, "worker_execution_mismatch")
    require(same(read_json(retained_native_file(store, value["plan_file"])), plan), "worker_execution_mismatch")
    require(validate_file(value["execution_receipt_file"])["format"] == EXECUTION_VERSION, "worker_execution_mismatch")
    execution = read_json(retained_native_file(store, value["execution_receipt_file"]))
    validate_fluorescence_worker_execution(execution, plan=plan, plan_file=value["plan_file"])
    require(same(read_json(retained_native_file(store, execution["handle_file"])), execution["handle"]), "worker_execution_mismatch")
    require(retained_native_file(store, execution["request_file"]).read_bytes().decode("utf-8") == execution["request_raw"],
            "worker_execution_mismatch")
    for name in ("stdout_file", "stderr_file"):
        retained_native_file(store, execution[name])
    if value["worker_result_file"] is not None:
        require(validate_file(value["worker_result_file"])["format"] == RESULT_VERSION, "worker_execution_mismatch")
        result_path = retained_native_file(store, value["worker_result_file"])
    else:
        result_path = None
    result = value["result"]
    require(type(value["outputs"]) is list and type(value["failures"]) is list, "worker_execution_mismatch")
    expected_failures = []
    if execution["failure"] is not None or execution["returncode"] != 0:
        expected_failures.append(failure("worker_resource_failure" if execution["failure"] is not None
            and execution["failure"]["code"] == "local_job_resource_limit" else "worker_nonzero_exit", "worker"))
    if result is None:
        require(value["outputs"] == [], "worker_execution_mismatch")
        expected_failures.append(failure("worker_output_unavailable" if result_path is None else "worker_output_malformed",
            "worker", role="worker_result"))
        if result_path is not None:
            try:
                _validate_result_plan(read_json(result_path), plan)
            except (ValueError, KeyError, TypeError):
                pass
            else:
                require(False, "worker_execution_mismatch")
    else:
        require(result_path is not None, "worker_execution_mismatch")
        result = _validate_result_plan(result, plan)
        require(same(read_json(result_path), result) and len(value["outputs"]) == len(OUTPUTS), "worker_execution_mismatch")
        for declared, captured, spec in zip(result["outputs"], value["outputs"], OUTPUTS):
            closed(captured, ("declared", "observed", "outcome", "failure"))
            require(same(captured["declared"], declared["declaration"]), "worker_execution_mismatch")
            d, observed = captured["declared"], captured["observed"]
            if observed is not None:
                retained_native_file(store, observed)
            equal = observed is not None and all(observed[key] == d[key] for key in ("sha256", "size_bytes", "format"))
            state = captured["outcome"]
            require((state == "verified" and d["state"] == "present" and equal and captured["failure"] is None)
                or (state == "declared_absent" and d["state"] == "absent" and observed is None and captured["failure"] is None)
                or (state == "unavailable" and d["state"] == "present" and observed is None and captured["failure"] == "capture_file_unavailable")
                or (state == "digest_mismatch" and d["state"] == "present" and observed is not None and not equal
                    and captured["failure"] == "capture_file_digest_mismatch"), "worker_execution_mismatch")
            if captured["failure"] is not None:
                expected_failures.append(failure(captured["failure"], "capture", role=spec[0]))
    for row in value["failures"]:
        validate_failure(row)
    require(same(value["failures"], unique(expected_failures)), "worker_execution_mismatch")
    return deepcopy(value)


def _operand_paths(store, plan):
    retained = ([plan["sheet"]] if plan["mode"] == "saved_sheet_recalculation" else
        [row["retained"] for row in plan["capture"]["files"] if row["retained"] is not None])
    for row in retained:
        file = validate_file(row["file"])
        metadata = store._require(file["artifact_ref"], {"artifact"})
        require(metadata["sha256"] == file["sha256"] and metadata["size"] == file["size_bytes"]
            and row["path"] == str(store.path / "artifacts" / file["sha256"][:2] / file["sha256"]),
            "worker_execution_mismatch")
    # Bytes are checked by the finite worker. A missing captured operand must
    # preserve other supplied data through its typed worker failure.


def prepare_fluorescence_result_worker(store, *, plan, policy):
    plan = validate_fluorescence_worker_plan(plan)
    require(type(policy) is LocalJobPolicy and same(policy.to_dict(), POLICY), "worker_execution_mismatch")
    root = directory(plan["directory"])
    root.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(root / ".preparation.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), "a+b") as lock:
        require(stat.S_ISREG(os.fstat(lock.fileno()).st_mode), "worker_execution_mismatch")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        saved = root / "capture.json"
        if saved.exists():
            return validate_prepared_fluorescence_worker(store, read_json(saved), plan=plan)
        immutable_json(root / "plan.json", plan)
        intent_path = root / "intent.json"
        if intent_path.exists():
            intent = _validate_intent(read_json(intent_path), plan)
        else:
            require(not (root / "worker.handle.json").exists(), "worker_execution_mismatch")
            _operand_paths(store, plan)
            intent = _validate_intent(_snapshot(plan, policy), plan)
            immutable_json(intent_path, intent)
        plan_file = _capture(store, root, "plan.json", PLAN_VERSION)
        execution_path = root / "execution.json"
        handle = native.NativeJobHandle(root / "worker.handle.json")
        if not execution_path.exists():
            _verify_pins(intent)
            if not handle.path.exists():
                native.prepare_job(intent["command"], cwd=root, policy=policy, handle_path=handle.path,
                    stdout_path=root / "worker.stdout", stderr_path=root / "worker.stderr", env=intent["environment"])
            body = handle.read()
            _controls(body, read_json(body["paths"]["request"]), intent)
            require(file_pin(body["paths"]["request"])["sha256"] == body["request_sha256"], "worker_execution_mismatch")
            native.resume_start(handle)
            result, problem = None, None
            try:
                result = native.wait_job(handle)
            except AcquisitionError as error:
                view = native.status(handle)
                if not view["terminal"] or not view["quiescent"]:
                    raise
                problem = dict(code=error.code, phase=error.phase, diagnostic=error.diagnostic, operational=error.operational)
            view = native.status(handle)
            require(view["terminal"] and view["quiescent"], "worker_execution_mismatch")
            _verify_pins(intent)
            body = handle.read()
            with regular(body["paths"]["request"]) as stream:
                request_raw = stream.read().decode("utf-8")
            execution = dict(version=EXECUTION_VERSION, plan_file=plan_file, intent=intent,
                terminal=True, quiescent=True, policy=deepcopy(POLICY), returncode=result.returncode if result else None,
                metadata=view["metadata"], failure=problem,
                handle_file=_capture(store, root, "worker.handle.json", native.VERSION),
                request_file=_capture(store, root, Path(body["paths"]["request"]).name, "native_local_job_request"),
                stdout_file=_capture(store, root, "worker.stdout", "native_worker_stdout"),
                stderr_file=_capture(store, root, "worker.stderr", "native_worker_stderr"),
                handle=body, request=decode_json(request_raw), request_raw=request_raw)
            validate_fluorescence_worker_execution(execution, plan=plan, plan_file=plan_file)
            immutable_json(execution_path, execution)
        execution = read_json(execution_path)
        validate_fluorescence_worker_execution(execution, plan=plan, plan_file=plan_file)
        execution_file = _capture(store, root, "execution.json", EXECUTION_VERSION)
        failures, result, result_file, outputs = [], None, None, []
        if execution["failure"] is not None or execution["returncode"] != 0:
            failures.append(failure("worker_resource_failure" if execution["failure"] is not None
                and execution["failure"]["code"] == "local_job_resource_limit" else "worker_nonzero_exit", "worker"))
        try:
            result_file = _capture(store, root, "worker-result.json", RESULT_VERSION)
            result = _validate_result_plan(read_json(retained_native_file(store, result_file)), plan)
        except NativeFileCaptureError as error:
            if error.code != "capture_file_unavailable":
                raise
            failures.append(failure("worker_output_unavailable", "worker", role="worker_result"))
        except (ValueError, KeyError, TypeError):
            result = None
            failures.append(failure("worker_output_malformed", "worker", role="worker_result"))
        if result is not None:
            outputs = capture_declared_native_files(store, directory=str(root), declarations=[row["declaration"] for row in result["outputs"]])
            for spec, row in zip(OUTPUTS, outputs):
                if row["failure"] is not None:
                    failures.append(failure(row["failure"], "capture", role=spec[0]))
        value = validate_prepared_fluorescence_worker(store, dict(version=CAPTURE_VERSION, plan_file=plan_file,
            execution_receipt_file=execution_file, worker_result_file=result_file, result=result, outputs=outputs,
            failures=unique(failures)), plan=plan)
        immutable_json(saved, value)
        return value
