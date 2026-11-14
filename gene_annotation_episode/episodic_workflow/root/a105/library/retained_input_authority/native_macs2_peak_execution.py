"""One selected MACS2 callpeak attempt on the existing local native lifecycle.

The caller owns received-File authority and PracticalState owns dispatch. This
module freezes that selected job, stages exact opaque input bytes and seals one
native command. Shared peak parsers and components retain numerical authority.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import os
import re
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority import native_atac_differential_contracts as shared
OPERATION = 'perform_chipseq_peak_calling_with_macs2'
MODE = 'macs2_2_2_9_1_auto_matched_control_native_model'
DRIVER_MODULE = 'gene_annotation_episode.native_macs2_peak_execution'
RUN_PLAN_FILENAME = 'macs2-peak-plan.json'
ATTEMPT_DIRECTORY_NAME = 'macs2-peak-attempt'
OWNER_FILENAME = '.native-macs2-peak-owner.json'
STARTED_FILENAME = '.native-macs2-peak-started.json'
SEAL_FILENAME = 'macs2-peak-seal.json'
POLICY = deepcopy(shared.POLICY)
REQUEST_VERSION = 'macs2_peak_request_v1'
PLAN_VERSION = 'macs2_peak_run_plan_v1'
SEAL_VERSION = 'macs2_peak_command_seal_v1'
require, canonical, digest = (shared.require, shared.canonical, shared.digest)
obj, arr, enum, nullable = (shared._obj, shared._arr, shared._enum, shared._null)
TEXT, ID, INT, BOOL = (shared._TEXT, shared._ID, shared._INT, shared._BOOL)
FILE = deepcopy(shared._FILE)
SOFTWARE = shared.atac_execution_schema('SoftwareBinding')
REFERENCE, SAMPLE = (deepcopy(shared._REFERENCE), deepcopy(shared._SAMPLE))
INPUT = obj(input_key=ID, role=enum('treatment', 'control'), sample_id=ID, reference_id=ID, file=FILE)
REQUEST = obj(version={'const': REQUEST_VERSION}, operation={'const': OPERATION}, mode={'const': MODE}, run_key=ID, condition_id=ID, reference=REFERENCE, samples=arr(SAMPLE, minItems=1, maxItems=2), inputs=arr(INPUT, minItems=2, maxItems=2), callpeak=obj(genome_size_argument=TEXT, qvalue_cutoff={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 1}), output_prefix=TEXT)
JOB = obj(request=REQUEST, software=SOFTWARE, input_bindings=arr(obj(input_key=ID, file=FILE, path=TEXT), minItems=2, maxItems=2))
REQUESTED = obj(argv=arr(TEXT, minItems=6, maxItems=6), environment=shared._ENV, native_macs2_peak=JOB)
SPEC = obj(file_key=ID, role=enum('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal'), relative_path=TEXT, format=ID, required=BOOL)
PLAN = obj(version={'const': PLAN_VERSION}, identity=deepcopy(shared._IDENTITY), requested_job=REQUESTED, attempt_directory=TEXT, policy={'const': POLICY}, outputs=arr(SPEC, minItems=7, maxItems=7))
SEAL = obj(version={'const': SEAL_VERSION}, identity=deepcopy(shared._IDENTITY), producer_ref=ID, argv=arr(TEXT), environment=shared._ENV, inputs=arr(obj(input_key=ID, role=enum('treatment', 'control'), file=FILE), minItems=2, maxItems=2), started_at=nullable(TEXT), finished_at=nullable(TEXT), returncode=nullable({'type': 'integer'}), outcome=enum('succeeded', 'failed', 'not_run'), outputs=arr(obj(specification=SPEC, declaration=deepcopy(shared._DECL)), minItems=6, maxItems=6), failures=arr(shared.atac_execution_schema('Failure')))
SCHEMAS = {'Binding': obj(operation={'const': OPERATION}, mode={'const': MODE}, software=SOFTWARE), 'SoftwareBinding': SOFTWARE, 'Request': REQUEST, 'NativeJob': JOB, 'RequestedJob': REQUESTED, 'RunPlan': PLAN, 'CommandSeal': SEAL}

def _same(left, right):
    return canonical(left) == canonical(right)

def _record(kind, value):
    try:
        canonical(value)
        Draft202012Validator(SCHEMAS[kind]).validate(value)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('invalid_macs2_peak_' + kind.lower()) from error
    except Exception as error:
        from jsonschema.exceptions import ValidationError
        if not isinstance(error, ValidationError):
            raise
        raise ValueError('invalid_macs2_peak_' + kind.lower()) from error
    return deepcopy(value)

def _software(value):
    result = shared.validate_atac_software(value)
    require(DRIVER_MODULE in {row['module'] for row in result['driver_runtime']['implementation_files']}, 'native_dependency_unavailable')
    return result

def _file(value):
    require(value['artifact_ref'] == 'artifact_' + value['sha256'] and type(value['size_bytes']) is int, 'artifact_digest_mismatch')

def validate_macs2_peak_request(value):
    value = _record('Request', value)
    shared.validate_atac_reference(value['reference'])
    for row in value['samples']:
        shared.validate_atac_sample(row)
    samples = {row['sample_id']: row for row in value['samples']}
    require(len(samples) == len(value['samples']) and set(samples) == {row['sample_id'] for row in value['inputs']}, 'condition_mapping')
    require([row['role'] for row in value['inputs']] == ['treatment', 'control'] and len({row['input_key'] for row in value['inputs']}) == 2, 'condition_mapping')
    for row in value['inputs']:
        _file(row['file'])
        sample = samples[row['sample_id']]
        require(row['reference_id'] == value['reference']['reference_id'] == sample['reference_id'] and row['file']['artifact_ref'] in sample['input_artifact_refs'], 'condition_mapping')
    argument = value['callpeak']['genome_size_argument']
    if argument not in ('hs', 'mm', 'ce', 'dm'):
        try:
            numeric = Decimal(argument)
        except InvalidOperation as error:
            raise ValueError('invalid_macs2_peak_genome_size') from error
        require(re.fullmatch('[+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?', argument) and numeric.is_finite() and (numeric > 0), 'invalid_macs2_peak_genome_size')
    prefix = shared.path_value(value['output_prefix'], absolute=False)
    require(len(prefix.parts) == 1 and (not prefix.name.startswith('-')) and (prefix.name not in (OWNER_FILENAME, STARTED_FILENAME, SEAL_FILENAME)), 'invalid_output_path')
    return value

def validate_macs2_peak_native_job(value):
    value = _record('NativeJob', value)
    request = validate_macs2_peak_request(value['request'])
    _software(value['software'])
    require([row['input_key'] for row in value['input_bindings']] == [row['input_key'] for row in request['inputs']])
    paths = {}
    for binding, selected in zip(value['input_bindings'], request['inputs']):
        require(_same(binding['file'], selected['file']))
        path = shared.path_value(binding['path'], absolute=True)
        if path in paths:
            require(_same(paths[path], binding['file']))
        paths[path] = binding['file']
    return value

def requested_job_from_macs2_peak(job, *, environment):
    job = validate_macs2_peak_native_job(job)
    shared._environment(environment)
    driver = job['software']['driver_runtime']
    require(environment.get('PYTHONPATH') == os.pathsep.join([driver['module_root'], *shared._dependency_roots(driver)]), 'native_dependency_unavailable')
    return dict(argv=[driver['python_executable'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME], environment=deepcopy(environment), native_macs2_peak=job)

def validate_macs2_peak_requested_job(value):
    value = _record('RequestedJob', value)
    require(_same(value, requested_job_from_macs2_peak(value['native_macs2_peak'], environment=value['environment'])))
    return value

def macs2_peak_output_files(request):
    request = validate_macs2_peak_request(request)
    prefix = request['output_prefix']
    entries = [('peaks_xls', 'native/' + prefix + '_peaks.xls', 'macs2_peaks_xls_narrow', True), ('narrowpeak', 'native/' + prefix + '_peaks.narrowPeak', 'macs2_narrowpeak10', True), ('summits', 'native/' + prefix + '_summits.bed', 'macs2_summits_bed5', True), ('model', 'native/' + prefix + '_model.r', 'macs2_model_r', False), ('stdout', 'native/stdout.log', 'native_stdout', True), ('stderr', 'native/stderr.log', 'native_stderr', True), ('seal', SEAL_FILENAME, SEAL_VERSION, True)]
    return [dict(file_key=role, role=role, relative_path=path, format=fmt, required=required) for role, path, fmt, required in entries]
