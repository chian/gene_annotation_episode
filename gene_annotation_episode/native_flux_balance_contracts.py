"""Execution envelope for one selected, source-derived Cobra/GLPK FBA call.

Analytical records are owned by ``flux_balance_contracts``. This module only
validates execution paths, the selected software closure and the run envelope.
It neither discovers a resource nor starts work.
"""
from copy import deepcopy
import os
from pathlib import PurePosixPath

from .execution_contracts import canonical, digest
from .flux_balance_contracts import validate_flux_balance_record

RUN_PLAN_FILENAME = "flux-balance-plan.json"
ATTEMPT_DIRECTORY_NAME = "flux-balance-attempt"
OWNER_FILENAME = ".native-flux-balance-owner.json"
STARTED_FILENAME = ".native-flux-balance-started.json"
SOLVE_ENTERED_FILENAME = ".native-flux-balance-solve-entered.json"
ENVIRONMENT_FILENAME = ".native-flux-balance-environment.json"
DRIVER_MODULE = "gene_annotation_episode.native_flux_balance_driver"
POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
SOURCE_FUNCTION_SHA256 = "ab47e2640366833d05cf896091e1c3803ce69aae940bfa46ba993abda51983b9"
STACK = {"cobra": "0.32.1", "optlang": "1.9.1", "swiglpk": "5.0.13", "python-libsbml": "5.21.2"}
ARTIFACT_FORMATS = {
    "selected_request": "flux_balance_selected_request_v1", "effective_model": "cobra_model_capture_v1",
    "effective_problem": "cobra_glpk_problem_capture_v1", "solution": "cobra_glpk_solution_capture_v1",
    "flux_csv": "biomni_fba_csv_v1", "native_log": "utf8_text", "manifest": "flux_balance_native_manifest_v1",
}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def path_value(value, *, absolute):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "fba_invalid_path")
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
            and value not in (".", "/") and not value.startswith("//"), "fba_invalid_path")
    return path


def validate_flux_balance_software(value):
    value = validate_flux_balance_record("FBASoftware", value)
    require(value["solver_interface"] == "optlang.glpk_interface", "solver_unavailable")
    for field in ("python_home", "module_root"):
        path_value(value[field], absolute=True)
    roots = [path_value(p, absolute=True) for p in value["dependency_roots"]]
    require(roots and len(set(roots)) == len(roots), "fba_dependency_root_unbound")
    pins = [value["python"], *value["implementation_files"], *value["runtime_files"], *value["solver_runtime_files"]]
    paths = [str(path_value(p["path"], absolute=True)) for p in pins]
    require(len(paths) == len(set(paths)), "fba_duplicate_software_file")
    required = {str(PurePosixPath(value["module_root"]) / "gene_annotation_episode" / filename) for filename in (
        "__init__.py", "execution_contracts.py", "flux_balance_contracts.py", "native_flux_balance_contracts.py",
        "native_flux_balance_storage.py", "native_flux_balance_cobra_glpk.py", "native_flux_balance_driver.py")}
    require(required <= {p["path"] for p in value["implementation_files"]}, "fba_implementation_closure_incomplete")
    distributions = {p["name"].lower().replace("_", "-"): p["version"] for p in value["distributions"]}
    require(len(distributions) == len(value["distributions"]) and all(distributions.get(k) == v for k, v in STACK.items()),
            "fba_distribution_selection_mismatch")
    require(value["runtime_files"] and value["solver_runtime_files"], "fba_runtime_closure_incomplete")
    require(all(any(PurePosixPath(p["path"]).is_relative_to(root) for p in value["runtime_files"]) for root in roots),
            "fba_dependency_root_unbound")
    require(any(PurePosixPath(p["path"]).is_relative_to(PurePosixPath(value["python_home"]) / "lib")
                for p in value["runtime_files"]), "fba_standard_library_binding_missing")
    return value


def flux_balance_environment(software, *, attempt_directory, lifecycle_directory):
    software = validate_flux_balance_software(software)
    attempt = path_value(attempt_directory, absolute=True)
    lifecycle = path_value(lifecycle_directory, absolute=True)
    require(attempt == lifecycle / ATTEMPT_DIRECTORY_NAME, "fba_original_attempt_mismatch")
    return {"PYTHONPATH": os.pathsep.join([software["module_root"], *software["dependency_roots"]]),
            "PYTHONHOME": software["python_home"], "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
            "TMPDIR": str(lifecycle), "TMP": str(lifecycle), "TEMP": str(lifecycle),
            "XDG_CACHE_HOME": str(attempt / "cache"), "PIP_CACHE_DIR": str(attempt / "cache/pip")}


def validate_flux_balance_requested_job(value):
    value = validate_flux_balance_record("FBARequestedJob", value)
    job = value["native_flux_balance"]
    software = validate_flux_balance_software(job["software"])
    require(job["source_function_sha256"] == SOURCE_FUNCTION_SHA256, "fba_source_function_mismatch")
    path_value(job["model_input"]["file"]["path"], absolute=True)
    prefix = path_value(job["output_prefix"], absolute=False)
    path_value(job["flux_output_name"], absolute=False)
    require(not prefix.parts[0].startswith(".") and prefix.parts[0] not in {"tmp", "cache"}, "fba_invalid_output_prefix")
    lifecycle = value["environment"].get("TMPDIR")
    require(type(lifecycle) is str, "fba_runtime_environment_mismatch")
    expected = flux_balance_environment(software, attempt_directory=str(PurePosixPath(lifecycle) / ATTEMPT_DIRECTORY_NAME),
                                        lifecycle_directory=lifecycle)
    require(value["environment"] == expected, "fba_runtime_environment_mismatch")
    require(value["argv"] == [software["python"]["path"], "-B", "-S", "-m", DRIVER_MODULE, RUN_PLAN_FILENAME],
            "fba_requested_argv_mismatch")
    flux_balance_output_files(job)
    return value


def flux_balance_output_files(job):
    job = validate_flux_balance_record("FBAJob", job)
    prefix = path_value(job["output_prefix"], absolute=False)
    names = {"original_model": "original-model.xml" if job["model_input"]["format"] == "sbml" else "original-model.json",
             "selected_request": "selected-request.json", "effective_model": "model-capture.json",
             "effective_problem": "problem-capture.json", "solution": "solution-capture.json",
             "flux_csv": job["flux_output_name"], "native_log": "native-log.txt", "manifest": "native-manifest.json"}
    paths = [prefix / path_value(name, absolute=False) for name in names.values()]
    require(len(paths) == len(set(paths)) and not any(a.is_relative_to(b) for a in paths for b in paths if a != b),
            "fba_output_role_mismatch")
    return [{"role": role, "relative_path": str(prefix / names[role]),
             "format": job["model_input"]["format"] if role == "original_model" else ARTIFACT_FORMATS[role]}
            for role in names]


def bind_flux_balance_environment(requested_job, *, execution_id, attempt_directory, selection):
    """Describe only explicitly selected path realization; grant no authority.

    The original requested job remains untouched. The host must authenticate the
    selection against the original commission before executing this binding.
    """
    request = validate_flux_balance_requested_job(requested_job)
    execution = path_value(execution_id, absolute=True)
    require(execution.name in ("native.json", "intent.json"), "fba_original_attempt_mismatch")
    actual = flux_balance_environment(request["native_flux_balance"]["software"],
        attempt_directory=attempt_directory, lifecycle_directory=str(execution.parent))
    selected = request["environment"]
    if selection is None:
        require(selected == actual, "fba_runtime_environment_mismatch")
    else:
        require(type(selection) is dict and selection == {
            "version": "flux_balance_execution_selection_v1",
            "environment_realization": "operation_scoped_tmp_and_cache_v1"}, "fba_environment_selection_invalid")
    names = ("TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME", "PIP_CACHE_DIR")
    require({k: v for k, v in selected.items() if k not in names}
            == {k: v for k, v in actual.items() if k not in names}, "fba_runtime_environment_mismatch")
    return {"version": "flux_balance_environment_binding_v1", "selection": deepcopy(selection),
        "requested_job_sha256": digest(request), "requested_environment": deepcopy(selected),
        "realized_environment": actual, "relocations": [
            {"name": name, "selected": selected[name], "realized": actual[name]} for name in names]}


def validate_flux_balance_environment_binding(value, *, requested_job, execution_id, attempt_directory, selection):
    expected = bind_flux_balance_environment(requested_job, execution_id=execution_id,
        attempt_directory=attempt_directory, selection=selection)
    require(type(value) is dict and canonical(value) == canonical(expected), "fba_environment_binding_mismatch")
    return deepcopy(expected)


def validate_flux_balance_run_plan(value):
    require(type(value) is dict and value.get("version") in ("flux_balance_run_plan_v1", "flux_balance_run_plan_v2"),
            "fba_invalid_run_plan")
    is_v2 = value["version"] == "flux_balance_run_plan_v2"
    keys = {"version", "identity", "requested_job", "attempt_directory", "policy", "outputs"}
    require(set(value) == keys | ({"environment_binding"} if is_v2 else set()), "fba_invalid_run_plan")
    request = validate_flux_balance_requested_job(value["requested_job"])
    owner = validate_flux_balance_record("FBAAttemptIdentity", value["identity"])
    execution = path_value(owner["execution_id"], absolute=True)
    attempt = path_value(value["attempt_directory"], absolute=True)
    from .terminal_scientific_evidence import terminal_plan_identity
    legacy = (execution.name == "native.json" and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME
            and execution.parent.name == owner["attempt_id"]
            and execution.parent.parent.name == digest({"run": owner["run_id"], "episode": owner["episode_id"]})
            and execution.parent.parent.parent.name == ".episode-operations")
    require((legacy or terminal_plan_identity(owner, attempt_directory=str(attempt)))
            and owner["attempt_id"] == digest(owner["operation_key"])
            and owner["requested_job_sha256"] == digest(request), "fba_original_attempt_mismatch")
    if is_v2:
        binding = value["environment_binding"]
        require(type(binding) is dict and binding.get("selection") is not None, "fba_environment_selection_invalid")
        validate_flux_balance_environment_binding(binding, requested_job=request, execution_id=str(execution),
            attempt_directory=str(attempt), selection=binding["selection"])
    else:
        require(request["environment"] == flux_balance_environment(request["native_flux_balance"]["software"],
                attempt_directory=str(attempt), lifecycle_directory=str(execution.parent)), "fba_runtime_environment_mismatch")
    require(canonical(value["policy"]) == canonical(POLICY), "fba_original_allocation_mismatch")
    require(value["outputs"] == flux_balance_output_files(request["native_flux_balance"]), "fba_output_role_mismatch")
    job = request["native_flux_balance"]
    protected = [job["model_input"]["file"]["path"], job["software"]["python_home"], job["software"]["module_root"],
                 *job["software"]["dependency_roots"], *[p["path"] for p in job["software"]["solver_runtime_files"]]]
    require(all(not PurePosixPath(p).is_relative_to(execution.parent) and not execution.parent.is_relative_to(PurePosixPath(p))
                for p in protected), "fba_input_output_overlap")
    return deepcopy(value)


def flux_balance_driver_argv(plan):
    plan = validate_flux_balance_run_plan(plan)
    return [*plan["requested_job"]["argv"][:-1], str(PurePosixPath(plan["identity"]["execution_id"]).parent / RUN_PLAN_FILENAME)]
