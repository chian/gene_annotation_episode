"""Original supplied genomic-overlap job validation; no launch or run-plan admission."""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
from pathlib import PurePosixPath
import math
import re
from jsonschema import Draft202012Validator, FormatChecker, validators
from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_contracts import Request, validate_genomic_overlap_record
from gene_annotation_episode.episodic_workflow.root.library.native_genomic_overlap_job_schema import _EXECUTION_DEFINITIONS, _require, _digest, _definitions

RUN_PLAN_FILENAME = "genomic-overlap-plan.json"

BATCH_FILENAME = "bundle.json"
OWNER_FILENAME = ".native-genomic-overlap-owner.json"
STARTED_FILENAME = ".native-genomic-overlap-started.json"

DRIVER_MODULE = "gene_annotation_episode.episodic_workflow.root.library.native_genomic_overlap_driver"
_REQUIRED_MODULES = {DRIVER_MODULE, "gene_annotation_episode.episodic_workflow.root.library.native_genomic_overlap_contracts",
                     "gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_contracts",
                     "gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_inputs"}


def _plain(value):
    """Reject Python coercions before JSON Schema sees the supplied object."""
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("genomic_overlap_invalid_execution_record") from error
        return
    if type(value) is float:
        _require(math.isfinite(value))
        return
    if type(value) is list:
        for row in value:
            _plain(row)
        return
    _require(type(value) is dict and all(type(key) is str for key in value))
    for key, row in value.items():
        _plain(key)
        _plain(row)



_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _, v: type(v) is int)
        .redefine("number", lambda _, v: type(v) in (int, float)))


@lru_cache(maxsize=len(_EXECUTION_DEFINITIONS))
def _validator(name):
    return _STRICT({"$defs": _definitions(), "$ref": "#/$defs/" + name}, format_checker=FormatChecker())


def _checked(value, name):
    _plain(value)
    _require(_validator(name).is_valid(value))
    return deepcopy(value)


def _path(value, *, absolute):
    _require(type(value) is str and value and not any(c in value for c in "\x00\r\n\\"),
             "genomic_overlap_invalid_path")
    path = PurePosixPath(value)
    _require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
             and value not in (".", "/") and not value.startswith("//"), "genomic_overlap_invalid_path")
    return path


def _overlap(left, right):
    return left == right or left in right.parents or right in left.parents


def _software(value):
    value = _checked(value, "SoftwareBinding")
    for field in ("python_executable", "module_root", "bedtools_executable"):
        _path(value[field], absolute=True)
    modules = [row["module"] for row in value["implementation_files"]]
    required = (_REQUIRED_MODULES if value["driver_module"] == DRIVER_MODULE else
                {name.replace("gene_annotation_episode.episodic_workflow.root.library.", "gene_annotation_episode.", 1)
                 for name in _REQUIRED_MODULES})
    _require(len(modules) == len(set(modules)) and required <= set(modules),
             "genomic_overlap_software_binding")
    _require(all(name.startswith("gene_annotation_episode.") and
                 re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", name, re.ASCII) for name in modules),
             "genomic_overlap_software_binding")
    for field in ("python_version", "bedtools_version"):
        _require(not any(c in value[field] for c in "\x00\r\n"), "genomic_overlap_software_binding")
    return value


def validate_genomic_overlap_bindings(value: list[dict]) -> list[dict]:
    """Validate explicit deployments; an empty list exposes no operation."""
    _require(type(value) is list, "genomic_overlap_binding_mismatch")
    rows = [_checked(row, "Binding") for row in value]
    for row in rows:
        _software(row["software"])
    _require(len({_digest(row) for row in rows}) == len(rows), "genomic_overlap_duplicate_binding")
    return rows


def _request(value):
    value = validate_genomic_overlap_record("Request", value)
    specs, comparisons = value["region_sets"], value["comparisons"]
    keys = [spec["set_key"] for spec in specs]
    _require(len(keys) == len(set(keys)), "genomic_overlap_duplicate_set_key")
    endpoints = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]]
    _require(len(comparisons) == len(endpoints) and len({p["comparison_key"] for p in comparisons})
             == len(comparisons), "genomic_overlap_comparison_population")
    for i, (pair, ends) in enumerate(zip(comparisons, endpoints)):
        _require(pair["ordinal"] == i and (pair["a_set_key"], pair["b_set_key"]) == ends,
                 "genomic_overlap_comparison_order")
    artifacts = {}
    for spec in specs:
        source = spec["source"]
        kind = "bed_artifact" if spec["format"] == "bed_outer_span_v1" else "coordinate_rows_artifact"
        _require(source["kind"] == kind and source["file"]["format"] == spec["format"],
                 "genomic_overlap_input_format_binding")
        identity = source["file"]
        prior = artifacts.setdefault(identity["artifact_ref"], identity)
        _require(prior == identity, "genomic_overlap_input_identity_mismatch")
    return value


def genomic_overlap_output_files(request: Request) -> list[dict]:
    request = _request(request)
    prefix = request["output_prefix"]
    rows = []

    def add(key, role, path, format_name, set_key=None, comparison_key=None):
        rows.append({"file_key": key, "role": role, "set_key": set_key, "comparison_key": comparison_key,
                     "relative_path": path, "format": format_name})

    add("stdout", "stdout", "stdout.log", "genomic_overlap_driver_log_v1")
    add("stderr", "stderr", "stderr.log", "native_stderr_text_v1")
    add("version_stdout", "version_stdout", prefix + "/software/version.stdout.txt", "native_stdout_text_v1")
    add("version_stderr", "version_stderr", prefix + "/software/version.stderr.txt", "native_stderr_text_v1")
    for i, spec in enumerate(request["region_sets"]):
        stem = "s" + str(i)
        root = prefix + "/sets/" + stem + "/"
        for suffix, role, filename, format_name in (
            ("original", "original_input", "original.data", spec["format"]),
            ("rejected", "rejected_input", "rejected-source.data", spec["format"]),
            ("parsed", "parsed_set", "parsed-set.json", "genomic_overlap_parsed_set_v1"),
            ("canonical", "canonical_set", "canonical.bed", "bed4_occurrence_v1")):
            add(stem + ":" + suffix, role, root + filename, format_name, set_key=spec["set_key"])
    for pair in request["comparisons"]:
        stem = "p" + str(pair["ordinal"])
        root = prefix + "/pairs/" + stem + "/"
        for suffix, role, filename, format_name in (
            ("manifest", "pair_manifest", "manifest.json", "genomic_overlap_native_manifest_v1"),
            ("stdout", "overlap_stdout", "overlap.wo.tsv", "bedtools_intersect_wo_bed4_v1"),
            ("stderr", "overlap_stderr", "stderr.txt", "native_stderr_text_v1")):
            add(stem + ":" + suffix, role, root + filename, format_name, comparison_key=pair["comparison_key"])
    add("batch_manifest", "batch_manifest", BATCH_FILENAME, "genomic_overlap_native_batch_v1")
    reserved = [PurePosixPath(name) for name in (RUN_PLAN_FILENAME, OWNER_FILENAME, STARTED_FILENAME,
        "tmp", "cache", "native.json", "invoke.json", "request.json", "ready.json", "release.json",
        "status.json", "result.json", "launcher.json")]
    paths = [_path(row["relative_path"], absolute=False) for row in rows]
    for i, path in enumerate(paths):
        _require(not any(_overlap(path, other) for other in reserved + paths[:i]),
                 "genomic_overlap_invalid_path")
    return rows


def _environment(value):
    forbidden = {"HOME", "TMP", "TEMP", "TMPDIR", "PYTHONHOME", "PYTHONUSERBASE",
                 "PYTHONPYCACHEPREFIX", "PYTHONPATH", "XDG_CACHE_HOME", "PIP_CACHE_DIR"}
    _require(value.get("LC_ALL") == "C" and value.get("PYTHONDONTWRITEBYTECODE", "1") == "1",
             "genomic_overlap_invalid_environment")
    _require(not any(key in forbidden or "CACHE" in key.upper() for key in value),
             "genomic_overlap_invalid_environment")
    _require(all("\x00" not in text for text in value.values()), "genomic_overlap_invalid_environment")


def validate_genomic_overlap_job(value: dict) -> dict:
    value = _checked(value, "NativeJob")
    request = _request(value["request"])
    _software(value["software"])
    _environment(value["environment"])
    specs, inputs = request["region_sets"], value["inputs"]
    _require([row["set_key"] for row in inputs] == [row["set_key"] for row in specs],
             "genomic_overlap_input_identity_mismatch")
    paths = [_path(row["path"], absolute=True) for row in inputs]
    for i, path in enumerate(paths):
        for j, prior in enumerate(paths[:i]):
            _require(not _overlap(path, prior) or (path == prior and
                specs[i]["source"]["file"] == specs[j]["source"]["file"]),
                "genomic_overlap_input_identity_mismatch")
    _require(value["outputs"] == genomic_overlap_output_files(request), "genomic_overlap_output_binding")
    return value


def compile_genomic_overlap_job(job: dict, *, plan_path: str = RUN_PLAN_FILENAME) -> dict:
    job = validate_genomic_overlap_job(job)
    if plan_path != RUN_PLAN_FILENAME:
        _require(_path(plan_path, absolute=True).name == RUN_PLAN_FILENAME, "genomic_overlap_invalid_path")
    return {"argv": [job["software"]["python_executable"], "-B", "-m", job["software"]["driver_module"], plan_path],
            "environment": deepcopy(job["environment"]), "outputs": deepcopy(job["outputs"])}


def requested_job_from_genomic_overlap(job: dict) -> dict:
    job = validate_genomic_overlap_job(job)
    compiled = compile_genomic_overlap_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_genomic_overlap": job}


def validate_genomic_overlap_requested_job(value: dict) -> dict:
    value = _checked(value, "RequestedJob")
    _require(value == requested_job_from_genomic_overlap(value["native_genomic_overlap"]),
             "original_attempt_mismatch")
    return value


