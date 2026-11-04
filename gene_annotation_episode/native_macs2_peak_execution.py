"""One selected MACS2 callpeak attempt on the existing local native lifecycle.

The caller owns received-File authority and PracticalState owns dispatch. This
module freezes that selected job, stages exact opaque input bytes and seals one
native command. Shared peak parsers and components retain numerical authority.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

from jsonschema import Draft202012Validator

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .local_jobs import LocalJobPolicy, check_scratch_budget
from . import native_atac_differential_contracts as shared
from .native_atac_differential_driver import (
    _directory, _immutable, _read_control, _regular, _stage, confined_file,
    declaration, decode_json, verify_software,
)


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

require, canonical, digest = shared.require, shared.canonical, shared.digest
failure, unique_failures = shared.failure, shared.unique_failures
obj, arr, enum, nullable = shared._obj, shared._arr, shared._enum, shared._null
TEXT, ID, INT, BOOL = shared._TEXT, shared._ID, shared._INT, shared._BOOL
FILE = deepcopy(shared._FILE)
SOFTWARE = shared.atac_execution_schema('SoftwareBinding')
REFERENCE, SAMPLE = deepcopy(shared._REFERENCE), deepcopy(shared._SAMPLE)
INPUT = obj(input_key=ID, role=enum('treatment', 'control'), sample_id=ID, reference_id=ID, file=FILE)
REQUEST = obj(version={'const': REQUEST_VERSION}, operation={'const': OPERATION}, mode={'const': MODE},
    run_key=ID, condition_id=ID, reference=REFERENCE, samples=arr(SAMPLE, minItems=1, maxItems=2),
    inputs=arr(INPUT, minItems=2, maxItems=2),
    callpeak=obj(genome_size_argument=TEXT, qvalue_cutoff={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 1}),
    output_prefix=TEXT)
JOB = obj(request=REQUEST, software=SOFTWARE,
    input_bindings=arr(obj(input_key=ID, file=FILE, path=TEXT), minItems=2, maxItems=2))
REQUESTED = obj(argv=arr(TEXT, minItems=6, maxItems=6), environment=shared._ENV, native_macs2_peak=JOB)
SPEC = obj(file_key=ID, role=enum('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal'),
    relative_path=TEXT, format=ID, required=BOOL)
PLAN = obj(version={'const': PLAN_VERSION}, identity=deepcopy(shared._IDENTITY), requested_job=REQUESTED,
    attempt_directory=TEXT, policy={'const': POLICY}, outputs=arr(SPEC, minItems=7, maxItems=7))
SEAL = obj(version={'const': SEAL_VERSION}, identity=deepcopy(shared._IDENTITY), producer_ref=ID,
    argv=arr(TEXT), environment=shared._ENV,
    inputs=arr(obj(input_key=ID, role=enum('treatment', 'control'), file=FILE), minItems=2, maxItems=2),
    started_at=nullable(TEXT), finished_at=nullable(TEXT), returncode=nullable({'type': 'integer'}),
    outcome=enum('succeeded', 'failed', 'not_run'),
    outputs=arr(obj(specification=SPEC, declaration=deepcopy(shared._DECL)), minItems=6, maxItems=6),
    failures=arr(shared.atac_execution_schema('Failure')))
SCHEMAS = {'Binding': obj(operation={'const': OPERATION}, mode={'const': MODE}, software=SOFTWARE),
    'SoftwareBinding': SOFTWARE, 'Request': REQUEST, 'NativeJob': JOB, 'RequestedJob': REQUESTED,
    'RunPlan': PLAN, 'CommandSeal': SEAL}


def _same(left, right):
    return canonical(left) == canonical(right)


def macs2_peak_execution_schema(kind, *, bindings=None):
    require(type(kind) is str and kind in SCHEMAS, 'unsupported_macs2_peak_execution_schema')
    schema = deepcopy(SCHEMAS[kind])
    if bindings is not None:
        require(kind == 'RequestedJob', 'unsupported_macs2_peak_execution_schema')
        choices = [{'properties': {'native_macs2_peak': {'properties': {
            'software': {'const': row['software']}, 'request': {'properties': {
                'operation': {'const': OPERATION}, 'mode': {'const': MODE}}}}}}}
            for row in validate_macs2_peak_bindings(bindings)]
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
    require(DRIVER_MODULE in {row['module'] for row in result['driver_runtime']['implementation_files']},
        'native_dependency_unavailable')
    return result


def _file(value):
    require(value['artifact_ref'] == 'artifact_' + value['sha256']
        and type(value['size_bytes']) is int, 'artifact_digest_mismatch')


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
    require(len(samples) == len(value['samples']) and set(samples) == {row['sample_id'] for row in value['inputs']},
        'condition_mapping')
    require([row['role'] for row in value['inputs']] == ['treatment', 'control']
        and len({row['input_key'] for row in value['inputs']}) == 2, 'condition_mapping')
    for row in value['inputs']:
        _file(row['file'])
        sample = samples[row['sample_id']]
        require(row['reference_id'] == value['reference']['reference_id'] == sample['reference_id']
            and row['file']['artifact_ref'] in sample['input_artifact_refs'], 'condition_mapping')
    argument = value['callpeak']['genome_size_argument']
    if argument not in ('hs', 'mm', 'ce', 'dm'):
        try:
            numeric = Decimal(argument)
        except InvalidOperation as error:
            raise ValueError('invalid_macs2_peak_genome_size') from error
        require(re.fullmatch(r'[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', argument)
            and numeric.is_finite() and numeric > 0, 'invalid_macs2_peak_genome_size')
    prefix = shared.path_value(value['output_prefix'], absolute=False)
    require(len(prefix.parts) == 1 and not prefix.name.startswith('-')
        and prefix.name not in (OWNER_FILENAME, STARTED_FILENAME, SEAL_FILENAME),
        'invalid_output_path')
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
    require(environment.get('PYTHONPATH') == os.pathsep.join([driver['module_root'], *shared._dependency_roots(driver)]),
        'native_dependency_unavailable')
    return dict(argv=[driver['python_executable'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME],
        environment=deepcopy(environment), native_macs2_peak=job)


def validate_macs2_peak_requested_job(value):
    value = _record('RequestedJob', value)
    require(_same(value, requested_job_from_macs2_peak(value['native_macs2_peak'], environment=value['environment'])))
    return value


def macs2_peak_output_files(request):
    request = validate_macs2_peak_request(request)
    prefix = request['output_prefix']
    entries = [('peaks_xls', 'native/' + prefix + '_peaks.xls', 'macs2_peaks_xls_narrow', True),
        ('narrowpeak', 'native/' + prefix + '_peaks.narrowPeak', 'macs2_narrowpeak10', True),
        ('summits', 'native/' + prefix + '_summits.bed', 'macs2_summits_bed5', True),
        ('model', 'native/' + prefix + '_model.r', 'macs2_model_r', False),
        ('stdout', 'native/stdout.log', 'native_stdout', True),
        ('stderr', 'native/stderr.log', 'native_stderr', True),
        ('seal', SEAL_FILENAME, SEAL_VERSION, True)]
    return [dict(file_key=role, role=role, relative_path=path, format=fmt, required=required)
        for role, path, fmt, required in entries]


def _root(assignment, identity):
    return (Path(shared.path_value(assignment['workspace'], absolute=True)) / '.episode-operations'
        / digest({'run': identity['run_id'], 'episode': identity['episode_id']}) / digest(identity['operation_key']))


def _allocation(assignment, policy):
    require(assignment.get('resource_kind') == 'local' and _same(policy, POLICY)
        and type(assignment.get('resource_id')) is str and bool(assignment['resource_id']))
    constraints = assignment.get('constraints')
    require(type(constraints) is dict and not set(constraints) - {
        'allocation', 'memory_bytes', 'scratch_bytes', 'wall_seconds'})
    require('allocation' not in constraints or _same(constraints['allocation'], policy))
    require(all(key not in constraints or _same(constraints[key], value) for key, value in policy.items()))


def validate_macs2_peak_run_plan(value):
    value = _record('RunPlan', value)
    requested = validate_macs2_peak_requested_job(value['requested_job'])
    identity = value['identity']
    execution = shared.path_value(identity['execution_id'], absolute=True)
    attempt = shared.path_value(value['attempt_directory'], absolute=True)
    require(execution.name == 'native.json' and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME)
    require(identity['attempt_id'] == digest(identity['operation_key'])
        and identity['requested_job_sha256'] == digest(requested))
    expected = macs2_peak_output_files(requested['native_macs2_peak']['request'])
    require(_same(value['outputs'], expected))
    for row in value['outputs']:
        shared.path_value(row['relative_path'], absolute=False)
    return value


def macs2_peak_plan(assignment, identity, *, policy):
    """Rebuild only the original selected plan from retained typed metadata."""
    requested = validate_macs2_peak_requested_job(assignment['requested_job'])
    _allocation(assignment, policy)
    value = validate_macs2_peak_run_plan(dict(version=PLAN_VERSION, identity=deepcopy(identity),
        requested_job=requested,
        attempt_directory=str(PurePosixPath(identity['execution_id']).parent / ATTEMPT_DIRECTORY_NAME),
        policy=deepcopy(policy), outputs=macs2_peak_output_files(requested['native_macs2_peak']['request'])))
    require(identity['assignment_sha256'] == digest(assignment)
        and identity['resource_id'] == assignment['resource_id']
        and Path(identity['execution_id']).parent == _root(assignment, identity))
    return value


def macs2_peak_driver_argv(plan):
    plan = validate_macs2_peak_run_plan(plan)
    return [*plan['requested_job']['argv'][:-1], str(PurePosixPath(plan['identity']['execution_id']).parent / RUN_PLAN_FILENAME)]


def _driver_environment(plan):
    job = plan['requested_job']['native_macs2_peak']
    root = PurePosixPath(plan['attempt_directory'])
    driver = job['software']['driver_runtime']
    return {**plan['requested_job']['environment'],
        'PYTHONPATH': os.pathsep.join([driver['module_root'], *shared._dependency_roots(driver)]),
        'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'), 'TMPDIR': str(root / 'tmp'),
        'XDG_CACHE_HOME': str(root / 'cache'), 'PIP_CACHE_DIR': str(root / 'cache/pip')}


def _native_environment(plan):
    root = PurePosixPath(plan['attempt_directory'])
    runtime = plan['requested_job']['native_macs2_peak']['software']['macs2_runtime']
    return dict(PATH='/usr/bin:/bin', LC_ALL='C.UTF-8', PYTHONPATH=os.pathsep.join(runtime['import_roots']),
        PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
        OMP_NUM_THREADS='1', TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'), TMPDIR=str(root / 'tmp'),
        XDG_CACHE_HOME=str(root / 'cache'), PIP_CACHE_DIR=str(root / 'cache/pip'))


def macs2_peak_command_argv(plan):
    plan = validate_macs2_peak_run_plan(plan)
    job = plan['requested_job']['native_macs2_peak']
    request, runtime = job['request'], job['software']['macs2_runtime']
    root = PurePosixPath(plan['attempt_directory'])
    # Omit -f, --nomodel and ATAC overrides: these are the pinned native AUTO
    # reader and fragment-size/strand-shift model defaults, not inferred biology.
    return [runtime['python_executable'], '-B', '-S', runtime['macs2_script'], 'callpeak',
        '-t', str(root / 'inputs/treatment.input'), '-c', str(root / 'inputs/control.input'),
        '-n', request['output_prefix'], '-g', request['callpeak']['genome_size_argument'],
        '-q', str(request['callpeak']['qvalue_cutoff']), '--outdir', str(root / 'native'),
        '--tempdir', str(root / 'tmp')]


def _invoke(plan):
    requested = plan['requested_job']
    return dict(cwd=str(Path(plan['identity']['execution_id']).parent), argv=requested['argv'],
        environment=requested['environment'], native_macs2_peak_plan=RUN_PLAN_FILENAME)


def _job_request(plan, paths):
    return dict(command=macs2_peak_driver_argv(plan), cwd=str(Path(plan['identity']['execution_id']).parent),
        file_bytes=POLICY['scratch_bytes'], ready_path=paths['ready'], release_path=paths['release'],
        result_path=paths['result'], stdin_path=None, env=_driver_environment(plan))


def _strict_json(path):
    with _regular(path) as stream:
        return decode_json(stream.read())


def _no_dispatch(root, plan):
    require(not Path(plan['attempt_directory']).exists(), 'unsealed_native_attempt')
    for path in root.iterdir():
        confined_file(root, path.name)
        if path.name in {RUN_PLAN_FILENAME, 'invoke.json'}:
            continue
        if path.name in {'stdout.log', 'stderr.log'}:
            require(path.stat().st_size == 0, 'unsealed_native_attempt')
            continue
        require(path.name.startswith('.local-job-') and path.name.endswith('.request'), 'unsealed_native_attempt')
        token = path.name.removesuffix('.request')
        paths = {key: str(root / (token + '.' + key)) for key in ('ready', 'release', 'result')}
        require(_same(_strict_json(path), _job_request(plan, paths)))


def prepare_local_macs2_peak(state, operation_key, *, root, policy):
    """Reserve this actual pending start; only the existing host dispatches it."""
    require(type(policy) is LocalJobPolicy and type(operation_key) is str and bool(operation_key))
    requested = validate_macs2_peak_requested_job(state.assignment['requested_job'])
    _allocation(state.assignment, policy.to_dict())
    root = _directory(root)
    handle = native.NativeJobHandle(root / 'native.json')
    plan = macs2_peak_plan(state.assignment,
        dict(run_id=state.run_id, episode_id=state.episode_id, resource_id=state.assignment['resource_id'],
            execution_id=str(handle.path), attempt_id=digest(operation_key), operation_key=operation_key,
            requested_job_sha256=digest(requested), assignment_sha256=digest(state.assignment)),
        policy=policy.to_dict())
    require(root == _root(state.assignment, plan['identity']))
    with state._locked():
        pending = state._load()[4]
        require(pending is not None and pending['operation_key'] == operation_key
            and pending['tool_name'] == 'practical.job.start' and pending['run_id'] == state.run_id
            and pending['episode_id'] == state.episode_id
            and pending['assignment_sha256'] == plan['identity']['assignment_sha256'], 'selected_pending_start_required')
        root.mkdir(parents=True, exist_ok=True)
        _directory(root)
        for name in (RUN_PLAN_FILENAME, 'invoke.json', 'native.json', 'stdout.log', 'stderr.log'):
            confined_file(root, name)
        if handle.path.exists():
            require(_same(read_local_macs2_peak_plan(state.assignment, str(handle.path)), plan))
            return handle
        for name, expected in ((RUN_PLAN_FILENAME, plan), ('invoke.json', _invoke(plan))):
            path = confined_file(root, name)
            if path.exists():
                require(_same(_read_control(path), expected))
        _no_dispatch(root, plan)
        _immutable(root / RUN_PLAN_FILENAME, plan)
        _immutable(root / 'invoke.json', _invoke(plan))
        native.prepare_job(macs2_peak_driver_argv(plan), cwd=root, policy=policy,
            handle_path=handle.path, env=_driver_environment(plan))
        read_local_macs2_peak_plan(state.assignment, str(handle.path))
        return handle


def validate_macs2_peak_original_controls(plan, original, request_raw):
    """Authenticate retained original control bytes without reopening paths."""
    plan = validate_macs2_peak_run_plan(plan)
    root = Path(plan['identity']['execution_id']).parent
    require(type(original) is dict and type(original.get('metadata')) is dict)
    require(original.get('version') == native.VERSION and original.get('stage') in {'prepared', 'submitting', 'released'}
        and _same(original.get('command'), macs2_peak_driver_argv(plan)) and original.get('cwd') == str(root)
        and _same(original['metadata'].get('policy'), plan['policy']))
    paths = original.get('paths')
    required = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    require(type(paths) is dict and required <= paths.keys() and not paths.keys() - required - {'statistics', 'native_events'})
    require(all(type(path) is str and shared.path_value(path, absolute=True).parent == PurePosixPath(root)
        for path in paths.values())
        and len(set(paths.values())) == len(paths))
    fixed = {str(root / name) for name in ('native.json', 'invoke.json', RUN_PLAN_FILENAME, 'stdout.log', 'stderr.log')}
    require(not fixed.intersection(paths.values()))
    for role in ('statistics', 'native_events'):
        require((role in paths) == (role in original))
    for role in ('stdout', 'stderr'):
        require(original.get(role) == str(root / (role + '.log')))
    require(type(request_raw) in (bytes, str))
    raw = request_raw.encode('utf-8') if type(request_raw) is str else request_raw
    require(hashlib.sha256(raw).hexdigest() == original.get('request_sha256')
        and _same(decode_json(raw), _job_request(plan, paths)))
    return plan


def read_local_macs2_peak_plan(assignment, execution_id):
    """Authenticate the original reservation without starting or collecting."""
    requested = validate_macs2_peak_requested_job(assignment['requested_job'])
    require(type(execution_id) is str and str(shared.path_value(execution_id, absolute=True)) == execution_id
        and Path(execution_id).name == 'native.json')
    root = _directory(Path(execution_id).parent)
    for name in (RUN_PLAN_FILENAME, 'invoke.json', 'native.json', 'stdout.log', 'stderr.log'):
        confined_file(root, name)
    plan = validate_macs2_peak_run_plan(_read_control(root / RUN_PLAN_FILENAME))
    identity = plan['identity']
    _allocation(assignment, plan['policy'])
    require(identity['assignment_sha256'] == digest(assignment) and identity['resource_id'] == assignment['resource_id']
        and _same(plan['requested_job'], requested) and identity['execution_id'] == execution_id
        and root == _root(assignment, identity))
    original = _strict_json(root / 'native.json')
    paths = original.get('paths')
    require(type(paths) is dict and type(paths.get('request')) is str)
    request_path = confined_file(root, Path(paths['request']).name)
    require(str(request_path) == paths['request'])
    with _regular(request_path) as stream:
        request_raw = stream.read()
    validate_macs2_peak_original_controls(plan, original, request_raw)
    for path in paths.values():
        confined_file(root, Path(path).name)
    require(_same(_read_control(root / 'invoke.json'), _invoke(plan)))
    attempt = _directory(plan['attempt_directory'])
    owner, started = confined_file(attempt, OWNER_FILENAME), confined_file(attempt, STARTED_FILENAME)
    if owner.exists():
        require(_same(_read_control(owner), plan))
    if started.exists():
        value = _read_control(started)
        require(owner.exists() and type(value) is dict and set(value) == {'plan', 'started_at'}
            and _same(value['plan'], plan))
    return plan


def _producer_ref(plan):
    return 'macs2_peak_producer_' + digest({'identity': plan['identity'], 'command': 'callpeak'})


def validate_macs2_peak_seal(value, *, plan):
    plan = validate_macs2_peak_run_plan(plan)
    value = _record('CommandSeal', value)
    require(_same(value['identity'], plan['identity']) and value['producer_ref'] == _producer_ref(plan)
        and _same(value['argv'], macs2_peak_command_argv(plan)) and _same(value['environment'], _native_environment(plan)))
    request = plan['requested_job']['native_macs2_peak']['request']
    expected_inputs = [{key: row[key] for key in ('input_key', 'role', 'file')} for row in request['inputs']]
    require(_same(value['inputs'], expected_inputs))
    expected_outputs = [row for row in plan['outputs'] if row['role'] != 'seal']
    require(_same([row['specification'] for row in value['outputs']], expected_outputs))
    for row in value['outputs']:
        declaration_value, spec = row['declaration'], row['specification']
        require(declaration_value['relative_path'] == spec['relative_path'] and declaration_value['format'] == spec['format'])
        if declaration_value['state'] == 'present':
            require(type(declaration_value['size_bytes']) is int and type(declaration_value['sha256']) is str)
        else:
            require(declaration_value['sha256'] is None and declaration_value['size_bytes'] is None)
    if value['outcome'] == 'not_run':
        require(value['started_at'] is None and value['finished_at'] is None and value['returncode'] is None)
        require(value['failures'] and all(row['declaration']['state'] == 'absent' for row in value['outputs']))
    else:
        require(value['started_at'] is not None and value['finished_at'] is not None)
        try:
            start = datetime.fromisoformat(value['started_at'])
            finish = datetime.fromisoformat(value['finished_at'])
            require(start.tzinfo is not None and finish.tzinfo is not None and finish >= start)
        except (TypeError, ValueError) as error:
            raise ValueError('original_attempt_mismatch') from error
        require(value['returncode'] is None or type(value['returncode']) is int)
        require(value['returncode'] == 0 if value['outcome'] == 'succeeded' else value['returncode'] != 0)
        if value['outcome'] == 'failed':
            expected_failure = 'native_dependency_unavailable' if value['returncode'] is None else 'native_nonzero_exit'
            require(any(row['code'] == expected_failure for row in value['failures']))
        else:
            for row in value['outputs']:
                if row['specification']['required'] and row['declaration']['state'] == 'absent':
                    require(any(problem['code'] == 'native_output_unavailable'
                        and problem['file_key'] == row['specification']['file_key'] for problem in value['failures']))
    return value


def run_macs2_peak(plan):
    """Stage exact bytes and seal one subprocess; an orphan cannot be rerun."""
    plan = validate_macs2_peak_run_plan(plan)
    directory = _directory(plan['attempt_directory'])
    seal_path = confined_file(directory, SEAL_FILENAME)
    if directory.exists() and any(directory.iterdir()):
        require(_same(_read_control(confined_file(directory, OWNER_FILENAME)), plan))
        require(seal_path.exists(), 'unsealed_native_attempt')
        saved = validate_macs2_peak_seal(_read_control(seal_path), plan=plan)
        for row in saved['outputs']:
            require(_same(declaration(row['specification'], directory), row['declaration']))
        return saved
    directory.mkdir(parents=True, exist_ok=True)
    _immutable(directory / OWNER_FILENAME, plan)
    _immutable(directory / STARTED_FILENAME, {'plan': plan, 'started_at': datetime.now(timezone.utc).isoformat()})
    for name in ('inputs', 'native', 'tmp', 'cache/pip'):
        (directory / name).mkdir(parents=True, exist_ok=True)
    job = plan['requested_job']['native_macs2_peak']
    policy = LocalJobPolicy(**plan['policy'])
    problems, staged = [], []
    runtime_available = True
    try:
        verify_software(job['software'])
    except (OSError, ValueError, ImportError):
        runtime_available = False
        problems.append(failure('native_dependency_unavailable', 'execution', step_key='callpeak', requirement='native_runtime'))
    for selected, binding in zip(job['request']['inputs'], job['input_bindings']):
        if not runtime_available:
            continue
        try:
            staged.append(_stage(binding, {'relative_path': 'inputs/' + selected['role'] + '.input'},
                directory=directory, policy=policy))
        except (OSError, ValueError, AcquisitionError) as error:
            code = ('resource_limit' if isinstance(error, AcquisitionError) else
                'artifact_digest_mismatch' if str(error) == 'artifact_digest_mismatch' else 'input_unavailable')
            problems.append(failure(code, 'input', step_key='callpeak', binding_key=binding['input_key'],
                artifact_ref=binding['file']['artifact_ref'], requirement='resource_allocation'
                    if code == 'resource_limit' else 'matching_file_identity'))
    started = finished = returncode = None
    outcome = 'not_run'
    if len(staged) == 2:
        try:
            verify_software(job['software'])
            check_scratch_budget(directory.parent, policy)
        except (OSError, ValueError, ImportError, AcquisitionError) as error:
            problems.append(failure('resource_limit' if isinstance(error, AcquisitionError) else 'native_dependency_unavailable',
                'execution', step_key='callpeak', requirement='resource_allocation'
                    if isinstance(error, AcquisitionError) else 'native_runtime'))
        else:
            started = datetime.now(timezone.utc).isoformat()
            try:
                with confined_file(directory, 'native/stdout.log').open('xb') as stdout, \
                        confined_file(directory, 'native/stderr.log').open('xb') as stderr:
                    completed = subprocess.run(macs2_peak_command_argv(plan), cwd=directory,
                        env=_native_environment(plan), stdout=stdout, stderr=stderr, check=False)
                    returncode = completed.returncode
                outcome = 'succeeded' if returncode == 0 else 'failed'
                if returncode != 0:
                    problems.append(failure('native_nonzero_exit', 'execution', step_key='callpeak', requirement='original_native_outcome'))
            except OSError:
                outcome = 'failed'
                problems.append(failure('native_dependency_unavailable', 'execution', step_key='callpeak', requirement='native_runtime'))
            finished = datetime.now(timezone.utc).isoformat()
    outputs = [dict(specification=spec, declaration=declaration(spec, directory))
        for spec in plan['outputs'] if spec['role'] != 'seal']
    if outcome == 'succeeded':
        for row in outputs:
            if row['specification']['required'] and row['declaration']['state'] == 'absent':
                problems.append(failure('native_output_unavailable', 'execution', step_key='callpeak',
                    file_key=row['specification']['file_key'], requirement='complete_native_output'))
    seal = validate_macs2_peak_seal(dict(version=SEAL_VERSION, identity=plan['identity'], producer_ref=_producer_ref(plan),
        argv=macs2_peak_command_argv(plan), environment=_native_environment(plan),
        inputs=[{key: row[key] for key in ('input_key', 'role', 'file')} for row in job['request']['inputs']],
        started_at=started, finished_at=finished, returncode=returncode, outcome=outcome,
        outputs=outputs, failures=unique_failures(problems)), plan=plan)
    _immutable(seal_path, seal)
    return seal


def macs2_peak_callpeak_binding(plan, seal):
    plan = validate_macs2_peak_run_plan(plan)
    seal = validate_macs2_peak_seal(seal, plan=plan)
    request = plan['requested_job']['native_macs2_peak']['request']
    treatment, control = request['inputs']
    identities = {row['specification']['role']: ('artifact_' + row['declaration']['sha256']
        if row['declaration']['state'] == 'present' else None) for row in seal['outputs']}
    p = request['callpeak']
    return dict(run_key=request['run_key'], condition_id=request['condition_id'],
        sample_ids=[treatment['sample_id']], reference_id=request['reference']['reference_id'],
        treatment_input_refs=[treatment['file']['artifact_ref']], supplied_control_sample_ids=[control['sample_id']],
        supplied_control_input_refs=[control['file']['artifact_ref']], selected_format='AUTO', paired_end=False,
        selected_argv=deepcopy(seal['argv']), selected_parameters=dict(genome_size_argument=p['genome_size_argument'],
            effective_genome_size_bp=None, keep_duplicates=1, nomodel=False, shift_bp=0, extension_size_bp=200,
            qvalue_cutoff=p['qvalue_cutoff'], pvalue_cutoff=None, store_bedgraph=False, spmr=False, broad=False,
            downsample=False, small_local_window_bp=1000, large_local_window_bp=10000),
        artifact_roles=dict(peaks_xls=identities['peaks_xls'], narrowpeak=identities['narrowpeak'], summits=identities['summits'],
            signal_track=None, background_track=None), producer_ref=seal['producer_ref'])


def macs2_peak_observed_files(plan, view, *, log_window_bytes, log_roles):
    from .native_atac_differential_observations import _detail
    plan = validate_macs2_peak_run_plan(plan)
    require(type(log_window_bytes) is int and log_window_bytes > 0, 'positive_log_window_required')
    require(type(log_roles) in (tuple, list) and all(type(role) is str for role in log_roles)
        and len(set(log_roles)) == len(log_roles) and set(log_roles) <= {'stdout', 'stderr'}, 'unsupported_native_log_role')
    require(type(view) is dict and type(view.get('terminal')) is bool, 'native_terminal_observation_required')
    directory, root = Path(plan['attempt_directory']), Path(plan['identity']['execution_id']).parent
    outputs, logs, result_available = [], [], False
    for spec in plan['outputs']:
        role = spec['role']
        is_log = role in {'stdout', 'stderr'}
        limit = log_window_bytes if is_log and role in log_roles else None
        detail = _detail(directory, spec['relative_path'], tail_limit=limit)
        if is_log and not detail['available']:
            detail = _detail(root, role + '.log', tail_limit=limit)
        outputs.append(dict(role=role if is_log else 'requested_output:' + detail['path'], available=detail['available'],
            bytes=detail.get('bytes'), writer_closed=detail['available'] and view['terminal'] and view.get('quiescent') is True))
        result_available |= role == 'seal' and detail['available']
        if is_log and role in log_roles and detail['available']:
            logs.append(dict(role=role, path=detail['path'], offset=detail['tail_byte_offset'],
                observed_size=detail['bytes'], bytes_base64=detail['bytes_base64']))
    return outputs, logs, result_available


def read_macs2_peak_output(plan, *, path, offset, limit):
    from .native_file_capture import _path, _producer_file
    plan = validate_macs2_peak_run_plan(plan)
    require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 1024 * 1024,
        'bounded_native_output_window_required')
    target = _path(path, absolute=True)
    directory = _path(plan['attempt_directory'], absolute=True)
    root = _path(str(Path(plan['identity']['execution_id']).parent), absolute=True)
    allowed = {str(directory / row['relative_path']): (directory, row['relative_path']) for row in plan['outputs']}
    allowed.update({str(root / (role + '.log')): (root, role + '.log') for role in ('stdout', 'stderr')})
    require(str(target) in allowed, 'native_macs2_peak_original_output_path_required')
    owner, relative = allowed[str(target)]
    with _producer_file(owner, _path(relative, absolute=False)) as pinned:
        with pinned.open('rb') as stream:
            size = os.fstat(stream.fileno()).st_size
            stream.seek(offset)
            raw = stream.read(min(limit, max(0, size - offset)))
    return dict(path=str(target), offset=offset, returned_bytes=len(raw), size_bytes=size,
        bytes_base64=base64.b64encode(raw).decode('ascii'), text_utf8=raw.decode('utf-8', errors='replace'))


_DESCRIPTION = 'Call narrow ChIP-seq peaks from supplied treatment and matched-control reads with MACS2; retain native peak measurements.'
_INSTRUCTIONS = (
    'Use the supplied read Files and their declared sample/reference associations, effective genome size and q-value cutoff. '
    'Run one callpeak operation with the selected MACS2 installation and its native input-detection and '
    'fragment-size/strand-shift model defaults. Retain original XLS, narrowPeak, summit, model and log outputs. '
    'Populate the existing shared peak components and return the requested intervals, native statistics and qualifications. '
    'Preserve each format’s coordinates and native values; the three representations do not count as three separate peak sets. '
    'Missing or failed output remains distinguishable from a complete empty result. Later reads use retained results.'
)


def macs2_peak_tool_contracts(bindings, *, resource_kind, resource_id):
    from .macs2_peak_request_binding import resource_assignment_schema
    require(resource_kind == 'local' and type(resource_id) is str and bool(resource_id) and '\0' not in resource_id)
    bindings = validate_macs2_peak_bindings(bindings)
    if not bindings:
        return []
    return [dict(name=OPERATION, description=_DESCRIPTION, resources='local', instructions=_INSTRUCTIONS,
        input_schema=resource_assignment_schema(resource_id, bindings=bindings),
        invocation_route=dict(kind='commission', routes=[dict(entry_role='launch', resource_id=resource_id,
            resource_role='launch_local')]))]


def freeze_macs2_peak_software_binding(*, module_root, snapshot_directory, native_runtime):
    from .native_atac_differential_software import freeze_atac_native_software_binding
    return freeze_atac_native_software_binding(module_root=module_root, snapshot_directory=snapshot_directory,
        native_runtime=native_runtime, additional_driver_modules=(DRIVER_MODULE,))


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    require(type(arguments) is list and len(arguments) == 1, 'macs2_peak_plan_path_required')
    seal = run_macs2_peak(_read_control(Path(arguments[0])))
    return 0 if seal['outcome'] == 'succeeded' and not seal['failures'] else 1


__all__ = ['OPERATION', 'MODE', 'POLICY', 'DRIVER_MODULE', 'RUN_PLAN_FILENAME', 'ATTEMPT_DIRECTORY_NAME',
    'OWNER_FILENAME', 'STARTED_FILENAME', 'SEAL_FILENAME', 'REQUEST_VERSION', 'PLAN_VERSION', 'SEAL_VERSION',
    'macs2_peak_execution_schema', 'validate_macs2_peak_bindings', 'validate_macs2_peak_request',
    'validate_macs2_peak_native_job', 'validate_macs2_peak_requested_job', 'validate_macs2_peak_run_plan',
    'macs2_peak_plan',
    'validate_macs2_peak_original_controls',
    'requested_job_from_macs2_peak', 'macs2_peak_tool_contracts', 'macs2_peak_output_files', 'macs2_peak_driver_argv',
    'macs2_peak_command_argv', 'prepare_local_macs2_peak', 'read_local_macs2_peak_plan', 'run_macs2_peak',
    'validate_macs2_peak_seal', 'macs2_peak_callpeak_binding', 'macs2_peak_observed_files', 'read_macs2_peak_output',
    'freeze_macs2_peak_software_binding']


if __name__ == '__main__':
    raise SystemExit(main())
