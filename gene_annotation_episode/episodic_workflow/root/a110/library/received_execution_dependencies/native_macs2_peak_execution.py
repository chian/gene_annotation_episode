from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
from jsonschema import Draft202012Validator
import gene_annotation_episode.episodic_workflow.root.a110.native_lifecycle as native
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_contracts as shared
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_driver import decode_json
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

def macs2_peak_execution_schema(kind, *, bindings=None):
    require(type(kind) is str and kind in SCHEMAS, 'unsupported_macs2_peak_execution_schema')
    schema = deepcopy(SCHEMAS[kind])
    if bindings is not None:
        require(kind == 'RequestedJob', 'unsupported_macs2_peak_execution_schema')
        choices = [{'properties': {'native_macs2_peak': {'properties': {'software': {'const': row['software']}, 'request': {'properties': {'operation': {'const': OPERATION}, 'mode': {'const': MODE}}}}}}} for row in validate_macs2_peak_bindings(bindings)]
        schema = {'allOf': [schema, {'anyOf': choices} if choices else {'not': {}}]}
    return schema

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

def validate_macs2_peak_bindings(values):
    require(type(values) is list)
    result = [_record('Binding', row) for row in values]
    for row in result:
        _software(row['software'])
    require(len({digest(row) for row in result}) == len(result))
    return result

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

def _root(assignment, identity):
    return Path(shared.path_value(assignment['workspace'], absolute=True)) / '.episode-operations' / digest({'run': identity['run_id'], 'episode': identity['episode_id']}) / digest(identity['operation_key'])

def _allocation(assignment, policy):
    require(assignment.get('resource_kind') == 'local' and _same(policy, POLICY) and (type(assignment.get('resource_id')) is str) and bool(assignment['resource_id']))
    constraints = assignment.get('constraints')
    require(type(constraints) is dict and (not set(constraints) - {'allocation', 'memory_bytes', 'scratch_bytes'}))
    require('allocation' not in constraints or _same(constraints['allocation'], policy))
    require(all((key not in constraints or _same(constraints[key], value) for key, value in policy.items())))

def validate_macs2_peak_run_plan(value):
    value = _record('RunPlan', value)
    requested = validate_macs2_peak_requested_job(value['requested_job'])
    identity = value['identity']
    execution = shared.path_value(identity['execution_id'], absolute=True)
    attempt = shared.path_value(value['attempt_directory'], absolute=True)
    require(execution.name == 'native.json' and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME)
    require(identity['attempt_id'] == digest(identity['operation_key']) and identity['requested_job_sha256'] == digest(requested))
    expected = macs2_peak_output_files(requested['native_macs2_peak']['request'])
    require(_same(value['outputs'], expected))
    for row in value['outputs']:
        shared.path_value(row['relative_path'], absolute=False)
    return value

def macs2_peak_plan(assignment, identity, *, policy):
    """Rebuild only the original selected plan from retained typed metadata."""
    requested = validate_macs2_peak_requested_job(assignment['requested_job'])
    _allocation(assignment, policy)
    value = validate_macs2_peak_run_plan(dict(version=PLAN_VERSION, identity=deepcopy(identity), requested_job=requested, attempt_directory=str(PurePosixPath(identity['execution_id']).parent / ATTEMPT_DIRECTORY_NAME), policy=deepcopy(policy), outputs=macs2_peak_output_files(requested['native_macs2_peak']['request'])))
    require(identity['assignment_sha256'] == digest(assignment) and identity['resource_id'] == assignment['resource_id'] and (Path(identity['execution_id']).parent == _root(assignment, identity)))
    return value

def macs2_peak_driver_argv(plan):
    plan = validate_macs2_peak_run_plan(plan)
    return [*plan['requested_job']['argv'][:-1], str(PurePosixPath(plan['identity']['execution_id']).parent / RUN_PLAN_FILENAME)]

def _driver_environment(plan):
    job = plan['requested_job']['native_macs2_peak']
    root = PurePosixPath(plan['attempt_directory'])
    driver = job['software']['driver_runtime']
    return {**plan['requested_job']['environment'], 'PYTHONPATH': os.pathsep.join([driver['module_root'], *shared._dependency_roots(driver)]), 'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'), 'TMPDIR': str(root / 'tmp'), 'XDG_CACHE_HOME': str(root / 'cache'), 'PIP_CACHE_DIR': str(root / 'cache/pip')}

def _native_environment(plan):
    root = PurePosixPath(plan['attempt_directory'])
    runtime = plan['requested_job']['native_macs2_peak']['software']['macs2_runtime']
    return dict(PATH='/usr/bin:/bin', LC_ALL='C.UTF-8', PYTHONPATH=os.pathsep.join(runtime['import_roots']), PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'), TMPDIR=str(root / 'tmp'), XDG_CACHE_HOME=str(root / 'cache'), PIP_CACHE_DIR=str(root / 'cache/pip'))

def macs2_peak_command_argv(plan):
    plan = validate_macs2_peak_run_plan(plan)
    job = plan['requested_job']['native_macs2_peak']
    request, runtime = (job['request'], job['software']['macs2_runtime'])
    root = PurePosixPath(plan['attempt_directory'])
    return [runtime['python_executable'], '-B', '-S', runtime['macs2_script'], 'callpeak', '-t', str(root / 'inputs/treatment.input'), '-c', str(root / 'inputs/control.input'), '-n', request['output_prefix'], '-g', request['callpeak']['genome_size_argument'], '-q', str(request['callpeak']['qvalue_cutoff']), '--outdir', str(root / 'native'), '--tempdir', str(root / 'tmp')]

def _job_request(plan, paths):
    return dict(command=macs2_peak_driver_argv(plan), cwd=str(Path(plan['identity']['execution_id']).parent), file_bytes=POLICY['scratch_bytes'], ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None, env=_driver_environment(plan))

def validate_macs2_peak_original_controls(plan, original, request_raw):
    """Authenticate retained original control bytes without reopening paths."""
    plan = validate_macs2_peak_run_plan(plan)
    root = Path(plan['identity']['execution_id']).parent
    require(type(original) is dict and type(original.get('metadata')) is dict)
    require(original.get('version') == native.VERSION and original.get('stage') in {'prepared', 'submitting', 'released'} and _same(original.get('command'), macs2_peak_driver_argv(plan)) and (original.get('cwd') == str(root)) and _same(original['metadata'].get('policy'), plan['policy']))
    paths = original.get('paths')
    required = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    require(type(paths) is dict and required <= paths.keys() and (not paths.keys() - required - {'statistics', 'native_events'}))
    require(all((type(path) is str and shared.path_value(path, absolute=True).parent == PurePosixPath(root) for path in paths.values())) and len(set(paths.values())) == len(paths))
    fixed = {str(root / name) for name in ('native.json', 'invoke.json', RUN_PLAN_FILENAME, 'stdout.log', 'stderr.log')}
    require(not fixed.intersection(paths.values()))
    for role in ('statistics', 'native_events'):
        require((role in paths) == (role in original))
    for role in ('stdout', 'stderr'):
        require(original.get(role) == str(root / (role + '.log')))
    require(type(request_raw) in (bytes, str))
    raw = request_raw.encode('utf-8') if type(request_raw) is str else request_raw
    require(hashlib.sha256(raw).hexdigest() == original.get('request_sha256') and _same(decode_json(raw), _job_request(plan, paths)))
    return plan

def _producer_ref(plan):
    return 'macs2_peak_producer_' + digest({'identity': plan['identity'], 'command': 'callpeak'})

def validate_macs2_peak_seal(value, *, plan):
    plan = validate_macs2_peak_run_plan(plan)
    value = _record('CommandSeal', value)
    require(_same(value['identity'], plan['identity']) and value['producer_ref'] == _producer_ref(plan) and _same(value['argv'], macs2_peak_command_argv(plan)) and _same(value['environment'], _native_environment(plan)))
    request = plan['requested_job']['native_macs2_peak']['request']
    expected_inputs = [{key: row[key] for key in ('input_key', 'role', 'file')} for row in request['inputs']]
    require(_same(value['inputs'], expected_inputs))
    expected_outputs = [row for row in plan['outputs'] if row['role'] != 'seal']
    require(_same([row['specification'] for row in value['outputs']], expected_outputs))
    for row in value['outputs']:
        declaration_value, spec = (row['declaration'], row['specification'])
        require(declaration_value['relative_path'] == spec['relative_path'] and declaration_value['format'] == spec['format'])
        if declaration_value['state'] == 'present':
            require(type(declaration_value['size_bytes']) is int and type(declaration_value['sha256']) is str)
        else:
            require(declaration_value['sha256'] is None and declaration_value['size_bytes'] is None)
    if value['outcome'] == 'not_run':
        require(value['started_at'] is None and value['finished_at'] is None and (value['returncode'] is None))
        require(value['failures'] and all((row['declaration']['state'] == 'absent' for row in value['outputs'])))
    else:
        require(value['started_at'] is not None and value['finished_at'] is not None)
        try:
            start = datetime.fromisoformat(value['started_at'])
            finish = datetime.fromisoformat(value['finished_at'])
            require(start.tzinfo is not None and finish.tzinfo is not None and (finish >= start))
        except (TypeError, ValueError) as error:
            raise ValueError('original_attempt_mismatch') from error
        require(value['returncode'] is None or type(value['returncode']) is int)
        require(value['returncode'] == 0 if value['outcome'] == 'succeeded' else value['returncode'] != 0)
        if value['outcome'] == 'failed':
            expected_failure = 'native_dependency_unavailable' if value['returncode'] is None else 'native_nonzero_exit'
            require(any((row['code'] == expected_failure for row in value['failures'])))
        else:
            for row in value['outputs']:
                if row['specification']['required'] and row['declaration']['state'] == 'absent':
                    require(any((problem['code'] == 'native_output_unavailable' and problem['file_key'] == row['specification']['file_key'] for problem in value['failures'])))
    return value
