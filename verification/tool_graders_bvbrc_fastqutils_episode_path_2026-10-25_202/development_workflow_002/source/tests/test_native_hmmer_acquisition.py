"""Complete capture of retained B004 native outputs and explicit custody faults.

These fixtures copy producer manifests/native bytes and rebase only the test
directory/realized paths. A stub supplies the frozen retained plan because these
producer-only fixtures did not originate in practical execution. This suite
does not claim that stub verifies launch ownership; the Workflow companion does.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import native_hmmer_acquisition as acquisition
from gene_annotation_episode.native_hmmer_contracts import compile_native_hmmer_job
from gene_annotation_episode.state import Store
from test_native_hmmer_results_integration import LABELS, PRODUCER


def retained_capture(tmp_path, monkeypatch, label='hmmsearch_search_ordinary'):
    plan = json.loads((PRODUCER / label / 'plan.json').read_text())
    original = Path(plan['attempt_directory'])
    root = tmp_path / 'retained-attempt'
    shutil.copytree(original, root)
    plan['attempt_directory'] = str(root)
    bundle = json.loads((root / 'bundle.json').read_text())
    staged = {row['role']: str(root / row['relative_path']) for row in bundle['inputs']}
    compiled = compile_native_hmmer_job(plan['requested_job']['native_hmmer'],
        input_paths=staged, output_directory=str(root))
    bundle['realized_argv'] = compiled['argv']
    bundle['environment'] = {**compiled['environment'],
        **{key: str(root / 'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')},
        'XDG_CACHE_HOME': str(root / 'cache')}
    (root / 'bundle.json').write_text(json.dumps(bundle))
    target = {'resource_kind': 'local', 'run_id': plan['identity']['run_id'],
        'execution_id': plan['identity']['execution_id'],
        'assignment': {'requested_job': deepcopy(plan['requested_job'])}}
    monkeypatch.setattr(acquisition, 'local_hmmer_plan', lambda assignment, execution_id: deepcopy(plan))
    return root, plan, bundle, target


@pytest.mark.parametrize('label', LABELS)
def test_retained_six_program_modes_capture_every_original_byte(tmp_path, monkeypatch, label):
    root, plan, bundle, target = retained_capture(tmp_path, monkeypatch, label)
    with Store(tmp_path / 'state') as store:
        result = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert result['bundle_validated'] and result['complete'], result['failures']
        assert result['invalid_artifacts'] == []
        assert json.loads(store.get_artifact(result['bundle_artifact_ref'])) == bundle
        assert len(result['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts'])
        for row in result['artifacts']:
            assert store.get_artifact(row['artifact_ref']) == (root / row['relative_path']).read_bytes()
        snapshot = deepcopy(result)
        shutil.rmtree(root)
        def forbidden(*args, **kwargs):
            raise AssertionError('replay read original native plan/files')
        monkeypatch.setattr(acquisition, 'local_hmmer_plan', forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == snapshot


@pytest.mark.parametrize('fault', ['digest', 'size', 'missing', 'symlink'])
def test_changed_native_file_is_failed_custody_and_valid_siblings_survive(tmp_path, monkeypatch, fault):
    root, plan, bundle, target = retained_capture(tmp_path, monkeypatch)
    selected = next(row for row in bundle['artifacts'] if row['role'] == 'tblout')
    path = root / selected['relative_path']
    original = path.read_bytes()
    if fault == 'digest':
        path.write_bytes(b'!' + original[1:])
    elif fault == 'size':
        selected['size_bytes'] += 1
        (root / 'bundle.json').write_text(json.dumps(bundle))
    elif fault == 'missing':
        path.unlink()
    else:
        outside = tmp_path / 'outside.tbl'
        outside.write_bytes(original)
        path.unlink()
        path.symlink_to(outside)
    with Store(tmp_path / 'state') as store:
        result = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert result['bundle_validated'] and not result['complete']
        assert any(row['role'] == 'stdout' for row in result['artifacts'])
        assert not any(row['role'] == 'tblout' for row in result['artifacts'])
        assert len(result['failures']) == 1
        if fault in {'digest', 'size'}:
            invalid, = result['invalid_artifacts']
            assert invalid['role'] == 'tblout'
            assert store.get_artifact(invalid['artifact_ref']) == path.read_bytes()
            assert 'digest_mismatch' in result['failures'][0]['code']
        else:
            assert result['invalid_artifacts'] == []


@pytest.mark.parametrize('field', ['run_id', 'resource_id', 'execution_id', 'attempt_id', 'operation_key', 'requested_job'])
def test_original_manifest_rejects_wrong_native_identity(tmp_path, monkeypatch, field):
    root, plan, bundle, target = retained_capture(tmp_path, monkeypatch)
    if field == 'requested_job':
        bundle['requested_job']['native_hmmer']['metadata']['forged'] = True
    else:
        bundle['identity'][field] = 'different-original-work'
    (root / 'bundle.json').write_text(json.dumps(bundle))
    with Store(tmp_path / 'state') as store:
        result = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert not result['bundle_validated'] and not result['complete']
        assert result['artifacts'] == [] and result['invalid_artifacts'] == []
        assert result['failures'][0]['code'] == 'native_hmmer_original_bundle_identity_conflict'
        assert json.loads(store.get_artifact(result['bundle_artifact_ref'])) == bundle


@pytest.mark.parametrize('raw', [b'{', b'[]', b'null', b'{"version":"native_hmmer_bundle_v1"}'])
def test_malformed_manifest_is_retained_as_failed_capture(tmp_path, monkeypatch, raw):
    root, plan, bundle, target = retained_capture(tmp_path, monkeypatch)
    (root / 'bundle.json').write_bytes(raw)
    with Store(tmp_path / 'state') as store:
        result = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert not result['bundle_validated'] and not result['complete']
        assert result['failures'] and result['artifacts'] == []
        assert store.get_artifact(result['bundle_artifact_ref']) == raw


def test_capture_replay_rejects_retained_artifact_corruption(tmp_path, monkeypatch):
    root, plan, bundle, target = retained_capture(tmp_path, monkeypatch)
    with Store(tmp_path / 'state') as store:
        result = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        reference = result['artifacts'][0]['artifact_ref']
        path = acquisition.artifact_path(store, reference)
        path.write_bytes(path.read_bytes() + b'corrupt')
        with pytest.raises(ValueError):
            acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')


@pytest.mark.parametrize('role', ['stdout', 'included_msa'])
def test_success_manifest_cannot_omit_a_required_original_output(tmp_path, monkeypatch, role):
    root, plan, bundle, target = retained_capture(tmp_path, monkeypatch)
    assert any(row['role'] == role for row in bundle['artifacts'])
    bundle['artifacts'] = [row for row in bundle['artifacts'] if row['role'] != role]
    assert bundle['returncode'] == 0 and bundle['failures'] == []
    (root / 'bundle.json').write_text(json.dumps(bundle))
    with Store(tmp_path / 'state') as store:
        result = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert not result['complete'], result
        assert result['failures']


def test_truthful_failed_manifest_preserves_actual_available_partial_files(tmp_path, monkeypatch):
    root, plan, bundle, target = retained_capture(tmp_path, monkeypatch)
    bundle['artifacts'] = [row for row in bundle['artifacts'] if row['role'] != 'stdout']
    bundle['returncode'] = 1
    bundle['failures'] = [{'stage': 'native', 'code': 'native_nonzero', 'role': None,
                           'detail': {'returncode': 1}}]
    (root / 'bundle.json').write_text(json.dumps(bundle))
    with Store(tmp_path / 'state') as store:
        result = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert result['bundle_validated']
        assert len(result['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts'])
        retained = json.loads(store.get_artifact(result['bundle_artifact_ref']))
        assert retained['returncode'] == 1 and retained['failures'] == bundle['failures']
