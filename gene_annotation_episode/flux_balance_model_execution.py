"""Durable execution of one explicitly selected model worker, without Store."""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import subprocess

from .acquisition import AcquisitionError
from .execution_contracts import canonical
from .flux_balance_model_tools import validate_flux_balance_model_result
from .flux_balance_model_worker import WORKER_MODULE, validate_flux_balance_model_worker_request
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import MolecularOperationUnpublished
from . import native_lifecycle as native
from .native_flux_balance_contracts import ATTEMPT_DIRECTORY_NAME, POLICY, flux_balance_environment, path_value
from .native_flux_balance_storage import confined_file, directory, file_pin, immutable_json, read_bytes, read_json


VERSION = 'ordinary_flux_balance_model_execution_v1'
SELECTION_VERSION = 'ordinary_flux_balance_model_selection_v1'


def _require(condition, code):
    if not condition:
        raise ValueError('fba_model_execution_' + code)


def _same(left, right):
    return canonical(left) == canonical(right)


def _selection(request, *, model_path, root, software, policy):
    _require(type(policy) is LocalJobPolicy and _same(policy.to_dict(), POLICY), 'policy_invalid')
    root = Path(path_value(str(root), absolute=True))
    value = validate_flux_balance_model_worker_request({'request': request, 'model_path': str(model_path),
        'output_directory': str(root / 'model-output'), 'software': software})
    protected = [PurePosixPath(value['model_path']), PurePosixPath(value['software']['python_home']),
        PurePosixPath(value['software']['module_root']),
        *(PurePosixPath(path) for path in value['software']['dependency_roots']),
        *(PurePosixPath(pin['path']) for pin in [value['software']['python'],
            *value['software']['implementation_files'], *value['software']['runtime_files'],
            *value['software']['solver_runtime_files']])]
    _require(all(not path.is_relative_to(root) and not root.is_relative_to(path)
        for path in protected), 'input_output_overlap')
    return {'version': SELECTION_VERSION, 'request': value,
        'command': [value['software']['python']['path'], '-B', '-S', '-m', WORKER_MODULE,
            str(root / 'request.json'), str(root / 'result.json')],
        'cwd': str(root), 'environment': flux_balance_environment(value['software'],
            lifecycle_directory=str(root), attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME)),
        'policy': policy.to_dict()}


def _verify_selected_software(selected):
    software = selected['request']['software']
    for pin in [software['python'], *software['implementation_files'],
            *software['runtime_files'], *software['solver_runtime_files']]:
        _require(_same(file_pin(pin['path']), pin), 'selected_software_changed')


def _validate_handle(handle, selected, root):
    body = handle.read()
    paths = body.get('paths')
    _require(type(paths) is dict and set(paths) == {
        'request', 'ready', 'release', 'status', 'result', 'launcher'}, 'native_handle_conflict')
    request_path = Path(path_value(paths['request'], absolute=True))
    token = request_path.name.removesuffix('.request')
    _require(re.fullmatch(r'\.local-job-[a-f0-9]{32}', token) is not None
        and all(path == str(root / (token + '.' + name)) for name, path in paths.items()), 'native_handle_conflict')
    for path in paths.values():
        confined_file(root, Path(path).name)
    raw = read_bytes(request_path)
    expected = {'command': selected['command'], 'cwd': str(root),
        'file_bytes': selected['policy']['scratch_bytes'], 'ready_path': paths['ready'],
        'release_path': paths['release'], 'result_path': paths['result'],
        'stdin_path': None, 'env': selected['environment']}
    _require(body.get('version') == native.VERSION
        and re.fullmatch(r'gene-local-job-[a-f0-9]{32}\.service', body.get('unit', '')) is not None
        and body.get('stage') in {'prepared', 'submitting', 'released'}
        and body.get('command') == selected['command'] and body.get('cwd') == str(root)
        and body.get('stdout') == str(root / 'stdout') and body.get('stderr') == str(root / 'stderr')
        and _same(body.get('metadata', {}).get('policy'), selected['policy'])
        and hashlib.sha256(raw).hexdigest() == body.get('request_sha256')
        and _same(read_json(request_path), expected), 'native_handle_conflict')
    return body


def _retained_result(path, selected):
    try:
        value = validate_flux_balance_model_result(read_json(path))
        _require(_same(value['request'], selected['request']['request']), 'result_request_conflict')
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return None
    return value


def _observation(handle):
    try:
        return native.status(handle)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        raise MolecularOperationUnpublished('fba_model_original_attempt_unconfirmed') from error


def run_selected_flux_balance_model(request, *, model_path, root, software, policy, cancel_event=None):
    """Execute or observe only the original handle; caller owns action authority."""
    selected = _selection(request, model_path=model_path, root=root, software=software, policy=policy)
    root = directory(root, create=True)
    fixed = ('selection.json', 'request.json', 'result.json', 'native-handle.json', 'stdout', 'stderr')
    for name in fixed:
        confined_file(root, name)
    selection_path, request_path = root / 'selection.json', root / 'request.json'
    result_path, handle_path = root / 'result.json', root / 'native-handle.json'
    if selection_path.exists():
        _require(_same(read_json(selection_path), selected), 'original_selection_conflict')
    else:
        _require(not any(root.iterdir()), 'original_selection_missing')
        immutable_json(selection_path, selected)
    if request_path.exists():
        _require(_same(read_json(request_path), selected['request']), 'original_request_conflict')
    else:
        _require(not handle_path.exists(), 'original_request_missing')
        immutable_json(request_path, selected['request'])
    if handle_path.exists():
        handle = native.NativeJobHandle(handle_path)
        _validate_handle(handle, selected, root)
    else:
        _require(set(path.name for path in root.iterdir()) <= {'selection.json', 'request.json'},
            'original_handle_missing')
        _verify_selected_software(selected)
        directory(root / ATTEMPT_DIRECTORY_NAME / 'cache/pip', create=True)
        handle = native.prepare_job(selected['command'], cwd=root, policy=policy, handle_path=handle_path,
            stdout_path=root / 'stdout', stderr_path=root / 'stderr', env=selected['environment'])
        _validate_handle(handle, selected, root)
    job, failure = None, None
    try:
        observed = _observation(handle)
        if observed['terminal'] and observed['quiescent']:
            job = native.collect(handle)
        else:
            if not Path(handle.read()['paths']['release']).exists():
                _verify_selected_software(selected)
            native.resume_start(handle, cancel_event=cancel_event)
            job = native.wait_job(handle, cancel_event=cancel_event)
    except (AcquisitionError, OSError, subprocess.SubprocessError) as error:
        observed = _observation(handle)
        if not observed['terminal'] or not observed['quiescent']:
            raise MolecularOperationUnpublished('fba_model_original_attempt_unconfirmed') from error
        failure = ({'code': error.code, 'phase': error.phase, 'operational': deepcopy(error.operational)}
            if isinstance(error, AcquisitionError) else {'code': 'local_job_boundary_unavailable',
                'phase': 'local_execution', 'operational': {'exception_type': type(error).__name__,
                    'metadata': deepcopy(observed['metadata'])}})
    observed = _observation(handle)
    if not observed['terminal'] or not observed['quiescent']:
        raise MolecularOperationUnpublished('fba_model_original_attempt_unconfirmed')
    _validate_handle(handle, selected, root)
    result = _retained_result(result_path, selected)
    if failure is None and (job.returncode != 0 or result is None):
        failure = {'code': 'local_job_execution_failed' if job.returncode else 'local_job_output_invalid',
            'phase': 'local_execution', 'operational': deepcopy(job.metadata)}
    receipt = observed.get('native_receipt')
    returncode = job.returncode if job is not None else (
        receipt.get('native_returncode') if type(receipt) is dict else None)
    execution = {'observation': observed, 'metadata': deepcopy(job.metadata if job is not None else observed['metadata']),
        'returncode': returncode, 'failure': failure}
    return {'version': VERSION, 'selection': deepcopy(selected), 'handle': handle.read(),
        'execution': execution, 'result': result, 'output_path': str(result_path),
        'stdout_path': str(root / 'stdout'), 'stderr_path': str(root / 'stderr')}
