"""Own-axis byte admission and child quota controls; never launch a worker.

The canonical ancestor check is real. Native child observations and dispatch
are explicit local ports; subprocess itself is not globally monkeypatched.
"""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from .test_local_resource_count_free import capacity, handle, raw_state, resources_module, native, jobs


@pytest.mark.parametrize('supplied', [False, True])
def test_fresh_cpu_setting_is_optional_inert_descriptor_metadata(capacity, tmp_path, supplied):
    settings = {'memory_bytes': 20, 'scratch_bytes': 20}
    if supplied: settings['cpu_threads'] = 4
    owner = resources_module.LocalResources(tmp_path / 'optional-cpu', settings)
    assert owner.as_record()['version'] == 'shared_local_resources_v3'
    assert owner.as_record()['limits'] == settings
    assert owner.snapshot()['limits'] == {'memory_bytes': 20, 'scratch_bytes': 20}
    selected, _ = handle(owner.directory, 'requested-many', owner.as_record())
    reservation = owner.reserve(selected, cpu_threads=64, policy=jobs.LocalJobPolicy(10, 10))
    assert reservation['allocation']['cpu_threads'] == 64
    owner.release_reservation(reservation)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    from gene_annotation_episode import workflow_budget
    actual = workflow_budget.active_budget()
    assert actual['environment_bounds'] == {'cpu_percent': 100, 'memory_bytes': 5368709120, 'swap_bytes': 0}
    monkeypatch.setenv(resources_module.DIRECTORY_ENV, str(tmp_path / 'capacity'))
    monkeypatch.setattr(native, '_control', lambda *args: SimpleNamespace(returncode=0, stdout=''))
    monkeypatch.setattr(native, '_properties', lambda unit: {'LoadState': 'not-found'})
    root = tmp_path / 'native'; root.mkdir()
    policy = jobs.LocalJobPolicy(8 * 1024**2, 16 * 1024**2)
    command = ['/controlled/unexecuted-native', '--threads', '4', 'original-input']
    selected = native.prepare_job(command, cwd=root, policy=policy,
        handle_path=root / 'native.handle.json', cpu_threads=4)
    assert selected.read()['metadata']['whole_workflow_budget'] == actual
    return selected, command


def test_released_resume_authenticates_original_workflow_before_events(prepared, monkeypatch):
    selected, _ = prepared
    body = selected.read(); body['stage'] = 'released'
    body['metadata']['whole_workflow_budget']['window_id'] = 'controlled-wrong-owner'
    native.atomic_json(selected.path, body); Path(body['paths']['release']).touch()
    original = selected.path.read_bytes(); events = []
    monkeypatch.setattr(native, '_ensure_event_registration', lambda *args: events.append(args))
    with pytest.raises(native.AcquisitionError, match='whole_workflow_budget_identity_conflict'):
        native.resume_start(selected)
    assert events == [] and selected.path.read_bytes() == original
