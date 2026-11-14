"""Derived absent-execution controls, not genuine unfinished/live workers.

Original completed355 controls are immutable operands. Filesystem relocation,
service-properties, plan intake and artifact Store are explicit test ports.
Actual archived full control validators, native status/collect, current budget
and original host execution/capture validators run; no native dispatch occurs.
"""
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.workflow_budget import active_budget
from .. import native_flux_balance_preparation as host
from .. import native_lifecycle as native
from ..acquisition import AcquisitionError
from ..execution_contracts import canonical
from ..local_jobs import LocalJobPolicy
from ..native_file_capture import NativeFileCaptureError
from ..native_flux_balance_storage import confined_file
from ..library.received_execution_information import fba_operand_comparison
from ..library.received_execution_information.saved_fba_worker_read import archived_worker_validator

FIXTURE = Path(__file__).parent / 'fixtures'
ARTIFACTS = FIXTURE / 'genuine_fba360/store/artifacts'
RECORDS = (
    ('1fb7e38814d514e19259fcd7dc565a1360199d91eb9b61d114c1be6c222161db',
     '19b1bd0d1acd1a9e708cafb9739581736ae1cd60d4bca3e8a5ed5b83eea9e75d'),
    ('82c07aba7fea9d30c3cb28ec3be22a296baf2d1c2ae7e30bba20d4a50f51b122',
     'ce6c801d8aaed12afb7b36e8e537e8613820c0525247452891ead6183533ee29'))


def sha(raw): return hashlib.sha256(raw).hexdigest()


def original(identity):
    raw = (ARTIFACTS / identity[:2] / identity).read_bytes()
    assert sha(raw) == identity
    return raw


def captures(value):
    if type(value) is dict:
        if value.get('version') == 'flux_balance_worker_capture_v1': yield value
        for item in value.values(): yield from captures(item)
    elif type(value) is list:
        for item in value: yield from captures(item)


@pytest.mark.parametrize('record', RECORDS)
@pytest.mark.parametrize('fault', [None, 'missing_native_result', 'missing_worker_result',
    'missing_output', 'corrupt_request', 'corrupt_handle', 'race_handle_at_pins',
    'race_handle_at_collect', 'race_status_at_collect', 'prepared', 'submitting', 'unknown_source'])
def test_existing_controls_use_read_or_real_preflight_without_dispatch(tmp_path, monkeypatch, record, fault):
    execution = json.loads(original(record[0]))
    saved, = captures(json.loads(original(record[1])))
    assert saved['execution_receipt_file']['sha256'] == record[0] and saved['failures'] == []
    intent = deepcopy(execution['intent']); plan = intent['plan']
    selected = archived_worker_validator(intent)
    assert selected.__name__.endswith('.original_355_fba_worker_comparison')
    root, output = tmp_path / 'worker.execution', tmp_path / 'output'
    root.mkdir(); output.mkdir()
    controls = json.loads((FIXTURE / 'fba_existing_handle_controls/control_origins.json').read_text())[record[0]]
    mapping = {}
    for name, original_path in execution['handle']['paths'].items():
        raw = (FIXTURE / 'fba_existing_handle_controls' / record[0] / name).read_bytes()
        assert controls[name]['path'] == original_path and sha(raw) == controls[name]['sha256']
        target = tmp_path / Path(original_path).name
        target.write_bytes(raw); mapping[original_path] = target
    assert json.loads(mapping[execution['handle']['paths']['ready']].read_bytes())['request_sha256'] == execution['handle']['request_sha256']
    assert mapping[execution['handle']['paths']['request']].read_bytes() == execution['request_raw'].encode()
    assert json.loads(mapping[execution['handle']['paths']['status']].read_bytes()) == execution['metadata']['service_exit']
    native_result = json.loads(mapping[execution['handle']['paths']['result']].read_bytes())
    assert native_result['native_returncode'] == execution['returncode']
    assert native_result['observed_scratch_bytes'] == execution['metadata']['observed_scratch_bytes']
    body = deepcopy(execution['handle'])
    if fault in ('prepared', 'submitting'):
        body['stage'] = fault
        for name in ('release', 'status', 'result'):
            mapping[body['paths'][name]].unlink()
    if fault == 'corrupt_handle': body['command'] = [*body['command'], 'changed']
    if fault == 'corrupt_request':
        target = mapping[body['paths']['request']]; target.write_bytes(target.read_bytes() + b' ')
    if fault == 'missing_native_result': mapping[body['paths']['result']].unlink()
    if fault == 'unknown_source': intent['command'][4] = 'unowned.worker'
    handle_path = root / 'worker.handle.json'
    if fault in ('prepared', 'submitting', 'corrupt_handle'):
        handle_path.write_text(canonical(body))
    else:
        handle_path.write_bytes(original(execution['handle_file']['sha256']))
    original_root = Path(execution['intent']['execution_directory'])
    mapping[str(original_root / 'worker.handle.json')] = handle_path
    for name in ('stdout', 'stderr'):
        target = root / ('worker.' + name)
        target.write_bytes(original(execution[name + '_file']['sha256']))
        mapping[body[name]] = target
    (root / 'intent.json').write_text(canonical(intent))
    (output / 'worker-result.json').write_bytes(original(saved['worker_result_file']['sha256']))
    if fault == 'missing_worker_result': (output / 'worker-result.json').unlink()
    before = {str(path): path.read_bytes() for path in mapping.values() if path.exists()}
    environment = dict(os.environ); events = []; triggered = set()
    monkeypatch.setattr(fba_operand_comparison, 'validate_worker_input', lambda value: value)
    monkeypatch.setattr(host, '_layout', lambda value: (tmp_path, root, output))
    monkeypatch.setattr(host, '_locked', lambda value: nullcontext())
    # Preserve original declared paths for _controls; relocate only actual I/O.
    def original_file(directory, relative, **kwargs):
        source = str(Path(directory) / relative)
        assert source in mapping
        target = mapping[source]
        return confined_file(target.parent, target.name, **kwargs)
    monkeypatch.setattr(selected, 'confined_file', original_file)
    real_path = Path
    def relocated_native_path(value):
        return mapping.get(str(value), real_path(value))
    monkeypatch.setattr(native, 'Path', relocated_native_path)
    def properties(unit):
        assert unit == body['unit']
        events.append('properties')
        return {'ActiveState': 'active' if fault == 'submitting' else 'inactive', 'LoadState': 'loaded'}
    monkeypatch.setattr(native, '_properties', properties)
    actual_status = native.status
    def status(handle):
        events.append('status')
        view = actual_status(handle)
        if fault in ('race_handle_at_collect', 'race_status_at_collect') and fault not in triggered:
            triggered.add(fault)
            (handle_path if fault == 'race_handle_at_collect' else mapping[body['paths']['status']]).unlink()
        return view
    monkeypatch.setattr(native, 'status', status)
    actual_collect = native.collect
    def collect(handle):
        events.append('collect')
        return actual_collect(handle)
    monkeypatch.setattr(native, 'collect', collect)
    pins = {row['path']: row for row in selected._all_pins(execution['intent'])}
    def file_pin(path):
        events.append('pin')
        if fault == 'race_handle_at_pins' and fault not in triggered:
            triggered.add(fault); handle_path.unlink()
        return deepcopy(pins[path])
    monkeypatch.setattr(host, 'file_pin', file_pin)
    actual_controls = selected._validate_live_controls
    def checked_controls(handle, value):
        events.append('original_controls')
        return actual_controls(handle, value)
    monkeypatch.setattr(selected, '_validate_live_controls', checked_controls)
    # Actual original validators run over an explicitly controlled artifact
    # transport. New derived partial receipts are labelled by their real bytes.
    retained = tmp_path / 'captured'; retained.mkdir()
    def capture(store, directory, name, format_):
        events.append('capture:' + name)
        target = Path(directory) / name
        if not target.exists(): raise NativeFileCaptureError('capture_file_unavailable')
        raw = target.read_bytes(); identity = sha(raw)
        (retained / identity).write_bytes(raw)
        return {'artifact_ref': 'artifact_' + identity, 'sha256': identity, 'size_bytes': len(raw), 'format': format_}
    monkeypatch.setattr(host, '_capture', capture)
    def retained_file(store, file):
        path = retained / file['sha256']
        if not path.exists(): path = ARTIFACTS / file['sha256'][:2] / file['sha256']
        raw = path.read_bytes()
        assert sha(raw) == file['sha256'] and len(raw) == file['size_bytes']
        return path
    monkeypatch.setattr(host, 'retained_native_file', retained_file)
    def outputs(store, *, directory, declarations):
        assert directory == str(output) and declarations == [row['declared'] for row in saved['outputs']]
        rows = deepcopy(saved['outputs'])
        if fault == 'missing_output': rows[0].update(observed=None, outcome='unavailable', failure='capture_file_unavailable')
        return rows
    monkeypatch.setattr(host, 'capture_declared_native_files', outputs)
    def forbidden(*args, **kwargs): raise AssertionError('existing_old_control_must_not_dispatch_resume_wait_cancel_or_release')
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'cancel', 'release', 'run_job'):
        if hasattr(native, name): monkeypatch.setattr(native, name, forbidden)
    admitted = fault in (None, 'missing_native_result', 'missing_worker_result', 'missing_output')
    if admitted:
        result = host.prepare_flux_balance_result_worker(object(), plan=plan, policy=LocalJobPolicy(21474836480, 4294967296))
        created = json.loads((root / 'execution.json').read_bytes())
        selected.validate_flux_balance_worker_execution(created, plan=plan, plan_file=created['plan_file'])
        assert created['handle'] == execution['handle'] and created['request_raw'] == execution['request_raw']
        assert created['policy'] == execution['policy']
        if fault is None:
            assert created == execution and result == saved
        elif fault == 'missing_native_result':
            assert created['failure']['code'] == 'local_job_execution_error'
            assert [row['code'] for row in result['failures']] == ['binding_unavailable']
        elif fault == 'missing_worker_result':
            assert result['result'] is None and [row['code'] for row in result['failures']] == ['artifact_missing']
        else:
            assert result['outputs'][0]['outcome'] == 'unavailable'
            assert [row['code'] for row in result['failures']] == ['artifact_missing']
        assert events.index('original_controls') < events.index('status') < events.index('collect')
        assert events.count('original_controls') == 2
    else:
        with pytest.raises((ValueError, OSError, AcquisitionError)) as caught:
            host.prepare_flux_balance_result_worker(object(), plan=plan, policy=LocalJobPolicy(21474836480, 4294967296))
        if fault in ('prepared', 'submitting'):
            assert active_budget()['environment_bounds']['memory_bytes'] == 5 * 1024**3
            assert type(caught.value) is AcquisitionError
            assert caught.value.code == 'whole_workflow_budget_unavailable'
            assert caught.value.operational['reason'] == 'native_request_exceeds_environment_bounds'
            assert caught.value.operational['prepared_handle_preserved'] is True
            assert 'collect' not in events
        if fault in ('corrupt_request', 'corrupt_handle', 'unknown_source', 'race_handle_at_pins'):
            assert 'status' not in events and 'collect' not in events
        if fault == 'corrupt_request':
            assert type(caught.value) is ValueError and str(caught.value) == 'fba_preparation_request_mismatch'
        elif fault == 'corrupt_handle':
            assert type(caught.value) is ValueError and str(caught.value) == 'fba_preparation_handle_mismatch'
        elif fault in ('race_handle_at_pins', 'race_handle_at_collect'):
            assert type(caught.value) is FileNotFoundError
        elif fault == 'race_status_at_collect':
            assert type(caught.value) is AcquisitionError and caught.value.code == 'local_job_not_collectable'
            assert events.count('status') == 3 and events.count('collect') == 1
        assert not (root / 'execution.json').exists() and not (root / 'capture.json').exists()
    assert (root / 'intent.json').read_text() == canonical(intent)
    removed = ({str(handle_path)} if fault in ('race_handle_at_pins', 'race_handle_at_collect') else
        {str(mapping[body['paths']['status']])} if fault == 'race_status_at_collect' else set())
    for name, raw in before.items():
        if name in removed: assert not Path(name).exists()
        else: assert Path(name).read_bytes() == raw
    assert dict(os.environ) == environment
    (tmp_path / 'existing-handle-observation.json').write_text(json.dumps({
        'version': 'derived_fba_existing_handle_control_v1', 'original_execution_sha256': record[0],
        'fault': fault, 'events': events, 'service_properties_controlled': True,
        'actual_service_observed': False, 'actual_store_capture': False,
        'native_dispatch_permitted': False, 'partial_or_completed_capture': admitted}, indent=2) + '\n')
