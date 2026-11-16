"""Shared-worker controls with explicitly engineered lifecycle observations.

No service, Bio scoring, ToolOperation, native capture or completed episode is
created here. Distribution/handle fixtures test metadata selection and observer
behavior; they do not establish an installed native scientific producer.
Pending-capture and committed-producer checks require the actual ordinary TF
handler path and deliberately remain outside this module's current scope.
"""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode import molecular_measurement_tools as shared
from gene_annotation_episode import native_lifecycle


OPERATIONS = ('tf_binding_native', 'tf_binding_result', 'homer_motif_result')
MODULES = {'tf_binding_native': 'gene_annotation_episode.tf_binding_driver',
    'tf_binding_result': 'gene_annotation_episode.tf_binding_result_worker',
    'homer_motif_result': 'gene_annotation_episode.native_homer_worker'}


def forbidden(*_args, **_kwargs):
    raise AssertionError('shared-authority engineering control attempted real work')


@pytest.fixture
def controlled_worker(tmp_path, monkeypatch):
    """One synthetic reservation; no systemd/process/native calls occur."""
    owned = tmp_path / 'owned'; owned.mkdir()
    selected_source = tmp_path / 'selected-implementation.py'
    selected_source.write_bytes(b'explicit engineering software identity, never imported')
    policy = LocalJobPolicy(memory_bytes=5 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3)
    event = threading.Event()
    calls = dict(prepare=0, resume=0, collect=0)
    observations = dict(state='prepared', terminal=False, quiescent=False)
    class Handle:
        def __init__(self, path): self.path = Path(path)
        def read(self): return json.loads(self.path.read_bytes())
    def prepare(command, *, cwd, policy, handle_path, stdout_path, stderr_path, env):
        calls['prepare'] += 1
        paths = {name: str(cwd / ('.local-job-' + 'a' * 32 + '.' + name))
            for name in ('request', 'ready', 'release', 'status', 'result', 'launcher')}
        request = dict(command=command, cwd=str(cwd), file_bytes=policy.scratch_bytes,
            ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None, env=env)
        raw = canonical(request).encode(); Path(paths['request']).write_bytes(raw)
        body = dict(version=native_lifecycle.VERSION,
            stage='prepared' if observations['state'] == 'prepared' else 'released',
            command=command, cwd=str(cwd), stdout=str(stdout_path), stderr=str(stderr_path), paths=paths,
            request_sha256=hashlib.sha256(raw).hexdigest(), metadata=dict(policy=policy.to_dict()))
        Path(handle_path).write_text(json.dumps(body))
        return Handle(handle_path)
    def status(handle):
        handle.read()
        return {**observations, 'metadata': {'policy': policy.to_dict(), 'engineering_observation': True}}
    def resume(handle, **_kwargs):
        calls['resume'] += 1
        body = handle.read(); body['stage'] = 'released'
        handle.path.write_text(json.dumps(body)); Path(body['paths']['release']).touch()
        observations['state'] = 'running'; event.set()
    def collect(handle):
        calls['collect'] += 1
        assert observations['terminal'] and observations['quiescent']
        assert handle.path == owned / 'native-handle.json'
        return SimpleNamespace(returncode=0, metadata={'engineering_observation': True})
    monkeypatch.setattr(shared, '_molecular_implementation_files', lambda operation: [selected_source])
    monkeypatch.setattr(native_lifecycle, 'NativeJobHandle', Handle)
    monkeypatch.setattr(native_lifecycle, 'prepare_job', prepare)
    monkeypatch.setattr(native_lifecycle, 'status', status)
    monkeypatch.setattr(native_lifecycle, 'resume_start', resume)
    monkeypatch.setattr(native_lifecycle, 'collect', collect)
    for name in ('wait_job', 'cancel', 'start_job', 'start_prepared', 'release'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    def invoke(operation, *, selected_policy=policy):
        return shared.run_owned_molecular_worker(operation, {'engineering_metadata_only': True},
            directory=owned, owned_directory=owned, policy=selected_policy, cancel_event=event)
    return SimpleNamespace(owned=owned, selected_source=selected_source, policy=policy,
        event=event, calls=calls, observations=observations, invoke=invoke)


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('condition', ['already_stopped', 'stop_after_release', 'execution_unknown'])
def test_stop_or_unknown_keeps_one_original_worker_handle_without_cancel_or_resubmission(controlled_worker, operation, condition):
    case = controlled_worker
    if condition == 'already_stopped': case.event.set()
    if condition == 'execution_unknown': case.observations['state'] = 'execution_unknown'
    for attempt in range(2):
        with pytest.raises(shared.MolecularOperationUnpublished, match='worker_attempt_unconfirmed'):
            case.invoke(operation)
        current = {name: (case.owned / name).read_bytes() for name in
            ('execution-selection.json', 'worker-request.json', 'native-handle.json')}
        if attempt == 0: original = current
        else: assert current == original
    assert case.calls == dict(prepare=1, resume=1 if condition == 'stop_after_release' else 0, collect=0)
    selected = json.loads(original['execution-selection.json'])
    assert selected['command'][2] == MODULES[operation]
    assert selected['policy'] == case.policy.to_dict()
    if operation.startswith('tf_binding_'):
        assert selected['environment']['PYTHONDONTWRITEBYTECODE'] == '1'
        for key in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME'):
            assert Path(selected['environment'][key]).is_relative_to(case.owned)


