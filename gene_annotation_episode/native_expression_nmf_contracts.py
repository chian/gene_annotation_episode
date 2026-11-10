"""Closed selected NMF job, software and original-attempt data contracts.

Pure validation here grants no filesystem/episode authority and starts no job.
"""
from copy import deepcopy
from pathlib import PurePosixPath
import os
import re

from jsonschema import Draft202012Validator

from .expression_nmf_common import (METADATA_SCHEMA, MODE, OPERATION, canonical, digest, require, validate_parameters)

RUN_PLAN_FILENAME = 'expression-nmf-plan.json'
ATTEMPT_DIRECTORY_NAME = 'expression-nmf-attempt'
OWNER_FILENAME = '.native-expression-nmf-owner.json'
STARTED_FILENAME = '.native-expression-nmf-started.json'
DRIVER_MODULE = 'gene_annotation_episode.native_expression_nmf_driver'
POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
ARTIFACT_NAMES = {'original_input': 'original-input.bin', 'input_data': 'input.json',
    'prepared_data': 'prepared.json', 'factors': 'factors.json', 'manifest': 'fit-manifest.json'}
ARTIFACT_FORMATS = {'original_input': 'expression_delimited_bytes_v1', 'input_data': 'expression_nmf_input_v1',
    'prepared_data': 'expression_nmf_prepared_v1', 'factors': 'expression_nmf_factors_v1',
    'manifest': 'expression_nmf_native_manifest_v1'}


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required,
        'additionalProperties': False}


TEXT = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000]+$'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
NULL = {'type': 'null'}
COUNT = {'type': 'integer', 'minimum': 0}
FILE_SCHEMA = obj({'path': TEXT, 'sha256': SHA, 'size_bytes': COUNT})
PARAMETERS_SCHEMA = obj({'rank': {'type': 'integer', 'minimum': 1},
    'random_state': {'type': 'integer', 'minimum': 0, 'maximum': 2**32-1},
    'normalization': {'enum': ['none', 'column_sum_1000']}, 'tol': {'type': 'number', 'minimum': 0},
    'max_iter': {'type': 'integer', 'minimum': 1}})
SOFTWARE_SCHEMA = obj({'version': {'const': 'expression_nmf_software_v1'}, 'python': FILE_SCHEMA,
    'python_version': TEXT, 'python_home': TEXT, 'module_root': TEXT,
    'implementation_files': {'type': 'array', 'minItems': 1, 'items': FILE_SCHEMA},
    'dependency_roots': {'type': 'array', 'minItems': 1, 'items': TEXT, 'uniqueItems': True},
    'distributions': {'type': 'array', 'minItems': 1, 'items': obj({'name': TEXT, 'version': TEXT,
        'requires': {'type': 'array', 'items': TEXT}})},
    'runtime_files': {'type': 'array', 'minItems': 1, 'items': FILE_SCHEMA}})
INPUT_SPEC_SCHEMA = obj({'path': TEXT, 'sha256': SHA, 'size_bytes': COUNT,
    'artifact_ref': {'anyOf': [TEXT, NULL]}, 'delimiter': {'enum': [',', '\t']},
    'metadata': METADATA_SCHEMA})
JOB_SCHEMA = obj({'version': {'const': 'native_expression_nmf_job_v1'}, 'operation': {'const': OPERATION},
    'mode': {'const': MODE}, 'input': INPUT_SPEC_SCHEMA, 'parameters': PARAMETERS_SCHEMA,
    'software': SOFTWARE_SCHEMA, 'output_prefix': TEXT})
ENV_SCHEMA = {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
    'additionalProperties': {'type': 'string', 'pattern': '^[^\\u0000]*$'}}
NATIVE_EXPRESSION_NMF_REQUESTED_JOB_SCHEMA = obj({'argv': {'type': 'array', 'minItems': 1, 'items': TEXT},
    'environment': ENV_SCHEMA, 'native_expression_nmf': JOB_SCHEMA})
BINDING_SCHEMA = obj({'operation': {'const': OPERATION}, 'mode': {'const': MODE}, 'software': SOFTWARE_SCHEMA})


def checked(value, schema):
    canonical(value)
    require(Draft202012Validator(schema).is_valid(value), 'invalid_expression_nmf_contract')
    return deepcopy(value)


def path_value(value, *, absolute):
    require(type(value) is str and value and not any(c in value for c in '\0\r\n\\'), 'invalid_nmf_path')
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and '..' not in path.parts
        and value not in ('.', '/') and not value.startswith('//'), 'invalid_nmf_path')
    return path


def validate_expression_nmf_software(value):
    value = checked(value, SOFTWARE_SCHEMA)
    for field in ('python_home', 'module_root'):
        path_value(value[field], absolute=True)
    roots = [path_value(p, absolute=True) for p in value['dependency_roots']]
    pins = [value['python'], *value['implementation_files'], *value['runtime_files']]
    for row in pins:
        path_value(row['path'], absolute=True)
        require(type(row['size_bytes']) is int, 'invalid_nmf_file_identity')
    paths = [row['path'] for row in pins]
    require(len(paths) == len(set(paths)), 'duplicate_nmf_runtime_file')
    modules = {str(PurePosixPath(value['module_root']) / 'gene_annotation_episode' / name)
        for name in ('__init__.py', 'expression_nmf_common.py', 'expression_nmf_inputs.py',
            'native_expression_nmf_contracts.py', 'native_expression_nmf_storage.py', 'native_expression_nmf_driver.py')}
    require(modules <= {r['path'] for r in value['implementation_files']}, 'nmf_implementation_closure_incomplete')
    names = [row['name'].lower().replace('_', '-') for row in value['distributions']]
    require(len(names) == len(set(names)) and {'scikit-learn', 'numpy', 'scipy', 'joblib', 'threadpoolctl',
        'jsonschema', 'attrs', 'referencing', 'rpds-py', 'jsonschema-specifications', 'typing-extensions'} <= set(names),
        'nmf_dependency_closure_incomplete')
    require(any(PurePosixPath(row['path']).is_relative_to(PurePosixPath(value['python_home']) / 'lib')
        for row in value['runtime_files']), 'nmf_standard_library_binding_missing')
    require(all(any(PurePosixPath(row['path']).is_relative_to(root) for row in value['runtime_files']) for root in roots),
        'nmf_dependency_root_unbound')
    return value


def validate_expression_nmf_bindings(value):
    result = checked(value, {'type': 'array', 'items': BINDING_SCHEMA})
    require(len({digest(row) for row in result}) == len(result), 'duplicate_nmf_binding')
    for row in result:
        validate_expression_nmf_software(row['software'])
    return result


def validate_expression_nmf_job(value):
    value = checked(value, JOB_SCHEMA)
    validate_expression_nmf_software(value['software'])
    validate_parameters(value['parameters'])
    path_value(value['input']['path'], absolute=True)
    prefix = path_value(value['output_prefix'], absolute=False)
    require(prefix.parts[0] not in (OWNER_FILENAME, STARTED_FILENAME, 'tmp', 'cache')
        and not prefix.parts[0].startswith('.'), 'invalid_nmf_output_prefix')
    require(type(value['input']['size_bytes']) is int, 'invalid_nmf_file_identity')
    return value


def expression_nmf_environment(software, *, attempt_directory):
    software = validate_expression_nmf_software(software)
    root = path_value(str(attempt_directory), absolute=True)
    return {'PYTHONPATH': os.pathsep.join([software['module_root'], *software['dependency_roots']]),
        'PYTHONHOME': software['python_home'], 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'PYTHONSAFEPATH': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
        'TMPDIR': str(root / 'tmp'), 'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'),
        'XDG_CACHE_HOME': str(root / 'cache'), 'PIP_CACHE_DIR': str(root / 'cache/pip')}


def requested_job_from_expression_nmf(job, *, environment):
    job = validate_expression_nmf_job(job)
    environment = checked(environment, ENV_SCHEMA)
    software = job['software']
    # Parent-selected paths are persisted; local preparation substitutes only
    # the documented original attempt's tmp/cache locations.
    expected = expression_nmf_environment(software, attempt_directory=str(PurePosixPath(environment.get('TMPDIR', '')) .parent))
    require(environment == expected, 'invalid_nmf_runtime_environment')
    return {'argv': [software['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME],
        'environment': environment, 'native_expression_nmf': job}


def validate_expression_nmf_requested_job(value):
    value = checked(value, NATIVE_EXPRESSION_NMF_REQUESTED_JOB_SCHEMA)
    require(value == requested_job_from_expression_nmf(value['native_expression_nmf'], environment=value['environment']),
        'nmf_requested_job_mismatch')
    return value


def expression_nmf_output_files(job):
    job = validate_expression_nmf_job(job)
    return [{'role': role, 'relative_path': job['output_prefix'] + '/' + name, 'format': ARTIFACT_FORMATS[role]}
        for role, name in ARTIFACT_NAMES.items()]


def validate_expression_nmf_run_plan(value):
    require(type(value) is dict and set(value) == {'version', 'identity', 'requested_job', 'attempt_directory', 'policy', 'outputs'},
        'invalid_nmf_run_plan')
    require(value['version'] == 'expression_nmf_run_plan_v1', 'invalid_nmf_run_plan')
    request = validate_expression_nmf_requested_job(value['requested_job'])
    owner = value['identity']
    require(type(owner) is dict and set(owner) == {'run_id', 'episode_id', 'resource_id', 'execution_id',
        'attempt_id', 'operation_key', 'requested_job_sha256', 'assignment_sha256'}, 'invalid_nmf_run_plan')
    require(all(type(v) is str and v and '\0' not in v for v in owner.values()), 'invalid_nmf_run_plan')
    execution = path_value(owner['execution_id'], absolute=True)
    attempt = path_value(value['attempt_directory'], absolute=True)
    from .terminal_scientific_evidence import terminal_plan_identity
    current = terminal_plan_identity(owner, attempt_directory=str(attempt))
    legacy = (execution.name == 'native.json'
        and owner['attempt_id'] == digest(owner['operation_key']) and owner['requested_job_sha256'] == digest(request)
        and execution.parent.name == owner['attempt_id'] and execution.parent.parent.name == digest({
            'run': owner['run_id'], 'episode': owner['episode_id']})
        and execution.parent.parent.parent.name == '.episode-operations')
    require((current or legacy) and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME
        and owner['attempt_id'] == digest(owner['operation_key']) and owner['requested_job_sha256'] == digest(request),
        'nmf_original_attempt_mismatch')
    require(canonical(value['policy']) == canonical(POLICY), 'nmf_original_allocation_mismatch')
    require(value['outputs'] == expression_nmf_output_files(request['native_expression_nmf']), 'nmf_output_role_mismatch')
    supplied = path_value(request['native_expression_nmf']['input']['path'], absolute=True)
    require(not supplied.is_relative_to(execution.parent) and not execution.parent.is_relative_to(supplied), 'nmf_input_output_overlap')
    return deepcopy(value)


def expression_nmf_driver_argv(plan):
    plan = validate_expression_nmf_run_plan(plan)
    return [*plan['requested_job']['argv'][:-1], str(PurePosixPath(plan['identity']['execution_id']).parent / RUN_PLAN_FILENAME)]
