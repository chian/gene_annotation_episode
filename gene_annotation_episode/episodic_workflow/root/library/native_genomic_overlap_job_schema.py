"""Supplied-record schemas; no execution admission."""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_contracts import genomic_overlap_schema

POLICY = {'memory_bytes': 5368709120, 'scratch_bytes': 4294967296}


def validate_recorded_genomic_overlap_policy(value, *, code="genomic_overlap_policy_mismatch"):
    """Check retained allocations without authorizing their execution."""
    _require(type(value) is dict and set(value) == {"memory_bytes", "scratch_bytes"}, code)
    _require(type(value["memory_bytes"]) is int and value["memory_bytes"] == POLICY["memory_bytes"]
        and type(value["scratch_bytes"]) is int and value["scratch_bytes"] == POLICY["scratch_bytes"], code)
    return deepcopy(value)


_EXECUTION_DEFINITIONS = {'Policy': {'type': 'object',
            'properties': {'memory_bytes': {'enum': [5368709120]}, 'scratch_bytes': {'const': 4294967296}},
            'required': ['memory_bytes', 'scratch_bytes'],
            'additionalProperties': False},
 'ImplementationFile': {'type': 'object',
                        'properties': {'module': {'type': 'string', 'minLength': 1}},
                        'required': ['module'],
                        'additionalProperties': False},
 'SoftwareBinding': {'type': 'object',
                     'properties': {'python_executable': {'type': 'string', 'minLength': 1},
                                    'python_version': {'type': 'string', 'minLength': 1},
                                    'module_root': {'type': 'string', 'minLength': 1},
                                    'driver_module': {'enum': ['gene_annotation_episode.episodic_workflow.root.library.native_genomic_overlap_driver']},
                                    'implementation_files': {'type': 'array',
                                                             'items': {'$ref': '#/$defs/ImplementationFile'},
                                                             'minItems': 4},
                                    'bedtools_executable': {'type': 'string', 'minLength': 1},
                                    'bedtools_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                    'bedtools_version': {'type': 'string', 'minLength': 1}},
                     'required': ['python_executable',
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
                                                                        'properties': {'version': {'type': 'string',
                                                                                                   'minLength': 1}},
                                                                        'required': ['version'],
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
        from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_job_validation import validate_genomic_overlap_bindings
        selected = validate_genomic_overlap_bindings(bindings)
        alternatives = [{"allOf": [root, {"properties": {"native_genomic_overlap": {
            "properties": {"software": {"const": row["software"]}}}}}]} for row in selected]
        root = {"anyOf": alternatives} if alternatives else {"not": {}}
    # The applicator gives each nested resource its own reference scope even
    # inside a sibling oneOf/anyOf. No remote schema resolution is needed.
    resource = {"$defs": deepcopy(_definitions()), **root}
    resource["$id"] = "urn:gene-annotation:genomic-overlap-execution:schema:" + _digest(resource)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "allOf": [resource]}


