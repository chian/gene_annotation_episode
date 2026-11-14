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


@pytest.mark.parametrize('version', ['shared_local_resources_v1', 'shared_local_resources_v2'])
def test_existing_cpu_metadata_is_inert_and_exactly_authenticated(capacity, version):
    definition = capacity.as_record()
    definition['version'] = version
    definition['limits']['cpu_threads'] = 1
    if version == 'shared_local_resources_v1':
        definition['limits']['max_running_jobs'] = 1
    raw = json.dumps(definition, sort_keys=True)
    with closing(sqlite3.connect(capacity.path)) as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,)); db.commit()
    owner = resources_module.LocalResources.reopen(definition)
    before = raw_state(owner.path)
    same = resources_module.LocalResources(owner.directory, dict(definition['limits']))
    assert same.as_record() == definition
    with pytest.raises(ValueError, match='local_resource_limits_conflict'):
        resources_module.LocalResources(owner.directory, {'cpu_threads': 4})
    assert raw_state(owner.path) == before
    reservations = []
    for name in ('thread-metadata-one', 'thread-metadata-two'):
        selected, original = handle(owner.directory, name, definition)
        reservation = owner.reserve(selected, cpu_threads=64, policy=jobs.LocalJobPolicy(10, 10))
        owner.validate_reservation(reservation)
        assert reservation['allocation']['cpu_threads'] == 64
        assert selected.path.read_bytes() == original
        reservations.append(reservation)
    view = owner.snapshot()
    assert view['available'] == {'memory_bytes': 10, 'scratch_bytes': 10}
    assert [row['allocation']['cpu_threads'] for row in view['jobs']] == [64, 64]
    assert owner.as_record() == definition
    for reservation in reservations:
        native._release_capacity({'capacity_reservation': reservation})
    assert raw_state(owner.path) == before


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


@pytest.mark.parametrize('version', ['shared_local_resources_v1', 'shared_local_resources_v2'])
def test_missing_custom_historical_descriptor_retains_default_initialization(capacity, tmp_path, version):
    directory = tmp_path / 'custom-missing'
    limits = {'cpu_threads': 4, 'memory_bytes': 20, 'scratch_bytes': 20}
    if version == 'shared_local_resources_v1': limits['max_running_jobs'] = 1
    definition = {'version': version, 'resource_id': resources_module._resource_id(),
        'directory': str(directory), 'limits': limits}
    with pytest.raises(ValueError, match='local_resource_binding_conflict'):
        resources_module.LocalResources.reopen(definition)
    initialized = json.loads(raw_state(directory / 'capacity.sqlite3')['configuration'][0][1])
    expected = {'cpu_threads': 1, 'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    if version == 'shared_local_resources_v1': expected['max_running_jobs'] = 1
    assert initialized == {**definition, 'limits': expected}


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


@pytest.mark.parametrize('descriptorless', [False, True])
def test_new_dispatch_preserves_requested_metadata_and_fixed_cpu_quota(prepared, monkeypatch, descriptorless):
    selected, command = prepared
    body = selected.read()
    assert body['metadata']['cpu_threads'] == 4 and body['metadata']['cpu_quota_percent'] == 100
    body['metadata']['cpu_quota_percent'] = 200  # Must be replaced only at new dispatch.
    if descriptorless: del body['metadata']['local_resources']
    native.atomic_json(selected.path, body)
    request = Path(body['paths']['request']).read_bytes()
    submitted = []
    def dispatch(argv, **kwargs):
        stored = selected.read()
        assert stored['metadata']['cpu_threads'] == 4
        assert stored['metadata']['cpu_quota_percent'] == 100 and stored['stage'] == 'submitting'
        assert 'CPUQuota=100%' in argv and 'CPUQuota=400%' not in argv and 'CPUQuota=200%' not in argv
        submitted.append(argv)
        return SimpleNamespace(returncode=0)
    # Replace this module's subprocess binding, not subprocess.run shared by
    # canonical workflow_budget. The latter keeps real ancestor authentication.
    monkeypatch.setattr(native, 'subprocess', SimpleNamespace(run=dispatch))
    monkeypatch.setattr(native, 'resume_start', lambda chosen, **kwargs: chosen)
    assert native.start_prepared(selected) is selected
    assert len(submitted) == 1 and selected.read()['command'] == command
    assert Path(body['paths']['request']).read_bytes() == request
    native._release_capacity(selected.read())


def observed_child(selected, tmp_path, monkeypatch, percent):
    from gene_annotation_episode import workflow_budget
    body = selected.read(); body['stage'] = 'submitting'
    native.atomic_json(selected.path, body)
    Path(body['paths']['ready']).write_text(json.dumps({'request_sha256': body['request_sha256']}))
    root = tmp_path / 'child-observation'; root.mkdir()
    group = root / 'observed-child'; group.mkdir()
    (group / 'cpu.max').write_text(f'{percent * 1000} 100000\n')
    memory = body['metadata']['policy']['memory_bytes']
    (group / 'memory.max').write_text(str(memory)); (group / 'memory.swap.max').write_text('0')
    props = {'ControlGroup': '/observed-child', 'Slice': workflow_budget.SLICE,
        'BindsTo': workflow_budget.UNIT, 'MemoryMax': str(memory), 'MemorySwapMax': '0',
        'KillMode': 'control-group', 'OOMPolicy': 'kill'}
    monkeypatch.setattr(native, '_properties', lambda unit: props)
    monkeypatch.setattr(native, 'Path', lambda *parts: root if parts == ('/sys/fs/cgroup',) else Path(*parts))
    return body


@pytest.mark.parametrize('legacy', [False, True])
@pytest.mark.parametrize('wrong_ratio', [False, True])
def test_resume_preserves_current_and_original_child_quota_under_actual_ancestor(prepared, tmp_path, monkeypatch, legacy, wrong_ratio):
    selected, command = prepared
    body = selected.read()
    if legacy: del body['metadata']['cpu_quota_percent']
    native.atomic_json(selected.path, body)
    percent = (400 if legacy else 100) if not wrong_ratio else (100 if legacy else 400)
    body = observed_child(selected, tmp_path, monkeypatch, percent)
    request = Path(body['paths']['request']).read_bytes()
    if wrong_ratio:
        with pytest.raises(native.AcquisitionError) as error:
            native.resume_start(selected)
        assert error.value.operational['reason'] == 'cgroup_limits_not_verified'
        assert not Path(body['paths']['release']).exists()
    else:
        assert native.resume_start(selected) is selected
        saved = selected.read()
        assert saved['metadata']['verified_cgroup']['cpu_max'] == f'{percent * 1000} 100000'
        assert ('cpu_quota_percent' in saved['metadata']) is not legacy
        assert ('cpu_quota_percent' in saved['metadata']['verified_cgroup']) is not legacy
    assert selected.read()['command'] == command and selected.read()['metadata']['cpu_threads'] == 4
    assert Path(body['paths']['request']).read_bytes() == request


@pytest.mark.parametrize('marker', [None, '100', {}, True, 200])
def test_malformed_or_noncanonical_submitted_marker_is_rejected_before_arithmetic(prepared, tmp_path, monkeypatch, marker):
    selected, _ = prepared
    body = selected.read(); body['metadata']['cpu_quota_percent'] = marker
    native.atomic_json(selected.path, body)
    body = observed_child(selected, tmp_path, monkeypatch, 100)
    with pytest.raises(native.AcquisitionError) as error:
        native.resume_start(selected)
    assert error.value.operational['reason'] == 'cgroup_limits_not_verified'
    assert not Path(body['paths']['release']).exists()


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
