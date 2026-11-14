"""Controlled capacity-row contracts; no worker, process or native dispatch.

The legacy DB is a source-contract fixture built from the original two-table
schema and exact v1 descriptor shape, not an authenticated historical run.
Quantity values below are arithmetic data, never launcher allocations.
"""
from contextlib import closing
import importlib
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

AXIS = 'a110'
# Independent original defaults.toml authority, SHA256 d8bc88d4cd0a1eb29c5da406dce3ddb28e825f0f759b02a17793fb9bb2b16fc8.
ORIGINAL_V1_LIMITS = {'max_running_jobs': 1, 'cpu_threads': 1,
    'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
resources_module = importlib.import_module('gene_annotation_episode.episodic_workflow.root.' + AXIS + '.local_resources')
native = importlib.import_module('gene_annotation_episode.episodic_workflow.root.' + AXIS + '.native_lifecycle')
jobs = importlib.import_module('gene_annotation_episode.episodic_workflow.root.' + AXIS + '.local_jobs')
guidance = importlib.import_module('gene_annotation_episode.episodic_workflow.root.' + AXIS + '.execution_guidance')


def raw_state(path):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        return {
            'schema': db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall(),
            'configuration': db.execute('SELECT * FROM configuration ORDER BY id').fetchall(),
            'reservations': db.execute('SELECT * FROM reservations ORDER BY unit').fetchall(),
        }


@pytest.fixture
def capacity(tmp_path, monkeypatch):
    monkeypatch.setattr(resources_module, '_resource_id', lambda: 'controlled-host')
    monkeypatch.setattr(resources_module, '_boot', lambda: 'controlled-boot')
    monkeypatch.setattr(resources_module, '_process_start', lambda pid: 'controlled-start')
    monkeypatch.setattr(native, '_properties', lambda unit: {'ActiveState': 'inactive'})
    monkeypatch.setattr(native, '_control', lambda argv: SimpleNamespace(returncode=0, stdout=''))
    owner = resources_module.LocalResources(tmp_path / 'capacity',
        {'cpu_threads': 3, 'memory_bytes': 30, 'scratch_bytes': 30})
    return owner


def legacy(owner):
    definition = owner.as_record()
    definition['version'] = 'shared_local_resources_v1'
    definition['limits']['max_running_jobs'] = 1
    raw = json.dumps(definition, sort_keys=True)
    with closing(sqlite3.connect(owner.path)) as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
        db.commit()
    return resources_module.LocalResources.reopen(definition), raw


def handle(directory, name, definition):
    path = directory / (name + '.json')
    body = {'version': native.VERSION, 'unit': name, 'stage': 'prepared', 'paths': {},
        'metadata': {'local_resources': definition}}
    path.write_text(json.dumps(body, sort_keys=True))
    return native.NativeJobHandle(path), path.read_bytes()


@pytest.mark.parametrize('historical', [False, True])
def test_capacity_quantities_admit_multiple_rows_without_count_gate(capacity, historical):
    owner = legacy(capacity)[0] if historical else capacity
    definition = owner.as_record()
    before = raw_state(owner.path)
    reservations = []
    for name in ('controlled-a', 'controlled-b', 'controlled-c'):
        selected, raw = handle(owner.directory, name, definition)
        reservations.append(owner.reserve(selected, cpu_threads=4, policy=jobs.LocalJobPolicy(10, 10)))
        assert selected.path.read_bytes() == raw
    assert len(raw_state(owner.path)['reservations']) == 3
    view = owner.snapshot()
    assert view['version'] == 'shared_local_resources_v3'
    assert set(view['limits']) == set(view['reserved']) == set(view['available']) == {
        'memory_bytes', 'scratch_bytes'}
    assert view['reserved'] == {'memory_bytes': 30, 'scratch_bytes': 30}
    assert view['available'] == {'memory_bytes': 0, 'scratch_bytes': 0}
    assert [row['allocation']['cpu_threads'] for row in view['jobs']] == [4, 4, 4]
    assert all(row['allocation']['cpu_threads'] == 4 for row in reservations)
    assert owner.as_record() == definition
    after = raw_state(owner.path)
    assert before['configuration'] == after['configuration'] and before['schema'] == after['schema']
    selected, raw = handle(owner.directory, 'controlled-overflow', definition)
    with pytest.raises(resources_module.AcquisitionError):
        owner.reserve(selected, cpu_threads=1, policy=jobs.LocalJobPolicy(1, 1))
    assert raw_state(owner.path) == after and selected.path.read_bytes() == raw
    owner.release_reservation(reservations[0])
    remaining = raw_state(owner.path)
    assert remaining['reservations'] == [row for row in after['reservations'] if row[1] != reservations[0]['reservation_ref']]
    assert remaining['configuration'] == before['configuration']


def test_legacy_validate_and_lifecycle_cleanup_preserve_original_configuration(capacity):
    owner, raw = legacy(capacity)
    selected, _ = handle(owner.directory, 'controlled-cleanup', owner.as_record())
    reservation = owner.reserve(selected, cpu_threads=1, policy=jobs.LocalJobPolicy(1, 1))
    before = raw_state(owner.path)
    reopened = resources_module.LocalResources.reopen(reservation['resource'])
    reopened.validate_reservation(reservation)
    assert raw_state(owner.path) == before
    native._release_capacity({'capacity_reservation': reservation})
    native._release_capacity({'capacity_reservation': reservation})
    after = raw_state(owner.path)
    assert after['reservations'] == []
    assert after['configuration'] == [(1, raw)] and after['schema'] == before['schema']
    assert reopened.as_record() == reservation['resource']


def test_legacy_original_settings_reconstruct_without_rewriting_saved_count(capacity):
    owner, raw = legacy(capacity)
    before = raw_state(owner.path)
    same = resources_module.LocalResources(owner.directory, owner.as_record()['limits'])
    assert same.as_record() == owner.as_record() and raw_state(owner.path) == before
    with pytest.raises(ValueError, match='local_resource_limits_conflict'):
        resources_module.LocalResources(owner.directory, {'max_running_jobs': 2})
    assert raw_state(owner.path) == before


@pytest.mark.parametrize('count', [1, 0, None])
def test_new_count_setting_is_not_a_current_policy(tmp_path, count):
    with pytest.raises(ValueError, match='invalid_local_resource_settings'):
        resources_module.LocalResources(tmp_path / 'new', {'max_running_jobs': count})


def test_nondefault_missing_descriptor_does_not_adopt_supplied_limits(capacity, tmp_path):
    owner, _ = legacy(capacity)
    before = raw_state(owner.path)
    missing = owner.as_record()
    missing['directory'] = str(tmp_path / 'original-default-on-failure')
    with pytest.raises(ValueError, match='local_resource_binding_conflict'):
        resources_module.LocalResources.reopen(missing)
    initialized = raw_state(Path(missing['directory']) / 'capacity.sqlite3')
    assert json.loads(initialized['configuration'][0][1]) == {
        **missing, 'limits': ORIGINAL_V1_LIMITS}
    assert initialized['reservations'] == []
    changed = owner.as_record()
    changed['limits']['memory_bytes'] += 1
    with pytest.raises(ValueError, match='local_resource_binding_conflict'):
        resources_module.LocalResources.reopen(changed)
    assert raw_state(owner.path) == before


@pytest.mark.parametrize('empty_database', [False, True])
@pytest.mark.parametrize('version', ['shared_local_resources_v1', 'shared_local_resources_v2'])
def test_original_default_descriptor_reconstructs_exact_original_definition(capacity, tmp_path, empty_database, version):
    directory = tmp_path / 'original-default-reopen'
    if empty_database:
        directory.mkdir()
        with closing(sqlite3.connect(directory / 'capacity.sqlite3')):
            pass
    definition = {'version': version, 'resource_id': resources_module._resource_id(),
        'directory': str(directory), 'limits': dict(ORIGINAL_V1_LIMITS)}
    if version == 'shared_local_resources_v2':
        del definition['limits']['max_running_jobs']
    owner = resources_module.LocalResources.reopen(definition)
    assert owner.as_record() == definition
    before = raw_state(owner.path)
    assert json.loads(before['configuration'][0][1]) == definition
    assert before['reservations'] == []
    assert set(owner.snapshot()['limits']) == {'memory_bytes', 'scratch_bytes'}
    assert raw_state(owner.path) == before


def test_original_refresh_cleanup_remains_distinct_from_validation(capacity):
    owner, _ = legacy(capacity)
    selected, _ = handle(owner.directory, 'controlled-terminal', owner.as_record())
    owner.reserve(selected, cpu_threads=1, policy=jobs.LocalJobPolicy(1, 1))
    body = selected.read()
    status = owner.directory / 'terminal-status'
    status.write_text('controlled terminal marker')
    body['paths']['status'] = str(status)
    selected.path.write_text(json.dumps(body))
    before = raw_state(owner.path)
    owner.snapshot()
    after = raw_state(owner.path)
    assert after['reservations'] == []
    assert after['schema'] == before['schema'] and after['configuration'] == before['configuration']


def test_added_index_does_not_become_an_admission_gate(capacity):
    owner, _ = legacy(capacity)
    with closing(sqlite3.connect(owner.path)) as db:
        db.execute('CREATE INDEX retained_created_at ON reservations(created_at)')
        db.commit()
    before = raw_state(owner.path)
    reopened = resources_module.LocalResources.reopen(owner.as_record())
    selected, _ = handle(owner.directory, 'controlled-extra-index', owner.as_record())
    reservation = reopened.reserve(selected, cpu_threads=1, policy=jobs.LocalJobPolicy(1, 1))
    reopened.validate_reservation(reservation)
    reopened.release_reservation(reservation)
    assert raw_state(owner.path) == before


def test_ordinary_constructor_retains_empty_database_initialization(tmp_path):
    directory = tmp_path / 'empty-database'
    directory.mkdir()
    with closing(sqlite3.connect(directory / 'capacity.sqlite3')):
        pass
    owner = resources_module.LocalResources(directory)
    assert owner.as_record()['version'] == 'shared_local_resources_v3'
    assert set(owner.as_record()['limits']) == {'memory_bytes', 'scratch_bytes'}


def test_route_recommendation_uses_dimensions_not_historical_count():
    route = {'binding_available': True, 'capacity_state': 'fresh',
        'available': {'job_slots': 0, 'cpu_threads': 1, 'memory_bytes': 10, 'scratch_bytes': 10}}
    view = guidance.compare_routes(route, None,
        requirements={'cpu_threads': 64, 'memory_bytes': 10, 'scratch_bytes': 10})
    assert view['preferred'] == 'local' and view['routes']['local']['eligible'] is True


def test_already_released_handle_keeps_original_resume_event_path(capacity, monkeypatch):
    owner, _ = legacy(capacity)
    selected, _ = handle(owner.directory, 'controlled-released', owner.as_record())
    body = selected.read()
    release = owner.directory / 'release'
    release.touch()
    body.update(stage='released', paths={'release': str(release)})
    from gene_annotation_episode.workflow_budget import active_budget
    body['cwd'] = str(owner.directory)
    body['metadata'].update(policy=jobs.LocalJobPolicy(1, 1).to_dict(), cpu_threads=1,
        whole_workflow_budget=active_budget())
    selected.path.write_text(json.dumps(body))
    before = selected.path.read_bytes()
    events = []
    monkeypatch.setattr(native, '_ensure_event_registration', lambda h, b: events.append(h.path))
    assert native.resume_start(selected) is selected
    assert events == [selected.path] and selected.path.read_bytes() == before


def test_legacy_prepared_resume_reserves_before_controlled_dispatch(capacity, monkeypatch):
    """Actual resume/start/reserve; workflow observation and dispatch are ports."""
    owner, _ = legacy(capacity)
    selected, _ = handle(owner.directory, 'controlled-prepared-resume', owner.as_record())
    request = owner.directory / 'request.json'
    request.write_bytes(b'{"controlled_request":true}\n')
    workflow = {'controlled_workflow_observation': True}
    body = selected.read()
    body.update(cwd=str(owner.directory), paths={'request': str(request)},
        request_sha256=hashlib.sha256(request.read_bytes()).hexdigest())
    body['metadata'].update(policy=jobs.LocalJobPolicy(10, 10).to_dict(),
        cpu_threads=1, whole_workflow_budget=workflow)
    selected.path.write_text(json.dumps(body, sort_keys=True))
    before = selected.path.read_bytes()
    state = raw_state(owner.path)
    budget = importlib.import_module('gene_annotation_episode.workflow_budget')
    monkeypatch.setattr(budget, 'native_budget', lambda policy, cpu, cwd: workflow)
    reached = []
    sentinel = object()
    def dispatch(h, actual, *, cancel_event=None):
        reservation = actual['capacity_reservation']
        assert reservation['resource'] == owner.as_record()
        resources_module.LocalResources.reopen(reservation['resource']).validate_reservation(reservation)
        reached.append(reservation)
        return sentinel
    monkeypatch.setattr(native, '_dispatch_prepared', dispatch)
    assert native.resume_start(selected) is sentinel
    assert len(reached) == 1 and selected.path.read_bytes() == before
    after = raw_state(owner.path)
    assert len(after['reservations']) == 1
    assert after['configuration'] == state['configuration'] and after['schema'] == state['schema']
    native._release_capacity({'capacity_reservation': reached[0]})
    assert raw_state(owner.path) == state


@pytest.mark.parametrize('valid_reservation', [True, False])
def test_legacy_submitting_resume_authenticates_before_readiness_observation(capacity, monkeypatch, valid_reservation):
    """Actual reservation validation; stop at the controlled service observer."""
    owner, _ = legacy(capacity)
    selected, _ = handle(owner.directory, 'controlled-submitting-resume', owner.as_record())
    reservation = owner.reserve(selected, cpu_threads=1, policy=jobs.LocalJobPolicy(1, 1))
    body = selected.read()
    body.update(stage='submitting', capacity_reservation=reservation,
        paths={'release': str(owner.directory / 'unreleased'), 'ready': str(owner.directory / 'not-ready')})
    body['metadata']['policy'] = jobs.LocalJobPolicy(1, 1).to_dict()
    from gene_annotation_episode.workflow_budget import active_budget
    body['cwd'] = str(owner.directory)
    body['metadata'].update(cpu_threads=1, whole_workflow_budget=active_budget())
    if not valid_reservation:
        body['capacity_reservation']['reservation_ref'] = 'controlled-wrong-token'
    selected.path.write_text(json.dumps(body, sort_keys=True))
    before = selected.path.read_bytes()
    state = raw_state(owner.path)
    observed = []
    class ReachedServiceObserver(Exception):
        pass
    def observe(unit):
        observed.append(unit)
        raise ReachedServiceObserver()
    monkeypatch.setattr(native, '_properties', observe)
    if valid_reservation:
        with pytest.raises(ReachedServiceObserver):
            native.resume_start(selected)
        assert observed == [body['unit']]
    else:
        with pytest.raises(ValueError, match='local_resource_reservation_unavailable'):
            native.resume_start(selected)
        assert observed == []
    assert raw_state(owner.path) == state and selected.path.read_bytes() == before
    assert not Path(body['paths']['release']).exists()
