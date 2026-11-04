"""Synthetic producer bytes and bounded capture; no biological executable runs."""
import base64
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_blast_database_acquisition import capture_native_blast_database_bundle
from gene_annotation_episode.state import Store
from test_native_blast_database_driver import fixture, run_fixture, save_json
from test_execution_episodes_family import native_assignment


class CapturedReader:
    def __init__(self, witness):
        self.witness, self.calls, self.auth_calls = witness, [], 0

    def authenticate_native_blast_database_attempt(self, target):
        self.auth_calls += 1
        return deepcopy(self.witness)

    def read_file(self, target, *, path, offset, limit, operation_key):
        assert 1 <= limit <= 1024**2
        self.calls.append((path, offset, limit))
        raw = Path(path).read_bytes()
        data = raw[offset:offset + limit]
        return dict(path=path, offset=offset, returned_bytes=len(data), size_bytes=len(raw),
            bytes_base64=base64.b64encode(data).decode(), text_utf8=data.decode('utf8', 'replace'))


def original_attempt(tmp_path, program='psiblast'):
    workspace = tmp_path / 'project'
    path, plan, manifest = fixture(workspace / 'selected', program=program, checkpoint_output=False)
    assignment = native_assignment(workspace, 'synthetic-hpc', kind='hpc')
    assignment['requested_job'] = deepcopy(plan['requested_job'])
    owner = dict(run_id='synthetic-321', episode_id='original-hpc-child', resource_id='synthetic-hpc',
        operation_key='selected-original-operation', assignment_sha256=digest(assignment),
        requested_job_sha256=digest(assignment['requested_job']), execution_id=None)
    owner['attempt_id'] = digest(owner['operation_key'])
    owner['submission_token'] = digest({k: owner[k] for k in ('run_id', 'episode_id', 'assignment_sha256', 'operation_key')})
    root = workspace / '.episode-jobs' / digest({k: owner[k] for k in ('run_id', 'episode_id')}) / digest(assignment) / 'attempts' / owner['attempt_id']
    root.mkdir(parents=True)
    plan.update(identity=owner, attempt_directory=str(root), output_directory=str(root / 'outputs'),
        input_paths={r['input_key']: str(root / 'inputs' / r['input_key']) for r in assignment['requested_job']['native_blast_database']['inputs']})
    path = root / 'native-blast-database-plan.json'; save_json(path, plan)
    process, bundle = run_fixture(path, plan)
    assert process.returncode == 0, process.stderr.decode()
    target = dict(version='execution_target_v1', handle='source_synthetic_original_receipt',
        run_id=owner['run_id'], resource_id=owner['resource_id'], resource_kind='hpc', execution_id='313.synthetic',
        request_sha256=owner['requested_job_sha256'], origin_episode_id=owner['episode_id'], assignment=assignment,
        scope={'subject_refs': []})
    extra = dict(native_blast_database_plan_path=str(path), native_blast_database_plan_sha256=digest(plan))
    witness = dict(authenticated_attempt=dict(identity={**owner, 'execution_id': '313.synthetic'},
        attempt_directory=str(root), plan_sha256=digest(plan)), plan_path=str(path),
        ledger=dict(version='practical_pbs_submission_v2', job_id='313.synthetic', **extra,
            **{k: owner[k] for k in ('attempt_id', 'operation_key', 'assignment_sha256', 'submission_token')},
            selection={'requested_job_sha256': owner['requested_job_sha256']}),
        job_request=dict(job_request_sha256=owner['requested_job_sha256'], submission_token=owner['submission_token'], **extra))
    return SimpleNamespace(target=target, bundle=bundle, plan=plan, root=root, reader=CapturedReader(witness))


def test_complete_chunks_and_frozen_replay(tmp_path, monkeypatch):
    original = original_attempt(tmp_path)
    with Store(tmp_path / 'store') as store:
        value = capture_native_blast_database_bundle(store, target=original.target, reader=original.reader,
            operation_key='selected-collect', directory=tmp_path / 'capture')
        assert value['status'] == 'complete', value
        assert list(value['artifact_refs']) == [r['artifact_key'] for r in original.bundle['artifacts']]
        assert any(offset >= 1024**2 for _, offset, _ in original.reader.calls)
        assert original.reader.auth_calls == 1
        original.root.rename(original.root.with_name('offline-original'))
        monkeypatch.setattr(original.reader, 'read_file', lambda *a, **k: pytest.fail('replay acquired remote bytes'))
        monkeypatch.setattr(original.reader, 'authenticate_native_blast_database_attempt', lambda *a, **k: pytest.fail('replay reauthenticated remote'))
        assert capture_native_blast_database_bundle(store, target=original.target, reader=original.reader,
            operation_key='selected-collect', directory=tmp_path / 'capture') == value


@pytest.mark.parametrize('fault', ['ledger', 'plan', 'bundle', 'missing', 'digest', 'size', 'seal'])
def test_original_identity_and_partial_siblings(tmp_path, fault, monkeypatch):
    original = original_attempt(tmp_path)
    victim = next(r for r in original.bundle['artifacts'] if r['role'] == 'primary_report')
    path = original.root / victim['relative_path']
    if fault == 'ledger':
        original.reader.witness['ledger']['job_id'] = 'other'
    elif fault == 'plan':
        p = original.root / 'native-blast-database-plan.json'; value = json.loads(p.read_bytes()); value['identity']['resource_id'] = 'other'; save_json(p, value)
    elif fault == 'bundle':
        value = deepcopy(original.bundle); value['identity']['execution_id'] = 'other'; save_json(original.root / 'bundle.json', value)
    elif fault == 'missing':
        path.unlink()
    elif fault == 'digest':
        path.write_bytes(b'x' * path.stat().st_size)
    elif fault == 'size':
        path.write_bytes(b'changed length')
    elif fault == 'seal':
        read = original.reader.read_file
        def changing(target, **args):
            if args['path'].endswith('bundle.json') and sum(p.endswith('bundle.json') and o == 0 for p, o, _ in original.reader.calls):
                (original.root / 'bundle.json').write_bytes((original.root / 'bundle.json').read_bytes() + b' ')
            return read(target, **args)
        monkeypatch.setattr(original.reader, 'read_file', changing)
    with Store(tmp_path / 'store') as store:
        value = capture_native_blast_database_bundle(store, target=original.target, reader=original.reader,
            operation_key='selected-collect', directory=tmp_path / 'capture')
        assert value['status'] != 'complete'
        if fault in {'missing', 'digest', 'size'}:
            assert value['status'] == 'partial'
            assert len(value['artifact_refs']) == len(original.bundle['artifacts']) - 1
            assert value['failures'][0]['artifact_key'] == victim['artifact_key']
        if fault == 'ledger':
            assert original.reader.calls == []
            assert value['failures'][0]['code'] == 'attempt_mismatch'


@pytest.mark.parametrize('stage', ['plan.capture', 'bundle.capture', 'artifact', 'plan.seal', 'bundle.seal', 'partial', 'finalization'])
def test_same_selected_capture_resumes_verified_existing_bytes(tmp_path, monkeypatch, stage):
    import gene_annotation_episode.native_blast_database_acquisition as acquisition
    original = original_attempt(tmp_path)
    largest = max(original.bundle['artifacts'], key=lambda row: row['size_bytes'])
    artifact_name = 'artifact-' + str(original.bundle['artifacts'].index(largest)) + '.capture'
    selected = artifact_name if stage in {'artifact', 'partial'} else stage
    directory = tmp_path / 'capture'
    class Interrupted(BaseException):
        pass
    retain, read, immutable = acquisition.artifact_file, original.reader.read_file, acquisition._immutable
    if stage == 'finalization':
        selected = 'capture-finalization.json'
        def interrupt_commit(path, value):
            immutable(path, value)
            if Path(path).name == selected:
                raise Interrupted('synthetic interruption before final receipt commit')
        monkeypatch.setattr(acquisition, '_immutable', interrupt_commit)
    elif stage == 'partial':
        def interrupt_read(target, **arguments):
            if arguments['path'] == str(original.root / largest['relative_path']) and arguments['offset'] >= 1024**2:
                raise Interrupted('synthetic interruption during bounded transfer')
            return read(target, **arguments)
        monkeypatch.setattr(original.reader, 'read_file', interrupt_read)
    else:
        def interrupt_retain(store, path):
            if Path(path).name == selected:
                raise Interrupted('synthetic interruption after complete file, before receipt')
            return retain(store, path)
        monkeypatch.setattr(acquisition, 'artifact_file', interrupt_retain)
    with Store(tmp_path / 'store') as store:
        with pytest.raises(Interrupted):
            acquisition.capture_native_blast_database_bundle(store, target=original.target, reader=original.reader,
                operation_key='selected-collect', directory=directory)
        saved = (directory / selected).read_bytes()
        assert saved and not (directory / 'capture.json').exists()
        monkeypatch.setattr(acquisition, 'artifact_file', retain)
        monkeypatch.setattr(original.reader, 'read_file', read)
        monkeypatch.setattr(acquisition, '_immutable', immutable)
        if stage == 'finalization':
            monkeypatch.setattr(original.reader, 'read_file', lambda *a, **k: pytest.fail('sealed finalization acquired again'))
            monkeypatch.setattr(original.reader, 'authenticate_native_blast_database_attempt', lambda *a, **k: pytest.fail('sealed finalization authenticated again'))
        value = acquisition.capture_native_blast_database_bundle(store, target=original.target, reader=original.reader,
            operation_key='selected-collect', directory=directory)
        assert value['status'] == 'complete', value
        assert (directory / selected).read_bytes().startswith(saved)
        assert original.reader.auth_calls == (1 if stage == 'finalization' else 2)


def test_interrupted_capture_changed_prefix_is_preserved_and_not_missing(tmp_path, monkeypatch):
    import gene_annotation_episode.native_blast_database_acquisition as acquisition
    original = original_attempt(tmp_path)
    directory = tmp_path / 'capture'; directory.mkdir()
    changed = b'changed original prefix'
    (directory / 'plan.capture').write_bytes(changed)
    with Store(tmp_path / 'store') as store:
        value = acquisition.capture_native_blast_database_bundle(store, target=original.target, reader=original.reader,
            operation_key='selected-collect', directory=directory)
        assert value['failures'] == [{'code': 'file_changed', 'artifact_key': None}]
        assert (directory / 'plan.capture').read_bytes() == changed


@pytest.mark.parametrize('role', ['plan', 'bundle'])
@pytest.mark.parametrize('fault,expected', [('missing', 'missing'), ('read', 'file_read_failed'),
    ('size', 'file_size_mismatch'), ('changed', 'file_changed')])
def test_plan_and_bundle_transfer_failures_keep_exact_meaning(tmp_path, monkeypatch, role, fault, expected):
    original = original_attempt(tmp_path)
    remote = str(original.root / ('native-blast-database-plan.json' if role == 'plan' else 'bundle.json'))
    read = original.reader.read_file
    def failure(target, **arguments):
        if arguments['path'] != remote:
            return read(target, **arguments)
        if fault == 'missing':
            raise FileNotFoundError(remote)
        if fault == 'read':
            raise OSError('synthetic transport failure')
        row = read(target, **arguments)
        if fault == 'size' or fault == 'changed' and arguments['offset']:
            row['size_bytes'] += 1
        return row
    monkeypatch.setattr(original.reader, 'read_file', failure)
    with Store(tmp_path / 'store') as store:
        value = capture_native_blast_database_bundle(store, target=original.target, reader=original.reader,
            operation_key='selected-collect', directory=tmp_path / 'capture')
        assert value['failures'] == [{'code': role + '_missing' if expected == 'missing' else expected, 'artifact_key': None}]


@pytest.mark.parametrize('fault', ['plan_missing', 'artifact_missing', 'artifact_symlink', 'ledger', 'current_pointer'])
def test_actual_original_pbs_reader_authenticates_before_capture(tmp_path, monkeypatch, fault):
    from test_native_blast_database_episode_binding import SyntheticHost
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        root, = [path.parent for path in h.workspace.rglob('bundle.json')]
        bundle = json.loads((root / 'bundle.json').read_bytes())
        victim = next(row for row in bundle['artifacts'] if row['role'] == 'primary_report')
        path = root / victim['relative_path']
        if fault == 'plan_missing':
            (root / 'native-blast-database-plan.json').unlink()
        elif fault == 'artifact_missing':
            path.unlink()
        elif fault == 'artifact_symlink':
            other = path.with_name('same-bytes-other-path'); other.write_bytes(path.read_bytes())
            path.unlink(); path.symlink_to(other)
        elif fault == 'ledger':
            value = json.loads((root / 'submission.json').read_bytes()); value['job_id'] = 'other.synthetic'
            save_json(root / 'submission.json', value)
        else:
            save_json(root.parent.parent / 'current.json', {'attempt_id': 'unrelated-current-attempt'})
        before = len(h.calls)
        value = capture_native_blast_database_bundle(h.store, target=h.target, reader=h.family.job_progress_provider.targets,
            operation_key='selected-collect', directory=tmp_path / 'capture')
        if fault == 'current_pointer':
            assert value['status'] == 'complete', value
        else:
            code = {'plan_missing': 'plan_missing', 'artifact_missing': 'file_missing',
                'artifact_symlink': 'file_read_failed', 'ledger': 'attempt_mismatch'}[fault]
            assert value['failures'][0]['code'] == code, value
            if fault == 'ledger':
                assert not any(call['mode'] == 'read_output' for call in h.calls[before:])
            if fault in {'artifact_missing', 'artifact_symlink'}:
                assert value['status'] == 'partial' and victim['artifact_key'] not in value['artifact_refs']
        assert len(list(h.workspace.rglob('synthetic-emitter-invoked'))) == 1
    finally:
        h.store.close()
