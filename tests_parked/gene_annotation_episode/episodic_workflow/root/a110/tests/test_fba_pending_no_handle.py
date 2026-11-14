"""Archived intent controls plus actual current preflight; no worker execution.

The orchestration test declares plan/layout/Store artifact/pin-read ports. It is
not a genuine unfinished historical worker. Intent validation uses actual saved
producer bytes, and native admission uses the real current workflow budget.
"""
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.workflow_budget import active_budget
from .. import native_lifecycle as native
from .. import native_flux_balance_preparation as host
from ..acquisition import AcquisitionError
from ..execution_contracts import canonical
from ..local_jobs import LocalJobPolicy
from ..library.received_execution_information import fba_operand_comparison
from ..library.received_execution_information import pending_fba_worker_admission as pending

ARTIFACTS = Path(__file__).parent / 'fixtures/genuine_fba360/store/artifacts'
EXECUTIONS = ('1fb7e38814d514e19259fcd7dc565a1360199d91eb9b61d114c1be6c222161db',
              '82c07aba7fea9d30c3cb28ec3be22a296baf2d1c2ae7e30bba20d4a50f51b122')


def original_intent(identity):
    raw = (ARTIFACTS / identity[:2] / identity).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == identity
    return json.loads(raw)['intent']


def files(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


@pytest.mark.parametrize('identity', EXECUTIONS)
def test_authentic_intent_retains_full_policy_and_quantities(identity):
    intent = original_intent(identity); before = canonical(intent)
    comparison = pending.validated_pending_comparison(intent, intent['plan'])
    assert comparison.__name__.endswith('.original_355_fba_worker_comparison')
    policy = pending.pending_admission_policy(intent, comparison)
    assert type(policy) is LocalJobPolicy
    assert policy.to_dict() == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    assert intent['policy'] == {**policy.to_dict(), 'wall_seconds': None}
    assert canonical(intent) == before


@pytest.mark.parametrize('fault', ['smaller_policy', 'environment', 'unknown_source', 'unknown_command'])
def test_corrupt_or_unknown_producer_cannot_gain_pending_authority(fault):
    intent = original_intent(EXECUTIONS[0])
    if fault == 'smaller_policy': intent['policy']['memory_bytes'] = 5 * 1024**3
    elif fault == 'environment': intent['environment']['OMP_NUM_THREADS'] = '2'
    elif fault == 'unknown_source':
        row, = [row for row in intent['source_pins'] if row['path'].endswith('/native_flux_balance_contracts.py')]
        row['sha256'] = '0' * 64
    else: intent['command'][4] = 'unowned.worker'
    before = canonical(intent)
    if fault.startswith('unknown'):
        assert pending.validated_pending_comparison(intent, intent['plan']) is None
    else:
        with pytest.raises(ValueError): pending.validated_pending_comparison(intent, intent['plan'])
    assert canonical(intent) == before


@pytest.mark.parametrize('identity', EXECUTIONS)
def test_actual_native_preflight_rejects_twenty_gib_without_controls(tmp_path, identity):
    intent = original_intent(identity)
    selected = pending.validated_pending_comparison(intent, intent['plan'])
    policy = pending.pending_admission_policy(intent, selected)
    assert active_budget()['environment_bounds']['memory_bytes'] == 5 * 1024**3
    original = canonical(intent); before = files(tmp_path); environment = dict(os.environ)
    with pytest.raises(AcquisitionError) as caught:
        native.prepare_job(intent['command'], cwd=tmp_path, policy=policy,
            handle_path=tmp_path / 'worker.handle.json', env=intent['environment'])
    assert caught.value.code == 'whole_workflow_budget_unavailable'
    assert caught.value.phase == 'local_preflight'
    assert caught.value.operational['reason'] == 'native_request_exceeds_environment_bounds'
    assert caught.value.operational['prepared_handle_preserved'] is False
    assert files(tmp_path) == before and dict(os.environ) == environment
    assert canonical(intent) == original


@pytest.mark.parametrize('fault', [None, 'pin_mismatch', 'existing_handle'])
def test_host_validation_pins_then_original_admission_slot(tmp_path, monkeypatch, fault):
    intent = original_intent(EXECUTIONS[0]); plan = intent['plan']
    common, root, output = tmp_path, tmp_path / 'worker.execution', tmp_path / 'output'
    root.mkdir()
    (root / 'intent.json').write_text(canonical(intent))
    if fault == 'existing_handle': (root / 'worker.handle.json').write_text('{}')
    original_controls = files(root); calls = []
    # Explicit source-orchestration ports: this test does not claim a real Store
    # artifact capture, copied historical runtime, or native input intake.
    monkeypatch.setattr(fba_operand_comparison, 'validate_worker_input', lambda value: value)
    monkeypatch.setattr(host, '_layout', lambda value: (common, root, output))
    monkeypatch.setattr(host, '_locked', lambda value: nullcontext())
    monkeypatch.setattr(host, '_capture', lambda *args: {'controlled_capture_port': True})
    original_validate = pending.validated_pending_comparison
    def validate(*args, **kwargs):
        calls.append('validate')
        return original_validate(*args, **kwargs)
    monkeypatch.setattr(pending, 'validated_pending_comparison', validate)
    comparison = original_validate(intent, plan)
    if fault == "existing_handle":
        from ..native_flux_balance_storage import confined_file
        def malformed_handle_file(directory, relative, **options):
            assert relative == "worker.handle.json"
            return confined_file(root, relative, **options)
        monkeypatch.setattr(comparison, "confined_file", malformed_handle_file)
    pins = {row['path']: row for row in comparison._all_pins(intent)}
    def file_pin(path):
        calls.append('pin')
        value = deepcopy(pins[path])
        if fault == 'pin_mismatch': value['sha256'] = '0' * 64
        return value
    monkeypatch.setattr(host, 'file_pin', file_pin)
    actual_prepare = native.prepare_job
    def prepare(*args, **kwargs):
        calls.append('admission')
        assert args[0] == intent['command'] and kwargs['env'] == intent['environment']
        assert kwargs['policy'].memory_bytes == 21474836480
        return actual_prepare(*args, **kwargs)
    monkeypatch.setattr(native, 'prepare_job', prepare)
    def no_resume(*args, **kwargs):
        raise AssertionError('old_worker_must_not_reach_resume_or_dispatch')
    monkeypatch.setattr(native, 'resume_start', no_resume)
    if fault is None:
        with pytest.raises(AcquisitionError) as caught:
            host.prepare_flux_balance_result_worker(object(), plan=plan,
                policy=LocalJobPolicy(21474836480, 4294967296))
        assert caught.value.code == 'whole_workflow_budget_unavailable'
        assert calls == ['validate', *(['pin'] * len(pins)), 'admission']
        assert not (root / 'worker.handle.json').exists()
    else:
        with pytest.raises(ValueError):
            host.prepare_flux_balance_result_worker(object(), plan=plan,
                policy=LocalJobPolicy(21474836480, 4294967296))
        assert calls == (['validate', 'pin'] if fault == 'pin_mismatch' else ['pin'] * len(pins))
    # Original intent/handle bytes unchanged; the original immutable plan write
    # remains in the original position and is not a new execution receipt.
    for name, digest in original_controls.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
    assert not (root / 'execution.json').exists() and not (root / 'capture.json').exists()
