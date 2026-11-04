"""Closed selected native chromatin operands and original-attempt joins.

These validators consume supplied records only. They grant no file authority,
execute no producer, and make no scientific/resource/continuation decisions.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import PurePosixPath
import re

from .chromatin_interaction_contracts import chromatin_record_schema, validate_chromatin_record

RUN_PLAN_FILENAME = "chromatin-plan.json"
ATTEMPT_DIRECTORY_NAME = "chromatin-interaction-attempt"
BUNDLE_FILENAME = "bundle.json"
OWNER_FILENAME = ".native-chromatin-owner.json"
STARTED_FILENAME = ".native-chromatin-started.json"
DRIVER_MODULE = "gene_annotation_episode.native_chromatin_interaction_driver"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
TABLE_ROLES = ("bins", "contacts", "weights", "cell_states", "dense_values")
TABLE_NAMES = ("bins.tsv", "contacts.npy", "weights.npy", "cell-states.npy", "dense-values.npy")
REQUIRED_DEPENDENCIES = {"numpy", "h5py", "jsonschema", "attrs", "referencing", "rpds-py", "jsonschema-specifications"}
REQUIRED_MODULES = {DRIVER_MODULE, "gene_annotation_episode.native_chromatin_interaction_contracts",
    "gene_annotation_episode.chromatin_interaction_contracts", "gene_annotation_episode.chromatin_cooler_inputs",
    "gene_annotation_episode.chromatin_interaction_inputs"}


def require(condition, code="original_attempt_mismatch"):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def path_value(value, *, absolute):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "invalid_output_path")
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
        and value not in (".", "/") and not value.startswith("//"), "invalid_output_path")
    return path


def failure(code, stage, *, input_key=None, population_key=None, element_key=None,
        pair_key=None, artifact_ref=None, locator=None, field_path=None,
        partial_artifact_refs=(), requirement="matching_file_identity"):
    return validate_chromatin_record("Failure", {"code": code, "stage": stage, "input_key": input_key,
        "population_key": population_key, "element_key": element_key, "pair_key": pair_key,
        "artifact_ref": artifact_ref, "locator": locator, "field_path": field_path,
        "partial_artifact_refs": list(partial_artifact_refs), "requirement": requirement})


def unique_failures(*groups):
    return list({digest(row): row for group in groups for row in group}.values())


def validate_chromatin_software(value):
    value = validate_chromatin_record("SoftwareBinding", value)
    for key in ("python_executable", "module_root"):
        path_value(value[key], absolute=True)
    modules = [r["module"] for r in value["implementation_files"]]
    require(len(set(modules)) == len(modules) and REQUIRED_MODULES <= set(modules), "native_dependency_unavailable")
    require(all(re.fullmatch(r"gene_annotation_episode(?:\.[A-Za-z_]\w*)+", n, re.ASCII) for n in modules),
        "native_dependency_unavailable")
    dependencies = value["dependencies"]
    names = [r["distribution"].lower().replace("_", "-") for r in dependencies]
    require(len(names) == len(set(names)) and REQUIRED_DEPENDENCIES <= set(names), "native_dependency_unavailable")
    for dependency in dependencies:
        path_value(dependency["package_root"], absolute=True)
        paths = [str(path_value(r["path"], absolute=True)) for r in dependency["files"]]
        require(len(paths) == len(set(paths)), "native_dependency_unavailable")
    return value


def validate_chromatin_bindings(values):
    require(type(values) is list)
    result = [validate_chromatin_record("Binding", value) for value in values]
    for row in result:
        validate_chromatin_software(row["software"])
        require(row["supported_formats"] == ["cooler_hdf5_v3"], "unsupported_native_format")
    require(len({digest(row) for row in result}) == len(result))
    return result


def chromatin_interaction_execution_schema(kind, *, bindings=None):
    schema = chromatin_record_schema(kind)
    if bindings is not None:
        require(kind == "RequestedJob")
        rows = validate_chromatin_bindings(bindings)
        selected = [{"properties": {"native_chromatin_interactions": {"properties": {
            "software": {"const": row["software"]}, "request": {"properties": {
                "contact": {"properties": {"format": {"enum": row["supported_formats"]}}},
                "analysis_modes": {"items": {"enum": row["analysis_modes"]}}}}}}}} for row in rows]
        schema = {"allOf": [schema, {"anyOf": selected} if selected else {"not": {}}]}
    return schema


def validate_chromatin_job(value):
    value = validate_chromatin_record("NativeJob", value)
    request = value["request"]
    validate_chromatin_software(value["software"])
    require(request["contact"]["format"] == "cooler_hdf5_v3", "unsupported_native_format")
    specs = [request["contact"]] + ([request["elements"]] if request["elements"] is not None else [])
    require([r["input_key"] for r in value["input_bindings"]] == [r["input_key"] for r in specs])
    require(len({r["input_key"] for r in specs}) == len(specs))
    paths = {}
    for binding, spec in zip(value["input_bindings"], specs):
        require(binding["file"] == spec["file"] and spec["file"]["format"] == spec["format"])
        path = path_value(binding["path"], absolute=True)
        if path in paths:
            require(paths[path] == binding["file"])
        paths[path] = binding["file"]
    return value


def _environment(value):
    value = validate_chromatin_record("Environment", value)
    require(all("\0" not in text for text in value.values()), "invalid_native_environment")
    require(all(value[key] == "1" for key in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE",
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")), "invalid_native_environment")
    for key in ("PYTHONHOME", "TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR"):
        path_value(value[key], absolute=True)
    for path in value["PYTHONPATH"].split(os.pathsep):
        path_value(path, absolute=True)


def _dependency_roots(software):
    dependencies = sorted(software["dependencies"], key=lambda r: r["distribution"].lower() not in {"numpy", "h5py"})
    return list(dict.fromkeys(str(PurePosixPath(r["package_root"]).parent) for r in dependencies))


def requested_job_from_chromatin(job, *, environment=None):
    job = validate_chromatin_job(job)
    require(environment is not None, "explicit_runtime_environment_required")
    environment = deepcopy(environment)
    _environment(environment)
    require(environment["PYTHONPATH"] == os.pathsep.join([job["software"]["module_root"], *_dependency_roots(job["software"])]),
        "native_dependency_unavailable")
    return {"argv": [job["software"]["python_executable"], "-B", "-S", "-m", DRIVER_MODULE, RUN_PLAN_FILENAME],
        "environment": environment, "native_chromatin_interactions": job}


def validate_chromatin_requested_job(value):
    value = validate_chromatin_record("RequestedJob", value)
    require(value == requested_job_from_chromatin(value["native_chromatin_interactions"], environment=value["environment"]))
    return value


def chromatin_output_files(request):
    request = validate_chromatin_record("ChromatinRequest", request)
    path_value(request["output_prefix"], absolute=False)
    rows = []
    def add(key, population, role, path, format):
        rows.append({"file_key": key, "population_key": population, "role": role,
            "relative_path": request["output_prefix"] + "/" + path, "format": format})
    for ordinal, population in enumerate(request["populations"]):
        for role, name in zip(TABLE_ROLES, TABLE_NAMES):
            add(f"p{ordinal}.{role}", population["population_key"], role,
                f"populations/p{ordinal}/{name}", "chromatin_contact_tables_v1:" + role)
    add("original_contact", None, "original_contact", "inputs/contact.native", request["contact"]["format"])
    add("original_elements", None, "original_elements", "inputs/elements.bed", "bed_outer_span_v1")
    add("original_metadata", None, "original_metadata", "inputs/metadata.json", "chromatin_supplied_metadata_v1")
    for ordinal, population in enumerate(request["populations"]):
        add(f"p{ordinal}.population_manifest", population["population_key"], "population_manifest",
            f"populations/p{ordinal}/manifest.json", "chromatin_interaction_population_seal_v1")
    add("stdout", None, "stdout", "stdout.log", "native_stdout")
    add("stderr", None, "stderr", "stderr.log", "native_stderr")
    add("bundle", None, "bundle", BUNDLE_FILENAME, "chromatin_interaction_native_bundle_v1")
    return rows


def validate_chromatin_run_plan(value):
    value = validate_chromatin_record("RunPlan", value)
    requested = validate_chromatin_requested_job(value["requested_job"])
    identity = value["identity"]
    execution = path_value(identity["execution_id"], absolute=True)
    attempt = path_value(value["attempt_directory"], absolute=True)
    require(execution.name == "native.json" and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME)
    require(identity["attempt_id"] == digest(identity["operation_key"]) and identity["requested_job_sha256"] == digest(requested))
    require(execution.parent.name == identity["attempt_id"] and execution.parent.parent.name ==
        digest({"run": identity["run_id"], "episode": identity["episode_id"]}) and
        execution.parent.parent.parent.name == ".episode-operations")
    require(value["policy"] == POLICY and type(value["policy"]["memory_bytes"]) is int
        and type(value["policy"]["scratch_bytes"]) is int)
    require(value["outputs"] == chromatin_output_files(requested["native_chromatin_interactions"]["request"]))
    for binding in requested["native_chromatin_interactions"]["input_bindings"]:
        path = path_value(binding["path"], absolute=True)
        require(path != execution.parent and execution.parent not in path.parents and path not in execution.parent.parents)
    return value


def chromatin_driver_argv(plan):
    plan = validate_chromatin_run_plan(plan)
    return [*plan["requested_job"]["argv"][:-1], str(PurePosixPath(plan["identity"]["execution_id"]).parent / RUN_PLAN_FILENAME)]


def chromatin_environment(job, *, attempt_directory, environment=None):
    job = validate_chromatin_job(job)
    root = path_value(attempt_directory, absolute=True)
    software = job["software"]
    # Dependency binding order fixes precedence. NumPy/h5py's site root must
    # precede auxiliary schema packages; never prepend an unrelated venv.
    require(environment is not None, "explicit_runtime_environment_required")
    _environment(environment)
    roots = _dependency_roots(software)
    return {**environment, "PYTHONPATH": os.pathsep.join([software["module_root"], *roots]),
        "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"), "TMPDIR": str(root / "tmp"),
        "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip"),
        "HDF5_PLUGIN_PATH": str(root / "unbound-hdf5-plugins"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}


def validate_chromatin_population_seal(value, *, plan, population):
    plan = validate_chromatin_run_plan(plan)
    value = validate_chromatin_record("PopulationSeal", value)
    request = plan["requested_job"]["native_chromatin_interactions"]["request"]
    require(population in request["populations"] and value["identity"] == plan["identity"]
        and value["request_sha256"] == digest(request) and value["population"]["selected_region"] == population)
    require(value["input_files"] == [r["file"] for r in plan["requested_job"]["native_chromatin_interactions"]["input_bindings"]])
    specifications = [r for r in plan["outputs"] if r["population_key"] == population["population_key"] and r["role"] in TABLE_ROLES]
    require([r["draft"]["role"] for r in value["tables"]] == list(TABLE_ROLES))
    require(value["population"]["data_table_keys"] == [r["draft"]["table_key"] for r in value["tables"]])
    header = value["native"]
    require(value["population"]["extent"] != "complete" or header["metadata"] is not None)
    if header["metadata"] is not None:
        require(header["metadata"]["source_file"] == request["contact"]["file"] and
            header["metadata"]["source_ref"] == request["contact"]["source_ref"] and
            header["metadata"]["format"] == request["contact"]["format"] and
            header["metadata"]["group_path"] == request["contact"]["group_path"])
    for row, spec in zip(value["tables"], specifications):
        require(row["draft"]["population_key"] == population["population_key"] and
            all(row["declaration"][k] == spec[k] for k in ("relative_path", "format")) and
            (row["draft"]["availability"] == "present") == (row["declaration"]["state"] == "present"))
    return value


def unavailable_extraction(request, *, code, populations=None):
    """Exact unknown population records; never a fabricated empty matrix."""
    from .chromatin_cooler_inputs import unavailable_chromatin_extraction
    request = validate_chromatin_record("ChromatinRequest", request)
    return unavailable_chromatin_extraction(spec=request["contact"], normalization=request["normalization"],
        populations=request["populations"] if populations is None else populations, code=code)


def validate_chromatin_bundle(value, *, plan):
    plan = validate_chromatin_run_plan(plan)
    value = validate_chromatin_record("NativeBundle", value)
    job = plan["requested_job"]["native_chromatin_interactions"]
    require(value["identity"] == plan["identity"] and value["request"] == job["request"] and value["software"] == job["software"])
    require([r["specification"] for r in value["outputs"]] == plan["outputs"][:-1])
    for row in value["outputs"]:
        require(all(row["declaration"][k] == row["specification"][k] for k in ("relative_path", "format")))
    if value["extraction"] is not None:
        require([p["selected_region"] for p in value["extraction"]["populations"]] == job["request"]["populations"])
    return value

