"""Reserve and qualify one selected local masking attempt.

The ordinary practical episode and native lifecycle own selection and dispatch.
Reading or preparing this reservation never starts, retries, or grades work.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
from gene_annotation_episode.episodic_workflow.root.a110 import native_lifecycle as native
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_contracts import _path, native_blast_digest, validate_native_blast_masking_requested_job, validate_native_blast_masking_plan
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_driver import _confined_file, _read_json
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
PLAN_NAME = 'blast-masking-plan.json'
ATTEMPT_NAME = 'blast-masking-attempt'
OWNER_NAME = '.native-blast-masking-owner.json'

def _directory(value):
    _path(value, absolute=True)
    path = Path(value)
    if path.resolve() != path:
        raise ValueError('native_blast_masking_original_directory_path_escape')
    return path

def _command(root):
    return [sys.executable, '-m', 'gene_annotation_episode.native_blast_masking_driver', str(root / PLAN_NAME)]

def _environment(root):
    return {'PYTHONPATH': str(Path(__file__).resolve().parents[6]), 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(root), 'TMP': str(root), 'TEMP': str(root), 'XDG_CACHE_HOME': str(root / 'cache')}

def _invoke(request, attempt):
    return {'cwd': str(attempt), 'argv': request['argv'], 'environment': request['environment'], 'native_blast_masking_plan': PLAN_NAME}

def _root(assignment, owner):
    return _directory(assignment['workspace']) / '.episode-operations' / native_blast_digest({'run': owner['run_id'], 'episode': owner['episode_id']}) / native_blast_digest(owner['operation_key'])

def _resource(assignment):
    if assignment.get('resource_kind') != 'local':
        raise ValueError('native_blast_masking_local_resource_required')
    resource = assignment.get('resource_id')
    if type(resource) is not str or not resource or '\x00' in resource:
        raise ValueError('native_blast_masking_resource_identity_required')
    return resource

def _policy(assignment, policy):
    constraints = assignment.get('constraints', {})
    if 'allocation' in constraints and constraints['allocation'] != policy or any((key in constraints and constraints[key] != value for key, value in policy.items())):
        raise ValueError('native_blast_masking_original_allocation_conflict')

def local_blast_masking_plan(assignment, execution_id):
    """Qualify all original command, owner, environment and allocation ports."""
    request = validate_native_blast_masking_requested_job(assignment['requested_job'])
    resource = _resource(assignment)
    _path(execution_id, absolute=True)
    handle = Path(execution_id)
    if handle.name != 'native.json':
        raise ValueError('native_blast_masking_original_attempt_conflict')
    root = _directory(str(handle.parent))
    for name in ('native.json', PLAN_NAME, 'invoke.json'):
        _confined_file(root, name)
    plan = validate_native_blast_masking_plan(_read(root / PLAN_NAME))
    owner, original = (plan['identity'], native.NativeJobHandle(handle).read())
    _policy(assignment, plan['policy'])
    if plan['requested_job'] != request or owner['execution_id'] != str(handle) or owner['resource_id'] != resource or (root != _root(assignment, owner)) or (owner['attempt_id'] != native_blast_digest(owner['operation_key'])) or (original.get('command') != _command(root)) or (original.get('cwd') != str(root)) or (original.get('metadata', {}).get('policy') != plan['policy']) or (plan['attempt_directory'] != str(root / ATTEMPT_NAME)) or (_read(root / 'invoke.json') != _invoke(request, Path(plan['attempt_directory']))):
        raise ValueError('native_blast_masking_original_attempt_conflict')
    paths = original.get('paths', {})
    required = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    if type(paths) is not dict or not required <= paths.keys():
        raise ValueError('native_blast_masking_original_driver_request_conflict')
    for value in paths.values():
        if type(value) is not str or not Path(value).is_relative_to(root):
            raise ValueError('native_blast_masking_original_driver_path_conflict')
        _confined_file(root, str(Path(value).relative_to(root)))
    if len(set(paths.values())) != len(paths):
        raise ValueError('native_blast_masking_original_driver_path_conflict')
    for role in ('stdout', 'stderr'):
        if original.get(role) != str(root / (role + '.log')):
            raise ValueError('native_blast_masking_original_driver_path_conflict')
        _confined_file(root, role + '.log')
    path = Path(paths['request'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != original.get('request_sha256'):
        raise ValueError('native_blast_masking_original_driver_request_digest_conflict')
    expected = {'command': _command(root), 'cwd': str(root), 'file_bytes': plan['policy']['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(root)}
    if _read_json(path) != expected:
        raise ValueError('native_blast_masking_original_driver_request_conflict')
    owner_path = _confined_file(Path(plan['attempt_directory']), OWNER_NAME)
    if owner_path.exists() and _read_json(owner_path) != plan:
        raise ValueError('native_blast_masking_original_attempt_owner_conflict')
    return plan
