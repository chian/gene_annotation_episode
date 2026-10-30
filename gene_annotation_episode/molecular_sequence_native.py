"""Private execution of genuine, explicitly selected molecular primitives.

The host resolves software_files_ref on its own Store thread and supplies the
unchanged manifest as a pinned native input file. This helper has no Store,
deployment resolver, installer, source rewriting or numerical calculator.
"""
from __future__ import annotations

from copy import deepcopy
import contextlib
import hashlib
import importlib.metadata as metadata
import importlib.util
import inspect
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import traceback


REQUEST_VERSION = "molecular_sequence_request_v1"
DEPLOYMENT_VERSION = "molecular_sequence_deployment_v1"
RESULT_VERSION = "molecular_sequence_execution_v1"
REQUEST_VERSION_V2 = "molecular_sequence_request_v2"
DEPLOYMENT_VERSION_V2 = "molecular_sequence_deployment_v2"
RESULT_VERSION_V2 = "molecular_sequence_execution_v2"
REQUEST_VERSION_V3 = "molecular_sequence_request_v3"
DEPLOYMENT_VERSION_V3 = "molecular_sequence_deployment_v3"
RESULT_VERSION_V3 = "molecular_sequence_execution_v3"
BIOCHEMISTRY_SOURCE_SHA256 = "9b8ea7ea1f712553025bdaf16f981d8bec62df6004efd0954ed90f33a394e018"
PROTEASE_FUNCTION_SHA256 = "9ad74fa1c808c356f457748b2372e970b7c54bc960a5d41dba60375e9d91f36c"
SOURCE_SHA256 = "de47e1dc0013cd6e8d2941d8945835d585f938e486a69bb2ba3333403a3efba4"
GLYCO_SOURCE_SHA256 = "ed3726d318f239e98183a359f18bcd341f4159ef2e400322c6141f77dcd2aff2"
_MODULE_NAME = "_selected_molecular_sequence_native"
_OPERATIONS = {
    "annotate_open_reading_frames": {
        "fields": {"sequence", "min_length", "search_reverse", "filter_subsets"},
        "schema": "biomni_orf_native_record_v1",
        "sha256": "bc32fff2924e09ec940f6d9b8d74732a8ef86d0894761430a3ad57ea7148269b",
        "source": "molecular",
    },
    "align_sequences": {
        "fields": {"long_seq", "short_seqs"},
        "schema": "biomni_primer_placement_native_v1",
        "sha256": "22db874a1776118c633103253ae0366f1e2d09df47b6bf41b031f423ff25d82e",
        "source": "molecular",
    },
}
_LIBRARIES = (
    ("pandas", "pandas"), ("requests", "requests"), ("Bio", "biopython"),
    ("bs4", "beautifulsoup4"), ("soupsieve", "soupsieve"),
    ("typing_extensions", "typing_extensions"),
)
_SOURCE_PROFILES = {
    "molecular": {"sha256": SOURCE_SHA256, "libraries": _LIBRARIES},
    "glyco": {"sha256": GLYCO_SOURCE_SHA256, "libraries": ()},
}
_OPERATIONS_V2 = {
    **_OPERATIONS,
    "find_n_glycosylation_motifs": {
        "fields": {"sequence", "allow_overlap"},
        "schema": "biomni_glycosylation_log_native_v1",
        "sha256": "d574294b1088dfb22b6f4242cc0c94b17de4999e86330e07620a83a0b4754c61",
        "source": "glyco",
    },
    "predict_o_glycosylation_hotspots": {
        "fields": {"sequence", "window", "min_st_fraction", "disallow_proline_next"},
        "schema": "biomni_glycosylation_log_native_v1",
        "sha256": "dac5fa5bd182e0f7d4154ad72289c9adae173864e07e6392ae32d1e1102b2ca6",
        "source": "glyco",
    },
}


class _BoundaryError(ValueError):
    def __init__(self, code, path="", **details):
        super().__init__(code + (": " + path if path else ""))
        self.code, self.path, self.details = code, path, details


def _fail(code, path="", **details):
    raise _BoundaryError("molecular_sequence_" + code, path, **details)


def _closed(value, fields, path):
    if type(value) is not dict or set(value) != set(fields):
        _fail("closed_fields_required", path, required_fields=sorted(fields))


def _finite_json(value, path=""):
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _finite_json(child, path + "/" + str(index))
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for key, child in value.items():
            _finite_json(child, path + "/" + key.replace("~", "~0").replace("/", "~1"))
        return
    _fail("finite_json_request_required", path, value_type=type(value).__name__,
        nonfinite_token=repr(value) if type(value) is float else None)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode("utf-8")


def _path(value, path):
    if type(value) is not str or not value or not Path(value).is_absolute():
        _fail("absolute_path_required", path)
    return Path(value)


def _pin_schema(value, path):
    _closed(value, ("path", "sha256", "size_bytes"), path)
    _path(value["path"], path + "/path")
    if (type(value["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None
            or type(value["size_bytes"]) is not int or value["size_bytes"] < 0):
        _fail("file_pin_required", path)


def _actual_pin(path):
    selected = Path(path).resolve(strict=True)
    raw = selected.read_bytes()
    return {"path": str(selected), "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw)}, raw


def _exact_file(declared, path):
    actual, raw = _actual_pin(declared["path"])
    if actual != declared:
        _fail("selected_file_mismatch", path, expected=declared, actual=actual)
    return actual, raw


def _selected_file(path, index, field):
    actual, _ = _actual_pin(path)
    expected = index.get(actual["path"])
    if expected is None:
        _fail("file_not_selected", field, actual=actual)
    if actual != expected:
        _fail("import_file_mismatch", field, expected=expected, actual=actual)
    return actual


def _deployment(value, *, version=DEPLOYMENT_VERSION, source_sha256=SOURCE_SHA256):
    _closed(value, ("version", "runtime", "module", "import_roots",
        "software_files_ref", "software_files_file"), "/deployment")
    if value["version"] != version:
        _fail("deployment_version_required", "/deployment/version")
    _closed(value["runtime"], ("executable", "home"), "/deployment/runtime")
    _pin_schema(value["runtime"]["executable"], "/deployment/runtime/executable")
    _path(value["runtime"]["home"], "/deployment/runtime/home")
    _pin_schema(value["module"], "/deployment/module")
    _pin_schema(value["software_files_file"], "/deployment/software_files_file")
    reference = value["software_files_ref"]
    if (type(reference) is not str or re.fullmatch(r"artifact_[0-9a-f]{64}", reference) is None
            or reference != "artifact_" + value["software_files_file"]["sha256"]):
        _fail("manifest_artifact_identity_mismatch", "/deployment/software_files_ref")
    roots = value["import_roots"]
    if type(roots) is not list or not roots:
        _fail("ordered_import_roots_required", "/deployment/import_roots")
    for i, root in enumerate(roots):
        _path(root, "/deployment/import_roots/" + str(i))
    if len(roots) != len(set(roots)):
        _fail("ordered_import_roots_required", "/deployment/import_roots")
    if value["module"]["sha256"] != source_sha256:
        _fail("original_source_pin_required", "/deployment/module/sha256")


def _manifest(deployment):
    actual, raw = _exact_file(deployment["software_files_file"],
        "/deployment/software_files_file")
    def fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _fail("duplicate_manifest_field", "/deployment/software_files_file", field=key)
            result[key] = value
        return result
    try:
        rows = json.loads(raw, object_pairs_hook=fields, parse_constant=lambda value:
            _fail("finite_manifest_required", "/deployment/software_files_file", token=value))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        _fail("manifest_json_required", "/deployment/software_files_file",
            exception_type=type(error).__name__, message=str(error))
    if type(rows) is not list or not rows:
        _fail("file_pin_manifest_required", "/deployment/software_files_file")
    index = {}
    for i, row in enumerate(rows):
        field = "/software_files/" + str(i)
        _pin_schema(row, field)
        if row["path"] in index:
            _fail("duplicate_manifest_path", field + "/path")
        index[row["path"]] = row
    return index, actual


def _imports(index, roots, module_path):
    observed = []
    for name, module in sorted(sys.modules.copy().items()):
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        path = Path(filename).resolve(strict=True)
        if path != module_path and not any(path.is_relative_to(root) for root in roots):
            _fail("import_outside_selection", "/imports/" + name, path=str(path))
        observed.append({"module_name": name,
            "file": _selected_file(path, index, "/imports/" + name)})
    return observed


def _library_records(index, libraries=_LIBRARIES):
    records = []
    for module_name, distribution_name in libraries:
        library = sys.modules.get(module_name)
        if library is None or not getattr(library, "__file__", None):
            _fail("required_library_unavailable", "/libraries/" + module_name)
        distribution = metadata.distribution(distribution_name)
        files = distribution.files
        metadata_files = [] if files is None else [
            distribution.locate_file(row) for row in files
            if row.name in ("METADATA", "PKG-INFO")]
        if len(metadata_files) != 1:
            _fail("distribution_metadata_unavailable", "/libraries/" + module_name)
        distribution_version = distribution.version
        module_version = getattr(library, "__version__", None)
        if (type(distribution_version) is not str or not distribution_version
                or module_version is not None and module_version != distribution_version):
            _fail("library_version_identity_mismatch", "/libraries/" + module_name,
                module_version=module_version, distribution_version=distribution_version)
        records.append({"module_name": module_name, "distribution_name": distribution_name,
            "distribution_version": distribution_version, "module_version": module_version,
            "module_file": _selected_file(library.__file__, index, "/libraries/" + module_name),
            "metadata_file": _selected_file(metadata_files[0], index,
                "/libraries/" + module_name + "/metadata")})
    return records


def _failure(error, stage):
    return {"stage": stage, "code": getattr(error, "code",
        "molecular_sequence_" + stage + "_failed"),
        "path": getattr(error, "path", None), "details": getattr(error, "details", {}),
        "exception_type": type(error).__name__, "exception_module": type(error).__module__,
        "message": str(error), "traceback": traceback.format_exc()}


def execute_molecular_sequence_request(request):
    """Execute one complete private request under its already selected runtime.

    This does not launch an interpreter or resolve an artifact reference.
    Argument keys are closed; finite JSON values go unchanged to the genuine
    callable, including values that raise its original input errors. Biological
    validity and numerical interpretation remain with the existing readers.
    The canonical digest does not claim the host input file's byte identity.
    """
    if type(request) is dict and request.get("version") == REQUEST_VERSION_V3:
        return _execute_protease_request(request)
    result_version = (RESULT_VERSION_V2 if type(request) is dict
        and request.get("version") == REQUEST_VERSION_V2 else RESULT_VERSION)
    capture = {"version": result_version, "request": None,
        "request_canonical_sha256": None, "stage": "request", "native_record": None,
        "native_call_state": "not_started", "reference_data": None,
        "execution_receipt": {"software_files_file": None, "runtime": None,
            "helper_file": None, "module_load": {"state": "not_started", "source_file": None},
            "observed_callable": None, "libraries": [], "imported_files": []},
        "stdout": "", "stderr": "", "failure": None}
    saved_path, saved_bytecode = list(sys.path), sys.dont_write_bytecode
    previous_module = sys.modules.get(_MODULE_NAME)
    out, err = io.StringIO(), io.StringIO()
    try:
        _finite_json(request)
        encoded = _canonical(request)
        retained = json.loads(encoded)
        capture.update(request=retained, request_canonical_sha256=hashlib.sha256(encoded).hexdigest())
        _closed(retained, ("version", "operation", "arguments", "deployment"), "")
        if retained["version"] not in (REQUEST_VERSION, REQUEST_VERSION_V2):
            _fail("request_version_required", "/version")
        is_v2 = retained["version"] == REQUEST_VERSION_V2
        operations = _OPERATIONS_V2 if is_v2 else _OPERATIONS
        operation = retained["operation"]
        if type(operation) is not str or operation not in operations:
            _fail("operation_not_supported", "/operation")
        specification = operations[operation]
        source_profile = _SOURCE_PROFILES[specification["source"]]
        _closed(retained["arguments"], specification["fields"], "/arguments")
        record = {"schema": specification["schema"], "outcome": "failed", "result": None,
            "failure": None, "source_identity": None}
        capture["native_record"] = record
        deployment = retained["deployment"]
        capture["stage"] = "deployment_verification"
        _deployment(deployment,
            version=DEPLOYMENT_VERSION_V2 if is_v2 else DEPLOYMENT_VERSION,
            source_sha256=source_profile["sha256"])
        capture["stage"] = "software_manifest"
        index, manifest_file = _manifest(deployment)
        receipt = capture["execution_receipt"]
        receipt["software_files_file"] = manifest_file
        capture["stage"] = "runtime_verification"
        runtime = deployment["runtime"]
        executable, _ = _exact_file(runtime["executable"], "/deployment/runtime/executable")
        if Path(sys.executable).resolve(strict=True) != Path(executable["path"]):
            _fail("executing_interpreter_mismatch", "/deployment/runtime/executable")
        home = Path(runtime["home"]).resolve(strict=True)
        if not home.is_dir() or Path(sys.prefix).resolve(strict=True) != home:
            _fail("executing_runtime_home_mismatch", "/deployment/runtime/home")
        _selected_file(executable["path"], index, "/runtime/executable")
        helper = _selected_file(__file__, index, "/runtime/helper_file")
        stdlib = _selected_file(json.__file__, index, "/runtime/stdlib")
        if not Path(stdlib["path"]).is_relative_to(home):
            _fail("executing_stdlib_mismatch", "/runtime/stdlib")
        roots = [Path(value).resolve(strict=True) for value in deployment["import_roots"]]
        if any(not root.is_dir() for root in roots):
            _fail("import_root_directory_required", "/deployment/import_roots")
        receipt.update(helper_file=helper, runtime={"executable": executable,
            "sys_version": sys.version, "sys_prefix": str(home), "stdlib_file": stdlib})
        stdlib_paths = [value for value in saved_path if value and Path(value).is_absolute()
            and Path(value).resolve().is_relative_to(home)]
        sys.path[:] = [str(root) for root in roots] + stdlib_paths
        sys.dont_write_bytecode = True
        source_file, _ = _exact_file(deployment["module"], "/deployment/module")
        _selected_file(source_file["path"], index, "/source/module")
        module_path = Path(source_file["path"])
        capture["stage"] = "module_load"
        receipt["module_load"].update(state="loading", source_file=source_file)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            spec = importlib.util.spec_from_file_location(_MODULE_NAME, module_path)
            if spec is None or spec.loader is None:
                _fail("source_loader_unavailable", "/source/module")
            whole = importlib.util.module_from_spec(spec)
            sys.modules[_MODULE_NAME] = whole
            spec.loader.exec_module(whole)
            receipt["module_load"].update(state="loaded", module_name=whole.__name__,
                loader_type=type(spec.loader).__name__)
            capture["stage"] = "source_verification"
            if Path(whole.__file__).resolve(strict=True) != module_path:
                _fail("loaded_source_identity_mismatch", "/source/module")
            _exact_file(source_file, "/source/module")
            function = getattr(whole, operation)
            callable_identity = {"name": function.__name__, "module": function.__module__,
                "code_filename": function.__code__.co_filename,
                "sha256": hashlib.sha256(inspect.getsource(function).rstrip("\n").encode()).hexdigest()}
            if (callable_identity["name"] != operation or callable_identity["module"] != _MODULE_NAME
                    or Path(callable_identity["code_filename"]).resolve(strict=True) != module_path
                    or callable_identity["sha256"] != specification["sha256"]):
                _fail("original_callable_identity_mismatch", "/source/callable")
            if specification["source"] == "molecular" and (whole.pd is not sys.modules.get("pandas")
                    or whole.requests is not sys.modules.get("requests")
                    or whole.BeautifulSoup is not sys.modules["bs4"].BeautifulSoup
                    or whole.Seq is not sys.modules["Bio.Seq"].Seq):
                _fail("source_library_binding_mismatch", "/source/imports")
            receipt["libraries"] = _library_records(index, source_profile["libraries"])
            if operation == "annotate_open_reading_frames":
                from Bio.Data import CodonTable
                defaults = inspect.signature(whole.Seq.translate).parameters
                if defaults["table"].default != "Standard" or defaults["cds"].default is not False:
                    _fail("translation_defaults_unsupported", "/source/translation")
                bio_version = next(row["distribution_version"] for row in receipt["libraries"]
                    if row["module_name"] == "Bio")
                table = CodonTable.unambiguous_dna_by_id[1]
                capture["reference_data"] = {"source_file": _selected_file(
                    CodonTable.__file__, index, "/reference_data/source_file"),
                    "genetic_code_snapshot": {"code": 1, "names": list(table.names),
                        "start_codons": list(table.start_codons), "stop_codons": list(table.stop_codons),
                        "forward_table": dict(table.forward_table), "biopython_version": bio_version}}
                record.update(biopython_version=bio_version,
                    translation={"table": "Standard", "to_stop": True, "cds": False})
            receipt["imported_files"] = _imports(index, [home, *roots], module_path)
            receipt["observed_callable"] = callable_identity
            record["source_identity"] = {"path": source_file["path"], "callable": operation,
                "sha256": callable_identity["sha256"]}
            capture["stage"] = "call"
            capture["native_call_state"] = "running"
            result = function(**retained["arguments"])
            capture["native_call_state"] = "returned"
            capture["stage"] = "serialization"
            record["result"] = json.loads(json.dumps(result, allow_nan=False))
            record["outcome"] = "completed"
            capture["stage"] = "post_call_verification"
            receipt["imported_files"] = _imports(index, [home, *roots], module_path)
            _exact_file(source_file, "/source/module")
        capture["stage"] = "completed"
    except Exception as error:
        failure = _failure(error, capture["stage"])
        capture["failure"] = failure
        if capture["native_call_state"] == "running":
            capture["native_call_state"] = "raised"
        if capture["execution_receipt"]["module_load"]["state"] == "loading":
            capture["execution_receipt"]["module_load"]["state"] = "failed"
        if capture["native_record"] is not None:
            capture["native_record"].update(
                outcome="partial" if capture["native_record"]["result"] is not None else "failed",
                failure=deepcopy(failure))
    finally:
        capture.update(stdout=out.getvalue(), stderr=err.getvalue())
        sys.path[:] = saved_path
        sys.dont_write_bytecode = saved_bytecode
        if previous_module is None:
            sys.modules.pop(_MODULE_NAME, None)
        else:
            sys.modules[_MODULE_NAME] = previous_module
    return capture


_PROTEASE_LOCALS = ("time_points", "fluorescence_data", "substrate_concentrations", "enzyme_concentration",
    "initial_velocities", "num_points", "params", "covariance", "vmax", "km", "std_dev", "vmax_std",
    "km_std", "kcat", "kcat_std", "catalytic_efficiency", "catalytic_efficiency_std")
_PROTEASE_ARGUMENTS = {"time_points", "fluorescence_data", "substrate_concentrations", "enzyme_concentration",
    "output_prefix", "output_dir"}
_BIOCHEMISTRY_LIBRARIES = (("numpy", "numpy"), ("scipy", "scipy"), ("matplotlib", "matplotlib"))


def _observed_json(value):
    """Serialize actual native objects, preserving nonfinite values explicitly."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else {"type": "nonfinite", "token": value.hex()}
    if type(value) in (list, tuple):
        return [_observed_json(item) for item in value]
    if type(value).__module__.split(".")[0] == "numpy":
        if hasattr(value, "shape") and hasattr(value, "tolist") and len(value.shape) > 0:
            return {"type": "ndarray", "dtype": str(value.dtype), "shape": list(value.shape),
                "values": _observed_json(value.tolist())}
        if hasattr(value, "item"):
            return {"type": "numpy_scalar", "dtype": str(value.dtype), "value": _observed_json(value.item())}
    return {"type": "unsupported", "python_type": type(value).__module__ + "." + type(value).__qualname__}


def _observer_failure(error, stage):
    return {"stage": stage, "exception_type": type(error).__name__, "exception_module": type(error).__module__,
        "message": str(error)}


def _observer_problem(observation, error, stage):
    # Even failure-reporting failure cannot replace the selected call outcome.
    try:
        observation["failures"].append(_observer_failure(error, stage))
    except BaseException:
        pass


def _call_with_return_observer(function, arguments, observation):
    """Call once. Only read the selected frame; recorder failures cannot escape."""
    raw_locals = {}
    previous = None
    profile_readable = True
    try:
        previous = sys.getprofile()
    except BaseException as error:
        profile_readable = False
        _observer_problem(observation, error, "profile_state")
    installed = False
    selected_frame = None
    def observe(frame, event, arg):
        nonlocal selected_frame
        try:
            if frame.f_code is not function.__code__:
                return
            if event == "call":
                observation["selected_call_count"] += 1
                if selected_frame is None:
                    selected_frame = frame
            elif event == "return" and frame is selected_frame:
                observation["selected_terminal_event_count"] += 1
                fields = frame.f_locals
                raw_locals.update({name: fields[name] for name in _PROTEASE_LOCALS if name in fields})
                observation["state"] = "captured"
        except BaseException as error:
            try:
                _observer_problem(observation, error, "callback")
                observation["state"] = "failed"
            except BaseException:
                pass
    if not profile_readable:
        observation.update(state="unavailable", reason="profile_state_unavailable")
    elif previous is not None:
        observation.update(state="unavailable", reason="existing_profile_preserved")
    else:
        try:
            sys.setprofile(observe)
            installed = True
            observation["state"] = "observing"
        except BaseException as error:
            observation["state"] = "failed"
            _observer_problem(observation, error, "install")
    try:
        return function(**arguments)
    finally:
        if installed:
            try:
                sys.setprofile(previous)
                observation["profile_restored"] = sys.getprofile() is previous
                if not observation["profile_restored"]:
                    _observer_problem(observation, RuntimeError("profile_restoration_not_observed"), "cleanup")
            except BaseException as error:
                observation["profile_restored"] = False
                _observer_problem(observation, error, "cleanup")
        else:
            observation["profile_restored"] = None
        for name, value in raw_locals.items():
            try:
                observation["locals"][name] = _observed_json(value)
            except BaseException as error:
                _observer_problem(observation, error, "serialize:" + name)
        selected_frame = None
        raw_locals.clear()


def _protease_workspace(request):
    workspace = _path(request["output_workspace"], "/output_workspace").resolve(strict=True)
    if not workspace.is_dir():
        _fail("output_workspace_required", "/output_workspace")
    arguments = request["arguments"]
    prefix = arguments["output_prefix"]
    if type(prefix) is not str or not prefix or prefix in {".", ".."} or any(c in prefix for c in "/\\\0\n\r"):
        _fail("output_basename_required", "/arguments/output_prefix")
    output = _path(arguments["output_dir"], "/arguments/output_dir").resolve()
    if not output.is_relative_to(workspace):
        _fail("native_output_outside_workspace", "/arguments/output_dir")
    for suffix in ("_results.txt", "_mm_plot.png"):
        if (output / (prefix + suffix)).is_symlink():
            _fail("native_symlink_output_unsupported", "/arguments/output_prefix")
    environment = request["environment"]
    _closed(environment, ("MPLBACKEND", "MPLCONFIGDIR", "XDG_CACHE_HOME"), "/environment")
    if environment["MPLBACKEND"] != "Agg":
        _fail("explicit_agg_backend_required", "/environment/MPLBACKEND")
    for key in ("MPLCONFIGDIR", "XDG_CACHE_HOME"):
        directory = _path(environment[key], "/environment/" + key).resolve()
        if not directory.is_relative_to(workspace):
            _fail("cache_outside_workspace", "/environment/" + key)
        directory.mkdir(parents=True, exist_ok=True)
    return workspace


def _execute_protease_request(request):
    """v3 alone adds an unchanged biochemical call and passive observation."""
    capture = {"version": RESULT_VERSION_V3, "request": None, "request_canonical_sha256": None,
        "stage": "request", "native_record": None, "native_call_state": "not_started", "reference_data": None,
        "execution_receipt": {"software_files_file": None, "runtime": None, "helper_file": None,
            "module_load": {"state": "not_started", "source_file": None}, "observed_callable": None,
            "libraries": [], "imported_files": []}, "stdout": "", "stderr": "", "failure": None,
        "observer": {"schema": "native_selected_return_observation_v1", "mechanism": "selected_code_return_profile",
            "state": "not_started", "reason": None, "selected_call_count": 0, "selected_terminal_event_count": 0,
            "profile_restored": None, "locals": {}, "failures": []}, "verification_failures": []}
    saved_path, saved_bytecode = list(sys.path), sys.dont_write_bytecode
    previous_module = sys.modules.get(_MODULE_NAME)
    saved_environment = {}
    out, err = io.StringIO(), io.StringIO()
    try:
        _finite_json(request)
        encoded = _canonical(request)
        retained = json.loads(encoded)
        capture.update(request=retained, request_canonical_sha256=hashlib.sha256(encoded).hexdigest())
        _closed(retained, ("version", "operation", "arguments", "deployment", "output_workspace", "environment"), "")
        if retained["version"] != REQUEST_VERSION_V3 or retained["operation"] != "analyze_protease_kinetics":
            _fail("operation_not_supported", "/operation")
        _closed(retained["arguments"], _PROTEASE_ARGUMENTS, "/arguments")
        _protease_workspace(retained)
        if "matplotlib" in sys.modules:
            _fail("preloaded_matplotlib_state_unverified", "/environment")
        for key, value in retained["environment"].items():
            saved_environment[key] = os.environ.get(key)
            os.environ[key] = value
        record = {"schema": "biomni_protease_kinetics_native_v1", "outcome": "not_called", "result_kind": None,
            "result": None, "failure": None, "source_identity": None}
        capture["native_record"] = record
        deployment = retained["deployment"]
        capture["stage"] = "deployment_verification"
        _deployment(deployment, version=DEPLOYMENT_VERSION_V3, source_sha256=BIOCHEMISTRY_SOURCE_SHA256)
        capture["stage"] = "software_manifest"
        index, manifest_file = _manifest(deployment)
        receipt = capture["execution_receipt"]
        receipt["software_files_file"] = manifest_file
        capture["stage"] = "runtime_verification"
        runtime = deployment["runtime"]
        executable, _ = _exact_file(runtime["executable"], "/deployment/runtime/executable")
        home = Path(runtime["home"]).resolve(strict=True)
        if Path(sys.executable).resolve(strict=True) != Path(executable["path"]) or Path(sys.prefix).resolve(strict=True) != home:
            _fail("executing_runtime_mismatch", "/deployment/runtime")
        _selected_file(executable["path"], index, "/runtime/executable")
        helper = _selected_file(__file__, index, "/runtime/helper_file")
        stdlib = _selected_file(json.__file__, index, "/runtime/stdlib")
        if not Path(stdlib["path"]).is_relative_to(home):
            _fail("executing_stdlib_mismatch", "/runtime/stdlib")
        roots = [Path(value).resolve(strict=True) for value in deployment["import_roots"]]
        if any(not root.is_dir() for root in roots):
            _fail("import_root_directory_required", "/deployment/import_roots")
        receipt.update(helper_file=helper, runtime={"executable": executable, "sys_version": sys.version,
            "sys_prefix": str(home), "stdlib_file": stdlib}, environment=deepcopy(retained["environment"]))
        stdlib_paths = [value for value in saved_path if value and Path(value).is_absolute() and Path(value).resolve().is_relative_to(home)]
        sys.path[:] = [str(root) for root in roots] + stdlib_paths
        sys.dont_write_bytecode = True
        source_file, _ = _exact_file(deployment["module"], "/deployment/module")
        _selected_file(source_file["path"], index, "/source/module")
        module_path = Path(source_file["path"])
        capture["stage"] = "module_load"
        receipt["module_load"].update(state="loading", source_file=source_file)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            spec = importlib.util.spec_from_file_location(_MODULE_NAME, module_path)
            if spec is None or spec.loader is None:
                _fail("source_loader_unavailable", "/source/module")
            whole = importlib.util.module_from_spec(spec)
            sys.modules[_MODULE_NAME] = whole
            spec.loader.exec_module(whole)
            receipt["module_load"].update(state="loaded", module_name=whole.__name__, loader_type=type(spec.loader).__name__)
            capture["stage"] = "source_verification"
            function = whole.analyze_protease_kinetics
            callable_identity = {"name": function.__name__, "module": function.__module__,
                "code_filename": function.__code__.co_filename,
                "sha256": hashlib.sha256(inspect.getsource(function).rstrip("\n").encode()).hexdigest()}
            if (callable_identity["name"] != "analyze_protease_kinetics" or callable_identity["module"] != _MODULE_NAME
                    or Path(callable_identity["code_filename"]).resolve(strict=True) != module_path
                    or callable_identity["sha256"] != PROTEASE_FUNCTION_SHA256):
                _fail("original_callable_identity_mismatch", "/source/callable")
            _exact_file(source_file, "/source/module")
            receipt["observed_callable"] = callable_identity
            record["source_identity"] = {"path": source_file["path"], "callable": function.__name__, "sha256": callable_identity["sha256"]}
            capture["stage"] = "pre_call_verification"
            try:
                receipt["imported_files"] = _imports(index, [home, *roots], module_path)
            except BaseException as error:
                capture["verification_failures"].append(_failure(error, "pre_call_verification"))
                return capture
            capture["stage"] = "call"
            capture["native_call_state"] = "running"
            try:
                result = _call_with_return_observer(function, retained["arguments"], capture["observer"])
            except BaseException as error:
                failure = _failure(error, "call")
                capture.update(native_call_state="raised", failure=failure)
                record.update(outcome="raised", failure=deepcopy(failure))
            else:
                capture["native_call_state"] = "returned"
                source_error = type(result) is str and result.startswith("Error during analysis:")
                record.update(result=result, outcome="source_error" if source_error else "completed",
                    result_kind="source_error_string" if source_error else "analysis_report" if type(result) is str else "unexpected_return")
            capture["stage"] = "post_call_verification"
            # These inspect only modules actually imported by the genuine call.
            for library in _BIOCHEMISTRY_LIBRARIES:
                try:
                    receipt["libraries"].extend(_library_records(index, (library,)))
                except BaseException as error:
                    capture["verification_failures"].append(_observer_failure(error, "library:" + library[0]))
            try:
                plotting = sys.modules.get("matplotlib")
                if plotting is not None:
                    effective = {"backend": plotting.get_backend(), "config_directory": plotting.get_configdir(),
                        "cache_directory": plotting.get_cachedir()}
                    receipt["matplotlib_environment"] = effective
                    workspace = Path(retained["output_workspace"]).resolve()
                    if (str(effective["backend"]).lower() != "agg"
                            or Path(effective["config_directory"]).resolve() != Path(retained["environment"]["MPLCONFIGDIR"]).resolve()
                            or not Path(effective["cache_directory"]).resolve().is_relative_to(workspace)):
                        _fail("effective_matplotlib_environment_conflict", "/environment")
            except BaseException as error:
                capture["verification_failures"].append(_observer_failure(error, "matplotlib_environment"))
            for stage, verify in (("imports", lambda: receipt.update(imported_files=_imports(index, [home, *roots], module_path))),
                    ("source", lambda: _exact_file(source_file, "/source/module"))):
                try:
                    verify()
                except BaseException as error:
                    capture["verification_failures"].append(_observer_failure(error, stage))
        capture["stage"] = "completed"
    except Exception as error:
        # Only pre-call setup reaches this handler; post-call verification owns
        # separate failures and cannot replace a real native outcome.
        failure = _failure(error, capture["stage"])
        if capture["native_call_state"] in {"returned", "raised"}:
            capture["verification_failures"].append(failure)
        else:
            capture["failure"] = failure
        if capture["execution_receipt"]["module_load"]["state"] == "loading":
            capture["execution_receipt"]["module_load"]["state"] = "failed"
    finally:
        capture.update(stdout=out.getvalue(), stderr=err.getvalue())
        sys.path[:] = saved_path
        sys.dont_write_bytecode = saved_bytecode
        for key, value in saved_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if previous_module is None:
            sys.modules.pop(_MODULE_NAME, None)
        else:
            sys.modules[_MODULE_NAME] = previous_module
    return capture


__all__ = ["REQUEST_VERSION", "DEPLOYMENT_VERSION", "RESULT_VERSION",
    "REQUEST_VERSION_V2", "DEPLOYMENT_VERSION_V2", "RESULT_VERSION_V2",
    "REQUEST_VERSION_V3", "DEPLOYMENT_VERSION_V3", "RESULT_VERSION_V3",
    "execute_molecular_sequence_request"]
