"""Freeze and execute one finite NMF result worker under existing local limits.

This adapter retains exact source, dependency, interpreter and stdlib pins.
Completed replay checks the original controls, never today's runtime or native
producer, and recovery resumes the same durable local_jobs handle.
"""
from copy import deepcopy
import fcntl
import hashlib
import os
from pathlib import Path
import sys

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .expression_nmf_common import canonical, digest, unique_issues
from .expression_nmf_result_contracts import failure, require, validate_file, validate_issue
from .expression_nmf_result_worker import (OUTPUTS, PLAN_VERSION, RESULT_VERSION,
    validate_expression_nmf_worker_plan, validate_expression_nmf_worker_result)
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_expression_nmf_contracts import POLICY
from .native_expression_nmf_storage import directory, file_pin, immutable_json, read_json, regular
from .native_file_capture import (NativeFileCaptureError, capture_native_file, capture_declared_native_files, retained_native_file)
from .native_atac_differential_preparation import _source_closure, _dependencies, _copy_exact

WORKER_MODULE = 'gene_annotation_episode.expression_nmf_result_worker'
EXECUTION_VERSION = 'expression_nmf_worker_execution_v1'
CAPTURE_VERSION = 'expression_nmf_worker_capture_v1'


def build_native_expression_nmf_worker_plan(*, directory, original_plan, capture, selector):
    return validate_expression_nmf_worker_plan(dict(version=PLAN_VERSION, mode='native_result', directory=directory,
        original_plan=original_plan, capture=capture, selector=selector))


def build_saved_expression_nmf_worker_plan(*, directory, sheet, selector):
    return validate_expression_nmf_worker_plan(dict(version=PLAN_VERSION, mode='saved_sheet_recalculation',
        directory=directory, sheet=sheet, selector=selector))


def _snapshot(plan, policy):
    root = Path(plan['directory'])
    sources = _source_closure(Path(__file__).resolve().parents[1], [WORKER_MODULE])
    pins = []
    for name, path in sorted(sources.items()):
        check_scratch_budget(root, policy, additional_bytes=path.stat().st_size)
        pins.append(_copy_exact(path, root / 'source_snapshot' / (name.replace('.', '/') + '.py')))
    binary = Path(sys.executable).resolve(strict=True)
    check_scratch_budget(root, policy, additional_bytes=binary.stat().st_size)
    interpreter = _copy_exact(binary, root / 'runtime/python', executable=True)
    dependencies = _dependencies()
    # Distribution entries can name scripts outside site-packages. The actual
    # imported package root supplies the import path.
    from .native_atac_differential_contracts import _dependency_roots
    roots = _dependency_roots({'dependencies': dependencies})
    home = Path(sys.base_prefix).resolve(strict=True)
    stdlib = home / 'lib' / ('python%d.%d' % sys.version_info[:2])
    runtime_files = [file_pin(path) for path in sorted(stdlib.rglob('*')) if path.is_file()
        and not any(part in ('site-packages', 'dist-packages', '__pycache__') for part in path.relative_to(stdlib).parts)
        and path.suffix not in ('.pyc', '.pyo')]
    require(runtime_files, 'nmf_worker_stdlib_missing')
    environment = dict(PYTHONPATH=os.pathsep.join([str(root / 'source_snapshot'), *roots]), PYTHONHOME=str(home),
        PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        TMPDIR=str(root), TMP=str(root), TEMP=str(root), XDG_CACHE_HOME=str(root / 'cache'),
        PIP_CACHE_DIR=str(root / 'cache/pip'), OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    (root / 'cache/pip').mkdir(parents=True, exist_ok=True)
    return dict(version='expression_nmf_worker_intent_v1', plan=plan, policy=deepcopy(POLICY),
        command=[interpreter['path'], '-B', '-S', '-m', WORKER_MODULE, str(root / 'plan.json')],
        environment=environment, source_pins=pins, interpreter=interpreter,
        dependencies=dependencies, python_version=sys.version, python_home=str(home), runtime_files=runtime_files)


def _validate_intent(intent, plan):
    require(type(intent) is dict and set(intent) == {'version', 'plan', 'policy', 'command', 'environment',
        'source_pins', 'interpreter', 'dependencies', 'python_version', 'python_home', 'runtime_files'}
        and intent['version'] == 'expression_nmf_worker_intent_v1' and digest(intent['plan']) == digest(plan)
        and intent['policy'] == POLICY, 'nmf_worker_intent_mismatch')
    root = Path(plan['directory'])
    require(intent['command'] == [str(root / 'runtime/python'), '-B', '-S', '-m', WORKER_MODULE, str(root / 'plan.json')]
        and intent['interpreter']['path'] == str(root / 'runtime/python') and intent['source_pins']
        and intent['dependencies'] and intent['runtime_files'], 'nmf_worker_runtime_missing')
    pins = [*intent['source_pins'], intent['interpreter'], *intent['runtime_files'],
        *(pin for row in intent['dependencies'] for pin in row['files'])]
    for pin in pins:
        require(type(pin) is dict and set(pin) == {'path', 'sha256', 'size_bytes'} and Path(pin['path']).is_absolute(),
            'nmf_worker_pin_invalid')
        validate_file({'artifact_ref': 'artifact_' + pin['sha256'], 'sha256': pin['sha256'],
            'size_bytes': pin['size_bytes'], 'format': 'runtime_file'})
    require(len({p['path'] for p in pins}) == len(pins), 'nmf_worker_duplicate_pin')
    source_root = root / 'source_snapshot'
    require(all(Path(pin['path']).is_relative_to(source_root) for pin in intent['source_pins'])
        and str(source_root / 'gene_annotation_episode/expression_nmf_result_worker.py') in {p['path'] for p in intent['source_pins']},
        'nmf_worker_source_missing')
    require(all(Path(pin['path']).is_relative_to(Path(intent['python_home']) / 'lib') for pin in intent['runtime_files'])
        and intent['environment']['PYTHONHOME'] == intent['python_home']
        and intent['environment']['PYTHONPATH'].split(os.pathsep)[0] == str(source_root), 'nmf_worker_runtime_mismatch')
    return intent


def _verify_pins(intent):
    for pin in [*intent['source_pins'], intent['interpreter'], *intent['runtime_files'],
            *(pin for row in intent['dependencies'] for pin in row['files'])]:
        require(file_pin(pin['path']) == pin, 'nmf_worker_runtime_changed')


def _capture(store, root, name, format_):
    return capture_native_file(store, directory=str(root), relative_path=name, format=format_)


def _controls(body, request, intent):
    root = Path(intent['plan']['directory'])
    require(body.get('version') == native.VERSION and body.get('command') == intent['command']
        and body.get('cwd') == str(root) and body.get('metadata', {}).get('policy') == POLICY
        and body.get('stage') in ('prepared', 'submitting', 'released')
        and body.get('stdout') == str(root / 'worker.stdout') and body.get('stderr') == str(root / 'worker.stderr'),
        'nmf_worker_handle_mismatch')
    paths = body['paths']
    require(set(paths) == {'request', 'ready', 'release', 'status', 'result', 'launcher'}
        and len(set(paths.values())) == len(paths) and all(Path(p).parent == root for p in paths.values()), 'nmf_worker_handle_mismatch')
    require(request == dict(command=intent['command'], cwd=str(root), file_bytes=POLICY['scratch_bytes'],
        ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None,
        env=intent['environment']), 'nmf_worker_request_mismatch')
    return body


def validate_worker_execution(execution, *, plan, plan_file):
    require(type(execution) is dict and set(execution) == {'version', 'plan_file', 'intent', 'terminal', 'quiescent',
        'policy', 'returncode', 'metadata', 'failure', 'handle_file', 'request_file', 'stdout_file', 'stderr_file',
        'handle', 'request', 'request_raw'}, 'nmf_worker_execution_mismatch')
    require(execution['version'] == EXECUTION_VERSION and execution['plan_file'] == plan_file
        and execution['terminal'] is True and execution['quiescent'] is True and execution['policy'] == POLICY,
        'nmf_worker_execution_mismatch')
    intent = _validate_intent(execution['intent'], plan)
    body = _controls(execution['handle'], execution['request'], intent)
    raw = execution['request_raw'].encode('utf-8')
    from .native_expression_nmf_storage import decode_json
    require(decode_json(raw) == execution['request'] and hashlib.sha256(raw).hexdigest() == body['request_sha256']
        == execution['request_file']['sha256'] and len(raw) == execution['request_file']['size_bytes'], 'nmf_worker_request_mismatch')
    meta = execution['metadata']
    require(type(meta) is dict and meta.get('policy') == POLICY and type(meta.get('service_exit')) is dict
        and meta.get('verified_cgroup') == {'memory_max': POLICY['memory_bytes'], 'memory_swap_max': 0,
            'kill_mode': 'control-group', 'oom_policy': 'kill'}, 'nmf_worker_allocation_mismatch')
    if execution['failure'] is None:
        require(type(execution['returncode']) is int and meta['native_returncode'] == execution['returncode'], 'nmf_worker_exit_mismatch')
    else:
        require(execution['returncode'] is None and type(execution['failure']) is dict and
            set(execution['failure']) == {'code', 'phase', 'diagnostic', 'operational'}, 'nmf_worker_exit_mismatch')
    for name in ('plan_file', 'handle_file', 'request_file', 'stdout_file', 'stderr_file'):
        validate_file(execution[name])
    return execution


def validate_prepared_expression_nmf_worker(store, value, *, plan):
    plan = validate_expression_nmf_worker_plan(plan)
    require(type(value) is dict and set(value) == {'version', 'plan_file', 'execution_receipt_file',
        'worker_result_file', 'result', 'outputs', 'failures'} and value['version'] == CAPTURE_VERSION, 'nmf_worker_capture_mismatch')
    require(read_json(retained_native_file(store, value['plan_file'])) == plan, 'nmf_worker_plan_mismatch')
    execution = read_json(retained_native_file(store, value['execution_receipt_file']))
    validate_worker_execution(execution, plan=plan, plan_file=value['plan_file'])
    require(read_json(retained_native_file(store, execution['handle_file'])) == execution['handle'], 'nmf_worker_handle_mismatch')
    require(retained_native_file(store, execution['request_file']).read_bytes().decode('utf-8') == execution['request_raw'], 'nmf_worker_request_mismatch')
    result = value['result']
    if result is None:
        require(value['outputs'] == [], 'nmf_worker_outputs_mismatch')
    else:
        validate_expression_nmf_worker_result(result)
        require(read_json(retained_native_file(store, value['worker_result_file'])) == result
            and result['plan_sha256'] == digest(plan) and result['selector'] == plan['selector'], 'nmf_worker_result_mismatch')
        require(len(value['outputs']) == len(OUTPUTS), 'nmf_worker_outputs_mismatch')
        for declaration, captured in zip(result['outputs'], value['outputs']):
            require(set(captured) == {'declared', 'observed', 'outcome', 'failure'}
                and captured['declared'] == declaration['declaration'], 'nmf_worker_capture_mismatch')
            d, observed = captured['declared'], captured['observed']
            if observed is not None:
                retained_native_file(store, observed)
            equal = observed is not None and all(observed[k] == d[k] for k in ('sha256', 'size_bytes', 'format'))
            state = captured['outcome']
            require((state == 'verified' and d['state'] == 'present' and equal and captured['failure'] is None)
                or (state == 'declared_absent' and d['state'] == 'absent' and observed is None and captured['failure'] is None)
                or (state == 'unavailable' and d['state'] == 'present' and observed is None and captured['failure'] == 'capture_file_unavailable')
                or (state == 'digest_mismatch' and d['state'] == 'present' and observed is not None and not equal
                    and captured['failure'] == 'capture_file_digest_mismatch'), 'nmf_worker_capture_mismatch')
    for row in value['failures']:
        validate_issue(row)
    return deepcopy(value)


def prepare_expression_nmf_result_worker(store, *, plan, policy):
    plan = validate_expression_nmf_worker_plan(plan)
    require(type(policy) is LocalJobPolicy and policy.to_dict() == POLICY, 'nmf_worker_policy_mismatch')
    root = directory(plan['directory'])
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.preparation.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        saved = root / 'capture.json'
        if saved.exists():
            return validate_prepared_expression_nmf_worker(store, read_json(saved), plan=plan)
        immutable_json(root / 'plan.json', plan)
        intent_path = root / 'intent.json'
        if intent_path.exists():
            intent = _validate_intent(read_json(intent_path), plan)
        else:
            require(not (root / 'worker.handle.json').exists(), 'nmf_worker_unowned_handle')
            operands = ([plan['sheet']] if plan['mode'] == 'saved_sheet_recalculation' else
                [r['retained'] for r in plan['capture']['files']])
            for retained in operands:
                if retained is not None:
                    require(str(retained_native_file(store, retained['file'])) == retained['path'], 'nmf_worker_operand_path_mismatch')
            intent = _validate_intent(_snapshot(plan, policy), plan)
            immutable_json(intent_path, intent)
        plan_file = _capture(store, root, 'plan.json', PLAN_VERSION)
        execution_path = root / 'execution.json'
        handle = native.NativeJobHandle(root / 'worker.handle.json')
        if not execution_path.exists():
            _verify_pins(intent)
            if not handle.path.exists():
                native.prepare_job(intent['command'], cwd=root, policy=policy, handle_path=handle.path,
                    stdout_path=root / 'worker.stdout', stderr_path=root / 'worker.stderr', env=intent['environment'])
            body = handle.read()
            _controls(body, read_json(body['paths']['request']), intent)
            require(file_pin(body['paths']['request'])['sha256'] == body['request_sha256'], 'nmf_worker_request_mismatch')
            native.resume_start(handle)
            outcome, problem = None, None
            try:
                outcome = native.wait_job(handle)
            except AcquisitionError as error:
                view = native.status(handle)
                if not view['terminal'] or not view['quiescent']:
                    raise
                problem = dict(code=error.code, phase=error.phase, diagnostic=error.diagnostic, operational=error.operational)
            view = native.status(handle)
            require(view['terminal'] and view['quiescent'], 'nmf_worker_not_closed')
            _verify_pins(intent)
            body = handle.read()
            with regular(body['paths']['request']) as source:
                request_raw = source.read().decode('utf-8')
            execution = dict(version=EXECUTION_VERSION, plan_file=plan_file, intent=intent, terminal=True, quiescent=True,
                policy=deepcopy(POLICY), returncode=outcome.returncode if outcome else None, metadata=view['metadata'], failure=problem,
                handle_file=_capture(store, root, 'worker.handle.json', native.VERSION),
                request_file=_capture(store, root, Path(body['paths']['request']).name, 'native_local_job_request'),
                stdout_file=_capture(store, root, 'worker.stdout', 'native_worker_stdout'),
                stderr_file=_capture(store, root, 'worker.stderr', 'native_worker_stderr'),
                handle=body, request=read_json(body['paths']['request']), request_raw=request_raw)
            validate_worker_execution(execution, plan=plan, plan_file=plan_file)
            immutable_json(execution_path, execution)
        execution = read_json(execution_path)
        execution_file = _capture(store, root, 'execution.json', EXECUTION_VERSION)
        failures, result, result_file, outputs = [], None, None, []
        if execution['failure'] is not None or execution['returncode'] != 0:
            failures.append(failure('worker_resource_failure' if execution['failure'] and
                execution['failure']['code'] == 'local_job_resource_limit' else 'worker_nonzero_exit', 'worker'))
        try:
            result_file = _capture(store, root, 'worker-result.json', RESULT_VERSION)
            result = validate_expression_nmf_worker_result(read_json(retained_native_file(store, result_file)))
            require(result['plan_sha256'] == digest(plan) and result['selector'] == plan['selector'], 'nmf_worker_result_mismatch')
        except NativeFileCaptureError as error:
            if error.code != 'capture_file_unavailable':
                raise
            failures.append(failure('worker_output_unavailable', 'worker', field='result'))
        except (ValueError, KeyError, TypeError):
            result = None
            failures.append(failure('worker_output_malformed', 'worker', field='result'))
        if result is not None:
            outputs = capture_declared_native_files(store, directory=str(root), declarations=[row['declaration'] for row in result['outputs']])
            for spec, captured in zip(OUTPUTS, outputs):
                if captured['outcome'] not in ('verified', 'declared_absent'):
                    failures.append(failure('retained_artifact_mismatch' if captured['outcome'] == 'digest_mismatch'
                        else 'worker_output_unavailable', 'capture', field=spec[0]))
        value = validate_prepared_expression_nmf_worker(store, dict(version=CAPTURE_VERSION, plan_file=plan_file,
            execution_receipt_file=execution_file, worker_result_file=result_file, result=result, outputs=outputs,
            failures=unique_issues(failures)), plan=plan)
        immutable_json(saved, value)
        return value
