"""A107 lumpy request contracts."""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import math
import os
from pathlib import PurePosixPath
from jsonschema import Draft202012Validator, validators
from gene_annotation_episode.episodic_workflow.root.a107.library import atac_execution_contracts as shared
OPERATION = 'detect_and_characterize_structural_variations'
MODE = 'lumpy_pe_sr_vcf'
DRIVER_MODULE = 'gene_annotation_episode.native_lumpy_execution'
RUN_PLAN_FILENAME = 'lumpy-plan.json'
REQUEST_VERSION = 'lumpy_request_v1'
PLAN_VERSION = 'lumpy_run_plan_v1'
SEAL_VERSION = 'lumpy_command_seal_v1'
POLICY = deepcopy(shared.POLICY)
require, canonical, digest = (shared.require, shared.canonical, shared.digest)
obj, arr, enum, nullable = (shared._obj, shared._arr, shared._enum, shared._null)
TEXT, ID, BOOL = (deepcopy(shared._TEXT), deepcopy(shared._ID), deepcopy(shared._BOOL))
FILE, PIN = (deepcopy(shared._FILE), deepcopy(shared._PIN))
INTEGER = {'type': 'integer', 'minimum': -2 ** 31, 'maximum': 2 ** 31 - 1}
NATIVE_TOKEN = {'type': 'string', 'minLength': 1, 'maxLength': 512, 'pattern': '^[^\\x00-\\x20\\x7f,:]+$'}
SONAME = {'type': 'string', 'minLength': 1, 'maxLength': 255, 'pattern': '^[A-Za-z0-9_+.-]+\\.so(?:\\.[A-Za-z0-9_+.-]+)*$'}
DECIMAL = {'type': 'string', 'minLength': 1, 'maxLength': 512, 'pattern': '^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?$'}
_COMMON = dict(signal_key={**ID, 'maxLength': 500}, output_sample_label=NATIVE_TOKEN, declared_sample_id=nullable(TEXT), reference_id=nullable(TEXT), bam=FILE, read_group=nullable(NATIVE_TOKEN))
PE = obj(kind={'const': 'paired_end'}, **_COMMON, histogram=FILE, parameters=obj(mean=DECIMAL, stdev=DECIMAL, read_length=INTEGER, min_non_overlap=INTEGER, discordant_z=INTEGER, back_distance=INTEGER, weight=INTEGER, min_mapping_threshold=INTEGER))
SR = obj(kind={'const': 'split_read'}, **_COMMON, parameters=obj(back_distance=INTEGER, min_non_overlap=INTEGER, weight=INTEGER, min_mapping_threshold=INTEGER, min_clip=INTEGER))
REQUEST = obj(version={'const': REQUEST_VERSION}, operation={'const': OPERATION}, mode={'const': MODE}, run_key=ID, signals=arr({'oneOf': [PE, SR]}, minItems=1), parameters=obj(minimum_sample_weight=INTEGER, trim_threshold=DECIMAL, probability_output=BOOL))
NATIVE_RUNTIME = obj(executable=PIN, loader=PIN, libraries=arr(obj(name=SONAME, file=PIN)), reported_version=nullable(TEXT))
SOFTWARE = obj(driver_runtime=shared.driver_runtime_schema(), native_runtime=NATIVE_RUNTIME)
JOB = obj(request=REQUEST, software=SOFTWARE, input_bindings=arr(obj(input_key=ID, file=FILE, path=TEXT), minItems=1))
REQUESTED = obj(argv=arr(TEXT, minItems=6, maxItems=6), environment=deepcopy(shared._ENV), native_lumpy=JOB)
SPEC = obj(file_key=ID, role=enum('vcf', 'stderr', 'bam_header', 'seal'), relative_path=TEXT, format=ID, required=BOOL)
PLAN = obj(version={'const': PLAN_VERSION}, identity=deepcopy(shared._IDENTITY), requested_job=REQUESTED, attempt_directory=TEXT, policy={'const': POLICY}, outputs=arr(SPEC, minItems=4))
INPUT_SEAL = obj(input_key=ID, signal_key=ID, role=enum('bam', 'histogram'), file=FILE, staging_state=enum('verified', 'failed', 'not_attempted'), staged=deepcopy(shared._DECL), staging_temporary=deepcopy(shared._DECL))
SEAL = obj(version={'const': SEAL_VERSION}, identity=deepcopy(shared._IDENTITY), producer_ref=ID, software_sha256=deepcopy(shared._SHA), argv=arr(TEXT), environment=deepcopy(shared._ENV), inputs=arr(INPUT_SEAL, minItems=1), input_inspections=arr(shared.atac_execution_schema('HeaderExtraction')), started_at=nullable(TEXT), finished_at=nullable(TEXT), returncode=nullable({'type': 'integer'}), outcome=enum('succeeded', 'failed', 'not_run'), outputs=arr(obj(specification=SPEC, declaration=deepcopy(shared._DECL)), minItems=3), failures=arr(shared.atac_execution_schema('Failure')))
SCHEMAS = {'Binding': obj(operation={'const': OPERATION}, mode={'const': MODE}, software=SOFTWARE), 'NativeRuntime': NATIVE_RUNTIME, 'SoftwareBinding': SOFTWARE, 'Request': REQUEST, 'NativeJob': JOB, 'RequestedJob': REQUESTED, 'RunPlan': PLAN, 'CommandSeal': SEAL}
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda checker, value: type(value) is int))
_REQUIRED_MODULES = (DRIVER_MODULE, 'gene_annotation_episode.native_atac_differential_reference')
_REQUIRED_DEPENDENCIES = ('jsonschema', 'attrs', 'referencing', 'rpds-py', 'jsonschema-specifications')

def _same(left, right):
    return canonical(left) == canonical(right)

def _record(kind, value):
    try:
        canonical(value)
        _STRICT(SCHEMAS[kind]).validate(value)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('invalid_lumpy_' + kind.lower()) from error
    except Exception as error:
        from jsonschema.exceptions import ValidationError
        if not isinstance(error, ValidationError):
            raise
        raise ValueError('invalid_lumpy_' + kind.lower()) from error
    return deepcopy(value)

def lumpy_execution_schema(kind, *, bindings=None):
    require(type(kind) is str and kind in SCHEMAS, 'unsupported_lumpy_execution_schema')
    schema = deepcopy(SCHEMAS[kind])
    if bindings is not None:
        require(kind == 'RequestedJob', 'unsupported_lumpy_execution_schema')
        choices = [{'properties': {'native_lumpy': {'properties': {'software': {'const': row['software']}, 'request': {'properties': {'operation': {'const': OPERATION}, 'mode': {'const': MODE}}}}}}} for row in validate_lumpy_bindings(bindings)]
        schema = {'allOf': [schema, {'anyOf': choices} if choices else {'not': {}}]}
    return schema

def _file(value):
    require(value['artifact_ref'] == 'artifact_' + value['sha256'] and type(value['size_bytes']) is int, 'artifact_digest_mismatch')

def _decimal(value, *, nonzero=False):
    try:
        number = Decimal(value)
        floating = float(value)
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise ValueError('invalid_lumpy_native_number') from error
    require(number.is_finite() and math.isfinite(floating) and (not nonzero or (number != 0 and floating != 0)) and (number == 0 or floating != 0), 'invalid_lumpy_native_number')

def _runtime(value):
    value = _record('NativeRuntime', value)
    for pin in [value['executable'], value['loader'], *(row['file'] for row in value['libraries'])]:
        shared.path_value(pin['path'], absolute=True)
    names = [row['name'] for row in value['libraries']]
    require(len(names) == len(set(names)), 'native_dependency_unavailable')
    root = PurePosixPath(value['executable']['path']).parent.parent
    require(root.name == 'native' and PurePosixPath(value['executable']['path']) == root / 'bin/lumpy' and (PurePosixPath(value['loader']['path']) == root / 'loader') and all((PurePosixPath(row['file']['path']) == root / 'lib' / row['name'] for row in value['libraries'])) and (':' not in str(root)), 'native_dependency_unavailable')
    return deepcopy(value)

def _software(value):
    result = _record('SoftwareBinding', value)
    shared.validate_driver_runtime(result['driver_runtime'], required_modules=_REQUIRED_MODULES, required_dependencies=_REQUIRED_DEPENDENCIES)
    _runtime(result['native_runtime'])
    return result

def validate_lumpy_bindings(values):
    require(type(values) is list, 'invalid_lumpy_bindings')
    result = [_record('Binding', row) for row in values]
    for row in result:
        _software(row['software'])
    require(len({digest(row) for row in result}) == len(result), 'invalid_lumpy_bindings')
    return result

def validate_lumpy_request(value):
    value = _record('Request', value)
    require(len({row['signal_key'] for row in value['signals']}) == len(value['signals']), 'lumpy_signal_key_conflict')
    require(value['parameters']['minimum_sample_weight'] != 0, 'invalid_lumpy_native_number')
    _decimal(value['parameters']['trim_threshold'])
    for signal in value['signals']:
        _file(signal['bam'])
        require(signal['bam']['format'] == 'bam', 'invalid_lumpy_bam_format')
        p = signal['parameters']
        required = ('read_length', 'min_non_overlap', 'discordant_z', 'back_distance', 'weight') if signal['kind'] == 'paired_end' else ('back_distance', 'weight')
        require(all((p[key] != 0 for key in required)), 'invalid_lumpy_native_number')
        if signal['kind'] == 'paired_end':
            _file(signal['histogram'])
            require(signal['histogram']['format'] == 'lumpy_insert_histogram', 'invalid_lumpy_histogram_format')
            _decimal(p['mean'], nonzero=True)
            _decimal(p['stdev'], nonzero=True)
    return value

def _input_occurrences(request):
    result = []
    for ordinal, signal in enumerate(request['signals']):
        for role in ('bam', 'histogram') if signal['kind'] == 'paired_end' else ('bam',):
            result.append(dict(input_key=signal['signal_key'] + ':' + role, signal_key=signal['signal_key'], role=role, file=deepcopy(signal[role]), relative_path=f'inputs/{ordinal:06d}.' + ('bam' if role == 'bam' else 'histo')))
    return result

def validate_lumpy_native_job(value):
    value = _record('NativeJob', value)
    request = validate_lumpy_request(value['request'])
    _software(value['software'])
    occurrences = _input_occurrences(request)
    require([row['input_key'] for row in value['input_bindings']] == [row['input_key'] for row in occurrences], 'lumpy_input_binding_conflict')
    paths = {}
    for binding, occurrence in zip(value['input_bindings'], occurrences):
        require(_same(binding['file'], occurrence['file']), 'lumpy_input_binding_conflict')
        path = shared.path_value(binding['path'], absolute=True)
        if path in paths:
            require(_same(paths[path], binding['file']), 'lumpy_input_binding_conflict')
        paths[path] = binding['file']
    return value

def requested_job_from_lumpy(job, *, environment):
    job = validate_lumpy_native_job(job)
    shared._environment(environment)
    driver = job['software']['driver_runtime']
    require(environment.get('PYTHONPATH') == os.pathsep.join([driver['module_root'], *shared._dependency_roots(driver)]), 'native_dependency_unavailable')
    return dict(argv=[driver['python_executable'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME], environment=deepcopy(environment), native_lumpy=job)

def validate_lumpy_requested_job(value):
    value = _record('RequestedJob', value)
    require(_same(value, requested_job_from_lumpy(value['native_lumpy'], environment=value['environment'])))
    return value
