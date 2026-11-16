"""Controlled capacity-row contracts; no worker, process or native dispatch.

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

AXIS = 'a107'
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


def handle(directory, name, definition):
    path = directory / (name + '.json')
    body = {'version': native.VERSION, 'unit': name, 'stage': 'prepared', 'paths': {},
        'metadata': {'local_resources': definition}}
    path.write_text(json.dumps(body, sort_keys=True))
    return native.NativeJobHandle(path), path.read_bytes()


def test_capacity_quantities_admit_multiple_rows_without_count_gate(capacity):
    owner = capacity
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


@pytest.mark.parametrize('count', [1, 0, None])
def test_new_count_setting_is_not_a_current_policy(tmp_path, count):
    with pytest.raises(ValueError, match='invalid_local_resource_settings'):
        resources_module.LocalResources(tmp_path / 'new', {'max_running_jobs': count})


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


