"""Shared-worker controls with explicitly engineered lifecycle observations.

No service, Bio scoring, ToolOperation, native capture or completed episode is
created here. Distribution/handle fixtures test metadata selection and observer
behavior; they do not establish an installed native scientific producer.
Pending-capture and committed-producer checks require the actual ordinary TF
handler path and deliberately remain outside this module's current scope.
"""
import hashlib
from importlib import metadata, util
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError, canonical
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
def distribution_metadata(tmp_path, monkeypatch):
    """Actual temporary Files behind fake distribution/spec metadata only."""
    distributions, specifications, expected, outside = {}, {}, {}, {}
    for distribution_name, package in (('biopython', 'Bio'), ('numpy', 'numpy')):
        root = tmp_path / distribution_name / 'site-packages'
        entries = [Path(package) / '__init__.py', Path(package) / 'native-data.bin',
            Path(distribution_name + '.dist-info') / 'METADATA', Path('../bin/unused-console')]
        for index, entry in enumerate(entries):
            path = root / entry
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('explicit engineering distribution file ' + str(index)).encode())
        entries += [Path(package) / '__pycache__' / '__init__.pyc']
        distributions[distribution_name] = SimpleNamespace(files=entries,
            locate_file=lambda entry, root=root: root / entry)
        specifications[package] = SimpleNamespace(origin=str((root / entries[0]).resolve()))
        expected[distribution_name] = {(root / entry).resolve() for entry in entries[:3]}
        outside[distribution_name] = (root / '../bin/unused-console').resolve()
    monkeypatch.setattr(metadata, 'distribution', lambda name: distributions[name])
    monkeypatch.setattr(util, 'find_spec', lambda name: specifications[name])
    return SimpleNamespace(distributions=distributions, specifications=specifications,
        expected=expected, outside=outside)


@pytest.mark.parametrize('operation', OPERATIONS)
def test_finite_shared_worker_route_preserves_tf_and_homer_entry_modules(operation):
    assert shared._molecular_worker_module(operation) == MODULES[operation]


@pytest.mark.parametrize('operation', ['tf_binding_native', 'tf_binding_result'])
def test_tf_selected_distribution_identity_includes_imported_assets_and_excludes_unused_console(
        distribution_metadata, operation):
    case = distribution_metadata
    files = shared._molecular_implementation_files(operation)
    assert Path(shared.__file__) in files
    assert Path(shared.__file__).with_name(MODULES[operation].rsplit('.', 1)[-1] + '.py') in files
    assert len(files) == len(set(files))
    assert set().union(*case.expected.values()) <= set(files)
    assert not set(case.outside.values()) & set(files)
    assert all(path.suffix != '.pyc' and '__pycache__' not in path.parts for path in files)


@pytest.mark.parametrize('fault', ['wrong_import_origin', 'missing_distribution_file'])
def test_tf_distribution_identity_failure_has_no_fallback_or_native_probe(distribution_metadata, monkeypatch, fault):
    case = distribution_metadata
    monkeypatch.setattr(native_lifecycle, 'prepare_job', forbidden)
    if fault == 'wrong_import_origin':
        case.specifications['Bio'].origin = str(case.outside['biopython'])
    else:
        next(path for path in case.expected['biopython'] if path.name == 'METADATA').unlink()
    with pytest.raises(AcquisitionError) as caught:
        shared._molecular_implementation_files('tf_binding_native')
    assert caught.value.code == 'biopython_not_installed' and caught.value.phase == 'local_preflight'
    assert caught.value.operational['reason'] == ('distribution_import_or_files_conflict'
        if fault == 'wrong_import_origin' else 'distribution_file_unavailable')


def test_unlisted_worker_operation_is_denied_before_selection_or_reservation(tmp_path, monkeypatch):
    policy = LocalJobPolicy(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3, wall_seconds=None)
    monkeypatch.setattr(shared, '_molecular_implementation_files', forbidden)
    monkeypatch.setattr(native_lifecycle, 'prepare_job', forbidden)
    before = sorted(tmp_path.iterdir())
    with pytest.raises(ContractError, match='molecular_tool_owned_directory_conflict'):
        shared.run_owned_molecular_worker('tf_binding_arbitrary', {}, directory=tmp_path,
            owned_directory=tmp_path, policy=policy, cancel_event=None)
    assert sorted(tmp_path.iterdir()) == before


@pytest.fixture
def controlled_worker(tmp_path, monkeypatch):
    """One synthetic reservation; no systemd/process/native calls occur."""
    owned = tmp_path / 'owned'; owned.mkdir()
    selected_source = tmp_path / 'selected-implementation.py'
    selected_source.write_bytes(b'explicit engineering software identity, never imported')
    policy = LocalJobPolicy(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3, wall_seconds=None)
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


@pytest.mark.parametrize('operation', OPERATIONS)
def test_later_terminal_observation_collects_only_original_handle_and_selection(controlled_worker, monkeypatch, operation):
    case = controlled_worker; case.observations['state'] = 'execution_unknown'
    with pytest.raises(shared.MolecularOperationUnpublished): case.invoke(operation)
    original = {name: (case.owned / name).read_bytes() for name in
        ('execution-selection.json', 'worker-request.json', 'native-handle.json')}
    # A terminal metadata adapter and an opaque output file are explicit test
    # inputs, not a claim that a scientific worker actually ran successfully.
    output = case.owned / 'worker-result.json'; output.write_bytes(b'engineering opaque output')
    case.observations.update(state='returned', terminal=True, quiescent=True)
    case.selected_source.unlink()
    monkeypatch.setattr(shared, '_molecular_implementation_files', forbidden)
    later_policy = LocalJobPolicy(memory_bytes=1024, scratch_bytes=2048, wall_seconds=1)
    result, metadata_result = case.invoke(operation, selected_policy=later_policy)
    assert result == output and metadata_result == {'engineering_observation': True}
    assert case.calls == dict(prepare=1, resume=0, collect=1)
    assert {name: (case.owned / name).read_bytes() for name in original} == original


def selected_manifest(case, operation):
    """Explicit unstarted selection metadata, without a reservation/outcome."""
    request = case.owned / 'worker-request.json'; output = case.owned / 'worker-result.json'
    return dict(version='ordinary_molecular_execution_v1',
        command=[shared.sys.executable, '-m', MODULES[operation], str(request), str(output)],
        cwd=str(case.owned), environment={'PYTHONDONTWRITEBYTECODE': '1'}, policy=case.policy.to_dict(),
        request=dict(operation=operation, arguments={'engineering_metadata_only': True}),
        python=dict(path=shared.sys.executable, sha256=hashlib.sha256(Path(shared.sys.executable).read_bytes()).hexdigest()),
        implementation_files=[dict(path=str(case.selected_source), sha256=hashlib.sha256(case.selected_source.read_bytes()).hexdigest())])


@pytest.mark.parametrize('operation', OPERATIONS)
def test_selected_software_byte_change_blocks_first_dispatch_without_reselection(controlled_worker, monkeypatch, operation):
    case = controlled_worker
    selected_path = case.owned / 'execution-selection.json'; selected = selected_manifest(case, operation)
    selected_path.write_text(json.dumps(selected)); original = selected_path.read_bytes()
    case.selected_source.write_bytes(b'changed selected software')
    monkeypatch.setattr(native_lifecycle, 'prepare_job', forbidden)
    monkeypatch.setattr(shared, '_molecular_implementation_files', forbidden)
    with pytest.raises(ContractError, match='original_software_changed_before_dispatch'):
        case.invoke(operation)
    assert case.calls == dict(prepare=0, resume=0, collect=0)
    assert selected_path.read_bytes() == original and not (case.owned / 'native-handle.json').exists()


@pytest.mark.parametrize('operation', OPERATIONS)
def test_selected_module_conflict_is_rejected_before_request_or_dispatch(controlled_worker, monkeypatch, operation):
    case = controlled_worker; selected = selected_manifest(case, operation)
    selected['command'][2] = 'gene_annotation_episode.unselected_worker'
    selected_path = case.owned / 'execution-selection.json'; selected_path.write_text(json.dumps(selected))
    original = selected_path.read_bytes()
    monkeypatch.setattr(native_lifecycle, 'prepare_job', forbidden)
    monkeypatch.setattr(shared, '_molecular_implementation_files', forbidden)
    with pytest.raises(ContractError, match='execution_selection_conflict'):
        case.invoke(operation)
    assert case.calls == dict(prepare=0, resume=0, collect=0)
    assert selected_path.read_bytes() == original and not (case.owned / 'worker-request.json').exists()
