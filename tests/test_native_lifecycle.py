"""Actual small detached processes; fixture barriers are not production policy."""
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, cancel, collect, prepare_job, release, resume_start, start_job, start_prepared, status


def policy():
    return LocalJobPolicy(64*1024**2, 4*1024**2)


def wait_for(predicate, seconds=10):
    # Test assertion deadline, never a configured work timeout.
    start = time.monotonic()
    while not predicate():
        assert time.monotonic()-start < seconds
        time.sleep(.02)


def cleanup(handle):
    if handle.path.exists():
        if not status(handle)['quiescent']:
            cancel(handle)
        release(handle)


def test_detached_job_survives_submitting_process_and_has_stable_duration(tmp_path):
    handle = NativeJobHandle(tmp_path/'handle.json')
    command = [sys.executable, '-c', "import pathlib,time;pathlib.Path('started').touch();print('started',flush=True)\n"
        "while not pathlib.Path('finish').exists(): time.sleep(.01)\nprint('finished')"]
    script = "from pathlib import Path\nfrom gene_annotation_episode.native_lifecycle import start_job\n" \
        "from gene_annotation_episode.local_jobs import LocalJobPolicy\n" \
        f"start_job({command!r},cwd=Path({str(tmp_path)!r}),policy=LocalJobPolicy(**{policy().to_dict()!r}),handle_path=Path({str(handle.path)!r}))"
    try:
        child = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=15)
        if child.returncode and 'local_job_boundary_unavailable' in child.stderr:
            pytest.skip('user-systemd boundary unavailable')
        assert child.returncode == 0, child.stderr
        wait_for(lambda: (tmp_path/'started').exists())
        current = status(NativeJobHandle(handle.path))  # A fresh receiver; no launcher memory.
        assert current['state'] == 'running' and not current['terminal']
        assert current['files']['stdout']['bytes'] > 0
        assert current['metadata']['verified_cgroup']['memory_max'] == policy().memory_bytes
        assert current['metadata']['verified_cgroup']['runtime_max'] == 'infinity'
        (tmp_path/'finish').touch()
        wait_for(lambda: status(handle)['terminal'])
        result = collect(handle)
        assert result.returncode == 0 and result.stdout_path.read_text() == 'started\nfinished\n'
        elapsed = result.metadata['elapsed_seconds']
        time.sleep(.04)
        assert collect(NativeJobHandle(handle.path)).metadata['elapsed_seconds'] == elapsed
        assert elapsed > 0
    finally:
        cleanup(handle)


def test_interrupted_startup_resumes_same_verified_service_without_resubmission(tmp_path):
    handle = NativeJobHandle(tmp_path/'handle.json')
    command = [sys.executable, '-c', "import pathlib;pathlib.Path('native-ran').write_text('once')"]
    script = "import os\nfrom pathlib import Path\nimport gene_annotation_episode.native_lifecycle as n\n" \
        "from gene_annotation_episode.local_jobs import LocalJobPolicy\n" \
        "n.resume_start=lambda *args,**kw: os._exit(42)\n" \
        f"n.start_job({command!r},cwd=Path({str(tmp_path)!r}),policy=LocalJobPolicy(**{policy().to_dict()!r}),handle_path=Path({str(handle.path)!r}))"
    try:
        child = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=15)
        if child.returncode != 42 and 'local_job_boundary_unavailable' in child.stderr:
            pytest.skip('user-systemd boundary unavailable')
        assert child.returncode == 42, child.stderr
        original_unit = handle.read()['unit']
        assert not (tmp_path/'native-ran').exists()
        resume_start(NativeJobHandle(handle.path))
        wait_for(lambda: status(handle)['terminal'])
        assert collect(handle).returncode == 0
        assert (tmp_path/'native-ran').read_text() == 'once'
        assert handle.read()['unit'] == original_unit
        with pytest.raises(ValueError, match='handle_already_exists'):
            start_job(command, cwd=tmp_path, policy=policy(), handle_path=handle.path)
        assert handle.read()['unit'] == original_unit
    finally:
        cleanup(handle)


def test_missing_terminal_evidence_is_unknown_not_zero_or_completed(tmp_path, monkeypatch):
    from gene_annotation_episode import native_lifecycle as module
    handle = NativeJobHandle(tmp_path/'handle.json')
    handle.path.write_text(json.dumps({'version': module.VERSION, 'unit': 'fixture-not-submitted.service',
        'paths': {'status': str(tmp_path/'missing-status'), 'result': str(tmp_path/'missing-result'),
                  'release': str(tmp_path/'missing-release')},
        'boot_id': module._boot(), 'started_monotonic_ns': time.monotonic_ns(),
        'metadata': {'policy': policy().to_dict()}, 'stdout': str(tmp_path/'out'), 'stderr': str(tmp_path/'err')}))
    monkeypatch.setattr(module, '_properties', lambda _: {'LoadState': 'not-found'})
    view = status(handle)
    assert view['state'] == 'execution_unknown' and not view['terminal']
    assert view['metadata']['elapsed_seconds'] is None
    assert view['metadata']['native_returncode'] is None
    with pytest.raises(AcquisitionError) as error:
        collect(handle)
    assert error.value.code == 'local_job_not_collectable'
    released=[]
    monkeypatch.setattr(module,'_release_capacity',lambda body:released.append(body['unit']))
    with pytest.raises(AcquisitionError) as error:
        module.wait_job(handle)
    assert error.value.code=='local_job_execution_unknown'
    assert released==['fixture-not-submitted.service']


def test_failed_service_submission_preserves_typed_operational_failure_without_execution(tmp_path,monkeypatch):
    from gene_annotation_episode import native_lifecycle as module
    handle = prepare_job([sys.executable,'-c',"raise AssertionError('must not run')"],
        cwd=tmp_path,policy=policy(),handle_path=tmp_path/'handle.json')
    calls = []
    def rejected(command,**kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command,1)
    monkeypatch.setattr(module.subprocess,'run',rejected)
    with pytest.raises(AcquisitionError) as error:
        module._dispatch_prepared(handle,handle.read())
    assert error.value.code=='local_job_boundary_unavailable'
    assert error.value.phase=='local_preflight'
    assert error.value.operational['reason']=='service_submission_failed'
    assert error.value.operational['launcher_returncode']==1
    assert error.value.operational['policy']==policy().to_dict()
    assert len(calls)==1 and calls[0][0]=='systemd-run'
    assert not Path(handle.read()['paths']['release']).exists()


def test_reserved_request_change_is_rejected_without_native_execution(tmp_path):
    command = [sys.executable, '-c', "from pathlib import Path;Path('native-ran').touch()"]
    handle = prepare_job(command, cwd=tmp_path, policy=policy(), handle_path=tmp_path/'handle.json')
    request = Path(handle.read()['paths']['request'])
    original = request.read_bytes()
    altered = json.loads(original)
    altered['command'] = [sys.executable, '-c', "from pathlib import Path;Path('wrong-native-ran').touch()"]
    request.write_text(json.dumps(altered))
    try:
        with pytest.raises(AcquisitionError) as error:
            start_prepared(handle)
        assert error.value.operational['reason'] == 'native_request_identity_mismatch'
        assert status(handle)['state'] == 'prepared'
        assert not (tmp_path/'native-ran').exists() and not (tmp_path/'wrong-native-ran').exists()
        request.write_bytes(original)
        start_prepared(handle)
        wait_for(lambda: status(handle)['terminal'])
        assert collect(handle).returncode == 0 and (tmp_path/'native-ran').exists()
    finally:
        cleanup(handle)


def test_worker_checks_actual_request_bytes_before_command_release(tmp_path, monkeypatch):
    import gene_annotation_episode.native_lifecycle as native
    command = [sys.executable, '-c', "from pathlib import Path;Path('native-ran').touch()"]
    handle = prepare_job(command, cwd=tmp_path, policy=policy(), handle_path=tmp_path/'handle.json')
    request = Path(handle.read()['paths']['request'])
    real_run = subprocess.run
    def change_transport_before_backend(command, *args, **kwargs):
        if command[0] == 'systemd-run':
            altered = json.loads(request.read_text())
            altered['command'] = [sys.executable, '-c', "from pathlib import Path;Path('wrong-native-ran').touch()"]
            request.write_text(json.dumps(altered))
        return real_run(command, *args, **kwargs)
    try:
        monkeypatch.setattr(native.subprocess, 'run', change_transport_before_backend)
        with pytest.raises(AcquisitionError):
            start_prepared(handle)
        wait_for(lambda: status(handle)['terminal'])
        assert 'native_request_identity_mismatch' in Path(handle.read()['stderr']).read_text()
        assert not (tmp_path/'native-ran').exists() and not (tmp_path/'wrong-native-ran').exists()
    finally:
        cleanup(handle)
