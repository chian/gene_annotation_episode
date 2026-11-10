"""One caller-selected ordinary sequence reservation and non-cancelling observation.

The caller authenticates and locks its selected action before this port. Frozen
operand metadata are supplied facts, never authority created here. This module
resolves no subjects or Files, normalizes no symbols, performs no scientific
calculation, and publishes no Source, receipt, grant or episode.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import time

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .communication import plain
from .episode_bindings import BindingContext
from .execution_contracts import canonical, digest
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import MolecularOperationUnpublished
from . import molecular_sequence_driver as driver
from . import molecular_sequence_native as source
from .molecular_sequence_execution_contracts import (
    ADAPTER_MODULE, ATTEMPT_DIRECTORY, BUNDLE_FILENAME, OUTPUT_DIRECTORY,
    PLAN_FILENAME, REQUEST_RELATIVE, absolute_path, build_molecular_sequence_selected_plan,
    molecular_sequence_adapter_argv, selected_payload_sha256,
    validate_molecular_sequence_attempt_bundle, validate_molecular_sequence_selected_plan,
)
from . import molecular_sequence_result_contracts as contracts
from .native_file_capture import _declaration, _identity
from .native_flux_balance_storage import confined_file, directory, immutable_bytes, read_bytes


OPERATION = "annotate_open_reading_frames"
PREPARED_VERSION = "ordinary_orf_prepared_v1"
EXECUTION_VERSION = "ordinary_orf_execution_v1"
BINDING_VERSION = "ordinary_orf_attempt_binding_v1"
OPERAND_VERSION = "ordinary_orf_sequence_operand_v1"
DRIVER_REQUEST_FILENAME = "molecular-sequence-driver-request.json"
BINDING_FILENAME = "ordinary-orf-input-binding.json"
ENVIRONMENT_SELECTION = {"version": "molecular_sequence_execution_selection_v1",
    "environment_realization": "operation_scoped_tmp_and_cache_v1"}
POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
_CONTROL_NAMES = (BINDING_FILENAME, DRIVER_REQUEST_FILENAME, PLAN_FILENAME)
_NATIVE_PATHS = ("request", "ready", "release", "status", "result", "launcher")


def _require(condition, code):
    if not condition:
        raise ValueError("ordinary_orf_" + code)


def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)


def _copy(value):
    return json.loads(canonical(value))


def _bytes(value):
    return (canonical(value) + "\n").encode("utf-8")


def _pin(path, raw):
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _read_json(path):
    return driver._json(read_bytes(path))


def _same_or_write(path, raw):
    if path.exists() or path.is_symlink():
        _require(read_bytes(path) == raw, "original_control_conflict")
        return
    try:
        immutable_bytes(path, raw)
    except FileExistsError:
        _require(read_bytes(path) == raw, "original_control_conflict")


def _profile(operation):
    return contracts.ordinary_molecular_sequence_profile(operation)


def _code(profile, suffix):
    return profile["operand_version"].removesuffix("_sequence_operand_v1") + "_" + suffix


def _deployment(operation, value):
    profile = _profile(operation)
    source._deployment(value, version=profile["deployment_version"],
        source_sha256=source._SOURCE_PROFILES[profile["native_source"]]["sha256"])


def _prepared_profile(prepared):
    # The already selected plan names the finite operation. Tags must agree;
    # a caller cannot obtain another operation by changing a carrier version.
    _require(type(prepared) is dict and type(prepared.get("plan")) is dict
        and type(prepared["plan"].get("selection")) is dict, "prepared_fields_required")
    profile = _profile(prepared["plan"]["selection"].get("operation"))
    _require(prepared.get("version") == profile["prepared_version"], "prepared_version_invalid")
    return profile


def _operand(value, subject_ref, *, operation=OPERATION):
    profile = _profile(operation)
    if operation == "align_sequences":
        from .primer_placement_result_contracts import validate_operands
        return validate_operands(value, subject_ref)
    value = _copy(value)
    _closed(value, ("version", "subject", "sequence", "parent_mapping", "mapping_failure",
        "input_file", "associations", "footprint"), "operand_fields_required")
    _require(value["version"] == profile["operand_version"] and type(value["subject"]) is dict
        and value["subject"].get("id") == subject_ref and type(value["sequence"]) is str
        and type(value["associations"]) is dict and type(value["footprint"]) is list,
        "operand_invalid")
    _require(value["parent_mapping"] is None or type(value["parent_mapping"]) is dict,
        "operand_mapping_invalid")
    _require(value["mapping_failure"] is None or value["mapping_failure"] == {
        "code": "subregion_mapping_unavailable"}, "operand_mapping_failure_invalid")
    _require((value["parent_mapping"] is None) == (value["mapping_failure"] is not None),
        "operand_mapping_failure_conflict")
    file = _identity(value["input_file"])
    try:
        raw = value["sequence"].encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError(_code(profile, "operand_sequence_not_ascii")) from error
    _require(file["format"] == "ascii_sequence" and file["size_bytes"] == len(raw)
        and file["sha256"] == hashlib.sha256(raw).hexdigest(), "operand_file_identity_conflict")
    return value


def _arguments(value, *, operation=OPERATION):
    value = contracts.validate_ordinary_molecular_sequence_arguments(operation, _copy(value))
    _require("mode" not in value or operation == "align_sequences" and value["mode"] == "run_native", "native_arguments_required")
    return value


def _native_arguments(operation, arguments, operand):
    profile = _profile(operation)
    if operation == "align_sequences":
        from .primer_placement_result_contracts import native_arguments
        return native_arguments(arguments, operand)
    return dict(sequence=operand["sequence"], **{key: arguments[key]
        for key in profile["native_argument_names"]})


def _scientific_context(operation, arguments, operand):
    _profile(operation)
    if operation == "align_sequences":
        from .primer_placement_result_contracts import scientific_context
        return scientific_context(arguments, operand)
    return (dict(subject_ref=arguments["subject_ref"], parent_mapping=operand["parent_mapping"])
        if operation == OPERATION else
        dict(input_ref=arguments["subject_ref"], input_mapping=operand["parent_mapping"]))


def _driver_request(*, operation, arguments, operand, deployment, attempt_identity):
    profile = _profile(operation)
    return dict(version=profile["driver_request_version"], mode="native",
        attempt_identity=deepcopy(attempt_identity),
        selection=dict(version=profile["native_request_version"], operation=operation,
            arguments=_native_arguments(operation, arguments, operand), deployment=deepcopy(deployment)),
        scientific_context=_scientific_context(operation, arguments, operand))


def _environment(selected, root):
    _require(selected["environment"] == ENVIRONMENT_SELECTION, "environment_selection_invalid")
    software = selected["software"]
    return {"PYTHONHOME": software["python_home"], "PYTHONPATH": ":".join(software["import_roots"]),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        "PYTHONPYCACHEPREFIX": str(root / "cache" / "pycache"),
        # The shared lifecycle worker realizes these three at its cwd.
        "TMPDIR": str(root), "TMP": str(root), "TEMP": str(root),
        "XDG_CACHE_HOME": str(root / "cache"), "MPLCONFIGDIR": str(root / "cache" / "matplotlib")}


def _native_request(plan, paths):
    return {"command": molecular_sequence_adapter_argv(plan),
        "cwd": str(Path(plan["identity"]["execution_id"]).parent),
        "file_bytes": plan["policy"]["scratch_bytes"], "ready_path": paths["ready"],
        "release_path": paths["release"], "result_path": paths["result"],
        "stdin_path": None, "env": plan["selected_environment"]}


def _verify_controls(prepared):
    _closed(prepared, ("version", "binding", "binding_file", "plan", "plan_file", "driver_request_file",
        "handle_path"), "prepared_fields_required")
    profile = _prepared_profile(prepared)
    operation = profile["operation"]
    plan = validate_molecular_sequence_selected_plan(prepared["plan"],
        expected_payload_sha256=prepared["plan"]["selected_payload_sha256"])
    root = directory(Path(plan["identity"]["execution_id"]).parent)
    binding = prepared["binding"]
    _closed(binding, ("version", "context", "operation_key", "arguments", "frozen_operand", "selected", "policy"),
        "binding_fields_required")
    _require(binding["version"] == profile["binding_version"] and binding["policy"] == POLICY == plan["policy"],
        "original_allocation_conflict")
    context, selected = binding["context"], binding["selected"]
    _closed(selected, ("resource_id", "workspace", "deployment", "software", "environment"),
        "selection_fields_required")
    _deployment(operation, selected["deployment"])
    _require(type(context) is dict and plan["identity"]["run_id"] == context.get("run_id")
        and plan["identity"]["episode_id"] == context.get("episode_id")
        and plan["identity"]["assignment_sha256"] == digest(context.get("assignment"))
        and plan["identity"]["operation_key"] == binding["operation_key"]
        and plan["identity"]["resource_id"] == selected["resource_id"]
        and plan["software"] == selected["software"]
        and plan["selected_environment"] == _environment(selected, root), "original_plan_conflict")
    _require(root == Path(absolute_path(selected["workspace"])) / ".episode-operations" /
        digest({"run": context["run_id"], "episode": context["episode_id"]}) / digest(binding["operation_key"])
        and prepared["handle_path"] == str(root / "native.json"), "original_root_conflict")
    arguments = _arguments(binding["arguments"], operation=operation)
    operand = _operand(binding["frozen_operand"], arguments if operation == "align_sequences" else arguments["subject_ref"], operation=operation)
    request = plan["selection"]["driver_request"]
    expected_request = _driver_request(operation=operation, arguments=arguments, operand=operand,
        deployment=selected["deployment"], attempt_identity={key: plan["identity"][key] for key in
            ("run_id", "episode_id", "resource_id", "operation_key", "execution_id")})
    _require(request == expected_request, "original_request_conflict")
    for key, name, value in (("binding_file", profile["binding_filename"], binding),
            ("plan_file", PLAN_FILENAME, plan), ("driver_request_file", DRIVER_REQUEST_FILENAME, request)):
        path = confined_file(root, name)
        raw = read_bytes(path)
        _require(prepared[key] == _pin(path, raw) and raw == _bytes(value), "original_control_conflict")
    _require(plan["selection"]["request_file"] == prepared["driver_request_file"], "original_request_pin_conflict")
    return plan, root


def _verify_handle(prepared):
    plan, root = _verify_controls(prepared)
    path = confined_file(root, "native.json")
    handle = native.NativeJobHandle(path)
    body = _read_json(path)
    _require(type(body) is dict and body.get("version") == native.VERSION
        and body.get("stage") in ("prepared", "submitting", "released")
        and body.get("command") == molecular_sequence_adapter_argv(plan) and body.get("cwd") == str(root)
        and body.get("stdout") == str(root / "stdout.log") and body.get("stderr") == str(root / "stderr.log")
        and type(body.get("metadata")) is dict and body["metadata"].get("policy") == plan["policy"],
        "original_handle_conflict")
    paths = body.get("paths")
    _closed(paths, _NATIVE_PATHS, "original_native_paths_invalid")
    _require(all(type(value) is str for value in paths.values()), "original_native_paths_invalid")
    match = re.fullmatch(r"(\.local-job-[0-9a-f]{32})\.request", Path(paths["request"]).name)
    _require(match is not None and paths == {role: str(root / (match[1] + "." + role)) for role in _NATIVE_PATHS},
        "original_native_paths_conflict")
    for selected_path in paths.values():
        confined_file(root, Path(selected_path).name)
    raw = read_bytes(paths["request"])
    _require(hashlib.sha256(raw).hexdigest() == body.get("request_sha256")
        and driver._json(raw) == _native_request(plan, paths), "original_native_request_conflict")
    return handle, body


def prepare_ordinary_molecular_sequence_attempt(*, operation, context, operation_key, arguments, frozen_operand, selected, policy):
    """Persist the selected controls and reserve once; never dispatch work.

    BindingContext's type is checked, but authentication and the action lock
    belong to the caller. The returned record asserts no received-input or
    scientific producing-attempt authority. No source software is loaded here.
    """
    profile = _profile(operation)
    control_names = (profile["binding_filename"], DRIVER_REQUEST_FILENAME, PLAN_FILENAME)
    _require(type(context) is BindingContext, "binding_context_required")
    prefix = context.run_id + ":" + context.episode_id + ":"
    suffix = operation_key[len(prefix):] if type(operation_key) is str and operation_key.startswith(prefix) else ""
    _require(bool(suffix) and suffix.isdecimal() and str(int(suffix)) == suffix, "selected_operation_key_required")
    _require(type(policy) is LocalJobPolicy and policy.to_dict() == POLICY, "registry_allocation_required")
    arguments = _arguments(arguments, operation=operation)
    operand = _operand(frozen_operand, arguments if operation == "align_sequences" else arguments["subject_ref"], operation=operation)
    selected = _copy(selected)
    _closed(selected, ("resource_id", "workspace", "deployment", "software", "environment"), "selection_fields_required")
    _require(type(selected["resource_id"]) is str and bool(selected["resource_id"]), "resource_id_required")
    _deployment(operation, selected["deployment"])
    workspace = directory(absolute_path(selected["workspace"]))
    root = workspace / ".episode-operations" / digest({"run": context.run_id, "episode": context.episode_id}) / digest(operation_key)
    execution_id = str(root / "native.json")
    environment = _environment(selected, root)
    request = _driver_request(operation=operation, arguments=arguments, operand=operand,
        deployment=selected["deployment"], attempt_identity=dict(run_id=context.run_id,
            episode_id=context.episode_id, resource_id=selected["resource_id"],
            operation_key=operation_key, execution_id=execution_id))
    request_raw = _bytes(request)
    request_file = _pin(root / DRIVER_REQUEST_FILENAME, request_raw)
    selection = dict(operation=operation, mode="native", driver_request=request, request_file=request_file)
    payload = selected_payload_sha256(selection=selection, software=selected["software"],
        policy=policy.to_dict(), selected_environment=environment)
    job = dict(argv=[selected["software"]["python"]["path"], "-B", "-m", ADAPTER_MODULE,
        "--plan", PLAN_FILENAME, "--selected-payload-sha256", payload], environment=environment)
    identity = dict(run_id=context.run_id, episode_id=context.episode_id, resource_id=selected["resource_id"],
        execution_id=execution_id, attempt_id=digest(operation_key), operation_key=operation_key,
        assignment_sha256=digest(plain(context.assignment)), requested_job_sha256=digest(job))
    plan = build_molecular_sequence_selected_plan(identity=identity, requested_job=job, selection=selection,
        software=selected["software"], policy=policy.to_dict(), selected_environment=environment)
    binding = dict(version=profile["binding_version"], context=context.as_record(), operation_key=operation_key,
        arguments=arguments, frozen_operand=operand, selected=selected, policy=policy.to_dict())
    binding_raw, plan_raw = _bytes(binding), _bytes(plan)
    prepared = dict(version=profile["prepared_version"], binding=binding,
        binding_file=_pin(root / profile["binding_filename"], binding_raw), plan=plan,
        plan_file=_pin(root / PLAN_FILENAME, plan_raw), driver_request_file=request_file, handle_path=execution_id)
    directory(root, create=True)
    for name in (*control_names, "native.json", "stdout.log", "stderr.log"):
        confined_file(root, name)
    handle_exists = (root / "native.json").exists()
    if handle_exists:
        _verify_handle(prepared)
        return _copy(prepared)
    if (root / ATTEMPT_DIRECTORY).exists() or (root / ATTEMPT_DIRECTORY).is_symlink():
        raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed"))
    for path in root.iterdir():
        if path.name in control_names:
            continue
        if path.name == "cache":
            directory(path)
            continue
        confined_file(root, path.name)
        if path.name in ("stdout.log", "stderr.log"):
            _require(read_bytes(path) == b"", "unreserved_native_output_conflict")
            continue
        match = re.fullmatch(r"(\.local-job-[0-9a-f]{32})\.request", path.name)
        _require(match is not None, "unreserved_control_conflict")
        paths = {role: str(root / (match[1] + "." + role)) for role in _NATIVE_PATHS}
        _require(_read_json(path) == _native_request(plan, paths), "unreserved_native_request_conflict")
    for name, raw in ((profile["binding_filename"], binding_raw), (DRIVER_REQUEST_FILENAME, request_raw), (PLAN_FILENAME, plan_raw)):
        _same_or_write(root / name, raw)
    for child in (root / "cache", root / "cache" / "pycache", root / "cache" / "matplotlib"):
        directory(child, create=True)
    native.prepare_job(molecular_sequence_adapter_argv(plan), cwd=root, policy=policy,
        handle_path=root / "native.json", stdout_path=root / "stdout.log", stderr_path=root / "stderr.log", env=environment)
    _verify_handle(prepared)
    return _copy(prepared)


def prepare_ordinary_orf_attempt(*, context, operation_key, arguments, frozen_operand, selected, policy):
    """Compatibility port for the original ordinary ORF record and selection."""
    return prepare_ordinary_molecular_sequence_attempt(operation=OPERATION, context=context,
        operation_key=operation_key, arguments=arguments, frozen_operand=frozen_operand,
        selected=selected, policy=policy)


def _metadata_issue(code, error=None, role=None):
    return dict(code=code, role=role, exception_type=None if error is None else type(error).__name__,
        message=None if error is None else str(error))


def _result_metadata(plan, *, read_json=None):
    """Read metadata independently; never verify or discard all output bytes."""
    read = _read_json if read_json is None else read_json
    profile = _profile(plan["selection"]["operation"])
    root = Path(plan["attempt_directory"])
    issues, bundle, declaration = [], None, None
    declarations = {}
    try:
        bundle = validate_molecular_sequence_attempt_bundle(read(root / BUNDLE_FILENAME), plan=plan)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        issues.append(_metadata_issue("bundle_metadata_unavailable" if isinstance(error, FileNotFoundError)
            else "bundle_metadata_invalid", error))
    try:
        value = read(root / OUTPUT_DIRECTORY / "declaration.json")
        _closed(value, ("version", "mode", "operation", "request_file", "request_file_pin_verified", "attempt_identity",
            "native_call_state", "native_failure", "driver_failure", "files", "qualification"), "declaration_fields_invalid")
        expected_request = plan["selection"]["driver_request"]
        expected_file = {**plan["selection"]["request_file"], "path": str(root / REQUEST_RELATIVE)}
        _require(value["version"] == driver.DECLARATION_VERSION and value["mode"] == "native"
            and value["operation"] == profile["operation"] and value["request_file"] == expected_file
            and value["request_file_pin_verified"] is True
            and value["attempt_identity"] == expected_request["attempt_identity"]
            and type(value["files"]) is dict, "declaration_selection_conflict")
        declaration = value
        if set(value["files"]) != {"capture", "sheet", "components"}:
            issues.append(_metadata_issue("declaration_role_set_invalid"))
        for role in ("capture", "sheet", "components"):
            try:
                selected = _declaration(value["files"].get(role))
                _require(selected["relative_path"] == role + ".json" and selected["format"] == "json",
                    "declaration_role_path_conflict")
                declarations[role] = selected
            except (ValueError, TypeError, KeyError) as error:
                issues.append(_metadata_issue("declaration_role_invalid", error, role))
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        issues.append(_metadata_issue("declaration_metadata_unavailable" if isinstance(error, FileNotFoundError)
            else "declaration_metadata_invalid", error))
    return bundle, declaration, declarations, issues


def _observe(handle, policy):
    view = native.status(handle)
    _require(type(view) is dict and type(view.get("terminal")) is bool and type(view.get("quiescent")) is bool
        and type(view.get("metadata")) is dict and view["metadata"].get("policy") == policy,
        "lifecycle_observation_invalid")
    return view


def run_ordinary_molecular_sequence_attempt(prepared, *, cancel_event=None):
    """Observe/collect the original unit without cancellation or a time budget.

    The existing wait_job cancels on exception, so this port uses the same
    lifecycle status/collect operations and its existing 50 ms wait interval.
    Caller cancellation stops observation only. A released unit stays intact.
    Result metadata validation does not establish output-byte validity, native
    scientific success, or any scientific/native-call count.
    """
    prepared = _copy(prepared)
    profile = _profile(OPERATION)
    try:
        profile = _prepared_profile(prepared)
        handle, body = _verify_handle(prepared)
        plan, _root = _verify_controls(prepared)
    except Exception as error:
        raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed")) from error
    result, failure = None, None
    try:
        view = _observe(handle, plan["policy"])
        if not (view["terminal"] and view["quiescent"]):
            if cancel_event is not None and cancel_event.is_set():
                raise MolecularOperationUnpublished(_code(profile, "observation_stopped"))
            if view.get("state") == "execution_unknown":
                raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed"))
            if body["stage"] == "prepared" or not Path(body["paths"]["release"]).exists():
                native.resume_start(handle)
            while True:
                view = _observe(handle, plan["policy"])
                if view["terminal"] and view["quiescent"]:
                    break
                if cancel_event is not None and cancel_event.is_set():
                    raise MolecularOperationUnpublished(_code(profile, "observation_stopped"))
                if view.get("state") == "execution_unknown":
                    raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed"))
                time.sleep(0.05)
        result = native.collect(handle)
    except MolecularOperationUnpublished:
        raise
    except Exception as error:
        try:
            view = _observe(handle, plan["policy"])
        except Exception as observation_error:
            raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed")) from observation_error
        if not (view["terminal"] and view["quiescent"]):
            raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed")) from error
        failure = (dict(code=error.code, phase=error.phase, diagnostic=deepcopy(error.diagnostic),
            operational=deepcopy(error.operational)) if isinstance(error, AcquisitionError) else
            dict(code=_code(profile, "lifecycle_error"), phase="local_execution",
                diagnostic=dict(exception_type=type(error).__name__, message=str(error)), operational=None))
    try:
        view = _observe(handle, plan["policy"])
    except Exception as error:
        raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed")) from error
    if not (view["terminal"] and view["quiescent"]):
        raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed"))
    try:
        _handle, body = _verify_handle(prepared)
    except Exception as error:
        raise MolecularOperationUnpublished(_code(profile, "original_attempt_unconfirmed")) from error
    metadata = deepcopy(view["metadata"])
    code = result.returncode if result is not None else metadata.get("native_returncode")
    _require(code is None or type(code) is int, "native_returncode_invalid")
    bundle, declaration, declarations, issues = _result_metadata(plan)
    return dict(version=profile["execution_version"], plan=deepcopy(plan), handle=deepcopy(body),
        plan_file=deepcopy(prepared["plan_file"]), binding_file=deepcopy(prepared["binding_file"]),
        driver_request_file=deepcopy(prepared["driver_request_file"]),
        terminal=True, quiescent=True, returncode=code, metadata=metadata, failure=failure,
        bundle=bundle, declaration=declaration, declarations=declarations, metadata_failures=issues,
        output_byte_validation="deferred_to_result_owner")


def run_ordinary_orf_attempt(prepared, *, cancel_event=None):
    """Compatibility observer for the original ordinary ORF carrier only."""
    try:
        _require(_prepared_profile(prepared)["operation"] == OPERATION, "prepared_version_invalid")
    except Exception as error:
        raise MolecularOperationUnpublished("ordinary_orf_original_attempt_unconfirmed") from error
    return run_ordinary_molecular_sequence_attempt(prepared, cancel_event=cancel_event)


__all__ = ["OPERATION", "PREPARED_VERSION", "EXECUTION_VERSION", "BINDING_VERSION", "OPERAND_VERSION",
    "DRIVER_REQUEST_FILENAME", "BINDING_FILENAME", "ENVIRONMENT_SELECTION", "POLICY",
    "prepare_ordinary_orf_attempt", "run_ordinary_orf_attempt",
    "prepare_ordinary_molecular_sequence_attempt", "run_ordinary_molecular_sequence_attempt"]
