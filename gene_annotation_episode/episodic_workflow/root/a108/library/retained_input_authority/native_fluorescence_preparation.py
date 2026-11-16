"""One bounded, durable fluorescence result-worker reservation and capture.

The host freezes the real finite worker closure and resumes its original native
handle. Historical validation authenticates saved controls without requiring
today's interpreter, scientific inputs, or producer directory.
"""
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.retained_native_read_profiles import retained_cgroup, retained_metadata, retained_policy_matches
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
from gene_annotation_episode.episodic_workflow.root.a108 import native_lifecycle as native
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.fluorescence_execution_common import canonical, closed, identity, require, same
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.fluorescence_result_contracts import PLAN_VERSION, validate_file, validate_path, validate_fluorescence_worker_plan
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_fluorescence_contracts import POLICY
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_fluorescence_storage import decode_json
WORKER_MODULE = 'gene_annotation_episode.fluorescence_result_worker'
INTENT_VERSION = 'fluorescence_worker_intent_v1'
EXECUTION_VERSION = 'fluorescence_worker_execution_v1'

def _environment(root, home, dependencies):
    roots = []
    for row in dependencies:
        path = str(Path(row['package_root']).parent)
        if path not in roots:
            roots.append(path)
    return dict(PYTHONPATH=os.pathsep.join([str(root / 'source_snapshot'), *roots]), PYTHONHOME=home, PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(root), TMP=str(root), TEMP=str(root), XDG_CACHE_HOME=str(root / 'cache'), PIP_CACHE_DIR=str(root / 'cache/pip'))

def _pin(value):
    closed(value, ('path',))
    validate_path(value['path'])

def _validate_intent(intent, plan):
    closed(intent, ('version', 'plan', 'policy', 'command', 'environment', 'source_pins', 'interpreter', 'dependencies', 'python_version', 'python_home', 'runtime_files'))
    require(intent['version'] == INTENT_VERSION and same(intent['plan'], plan) and retained_policy_matches(intent['policy']), 'worker_execution_mismatch')
    root = Path(plan['directory'])
    require(intent['command'] == [str(root / 'runtime/python'), '-B', '-S', '-m', WORKER_MODULE, str(root / 'plan.json')], 'worker_execution_mismatch')
    require(type(intent['source_pins']) is list and intent['source_pins'] and (type(intent['runtime_files']) is list) and intent['runtime_files'] and (type(intent['dependencies']) is list), 'worker_execution_mismatch')
    validate_path(intent['python_home'])
    require(type(intent['python_version']) is str and bool(intent['python_version']), 'worker_execution_mismatch')
    distributions = set()
    for row in intent['dependencies']:
        closed(row, ('distribution', 'version', 'package_root', 'files'))
        require(type(row['distribution']) is str and row['distribution'] and (type(row['version']) is str) and row['version'] and (type(row['files']) is list) and row['files'], 'worker_execution_mismatch')
        name = re.sub('[-_.]+', '-', row['distribution']).lower()
        require(name not in distributions, 'worker_execution_mismatch')
        distributions.add(name)
        validate_path(row['package_root'])
        require(any((Path(pin['path']).is_relative_to(row['package_root']) for pin in row['files'])), 'worker_execution_mismatch')
    pins = [*intent['source_pins'], intent['interpreter'], *intent['runtime_files'], *(pin for row in intent['dependencies'] for pin in row['files'])]
    for pin in pins:
        _pin(pin)
    require(len({pin['path'] for pin in pins}) == len(pins), 'worker_execution_mismatch')
    require(intent['interpreter']['path'] == str(root / 'runtime/python'), 'worker_execution_mismatch')
    source_root = root / 'source_snapshot'
    require(all((Path(pin['path']).is_relative_to(source_root) and Path(pin['path']).suffix == '.py' for pin in intent['source_pins'])) and str(source_root / 'gene_annotation_episode/fluorescence_result_worker.py') in {pin['path'] for pin in intent['source_pins']}, 'worker_execution_mismatch')
    require(all((Path(pin['path']).is_relative_to(Path(intent['python_home']) / 'lib') for pin in intent['runtime_files'])) and same(intent['environment'], _environment(root, intent['python_home'], intent['dependencies'])), 'worker_execution_mismatch')
    return deepcopy(intent)

def _controls(body, request, intent):
    root = Path(intent['plan']['directory'])
    closed(body, ('version', 'unit', 'command', 'cwd', 'stdout', 'stderr', 'paths', 'metadata', 'stage', 'started_at', 'started_monotonic_ns', 'boot_id', 'request_sha256'))
    require(body['version'] == native.VERSION and same(body['command'], intent['command']) and (body['cwd'] == str(root)) and (body['stage'] in ('prepared', 'submitting', 'released')) and (body['stdout'] == str(root / 'worker.stdout')) and (body['stderr'] == str(root / 'worker.stderr')), 'worker_execution_mismatch')
    require(type(body['unit']) is str and re.fullmatch('gene-local-job-[0-9a-f]{32}\\.service', body['unit']) and (type(body['request_sha256']) is str) and re.fullmatch('[0-9a-f]{64}', body['request_sha256']), 'worker_execution_mismatch')
    metadata = body['metadata']
    base = retained_metadata(intent['policy'])
    require(type(metadata) is dict and same({key: metadata.get(key) for key in base}, base) and (set(metadata) <= set(base) | {'verified_cgroup'}), 'worker_execution_mismatch')
    paths = body['paths']
    closed(paths, ('request', 'ready', 'release', 'status', 'result', 'launcher'))
    require(all((type(path) is str and Path(path).parent == root and (str(Path(path)) == path) for path in paths.values())), 'worker_execution_mismatch')
    request_name = Path(paths['request']).name
    require(re.fullmatch('\\.local-job-[0-9a-f]{32}\\.request', request_name), 'worker_execution_mismatch')
    token = request_name.removesuffix('.request')
    require(all((path == str(root / (token + '.' + name)) for name, path in paths.items())), 'worker_execution_mismatch')
    require(same(request, dict(command=intent['command'], cwd=str(root), file_bytes=POLICY['scratch_bytes'], ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None, env=intent['environment'])), 'worker_execution_mismatch')
    if body['stage'] == 'prepared':
        require(all((body[name] is None for name in ('started_at', 'started_monotonic_ns', 'boot_id'))), 'worker_execution_mismatch')
    else:
        require(type(body['started_at']) is str and bool(body['started_at']) and (type(body['started_monotonic_ns']) is int) and (body['started_monotonic_ns'] >= 0) and (type(body['boot_id']) is str) and bool(body['boot_id']), 'worker_execution_mismatch')
    return body

def validate_fluorescence_worker_execution(execution, *, plan, plan_file):
    plan = validate_fluorescence_worker_plan(plan)
    closed(execution, ('version', 'plan_file', 'intent', 'terminal', 'quiescent', 'policy', 'returncode', 'metadata', 'failure', 'handle_file', 'request_file', 'stdout_file', 'stderr_file', 'handle', 'request', 'request_raw'))
    require(execution['version'] == EXECUTION_VERSION and same(execution['plan_file'], plan_file) and same(plan_file, identity(canonical(plan) + b'\n', format=PLAN_VERSION)) and (execution['terminal'] is True) and (execution['quiescent'] is True) and retained_policy_matches(execution['policy']), 'worker_execution_mismatch')
    intent = _validate_intent(execution['intent'], plan)
    require(same(execution['policy'], intent['policy']), 'worker_execution_mismatch')
    body = _controls(execution['handle'], execution['request'], intent)
    require(type(execution['request_raw']) is str, 'worker_execution_mismatch')
    raw = execution['request_raw'].encode('utf-8')
    require(same(decode_json(raw), execution['request']) and hashlib.sha256(raw).hexdigest() == body['request_sha256'] == execution['request_file']['sha256'] and (len(raw) == execution['request_file']['size_bytes']), 'worker_execution_mismatch')
    formats = dict(plan_file=PLAN_VERSION, handle_file=native.VERSION, request_file='native_local_job_request', stdout_file='native_worker_stdout', stderr_file='native_worker_stderr')
    for name, format_ in formats.items():
        require(validate_file(execution[name])['format'] == format_, 'worker_execution_mismatch')
    meta = execution['metadata']
    expected_limits = retained_cgroup(execution['policy'])
    require(type(meta) is dict and same(meta.get('policy'), execution['policy']) and (type(meta.get('service_exit')) is dict) and same(meta.get('verified_cgroup'), expected_limits) and same(body['metadata'].get('verified_cgroup'), expected_limits) and all((same(meta.get(key), value) for key, value in body['metadata'].items())) and (meta.get('duration_measure') == 'systemd_service_wall_seconds'), 'worker_execution_mismatch')
    if execution['failure'] is None:
        require(type(execution['returncode']) is int and meta.get('native_returncode') == execution['returncode'] and (body['stage'] == 'released'), 'worker_execution_mismatch')
    else:
        closed(execution['failure'], ('code', 'phase', 'diagnostic', 'operational'))
        problem = execution['failure']
        require(execution['returncode'] is None and all((type(problem[key]) is str and problem[key] for key in ('code', 'phase'))) and (type(problem['operational']) is dict) and (problem['diagnostic'] is None or type(problem['diagnostic']) is dict), 'worker_execution_mismatch')
    canonical(execution)
    return deepcopy(execution)
