"""Reserve/authenticate one selected NMF start with the existing lifecycle."""
from pathlib import Path

from . import native_lifecycle as native
from .expression_nmf_common import digest, identity, require
from .local_jobs import LocalJobPolicy
from .native_expression_nmf_contracts import (ATTEMPT_DIRECTORY_NAME, OWNER_FILENAME, POLICY,
    RUN_PLAN_FILENAME, STARTED_FILENAME, expression_nmf_driver_argv, expression_nmf_environment,
    expression_nmf_output_files, validate_expression_nmf_requested_job, validate_expression_nmf_run_plan)
from .native_expression_nmf_storage import confined_file, directory, immutable_json, read_json, regular


def _root(assignment, owner):
    return directory(assignment['workspace']) / '.episode-operations' / digest({
        'run': owner['run_id'], 'episode': owner['episode_id']}) / digest(owner['operation_key'])


def _allocation(assignment, policy):
    require(assignment.get('resource_kind') == 'local' and policy == POLICY
        and type(assignment.get('resource_id')) is str, 'nmf_original_allocation_mismatch')
    constraints = assignment.get('constraints')
    require(type(constraints) is dict and not set(constraints) - {'allocation', *POLICY}, 'nmf_original_allocation_mismatch')
    require('allocation' not in constraints or digest(constraints['allocation']) == digest(policy), 'nmf_original_allocation_mismatch')
    require(all(k not in constraints or digest(constraints[k]) == digest(v) for k, v in policy.items()), 'nmf_original_allocation_mismatch')


def _environment(plan):
    return expression_nmf_environment(plan['requested_job']['native_expression_nmf']['software'],
        attempt_directory=plan['attempt_directory'])


def _invoke(plan):
    request = plan['requested_job']
    return {'cwd': str(Path(plan['identity']['execution_id']).parent), 'argv': request['argv'],
        'environment': request['environment'], 'native_expression_nmf_plan': RUN_PLAN_FILENAME}


def _request(plan, paths):
    return {'command': expression_nmf_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent),
        'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'],
        'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}


def prepare_local_expression_nmf(state, operation_key, *, root, policy):
    """Reserve the exact pending practical.job.start; this function never runs it."""
    require(isinstance(policy, LocalJobPolicy) and type(operation_key) is str and bool(operation_key), 'nmf_selected_start_required')
    request = validate_expression_nmf_requested_job(state.assignment['requested_job'])
    _allocation(state.assignment, policy.to_dict())
    root = directory(root)
    handle = native.NativeJobHandle(root / 'native.json')
    plan = validate_expression_nmf_run_plan({'version': 'expression_nmf_run_plan_v1', 'identity': {
        'run_id': state.run_id, 'episode_id': state.episode_id, 'resource_id': state.assignment['resource_id'],
        'execution_id': str(handle.path), 'attempt_id': digest(operation_key), 'operation_key': operation_key,
        'requested_job_sha256': digest(request), 'assignment_sha256': digest(state.assignment)},
        'requested_job': request, 'attempt_directory': str(root / ATTEMPT_DIRECTORY_NAME), 'policy': policy.to_dict(),
        'outputs': expression_nmf_output_files(request['native_expression_nmf'])})
    require(root == _root(state.assignment, plan['identity']), 'nmf_original_attempt_mismatch')
    with state._locked():
        pending = state._load()[4]
        require(pending is not None and pending['operation_key'] == operation_key
            and pending['tool_name'] == 'practical.job.start' and pending['run_id'] == state.run_id
            and pending['episode_id'] == state.episode_id and pending['assignment_sha256'] == digest(state.assignment),
            'nmf_selected_pending_start_required')
        root.mkdir(parents=True, exist_ok=True)
        for name in (RUN_PLAN_FILENAME, 'invoke.json', 'native.json', 'stdout.log', 'stderr.log'):
            confined_file(root, name)
        if handle.path.exists():
            require(local_expression_nmf_plan(state.assignment, str(handle.path)) == plan, 'nmf_original_attempt_mismatch')
            return handle
        require(not Path(plan['attempt_directory']).exists(), 'nmf_original_attempt_unsealed')
        for path in root.iterdir():
            confined_file(root, path.name)
            if path.name in (RUN_PLAN_FILENAME, 'invoke.json'):
                continue
            if path.name in ('stdout.log', 'stderr.log'):
                require(path.stat().st_size == 0, 'nmf_original_attempt_unsealed')
                continue
            require(path.name.startswith('.local-job-') and path.name.endswith('.request'), 'nmf_original_attempt_unsealed')
            token = path.name.removesuffix('.request')
            paths = {name: str(root / (token + '.' + name)) for name in ('ready', 'release', 'result')}
            require(read_json(path) == _request(plan, paths), 'nmf_original_attempt_mismatch')
        immutable_json(root / RUN_PLAN_FILENAME, plan)
        immutable_json(root / 'invoke.json', _invoke(plan))
        native.prepare_job(expression_nmf_driver_argv(plan), cwd=root, policy=policy, handle_path=handle.path,
            env=_environment(plan))
        local_expression_nmf_plan(state.assignment, str(handle.path))
        return handle


def local_expression_nmf_plan(assignment, execution_id):
    """Read the original reservation only; no dispatch, polling or collection."""
    request = validate_expression_nmf_requested_job(assignment['requested_job'])
    require(type(execution_id) is str and Path(execution_id).is_absolute() and str(Path(execution_id)) == execution_id
        and Path(execution_id).name == 'native.json', 'nmf_original_attempt_mismatch')
    root = directory(Path(execution_id).parent)
    plan = validate_expression_nmf_run_plan(read_json(confined_file(root, RUN_PLAN_FILENAME)))
    owner = plan['identity']
    _allocation(assignment, plan['policy'])
    require(owner['assignment_sha256'] == digest(assignment) and owner['resource_id'] == assignment['resource_id']
        and owner['execution_id'] == execution_id and plan['requested_job'] == request and root == _root(assignment, owner),
        'nmf_original_attempt_mismatch')
    original = read_json(confined_file(root, 'native.json'))
    require(original.get('version') == native.VERSION and original.get('stage') in ('prepared', 'submitting', 'released')
        and original.get('command') == expression_nmf_driver_argv(plan) and original.get('cwd') == str(root)
        and digest(original.get('metadata', {}).get('policy')) == digest(plan['policy'])
        and read_json(confined_file(root, 'invoke.json')) == _invoke(plan), 'nmf_original_attempt_mismatch')
    paths = original.get('paths')
    required = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    require(type(paths) is dict and required <= set(paths) and not set(paths) - required - {'statistics', 'native_events'},
        'nmf_original_attempt_mismatch')
    require(len(set(paths.values())) == len(paths) and all(type(p) is str and Path(p).parent == root
        and str(Path(p)) == p for p in paths.values()), 'nmf_original_attempt_mismatch')
    fixed = {str(root / name) for name in (RUN_PLAN_FILENAME, 'invoke.json', 'native.json', 'stdout.log', 'stderr.log')}
    require(not fixed.intersection(paths.values()), 'nmf_original_attempt_mismatch')
    for path in paths.values():
        confined_file(root, Path(path).name)
    for role in ('stdout', 'stderr'):
        require(original.get(role) == str(root / (role + '.log')), 'nmf_original_attempt_mismatch')
        confined_file(root, role + '.log')
    with regular(paths['request']) as stream:
        raw = stream.read()
    require(identity(raw)['sha256'] == original.get('request_sha256') and read_json(paths['request']) == _request(plan, paths),
        'nmf_original_attempt_mismatch')
    attempt = directory(plan['attempt_directory'])
    owner_file, started = confined_file(attempt, OWNER_FILENAME), confined_file(attempt, STARTED_FILENAME)
    if owner_file.exists():
        require(read_json(owner_file) == plan, 'nmf_original_attempt_mismatch')
    if started.exists():
        value = read_json(started)
        require(owner_file.exists() and type(value) is dict and set(value) == {'plan', 'started_at'}
            and value['plan'] == plan, 'nmf_original_attempt_mismatch')
    return plan
