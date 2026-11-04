"""Closed operands for one selected two-condition MACS2 native attempt.

These supplied-record validators make no resource choice or filesystem access.
Native measurements and scientific calculations retain their separate modules.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator

from .atac_differential_contracts import (
    validate_atac_condition, validate_atac_depth_selection,
    validate_atac_reference, validate_atac_sample,
)

POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
RUN_PLAN_FILENAME = "atac-plan.json"
ATTEMPT_DIRECTORY_NAME = "atac-differential-attempt"
OWNER_FILENAME = ".native-atac-owner.json"
STARTED_FILENAME = ".native-atac-started.json"
DRIVER_MODULE = "gene_annotation_episode.native_atac_differential_driver"
OPERATION = "analyze_atac_seq_differential_accessibility"
MODE = "macs2_2_2_9_1_bam_single_end_no_control"
STEP_KEYS = ("callpeak1", "callpeak2", "bdgdiff")
REQUIRED_MODULES = {DRIVER_MODULE, "gene_annotation_episode.native_atac_differential_contracts",
    "gene_annotation_episode.native_atac_differential_reference", "gene_annotation_episode.atac_differential_inputs",
    "gene_annotation_episode.atac_differential_sheet", "gene_annotation_episode.atac_differential_contracts"}
REQUIRED_DEPENDENCIES = {"jsonschema", "attrs", "referencing", "rpds-py", "jsonschema-specifications"}


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


def _obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _arr(items, **kwargs):
    return {"type": "array", "items": items, **kwargs}


def _enum(*values):
    return {"enum": list(values)}


def _null(schema):
    return {"anyOf": [schema, {"type": "null"}]}


_TEXT = {"type": "string", "minLength": 1, "maxLength": 4096, "pattern": r"^[^\x00-\x1f\x7f]+$"}
_ID = {"type": "string", "minLength": 1, "maxLength": 512, "pattern": r"^[A-Za-z0-9_.:/@+\-]+$"}
_SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_INT = {"type": "integer", "minimum": 0}
_NUM = {"type": "number"}
_BOOL = {"type": "boolean"}
_ENV = {"type": "object", "propertyNames": {"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
    "additionalProperties": {"type": "string", "pattern": "^[^\u0000]*$"}}
_FILE = _obj(artifact_ref={"type": "string", "pattern": "^artifact_[0-9a-f]{64}$"},
    sha256=_SHA, size_bytes=_INT, format=_ID)
_DECL = _obj(relative_path=_TEXT, format=_ID, state=_enum("present", "absent"), sha256=_null(_SHA), size_bytes=_null(_INT))
_PIN = _obj(path=_TEXT, sha256=_SHA, size_bytes=_INT)
_LOCATOR = _obj(line_number={"type": "integer", "minimum": 1}, byte_start=_INT, byte_end=_INT)
_ISSUE = _obj(code=_enum("metadata_missing", "metadata_conflict", "condition_binding_conflict", "unsupported_mode",
    "zero_depth", "duplicate_record", "reference_conflict"), artifact_ref=_null(_ID), binding_key=_ID,
    row_ordinals=_arr(_INT), locations=_arr(_LOCATOR), field=_null(_TEXT),
    requirement=_enum("none", "matching_count_population", "condition_mapping", "original_native_metadata",
        "compatible_native_mode", "explicit_reference_mapping"))
_DEPTH_ROW = _obj(condition_id=_ID, sample_ids=_arr(_ID), callpeak_run_key=_null(_ID),
    count=_null(_INT), count_lexeme=_null(_TEXT), count_unit=_enum("postfilter_single_end_tags"),
    count_population=_enum("macs2_loaded_treatment_tags_after_duplicate_filtering"),
    source_artifact_ref=_null(_ID), source_locations=_arr(_LOCATOR), source_field=_enum("treatment_postfilter_tags"),
    million_denominator={"const": 1000000}, state=_enum("observed", "missing", "conflicting", "incompatible_mode", "zero"))
_DEPTH = _obj(kind=_enum("native_postfilter_counts"), conditions=_arr(_DEPTH_ROW, minItems=2, maxItems=2),
    compatible_population=_BOOL, issues=_arr(_ISSUE))
_FAILURE = _obj(code=_enum("input_unavailable", "artifact_digest_mismatch", "reference_conflict", "unsupported_native_mode",
    "native_nonzero_exit", "resource_limit", "native_dependency_unavailable", "native_output_unavailable",
    "native_dependency_output_unavailable", "native_depth_unavailable", "original_attempt_mismatch",
    "worker_output_unavailable", "saved_attachment_unavailable", "calculation_input_unavailable",
    "calculation_stream_failed", "requested_field_unavailable", "return_authority_mismatch"),
    stage=_enum("input", "reference", "execution", "capture", "parse", "calculation", "return"),
    step_key=_null(_ID), file_key=_null(_ID), binding_key=_null(_ID), artifact_ref=_null(_ID),
    locator=_null(_LOCATOR), field_path=_null(_TEXT),
    requirement=_enum("none", "matching_file_identity", "original_native_outcome", "complete_native_output",
        "actual_bam_header", "matching_reference_dictionary", "condition_mapping", "matching_count_population",
        "compatible_native_mode", "complete_saved_bundle", "ordered_track_rows", "requested_selected_field",
        "original_return_authority", "native_runtime", "resource_allocation"), partial_artifact_refs=_arr(_ID))
_REFERENCE = _obj(reference_id=_ID, assembly_accession_version=_null(_ID), source_refs=_arr(_ID),
    contigs=_arr(_obj(chromosome=_ID, length_bp=_null(_INT), sequence_accession_version=_null(_ID),
        sequence_sha256=_null(_SHA), source_refs=_arr(_ID))),
    aliases=_arr(_obj(source_chromosome=_ID, target_chromosome=_ID, reference_id=_ID, source_refs=_arr(_ID))))
_SAMPLE = _obj(sample_id=_ID, input_artifact_refs=_arr(_ID), reference_id=_ID, biospecimen_id=_null(_ID),
    replicate_id=_null(_ID), origin=_enum("supplied_measurement", "synthetic_engineering_fixture", "unknown"))
_CONDITION = _obj(condition_id=_ID, label=_null(_TEXT), sample_ids=_arr(_ID, minItems=1, maxItems=1))
_INPUT = _obj(input_key=_ID, condition_id=_ID, sample_id=_ID, reference_id=_ID, file={**_FILE,
    "properties": {**_FILE["properties"], "format": {"const": "bam"}}})
_DRIVER = _obj(python_executable=_TEXT, python_sha256=_SHA, python_version=_ID, module_root=_TEXT,
    implementation_files=_arr(_obj(module=_ID, sha256=_SHA), minItems=1),
    dependencies=_arr(_obj(distribution=_ID, version=_TEXT, package_root=_TEXT, files=_arr(_PIN, minItems=1)), minItems=1))
_MACS = _obj(python_executable=_TEXT, python_sha256=_SHA, python_version=_ID, macs2_script=_TEXT,
    macs2_sha256=_SHA, macs2_version={"const": "2.2.9.1"}, import_roots=_arr(_TEXT, minItems=1), files=_arr(_PIN, minItems=1))
_SOFTWARE = _obj(driver_runtime=_DRIVER, macs2_runtime=_MACS)
_REQUEST = _obj(version={"const": "atac_differential_request_v1"}, operation={"const": OPERATION}, mode={"const": MODE},
    comparison_key=_ID, reference=_REFERENCE, samples=_arr(_SAMPLE, minItems=1, maxItems=2),
    conditions=_arr(_CONDITION, minItems=2, maxItems=2), inputs=_arr(_INPUT, minItems=2, maxItems=2),
    callpeak=_obj(genome_size_argument=_TEXT, qvalue_cutoff={"type": "number", "exclusiveMinimum": 0, "maximum": 1},
        keep_duplicates={"const": 1, "type": "integer"}, nomodel={"const": True}, shift_bp={"const": -100},
        extension_size_bp={"const": 200}, store_bedgraph={"const": True}, spmr={"const": False},
        broad={"const": False}, downsample={"const": False}),
    bdgdiff=_obj(cutoff_log10_lr={"type": "number", "minimum": 0}, minimum_length_bp={"type": "integer", "minimum": 1},
        maximum_gap_bp=_INT), output_prefix=_TEXT)
_JOB = _obj(request=_REQUEST, software=_SOFTWARE,
    input_bindings=_arr(_obj(input_key=_ID, file=_FILE, path=_TEXT), minItems=2, maxItems=2))
_REQUESTED = _obj(argv=_arr(_TEXT, minItems=6, maxItems=6), environment=_ENV, native_atac_differential=_JOB)
_IDENTITY = _obj(run_id=_ID, episode_id=_ID, resource_id=_ID, execution_id=_TEXT, attempt_id=_SHA,
    operation_key=_TEXT, requested_job_sha256=_SHA, assignment_sha256=_SHA)
_SPEC = _obj(file_key=_ID, step_key=_null(_enum(*STEP_KEYS)), role=_ID, relative_path=_TEXT, format=_ID)
_OUTPUT = _obj(specification=_SPEC, declaration=_DECL)
_PLAN = _obj(version={"const": "atac_differential_run_plan_v1"}, identity=_IDENTITY, requested_job=_REQUESTED,
    attempt_directory=_TEXT, policy={"const": POLICY}, outputs=_arr(_SPEC))
_HEADER = _obj(version={"const": "atac_bam_header_extraction_v1"}, input_key=_ID, callpeak_run_key=_ID,
    input_ordinal=_INT, input_file=_FILE, header=_DECL, producer_outcome=_enum("succeeded", "failed", "not_run", "unknown"),
    supplied_extent=_enum("complete", "partial", "unknown"), failures=_arr(_FAILURE))
_SEAL = _obj(version={"const": "atac_native_command_seal_v1"}, identity=_IDENTITY, step_key=_enum(*STEP_KEYS),
    producer_ref=_ID, argv=_arr(_TEXT), environment=_ENV, inputs=_arr(_obj(file_key=_ID, role=_ID, file=_FILE)),
    started_at=_null(_TEXT), finished_at=_null(_TEXT), returncode=_null({"type": "integer"}),
    outcome=_enum("succeeded", "failed", "not_run"), outputs=_arr(_OUTPUT), failures=_arr(_FAILURE))
_BUNDLE = _obj(version={"const": "atac_differential_native_bundle_v1"}, identity=_IDENTITY, request=_REQUEST,
    software=_SOFTWARE, input_inspections=_arr(_HEADER, minItems=2, maxItems=2),
    steps=_arr(_SEAL, minItems=3, maxItems=3), depth_selection=_null(_DEPTH), outputs=_arr(_OUTPUT), failures=_arr(_FAILURE))
_RETAINED = _obj(file=_FILE, path=_TEXT)
_CAPTURE = _obj(version={"const": "atac_native_capture_v1"}, bundle=_null(_RETAINED),
    files=_arr(_obj(specification=_SPEC, declared=_null(_DECL), retained=_null(_RETAINED),
        outcome=_enum("verified", "declared_absent", "unavailable", "digest_mismatch", "unsealed"),
        producer_outcome=_enum("succeeded", "failed", "not_run", "unknown"), supplied_extent=_enum("complete", "partial", "unknown"))),
    source_action_receipt_ref=_ID, writer_closure_receipt_ref=_ID,
    driver_state=_enum("succeeded", "failed", "not_run", "unknown"), failures=_arr(_FAILURE))
_SCHEMAS = {"Binding": _obj(operation={"const": OPERATION}, mode={"const": MODE}, software=_SOFTWARE),
    "SoftwareBinding": _SOFTWARE, "Request": _REQUEST, "NativeJob": _JOB, "RequestedJob": _REQUESTED,
    "RunPlan": _PLAN, "CommandSeal": _SEAL, "NativeBundle": _BUNDLE, "NativeCapture": _CAPTURE,
    "HeaderExtraction": _HEADER, "Failure": _FAILURE}


def atac_execution_schema(kind, *, bindings=None):
    require(kind in _SCHEMAS, "unsupported_atac_execution_schema")
    schema = deepcopy(_SCHEMAS[kind])
    if bindings is not None:
        require(kind == "RequestedJob", "unsupported_atac_execution_schema")
        rows = validate_atac_bindings(bindings)
        choices = [{"properties": {"native_atac_differential": {"properties": {
            "software": {"const": row["software"]}, "request": {"properties": {
                "operation": {"const": row["operation"]}, "mode": {"const": row["mode"]}}}}}}} for row in rows]
        schema = {"allOf": [schema, {"anyOf": choices} if choices else {"not": {}}]}
    return schema


def validate_atac_record(kind, value):
    try:
        canonical(value)
        Draft202012Validator(_SCHEMAS[kind]).validate(value)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid_atac_" + kind.lower()) from error
    except Exception as error:
        from jsonschema.exceptions import ValidationError
        if not isinstance(error, ValidationError):
            raise
        raise ValueError("invalid_atac_" + kind.lower()) from error
    return deepcopy(value)


def failure(code, stage, *, step_key=None, file_key=None, binding_key=None, artifact_ref=None,
        locator=None, field_path=None, requirement="none", partial_artifact_refs=()):
    return validate_atac_record("Failure", dict(code=code, stage=stage, step_key=step_key, file_key=file_key,
        binding_key=binding_key, artifact_ref=artifact_ref, locator=locator, field_path=field_path,
        requirement=requirement, partial_artifact_refs=list(partial_artifact_refs)))


def unique_failures(*groups):
    return list({digest(row): row for group in groups for row in group}.values())


def validate_atac_software(value):
    value = validate_atac_record("SoftwareBinding", value)
    driver, macs = value["driver_runtime"], value["macs2_runtime"]
    for row in (driver, macs):
        path_value(row["python_executable"], absolute=True)
    path_value(driver["module_root"], absolute=True)
    path_value(macs["macs2_script"], absolute=True)
    names = [r["module"] for r in driver["implementation_files"]]
    require(len(names) == len(set(names)) and REQUIRED_MODULES <= set(names), "native_dependency_unavailable")
    require(all(re.fullmatch(r"gene_annotation_episode(?:\.[A-Za-z_]\w*)+", n, re.ASCII) for n in names), "native_dependency_unavailable")
    dependencies = driver["dependencies"]
    names = [r["distribution"].lower().replace("_", "-") for r in dependencies]
    require(len(names) == len(set(names)) and REQUIRED_DEPENDENCIES <= set(names), "native_dependency_unavailable")
    for row in dependencies:
        path_value(row["package_root"], absolute=True)
    for pins in [macs["files"], *(r["files"] for r in dependencies)]:
        paths = [str(path_value(r["path"], absolute=True)) for r in pins]
        require(len(paths) == len(set(paths)), "native_dependency_unavailable")
    roots = [str(path_value(p, absolute=True)) for p in macs["import_roots"]]
    require(len(roots) == len(set(roots)), "native_dependency_unavailable")
    # Require the actual native algorithm and NumPy closure, not a script-only pin.
    paths = {p["path"] for p in macs["files"]}
    require(macs["macs2_script"] in paths and any("/MACS2/callpeak_cmd.py" in p for p in paths)
        and any("/MACS2/bdgdiff_cmd.py" in p for p in paths)
        and any("/MACS2/IO/Parser." in p and p.endswith(".so") for p in paths)
        and any("/numpy/__init__.py" in p for p in paths), "native_dependency_unavailable")
    return value


def validate_atac_bindings(values):
    require(type(values) is list)
    result = [validate_atac_record("Binding", row) for row in values]
    for row in result:
        validate_atac_software(row["software"])
    require(len({digest(row) for row in result}) == len(result))
    return result


def validate_atac_request(value):
    value = validate_atac_record("Request", value)
    validate_atac_reference(value["reference"])
    for row in value["samples"]:
        validate_atac_sample(row)
    for row in value["conditions"]:
        validate_atac_condition(row)
    for collection, key in ((value["samples"], "sample_id"), (value["conditions"], "condition_id"), (value["inputs"], "input_key")):
        require(len({r[key] for r in collection}) == len(collection), "condition_mapping")
    samples = {r["sample_id"]: r for r in value["samples"]}
    require(set(samples) == {r["sample_id"] for r in value["inputs"]}, "condition_mapping")
    for selected, condition in zip(value["inputs"], value["conditions"]):
        require(selected["condition_id"] == condition["condition_id"] and condition["sample_ids"] == [selected["sample_id"]]
            and selected["reference_id"] == value["reference"]["reference_id"], "condition_mapping")
        sample = samples[selected["sample_id"]]
        require(sample["reference_id"] == selected["reference_id"] and selected["file"]["artifact_ref"] in sample["input_artifact_refs"], "condition_mapping")
        require(selected["file"]["artifact_ref"] == "artifact_" + selected["file"]["sha256"], "artifact_digest_mismatch")
    argument = value["callpeak"]["genome_size_argument"]
    if argument not in ("hs", "mm", "ce", "dm"):
        try:
            numeric = Decimal(argument)
        except InvalidOperation as error:
            raise ValueError("invalid_atac_genome_size") from error
        require(re.fullmatch(r"[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", argument)
            and numeric.is_finite() and numeric > 0, "invalid_atac_genome_size")
    p = value["bdgdiff"]
    require(p["maximum_gap_bp"] < p["minimum_length_bp"], "invalid_atac_region_parameters")
    prefix = path_value(value["output_prefix"], absolute=False)
    require(prefix.parts[0] not in (OWNER_FILENAME, STARTED_FILENAME), "invalid_output_path")
    return value


def validate_atac_native_job(value):
    value = validate_atac_record("NativeJob", value)
    request = validate_atac_request(value["request"])
    validate_atac_software(value["software"])
    require([r["input_key"] for r in value["input_bindings"]] == [r["input_key"] for r in request["inputs"]])
    paths = {}
    for binding, selected in zip(value["input_bindings"], request["inputs"]):
        require(binding["file"] == selected["file"])
        path = path_value(binding["path"], absolute=True)
        if path in paths:
            require(paths[path] == binding["file"])
        paths[path] = binding["file"]
    return value


def _dependency_roots(driver):
    roots = []
    for row in driver["dependencies"]:
        path = PurePosixPath(row["package_root"])
        is_package = any(p["path"] == str(path / "__init__.py") for p in row["files"])
        roots.append(str(path.parent if is_package else path))
    return list(dict.fromkeys(roots))


def _environment(value):
    require(type(value) is dict and all(type(k) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k)
        and type(v) is str and "\0" not in v for k, v in value.items()), "invalid_native_environment")
    require(all(value.get(k) == "1" for k in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE",
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")), "invalid_native_environment")
    for name in ("PYTHONHOME", "TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR"):
        path_value(value.get(name), absolute=True)


def requested_job_from_atac(job, *, environment):
    job = validate_atac_native_job(job)
    _environment(environment)
    driver = job["software"]["driver_runtime"]
    require(environment.get("PYTHONPATH") == os.pathsep.join([driver["module_root"], *_dependency_roots(driver)]), "native_dependency_unavailable")
    return {"argv": [driver["python_executable"], "-B", "-S", "-m", DRIVER_MODULE, RUN_PLAN_FILENAME],
        "environment": deepcopy(environment), "native_atac_differential": job}


def validate_atac_requested_job(value):
    value = validate_atac_record("RequestedJob", value)
    require(value == requested_job_from_atac(value["native_atac_differential"], environment=value["environment"]))
    return value


def atac_output_files(request):
    request = validate_atac_request(request)
    rows = []
    def add(key, step, role, suffix, format):
        rows.append(dict(file_key=key, step_key=step, role=role,
            relative_path=request["output_prefix"] + "/" + suffix, format=format))
    for i in (1, 2):
        add(f"input{i}", None, f"input{i}", f"inputs/c{i}.bam", "bam")
    add("request_metadata", None, "request_metadata", "metadata/request.json", "atac_differential_request_v1")
    for i in (1, 2):
        add(f"header{i}", None, f"header{i}", f"metadata/c{i}.header.sam", "sam_header_text")
    for i in (1, 2):
        step = f"callpeak{i}"
        for role, suffix, fmt in (("peaks_xls", f"c{i}_peaks.xls", "macs2_peaks_xls_narrow"),
            ("narrowpeak", f"c{i}_peaks.narrowPeak", "macs2_narrowpeak10"),
            ("summits", f"c{i}_summits.bed", "macs2_summits_bed5"),
            ("signal", f"c{i}_treat_pileup.bdg", "bedgraph4"),
            ("background", f"c{i}_control_lambda.bdg", "bedgraph4"),
            ("stdout", "stdout.log", "native_stdout"), ("stderr", "stderr.log", "native_stderr"),
            ("seal", "seal.json", "atac_native_command_seal_v1")):
            add(step + "." + role, step, role, f"callpeak/c{i}/" + suffix, fmt)
    add("depth_selection", None, "depth_selection", "metadata/depth-selection.json", "atac_native_depth_selection_v1")
    for role in ("condition1", "condition2", "common"):
        add("bdgdiff." + role, "bdgdiff", role, "bdgdiff/" + role + ".bed", "macs2_bdgdiff_bed5")
    for role, suffix, fmt in (("stdout", "stdout.log", "native_stdout"), ("stderr", "stderr.log", "native_stderr"),
        ("seal", "seal.json", "atac_native_command_seal_v1")):
        add("bdgdiff." + role, "bdgdiff", role, "bdgdiff/" + suffix, fmt)
    add("stdout", None, "stdout", "stdout.log", "native_stdout")
    add("stderr", None, "stderr", "stderr.log", "native_stderr")
    add("bundle", None, "bundle", "bundle.json", "atac_differential_native_bundle_v1")
    return rows


def validate_atac_run_plan(value):
    value = validate_atac_record("RunPlan", value)
    requested = validate_atac_requested_job(value["requested_job"])
    identity = value["identity"]
    execution = path_value(identity["execution_id"], absolute=True)
    attempt = path_value(value["attempt_directory"], absolute=True)
    require(execution.name == "native.json" and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME)
    require(identity["attempt_id"] == digest(identity["operation_key"]) and identity["requested_job_sha256"] == digest(requested))
    require(execution.parent.name == identity["attempt_id"] and execution.parent.parent.name ==
        digest({"run": identity["run_id"], "episode": identity["episode_id"]}) and execution.parent.parent.parent.name == ".episode-operations")
    require(value["policy"] == POLICY and type(value["policy"]["memory_bytes"]) is int and type(value["policy"]["scratch_bytes"]) is int)
    require(value["outputs"] == atac_output_files(requested["native_atac_differential"]["request"]))
    for binding in requested["native_atac_differential"]["input_bindings"]:
        path = path_value(binding["path"], absolute=True)
        require(path != execution.parent and execution.parent not in path.parents and path not in execution.parent.parents)
    return value


def atac_driver_argv(plan):
    plan = validate_atac_run_plan(plan)
    return [*plan["requested_job"]["argv"][:-1], str(PurePosixPath(plan["identity"]["execution_id"]).parent / RUN_PLAN_FILENAME)]


def atac_environment(job, *, attempt_directory, environment):
    job = validate_atac_native_job(job)
    _environment(environment)
    root = path_value(attempt_directory, absolute=True)
    driver = job["software"]["driver_runtime"]
    return {**environment, "PYTHONPATH": os.pathsep.join([driver["module_root"], *_dependency_roots(driver)]),
        "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"), "TMPDIR": str(root / "tmp"),
        "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip")}


def atac_native_environment(plan, step_key):
    require(step_key in STEP_KEYS)
    root = PurePosixPath(plan["attempt_directory"])
    native = plan["requested_job"]["native_atac_differential"]["software"]["macs2_runtime"]
    temporary = root / "tmp" / step_key
    return {"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8", "PYTHONPATH": os.pathsep.join(native["import_roots"]),
        "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "TMP": str(temporary),
        "TEMP": str(temporary), "TMPDIR": str(temporary), "XDG_CACHE_HOME": str(root / "cache"),
        "PIP_CACHE_DIR": str(root / "cache/pip")}


def atac_command_argv(plan, step_key, *, depth_selection=None):
    job = plan["requested_job"]["native_atac_differential"]
    request, native = job["request"], job["software"]["macs2_runtime"]
    root = PurePosixPath(plan["attempt_directory"])
    output = {r["file_key"]: str(root / r["relative_path"]) for r in plan["outputs"]}
    argv = [native["python_executable"], "-B", "-S", native["macs2_script"]]
    if step_key in ("callpeak1", "callpeak2"):
        i, p = int(step_key[-1]), request["callpeak"]
        return [*argv, "callpeak", "-t", output[f"input{i}"], "-f", "BAM", "-g", p["genome_size_argument"],
            "--keep-dup", "1", "--nomodel", "--shift", "-100", "--extsize", "200", "-q", str(p["qvalue_cutoff"]),
            "-B", "-n", f"c{i}", "--outdir", str(PurePosixPath(output[step_key + ".peaks_xls"]).parent),
            "--tempdir", str(root / "tmp" / f"c{i}")]
    require(step_key == "bdgdiff")
    if depth_selection is None:
        return []
    validate_atac_depth_selection(depth_selection)
    if not depth_selection["compatible_population"] or any(r["state"] != "observed" for r in depth_selection["conditions"]):
        return []
    depths = [format(Decimal(r["count"]) / Decimal(1000000), "f") for r in depth_selection["conditions"]]
    return _bdgdiff_argv(plan, depths)


def _bdgdiff_argv(plan, depths):
    """Compile fixed operands with two already validated decimal depth tokens."""
    job = plan["requested_job"]["native_atac_differential"]
    native = job["software"]["macs2_runtime"]
    root = PurePosixPath(plan["attempt_directory"])
    output = {r["file_key"]: str(root / r["relative_path"]) for r in plan["outputs"]}
    argv = [native["python_executable"], "-B", "-S", native["macs2_script"]]
    p = job["request"]["bdgdiff"]
    return [*argv, "bdgdiff", "--t1", output["callpeak1.signal"], "--c1", output["callpeak1.background"],
        "--t2", output["callpeak2.signal"], "--c2", output["callpeak2.background"], "--d1", depths[0], "--d2", depths[1],
        "-C", str(p["cutoff_log10_lr"]), "-l", str(p["minimum_length_bp"]), "-g", str(p["maximum_gap_bp"]),
        "--outdir", str(PurePosixPath(output["bdgdiff.common"]).parent), "-o", "condition1.bed", "condition2.bed", "common.bed"]


def producer_ref(plan, step_key):
    return "atac_native_run:" + digest([plan["identity"], step_key])


def _check_declaration(row):
    spec, declaration = row["specification"], row["declaration"]
    require(all(declaration[k] == spec[k] for k in ("relative_path", "format")))
    require((declaration["sha256"] is None and declaration["size_bytes"] is None) if declaration["state"] == "absent"
        else declaration["sha256"] is not None and type(declaration["size_bytes"]) is int)


def _command_times(value):
    if value["outcome"] == "not_run":
        require(value["started_at"] is None and value["finished_at"] is None and value["returncode"] is None)
        return
    try:
        first, last = (datetime.fromisoformat(value[name]) for name in ("started_at", "finished_at"))
    except (TypeError, ValueError) as error:
        raise ValueError("original_attempt_mismatch") from error
    require(first.tzinfo is not None and last.tzinfo is not None and last >= first)
    require(value["returncode"] == 0 if value["outcome"] == "succeeded" else value["returncode"] != 0)


def _bdgdiff_seal_operands(value, plan):
    inputs, argv = value["inputs"], value["argv"]
    keys = ["callpeak1.signal", "callpeak1.background", "callpeak2.signal", "callpeak2.background"]
    require([r["file_key"] for r in inputs] in ([], keys))
    for row, role in zip(inputs, ("signal", "background", "signal", "background")):
        require(row["role"] == role and row["file"]["format"] == "bedgraph4"
            and row["file"]["artifact_ref"] == "artifact_" + row["file"]["sha256"])
    if not argv:
        require(value["outcome"] == "not_run")
        return
    try:
        depths = [argv[argv.index(flag) + 1] for flag in ("--d1", "--d2")]
        numbers = [Decimal(token) for token in depths]
    except (ValueError, IndexError, InvalidOperation) as error:
        raise ValueError("original_attempt_mismatch") from error
    require(all(number.is_finite() and number > 0
        and number * 1000000 == (number * 1000000).to_integral_value()
        and token == format(number, "f") for token, number in zip(depths, numbers)))
    require(argv == _bdgdiff_argv(plan, depths))
    require(value["outcome"] == "not_run" or len(inputs) == 4)


def validate_atac_command_seal(value, *, plan, step_key):
    plan = validate_atac_run_plan(plan)
    value = validate_atac_record("CommandSeal", value)
    require(value["identity"] == plan["identity"] and value["step_key"] == step_key
        and value["producer_ref"] == producer_ref(plan, step_key))
    specs = [r for r in plan["outputs"] if r["step_key"] == step_key and r["role"] != "seal"]
    require([r["specification"] for r in value["outputs"]] == specs)
    for row in value["outputs"]:
        _check_declaration(row)
    require(value["environment"] == atac_native_environment(plan, step_key))
    if step_key != "bdgdiff":
        require(value["argv"] == atac_command_argv(plan, step_key))
        i = int(step_key[-1])
        selected = plan["requested_job"]["native_atac_differential"]["request"]["inputs"][i - 1]
        require(value["inputs"] == [{"file_key": f"input{i}", "role": "treatment", "file": selected["file"]}])
    else:
        _bdgdiff_seal_operands(value, plan)
    _command_times(value)
    return value


def validate_atac_native_bundle(value, *, plan):
    plan = validate_atac_run_plan(plan)
    value = validate_atac_record("NativeBundle", value)
    job = plan["requested_job"]["native_atac_differential"]
    require(value["identity"] == plan["identity"] and value["request"] == job["request"] and value["software"] == job["software"])
    require([r["specification"] for r in value["outputs"]] == plan["outputs"][:-1])
    for row in value["outputs"]:
        _check_declaration(row)
    declared = {r["specification"]["file_key"]: r["declaration"] for r in value["outputs"]}
    for i, header in enumerate(value["input_inspections"], 1):
        selected = job["request"]["inputs"][i - 1]
        require(header["input_key"] == selected["input_key"] and header["input_file"] == selected["file"]
            and header["callpeak_run_key"] == f"callpeak{i}" and header["input_ordinal"] == 0
            and header["header"] == declared[f"header{i}"])
        if declared[f"input{i}"]["state"] == "present":
            require(all(declared[f"input{i}"][k] == selected["file"][k] for k in ("sha256", "size_bytes", "format")))
    for step_key, seal in zip(STEP_KEYS, value["steps"]):
        validate_atac_command_seal(seal, plan=plan, step_key=step_key)
        for row in seal["outputs"]:
            require(row["declaration"] == declared[row["specification"]["file_key"]])
        expected = canonical(seal)
        require(declared[step_key + ".seal"]["state"] == "present" and declared[step_key + ".seal"]["sha256"] == hashlib.sha256(expected).hexdigest()
            and declared[step_key + ".seal"]["size_bytes"] == len(expected))
    depth = value["depth_selection"]
    if depth is not None:
        validate_atac_depth_selection(depth)
        require([r["condition_id"] for r in depth["conditions"]] == [r["condition_id"] for r in job["request"]["conditions"]])
        for i, row in enumerate(depth["conditions"], 1):
            require(row["callpeak_run_key"] == f"callpeak{i}" and row["sample_ids"] == [job["request"]["inputs"][i - 1]["sample_id"]])
            if row["source_artifact_ref"] is not None:
                require(declared[f"callpeak{i}.peaks_xls"]["state"] == "present"
                    and row["source_artifact_ref"] == "artifact_" + declared[f"callpeak{i}.peaks_xls"]["sha256"])
    require(value["steps"][2]["argv"] == atac_command_argv(plan, "bdgdiff", depth_selection=depth))
    for row in value["steps"][2]["inputs"]:
        declaration = declared[row["file_key"]]
        require(declaration["state"] == "present" and all(row["file"][k] == declaration[k]
            for k in ("sha256", "size_bytes", "format")))
    if value["steps"][2]["outcome"] != "not_run":
        require(all(step["outcome"] == "succeeded" for step in value["steps"][:2]))
    for name, record in (("request_metadata", job["request"]), ("depth_selection", depth)):
        raw = canonical(record)
        require(declared[name]["state"] == "present" and declared[name]["sha256"] == hashlib.sha256(raw).hexdigest()
            and declared[name]["size_bytes"] == len(raw))
    return value
