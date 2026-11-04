"""Retain preparation numbers and publish exactly the requested saved facts.

Capture must already be sealed. Native files never reopen here, and the host
never hydrates a full numerical sheet. Separate bounded workers grade retained
bytes or select retained values. Neither path creates an observation or credit.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .domain import ContractError, canonical, validate_schema
from .hmmer_preparation_result_views import (
    ARTIFACT_SCHEMA, POPULATION_SCHEMA, ROW_SCHEMA, validate_preparation_result_selector,
)
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job
from .native_infernal_contracts import finite_json_copy, native_infernal_digest
from .native_hmmer_preparation_acquisition import (
    _capture_file, _decode, _directory, _read_record, _retained, _shape, _validate_rows,
    capture_local_bundle, original_source_payload, validate_original_bundle,
)
from .native_hmmer_preparation_result_worker import (
    MANIFEST_VERSION, NUMERICAL_FILES, PLAN_VERSION, PREFIX, effective_metadata,
    eligible_occurrences, grading_context, exception_code, exception_diagnostic, failure,
    qualified_occurrences, unique_failures, validate_failures,
)
from .practical_execution_state import _immutable
from .tool_grading_artifacts import retain_tool_grading


PREPARED_VERSION = PREFIX + "prepared_v1"
RETAINED_VERSION = PREFIX + "retained_grading_v1"
_NUMERICAL = ("grading_artifact_ref", "sheet_artifact_ref", "calculations_artifact_ref")
_PREPARED_FIELDS = {"version", "bundle_artifact_ref", "source_grading_artifact_ref",
    *_NUMERICAL, "occurrences", "failures", "graded"}
_STABLE_FIELDS = {"schema", "original_plan", "capture", "bundle_sha256", "original_parameters",
    "effective_metadata", "grading_context", "occurrences", *_NUMERICAL, "numerical_artifacts", "failures", "graded"}
_PUBLICATION_FIELDS = {"record_refs", "rows", "artifacts", "population", "failures", "projection_artifact_ref"}
_WORKER_MODULE = "gene_annotation_episode.native_hmmer_preparation_result_worker"
_VERIFY_MODULE = "gene_annotation_episode.native_atac_differential_driver"
_WORKER_SELECTION = PREFIX + "worker_execution_v1"
_WORKER_PROGRAM = (
    "import json,sys\n"
    "from pathlib import Path\n"
    "from gene_annotation_episode.native_atac_differential_driver import verify_driver_runtime\n"
    "with open(sys.argv[1]) as stream:\n"
    "    selected=json.load(stream)\n"
    "with open(selected['runtime_path']) as stream:\n"
    "    runtime=json.load(stream)\n"
    "if runtime['data_files'] != []:\n"
    "    raise ValueError('original_worker_required_data_conflict')\n"
    "if sys.prefix != selected['python_home']:\n"
    "    raise ValueError('original_worker_python_home_conflict')\n"
    "verify_driver_runtime(selected['driver_runtime'])\n"
    "from gene_annotation_episode.native_infernal_contracts import native_infernal_digest\n"
    "root=Path(sys.argv[1]).parent\n"
    "with open(root/'original-handle.json') as stream:\n"
    "    binding=json.load(stream)\n"
    "with open(sys.argv[2]) as stream:\n"
    "    plan=json.load(stream)\n"
    "with open(root/'intent.json') as stream:\n"
    "    intent=json.load(stream)\n"
    "if (native_infernal_digest(selected) != binding['selection_sha256'] or "
    "native_infernal_digest(runtime) != selected['runtime_sha256'] or "
    "native_infernal_digest(plan) != selected['plan_sha256'] or "
    "native_infernal_digest(intent) != selected['intent_sha256']):\n"
    "    raise ValueError('original_worker_operands_conflict')\n"
    "from gene_annotation_episode.native_hmmer_preparation_result_worker import main\n"
    "raise SystemExit(main([sys.argv[2]]))\n"
)


class HmmerPreparationWorkerPending(RuntimeError):
    """The selected original phase has no terminal result to publish yet."""
    def __init__(self, directory, *, observation=None, failure=None):
        super().__init__(PREFIX + "result_worker_pending")
        self.handle_path = Path(directory) / "native-handle.json"
        self.observation = deepcopy(observation)
        self.failure = deepcopy(failure)


def _error(code):
    raise ContractError(PREFIX + code)


def _artifact_path(store, reference, *, verify=True):
    row = _retained(store, reference) if verify else store._require(reference, {"artifact"})
    if reference != "artifact_" + row["sha256"] or type(row["size"]) is not int or row["size"] < 0:
        _error("retained_artifact_identity_conflict")
    return store.path / "artifacts" / row["sha256"][:2] / row["sha256"]


def _descriptor(store, reference):
    row = store._require(reference, {"artifact"})
    return {"artifact_ref": reference, "sha256": row["sha256"], "size_bytes": row["size"]}


def _worker_file(store, reference):
    descriptor = _descriptor(store, reference)
    return {"path": str(_artifact_path(store, reference)),
            **{k: descriptor[k] for k in ("sha256", "size_bytes")}}


def _prepared(bundle_ref=None, *, failures=()):
    return {"version": PREPARED_VERSION, "bundle_artifact_ref": bundle_ref,
        "source_grading_artifact_ref": None, **{k: None for k in _NUMERICAL},
        "occurrences": [], "failures": list(failures), "graded": False}


def _prepared_shape(value):
    prepared = finite_json_copy(value)
    if (type(prepared) is not dict or set(prepared) != _PREPARED_FIELDS
            or prepared["version"] != PREPARED_VERSION or type(prepared["graded"]) is not bool
            or type(prepared["occurrences"]) is not list):
        _error("prepared_grading_invalid")
    validate_failures(prepared["failures"])
    for key in ("bundle_artifact_ref", "source_grading_artifact_ref", *_NUMERICAL):
        if prepared[key] is not None and (type(prepared[key]) is not str or not prepared[key]):
            _error("prepared_grading_reference_invalid")
    return prepared


def _stable(store, prepared):
    reference = prepared["source_grading_artifact_ref"]
    if reference is None:
        _error("source_grading_required")
    _artifact_path(store, reference)
    envelope = _decode(store.get_artifact(reference))
    if (type(envelope) is not dict or set(envelope) != {"schema", "provider", "native_artifact_ref", "grading"}
            or envelope["schema"] != "tool_grading_artifact_v1"
            or envelope["provider"] != "episode.execution_result"
            or envelope["native_artifact_ref"] != prepared["bundle_artifact_ref"]):
        _error("source_grading_custody_conflict")
    stable = envelope["grading"]
    if type(stable) is not dict or set(stable) != _STABLE_FIELDS or stable["schema"] != RETAINED_VERSION:
        _error("source_grading_envelope_invalid")
    return stable


def validate_prepared_grading(store, prepared, *, bundle, verify_files=True):
    """Validate small custody records and stream byte checks; never parse a sheet."""
    prepared = _prepared_shape(prepared)
    if type(verify_files) is not bool:
        _error("verify_files_boolean_required")
    stable = _stable(store, prepared)
    bundle = validate_original_bundle(bundle, stable["original_plan"])
    _artifact_path(store, prepared["bundle_artifact_ref"], verify=verify_files)
    retained_bundle = _decode(store.get_artifact(prepared["bundle_artifact_ref"]))
    if (retained_bundle != bundle or stable["bundle_sha256"] != native_infernal_digest(bundle)
            or any(native_infernal_digest(stable[k]) != native_infernal_digest(prepared[k])
                   for k in (*_NUMERICAL, "occurrences", "failures", "graded"))):
        _error("prepared_grading_identity_conflict")
    capture = _shape(stable["capture"])
    if verify_files:
        _validate_rows(store, capture, bundle)
    occurrences, custody_failures = qualified_occurrences(bundle, prepared["bundle_artifact_ref"], capture)
    # A saved publication keeps its original interpretation. Absence of this
    # optional field is historical absence, never permission to upgrade it.
    metadata, metadata_failures = effective_metadata(bundle, occurrences,
        include_map_context="map_reconstruction_context" in stable["effective_metadata"])
    if (native_infernal_digest(occurrences) != native_infernal_digest(prepared["occurrences"])
            or native_infernal_digest(stable["effective_metadata"]) != native_infernal_digest(metadata)
            or native_infernal_digest(stable["grading_context"]) != native_infernal_digest(grading_context(bundle, occurrences, metadata))
            or native_infernal_digest(stable["original_parameters"]) != native_infernal_digest(bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"])
            or any(r not in prepared["failures"] for r in [*custody_failures, *metadata_failures])):
        _error("prepared_grading_custody_conflict")
    for occurrence in occurrences:
        _artifact_path(store, occurrence["artifact_ref"], verify=verify_files)
        if _descriptor(store, occurrence["artifact_ref"]) != {k: occurrence[k] for k in ("artifact_ref", "sha256", "size_bytes")}:
            _error("prepared_occurrence_bytes_conflict")
    numerical = stable["numerical_artifacts"]
    if type(numerical) is not dict or set(numerical) != {k.removesuffix("_artifact_ref") for k in _NUMERICAL if prepared[k] is not None}:
        _error("prepared_numerical_artifact_population_conflict")
    for role, descriptor in numerical.items():
        reference = prepared[role + "_artifact_ref"]
        if native_infernal_digest(descriptor) != native_infernal_digest(_descriptor(store, reference)):
            _error("prepared_numerical_artifact_identity_conflict")
        _artifact_path(store, reference, verify=verify_files)
    if prepared["graded"] and any(prepared[k] is None for k in _NUMERICAL):
        _error("prepared_graded_artifacts_missing")
    return prepared


def _begin(directory, name, intent, receipt, *, failure_receipt=None):
    directory = _directory(directory) / name
    if directory.exists():
        if _read_record(directory, "intent.json") != intent:
            _error(name.replace("-", "_") + "_directory_identity_conflict")
        if failure_receipt and (directory / failure_receipt).is_file():
            if (directory / receipt).exists():
                _error("projection_success_failure_conflict")
            return directory, {"_failure": _read_record(directory, failure_receipt)}
        if not (directory / receipt).is_file():
            # A matching directory alone never licenses replacement work. The
            # original sealed plan, runtime and existing durable handle must all
            # authenticate before its pending phase can be resumed.
            task = {"native-hmmer-preparation-grading": "grade",
                    "native-hmmer-preparation-projection": "project"}[name]
            if not all((directory / filename).is_file() for filename in (
                    "execution-selection.json", "plan.json", "native-handle.json", "original-handle.json")):
                _error(name.replace("-", "_") + "_original_work_incomplete")
            _worker_selection(directory, task=task, policy=LocalJobPolicy(**intent["policy"]))
            return directory, None
        return directory, _read_record(directory, receipt)
    directory.mkdir(parents=True)
    _immutable(directory / "intent.json", intent)
    return directory, None


def _runtime_files(driver):
    from .native_atac_differential_contracts import validate_driver_runtime
    driver = validate_driver_runtime(driver, required_modules=(_WORKER_MODULE, _VERIFY_MODULE))
    sources = [{"path": str(Path(driver["module_root"]) / (row["module"].replace(".", "/") + ".py")),
                "sha256": row["sha256"]} for row in driver["implementation_files"]]
    if {row["path"] for row in sources} != {
            str(path) for path in Path(driver["module_root"]).rglob("*") if path.is_file()}:
        _error("result_worker_original_source_inventory_conflict")
    files = [{"path": driver["python_executable"], "sha256": driver["python_sha256"]}, *sources]
    files.extend(file for dependency in driver["dependencies"] for file in dependency["files"])
    for file in files:
        path = Path(file["path"])
        if (not path.is_absolute() or hashlib.sha256(path.read_bytes()).hexdigest() != file["sha256"]
                or "size_bytes" in file and path.stat().st_size != file["size_bytes"]):
            _error("result_worker_original_software_changed")
    return driver


def _worker_runtime(directory, policy):
    """Reuse one exact driver closure for the two phases of this result action.

    Only application source is copied. The selected interpreter and dependency
    files remain pinned at their actual original paths; no environment is cloned.
    This operational driver identity never replaces the native HMMER producer.
    """
    from .native_atac_differential_software import freeze_driver_runtime, _source_closure
    shared = directory.parent.parent / "native-hmmer-preparation-worker-runtime"
    record = shared / "runtime.json"
    if record.exists():
        retained = _read_record(shared, "runtime.json")
        fields = {"version", "driver_runtime", "python_home", "source_copy_size_bytes", "data_files",
                  "dependency_record_mode", "dependency_exclusions"}
        if (type(retained) is not dict or set(retained) != fields
                or retained["version"] != PREFIX + "worker_runtime_v1"
                or type(retained["python_home"]) is not str or not Path(retained["python_home"]).is_absolute()
                or type(retained["source_copy_size_bytes"]) is not int or retained["source_copy_size_bytes"] < 0
                or retained["data_files"] != []
                or retained["dependency_record_mode"] != "contained_distribution_files_v1"
                or type(retained["dependency_exclusions"]) is not list):
            _error("result_worker_runtime_invalid")
        for row in retained["dependency_exclusions"]:
            if (type(row) is not dict or set(row) != {"distribution", "record_path", "declared_path", "reason"}
                    or any(type(row[key]) is not str or not row[key] for key in row)
                    or not Path(row["declared_path"]).is_absolute()
                    or row["reason"] not in {"outside_distribution_root", "non_runtime_bytecode"}):
                _error("result_worker_runtime_invalid")
        driver = _runtime_files(retained["driver_runtime"])
        if retained["source_copy_size_bytes"] != sum(
                path.stat().st_size for path in Path(driver["module_root"]).rglob("*") if path.is_file()):
            _error("result_worker_original_source_size_conflict")
        return retained
    if shared.exists():
        _error("result_worker_runtime_original_work_incomplete")
    modules = (_WORKER_MODULE, _VERIFY_MODULE)
    closure = _source_closure(Path(__file__).resolve().parents[1], modules)
    # Check the complete known copy footprint before the first source copy.
    # Dependencies and the Python runtime are authenticated in place.
    copy_bytes = sum(path.stat().st_size for path in closure.values())
    check_scratch_budget(directory.parent.parent, policy, additional_bytes=copy_bytes)
    shared.mkdir()
    exclusions = []
    driver = freeze_driver_runtime(module_root=str(Path(__file__).resolve().parents[1]),
        snapshot_directory=str(shared / "source"), driver_modules=list(modules), policy=policy,
        contained_dependency_records=True, dependency_exclusions=exclusions)
    # Fixed grade/project/verify imports use embedded application schemas.
    # jsonschema's actual JSON resources are included in its distribution pins;
    # no application package-data file is selected by these entry points.
    retained = {"version": PREFIX + "worker_runtime_v1", "driver_runtime": driver,
        "python_home": sys.prefix, "source_copy_size_bytes": copy_bytes, "data_files": [],
        "dependency_record_mode": "contained_distribution_files_v1", "dependency_exclusions": exclusions}
    _immutable(record, retained)
    _runtime_files(driver)
    return retained


def _worker_environment(directory, driver, python_home):
    from .native_atac_differential_contracts import _dependency_roots
    return {"PYTHONPATH": os.pathsep.join([driver["module_root"], *_dependency_roots(driver)]),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        "PYTHONHOME": python_home,
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        **{key: str(directory / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
        "XDG_CACHE_HOME": str(directory / "cache")}


def _worker_selection(directory, *, task, policy, plan=None):
    """Authenticate one existing phase before observing or resuming its handle."""
    selected = _read_record(directory, "execution-selection.json")
    saved_plan = _read_record(directory, "plan.json")
    fields = {"version", "task", "plan_sha256", "intent_sha256", "driver_runtime", "python_home", "command",
              "runtime_path", "runtime_sha256",
              "cwd", "environment", "policy", "handle_path", "stdout", "stderr"}
    if (type(selected) is not dict or set(selected) != fields or selected["version"] != _WORKER_SELECTION
            or type(saved_plan) is not dict
            or selected["task"] != task or saved_plan.get("task") != task
            or selected["plan_sha256"] != native_infernal_digest(saved_plan)
            or selected["intent_sha256"] != native_infernal_digest(_read_record(directory, "intent.json"))
            or selected["policy"] != policy.to_dict()
            or selected["cwd"] != str(directory) or saved_plan.get("directory") != str(directory)
            or plan is not None and native_infernal_digest(saved_plan) != native_infernal_digest(plan)):
        _error("result_worker_original_selection_conflict")
    driver = _runtime_files(selected["driver_runtime"])
    if not (directory.parent.parent / "native-hmmer-preparation-worker-runtime/runtime.json").is_file():
        _error("result_worker_original_runtime_missing")
    retained = _worker_runtime(directory, policy)
    expected_command = [driver["python_executable"], "-B", "-c", _WORKER_PROGRAM,
        str(directory / "execution-selection.json"), str(directory / "plan.json")]
    if (selected["command"] != expected_command
            or selected["runtime_path"] != str(directory.parent.parent / "native-hmmer-preparation-worker-runtime/runtime.json")
            or selected["runtime_sha256"] != native_infernal_digest(retained)
            or canonical(retained["driver_runtime"]) != canonical(driver)
            or selected["python_home"] != retained["python_home"]
            or selected["environment"] != _worker_environment(directory, driver, selected["python_home"])
            or selected["handle_path"] != str(directory / "native-handle.json")
            or selected["stdout"] != str(directory / "worker.stdout")
            or selected["stderr"] != str(directory / "worker.stderr")):
        _error("result_worker_original_selection_conflict")
    handle = native.NativeJobHandle(Path(selected["handle_path"]))
    body = handle.read()
    paths = body["paths"]
    binding = _read_record(directory, "original-handle.json")
    if (binding != {"version": PREFIX + "worker_handle_v1", "handle_path": str(handle.path),
            "selection_sha256": native_infernal_digest(selected), "unit": body["unit"],
            "request_sha256": body["request_sha256"], "paths": paths}
            or body["command"] != selected["command"] or body["cwd"] != str(directory)
            or body["stdout"] != selected["stdout"] or body["stderr"] != selected["stderr"]
            or body["metadata"]["policy"] != selected["policy"]
            or any(not Path(path).resolve().is_relative_to(directory) for path in paths.values())):
        _error("result_worker_original_handle_conflict")
    raw = Path(paths["request"]).read_bytes()
    expected_request = {"command": selected["command"], "cwd": str(directory),
        "file_bytes": policy.scratch_bytes, "ready_path": paths["ready"], "release_path": paths["release"],
        "result_path": paths["result"], "stdin_path": None, "env": selected["environment"]}
    if (hashlib.sha256(raw).hexdigest() != body["request_sha256"]
            or json.loads(raw) != expected_request):
        _error("result_worker_original_request_conflict")
    return selected, handle


def _prepare_worker(directory, plan, policy):
    selection_path = directory / "execution-selection.json"
    handle_path = directory / "native-handle.json"
    if selection_path.exists():
        return _worker_selection(directory, task=plan["task"], policy=policy, plan=plan)
    if handle_path.exists() or (directory / "worker-result.json").exists():
        _error("result_worker_original_selection_missing")
    runtime = _worker_runtime(directory, policy)
    driver = runtime["driver_runtime"]
    for name in ("tmp", "cache"):
        (directory / name).mkdir(exist_ok=True)
    selected = {"version": _WORKER_SELECTION, "task": plan["task"],
        "plan_sha256": native_infernal_digest(plan),
        "intent_sha256": native_infernal_digest(_read_record(directory, "intent.json")),
        "driver_runtime": driver, "python_home": runtime["python_home"],
        "runtime_path": str(directory.parent.parent / "native-hmmer-preparation-worker-runtime/runtime.json"),
        "runtime_sha256": native_infernal_digest(runtime),
        "command": [driver["python_executable"], "-B", "-c", _WORKER_PROGRAM,
            str(selection_path), str(directory / "plan.json")], "cwd": str(directory),
        "environment": _worker_environment(directory, driver, runtime["python_home"]), "policy": policy.to_dict(),
        "handle_path": str(handle_path), "stdout": str(directory / "worker.stdout"),
        "stderr": str(directory / "worker.stderr")}
    _immutable(selection_path, selected)
    native.prepare_job(selected["command"], cwd=directory, policy=policy, handle_path=handle_path,
        stdout_path=Path(selected["stdout"]), stderr_path=Path(selected["stderr"]),
        env=selected["environment"])
    body = native.NativeJobHandle(handle_path).read()
    _immutable(directory / "original-handle.json", {"version": PREFIX + "worker_handle_v1",
        "handle_path": str(handle_path), "selection_sha256": native_infernal_digest(selected),
        "unit": body["unit"], "request_sha256": body["request_sha256"], "paths": body["paths"]})
    return _worker_selection(directory, task=plan["task"], policy=policy, plan=plan)


def _collect_worker(directory, plan, policy):
    selected, handle = _prepare_worker(directory, plan, policy)
    try:
        view = native.status(handle)
        if not view["terminal"]:
            if view["state"] == "execution_unknown":
                raise HmmerPreparationWorkerPending(directory, observation=view)
            native.resume_start(handle)
            while True:
                view = native.status(handle)
                if view["terminal"] and view["quiescent"]:
                    break
                if view["state"] == "execution_unknown":
                    raise HmmerPreparationWorkerPending(directory, observation=view)
                time.sleep(.05)
        # Recheck the original selected files; a terminal worker cannot promote
        # changed software to the recorded selected implementation.
        _runtime_files(selected["driver_runtime"])
        return native.collect(handle)
    except (AcquisitionError, OSError, ValueError) as error:
        view = native.status(handle)
        if not view["terminal"] or not view["quiescent"]:
            raise HmmerPreparationWorkerPending(directory, observation=view,
                failure={**exception_diagnostic(error), "operational": getattr(error, "operational", None)}) from error
        raise


def _execute_worker(store, directory, plan, policy):
    """Retain execution diagnostics separately from stable numerical custody."""
    _immutable(directory / "plan.json", plan)
    failures, successful = [], False
    try:
        check_scratch_budget(directory, policy)
        result = _collect_worker(directory, plan, policy)
        receipt = {"returncode": result.returncode, "metadata": result.metadata}
        successful = result.returncode == 0
        if not successful:
            failures.append(failure("worker", PREFIX + "result_worker_nonzero"))
    except (AcquisitionError, OSError, ValueError) as error:
        failures.append(failure("worker", exception_code(error, PREFIX + "result_worker_failed")))
        receipt = {**exception_diagnostic(error),
                   "operational": getattr(error, "operational", None)}
    diagnostics = {"artifacts": []}
    manifest = None
    try:
        manifest = _read_record(directory, "worker-result.json")
        if (type(manifest) is not dict or set(manifest) != {"version", "task", "plan_sha256", "completed", "outputs", "failures"}
                or manifest["version"] != MANIFEST_VERSION or manifest["task"] != plan["task"]
                or manifest["plan_sha256"] != native_infernal_digest(plan) or type(manifest["completed"]) is not bool
                or type(manifest["outputs"]) is not dict):
            _error("result_worker_manifest_invalid")
        validate_failures(manifest["failures"])
    except (ValueError, OSError) as error:
        manifest = None
        receipt["manifest_error"] = exception_diagnostic(error)
        failures.append(failure("worker", PREFIX + "result_worker_manifest_invalid"))
    outputs = {}
    allowed = NUMERICAL_FILES if plan["task"] == "grade" else {"projection": "projection.json"}
    if manifest is not None:
        failures.extend(manifest["failures"])
        if set(manifest["outputs"]) - allowed.keys():
            _error("result_worker_output_role_invalid")
        for role, descriptor in manifest["outputs"].items():
            try:
                if (type(descriptor) is not dict or set(descriptor) != {"filename", "sha256", "size_bytes"}
                        or descriptor["filename"] != allowed[role] or type(descriptor["size_bytes"]) is not int):
                    _error("result_worker_output_descriptor_invalid")
                reference = _capture_file(store, directory, descriptor["filename"], "application/json")
                _artifact_path(store, reference)
                if _descriptor(store, reference) != {"artifact_ref": reference, **{k: descriptor[k] for k in ("sha256", "size_bytes")}}:
                    _error("result_worker_output_bytes_conflict")
                outputs[role] = reference
            except (ValueError, OSError) as error:
                receipt.setdefault("output_errors", []).append({"role": role, **exception_diagnostic(error)})
                failures.append(failure("worker", exception_code(error, PREFIX + "result_worker_output_invalid") if isinstance(error, ValueError)
                    else PREFIX + "result_worker_output_unavailable:" + role))
    diagnostics["worker_receipt_artifact_ref"] = store.artifact(canonical(receipt), "application/json")
    for name in ("worker.stdout", "worker.stderr", "worker-result.json"):
        if (directory / name).exists():
            reference = _capture_file(store, directory, name)
            diagnostics["artifacts"].append({"role": name, "artifact_ref": reference})
    completed = successful and manifest is not None and manifest["completed"] and set(outputs) == set(allowed)
    if manifest is not None and manifest["completed"] and set(outputs) != set(allowed):
        failures.append(failure("worker", PREFIX + "result_worker_outputs_incomplete"))
    return outputs, unique_failures([*plan["failures"], *failures]), bool(completed), diagnostics


def prepare_native_hmmer_preparation_grading(store, *, target, capture, capture_directory, directory, policy):
    """Grade one already captured attempt once, independent of parent selection."""
    if not isinstance(policy, LocalJobPolicy):
        _error("local_job_policy_required")
    target, capture = finite_json_copy(target), finite_json_copy(capture)
    capture_directory = _directory(capture_directory)
    intent = {"target": target, "capture": capture, "capture_directory": str(capture_directory), "policy": policy.to_dict()}
    directory, saved = _begin(directory, "native-hmmer-preparation-grading", intent, "prepared.json")
    if saved is not None and saved.get("source_grading_artifact_ref") is None:
        prepared = _prepared_shape(saved)
        if prepared["graded"] or prepared["occurrences"] or any(prepared[k] is not None for k in _NUMERICAL) or not prepared["failures"]:
            _error("ungraded_prerequisite_receipt_invalid")
        if prepared["bundle_artifact_ref"] is not None:
            _artifact_path(store, prepared["bundle_artifact_ref"])
        return prepared
    # This is deliberately checked BEFORE calling capture_local_bundle: a grade
    # selection never performs the first native acquisition.
    if not (capture_directory / "capture.json").is_file():
        if saved is not None:
            _error("grading_capture_receipt_unavailable")
        prepared = _prepared(failures=[failure("prerequisite", PREFIX + "completed_capture_required")])
        _immutable(directory / "prepared.json", prepared)
        return prepared
    authenticated = capture_local_bundle(store, target=target, directory=capture_directory)
    if native_infernal_digest(authenticated) != native_infernal_digest(capture):
        _error("supplied_capture_conflict")
    if not capture["bundle_validated"]:
        prepared = _prepared(capture["bundle_artifact_ref"], failures=capture["failures"])
        _immutable(directory / "prepared.json", prepared)
        return prepared
    bundle = _decode(store.get_artifact(capture["bundle_artifact_ref"]))
    if saved is not None:
        return validate_prepared_grading(store, saved, bundle=bundle)
    original_plan = _read_record(capture_directory, "capture-plan.json")
    bundle = validate_original_bundle(bundle, original_plan)
    occurrences, problems = qualified_occurrences(bundle, capture["bundle_artifact_ref"], capture)
    metadata, metadata_failures = effective_metadata(bundle, occurrences, include_map_context=True)
    failures = unique_failures([*problems, *metadata_failures])
    files = [{"occurrence_id": r["occurrence_id"], "path": str(_artifact_path(store, r["artifact_ref"]))}
             for r in eligible_occurrences(occurrences)]
    plan = {"version": PLAN_VERSION, "task": "grade", "directory": str(directory), "bundle": bundle,
        "original_plan": original_plan, "bundle_artifact_ref": capture["bundle_artifact_ref"],
        "capture": capture, "occurrences": occurrences, "effective_metadata": metadata,
        "files": files, "failures": failures}
    outputs, failures, completed, diagnostics = _execute_worker(store, directory, plan, policy)
    prepared = _prepared(capture["bundle_artifact_ref"], failures=failures)
    prepared.update({role + "_artifact_ref": ref for role, ref in outputs.items()})
    prepared.update(occurrences=occurrences, graded=completed)
    stable = {"schema": RETAINED_VERSION, "original_plan": original_plan, "capture": capture,
        "bundle_sha256": native_infernal_digest(bundle),
        "original_parameters": deepcopy(bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"]),
        "effective_metadata": metadata, "grading_context": grading_context(bundle, occurrences, metadata), "numerical_artifacts": {role: _descriptor(store, ref) for role, ref in outputs.items()},
        **{k: prepared[k] for k in (*_NUMERICAL, "occurrences", "failures", "graded")}}
    prepared["source_grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=prepared["bundle_artifact_ref"], grading=stable)
    _immutable(directory / "grading-receipt.json", {"prepared_sha256": native_infernal_digest(prepared), **diagnostics})
    _immutable(directory / "prepared.json", prepared)
    return validate_prepared_grading(store, prepared, bundle=bundle)


def _record_refs(source_ref, projection):
    refs = [source_ref]
    for row in projection["rows"]:
        if row["artifact_ref"] is not None:
            refs.append(row["artifact_ref"])
        for check in row["checks"]:
            refs.extend(r["artifact_ref"] for r in check["occurrences"])
    refs.extend(r["artifact_ref"] for r in projection["artifacts"])
    return list(dict.fromkeys(refs))


def _selected(store, reference, *, source_ref, selector, occurrences):
    """Validate the small selected return; no re-projection or recalculation."""
    _artifact_path(store, reference)
    selected = _decode(store.get_artifact(reference))
    if type(selected) is not dict or set(selected) != {"rows", "artifacts", "population"}:
        _error("selected_projection_invalid")
    validate_schema(selected["rows"], {"type": "array", "items": ROW_SCHEMA})
    validate_schema(selected["artifacts"], {"type": "array", "items": ARTIFACT_SCHEMA})
    validate_schema(selected["population"], POPULATION_SCHEMA)
    choice, population = selector["projection"], selected["population"]
    lookup = {(r["direction"], r["role"], r["ordinal"]): r for r in occurrences}
    if (population["source_ref"] != source_ref or population["collection"] != (choice["collection"] if choice else None)
            or population["returned_records"] != len(selected["rows"])
            or population["total_records"] != population["returned_records"] + population["omitted_records"]
            or population["requested_artifact_count"] != len(selector["artifacts"])
            or population["returned_artifact_count"] != len(selected["artifacts"])
            or choice is None and selected["rows"]):
        _error("selected_population_conflict")
    expected_artifacts, missing = [], []
    for request in selector["artifacts"]:
        row = lookup.get(tuple(request[k] for k in ("direction", "role", "ordinal")))
        if row is None:
            missing.append(request)
        else:
            expected_artifacts.append({k: source_ref if k == "source_ref" else row[k]
                                       for k in ARTIFACT_SCHEMA["properties"]})
    # V1 preserves explicitly selected files first, then the exact occurrence
    # dependencies of selected quantities/rows/checks. Those joins are validated
    # by the bounded selector against the saved sheet. The host authenticates
    # that worker output and its byte custody without hydrating the full sheet.
    artifacts = selected["artifacts"]
    if (artifacts[:len(expected_artifacts)] != expected_artifacts
            or population["missing_artifacts"] != missing
            or not selected["rows"] and artifacts != expected_artifacts):
        _error("selected_artifact_association_conflict")
    selected_slots, selected_refs = set(), set()
    for artifact in artifacts:
        slot = tuple(artifact[k] for k in ("direction", "role", "ordinal"))
        original = lookup.get(slot)
        if (slot in selected_slots or original is None or artifact["source_ref"] != source_ref
                or any(original[k] != v for k, v in artifact.items() if k != "source_ref")):
            _error("selected_artifact_custody_conflict")
        selected_slots.add(slot)
        selected_refs.add(artifact["artifact_ref"])
    seen = set()
    for row in selected["rows"]:
        if (row["source_ref"] != source_ref or row["record_key"] in seen or row["artifact_ref"] is not None
                and row["artifact_ref"] not in selected_refs or choice is None
                or [q["path"] for q in row["quantities"]] != choice["quantities"]
                or set(c["name"] for c in row["checks"]) != set(choice["checks"])):
            _error("selected_row_custody_conflict")
        seen.add(row["record_key"])
        for check in row["checks"]:
            for occurrence in check["occurrences"]:
                original = lookup.get(tuple(occurrence[k] for k in ("direction", "role", "ordinal")))
                if (original is None or any(original[k] != v for k, v in occurrence.items())
                        or tuple(occurrence[k] for k in ("direction", "role", "ordinal")) not in selected_slots):
                    _error("selected_check_occurrence_conflict")
    if choice is not None:
        wanted = choice["rows"]
        if "record_keys" in wanted:
            keys = [r["record_key"] for r in selected["rows"]]
            if (keys != [key for key in wanted["record_keys"] if key in seen]
                    or population["missing_record_keys"] != [key for key in wanted["record_keys"] if key not in seen]):
                _error("selected_record_keys_conflict")
        elif len(selected["rows"]) > wanted["limit"] or population["missing_record_keys"]:
            _error("selected_record_window_conflict")
    return selected


def publish_selected_preparation_result(store, *, source_ref, prepared, selector, directory, policy):
    """Return pure V1 selections, retaining a separate immutable projection."""
    if not isinstance(policy, LocalJobPolicy):
        _error("local_job_policy_required")
    prepared = _prepared_shape(prepared)
    bundle = _decode(store.get_artifact(prepared["bundle_artifact_ref"]))
    prepared = validate_prepared_grading(store, prepared, bundle=bundle)
    stable = _stable(store, prepared)
    source = store._require(source_ref, {"source"})
    expected = original_source_payload(bundle=bundle, capture=stable["capture"], prepared=prepared)
    if source.get("origin") != "tool" or any(source.get(k) != v for k, v in expected.items()):
        _error("publication_source_custody_conflict")
    selector = validate_preparation_result_selector(selector, program=bundle["program"], mode=bundle["mode"])
    intent = {"source_ref": source_ref, "prepared_sha256": native_infernal_digest(prepared),
        "selector": selector, "policy": policy.to_dict()}
    directory, saved = _begin(directory, "native-hmmer-preparation-projection", intent, "publication.json",
                             failure_receipt="projection-failure.json")
    if saved is not None:
        if set(saved) == {"_failure"}:
            record = saved["_failure"]
            if (type(record) is not dict or set(record) != {"version", "intent", "code", "failures",
                    "projection_artifact_ref", "worker_receipt_artifact_ref", "artifacts"}
                    or record["version"] != PREFIX + "projection_failure_v1" or record["intent"] != intent
                    or record["code"] not in {PREFIX + "projection_worker_failed", PREFIX + "saved_numerical_grading_unavailable"}):
                _error("projection_failure_receipt_invalid")
            validate_failures(record["failures"])
            for ref in [record["worker_receipt_artifact_ref"], *[r["artifact_ref"] for r in record["artifacts"]],
                        *([record["projection_artifact_ref"]] if record["projection_artifact_ref"] else [])]:
                _artifact_path(store, ref)
            raise ContractError(record["code"])
        if (type(saved) is not dict or set(saved) != _PUBLICATION_FIELDS
                or type(saved["projection_artifact_ref"]) is not str or not saved["projection_artifact_ref"]):
            _error("publication_receipt_invalid")
        receipt = _read_record(directory, "projection-receipt.json")
        if (receipt["publication_sha256"] != native_infernal_digest(saved) or receipt["intent"] != intent
                or receipt.get("completed") is not True or saved["failures"] != prepared["failures"]):
            _error("publication_receipt_identity_conflict")
        selected = _selected(store, saved["projection_artifact_ref"], source_ref=source_ref,
            selector=selector, occurrences=prepared["occurrences"])
        if any(saved[k] != selected[k] for k in selected) or saved["record_refs"] != _record_refs(source_ref, selected):
            _error("publication_selected_data_conflict")
        validate_failures(saved["failures"])
        for ref in [receipt["worker_receipt_artifact_ref"], *[r["artifact_ref"] for r in receipt["artifacts"]]]:
            _artifact_path(store, ref)
        return saved
    plan = {"version": PLAN_VERSION, "task": "project", "directory": str(directory),
        "grading": _worker_file(store, prepared["grading_artifact_ref"]) if prepared["grading_artifact_ref"] else None,
        "grading_context": stable["grading_context"], "occurrences": prepared["occurrences"], "source_ref": source_ref,
        "selector": selector, "failures": deepcopy(prepared["failures"])}
    outputs, failures, completed, diagnostics = _execute_worker(store, directory, plan, policy)
    reference = outputs.get("projection")
    if not completed or reference is None:
        code = PREFIX + ("saved_numerical_grading_unavailable" if any(
            row["code"] == PREFIX + "saved_numerical_grading_unavailable" for row in failures)
            else "projection_worker_failed")
        _immutable(directory / "projection-failure.json", {"version": PREFIX + "projection_failure_v1",
            "intent": intent, "code": code, "failures": failures,
            "projection_artifact_ref": reference, **diagnostics})
        raise ContractError(code)
    selected = _selected(store, reference, source_ref=source_ref, selector=selector, occurrences=prepared["occurrences"])
    result = {"record_refs": _record_refs(source_ref, selected), **selected,
        "failures": failures, "projection_artifact_ref": reference}
    _immutable(directory / "projection-receipt.json", {"intent": intent,
        "publication_sha256": native_infernal_digest(result), "completed": completed, **diagnostics})
    _immutable(directory / "publication.json", result)
    return result


def validate_publication(store, publication, *, source_ref, prepared, selector, directory, policy):
    """Authenticate an existing selection receipt with all worker work forbidden."""
    saved_directory = _directory(directory) / "native-hmmer-preparation-projection"
    if not (saved_directory / "publication.json").is_file():
        _error("saved_publication_required")
    saved = publish_selected_preparation_result(store, source_ref=source_ref, prepared=prepared,
        selector=selector, directory=directory, policy=policy)
    if saved != finite_json_copy(publication):
        _error("supplied_publication_conflict")
    return saved


__all__ = ["prepare_native_hmmer_preparation_grading", "publish_selected_preparation_result",
           "validate_prepared_grading", "validate_publication", "HmmerPreparationWorkerPending"]
