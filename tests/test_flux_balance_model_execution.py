"""Engineered model-worker protocol controls; no native/model calculation.

The lifecycle fixture is explicitly synthetic. Its retained model result is an
unavailable load, never invented scientific measurements or a native-run proof.
Root-owned bounded verification exercises the real selected interpreter later.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode import flux_balance_model_execution as execution
from gene_annotation_episode import flux_balance_model_worker as worker
from gene_annotation_episode import flux_balance_model_tools as model_tools
from gene_annotation_episode.local_jobs import LocalJobPolicy, LocalJobResult
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
from gene_annotation_episode.native_flux_balance_contracts import POLICY, flux_balance_environment
from gene_annotation_episode.native_flux_balance_storage import immutable_json, read_json
from test_flux_balance_ordinary_configuration import software as declared_software


def forbidden(*args, **kwargs):
    raise AssertionError('engineered control unexpectedly dispatched or calculated')


def software():
    value = declared_software()
    names = [str(Path(value['module_root']) / 'gene_annotation_episode' / name)
        for name in worker.MODEL_MODULE_FILES]
    names += [str(Path(worker.__file__).resolve()), str(Path(model_tools.__file__).resolve())]
    existing = {pin['path'] for pin in value['implementation_files']}
    value['implementation_files'].extend({'path': name, 'sha256': 'b' * 64, 'size_bytes': 0}
        for name in names if name not in existing)
    return value


def model_request(raw=b'engineered unread model'):
    sha = hashlib.sha256(raw).hexdigest()
    return {'version': model_tools.REQUEST_VERSION, 'mode': 'inspect', 'edits': None,
        'model_file': {'artifact_ref': 'artifact_' + sha, 'sha256': sha,
            'size_bytes': len(raw), 'format': 'cobra_json'}}


def unavailable_result(request):
    return {'version': model_tools.RESULT_VERSION, 'request': deepcopy(request),
        'models': None, 'problems': None, 'edit_results': [], 'edit_state': 'not_requested',
        'edited_model': None, 'files': [], 'model_optimize_call_count': 0,
        'issues': [model_tools._issue('model_load_failed', 'load', '/model')]}


def envelope(tmp_path):
    root = tmp_path / 'operation'
    return {'request': model_request(), 'model_path': str(tmp_path / 'input.json'),
        'output_directory': str(root / 'model-output'), 'software': software()}


def run_arguments(tmp_path):
    value = envelope(tmp_path)
    return value['request'], {'model_path': value['model_path'], 'root': tmp_path / 'operation',
        'software': value['software'], 'policy': LocalJobPolicy(**POLICY)}


@pytest.mark.parametrize('fault', ['extra', 'relative_model', 'relative_output', 'unbound_worker', 'overlap'])
def test_closed_worker_envelope_rejects_before_model_or_file_access(tmp_path, monkeypatch, fault):
    value = envelope(tmp_path)
    if fault == 'extra': value['fallback_python'] = '/invented'
    elif fault == 'relative_model': value['model_path'] = 'relative.json'
    elif fault == 'relative_output': value['output_directory'] = 'relative-output'
    elif fault == 'unbound_worker':
        value['software']['implementation_files'] = [pin for pin in value['software']['implementation_files']
            if pin['path'] != str(Path(value['software']['module_root']) / 'gene_annotation_episode' / 'flux_balance_model_worker.py')]
    else: value['model_path'] = value['output_directory'] + '/caller.json'
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(model_tools, 'run_flux_balance_model_request', forbidden)
    with pytest.raises(ValueError):
        worker.validate_flux_balance_model_worker_request(value)


@pytest.mark.parametrize('arguments', [[], ['relative-request', '/absolute-result'], ['/same', '/same'], ['/a', '/b', '/c']])
def test_cli_requires_two_distinct_absolute_arguments(arguments, monkeypatch):
    monkeypatch.setattr(worker, 'read_json', forbidden)
    with pytest.raises(ValueError): worker.main(arguments)


def test_cli_delegates_literal_selected_request_and_retains_immutable_canonical_result(tmp_path, monkeypatch):
    value = envelope(tmp_path)
    root = Path(value['output_directory']).parent
    immutable_json(root / 'request.json', value)
    calls = []
    def selected(request, **kwargs):
        calls.append((deepcopy(request), deepcopy(kwargs)))
        return unavailable_result(request)
    monkeypatch.setattr(model_tools, 'run_flux_balance_model_request', selected)
    assert worker.main([str(root / 'request.json'), str(root / 'result.json')]) == 0
    assert calls == [(value['request'], {key: value[key] for key in ('model_path', 'output_directory', 'software')})]
    assert read_json(root / 'result.json') == unavailable_result(value['request'])
    assert (root / 'result.json').read_bytes() == canonical(unavailable_result(value['request'])).encode() + b'\n'
    with pytest.raises(ValueError, match='result_exists'):
        worker.main([str(root / 'request.json'), str(root / 'result.json')])
    assert len(calls) == 1


@pytest.fixture
def lifecycle(monkeypatch):
    state = SimpleNamespace(calls=[], terminal=False, quiescent=True, returncode=0,
        wait_error=None, write_result=True, invalid_result=False, checked=[])
    def pins(selected):
        return {pin['path']: pin for pin in [selected['python'], *selected['implementation_files'],
            *selected['runtime_files'], *selected['solver_runtime_files']]}
    def verify(path):
        state.checked.append(str(path))
        return deepcopy(pins(state.software)[str(path)])
    monkeypatch.setattr(execution, 'file_pin', verify)
    def prepare(command, *, cwd, policy, handle_path, stdout_path, stderr_path, env):
        state.calls.append(('prepare', str(handle_path)))
        token = '.local-job-' + 'a' * 32
        paths = {name: str(cwd / (token + '.' + name)) for name in
            ('request', 'ready', 'release', 'status', 'result', 'launcher')}
        native_request = {'command': command, 'cwd': str(cwd), 'file_bytes': policy.scratch_bytes,
            'ready_path': paths['ready'], 'release_path': paths['release'],
            'result_path': paths['result'], 'stdin_path': None, 'env': env}
        immutable_json(Path(paths['request']), native_request)
        body = {'version': execution.native.VERSION, 'unit': 'gene-local-job-' + 'b' * 32 + '.service',
            'command': command, 'cwd': str(cwd), 'stdout': str(stdout_path), 'stderr': str(stderr_path),
            'paths': paths, 'metadata': {'policy': policy.to_dict(), 'engineered': True},
            'stage': 'prepared', 'request_sha256': hashlib.sha256(Path(paths['request']).read_bytes()).hexdigest()}
        handle_path.write_text(canonical(body))
        Path(stdout_path).write_bytes(b'engineered stdout')
        Path(stderr_path).write_bytes(b'engineered stderr')
        return execution.native.NativeJobHandle(handle_path)
    def status(handle):
        body = handle.read()
        return {'version': execution.native.VERSION, 'state': 'returned' if state.terminal else 'execution_unknown',
            'terminal': state.terminal, 'quiescent': state.quiescent,
            'metadata': body['metadata'], 'native_receipt': {'native_returncode': state.returncode}, 'files': {}}
    def resume(handle, *, cancel_event=None):
        state.calls.append(('resume', str(handle.path)))
        body = handle.read()
        body['stage'] = 'released'
        handle.path.write_text(canonical(body))
        Path(body['paths']['release']).touch()
    def collect(handle):
        state.calls.append(('collect', str(handle.path)))
        body = handle.read()
        return LocalJobResult(state.returncode, Path(body['stdout']), Path(body['stderr']), body['metadata'])
    def wait(handle, *, cancel_event=None):
        state.calls.append(('wait', str(handle.path)))
        root = handle.path.parent
        if state.write_result:
            request = read_json(root / 'request.json')['request']
            result = unavailable_result(request)
            if state.invalid_result: result['extra'] = 'engineered-invalid-result'
            immutable_json(root / 'result.json', result)
        if state.wait_error is not None:
            raise state.wait_error
        state.terminal = True
        return collect(handle)
    for name, callback in [('prepare_job', prepare), ('status', status), ('resume_start', resume),
            ('wait_job', wait), ('collect', collect)]:
        monkeypatch.setattr(execution.native, name, callback)
    return state


def test_selected_command_environment_pins_and_saved_same_handle_are_preserved(tmp_path, lifecycle, monkeypatch):
    request, kwargs = run_arguments(tmp_path)
    lifecycle.software = kwargs['software']
    result = execution.run_selected_flux_balance_model(request, **kwargs)
    selected, root = result['selection'], kwargs['root']
    assert selected['command'] == [kwargs['software']['python']['path'], '-B', '-S', '-m', worker.WORKER_MODULE,
        str(root / 'request.json'), str(root / 'result.json')]
    assert selected['environment'] == flux_balance_environment(kwargs['software'],
        lifecycle_directory=str(root), attempt_directory=str(root / execution.ATTEMPT_DIRECTORY_NAME))
    all_pins = [kwargs['software']['python'], *kwargs['software']['implementation_files'],
        *kwargs['software']['runtime_files'], *kwargs['software']['solver_runtime_files']]
    assert set(lifecycle.checked) == {pin['path'] for pin in all_pins}
    assert result['result'] == unavailable_result(request)
    assert result['execution']['failure'] is None and result['execution']['returncode'] == 0
    original = deepcopy(result)
    monkeypatch.setattr(execution.native, 'prepare_job', forbidden)
    monkeypatch.setattr(execution.native, 'resume_start', forbidden)
    monkeypatch.setattr(execution.native, 'wait_job', forbidden)
    monkeypatch.setattr(execution, '_verify_selected_software', forbidden)
    assert execution.run_selected_flux_balance_model(request, **kwargs) == original
    assert [name for name, _ in lifecycle.calls].count('prepare') == 1


@pytest.mark.parametrize('policy', [None, POLICY, LocalJobPolicy(POLICY['memory_bytes'] + 1, POLICY['scratch_bytes']),
    LocalJobPolicy(POLICY['memory_bytes'], POLICY['scratch_bytes'] + 1)])
def test_explicit_exact_policy_is_required_before_any_dispatch(tmp_path, monkeypatch, policy):
    request, kwargs = run_arguments(tmp_path)
    kwargs['policy'] = policy
    monkeypatch.setattr(execution.native, 'prepare_job', forbidden)
    with pytest.raises(ValueError, match='policy_invalid'):
        execution.run_selected_flux_balance_model(request, **kwargs)
    assert not kwargs['root'].exists()


@pytest.mark.parametrize('fault', ['input_overlap', 'software_overlap', 'pin_changed'])
def test_inputs_and_selected_software_are_protected_before_dispatch(tmp_path, monkeypatch, fault):
    request, kwargs = run_arguments(tmp_path)
    if fault == 'input_overlap': kwargs['model_path'] = kwargs['root'] / 'caller.json'
    elif fault == 'software_overlap': kwargs['software']['python_home'] = str(kwargs['root'])
    else: monkeypatch.setattr(execution, 'file_pin', lambda path: {'path': str(path), 'sha256': '0' * 64, 'size_bytes': 9})
    monkeypatch.setattr(execution.native, 'prepare_job', forbidden)
    with pytest.raises(ValueError): execution.run_selected_flux_balance_model(request, **kwargs)


@pytest.mark.parametrize('fault', ['selection', 'request', 'handle', 'native_request', 'orphan_output'])
def test_saved_controls_cannot_be_replaced_to_dispatch_again(tmp_path, lifecycle, monkeypatch, fault):
    request, kwargs = run_arguments(tmp_path)
    lifecycle.software = kwargs['software']
    original = execution.run_selected_flux_balance_model(request, **kwargs)
    root = kwargs['root']
    if fault == 'selection':
        selected = read_json(root / 'selection.json'); selected['environment']['TMPDIR'] = '/invented'
        (root / 'selection.json').chmod(0o600); (root / 'selection.json').write_text(canonical(selected))
    elif fault == 'request':
        value = read_json(root / 'request.json'); value['request']['model_file']['size_bytes'] += 1
        (root / 'request.json').chmod(0o600); (root / 'request.json').write_text(canonical(value))
    elif fault == 'handle':
        body = read_json(root / 'native-handle.json'); body['stdout'] = '/outside'
        (root / 'native-handle.json').write_text(canonical(body))
    elif fault == 'native_request':
        path = Path(original['handle']['paths']['request']); path.chmod(0o600); path.write_text('{}')
    else: (root / 'native-handle.json').unlink()
    monkeypatch.setattr(execution.native, 'prepare_job', forbidden)
    with pytest.raises(ValueError): execution.run_selected_flux_balance_model(request, **kwargs)


def test_uncertain_original_handle_is_pending_and_later_collected_without_new_unit(tmp_path, lifecycle, monkeypatch):
    request, kwargs = run_arguments(tmp_path)
    lifecycle.software, lifecycle.write_result = kwargs['software'], False
    lifecycle.wait_error = AcquisitionError('local_job_execution_unknown', phase='local_execution')
    with pytest.raises(MolecularOperationUnpublished): execution.run_selected_flux_balance_model(request, **kwargs)
    handle = read_json(kwargs['root'] / 'native-handle.json')
    assert [name for name, _ in lifecycle.calls].count('prepare') == 1
    lifecycle.terminal, lifecycle.wait_error = True, None
    immutable_json(kwargs['root'] / 'result.json', unavailable_result(request))
    monkeypatch.setattr(execution.native, 'prepare_job', forbidden)
    monkeypatch.setattr(execution.native, 'resume_start', forbidden)
    result = execution.run_selected_flux_balance_model(request, **kwargs)
    assert result['handle'] == handle and result['result'] == unavailable_result(request)


@pytest.mark.parametrize('failure', ['nonzero', 'resource', 'missing_result', 'invalid_result'])
def test_known_terminal_failures_preserve_actual_metadata_and_only_valid_partial_result(tmp_path, lifecycle, monkeypatch, failure):
    request, kwargs = run_arguments(tmp_path)
    lifecycle.software = kwargs['software']
    if failure == 'nonzero': lifecycle.returncode = 9
    elif failure == 'resource':
        lifecycle.terminal = True
        lifecycle.wait_error = AcquisitionError('local_job_resource_limit', phase='local_execution',
            operational={'resource': 'memory_bytes', 'engineered': True})
        # A previously running original handle can become terminal while wait
        # reports its actual resource failure. The initial observation is live.
        lifecycle.terminal = False
        original_wait = execution.native.wait_job
        def failed_wait(handle, *, cancel_event=None):
            lifecycle.terminal = True
            return original_wait(handle, cancel_event=cancel_event)
        monkeypatch.setattr(execution.native, 'wait_job', failed_wait)
    elif failure == 'missing_result': lifecycle.write_result = False
    else: lifecycle.invalid_result = True
    result = execution.run_selected_flux_balance_model(request, **kwargs)
    assert result['execution']['failure'] is not None
    assert result['execution']['observation']['terminal'] is True
    assert result['execution']['observation']['quiescent'] is True
    assert result['execution']['metadata']['engineered'] is True
    assert result['result'] == (unavailable_result(request) if failure in {'nonzero', 'resource'} else None)
