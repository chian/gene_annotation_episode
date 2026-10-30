"""Freeze current host code and run one bounded, replayable ATAC result worker.

This supplies byte custody and the existing native lifecycle. Receiving episode
authority, completion, and credit are separate host responsibilities.
"""
from __future__ import annotations

import ast
import fcntl
import importlib
import importlib.metadata
import os
from pathlib import Path
import shutil
import stat
import sys

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_file_capture import capture_native_file, capture_declared_native_files, retained_native_file, NativeFileCaptureError
from .native_atac_differential_contracts import POLICY, failure, unique_failures, _dependency_roots
from .native_atac_differential_driver import _regular, _directory, _writing, _immutable, _read_control, file_identity, confined_file, decode_json
from .atac_differential_result_contracts import PLAN_VERSION, RESULT_VERSION, require, validate_atac_result_record
from .atac_differential_result_worker import validate_atac_result_worker_plan, validate_atac_result_worker_result, worker_output_specs

WORKER_MODULE = 'gene_annotation_episode.atac_differential_result_worker'
_PACKAGES = {'jsonschema': 'jsonschema', 'attrs': 'attr', 'referencing': 'referencing',
    'rpds-py': 'rpds', 'jsonschema-specifications': 'jsonschema_specifications'}
_OPTIONAL = {'typing-extensions': 'typing_extensions', 'idna': 'idna', 'jsonpointer': 'jsonpointer',
    'fqdn': 'fqdn', 'rfc3987': 'rfc3987', 'rfc3986-validator': 'rfc3986_validator', 'rfc3987-syntax': 'rfc3987_syntax',
    'rfc3339-validator': 'rfc3339_validator', 'webcolors': 'webcolors', 'uri-template': 'uri_template',
    'isoduration': 'isoduration', 'lark': 'lark', 'arrow': 'arrow', 'python-dateutil': 'dateutil', 'six': 'six'}


def build_native_atac_worker_plan(*, directory, original_plan, bundle, files, selector,
        source_action_receipt_ref, writer_closure_receipt_ref, driver_state, failures):
    return validate_atac_result_worker_plan(dict(version=PLAN_VERSION, mode='native_result', directory=directory,
        original_plan=original_plan, bundle=bundle, files=files, selector=selector, source_action_receipt_ref=source_action_receipt_ref,
        writer_closure_receipt_ref=writer_closure_receipt_ref, driver_state=driver_state, failures=failures))


def build_saved_atac_worker_plan(*, directory, sheet_bundle, selector):
    return validate_atac_result_worker_plan(dict(version=PLAN_VERSION, mode='saved_sheet_recalculation',
        directory=directory, sheet_bundle=sheet_bundle, selector=selector))


def _source_closure(module_root, modules):
    root, paths, pending = Path(module_root), {}, [*modules, 'gene_annotation_episode.__init__']
    while pending:
        name = pending.pop()
        if name in paths:
            continue
        path = root / (name.replace('.', '/') + '.py')
        if not path.is_file() and (root / name.replace('.', '/') / '__init__.py').is_file():
            name += '.__init__'
            path = root / (name.replace('.', '/') + '.py')
        require(path.is_file(), 'native_dependency_unavailable')
        paths[name] = path
        package = name.rsplit('.', 1)[0]
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.ImportFrom):
                base = package.split('.')[:len(package.split('.')) - node.level + 1] if node.level else []
                imported = '.'.join([*base, *([node.module] if node.module else [])])
                if imported.startswith('gene_annotation_episode.'):
                    pending.append(imported)
                elif imported == 'gene_annotation_episode' and node.module is None:
                    pending.extend(imported + '.' + alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                pending.extend(alias.name for alias in node.names if alias.name.startswith('gene_annotation_episode.'))
    return paths


def _copy_exact(source, destination, *, executable=False):
    identity = file_identity(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(file_identity(destination) == identity and not destination.stat().st_mode & 0o222, 'native_dependency_unavailable')
    else:
        with _regular(source) as original, _writing(destination) as output:
            shutil.copyfileobj(original, output, length=1024 * 1024)
        if executable:
            destination.chmod(0o555)
    require(file_identity(destination) == identity, 'native_dependency_unavailable')
    return dict(path=str(destination), **identity)


def _dependencies():
    selected = dict(_PACKAGES)
    for module in selected.values():
        importlib.import_module(module)
    selected.update({name: module for name, module in _OPTIONAL.items() if module in sys.modules})
    result = []
    for distribution, module_name in selected.items():
        module = importlib.import_module(module_name)
        installed = importlib.metadata.distribution(distribution)
        files = []
        for entry in installed.files or ():
            path = Path(installed.locate_file(entry)).resolve(strict=True)
            if path.suffix not in ('.pyc', '.pyo') and path.is_file():
                files.append(dict(path=str(path), **file_identity(path)))
        require(files, 'native_dependency_unavailable')
        result.append(dict(distribution=distribution, version=installed.version,
            package_root=str(Path(module.__file__).resolve(strict=True).parent), files=sorted({r['path']: r for r in files}.values(), key=lambda r: r['path'])))
    return result


def _snapshot(plan, policy):
    directory = Path(plan['directory'])
    sources = _source_closure(Path(__file__).resolve().parents[1], [WORKER_MODULE])
    pins = []
    for name, source in sorted(sources.items()):
        check_scratch_budget(directory, policy, additional_bytes=source.stat().st_size)
        pins.append(_copy_exact(source, directory / 'source_snapshot' / (name.replace('.', '/') + '.py')))
    binary = Path(sys.executable).resolve(strict=True)
    check_scratch_budget(directory, policy, additional_bytes=binary.stat().st_size)
    interpreter = _copy_exact(binary, directory / 'runtime/python', executable=True)
    dependencies = _dependencies()
    roots = _dependency_roots({'dependencies': dependencies})
    environment = dict(PYTHONPATH=os.pathsep.join([str(directory / 'source_snapshot'), *roots]),
        PYTHONHOME=str(Path(sys.base_prefix).resolve(strict=True)), PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        TMPDIR=str(directory / 'tmp'), TMP=str(directory / 'tmp'), TEMP=str(directory / 'tmp'), XDG_CACHE_HOME=str(directory / 'cache'),
        PIP_CACHE_DIR=str(directory / 'cache/pip'))
    for name in ('tmp', 'cache/pip'):
        (directory / name).mkdir(parents=True, exist_ok=True)
    return dict(version='atac_worker_intent_v1', plan=plan, policy=POLICY,
        command=[interpreter['path'], '-B', '-S', '-m', WORKER_MODULE, str(directory / 'plan.json')],
        environment=environment, source_pins=pins, interpreter=interpreter, dependencies=dependencies)


def _verify_pins(intent):
    for pin in [*intent['source_pins'], intent['interpreter'], *(pin for row in intent['dependencies'] for pin in row['files'])]:
        require(file_identity(pin['path']) == {key: pin[key] for key in ('sha256', 'size_bytes')}, 'native_dependency_unavailable')


def _capture(store, directory, name, format_name):
    return capture_native_file(store, directory=str(directory), relative_path=name, format=format_name)


def _check_controls(body, request, intent):
    require(body['version'] == native.VERSION and body['command'] == intent['command'] and body['cwd'] == intent['plan']['directory']
        and body['metadata']['policy'] == POLICY and body['stage'] in ('prepared', 'submitting', 'released'), 'atac_worker_handle_mismatch')
    require(len(set(body['paths'].values())) == len(body['paths'])
        and all(Path(path).parent == Path(body['cwd']) for path in body['paths'].values()), 'atac_worker_handle_mismatch')
    require(request == dict(command=intent['command'], cwd=body['cwd'], file_bytes=POLICY['scratch_bytes'],
        ready_path=body['paths']['ready'], release_path=body['paths']['release'], result_path=body['paths']['result'],
        stdin_path=None, env=intent['environment']), 'atac_worker_request_mismatch')
    return body


def _check_handle(handle, intent):
    body = handle.read()
    with _regular(body['paths']['request']) as stream:
        request = decode_json(stream.read())
    require(file_identity(body['paths']['request'])['sha256'] == body['request_sha256'], 'atac_worker_request_mismatch')
    return _check_controls(body, request, intent)


def validate_prepared_atac_worker(store, value, *, plan):
    """Validate retained controls only; never refresh source or native inputs."""
    plan = validate_atac_result_worker_plan(plan)
    value = validate_atac_result_record('WorkerCapture', value)
    require(_read_control(retained_native_file(store, value['plan_file'])) == plan, 'atac_worker_plan_mismatch')
    execution = _read_control(retained_native_file(store, value['execution_receipt_file']))
    expected = {'version', 'plan_file', 'intent', 'terminal', 'quiescent', 'policy', 'returncode', 'metadata', 'failure',
                'handle_file', 'request_file', 'stdout_file', 'stderr_file'}
    require(set(execution) == expected and execution['version'] == 'atac_worker_execution_v1'
        and execution['plan_file'] == value['plan_file'] and execution['intent']['plan'] == plan
        and execution['terminal'] is True and execution['quiescent'] is True and execution['policy'] == POLICY, 'atac_worker_execution_mismatch')
    intent = execution['intent']
    require(set(intent) == {'version', 'plan', 'policy', 'command', 'environment', 'source_pins', 'interpreter', 'dependencies'}
        and intent['version'] == 'atac_worker_intent_v1' and intent['policy'] == POLICY
        and intent['command'] == [intent['interpreter']['path'], '-B', '-S', '-m', WORKER_MODULE, str(Path(plan['directory']) / 'plan.json')]
        and intent['source_pins'] and intent['dependencies'], 'atac_worker_intent_mismatch')
    # Lifecycle controls use their own ordinary JSON writer. Exact retained
    # identity authenticates those bytes; ATAC's canonical writer is not their
    # serialization contract.
    with _regular(retained_native_file(store, execution['handle_file'])) as stream:
        body = decode_json(stream.read())
    request_path = retained_native_file(store, execution['request_file'])
    with _regular(request_path) as stream:
        request = decode_json(stream.read())
    require(execution['request_file']['sha256'] == body['request_sha256'], 'atac_worker_request_mismatch')
    _check_controls(body, request, intent)
    if value['result'] is not None:
        require(value['worker_result_file'] is not None, 'atac_worker_result_unavailable')
        result = validate_atac_result_worker_result(_read_control(retained_native_file(store, value['worker_result_file'])))
        require(result == value['result'] and result['mode'] == plan['mode'] and result['parameters'] == plan['selector']['parameters'], 'atac_worker_result_mismatch')
        specs = worker_output_specs(plan)
        require(len(result['outputs']) == len(specs) == len(value['outputs']), 'atac_worker_outputs_mismatch')
        for row, captured, spec in zip(result['outputs'], value['outputs'], specs):
            require(all(row[key] == captured[key] == spec[key] for key in ('role', 'table_key'))
                and all(row['declaration'][k] == spec[k] for k in ('relative_path', 'format'))
                and row['declaration'] == captured['capture']['declared'], 'atac_worker_outputs_mismatch')
            actual = captured['capture']['observed']
            equal = actual is not None and all(actual[k] == row['declaration'][k] for k in ('sha256', 'size_bytes', 'format'))
            outcome = captured['capture']['outcome']
            require((outcome == 'verified' and row['declaration']['state'] == 'present' and equal and captured['capture']['failure'] is None)
                or (outcome == 'declared_absent' and row['declaration']['state'] == 'absent' and actual is None and captured['capture']['failure'] is None)
                or (outcome == 'unavailable' and row['declaration']['state'] == 'present' and actual is None and captured['capture']['failure'] == 'capture_file_unavailable')
                or (outcome == 'digest_mismatch' and row['declaration']['state'] == 'present' and actual is not None and not equal and captured['capture']['failure'] == 'capture_file_digest_mismatch'), 'atac_worker_capture_mismatch')
    else:
        require(value['outputs'] == [], 'atac_worker_outputs_mismatch')
    return value


def prepare_atac_result_worker(store, *, plan, policy):
    plan = validate_atac_result_worker_plan(plan)
    require(type(policy) is LocalJobPolicy and policy.to_dict() == POLICY, 'atac_worker_policy_mismatch')
    directory = _directory(plan['directory'])
    directory.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(confined_file(directory, '.preparation.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), 'a+b') as lock:
        require(stat.S_ISREG(os.fstat(lock.fileno()).st_mode), 'invalid_output_path')
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = directory / 'prepared.json'
        if saved.exists():
            return validate_prepared_atac_worker(store, _read_control(saved), plan=plan)
        _immutable(directory / 'plan.json', plan)
        intent_path = directory / 'intent.json'
        if intent_path.exists():
            intent = _read_control(intent_path)
            require(intent['plan'] == plan and intent['policy'] == POLICY, 'atac_worker_intent_mismatch')
        else:
            require(not (directory / 'worker.handle.json').exists(), 'atac_worker_unowned_handle')
            inputs = ([plan['sheet_bundle']['sheet'], *plan['sheet_bundle']['tables']] if plan['mode'] != 'native_result'
                      else [plan['bundle'], *(r['retained'] for r in plan['files'])])
            for retained in inputs:
                if retained is not None:
                    file = retained['file']
                    require(retained['path'] == str(store.path / 'artifacts' / file['sha256'][:2] / file['sha256']),
                        'atac_worker_input_custody_mismatch')
                    # The host authenticates the received bundle. Missing or
                    # changed saved tables must reach the finite reader so the
                    # other supplied streams and valid prefixes survive. The
                    # sheet itself and all original native captures still
                    # require current complete byte custody before dispatch.
                    if plan['mode'] == 'native_result' or retained is inputs[0]:
                        require(str(retained_native_file(store, file)) == retained['path'], 'atac_worker_input_custody_mismatch')
            intent = _snapshot(plan, policy)
            _immutable(intent_path, intent)
        plan_file = _capture(store, directory, 'plan.json', PLAN_VERSION)
        execution_path = directory / 'execution.json'
        handle = native.NativeJobHandle(directory / 'worker.handle.json')
        if not execution_path.exists():
            _verify_pins(intent)
            if not handle.path.exists():
                native.prepare_job(intent['command'], cwd=directory, policy=policy, handle_path=handle.path,
                    stdout_path=directory / 'worker.stdout', stderr_path=directory / 'worker.stderr', env=intent['environment'])
            _check_handle(handle, intent)
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
            require(view['terminal'] and view['quiescent'], 'atac_worker_not_closed')
            _verify_pins(intent)
            body = _check_handle(handle, intent)
            execution = dict(version='atac_worker_execution_v1', plan_file=plan_file, intent=intent, terminal=True, quiescent=True,
                policy=POLICY, returncode=outcome.returncode if outcome else None, metadata=view['metadata'], failure=problem,
                handle_file=_capture(store, directory, 'worker.handle.json', native.VERSION),
                request_file=_capture(store, directory, Path(body['paths']['request']).name, 'native_local_job_request'),
                stdout_file=_capture(store, directory, 'worker.stdout', 'native_worker_stdout'), stderr_file=_capture(store, directory, 'worker.stderr', 'native_worker_stderr'))
            _immutable(execution_path, execution)
        execution = _read_control(execution_path)
        execution_file = _capture(store, directory, 'execution.json', 'atac_worker_execution_v1')
        problems, result, result_file, outputs = [], None, None, []
        if execution['failure'] is not None or execution['returncode'] != 0:
            problems.append(failure('resource_limit' if execution['failure'] and execution['failure']['code'] == 'local_job_resource_limit' else 'native_nonzero_exit',
                'execution', requirement='original_native_outcome'))
        try:
            result_file = _capture(store, directory, 'worker-result.json', RESULT_VERSION)
            result = validate_atac_result_worker_result(_read_control(retained_native_file(store, result_file)))
            require(result['mode'] == plan['mode'] and result['parameters'] == plan['selector']['parameters'], 'atac_worker_result_mismatch')
        except NativeFileCaptureError as error:
            if error.code != 'capture_file_unavailable':
                raise
            problems.append(failure('worker_output_unavailable', 'capture', field_path='/worker_result', requirement='requested_selected_field'))
        except ValueError:
            result = None
            problems.append(failure('original_attempt_mismatch', 'capture', field_path='/worker_result', requirement='matching_file_identity'))
        if result is not None:
            captures = capture_declared_native_files(store, directory=str(directory), declarations=[r['declaration'] for r in result['outputs']])
            outputs = [dict(role=row['role'], table_key=row['table_key'], capture=captured) for row, captured in zip(result['outputs'], captures)]
            for row in outputs:
                if row['capture']['outcome'] not in ('verified', 'declared_absent'):
                    problems.append(failure('artifact_digest_mismatch' if row['capture']['outcome'] == 'digest_mismatch' else 'worker_output_unavailable',
                        'capture', binding_key=row['table_key'], field_path='/outputs/' + row['role'], requirement='matching_file_identity'))
        value = validate_prepared_atac_worker(store, dict(version='atac_differential_worker_capture_v1', plan_file=plan_file,
            execution_receipt_file=execution_file, worker_result_file=result_file, result=result, outputs=outputs, failures=unique_failures(problems)), plan=plan)
        _immutable(saved, value)
        return value


__all__ = ['build_native_atac_worker_plan', 'build_saved_atac_worker_plan', 'prepare_atac_result_worker', 'validate_prepared_atac_worker']
