from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import gene_annotation_episode.episodic_workflow.root.a110.native_lifecycle as native
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_driver import _absolute_directory, _confined_file, _read_json
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_preparation_contracts import validate_native_hmmer_preparation_requested_job
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_preparation_driver import OWNER_NAME, validate_preparation_plan
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
PLAN_NAME = 'hmmer-preparation-plan.json'

def _command(root):
    return [sys.executable, '-m', 'gene_annotation_episode.native_hmmer_preparation_driver', str(root / PLAN_NAME)]

def _driver_environment(root):
    return {'PYTHONPATH': str(Path(__file__).resolve().parents[6]), 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(root), 'XDG_CACHE_HOME': str(root / 'cache')}

def _invoke(request, attempt):
    return {'cwd': str(attempt), 'argv': request['argv'], 'environment': request['environment'], 'native_hmmer_preparation_plan': 'hmmer-preparation-plan.json'}

def _expected_root(assignment, identity):
    workspace = _absolute_directory(assignment['workspace'])
    return workspace / '.episode-operations' / native_infernal_digest({'run': identity['run_id'], 'episode': identity['episode_id']}) / native_infernal_digest(identity['operation_key'])

def local_hmmer_preparation_plan(assignment, execution_id):
    """Read and validate the original preparation reservation, without dispatch."""
    request = validate_native_hmmer_preparation_requested_job(assignment['requested_job'])
    if type(execution_id) is not str or not Path(execution_id).is_absolute() or Path(execution_id).name != 'native.json':
        raise ValueError('native_hmmer_preparation_original_attempt_conflict')
    handle = Path(execution_id)
    root = _absolute_directory(str(handle.parent))
    for name in ('native.json', 'hmmer-preparation-plan.json', 'invoke.json'):
        _confined_file(root, name)
    plan = validate_preparation_plan(_read(root / 'hmmer-preparation-plan.json'))
    owner = plan['identity']
    original = native.NativeJobHandle(handle).read()
    if plan['requested_job'] != request or assignment.get('resource_kind') != 'local' or owner['execution_id'] != str(handle) or (owner['resource_id'] != assignment.get('resource_id')) or (root != _expected_root(assignment, owner)) or (original.get('command') != _command(root)) or (original.get('cwd') != str(root)) or (original.get('metadata', {}).get('policy') != plan['policy']) or (plan['attempt_directory'] != str(root / 'hmmer-preparation-attempt')) or (_read(root / 'invoke.json') != _invoke(request, Path(plan['attempt_directory']))):
        raise ValueError('native_hmmer_preparation_original_attempt_conflict')
    paths = original.get('paths', {})
    if type(paths) is not dict or 'request' not in paths:
        raise ValueError('native_hmmer_preparation_original_driver_request_conflict')
    for value in paths.values():
        if type(value) is not str or not Path(value).is_relative_to(root):
            raise ValueError('native_hmmer_preparation_original_driver_path_conflict')
        _confined_file(root, str(Path(value).relative_to(root)))
    for role in ('stdout', 'stderr'):
        if original.get(role) != str(root / (role + '.log')):
            raise ValueError('native_hmmer_preparation_original_driver_path_conflict')
        _confined_file(root, role + '.log')
    native_request_path = Path(paths['request'])
    raw = native_request_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != original.get('request_sha256'):
        raise ValueError('native_hmmer_preparation_original_driver_request_digest_conflict')
    native_request = _read_json(native_request_path)
    expected = {'command': _command(root), 'cwd': str(root), 'file_bytes': plan['policy']['scratch_bytes'], 'ready_path': paths.get('ready'), 'release_path': paths.get('release'), 'result_path': paths.get('result'), 'stdin_path': None, 'env': _driver_environment(root)}
    if native_request != expected:
        raise ValueError('native_hmmer_preparation_original_driver_request_conflict')
    owner_path = _confined_file(Path(plan['attempt_directory']), OWNER_NAME)
    if owner_path.exists() and _read_json(owner_path, sealed=True) != plan:
        raise ValueError('native_hmmer_preparation_original_attempt_owner_conflict')
    return plan
