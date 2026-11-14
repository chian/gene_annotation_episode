"""Freeze and execute one finite NMF result worker under existing local limits.

This adapter retains exact source, dependency, interpreter and stdlib pins.
Completed replay checks the original controls, never today's runtime or native
producer, and recovery resumes the same durable local_jobs handle.
"""
import hashlib
import os
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a108 import native_lifecycle as native
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.expression_nmf_common import digest
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.expression_nmf_result_contracts import require, validate_file
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_expression_nmf_contracts import POLICY
WORKER_MODULE = 'gene_annotation_episode.expression_nmf_result_worker'
EXECUTION_VERSION = 'expression_nmf_worker_execution_v1'

def _validate_intent(intent, plan):
    require(type(intent) is dict and set(intent) == {'version', 'plan', 'policy', 'command', 'environment', 'source_pins', 'interpreter', 'dependencies', 'python_version', 'python_home', 'runtime_files'} and (intent['version'] == 'expression_nmf_worker_intent_v1') and (digest(intent['plan']) == digest(plan)) and (intent['policy'] == POLICY), 'nmf_worker_intent_mismatch')
    root = Path(plan['directory'])
    require(intent['command'] == [str(root / 'runtime/python'), '-B', '-S', '-m', WORKER_MODULE, str(root / 'plan.json')] and intent['interpreter']['path'] == str(root / 'runtime/python') and intent['source_pins'] and intent['dependencies'] and intent['runtime_files'], 'nmf_worker_runtime_missing')
    pins = [*intent['source_pins'], intent['interpreter'], *intent['runtime_files'], *(pin for row in intent['dependencies'] for pin in row['files'])]
    for pin in pins:
        require(type(pin) is dict and set(pin) == {'path', 'sha256', 'size_bytes'} and Path(pin['path']).is_absolute(), 'nmf_worker_pin_invalid')
        validate_file({'artifact_ref': 'artifact_' + pin['sha256'], 'sha256': pin['sha256'], 'size_bytes': pin['size_bytes'], 'format': 'runtime_file'})
    require(len({p['path'] for p in pins}) == len(pins), 'nmf_worker_duplicate_pin')
    source_root = root / 'source_snapshot'
    require(all((Path(pin['path']).is_relative_to(source_root) for pin in intent['source_pins'])) and str(source_root / 'gene_annotation_episode/expression_nmf_result_worker.py') in {p['path'] for p in intent['source_pins']}, 'nmf_worker_source_missing')
    require(all((Path(pin['path']).is_relative_to(Path(intent['python_home']) / 'lib') for pin in intent['runtime_files'])) and intent['environment']['PYTHONHOME'] == intent['python_home'] and (intent['environment']['PYTHONPATH'].split(os.pathsep)[0] == str(source_root)), 'nmf_worker_runtime_mismatch')
    return intent

def _controls(body, request, intent):
    root = Path(intent['plan']['directory'])
    require(body.get('version') == native.VERSION and body.get('command') == intent['command'] and (body.get('cwd') == str(root)) and (body.get('metadata', {}).get('policy') == POLICY) and (body.get('stage') in ('prepared', 'submitting', 'released')) and (body.get('stdout') == str(root / 'worker.stdout')) and (body.get('stderr') == str(root / 'worker.stderr')), 'nmf_worker_handle_mismatch')
    paths = body['paths']
    require(set(paths) == {'request', 'ready', 'release', 'status', 'result', 'launcher'} and len(set(paths.values())) == len(paths) and all((Path(p).parent == root for p in paths.values())), 'nmf_worker_handle_mismatch')
    require(request == dict(command=intent['command'], cwd=str(root), file_bytes=POLICY['scratch_bytes'], ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None, env=intent['environment']), 'nmf_worker_request_mismatch')
    return body

def validate_worker_execution(execution, *, plan, plan_file):
    require(type(execution) is dict and set(execution) == {'version', 'plan_file', 'intent', 'terminal', 'quiescent', 'policy', 'returncode', 'metadata', 'failure', 'handle_file', 'request_file', 'stdout_file', 'stderr_file', 'handle', 'request', 'request_raw'}, 'nmf_worker_execution_mismatch')
    require(execution['version'] == EXECUTION_VERSION and execution['plan_file'] == plan_file and (execution['terminal'] is True) and (execution['quiescent'] is True) and (execution['policy'] == POLICY), 'nmf_worker_execution_mismatch')
    intent = _validate_intent(execution['intent'], plan)
    body = _controls(execution['handle'], execution['request'], intent)
    raw = execution['request_raw'].encode('utf-8')
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_expression_nmf_storage import decode_json
    require(decode_json(raw) == execution['request'] and hashlib.sha256(raw).hexdigest() == body['request_sha256'] == execution['request_file']['sha256'] and (len(raw) == execution['request_file']['size_bytes']), 'nmf_worker_request_mismatch')
    meta = execution['metadata']
    require(type(meta) is dict and meta.get('policy') == POLICY and (type(meta.get('service_exit')) is dict) and (meta.get('verified_cgroup') == {'memory_max': POLICY['memory_bytes'], 'memory_swap_max': 0, 'kill_mode': 'control-group', 'oom_policy': 'kill'}), 'nmf_worker_allocation_mismatch')
    if execution['failure'] is None:
        require(type(execution['returncode']) is int and meta['native_returncode'] == execution['returncode'], 'nmf_worker_exit_mismatch')
    else:
        require(execution['returncode'] is None and type(execution['failure']) is dict and (set(execution['failure']) == {'code', 'phase', 'diagnostic', 'operational'}), 'nmf_worker_exit_mismatch')
    for name in ('plan_file', 'handle_file', 'request_file', 'stdout_file', 'stderr_file'):
        validate_file(execution[name])
    return execution
