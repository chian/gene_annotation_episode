"""Pure records for the selected native all-pairs genomic overlap operation.

Fixed G2 definitions implement packet425 DATA_CONTRACT.json, SHA-256
4b8f38595549bd32484121129132474bc6fd3f5e9f7be1130433a6b3a208c00e.
G1 owns scientific records; these checks validate supplied execution facts and
associations, never observe files, grant source authority or execute work.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator, FormatChecker, validators
from .genomic_overlap_contracts import (
    ComparisonSpec, Request, genomic_overlap_schema, validate_genomic_overlap_record,
)

RUN_PLAN_FILENAME = "genomic-overlap-plan.json"
ATTEMPT_DIRECTORY_NAME = "genomic-overlap-attempt"
BATCH_FILENAME = "bundle.json"
OWNER_FILENAME = ".native-genomic-overlap-owner.json"
STARTED_FILENAME = ".native-genomic-overlap-started.json"
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
DRIVER_MODULE = "gene_annotation_episode.native_genomic_overlap_driver"
_REQUIRED_MODULES = {DRIVER_MODULE, "gene_annotation_episode.native_genomic_overlap_contracts",
                     "gene_annotation_episode.genomic_overlap_contracts",
                     "gene_annotation_episode.genomic_overlap_inputs"}

# Fixed data schemas, not an executable scoring language. G1 references below
# resolve to the unchanged, in-code G1 definitions in _definitions().
_EXECUTION_DEFINITIONS = {'Policy': {'type': 'object',
            'properties': {'memory_bytes': {'const': 21474836480},
                           'scratch_bytes': {'const': 4294967296},
                           'wall_seconds': {'type': 'null'}},
            'required': ['memory_bytes', 'scratch_bytes', 'wall_seconds'],
            'additionalProperties': False},
 'ImplementationFile': {'type': 'object',
                        'properties': {'module': {'type': 'string', 'minLength': 1},
                                       'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}},
                        'required': ['module', 'sha256'],
                        'additionalProperties': False},
 'SoftwareBinding': {'type': 'object',
                     'properties': {'python_executable': {'type': 'string', 'minLength': 1},
                                    'python_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                    'python_version': {'type': 'string', 'minLength': 1},
                                    'module_root': {'type': 'string', 'minLength': 1},
                                    'driver_module': {'const': 'gene_annotation_episode.native_genomic_overlap_driver'},
                                    'implementation_files': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/ImplementationFile'},
                                                             'minItems': 4},
                                    'bedtools_executable': {'type': 'string', 'minLength': 1},
                                    'bedtools_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                    'bedtools_version': {'type': 'string', 'minLength': 1}},
                     'required': ['python_executable',
                                  'python_sha256',
                                  'python_version',
                                  'module_root',
                                  'driver_module',
                                  'implementation_files',
                                  'bedtools_executable',
                                  'bedtools_sha256',
                                  'bedtools_version'],
                     'additionalProperties': False},
 'Binding': {'type': 'object',
             'properties': {'operation': {'const': 'analyze_genomic_region_overlap'},
                            'mode': {'const': 'unstranded_outer_span'},
                            'software': {'$ref': '#/$defs/SoftwareBinding'}},
             'required': ['operation', 'mode', 'software'],
             'additionalProperties': False},
 'InputBinding': {'type': 'object',
                  'properties': {'set_key': {'type': 'string', 'minLength': 1},
                                 'path': {'type': 'string', 'minLength': 1}},
                  'required': ['set_key', 'path'],
                  'additionalProperties': False},
 'OutputSpec': {'type': 'object',
                'properties': {'file_key': {'type': 'string', 'minLength': 1},
                               'role': {'enum': ['stdout',
                                                 'stderr',
                                                 'version_stdout',
                                                 'version_stderr',
                                                 'original_input',
                                                 'rejected_input',
                                                 'parsed_set',
                                                 'canonical_set',
                                                 'pair_manifest',
                                                 'overlap_stdout',
                                                 'overlap_stderr',
                                                 'batch_manifest']},
                               'set_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]},
                               'comparison_key': {'anyOf': [{'type': 'string', 'minLength': 1},
                                                            {'type': 'null'}]},
                               'relative_path': {'type': 'string', 'minLength': 1},
                               'format': {'type': 'string', 'minLength': 1}},
                'required': ['file_key', 'role', 'set_key', 'comparison_key', 'relative_path', 'format'],
                'additionalProperties': False},
 'NativeJob': {'type': 'object',
               'properties': {'version': {'const': 'native_genomic_overlap_job_v1'},
                              'program': {'const': 'bedtools_intersect_all_pairs'},
                              'request': {'$ref': '#/$defs/Request'},
                              'software': {'$ref': '#/$defs/SoftwareBinding'},
                              'inputs': {'type': 'array',
                                         'items': {'$ref': '#/$defs/InputBinding'},
                                         'minItems': 2},
                              'outputs': {'type': 'array',
                                          'items': {'$ref': '#/$defs/OutputSpec'},
                                          'minItems': 16},
                              'environment': {'type': 'object',
                                              'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
                                              'additionalProperties': {'type': 'string'}}},
               'required': ['version',
                            'program',
                            'request',
                            'software',
                            'inputs',
                            'outputs',
                            'environment'],
               'additionalProperties': False},
 'RequestedJob': {'type': 'object',
                  'properties': {'argv': {'type': 'array',
                                          'items': {'type': 'string', 'minLength': 1},
                                          'minItems': 5},
                                 'environment': {'type': 'object',
                                                 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
                                                 'additionalProperties': {'type': 'string'}},
                                 'native_genomic_overlap': {'$ref': '#/$defs/NativeJob'}},
                  'required': ['argv', 'environment', 'native_genomic_overlap'],
                  'additionalProperties': False},
 'AttemptIdentity': {'type': 'object',
                     'properties': {'run_id': {'type': 'string', 'minLength': 1},
                                    'episode_id': {'type': 'string', 'minLength': 1},
                                    'resource_id': {'type': 'string', 'minLength': 1},
                                    'execution_id': {'type': 'string', 'minLength': 1},
                                    'operation_key': {'type': 'string', 'minLength': 1},
                                    'attempt_id': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                    'requested_job_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                    'assignment_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}},
                     'required': ['run_id',
                                  'episode_id',
                                  'resource_id',
                                  'execution_id',
                                  'operation_key',
                                  'attempt_id',
                                  'requested_job_sha256',
                                  'assignment_sha256'],
                     'additionalProperties': False},
 'RunPlan': {'type': 'object',
             'properties': {'version': {'const': 'native_genomic_overlap_run_plan_v1'},
                            'identity': {'$ref': '#/$defs/AttemptIdentity'},
                            'requested_job': {'$ref': '#/$defs/RequestedJob'},
                            'attempt_directory': {'type': 'string', 'minLength': 1},
                            'policy': {'$ref': '#/$defs/Policy'}},
             'required': ['version', 'identity', 'requested_job', 'attempt_directory', 'policy'],
             'additionalProperties': False},
 'DriverFailure': {'type': 'object',
                   'properties': {'code': {'enum': ['input_unavailable',
                                                    'input_digest_mismatch',
                                                    'invalid_input',
                                                    'native_dependency_unavailable',
                                                    'native_version_unverified',
                                                    'software_identity_mismatch',
                                                    'native_spawn_failed',
                                                    'native_nonzero_exit',
                                                    'resource_limit',
                                                    'output_unavailable',
                                                    'seal_failed']},
                                  'stage': {'enum': ['input', 'software', 'native', 'seal']},
                                  'set_key': {'anyOf': [{'type': 'string', 'minLength': 1},
                                                        {'type': 'null'}]},
                                  'comparison_key': {'anyOf': [{'type': 'string', 'minLength': 1},
                                                               {'type': 'null'}]},
                                  'file_key': {'anyOf': [{'type': 'string', 'minLength': 1},
                                                         {'type': 'null'}]},
                                  'field_path': {'anyOf': [{'type': 'string', 'pattern': '^/'},
                                                           {'type': 'null'}]},
                                  'expected_value': {'$ref': '#/$defs/JsonValue'},
                                  'observed_value': {'$ref': '#/$defs/JsonValue'}},
                   'required': ['code',
                                'stage',
                                'set_key',
                                'comparison_key',
                                'file_key',
                                'field_path',
                                'expected_value',
                                'observed_value'],
                   'additionalProperties': False},
 'BatchFile': {'type': 'object',
               'properties': {'specification': {'$ref': '#/$defs/OutputSpec'},
                              'declaration': {'$ref': '#/$defs/NativeFileDeclaration'}},
               'required': ['specification', 'declaration'],
               'additionalProperties': False},
 'SetOutput': {'type': 'object',
               'properties': {'set_key': {'type': 'string', 'minLength': 1},
                              'set_position': {'type': 'integer', 'minimum': 0},
                              'input_state': {'enum': ['verified', 'unavailable', 'digest_mismatch']},
                              'measured_fingerprint': {'anyOf': [{'$ref': '#/$defs/NativeSourceFingerprint'},
                                                                 {'type': 'null'}]},
                              'parse_extent': {'anyOf': [{'enum': ['complete', 'partial', 'unavailable']},
                                                         {'type': 'null'}]},
                              'original_file_key': {'type': 'string', 'minLength': 1},
                              'rejected_file_key': {'type': 'string', 'minLength': 1},
                              'parsed_file_key': {'type': 'string', 'minLength': 1},
                              'canonical_file_key': {'type': 'string', 'minLength': 1},
                              'failure_indices': {'type': 'array',
                                                  'items': {'type': 'integer', 'minimum': 0},
                                                  'uniqueItems': True}},
               'required': ['set_key',
                            'set_position',
                            'input_state',
                            'measured_fingerprint',
                            'parse_extent',
                            'original_file_key',
                            'rejected_file_key',
                            'parsed_file_key',
                            'canonical_file_key',
                            'failure_indices'],
               'additionalProperties': False},
 'PairOutput': {'type': 'object',
                'properties': {'comparison': {'$ref': '#/$defs/ComparisonSpec'},
                               'disposition': {'enum': ['native_succeeded',
                                                        'native_failed',
                                                        'analytic_empty',
                                                        'invalid_input',
                                                        'input_unavailable',
                                                        'native_unavailable']},
                               'manifest_file_key': {'anyOf': [{'type': 'string', 'minLength': 1},
                                                               {'type': 'null'}]},
                               'manifest': {'anyOf': [{'$ref': '#/$defs/NativeDriverManifest'},
                                                      {'type': 'null'}]},
                               'failure_indices': {'type': 'array',
                                                   'items': {'type': 'integer', 'minimum': 0},
                                                   'uniqueItems': True}},
                'required': ['comparison',
                             'disposition',
                             'manifest_file_key',
                             'manifest',
                             'failure_indices'],
                'additionalProperties': False},
 'VersionProbe': {'type': 'object',
                  'properties': {'realized_argv': {'type': 'array',
                                                   'items': {'type': 'string', 'minLength': 1},
                                                   'minItems': 2},
                                 'environment': {'type': 'object',
                                                 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
                                                 'additionalProperties': {'type': 'string'}},
                                 'returncode': {'type': 'integer'},
                                 'started_at': {'type': 'string', 'format': 'date-time'},
                                 'finished_at': {'type': 'string', 'format': 'date-time'},
                                 'writer_closed': {'const': True},
                                 'stdout_file_key': {'const': 'version_stdout'},
                                 'stderr_file_key': {'const': 'version_stderr'}},
                  'required': ['realized_argv',
                               'environment',
                               'returncode',
                               'started_at',
                               'finished_at',
                               'writer_closed',
                               'stdout_file_key',
                               'stderr_file_key'],
                  'additionalProperties': False},
 'SoftwareVerification': {'type': 'object',
                          'properties': {'state': {'enum': ['verified', 'not_needed', 'failed']},
                                         'python_observed': {'anyOf': [{'type': 'object',
                                                                        'properties': {'sha256': {'type': 'string',
                                                                                                  'pattern': '^[0-9a-f]{64}$'},
                                                                                       'version': {'type': 'string',
                                                                                                   'minLength': 1}},
                                                                        'required': ['sha256', 'version'],
                                                                        'additionalProperties': False},
                                                                       {'type': 'null'}]},
                                         'bedtools_observed': {'anyOf': [{'$ref': '#/$defs/Software'},
                                                                         {'type': 'null'}]},
                                         'version_probe': {'anyOf': [{'$ref': '#/$defs/VersionProbe'},
                                                                     {'type': 'null'}]},
                                         'failure_indices': {'type': 'array',
                                                             'items': {'type': 'integer', 'minimum': 0},
                                                             'uniqueItems': True}},
                          'required': ['state',
                                       'python_observed',
                                       'bedtools_observed',
                                       'version_probe',
                                       'failure_indices'],
                          'additionalProperties': False},
 'BatchManifest': {'type': 'object',
                   'properties': {'version': {'const': 'genomic_overlap_native_batch_v1'},
                                  'identity': {'$ref': '#/$defs/NativeIdentity'},
                                  'plan_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                  'requested_job_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                  'policy': {'$ref': '#/$defs/Policy'},
                                  'driver_argv': {'type': 'array',
                                                  'items': {'type': 'string', 'minLength': 1},
                                                  'minItems': 5},
                                  'realized_environment': {'type': 'object',
                                                           'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
                                                           'additionalProperties': {'type': 'string'}},
                                  'requested_set_keys': {'type': 'array',
                                                         'items': {'type': 'string', 'minLength': 1},
                                                         'minItems': 2,
                                                         'uniqueItems': True},
                                  'requested_comparisons': {'type': 'array',
                                                            'items': {'$ref': '#/$defs/ComparisonSpec'},
                                                            'minItems': 1},
                                  'software_verification': {'$ref': '#/$defs/SoftwareVerification'},
                                  'sets': {'type': 'array',
                                           'items': {'$ref': '#/$defs/SetOutput'},
                                           'minItems': 2},
                                  'pairs': {'type': 'array',
                                            'items': {'$ref': '#/$defs/PairOutput'},
                                            'minItems': 1},
                                  'files': {'type': 'array',
                                            'items': {'$ref': '#/$defs/BatchFile'},
                                            'minItems': 15},
                                  'failures': {'type': 'array', 'items': {'$ref': '#/$defs/DriverFailure'}},
                                  'batch_status': {'enum': ['complete', 'partial', 'failed']},
                                  'started_at': {'type': 'string', 'format': 'date-time'},
                                  'finished_at': {'type': 'string', 'format': 'date-time'},
                                  'sealed': {'const': True}},
                   'required': ['version',
                                'identity',
                                'plan_sha256',
                                'requested_job_sha256',
                                'policy',
                                'driver_argv',
                                'realized_environment',
                                'requested_set_keys',
                                'requested_comparisons',
                                'software_verification',
                                'sets',
                                'pairs',
                                'files',
                                'failures',
                                'batch_status',
                                'started_at',
                                'finished_at',
                                'sealed'],
                   'additionalProperties': False}}


def _require(condition, code="genomic_overlap_invalid_execution_record"):
    if not condition:
        raise ValueError(code)


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


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _references(value):
    if type(value) is dict:
        if "$ref" in value:
            yield value["$ref"].removeprefix("#/$defs/")
        for item in value.values():
            yield from _references(item)
    elif type(value) is list:
        for item in value:
            yield from _references(item)


@lru_cache(maxsize=1)
def _definitions():
    # Include only referenced G1 records, without copying or revising their
    # scientific definitions. Every resulting reference is local and finite.
    science = genomic_overlap_schema("Request")["$defs"]
    result = deepcopy(_EXECUTION_DEFINITIONS)
    pending = set(_references(result)) - result.keys()
    while pending:
        name = pending.pop()
        result[name] = science[name]
        pending.update(set(_references(result[name])) - result.keys())
    return result


def genomic_overlap_execution_schema(record_name: str, *, bindings: list[dict] | None = None) -> dict:
    """Return a detached fixed record schema, nestable in commission schemas."""
    _require(type(record_name) is str and record_name in _EXECUTION_DEFINITIONS,
             "genomic_overlap_unknown_execution_record")
    root = {"$ref": "#/$defs/" + record_name}
    if bindings is not None:
        _require(record_name == "RequestedJob", "genomic_overlap_binding_mismatch")
        selected = validate_genomic_overlap_bindings(bindings)
        alternatives = [{"allOf": [root, {"properties": {"native_genomic_overlap": {
            "properties": {"software": {"const": row["software"]}}}}}]} for row in selected]
        root = {"anyOf": alternatives} if alternatives else {"not": {}}
    # The applicator gives each nested resource its own reference scope even
    # inside a sibling oneOf/anyOf. No remote schema resolution is needed.
    resource = {"$defs": deepcopy(_definitions()), **root}
    resource["$id"] = "urn:gene-annotation:genomic-overlap-execution:schema:" + _digest(resource)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "allOf": [resource]}


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
    _require(len(modules) == len(set(modules)) and _REQUIRED_MODULES <= set(modules),
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
    return {"argv": [job["software"]["python_executable"], "-B", "-m", DRIVER_MODULE, plan_path],
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


def validate_genomic_overlap_run_plan(value: dict) -> dict:
    value = _checked(value, "RunPlan")
    request = validate_genomic_overlap_requested_job(value["requested_job"])
    identity = value["identity"]
    execution = _path(identity["execution_id"], absolute=True)
    attempt = _path(value["attempt_directory"], absolute=True)
    _require(execution.name == "native.json" and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME,
             "original_attempt_mismatch")
    _require(identity["attempt_id"] == _digest(identity["operation_key"]) and
             identity["requested_job_sha256"] == _digest(request), "original_attempt_mismatch")
    _require(execution.parent.name == identity["attempt_id"] and execution.parent.parent.name ==
             _digest({"run": identity["run_id"], "episode": identity["episode_id"]}) and
             execution.parent.parent.parent.name == ".episode-operations", "original_attempt_mismatch")
    _require(type(value["policy"]["memory_bytes"]) is int and type(value["policy"]["scratch_bytes"]) is int
             and value["policy"] == POLICY, "genomic_overlap_policy_mismatch")
    for row in request["native_genomic_overlap"]["inputs"]:
        _require(not _overlap(_path(row["path"], absolute=True), execution.parent),
                 "genomic_overlap_invalid_path")
    return value


def genomic_overlap_driver_argv(plan: dict) -> list[str]:
    plan = validate_genomic_overlap_run_plan(plan)
    return compile_genomic_overlap_job(plan["requested_job"]["native_genomic_overlap"],
        plan_path=str(PurePosixPath(plan["identity"]["execution_id"]).parent / RUN_PLAN_FILENAME))["argv"]


def genomic_overlap_environment(job: dict, *, attempt_directory: str) -> dict:
    job = validate_genomic_overlap_job(job)
    root = _path(attempt_directory, absolute=True)
    return {**job["environment"], "PYTHONPATH": job["software"]["module_root"],
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "TMP": str(root / "tmp"),
            "TEMP": str(root / "tmp"), "TMPDIR": str(root / "tmp"),
            "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip")}


def _native_identity(plan):
    identity = plan["identity"]
    return {**{k: identity[k] for k in ("run_id", "resource_id", "execution_id", "attempt_id", "operation_key")},
            "origin_episode_id": identity["episode_id"]}


def _fingerprint(spec):
    return {"set_key": spec["set_key"], **{k: spec["source"]["file"][k] for k in ("format", "sha256", "size_bytes")}}


def _declared_software(plan):
    software = plan["requested_job"]["native_genomic_overlap"]["software"]
    return {"executable": software["bedtools_executable"], "declared_version": software["bedtools_version"],
            "observed_version": software["bedtools_version"], "executable_sha256": software["bedtools_sha256"]}


def _interval(value):
    try:
        start, finish = (datetime.fromisoformat(value[k].replace("Z", "+00:00"))
                         for k in ("started_at", "finished_at"))
        _require(start.tzinfo is not None and finish.tzinfo is not None and finish >= start,
                 "genomic_overlap_invalid_times")
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("genomic_overlap_invalid_times") from error
    return start, finish


def _declaration(value):
    value = validate_genomic_overlap_record("NativeFileDeclaration", value)
    _path(value["relative_path"], absolute=False)
    _require((value["sha256"] is not None and value["size_bytes"] is not None) if value["state"] == "present"
             else (value["sha256"] is None and value["size_bytes"] is None), "genomic_overlap_file_declaration")
    if value["size_bytes"] == 0:
        _require(value["sha256"] == hashlib.sha256(b"").hexdigest(), "genomic_overlap_file_declaration")
    return value


def _set_outputs(values, request):
    _require(type(values) is list and len(values) == len(request["region_sets"]), "genomic_overlap_set_binding")
    rows = [_checked(row, "SetOutput") for row in values]
    for i, (row, spec) in enumerate(zip(rows, request["region_sets"])):
        _require(row["set_key"] == spec["set_key"] and row["set_position"] == i and
                 all(row[k + "_file_key"] == "s" + str(i) + ":" + k for k in
                     ("original", "rejected", "parsed", "canonical")), "genomic_overlap_set_binding")
        fp = row["measured_fingerprint"]
        if row["input_state"] == "unavailable":
            _require(fp is None and row["parse_extent"] in (None, "unavailable"), "genomic_overlap_set_binding")
        else:
            _require(fp is not None and fp["set_key"] == spec["set_key"] and fp["format"] == spec["format"],
                     "genomic_overlap_input_identity_mismatch")
            _require((fp == _fingerprint(spec)) == (row["input_state"] == "verified"),
                     "genomic_overlap_input_identity_mismatch")
            if row["input_state"] == "digest_mismatch":
                _require(row["parse_extent"] in (None, "unavailable"), "genomic_overlap_set_binding")
    return rows


def validate_genomic_overlap_independent_pair_manifest(value: object, *, plan: dict,
        comparison: ComparisonSpec) -> dict:
    """Validate an original pair seal without inventing missing batch facts.

    This checks only supplied original declarations. Current input availability
    and scientific use are checked separately by G1; source/closure authority
    and the seal's actual byte capture remain host responsibilities.
    """
    plan = validate_genomic_overlap_run_plan(plan)
    request = plan["requested_job"]["native_genomic_overlap"]["request"]
    comparison = validate_genomic_overlap_record("ComparisonSpec", comparison)
    _require(comparison in request["comparisons"], "genomic_overlap_pair_binding")
    sets = {row["set_key"]: (i, row) for i, row in enumerate(request["region_sets"])}
    operands = [sets[comparison[k + "_set_key"]] for k in ("a", "b")]
    value = validate_genomic_overlap_record("NativeDriverManifest", value)
    _require(value["identity"] == _native_identity(plan) and value["comparison_key"] == comparison["comparison_key"]
        and all(value[k + "_set_key"] == comparison[k + "_set_key"] for k in ("a", "b")),
        "genomic_overlap_pair_binding")
    _require(value["input_fingerprints"] == [_fingerprint(spec) for _, spec in operands],
        "genomic_overlap_input_identity_mismatch")
    _require(value["writer_closed"] is True, "genomic_overlap_pair_not_closed")
    if value["derivation"] != "bedtools_intersect":
        _require(value["outcome"] == "not_executed" and value["software"] is None and
            value["returncode"] is None and value["started_at"] is None and value["finished_at"] is None and
            value["realized_argv"] == [] and value["environment"] == {} and value["files"] == [],
            "genomic_overlap_uninvoked_facts")
        return value
    _require(value["outcome"] in ("succeeded", "failed") and type(value["returncode"]) is int
        and ((value["returncode"] == 0) == (value["outcome"] == "succeeded")), "genomic_overlap_native_outcome")
    _interval(value)
    _require(value["software"] == _declared_software(plan), "genomic_overlap_software_binding")
    expected = genomic_overlap_output_files(request)
    by_key = {row["file_key"]: row for row in expected}
    keys = ["s" + str(i) + ":canonical" for i, _ in operands] + ["p" + str(comparison["ordinal"]) + ":" + k
                                                          for k in ("stdout", "stderr")]
    roles = ("canonical_a", "canonical_b", "overlap_stdout", "overlap_stderr")
    _require(len(value["files"]) == 4, "genomic_overlap_pair_files")
    for i, (row, key, role) in enumerate(zip(value["files"], keys, roles)):
        decl = _declaration(row["declaration"])
        _require(row["file_key"] == comparison["comparison_key"] + ":file:" + str(i) and row["role"] == role
            and all(decl[k] == by_key[key][k] for k in ("relative_path", "format")), "genomic_overlap_pair_files")
        if i < 2 or value["outcome"] == "succeeded":
            _require(decl["state"] == "present", "genomic_overlap_pair_files")
        if i < 2:
            _require(decl["size_bytes"] > 0, "genomic_overlap_empty_input_binding")
    attempt = PurePosixPath(plan["attempt_directory"])
    expected_argv = [value["software"]["executable"], "intersect", "-a", str(attempt / by_key[keys[0]]["relative_path"]),
                     "-b", str(attempt / by_key[keys[1]]["relative_path"]), "-wo", "-sorted"]
    _require(value["realized_argv"] == expected_argv and value["environment"] ==
        genomic_overlap_environment(plan["requested_job"]["native_genomic_overlap"], attempt_directory=str(attempt)),
        "genomic_overlap_native_invocation")
    return value


def validate_genomic_overlap_pair_manifest(value: dict, *, plan: dict,
        comparison: ComparisonSpec, set_outputs: list[dict]) -> dict:
    """Also check an original pair against its supplied batch set observations."""
    plan = validate_genomic_overlap_run_plan(plan)
    request = plan["requested_job"]["native_genomic_overlap"]["request"]
    comparison = validate_genomic_overlap_record("ComparisonSpec", comparison)
    _require(comparison in request["comparisons"], "genomic_overlap_pair_binding")
    sets = {row["set_key"]: row for row in _set_outputs(set_outputs, request)}
    operands = [sets[comparison[k + "_set_key"]] for k in ("a", "b")]
    value = validate_genomic_overlap_independent_pair_manifest(value, plan=plan, comparison=comparison)
    _require(all(row["input_state"] == "verified" for row in operands) and
        value["input_fingerprints"] == [row["measured_fingerprint"] for row in operands],
        "genomic_overlap_input_identity_mismatch")
    complete = all(row["parse_extent"] == "complete" for row in operands)
    if value["derivation"] == "validated_empty_input":
        _require(complete, "genomic_overlap_empty_input_binding")
    elif value["derivation"] == "not_executed_invalid_input":
        _require(not complete and any(row["parse_extent"] in ("partial", "unavailable") for row in operands),
                 "genomic_overlap_invalid_input_binding")
    else:
        _require(complete, "genomic_overlap_native_outcome")
    return value


def validate_genomic_overlap_batch(value: dict, *, plan: dict) -> dict:
    """Validate a supplied seal and its joins; never inspect producer paths."""
    plan = validate_genomic_overlap_run_plan(plan)
    value = _checked(value, "BatchManifest")
    job = plan["requested_job"]["native_genomic_overlap"]
    request, software = job["request"], job["software"]
    environment = genomic_overlap_environment(job, attempt_directory=plan["attempt_directory"])
    _require(value["identity"] == _native_identity(plan) and value["plan_sha256"] == _digest(plan)
        and value["requested_job_sha256"] == plan["identity"]["requested_job_sha256"]
        and value["policy"] == plan["policy"] and type(value["policy"]["memory_bytes"]) is int
        and type(value["policy"]["scratch_bytes"]) is int and value["driver_argv"] == genomic_overlap_driver_argv(plan)
        and value["realized_environment"] == environment, "original_attempt_mismatch")
    _require(value["requested_set_keys"] == [row["set_key"] for row in request["region_sets"]]
        and value["requested_comparisons"] == request["comparisons"], "genomic_overlap_batch_population")
    start, finish = _interval(value)
    sets = _set_outputs(value["sets"], request)
    set_index = {row["set_key"]: row for row in sets}
    comparisons = {row["comparison_key"]: row for row in request["comparisons"]}
    specifications = genomic_overlap_output_files(request)
    _require([row["specification"] for row in value["files"]] == specifications[:-1],
             "genomic_overlap_batch_files")
    files = {}
    specs = {row["file_key"]: row for row in specifications}
    for row in value["files"]:
        specification, declaration = row["specification"], _declaration(row["declaration"])
        _require(all(declaration[k] == specification[k] for k in ("relative_path", "format")),
                 "genomic_overlap_batch_files")
        files[specification["file_key"]] = declaration
    failures = value["failures"]
    for failure in failures:
        sk, pk, fk = (failure[k] for k in ("set_key", "comparison_key", "file_key"))
        _require(sk is None or sk in set_index, "genomic_overlap_failure_binding")
        _require(pk is None or pk in comparisons, "genomic_overlap_failure_binding")
        _require(fk is None or fk in specs, "genomic_overlap_failure_binding")
        if sk is not None and pk is not None:
            _require(sk in (comparisons[pk]["a_set_key"], comparisons[pk]["b_set_key"]),
                     "genomic_overlap_failure_binding")
        if fk is not None:
            spec = specs[fk]
            _require(sk is None or spec["set_key"] in (None, sk), "genomic_overlap_failure_binding")
            _require(pk is None or spec["comparison_key"] in (None, pk), "genomic_overlap_failure_binding")
            if pk is not None and spec["set_key"] is not None:
                _require(spec["set_key"] in (comparisons[pk]["a_set_key"], comparisons[pk]["b_set_key"]),
                         "genomic_overlap_failure_binding")
            if sk is not None and spec["comparison_key"] is not None:
                pair = comparisons[spec["comparison_key"]]
                _require(sk in (pair["a_set_key"], pair["b_set_key"]), "genomic_overlap_failure_binding")

    referenced = set()

    def failure_rows(indices, *, set_key=None, comparison=None, software_only=False):
        result = []
        for index in indices:
            _require(index < len(failures), "genomic_overlap_failure_binding")
            failure = failures[index]
            if set_key is not None:
                _require(failure["set_key"] in (None, set_key) and failure["comparison_key"] is None,
                         "genomic_overlap_failure_binding")
            if comparison is not None:
                _require(failure["comparison_key"] in (None, comparison["comparison_key"])
                    and failure["set_key"] in (None, comparison["a_set_key"], comparison["b_set_key"]),
                    "genomic_overlap_failure_binding")
            if software_only:
                _require(failure["stage"] == "software" and failure["set_key"] is None,
                         "genomic_overlap_failure_binding")
            referenced.add(index)
            result.append(failure)
        return result

    verification = value["software_verification"]
    software_failures = failure_rows(verification["failure_indices"], software_only=True)
    python_expected = {"sha256": software["python_sha256"], "version": software["python_version"]}
    if verification["state"] in ("verified", "not_needed"):
        _require(verification["python_observed"] == python_expected and not software_failures,
                 "genomic_overlap_software_binding")
    else:
        _require(bool(software_failures), "genomic_overlap_software_binding")
    implementation_failed = verification["python_observed"] != python_expected or any(
        f["code"] == "software_identity_mismatch" and (f["field_path"] == "/software" or
            (f["field_path"] or "").startswith(("/software/python_", "/software/implementation_files/",
                                                "/software/module_root/"))) for f in software_failures)
    if implementation_failed:
        _require(verification["state"] == "failed" and
            any(f["code"] == "software_identity_mismatch" for f in software_failures) and
            all(row["parse_extent"] is None for row in sets), "genomic_overlap_software_binding")
    probe = verification["version_probe"]
    observed = verification["bedtools_observed"]
    if observed is not None:
        _require(observed["executable"] == software["bedtools_executable"] and
            observed["declared_version"] == software["bedtools_version"], "genomic_overlap_software_binding")
        _require(observed["observed_version"] is None or probe is not None, "genomic_overlap_uninvoked_facts")
    if verification["state"] == "verified":
        _require(observed == _declared_software(plan) and probe is not None and probe["returncode"] == 0,
                 "genomic_overlap_software_binding")
    if verification["state"] == "not_needed":
        _require(probe is None and observed is None, "genomic_overlap_uninvoked_facts")
    if probe is not None:
        probe_start, probe_finish = _interval(probe)
        _require(start <= probe_start <= probe_finish <= finish and probe["realized_argv"] ==
            [software["bedtools_executable"], "--version"] and probe["environment"] == environment,
            "genomic_overlap_native_invocation")
        _require(all(files[k]["state"] == "present" for k in ("version_stdout", "version_stderr")),
                 "genomic_overlap_batch_files")
    elif verification["state"] == "not_needed":
        _require(all(files[k]["state"] == "absent" for k in ("version_stdout", "version_stderr")),
                 "genomic_overlap_uninvoked_facts")

    for row in sets:
        located = failure_rows(row["failure_indices"], set_key=row["set_key"])
        original, rejected, parsed, canonical = [files[row[k + "_file_key"]] for k in
                                                ("original", "rejected", "parsed", "canonical")]
        fp = row["measured_fingerprint"]
        if row["input_state"] == "verified":
            _require(original["state"] == "present" and rejected["state"] == "absent" and
                all(original[k] == fp[k] for k in ("sha256", "size_bytes", "format")),
                "genomic_overlap_input_identity_mismatch")
        elif row["input_state"] == "digest_mismatch":
            _require(original["state"] == "absent" and rejected["state"] == "present" and
                all(rejected[k] == fp[k] for k in ("sha256", "size_bytes", "format")) and
                any(f["code"] == "input_digest_mismatch" for f in located), "genomic_overlap_input_identity_mismatch")
        else:
            _require(original["state"] == "absent" and any(f["code"] in
                ("input_unavailable", "resource_limit", "output_unavailable", "seal_failed") for f in located),
                "genomic_overlap_input_identity_mismatch")
        if row["parse_extent"] is None:
            _require(parsed["state"] == canonical["state"] == "absent" and bool(located or software_failures),
                     "genomic_overlap_set_binding")
        else:
            _require(parsed["state"] == "present", "genomic_overlap_set_binding")
            if row["parse_extent"] == "complete":
                _require(canonical["state"] == "present" or any(f["code"] in
                    ("seal_failed", "resource_limit", "output_unavailable") for f in located),
                    "genomic_overlap_set_binding")
            else:
                _require(canonical["state"] == "absent", "genomic_overlap_set_binding")
        if row["parse_extent"] not in (None, "complete"):
            _require(bool(located), "genomic_overlap_failure_binding")

    _require(len(value["pairs"]) == len(request["comparisons"]), "genomic_overlap_batch_population")
    successful = 0
    needs_bedtools = False
    for row, comparison in zip(value["pairs"], request["comparisons"]):
        _require(row["comparison"] == comparison, "genomic_overlap_pair_binding")
        pair_failures = failure_rows(row["failure_indices"], comparison=comparison)
        operands = [set_index[comparison[k + "_set_key"]] for k in ("a", "b")]
        canonical_files = [files[r["canonical_file_key"]] for r in operands]
        complete = all(r["parse_extent"] == "complete" for r in operands)
        verified_inputs = all(r["input_state"] == "verified" for r in operands)
        # A complete parsed map can survive a failed canonical-file publication.
        # Keep that fact, but do not require an analytic-success disposition for
        # a pair whose other canonical input was never successfully published.
        is_empty = complete and all(f["state"] == "present" for f in canonical_files) and any(
            f["size_bytes"] == 0 for f in canonical_files)
        eligible_native = complete and all(f["state"] == "present" and f["size_bytes"] > 0 for f in canonical_files)
        needs_bedtools |= eligible_native
        stem = "p" + str(comparison["ordinal"]) + ":"
        disposition, manifest = row["disposition"], row["manifest"]
        if disposition in ("input_unavailable", "native_unavailable"):
            _require(manifest is None and row["manifest_file_key"] is None and files[stem + "manifest"]["state"] == "absent"
                and bool(pair_failures), "genomic_overlap_uninvoked_facts")
            if disposition == "input_unavailable":
                _require(not verified_inputs and all(files[stem + k]["state"] == "absent" for k in ("stdout", "stderr")),
                         "genomic_overlap_input_identity_mismatch")
                _require(any(f["code"] in ("input_unavailable", "input_digest_mismatch", "resource_limit",
                    "output_unavailable", "seal_failed") for f in pair_failures), "genomic_overlap_failure_binding")
            else:
                _require(verified_inputs and not is_empty and any(f["code"] in
                    ("native_dependency_unavailable", "native_version_unverified", "software_identity_mismatch",
                     "native_spawn_failed", "resource_limit", "output_unavailable", "seal_failed") for f in pair_failures),
                    "genomic_overlap_failure_binding")
                # A failed interpreter/implementation check may retain verified
                # originals without running G1 on unverified code.
                if not complete:
                    _require(any(r["parse_extent"] is None for r in operands) and
                        (verification["state"] == "failed" and any(f["code"] == "software_identity_mismatch"
                            for f in pair_failures) or any(f["code"] in
                            ("seal_failed", "resource_limit", "output_unavailable") for f in pair_failures)),
                        "genomic_overlap_set_binding")
            continue
        _require(manifest is not None and row["manifest_file_key"] == stem + "manifest"
            and files[stem + "manifest"]["state"] == "present", "genomic_overlap_pair_binding")
        checked = validate_genomic_overlap_pair_manifest(manifest, plan=plan, comparison=comparison, set_outputs=sets)
        # Pair JSON is an immutable canonical control record with one LF. This
        # checks its declared original bytes; the host still captures them.
        raw = json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8") + b"\n"
        _require(files[stem + "manifest"]["sha256"] == hashlib.sha256(raw).hexdigest() and
            files[stem + "manifest"]["size_bytes"] == len(raw), "genomic_overlap_pair_seal_mismatch")
        expected = {"native_succeeded": ("bedtools_intersect", "succeeded"),
                    "native_failed": ("bedtools_intersect", "failed"),
                    "analytic_empty": ("validated_empty_input", "not_executed"),
                    "invalid_input": ("not_executed_invalid_input", "not_executed")}[disposition]
        _require((manifest["derivation"], manifest["outcome"]) == expected, "genomic_overlap_native_outcome")
        if disposition in ("analytic_empty", "invalid_input"):
            _require(all(files[stem + k]["state"] == "absent" for k in ("stdout", "stderr")),
                     "genomic_overlap_uninvoked_facts")
            if disposition == "analytic_empty":
                _require(is_empty and not pair_failures, "genomic_overlap_empty_input_binding")
            else:
                _require(any(f["code"] == "invalid_input" for f in pair_failures), "genomic_overlap_failure_binding")
        else:
            _require(eligible_native and verification["state"] == "verified", "genomic_overlap_software_binding")
            pair_start, pair_finish = _interval(manifest)
            _require(start <= pair_start <= pair_finish <= finish and _interval(probe)[1] <= pair_start,
                     "genomic_overlap_invalid_times")
            keys = [r["canonical_file_key"] for r in operands] + [stem + "stdout", stem + "stderr"]
            _require([r["declaration"] for r in manifest["files"]] == [files[k] for k in keys],
                     "genomic_overlap_pair_files")
            if disposition == "native_failed":
                _require(any(f["code"] == "native_nonzero_exit" for f in pair_failures),
                         "genomic_overlap_failure_binding")
            else:
                _require(not pair_failures, "genomic_overlap_failure_binding")
        successful += disposition in ("native_succeeded", "analytic_empty")
    if verification["state"] == "not_needed":
        _require(not needs_bedtools, "genomic_overlap_software_binding")
    if verification["state"] == "verified":
        _require(needs_bedtools, "genomic_overlap_software_binding")
    # Unreferenced seal-level failures can concern the final batch or driver
    # logs; input/software/native failures must resolve to their owning rows.
    _require(all(i in referenced or f["stage"] == "seal" for i, f in enumerate(failures)),
             "genomic_overlap_failure_binding")
    all_success = successful == len(request["comparisons"]) and all(r["parse_extent"] == "complete" for r in sets)
    expected_status = "complete" if all_success else "partial" if successful else "failed"
    _require(value["batch_status"] == expected_status, "genomic_overlap_batch_status")
    return value


__all__ = ["RUN_PLAN_FILENAME", "ATTEMPT_DIRECTORY_NAME", "BATCH_FILENAME", "OWNER_FILENAME", "STARTED_FILENAME", "POLICY",
    "genomic_overlap_execution_schema", "validate_genomic_overlap_bindings", "validate_genomic_overlap_job",
    "genomic_overlap_output_files", "compile_genomic_overlap_job", "requested_job_from_genomic_overlap",
    "validate_genomic_overlap_requested_job", "validate_genomic_overlap_run_plan", "genomic_overlap_driver_argv",
    "genomic_overlap_environment", "validate_genomic_overlap_batch", "validate_genomic_overlap_pair_manifest",
    "validate_genomic_overlap_independent_pair_manifest"]
