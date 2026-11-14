"""Derived missing-capture controls; genuine bytes, controlled storage/layout ports.

No original pending-native claim and no native dispatch. Full archived intent,
execution and final capture validators are actual implementations. Store custody
and original on-disk execution-directory reopening are not claimed by these ports.
"""
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from .. import native_flux_balance_preparation as host
from .. import native_lifecycle as native
from ..execution_contracts import canonical
from ..local_jobs import LocalJobPolicy
from ..native_file_capture import NativeFileCaptureError
from ..library.received_execution_information import fba_operand_comparison
from ..library.received_execution_information.saved_fba_worker_read import archived_worker_validator

ARTIFACTS = Path(__file__).parent / 'fixtures/genuine_fba360/store/artifacts'
RECORDS = (
    ('1fb7e38814d514e19259fcd7dc565a1360199d91eb9b61d114c1be6c222161db',
     '19b1bd0d1acd1a9e708cafb9739581736ae1cd60d4bca3e8a5ed5b83eea9e75d'),
    ('82c07aba7fea9d30c3cb28ec3be22a296baf2d1c2ae7e30bba20d4a50f51b122',
     'ce6c801d8aaed12afb7b36e8e537e8613820c0525247452891ead6183533ee29'),
)


def original(identity):
    raw = (ARTIFACTS / identity[:2] / identity).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == identity
    return raw, json.loads(raw)


def captures(value):
    if type(value) is dict:
        if value.get('version') == 'flux_balance_worker_capture_v1': yield value
        for child in value.values(): yield from captures(child)
    elif type(value) is list:
        for child in value: yield from captures(child)


def fixture(record):
    execution_raw, execution = original(record[0])
    _, publication = original(record[1])
    saved, = captures(publication)
    assert saved['execution_receipt_file']['sha256'] == record[0]
    assert saved['failures'] == []
    assert all(row['outcome'] == 'verified' for row in saved['outputs'])
    assert execution['intent']['version'] == 'flux_balance_worker_intent_v2'
    return execution_raw, execution, saved


@pytest.mark.parametrize('record', RECORDS)
@pytest.mark.parametrize('fault', [None, 'missing_result', 'missing_output', 'corrupt_execution', 'race_loss', 'storage_failure'])
def test_completed_execution_recaptures_without_native_calls(tmp_path, monkeypatch, record, fault):
    raw, execution, saved = fixture(record)
    intent, plan = execution['intent'], execution['intent']['plan']
    original_intent = canonical(intent)
    root, output = tmp_path / 'worker.execution', tmp_path / 'output'
    root.mkdir(); output.mkdir()
    (root / 'intent.json').write_text(original_intent)
    if fault == 'corrupt_execution':
        broken = deepcopy(execution); broken['request_raw'] += ' '
        (root / 'execution.json').write_text(canonical(broken))
    else:
        (root / 'execution.json').write_bytes(raw)
    execution_before = (root / 'execution.json').read_bytes()
    events = []
    # Actual historical plan/path metadata remains unchanged. These explicit
    # ports relocate test I/O, provide already authenticated artifact bytes and
    # isolate the original capture orchestration from actual Store writes.
    monkeypatch.setattr(fba_operand_comparison, 'validate_worker_input', lambda value: value)
    monkeypatch.setattr(host, '_layout', lambda value: (tmp_path, root, output))
    monkeypatch.setattr(host, '_locked', lambda value: nullcontext())
    def retained(store, file):
        path = ARTIFACTS / file['sha256'][:2] / file['sha256']
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == file['sha256'] and len(data) == file['size_bytes']
        return path
    monkeypatch.setattr(host, 'retained_native_file', retained)
    def capture(store, directory, name, format_):
        events.append('capture:' + name)
        if name == 'plan.json':
            assert json.loads((root / name).read_bytes()) == plan
            if fault == 'race_loss': (root / 'execution.json').unlink()
            return deepcopy(execution['plan_file'])
        if name == 'execution.json':
            assert (root / name).read_bytes() == raw
            return deepcopy(saved['execution_receipt_file'])
        assert name == 'worker-result.json' and directory == output
        if fault == 'missing_result': raise NativeFileCaptureError('capture_file_unavailable')
        if fault == 'storage_failure': raise NativeFileCaptureError('retained_artifact_unavailable')
        return deepcopy(saved['worker_result_file'])
    monkeypatch.setattr(host, '_capture', capture)
    def capture_outputs(store, *, directory, declarations):
        events.append('outputs')
        assert directory == str(output)
        assert declarations == [row['declared'] for row in saved['outputs']]
        rows = deepcopy(saved['outputs'])
        if fault == 'missing_output':
            rows[0].update(observed=None, outcome='unavailable', failure='capture_file_unavailable')
        return rows
    monkeypatch.setattr(host, 'capture_declared_native_files', capture_outputs)
    selected = archived_worker_validator(intent)
    actual_validate = selected.validate_flux_balance_worker_execution
    def validate(*args, **kwargs):
        events.append('validate_execution')
        return actual_validate(*args, **kwargs)
    monkeypatch.setattr(selected, 'validate_flux_balance_worker_execution', validate)
    def forbidden(*args, **kwargs): raise AssertionError('completed_receipt_must_not_call_native')
    for name in ('prepare_job', 'resume_start', 'start_prepared', 'wait_job', 'status'):
        monkeypatch.setattr(native, name, forbidden)
    if fault in ('corrupt_execution', 'race_loss', 'storage_failure'):
        with pytest.raises(ValueError) as caught:
            host.prepare_flux_balance_result_worker(object(), plan=plan, policy=LocalJobPolicy(21474836480, 4294967296))
        if fault == 'corrupt_execution': assert str(caught.value) == 'fba_preparation_request_mismatch'
        elif fault == 'race_loss': assert str(caught.value) == 'fba_preparation_execution_mismatch'
        else: assert caught.value.code == 'retained_artifact_unavailable'
        assert not (root / 'capture.json').exists()
    else:
        result = host.prepare_flux_balance_result_worker(object(), plan=plan, policy=LocalJobPolicy(21474836480, 4294967296))
        assert json.loads((root / 'capture.json').read_bytes()) == result
        if fault is None: assert result == saved
        elif fault == 'missing_result':
            assert result['result'] is None and result['worker_result_file'] is None and result['outputs'] == []
            assert [(row['code'], row['field']) for row in result['failures']] == [('artifact_missing', '/worker/result')]
        else:
            assert result['outputs'][0]['outcome'] == 'unavailable'
            assert result['outputs'][1:] == saved['outputs'][1:]
            assert [(row['code'], row['field']) for row in result['failures']] == [('artifact_missing', '/worker/outputs/' + host.OUTPUTS[0][0])]
    assert events[:2] == ['capture:plan.json', 'validate_execution']
    if fault in ('race_loss', 'corrupt_execution'): assert events == events[:2]
    else: assert events[2:4] == ['capture:execution.json', 'capture:worker-result.json']
    assert (root / 'intent.json').read_text() == original_intent
    if fault == 'race_loss': assert not (root / 'execution.json').exists()
    else: assert (root / 'execution.json').read_bytes() == execution_before
    assert not (root / 'worker.handle.json').exists()
    assert not any(path.name.startswith('.local-job-') for path in tmp_path.iterdir())


@pytest.mark.parametrize('fault', ['unknown_producer', 'existing_handle_no_execution'])
def test_no_new_authority_for_other_pending_states(tmp_path, monkeypatch, fault):
    raw, execution, _ = fixture(RECORDS[0])
    intent = deepcopy(execution['intent']); plan = intent['plan']
    root = tmp_path / 'worker.execution'; root.mkdir()
    if fault == 'unknown_producer':
        intent['command'][4] = 'unowned.worker'
        (root / 'execution.json').write_bytes(raw)
    else:
        (root / 'worker.handle.json').write_text('{}')
    (root / 'intent.json').write_text(canonical(intent))
    monkeypatch.setattr(fba_operand_comparison, 'validate_worker_input', lambda value: value)
    monkeypatch.setattr(host, '_layout', lambda value: (tmp_path, root, tmp_path / 'output'))
    monkeypatch.setattr(host, '_locked', lambda value: nullcontext())
    def forbidden(*args, **kwargs): raise AssertionError('unexpected_capture_or_native_call')
    monkeypatch.setattr(host, '_capture', forbidden)
    if fault == "existing_handle_no_execution":
        from ..native_flux_balance_storage import confined_file
        selected = archived_worker_validator(intent)
        pins = {row["path"]: row for row in selected._all_pins(intent)}
        monkeypatch.setattr(host, "file_pin", lambda path: deepcopy(pins[path]))
        def malformed_handle_file(directory, relative, **options):
            assert relative == "worker.handle.json"
            return confined_file(root, relative, **options)
        monkeypatch.setattr(selected, "confined_file", malformed_handle_file)
        def plan_capture(store, directory, name, format_):
            assert directory == root and name == "plan.json"
            return deepcopy(execution["plan_file"])
        monkeypatch.setattr(host, "_capture", plan_capture)
    for name in ('prepare_job', 'resume_start', 'start_prepared', 'wait_job', 'status'):
        monkeypatch.setattr(native, name, forbidden)
    with pytest.raises(ValueError):
        host.prepare_flux_balance_result_worker(object(), plan=plan, policy=LocalJobPolicy(21474836480, 4294967296))
    assert not (root / 'capture.json').exists()
    assert (root / 'intent.json').read_text() == canonical(intent)
