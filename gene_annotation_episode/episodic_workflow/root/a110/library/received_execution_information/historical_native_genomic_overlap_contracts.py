"""Pure records for the selected native all-pairs genomic overlap operation.

Fixed G2 definitions implement packet425 DATA_CONTRACT.json, SHA-256
4b8f38595549bd32484121129132474bc6fd3f5e9f7be1130433a6b3a208c00e.
G1 owns scientific records; these checks validate supplied execution facts and
associations, never observe files, grant source authority or execute work.
"""
from __future__ import annotations
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
from functools import lru_cache
import math
from pathlib import PurePosixPath
import re
from jsonschema import Draft202012Validator, FormatChecker, validators
from .historical_genomic_overlap_contracts import Request, genomic_overlap_schema, validate_genomic_overlap_record
RUN_PLAN_FILENAME = 'genomic-overlap-plan.json'
BATCH_FILENAME = 'bundle.json'
OWNER_FILENAME = '.native-genomic-overlap-owner.json'
STARTED_FILENAME = '.native-genomic-overlap-started.json'
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}
DRIVER_MODULE = 'gene_annotation_episode.native_genomic_overlap_driver'
_REQUIRED_MODULES = {DRIVER_MODULE, 'gene_annotation_episode.native_genomic_overlap_contracts', 'gene_annotation_episode.genomic_overlap_contracts', 'gene_annotation_episode.genomic_overlap_inputs'}
_EXECUTION_DEFINITIONS = {'Policy': {'type': 'object', 'properties': {'memory_bytes': {'const': ENVIRONMENT_BOUNDS['memory_bytes']}, 'scratch_bytes': {'const': 4294967296}}, 'required': ['memory_bytes', 'scratch_bytes'], 'additionalProperties': False}, 'ImplementationFile': {'type': 'object', 'properties': {'module': {'type': 'string', 'minLength': 1}}, 'required': ['module'], 'additionalProperties': False}, 'SoftwareBinding': {'type': 'object', 'properties': {'python_executable': {'type': 'string', 'minLength': 1}, 'python_version': {'type': 'string', 'minLength': 1}, 'module_root': {'type': 'string', 'minLength': 1}, 'driver_module': {'const': 'gene_annotation_episode.native_genomic_overlap_driver'}, 'implementation_files': {'type': 'array', 'items': {'$ref': '#/$defs/ImplementationFile'}, 'minItems': 4}, 'bedtools_executable': {'type': 'string', 'minLength': 1}, 'bedtools_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'bedtools_version': {'type': 'string', 'minLength': 1}}, 'required': ['python_executable', 'python_version', 'module_root', 'driver_module', 'implementation_files', 'bedtools_executable', 'bedtools_sha256', 'bedtools_version'], 'additionalProperties': False}, 'Binding': {'type': 'object', 'properties': {'operation': {'const': 'analyze_genomic_region_overlap'}, 'mode': {'const': 'unstranded_outer_span'}, 'software': {'$ref': '#/$defs/SoftwareBinding'}}, 'required': ['operation', 'mode', 'software'], 'additionalProperties': False}, 'InputBinding': {'type': 'object', 'properties': {'set_key': {'type': 'string', 'minLength': 1}, 'path': {'type': 'string', 'minLength': 1}}, 'required': ['set_key', 'path'], 'additionalProperties': False}, 'OutputSpec': {'type': 'object', 'properties': {'file_key': {'type': 'string', 'minLength': 1}, 'role': {'enum': ['stdout', 'stderr', 'version_stdout', 'version_stderr', 'original_input', 'rejected_input', 'parsed_set', 'canonical_set', 'pair_manifest', 'overlap_stdout', 'overlap_stderr', 'batch_manifest']}, 'set_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'comparison_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'relative_path': {'type': 'string', 'minLength': 1}, 'format': {'type': 'string', 'minLength': 1}}, 'required': ['file_key', 'role', 'set_key', 'comparison_key', 'relative_path', 'format'], 'additionalProperties': False}, 'NativeJob': {'type': 'object', 'properties': {'version': {'const': 'native_genomic_overlap_job_v1'}, 'program': {'const': 'bedtools_intersect_all_pairs'}, 'request': {'$ref': '#/$defs/Request'}, 'software': {'$ref': '#/$defs/SoftwareBinding'}, 'inputs': {'type': 'array', 'items': {'$ref': '#/$defs/InputBinding'}, 'minItems': 2}, 'outputs': {'type': 'array', 'items': {'$ref': '#/$defs/OutputSpec'}, 'minItems': 16}, 'environment': {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'}, 'additionalProperties': {'type': 'string'}}}, 'required': ['version', 'program', 'request', 'software', 'inputs', 'outputs', 'environment'], 'additionalProperties': False}, 'RequestedJob': {'type': 'object', 'properties': {'argv': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 5}, 'environment': {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'}, 'additionalProperties': {'type': 'string'}}, 'native_genomic_overlap': {'$ref': '#/$defs/NativeJob'}}, 'required': ['argv', 'environment', 'native_genomic_overlap'], 'additionalProperties': False}, 'AttemptIdentity': {'type': 'object', 'properties': {'run_id': {'type': 'string', 'minLength': 1}, 'episode_id': {'type': 'string', 'minLength': 1}, 'resource_id': {'type': 'string', 'minLength': 1}, 'execution_id': {'type': 'string', 'minLength': 1}, 'operation_key': {'type': 'string', 'minLength': 1}, 'attempt_id': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'requested_job_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'assignment_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}, 'required': ['run_id', 'episode_id', 'resource_id', 'execution_id', 'operation_key', 'attempt_id', 'requested_job_sha256', 'assignment_sha256'], 'additionalProperties': False}, 'RunPlan': {'type': 'object', 'properties': {'version': {'const': 'native_genomic_overlap_run_plan_v1'}, 'identity': {'$ref': '#/$defs/AttemptIdentity'}, 'requested_job': {'$ref': '#/$defs/RequestedJob'}, 'attempt_directory': {'type': 'string', 'minLength': 1}, 'policy': {'$ref': '#/$defs/Policy'}}, 'required': ['version', 'identity', 'requested_job', 'attempt_directory', 'policy'], 'additionalProperties': False}, 'DriverFailure': {'type': 'object', 'properties': {'code': {'enum': ['input_unavailable', 'input_digest_mismatch', 'invalid_input', 'native_dependency_unavailable', 'native_version_unverified', 'software_identity_mismatch', 'native_spawn_failed', 'native_nonzero_exit', 'resource_limit', 'output_unavailable', 'seal_failed']}, 'stage': {'enum': ['input', 'software', 'native', 'seal']}, 'set_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'comparison_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'file_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'field_path': {'anyOf': [{'type': 'string', 'pattern': '^/'}, {'type': 'null'}]}, 'expected_value': {'$ref': '#/$defs/JsonValue'}, 'observed_value': {'$ref': '#/$defs/JsonValue'}}, 'required': ['code', 'stage', 'set_key', 'comparison_key', 'file_key', 'field_path', 'expected_value', 'observed_value'], 'additionalProperties': False}, 'BatchFile': {'type': 'object', 'properties': {'specification': {'$ref': '#/$defs/OutputSpec'}, 'declaration': {'$ref': '#/$defs/NativeFileDeclaration'}}, 'required': ['specification', 'declaration'], 'additionalProperties': False}, 'SetOutput': {'type': 'object', 'properties': {'set_key': {'type': 'string', 'minLength': 1}, 'set_position': {'type': 'integer', 'minimum': 0}, 'input_state': {'enum': ['verified', 'unavailable', 'digest_mismatch']}, 'measured_fingerprint': {'anyOf': [{'$ref': '#/$defs/NativeSourceFingerprint'}, {'type': 'null'}]}, 'parse_extent': {'anyOf': [{'enum': ['complete', 'partial', 'unavailable']}, {'type': 'null'}]}, 'original_file_key': {'type': 'string', 'minLength': 1}, 'rejected_file_key': {'type': 'string', 'minLength': 1}, 'parsed_file_key': {'type': 'string', 'minLength': 1}, 'canonical_file_key': {'type': 'string', 'minLength': 1}, 'failure_indices': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}, 'uniqueItems': True}}, 'required': ['set_key', 'set_position', 'input_state', 'measured_fingerprint', 'parse_extent', 'original_file_key', 'rejected_file_key', 'parsed_file_key', 'canonical_file_key', 'failure_indices'], 'additionalProperties': False}, 'PairOutput': {'type': 'object', 'properties': {'comparison': {'$ref': '#/$defs/ComparisonSpec'}, 'disposition': {'enum': ['native_succeeded', 'native_failed', 'analytic_empty', 'invalid_input', 'input_unavailable', 'native_unavailable']}, 'manifest_file_key': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'null'}]}, 'manifest': {'anyOf': [{'$ref': '#/$defs/NativeDriverManifest'}, {'type': 'null'}]}, 'failure_indices': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}, 'uniqueItems': True}}, 'required': ['comparison', 'disposition', 'manifest_file_key', 'manifest', 'failure_indices'], 'additionalProperties': False}, 'VersionProbe': {'type': 'object', 'properties': {'realized_argv': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 2}, 'environment': {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'}, 'additionalProperties': {'type': 'string'}}, 'returncode': {'type': 'integer'}, 'started_at': {'type': 'string', 'format': 'date-time'}, 'finished_at': {'type': 'string', 'format': 'date-time'}, 'writer_closed': {'const': True}, 'stdout_file_key': {'const': 'version_stdout'}, 'stderr_file_key': {'const': 'version_stderr'}}, 'required': ['realized_argv', 'environment', 'returncode', 'started_at', 'finished_at', 'writer_closed', 'stdout_file_key', 'stderr_file_key'], 'additionalProperties': False}, 'SoftwareVerification': {'type': 'object', 'properties': {'state': {'enum': ['verified', 'not_needed', 'failed']}, 'python_observed': {'anyOf': [{'type': 'object', 'properties': {'version': {'type': 'string', 'minLength': 1}}, 'required': ['version'], 'additionalProperties': False}, {'type': 'null'}]}, 'bedtools_observed': {'anyOf': [{'$ref': '#/$defs/Software'}, {'type': 'null'}]}, 'version_probe': {'anyOf': [{'$ref': '#/$defs/VersionProbe'}, {'type': 'null'}]}, 'failure_indices': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}, 'uniqueItems': True}}, 'required': ['state', 'python_observed', 'bedtools_observed', 'version_probe', 'failure_indices'], 'additionalProperties': False}, 'BatchManifest': {'type': 'object', 'properties': {'version': {'const': 'genomic_overlap_native_batch_v1'}, 'identity': {'$ref': '#/$defs/NativeIdentity'}, 'plan_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'requested_job_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'policy': {'$ref': '#/$defs/Policy'}, 'driver_argv': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 5}, 'realized_environment': {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'}, 'additionalProperties': {'type': 'string'}}, 'requested_set_keys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 2, 'uniqueItems': True}, 'requested_comparisons': {'type': 'array', 'items': {'$ref': '#/$defs/ComparisonSpec'}, 'minItems': 1}, 'software_verification': {'$ref': '#/$defs/SoftwareVerification'}, 'sets': {'type': 'array', 'items': {'$ref': '#/$defs/SetOutput'}, 'minItems': 2}, 'pairs': {'type': 'array', 'items': {'$ref': '#/$defs/PairOutput'}, 'minItems': 1}, 'files': {'type': 'array', 'items': {'$ref': '#/$defs/BatchFile'}, 'minItems': 15}, 'failures': {'type': 'array', 'items': {'$ref': '#/$defs/DriverFailure'}}, 'batch_status': {'enum': ['complete', 'partial', 'failed']}, 'started_at': {'type': 'string', 'format': 'date-time'}, 'finished_at': {'type': 'string', 'format': 'date-time'}, 'sealed': {'const': True}}, 'required': ['version', 'identity', 'plan_sha256', 'requested_job_sha256', 'policy', 'driver_argv', 'realized_environment', 'requested_set_keys', 'requested_comparisons', 'software_verification', 'sets', 'pairs', 'files', 'failures', 'batch_status', 'started_at', 'finished_at', 'sealed'], 'additionalProperties': False}}

def _require(condition, code='genomic_overlap_invalid_execution_record'):
    if not condition:
        raise ValueError(code)

def _plain(value):
    """Reject Python coercions before JSON Schema sees the supplied object."""
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        try:
            value.encode('utf-8')
        except UnicodeEncodeError as error:
            raise ValueError('genomic_overlap_invalid_execution_record') from error
        return
    if type(value) is float:
        _require(math.isfinite(value))
        return
    if type(value) is list:
        for row in value:
            _plain(row)
        return
    _require(type(value) is dict and all((type(key) is str for key in value)))
    for key, row in value.items():
        _plain(key)
        _plain(row)

def _references(value):
    if type(value) is dict:
        if '$ref' in value:
            yield value['$ref'].removeprefix('#/$defs/')
        for item in value.values():
            yield from _references(item)
    elif type(value) is list:
        for item in value:
            yield from _references(item)

@lru_cache(maxsize=1)
def _definitions():
    science = genomic_overlap_schema('Request')['$defs']
    result = deepcopy(_EXECUTION_DEFINITIONS)
    pending = set(_references(result)) - result.keys()
    while pending:
        name = pending.pop()
        result[name] = science[name]
        pending.update(set(_references(result[name])) - result.keys())
    return result
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda _, v: type(v) is int).redefine('number', lambda _, v: type(v) in (int, float)))

@lru_cache(maxsize=len(_EXECUTION_DEFINITIONS))
def _validator(name):
    return _STRICT({'$defs': _definitions(), '$ref': '#/$defs/' + name}, format_checker=FormatChecker())

def _checked(value, name):
    _plain(value)
    _require(_validator(name).is_valid(value))
    return deepcopy(value)

def _path(value, *, absolute):
    _require(type(value) is str and value and (not any((c in value for c in '\x00\r\n\\'))), 'genomic_overlap_invalid_path')
    path = PurePosixPath(value)
    _require(path.is_absolute() == absolute and str(path) == value and ('..' not in path.parts) and (value not in ('.', '/')) and (not value.startswith('//')), 'genomic_overlap_invalid_path')
    return path

def _overlap(left, right):
    return left == right or left in right.parents or right in left.parents

def _software(value):
    value = _checked(value, 'SoftwareBinding')
    for field in ('python_executable', 'module_root', 'bedtools_executable'):
        _path(value[field], absolute=True)
    modules = [row['module'] for row in value['implementation_files']]
    _require(len(modules) == len(set(modules)) and _REQUIRED_MODULES <= set(modules), 'genomic_overlap_software_binding')
    _require(all((name.startswith('gene_annotation_episode.') and re.fullmatch('[A-Za-z_]\\w*(?:\\.[A-Za-z_]\\w*)+', name, re.ASCII) for name in modules)), 'genomic_overlap_software_binding')
    for field in ('python_version', 'bedtools_version'):
        _require(not any((c in value[field] for c in '\x00\r\n')), 'genomic_overlap_software_binding')
    return value

def _request(value):
    value = validate_genomic_overlap_record('Request', value)
    specs, comparisons = (value['region_sets'], value['comparisons'])
    keys = [spec['set_key'] for spec in specs]
    _require(len(keys) == len(set(keys)), 'genomic_overlap_duplicate_set_key')
    endpoints = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]]
    _require(len(comparisons) == len(endpoints) and len({p['comparison_key'] for p in comparisons}) == len(comparisons), 'genomic_overlap_comparison_population')
    for i, (pair, ends) in enumerate(zip(comparisons, endpoints)):
        _require(pair['ordinal'] == i and (pair['a_set_key'], pair['b_set_key']) == ends, 'genomic_overlap_comparison_order')
    artifacts = {}
    for spec in specs:
        source = spec['source']
        kind = 'bed_artifact' if spec['format'] == 'bed_outer_span_v1' else 'coordinate_rows_artifact'
        _require(source['kind'] == kind and source['file']['format'] == spec['format'], 'genomic_overlap_input_format_binding')
        identity = source['file']
        prior = artifacts.setdefault(identity['artifact_ref'], identity)
        _require(prior == identity, 'genomic_overlap_input_identity_mismatch')
    return value

def genomic_overlap_output_files(request: Request) -> list[dict]:
    request = _request(request)
    prefix = request['output_prefix']
    rows = []

    def add(key, role, path, format_name, set_key=None, comparison_key=None):
        rows.append({'file_key': key, 'role': role, 'set_key': set_key, 'comparison_key': comparison_key, 'relative_path': path, 'format': format_name})
    add('stdout', 'stdout', 'stdout.log', 'genomic_overlap_driver_log_v1')
    add('stderr', 'stderr', 'stderr.log', 'native_stderr_text_v1')
    add('version_stdout', 'version_stdout', prefix + '/software/version.stdout.txt', 'native_stdout_text_v1')
    add('version_stderr', 'version_stderr', prefix + '/software/version.stderr.txt', 'native_stderr_text_v1')
    for i, spec in enumerate(request['region_sets']):
        stem = 's' + str(i)
        root = prefix + '/sets/' + stem + '/'
        for suffix, role, filename, format_name in (('original', 'original_input', 'original.data', spec['format']), ('rejected', 'rejected_input', 'rejected-source.data', spec['format']), ('parsed', 'parsed_set', 'parsed-set.json', 'genomic_overlap_parsed_set_v1'), ('canonical', 'canonical_set', 'canonical.bed', 'bed4_occurrence_v1')):
            add(stem + ':' + suffix, role, root + filename, format_name, set_key=spec['set_key'])
    for pair in request['comparisons']:
        stem = 'p' + str(pair['ordinal'])
        root = prefix + '/pairs/' + stem + '/'
        for suffix, role, filename, format_name in (('manifest', 'pair_manifest', 'manifest.json', 'genomic_overlap_native_manifest_v1'), ('stdout', 'overlap_stdout', 'overlap.wo.tsv', 'bedtools_intersect_wo_bed4_v1'), ('stderr', 'overlap_stderr', 'stderr.txt', 'native_stderr_text_v1')):
            add(stem + ':' + suffix, role, root + filename, format_name, comparison_key=pair['comparison_key'])
    add('batch_manifest', 'batch_manifest', BATCH_FILENAME, 'genomic_overlap_native_batch_v1')
    reserved = [PurePosixPath(name) for name in (RUN_PLAN_FILENAME, OWNER_FILENAME, STARTED_FILENAME, 'tmp', 'cache', 'native.json', 'invoke.json', 'request.json', 'ready.json', 'release.json', 'status.json', 'result.json', 'launcher.json')]
    paths = [_path(row['relative_path'], absolute=False) for row in rows]
    for i, path in enumerate(paths):
        _require(not any((_overlap(path, other) for other in reserved + paths[:i])), 'genomic_overlap_invalid_path')
    return rows

def _environment(value):
    forbidden = {'HOME', 'TMP', 'TEMP', 'TMPDIR', 'PYTHONHOME', 'PYTHONUSERBASE', 'PYTHONPYCACHEPREFIX', 'PYTHONPATH', 'XDG_CACHE_HOME', 'PIP_CACHE_DIR'}
    _require(value.get('LC_ALL') == 'C' and value.get('PYTHONDONTWRITEBYTECODE', '1') == '1', 'genomic_overlap_invalid_environment')
    _require(not any((key in forbidden or 'CACHE' in key.upper() for key in value)), 'genomic_overlap_invalid_environment')
    _require(all(('\x00' not in text for text in value.values())), 'genomic_overlap_invalid_environment')

def validate_genomic_overlap_job(value: dict) -> dict:
    value = _checked(value, 'NativeJob')
    request = _request(value['request'])
    _software(value['software'])
    _environment(value['environment'])
    specs, inputs = (request['region_sets'], value['inputs'])
    _require([row['set_key'] for row in inputs] == [row['set_key'] for row in specs], 'genomic_overlap_input_identity_mismatch')
    paths = [_path(row['path'], absolute=True) for row in inputs]
    for i, path in enumerate(paths):
        for j, prior in enumerate(paths[:i]):
            _require(not _overlap(path, prior) or (path == prior and specs[i]['source']['file'] == specs[j]['source']['file']), 'genomic_overlap_input_identity_mismatch')
    _require(value['outputs'] == genomic_overlap_output_files(request), 'genomic_overlap_output_binding')
    return value

def compile_genomic_overlap_job(job: dict, *, plan_path: str=RUN_PLAN_FILENAME) -> dict:
    job = validate_genomic_overlap_job(job)
    if plan_path != RUN_PLAN_FILENAME:
        _require(_path(plan_path, absolute=True).name == RUN_PLAN_FILENAME, 'genomic_overlap_invalid_path')
    return {'argv': [job['software']['python_executable'], '-B', '-m', DRIVER_MODULE, plan_path], 'environment': deepcopy(job['environment']), 'outputs': deepcopy(job['outputs'])}

def requested_job_from_genomic_overlap(job: dict) -> dict:
    job = validate_genomic_overlap_job(job)
    compiled = compile_genomic_overlap_job(job)
    return {'argv': compiled['argv'], 'environment': compiled['environment'], 'native_genomic_overlap': job}

def validate_genomic_overlap_requested_job(value: dict) -> dict:
    value = _checked(value, 'RequestedJob')
    _require(value == requested_job_from_genomic_overlap(value['native_genomic_overlap']), 'original_attempt_mismatch')
    return value

import hashlib
import json
ATTEMPT_DIRECTORY_NAME = 'genomic-overlap-attempt'

def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def genomic_overlap_execution_schema(record_name: str, *, bindings: list[dict] | None=None) -> dict:
    """Return a detached fixed record schema, nestable in commission schemas."""
    _require(type(record_name) is str and record_name in _EXECUTION_DEFINITIONS, 'genomic_overlap_unknown_execution_record')
    root = {'$ref': '#/$defs/' + record_name}
    if bindings is not None:
        _require(record_name == 'RequestedJob', 'genomic_overlap_binding_mismatch')
        selected = validate_genomic_overlap_bindings(bindings)
        alternatives = [{'allOf': [root, {'properties': {'native_genomic_overlap': {'properties': {'software': {'const': row['software']}}}}}]} for row in selected]
        root = {'anyOf': alternatives} if alternatives else {'not': {}}
    resource = {'$defs': deepcopy(_definitions()), **root}
    resource['$id'] = 'urn:gene-annotation:genomic-overlap-execution:schema:' + _digest(resource)
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'allOf': [resource]}

def validate_genomic_overlap_bindings(value: list[dict]) -> list[dict]:
    """Validate explicit deployments; an empty list exposes no operation."""
    _require(type(value) is list, 'genomic_overlap_binding_mismatch')
    rows = [_checked(row, 'Binding') for row in value]
    for row in rows:
        _software(row['software'])
    _require(len({_digest(row) for row in rows}) == len(rows), 'genomic_overlap_duplicate_binding')
    return rows

def validate_genomic_overlap_run_plan(value: dict) -> dict:
    value = _checked(value, 'RunPlan')
    request = validate_genomic_overlap_requested_job(value['requested_job'])
    identity = value['identity']
    execution = _path(identity['execution_id'], absolute=True)
    attempt = _path(value['attempt_directory'], absolute=True)
    from gene_annotation_episode.episodic_workflow.root.a110.terminal_scientific_evidence import terminal_plan_identity
    current = terminal_plan_identity(identity, attempt_directory=str(attempt))
    _require((current or execution.name == 'native.json') and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME, 'original_attempt_mismatch')
    _require(identity['attempt_id'] == _digest(identity['operation_key']) and identity['requested_job_sha256'] == _digest(request), 'original_attempt_mismatch')
    _require(current or (execution.parent.name == identity['attempt_id'] and execution.parent.parent.name == _digest({'run': identity['run_id'], 'episode': identity['episode_id']}) and (execution.parent.parent.parent.name == '.episode-operations')), 'original_attempt_mismatch')
    _require(type(value['policy']['memory_bytes']) is int and type(value['policy']['scratch_bytes']) is int and (value['policy'] == POLICY), 'genomic_overlap_policy_mismatch')
    for row in request['native_genomic_overlap']['inputs']:
        _require(not _overlap(_path(row['path'], absolute=True), execution.parent), 'genomic_overlap_invalid_path')
    return value

def genomic_overlap_driver_argv(plan: dict) -> list[str]:
    plan = validate_genomic_overlap_run_plan(plan)
    return compile_genomic_overlap_job(plan['requested_job']['native_genomic_overlap'], plan_path=str(PurePosixPath(plan['identity']['execution_id']).parent / RUN_PLAN_FILENAME))['argv']

def genomic_overlap_environment(job: dict, *, attempt_directory: str) -> dict:
    job = validate_genomic_overlap_job(job)
    root = _path(attempt_directory, absolute=True)
    return {**job['environment'], 'PYTHONPATH': job['software']['module_root'], 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'), 'TMPDIR': str(root / 'tmp'), 'XDG_CACHE_HOME': str(root / 'cache'), 'PIP_CACHE_DIR': str(root / 'cache/pip')}
