"""No-native checks for independent child quota and authenticated replay."""
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

PACKAGE = __package__.rsplit('.tests', 1)[0]


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    native = import_module(PACKAGE+'.native_lifecycle')
    local = import_module(PACKAGE+'.local_resources')
    monkeypatch.setenv(local.DIRECTORY_ENV, str(tmp_path/'capacity'))
    monkeypatch.setattr(native, '_control', lambda *args: SimpleNamespace(returncode=0, stdout=''))
    monkeypatch.setattr(native, '_properties', lambda unit: {'LoadState':'not-found'})
    directory = tmp_path/'native'; directory.mkdir()
    policy = import_module(PACKAGE+'.local_jobs').LocalJobPolicy(8*1024**2,16*1024**2)
    command = ['/synthetic/unexecuted-native', '--cpu', '4', 'original-input']
    handle = native.prepare_job(command, cwd=directory, policy=policy,
                                handle_path=directory/'native.handle.json', cpu_threads=4)
    return native, handle, command


def test_new_preparation_records_independent_quota_and_exact_selected_command(prepared):
    _, handle, command = prepared
    body = handle.read()
    assert body['metadata']['cpu_quota_percent'] == 100
    assert body['metadata']['cpu_threads'] == 4
    assert body['command'] == command
    request = json.loads(Path(body['paths']['request']).read_text())
    assert request['command'] == command
    assert body['stage'] == 'prepared'


def test_dispatch_uses_fixed_child_quota_without_changing_request(prepared, monkeypatch):
    native, handle, command = prepared
    body = handle.read()
    request = Path(body['paths']['request']).read_bytes()
    commands = []
    monkeypatch.setattr(native.subprocess, 'run',
                        lambda argv, **kwargs: commands.append(argv) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(native, 'resume_start', lambda selected, **kwargs: selected)
    assert native._dispatch_prepared(handle, body) is handle
    assert len(commands) == 1
    assert 'CPUQuota=100%' in commands[0]
    assert not any(item.startswith('CPUQuota=400') for item in commands[0])
    assert handle.read()['command'] == command
    assert Path(body['paths']['request']).read_bytes() == request




def test_new_dispatch_cannot_turn_changed_metadata_into_extra_cpu_capacity(prepared, monkeypatch):
    native, handle, _ = prepared
    body = handle.read(); body['metadata']['cpu_quota_percent'] = 200
    native.atomic_json(handle.path, body)
    request = Path(body['paths']['request']).read_bytes()
    commands = []
    monkeypatch.setattr(native.subprocess, 'run',
        lambda argv, **kwargs: commands.append(argv) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(native, 'resume_start', lambda selected, **kwargs: selected)
    assert native.start_prepared(handle) is handle
    assert len(commands) == 1 and 'CPUQuota=100%' in commands[0]
    assert 'CPUQuota=200%' not in commands[0]
    saved = handle.read()
    assert saved['metadata']['cpu_quota_percent'] == 100
    assert saved['metadata']['cpu_threads'] == 4
    assert Path(body['paths']['request']).read_bytes() == request
    reservation = saved['capacity_reservation']
    import_module(PACKAGE+'.local_resources').LocalResources.reopen(
        reservation['resource']).release_reservation(reservation)


def test_direct_released_resume_authenticates_original_whole_workflow_identity(prepared):
    native, handle, _ = prepared
    body = handle.read()
    body['stage'] = 'released'
    body['metadata']['whole_workflow_budget'] = {
        **body['metadata']['whole_workflow_budget'], 'window_id': 'synthetic-wrong-owner'}
    native.atomic_json(handle.path, body)
    Path(body['paths']['release']).touch()
    before = handle.path.read_bytes()
    with pytest.raises(native.AcquisitionError, match='whole_workflow_budget_identity_conflict'):
        native.resume_start(handle)
    assert handle.path.read_bytes() == before
