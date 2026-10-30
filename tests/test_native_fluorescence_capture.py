"""Actual Store byte custody and selected output windows, not scientific credit."""
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity
from gene_annotation_episode.native_fluorescence_capture import capture_fluorescence_native_files
from gene_annotation_episode.native_fluorescence_contracts import validate_fluorescence_native_capture
from gene_annotation_episode.native_fluorescence_observations import fluorescence_observed_files, read_fluorescence_output
from gene_annotation_episode.native_file_capture import NativeFileCaptureError
from gene_annotation_episode.state import Store
from test_native_fluorescence_contracts import plan, parsed_batch
from gene_annotation_episode import fluorescence_event_contracts as core


def selected_files(original):
    return {row['role']: Path(original['attempt_directory']) / row['relative_path'] for row in original['outputs']}


def retain_one(original):
    paths = selected_files(original)
    binding = original['requested_job']['native_fluorescence']['inputs'][0]
    for path in paths.values(): path.parent.mkdir(parents=True, exist_ok=True)
    paths['event_input:0'].write_bytes(Path(binding['path']).read_bytes())
    paths['event_batch:0'].write_bytes(core.canonical(parsed_batch(original)) + b'\n')
    return paths


def captured(store, original, **changes):
    arguments = {'original_plan': original, 'source_action_receipt_ref': 'artifact_' + '3' * 64,
        'writer_closure_receipt_ref': 'artifact_' + '4' * 64, 'driver_started': True}
    arguments.update(changes)
    return capture_fluorescence_native_files(store, **arguments)


def test_missing_manifest_keeps_independently_retained_original_and_batch(tmp_path):
    original = plan(tmp_path)
    paths = retain_one(original)
    with Store(tmp_path / 'store') as store:
        capture = captured(store, original)
        assert [r['role'] for r in capture['files']] == ['event_input:0', 'event_batch:0', 'manifest']
        assert capture['files'][-1]['retained'] is None
        assert capture['failures'] == [{'code': 'capture_file_unavailable', 'stage': 'capture', 'input_index': None, 'role': 'manifest'}]
        for row in capture['files'][:2]:
            assert Path(row['retained']['path']).read_bytes() == paths[row['role']].read_bytes()
        copy = validate_fluorescence_native_capture(capture, original_plan=original)
        assert copy == capture and copy is not capture
        # The original producer can disappear without changing retained bytes.
        for path in paths.values(): path.unlink(missing_ok=True)
        assert Path(capture['files'][1]['retained']['path']).read_bytes()


def test_capture_preserves_actual_wrong_original_bytes_for_worker_qualification(tmp_path):
    original = plan(tmp_path)
    paths = retain_one(original)
    paths['event_input:0'].write_bytes(b'changed producer bytes')
    with Store(tmp_path / 'store') as store:
        capture = captured(store, original)
        retained = capture['files'][0]['retained']
        assert retained['file'] != original['requested_job']['native_fluorescence']['inputs'][0]['source']['file']
        assert Path(retained['path']).read_bytes() == b'changed producer bytes'


def test_capture_storage_failure_is_not_reported_as_missing_producer(tmp_path, monkeypatch):
    original = plan(tmp_path)
    def failure(*args, **kwargs): raise NativeFileCaptureError('retained_artifact_unavailable')
    monkeypatch.setattr('gene_annotation_episode.native_fluorescence_capture.capture_native_file', failure)
    with pytest.raises(NativeFileCaptureError, match='retained_artifact_unavailable'):
        captured(None, original)


def test_capture_contract_failure_precedes_file_access(tmp_path, monkeypatch):
    original = plan(tmp_path)
    monkeypatch.setattr('gene_annotation_episode.native_fluorescence_capture.capture_native_file',
        lambda *args, **kwargs: pytest.fail('file capture before contract validation'))
    with pytest.raises(ValueError): captured(None, original, driver_started=1)


@pytest.mark.parametrize('change', ['plan', 'role', 'path', 'file_format', 'retained_path', 'failure_index'])
def test_capture_cannot_relabel_original_outputs(tmp_path, change):
    original = plan(tmp_path)
    retain_one(original)
    with Store(tmp_path / 'store') as store:
        capture = captured(store, original)
        if change == 'plan': capture['original_plan_sha256'] = '0' * 64
        if change == 'role': capture['files'][0]['role'] = 'event_input:1'
        if change == 'path': capture['files'][0]['relative_path'] = 'elsewhere'
        if change == 'file_format': capture['files'][0]['retained']['file']['format'] = 'guessed'
        if change == 'retained_path': capture['files'][0]['retained']['path'] = '/not/a/store/file'
        if change == 'failure_index': capture['failures'][0]['input_index'] = 90
        with pytest.raises(ValueError): validate_fluorescence_native_capture(capture, original_plan=original)


def test_observations_expose_actual_windows_and_never_source_bytes(tmp_path):
    original = plan(tmp_path)
    paths = retain_one(original)
    root = Path(original['identity']['execution_id']).parent
    (root / 'stdout.log').write_bytes(b'actual selected log\n')
    (root / 'stderr.log').write_bytes(b'')
    outputs, logs, available = fluorescence_observed_files(original, {'terminal': True}, log_window_bytes=8, log_roles=['stdout'])
    assert available is False
    assert logs[0]['offset'] == len(b'actual selected log\n') - 8
    assert outputs[0]['writer_closed'] is True and outputs[-2]['writer_closed'] is True
    assert not any('count' in row for row in outputs)
    window = read_fluorescence_output(original, path=str(root / 'stdout.log'), offset=7, limit=8)
    assert window['returned_bytes'] == 8 and window['text_utf8'] == 'selected'
    with pytest.raises(ValueError, match='original_output_path_required'):
        read_fluorescence_output(original,
            path=original['requested_job']['native_fluorescence']['inputs'][0]['path'], offset=0, limit=8)
