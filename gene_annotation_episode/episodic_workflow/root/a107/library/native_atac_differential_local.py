"""A107 native atac differential local."""


from __future__ import annotations
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a107 import native_lifecycle as native
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a107.library.atac_execution_contracts import OWNER_FILENAME, POLICY, RUN_PLAN_FILENAME, STARTED_FILENAME, atac_driver_argv, atac_environment, validate_atac_requested_job, validate_atac_run_plan
from gene_annotation_episode.episodic_workflow.root.a107.library.native_atac_differential_driver import _directory, _read_control, _regular, require as _require, confined_file

def _strict_json(path):
    from gene_annotation_episode.episodic_workflow.root.a107.library.native_atac_differential_driver import decode_json
    with _regular(path) as stream:
        return decode_json(stream.read())

def _root(assignment, identity):
    return _directory(assignment['workspace']) / '.episode-operations' / digest({'run': identity['run_id'], 'episode': identity['episode_id']}) / digest(identity['operation_key'])

def _allocation(assignment, policy):
    _require(assignment.get('resource_kind') == 'local' and policy == POLICY and (type(assignment.get('resource_id')) is str) and bool(assignment['resource_id']), 'original_attempt_mismatch')
    constraints = assignment.get('constraints')
    _require(type(constraints) is dict and (not set(constraints) - {'allocation', 'memory_bytes', 'scratch_bytes'}), 'original_attempt_mismatch')
    _require('allocation' not in constraints or digest(constraints['allocation']) == digest(policy), 'original_attempt_mismatch')
    _require(all((key not in constraints or digest(constraints[key]) == digest(value) for key, value in policy.items())), 'original_attempt_mismatch')

def _environment(plan):
    return atac_environment(plan['requested_job']['native_atac_differential'], attempt_directory=plan['attempt_directory'], environment=plan['requested_job']['environment'])

def _invoke(plan):
    request = plan['requested_job']
    return {'cwd': str(Path(plan['identity']['execution_id']).parent), 'argv': request['argv'], 'environment': request['environment'], 'native_atac_differential_plan': RUN_PLAN_FILENAME}

def _request(plan, paths):
    return {'command': atac_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}

def local_atac_differential_plan(assignment: dict, execution_id: str) -> dict:
    """Read and qualify the original reservation; never start, poll or collect."""
    request = validate_atac_requested_job(assignment['requested_job'])
    _require(type(execution_id) is str and Path(execution_id).is_absolute() and (str(Path(execution_id)) == execution_id) and (Path(execution_id).name == 'native.json'), 'original_attempt_mismatch')
    root = _directory(Path(execution_id).parent)
    for name in (RUN_PLAN_FILENAME, 'invoke.json', 'native.json', 'stdout.log', 'stderr.log'):
        confined_file(root, name)
    plan = validate_atac_run_plan(_read_control(root / RUN_PLAN_FILENAME))
    identity = plan['identity']
    _allocation(assignment, plan['policy'])
    _require(identity['assignment_sha256'] == digest(assignment) and identity['resource_id'] == assignment['resource_id'] and (plan['requested_job'] == request) and (identity['requested_job_sha256'] == digest(request)) and (identity['execution_id'] == execution_id) and (identity['attempt_id'] == digest(identity['operation_key'])) and (root == _root(assignment, identity)), 'original_attempt_mismatch')
    original = _strict_json(root / 'native.json')
    _require(type(original) is dict and type(original.get('metadata')) is dict, 'original_attempt_mismatch')
    _require(original.get('version') == native.VERSION and original.get('stage') in {'prepared', 'submitting', 'released'} and (original.get('command') == atac_driver_argv(plan)) and (original.get('cwd') == str(root)) and (digest(original['metadata'].get('policy')) == digest(plan['policy'])) and (_read_control(root / 'invoke.json') == _invoke(plan)), 'original_attempt_mismatch')
    paths = original.get('paths')
    required = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    _require(type(paths) is dict and required <= paths.keys() and (not paths.keys() - required - {'statistics', 'native_events'}), 'original_attempt_mismatch')
    _require(all((type(path) is str and Path(path).parent == root and (str(Path(path)) == path) for path in paths.values())) and len(set(paths.values())) == len(paths), 'original_attempt_mismatch')
    fixed = {str(root / name) for name in ('native.json', 'invoke.json', RUN_PLAN_FILENAME, 'stdout.log', 'stderr.log')}
    _require(not fixed.intersection(paths.values()), 'original_attempt_mismatch')
    for path in paths.values():
        confined_file(root, Path(path).name)
    for role in ('statistics', 'native_events'):
        _require((role in paths) == (role in original), 'original_attempt_mismatch')
    for role in ('stdout', 'stderr'):
        _require(original.get(role) == str(root / (role + '.log')), 'original_attempt_mismatch')
    with _regular(paths['request']) as stream:
        raw = stream.read()
    _require(hashlib.sha256(raw).hexdigest() == original.get('request_sha256') and digest(_strict_json(paths['request'])) == digest(_request(plan, paths)), 'original_attempt_mismatch')
    attempt = _directory(plan['attempt_directory'])
    owner = confined_file(attempt, OWNER_FILENAME)
    started = confined_file(attempt, STARTED_FILENAME)
    if owner.exists():
        _require(_read_control(owner) == plan, 'original_attempt_mismatch')
    if started.exists():
        value = _read_control(started)
        _require(owner.exists() and type(value) is dict and (set(value) == {'plan', 'started_at'}) and (value['plan'] == plan), 'original_attempt_mismatch')
    return plan
