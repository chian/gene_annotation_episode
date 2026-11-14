"""LUMPY host reservation and exact original saved control/readback ownership.

The host retains the actual native lifecycle and supplied record identities.
It is not imported by the isolated current LUMPY driver.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import gene_annotation_episode.native_lifecycle as native
from gene_annotation_episode.local_job_policy import LocalJobPolicy
from .native_atac_file_records import _directory, _regular, confined_file
from .native_atac_control_files import decode_json, _read_control, _immutable
from .native_lumpy_execution import (
    POLICY, RUN_PLAN_FILENAME, ATTEMPT_DIRECTORY_NAME, OWNER_FILENAME,
    STARTED_FILENAME, PLAN_VERSION, _same, require, digest, shared,
    validate_lumpy_requested_job, validate_lumpy_run_plan, lumpy_output_files,
    lumpy_driver_argv, _driver_environment, _current_driver,
)


def _root(assignment, identity):
    return (Path(shared.path_value(assignment['workspace'], absolute=True)) / '.episode-operations'
        / digest({'run': identity['run_id'], 'episode': identity['episode_id']}) / digest(identity['operation_key']))


def _allocation(assignment, policy):
    require(assignment.get('resource_kind') == 'local' and _same(policy, POLICY)
        and type(assignment.get('resource_id')) is str and bool(assignment['resource_id']))
    constraints = assignment.get('constraints')
    require(type(constraints) is dict and not set(constraints) - {'allocation', 'memory_bytes', 'scratch_bytes'})
    require('allocation' not in constraints or _same(constraints['allocation'], policy))
    require(all(key not in constraints or _same(constraints[key], value) for key, value in policy.items()))


def lumpy_plan(assignment, identity, *, policy):
    requested = validate_lumpy_requested_job(assignment['requested_job'])
    _allocation(assignment, policy)
    plan = validate_lumpy_run_plan(dict(version=PLAN_VERSION, identity=deepcopy(identity),
        requested_job=requested, attempt_directory=str(PurePosixPath(identity['execution_id']).parent / ATTEMPT_DIRECTORY_NAME),
        policy=deepcopy(policy), outputs=lumpy_output_files(requested['native_lumpy']['request'])))
    require(identity['assignment_sha256'] == digest(assignment)
        and identity['resource_id'] == assignment['resource_id']
        and Path(identity['execution_id']).parent == _root(assignment, identity))
    return plan


def _invoke(plan):
    requested = plan['requested_job']
    return dict(cwd=str(Path(plan['identity']['execution_id']).parent), argv=requested['argv'],
        environment=requested['environment'], native_lumpy_plan=RUN_PLAN_FILENAME)


def _job_request(plan, paths):
    return dict(command=lumpy_driver_argv(plan), cwd=str(Path(plan['identity']['execution_id']).parent),
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


def prepare_local_lumpy(state, operation_key, *, root, policy):
    """Reserve the actual selected pending start; the shared host dispatches it."""
    require(type(policy) is LocalJobPolicy and type(operation_key) is str and bool(operation_key))
    requested = validate_lumpy_requested_job(state.assignment['requested_job'])
    _allocation(state.assignment, policy.to_dict())
    root = _directory(root)
    handle = native.NativeJobHandle(root / 'native.json')
    plan = lumpy_plan(state.assignment, dict(run_id=state.run_id, episode_id=state.episode_id,
        resource_id=state.assignment['resource_id'], execution_id=str(handle.path), attempt_id=digest(operation_key),
        operation_key=operation_key, requested_job_sha256=digest(requested), assignment_sha256=digest(state.assignment)),
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
            require(_same(read_local_lumpy_plan(state.assignment, str(handle.path)), plan))
            return handle
        for name, expected in ((RUN_PLAN_FILENAME, plan), ('invoke.json', _invoke(plan))):
            path = confined_file(root, name)
            if path.exists():
                require(_same(_read_control(path), expected))
        _no_dispatch(root, plan)
        require(_current_driver(plan['requested_job']['native_lumpy']['software']['driver_runtime']),
                'selected_worker_identity_conflict')
        _immutable(root / RUN_PLAN_FILENAME, plan)
        _immutable(root / 'invoke.json', _invoke(plan))
        native.prepare_job(lumpy_driver_argv(plan), cwd=root, policy=policy,
            handle_path=handle.path, env=_driver_environment(plan))
        read_local_lumpy_plan(state.assignment, str(handle.path))
        return handle


def validate_lumpy_original_controls(plan, original, request_raw):
    """Check literal original control bytes; this does not reopen their paths."""
    plan = validate_lumpy_run_plan(plan)
    root = Path(plan['identity']['execution_id']).parent
    require(type(original) is dict and type(original.get('metadata')) is dict)
    require(original.get('version') == native.VERSION and original.get('stage') in {'prepared', 'submitting', 'released'}
        and _same(original.get('command'), lumpy_driver_argv(plan)) and original.get('cwd') == str(root)
        and _same(original['metadata'].get('policy'), plan['policy']))
    paths = original.get('paths');required = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    require(type(paths) is dict and required <= paths.keys() and not paths.keys() - required - {'statistics', 'native_events'})
    require(all(type(path) is str and shared.path_value(path, absolute=True).parent == PurePosixPath(root)
        for path in paths.values()) and len(set(paths.values())) == len(paths))
    fixed = {str(root / name) for name in ('native.json', 'invoke.json', RUN_PLAN_FILENAME, 'stdout.log', 'stderr.log')}
    require(not fixed.intersection(paths.values()))
    for role in ('statistics', 'native_events'):
        require((role in paths) == (role in original))
    for role in ('stdout', 'stderr'):
        require(original.get(role) == str(root / (role + '.log')))
    require(type(request_raw) in (bytes, str))
    raw = request_raw.encode() if type(request_raw) is str else request_raw
    require(hashlib.sha256(raw).hexdigest() == original.get('request_sha256')
        and _same(decode_json(raw), _job_request(plan, paths)))
    return plan


def read_local_lumpy_plan(assignment, execution_id):
    requested = validate_lumpy_requested_job(assignment['requested_job'])
    require(type(execution_id) is str and str(shared.path_value(execution_id, absolute=True)) == execution_id
        and Path(execution_id).name == 'native.json')
    root = _directory(Path(execution_id).parent)
    for name in (RUN_PLAN_FILENAME, 'invoke.json', 'native.json', 'stdout.log', 'stderr.log'):
        confined_file(root, name)
    plan = validate_lumpy_run_plan(_read_control(root / RUN_PLAN_FILENAME));identity = plan['identity']
    _allocation(assignment, plan['policy'])
    require(identity['assignment_sha256'] == digest(assignment) and identity['resource_id'] == assignment['resource_id']
        and _same(plan['requested_job'], requested) and identity['execution_id'] == execution_id and root == _root(assignment, identity))
    original = _strict_json(root / 'native.json');paths = original.get('paths')
    require(type(paths) is dict and type(paths.get('request')) is str)
    request_path = confined_file(root, Path(paths['request']).name)
    require(str(request_path) == paths['request'])
    with _regular(request_path) as stream:
        request_raw = stream.read()
    validate_lumpy_original_controls(plan, original, request_raw)
    for path in paths.values():
        confined_file(root, Path(path).name)
    require(_same(_read_control(root / 'invoke.json'), _invoke(plan)))
    attempt = _directory(plan['attempt_directory'])
    owner, started = confined_file(attempt, OWNER_FILENAME), confined_file(attempt, STARTED_FILENAME)
    if owner.exists():
        require(_same(_read_control(owner), plan))
    if started.exists():
        value = _read_control(started)
        require(owner.exists() and type(value) is dict and set(value) == {'plan', 'started_at'} and _same(value['plan'], plan))
    return plan


