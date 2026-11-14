"""Closed executable contracts for selected local RNA primitives.

These validators check supplied records only. Native availability, input bytes
and effective settings are checked during the selected attempt, never inferred
from a binding or a null version. Scientific sheets remain in the pure lane.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import PurePosixPath
import re

from .execution_contracts import canonical, checked, digest, obj
from .rna_structure_contracts import (OPERATIONS, PAIR_TYPES, validate_rna_issue,
    validate_rna_model_spec_shape, validate_rna_parameters)

BUNDLE_FILENAME = "bundle.json"
RUN_PLAN_FILENAME = "rna-structure-plan.json"
ATTEMPT_DIRECTORY_NAME = "rna-structure-attempt"
OWNER_FILENAME = ".native-rna-structure-owner.json"
STARTED_FILENAME = ".native-rna-structure-started.json"
WORKER_MODULE = "gene_annotation_episode.native_rna_structure_worker"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
INPUT_NAMES = {"input": "input.json", "model_parameter_input": "model-parameter-input.par"}
ROLE_FORMATS = {"input": "rna_input_json_v1", "model_parameter_input": "viennarna_parameter_file",
    "native_result": "rna_native_record_json_v1", "model": "vienna_model_json_v1",
    "effective_parameters": "viennarna_parameter_file", "stdout": "text", "stderr": "text"}
_TEXT = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$"}
_SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_NULL = {"type": "null"}
_COUNT = {"type": "integer", "minimum": 0}
_ENV = {"type": "object", "propertyNames": {"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
    "additionalProperties": {"type": "string", "pattern": "^[^\\u0000]*$"}}
_SETTINGS = {"temperature_c": {"type": "number", "exclusiveMinimum": -273.15},
    "dangles": {"type": "integer", "enum": [0, 1, 2, 3]},
    **{name: {"type": "boolean"} for name in ("noLP", "noGU", "noGUclosure", "special_hp", "logML")},
    "min_loop_size": _COUNT, "max_bp_span": {"anyOf": [{"const": -1}, {"type": "integer", "minimum": 1}]},
    "circ": {"const": False}, "gquad": {"const": False}}
MODEL_SPEC_SCHEMA = obj({"schema": {"const": "vienna_rna_model_spec_v1"}, **_SETTINGS,
    "hard_constraints": _NULL, "soft_constraints": _NULL,
    "parameters": {"oneOf": [obj({"kind": {"const": "turner2004"}, "operand_role": _NULL}),
        obj({"kind": {"const": "supplied_parameter_file"}, "operand_role": {"const": "model_parameter_input"}})]}})
SOFTWARE_SCHEMA = obj({"python_executable": _TEXT, "python_sha256": _SHA,
    "python_version": {"anyOf": [_TEXT, _NULL]}, "worker_module": {"const": WORKER_MODULE},
    "worker_source_sha256": _SHA, "viennarna_distribution_version": {"anyOf": [_TEXT, _NULL]},
    "rna_module_sha256": {"anyOf": [_SHA, _NULL]}, "rna_extension_sha256": {"anyOf": [_SHA, _NULL]}})
PARAMETERS_SCHEMA = obj({"schema": {"const": "rna_calculation_parameters_v1"},
    "topology": obj({"long_stem_min_pairs": {"type": "integer", "minimum": 1},
        "include_exterior_in_loop_size_statistics": {"const": False}}),
    "pair_composition": obj({"accepted_ordered_pair_types": {"type": "array", "uniqueItems": True,
        "items": {"enum": list(PAIR_TYPES)}}, "denominator": {"const": "unambiguous_pairs"}}),
    "energy": obj({"normalization": {"enum": ["none", "per_nt"]}})})
_INPUT = obj({"role": {"enum": list(INPUT_NAMES)}, "path": _TEXT,
    "format": {"enum": [ROLE_FORMATS[r] for r in INPUT_NAMES]}, "sha256": _SHA,
    "size_bytes": _COUNT, "artifact_ref": {"anyOf": [_TEXT, _NULL]}})
_OUTPUT = obj({"role": {"enum": [r for r in ROLE_FORMATS if r not in INPUT_NAMES]},
    "format": {"enum": [ROLE_FORMATS[r] for r in ROLE_FORMATS if r not in INPUT_NAMES]}, "relative_path": _TEXT})
NATIVE_RNA_STRUCTURE_JOB_SCHEMA = obj({"version": {"const": "native_rna_structure_job_v1"},
    "program": {"const": "rna_structure_python"}, "operation": {"enum": list(OPERATIONS.values())},
    "mode": {"enum": list(OPERATIONS)}, "record_key": _TEXT, "software": SOFTWARE_SCHEMA,
    "model": {"anyOf": [MODEL_SPEC_SCHEMA, _NULL]},
    "operands": {"type": "array", "minItems": 1, "items": _INPUT},
    "outputs": {"type": "array", "minItems": 3, "items": _OUTPUT},
    "environment": _ENV, "grading_parameters": PARAMETERS_SCHEMA})
NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA = obj({
    "argv": {"type": "array", "minItems": 1, "items": _TEXT}, "environment": _ENV,
    "native_rna_structure": NATIVE_RNA_STRUCTURE_JOB_SCHEMA})


def _require(condition, code="rna_invalid_native_schema"):
    if not condition:
        raise ValueError(code)


def _path(value, *, absolute):
    _require(type(value) is str and bool(value) and not any(c in value for c in "\0\n\r\\"),
        "rna_output_path_conflict")
    path = PurePosixPath(value)
    _require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
        and value not in (".", "/"), "rna_output_path_conflict")
    return path


def _overlap(left, right):
    return left == right or left in right.parents or right in left.parents


def _environment(value):
    checked(value, _ENV, "rna_invalid_native_schema")
    reserved = {"HOME", "TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR",
        "PYTHONPYCACHEPREFIX", "PYTHONHOME", "PYTHONUSERBASE"}
    _require(not (reserved & value.keys()), "rna_output_path_conflict")
    _require(value.get("PYTHONDONTWRITEBYTECODE", "1") == "1", "rna_output_path_conflict")


def validate_rna_structure_software(value):
    result = checked(value, SOFTWARE_SCHEMA, "rna_invalid_native_schema")
    _path(result["python_executable"], absolute=True)
    return result


def validate_rna_structure_job(value: dict) -> dict:
    result = checked(value, NATIVE_RNA_STRUCTURE_JOB_SCHEMA, "rna_invalid_native_schema")
    _require(result["operation"] == OPERATIONS[result["mode"]], "rna_native_result_incompatible")
    validate_rna_structure_software(result["software"])
    validate_rna_parameters(result["grading_parameters"])
    _environment(result["environment"])
    model = result["model"]
    if model is not None:
        validate_rna_model_spec_shape(model)
    _require(result["mode"] != "mfe_prediction" or model is not None, "rna_invalid_parameter_schema")
    inputs = result["operands"]
    input_roles = [row["role"] for row in inputs]
    expected_inputs = {"input"}
    if model is not None and model["parameters"]["kind"] == "supplied_parameter_file":
        expected_inputs.add("model_parameter_input")
    _require(len(input_roles) == len(set(input_roles)) and set(input_roles) == expected_inputs)
    input_paths = []
    for row in inputs:
        _require(row["format"] == ROLE_FORMATS[row["role"]])
        input_paths.append(_path(row["path"], absolute=True))
        _require(type(row["size_bytes"]) is int)
    _require(len(input_paths) == len(set(input_paths)), "rna_output_path_conflict")
    roles = [row["role"] for row in result["outputs"]]
    expected_outputs = {"native_result", "stdout", "stderr"}
    if model is not None:
        expected_outputs.update(("model", "effective_parameters"))
    _require(len(roles) == len(set(roles)) and set(roles) == expected_outputs)
    reserved = [PurePosixPath(name) for name in (BUNDLE_FILENAME, RUN_PLAN_FILENAME, "native.json", "invoke.json",
        OWNER_FILENAME, STARTED_FILENAME, *INPUT_NAMES.values(),
        *(".staging-" + role for role in INPUT_NAMES), "tmp", "cache")]
    output_paths = []
    for row in result["outputs"]:
        _require(row["format"] == ROLE_FORMATS[row["role"]])
        path = _path(row["relative_path"], absolute=False)
        _require(not any(part.startswith((".local-job-", ".practical-")) for part in path.parts), "rna_output_path_conflict")
        _require(not any(_overlap(path, prior) for prior in reserved + output_paths), "rna_output_path_conflict")
        output_paths.append(path)
    return result


def compile_rna_structure_job(job: dict, *, input_paths: dict[str, str] | None = None,
        output_directory: str = ".") -> dict:
    job = validate_rna_structure_job(job)
    paths = {row["role"]: row["path"] for row in job["operands"]}
    if input_paths is not None:
        _require(type(input_paths) is dict and set(input_paths) == set(paths), "rna_input_identity_mismatch")
        for value in input_paths.values():
            _path(value, absolute=True)
        paths = dict(input_paths)
    if output_directory != ".":
        _path(output_directory, absolute=True)
    output_root = PurePosixPath(output_directory)
    outputs = {row["role"]: str(output_root / row["relative_path"]) for row in job["outputs"]}
    _require(not any(_overlap(PurePosixPath(p), PurePosixPath(q))
        for p in paths.values() for q in outputs.values()), "rna_output_path_conflict")
    argv = [job["software"]["python_executable"], "-B", "-m", WORKER_MODULE,
        "--operation", job["operation"], "--input-json", paths["input"],
        "--model-json", canonical(job["model"]), "--output-json", outputs["native_result"],
        "--record-key", job["record_key"], "--software-json", canonical(job["software"])]
    if "model_parameter_input" in paths:
        argv += ["--parameter-input", paths["model_parameter_input"]]
    if job["model"] is not None:
        argv += ["--model-output", outputs["model"], "--parameter-output", outputs["effective_parameters"]]
    return {"argv": argv, "environment": deepcopy(job["environment"]), "outputs": deepcopy(job["outputs"])}


def requested_job_from_rna_structure(job: dict) -> dict:
    job = validate_rna_structure_job(job)
    compiled = compile_rna_structure_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_rna_structure": job}


def validate_rna_structure_requested_job(value: dict) -> dict:
    result = checked(value, NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA, "rna_invalid_native_schema")
    expected = requested_job_from_rna_structure(result["native_rna_structure"])
    _require(canonical(result) == canonical(expected), "rna_input_identity_mismatch")
    return result


def validate_rna_structure_bindings(value: list[dict]) -> list[dict]:
    result = checked(value, {"type": "array", "items": obj({"operation": {"enum": list(OPERATIONS.values())},
        "mode": {"enum": list(OPERATIONS)}, "software": SOFTWARE_SCHEMA})}, "rna_invalid_native_schema")
    seen = set()
    for row in result:
        _require(row["operation"] == OPERATIONS[row["mode"]], "rna_native_result_incompatible")
        validate_rna_structure_software(row["software"])
        _require(row["mode"] not in seen, "rna_native_result_incompatible")
        seen.add(row["mode"])
    return result


def realized_environment(job, attempt_directory):
    """Explicit runtime additions keep temporary files and caches in this attempt."""
    _path(attempt_directory, absolute=True)
    root = PurePosixPath(attempt_directory)
    return {**job["environment"], "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
        "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache" / "pip")}


def validate_rna_structure_run_plan(value: dict) -> dict:
    identity_schema = obj({"run_id": _TEXT, "episode_id": _TEXT, "resource_id": _TEXT,
        "execution_id": _TEXT, "attempt_id": _SHA, "operation_key": _TEXT, "requested_job_sha256": _SHA})
    result = checked(value, obj({"version": {"const": "native_rna_structure_run_plan_v1"},
        "identity": identity_schema, "requested_job": NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA,
        "attempt_directory": _TEXT, "policy": obj({k: {"const": v} for k, v in POLICY.items()})}),
        "rna_original_attempt_mismatch")
    request = validate_rna_structure_requested_job(result["requested_job"])
    owner = result["identity"]
    execution = _path(owner["execution_id"], absolute=True)
    attempt = _path(result["attempt_directory"], absolute=True)
    _require(execution.name == "native.json" and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME,
        "rna_original_attempt_mismatch")
    _require(owner["attempt_id"] == digest(owner["operation_key"]) and owner["requested_job_sha256"] == digest(request),
        "rna_original_attempt_mismatch")
    _require(type(result["policy"]["memory_bytes"]) is int and type(result["policy"]["scratch_bytes"]) is int)
    for operand in request["native_rna_structure"]["operands"]:
        _require(not _overlap(_path(operand["path"], absolute=True), execution.parent), "rna_output_path_conflict")
    compile_rna_structure_job(request["native_rna_structure"],
        input_paths={row["role"]: str(attempt / INPUT_NAMES[row["role"]]) for row in request["native_rna_structure"]["operands"]},
        output_directory=str(attempt))
    return result


def validate_rna_structure_bundle(value: dict, *, plan: dict) -> dict:
    plan = validate_rna_structure_run_plan(plan)
    _require(type(value) is dict and set(value) == {"version", "identity", "requested_job", "program", "operation", "mode",
        "record_key", "software", "realized_argv", "environment", "files", "returncode", "native_status", "failures",
        "started_at", "finished_at", "sealed"})
    result = deepcopy(value)
    job = plan["requested_job"]["native_rna_structure"]
    _require(result["version"] == "native_rna_structure_bundle_v1" and result["sealed"] is True, "rna_unsealed_native_attempt")
    _require(result["identity"] == plan["identity"] and result["requested_job"] == plan["requested_job"], "rna_original_attempt_mismatch")
    _require(all(result[k] == job[k] for k in ("program", "operation", "mode", "record_key", "software")), "rna_original_attempt_mismatch")
    attempt = PurePosixPath(plan["attempt_directory"])
    compiled = compile_rna_structure_job(job, input_paths={row["role"]: str(attempt / INPUT_NAMES[row["role"]])
        for row in job["operands"]}, output_directory=str(attempt))
    _require(result["realized_argv"] == compiled["argv"] and
        result["environment"] == realized_environment(job, str(attempt)), "rna_original_attempt_mismatch")
    _require(result["returncode"] is None or type(result["returncode"]) is int)
    _require(result["native_status"] in ("complete", "partial", "failed"))
    _require(type(result["failures"]) is list)
    for failure in result["failures"]:
        validate_rna_issue(failure)
        _require(failure["record_key"] in (None, job["record_key"]), "rna_input_identity_mismatch")
    expected = [{"kind": "input", "role": row["role"], "format": row["format"],
        "relative_path": INPUT_NAMES[row["role"]]} for row in job["operands"]]
    expected += [{"kind": "output", **row} for row in job["outputs"]]
    _require(type(result["files"]) is list and len(result["files"]) == len(expected))
    for index, (row, selected) in enumerate(zip(result["files"], expected)):
        _require(type(row) is dict and set(row) == {*selected, "state", "sha256", "size_bytes"})
        _require(all(row[k] == v for k, v in selected.items()), "rna_original_attempt_mismatch")
        if row["state"] == "present":
            _require(type(row["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", row["sha256"]) is not None)
            _require(type(row["size_bytes"]) is int and row["size_bytes"] >= 0)
            if row["kind"] == "input":
                original = job["operands"][index]
                _require(row["sha256"] == original["sha256"] and row["size_bytes"] == original["size_bytes"], "rna_input_identity_mismatch")
        else:
            _require(row["state"] == "absent" and row["sha256"] is None and row["size_bytes"] is None)
            _require(any(f["artifact_role"] == row["role"] for f in result["failures"]))
    try:
        start, end = (datetime.fromisoformat(result[k]) for k in ("started_at", "finished_at"))
        _require(start.tzinfo is not None and end.tzinfo is not None and start <= end)
    except (ValueError, TypeError) as error:
        raise ValueError("rna_invalid_native_schema") from error
    if result["native_status"] == "complete":
        _require(result["returncode"] == 0 and all(r["state"] == "present" for r in result["files"]) and
            all(f["code"] == "no_sequence_supplied" for f in result["failures"]))
    else:
        _require(bool(result["failures"]))
    canonical(result)  # Reject nonfinite/unsupported JSON even in rejected-data paths.
    return result
