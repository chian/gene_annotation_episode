"""Real reservation SQLite; controlled service observations; no job dispatch.

The tiny capacities below are arithmetic fixtures, not requested cgroup bounds.
NativeJobHandle inputs are explicitly prepared-record fixtures. No completed
execution, scientific result, process, or service is manufactured.
"""
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode import local_resources, native_lifecycle
from gene_annotation_episode.local_jobs import LocalJobPolicy


FIELDS = {'memory_bytes', 'scratch_bytes'}
POLICY = LocalJobPolicy(memory_bytes=1, scratch_bytes=1)


@pytest.fixture
def observed_empty_host(monkeypatch):
    calls = []
    def inventory(argv):
        calls.append(argv)
        assert argv[:3] == ['systemctl', '--user', 'list-units']
        return SimpleNamespace(returncode=0, stdout='')
    monkeypatch.setattr(native_lifecycle, '_control', inventory)
    monkeypatch.setattr(native_lifecycle, '_properties', lambda unit: {'LoadState': 'not-found'})
    return calls


def prepared_handle(directory, name):
    path = directory / (name + '.json')
    path.write_text(json.dumps({'version': native_lifecycle.VERSION,
        'unit': 'gene-local-job-fixture-' + name + '.service', 'stage': 'prepared',
        'paths': {}}))
    return native_lifecycle.NativeJobHandle(path)


def reservations(resource):
    with sqlite3.connect(resource.path) as db:
        return db.execute('SELECT unit,token,cpu_threads,memory_bytes,scratch_bytes '
                          'FROM reservations ORDER BY unit').fetchall()


@pytest.mark.parametrize('count', [None, 0, 1, 2], ids=['none', 'zero', 'one', 'two'])
def test_process_count_settings_are_rejected(tmp_path, count):
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(tmp_path / 'capacity', {'max_running_jobs': count})


def test_defaults_and_exact_reopening_have_only_resource_dimensions(tmp_path):
    resource = local_resources.LocalResources(tmp_path / 'capacity')
    definition = resource.as_record()
    assert set(definition['limits']) == FIELDS
    assert definition['version'] == 'shared_local_resources_v1'
    assert local_resources.LocalResources.reopen(definition).as_record() == definition
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(resource.directory, {'max_running_jobs': 1})
    changed = deepcopy(definition)
    changed['limits']['scratch_bytes'] += 1
    with pytest.raises(ValueError, match='^local_resource_binding_conflict$'):
        local_resources.LocalResources.reopen(changed)
    assert local_resources.LocalResources.reopen(definition).as_record() == definition


def test_multiple_reservations_are_limited_only_by_actual_resource_arithmetic(tmp_path, observed_empty_host):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 3))
    handles = [prepared_handle(tmp_path, name) for name in ('one', 'two', 'three', 'four')]
    admitted = [resource.reserve(handle, cpu_threads=1, policy=POLICY) for handle in handles[:3]]
    assert len(reservations(resource)) == 3
    for row in admitted:
        resource.validate_reservation(row)
    view = resource.snapshot()
    assert view['reserved'] == dict.fromkeys(FIELDS, 3)
    assert view['available'] == dict.fromkeys(FIELDS, 0)
    assert len(view['jobs']) == 3 and {job['state'] for job in view['jobs']} == {'reserved'}
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(handles[3], cpu_threads=1, policy=POLICY)
    assert caught.value.code == 'local_resource_busy'
    assert caught.value.operational['retry_same_prepared_job'] is True
    assert len(reservations(resource)) == 3
    resource.release_reservation(admitted[1])
    resource.reserve(handles[3], cpu_threads=1, policy=POLICY)
    assert len(reservations(resource)) == 3
    assert observed_empty_host


@pytest.mark.parametrize('field', sorted(FIELDS))
def test_over_capacity_request_remains_rejected_before_insert(tmp_path, observed_empty_host, field):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 1))
    request = {'cpu_threads': 1, **dict.fromkeys(FIELDS, 1)}
    request[field] = 2
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(prepared_handle(tmp_path, 'oversize'), cpu_threads=request['cpu_threads'],
                         policy=LocalJobPolicy(request['memory_bytes'], request['scratch_bytes']))
    assert caught.value.code == 'local_job_resource_limit'
    assert caught.value.operational['resource'] == field
    assert caught.value.operational['retryable'] is False
    assert reservations(resource) == []


def configuration_text(resource):
    with sqlite3.connect(resource.path) as db:
        return db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]


def test_unknown_dispatch_retains_original_reservation_and_resources(tmp_path, observed_empty_host):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 1))
    handle = prepared_handle(tmp_path, 'unknown')
    reservation = resource.reserve(handle, cpu_threads=1, policy=POLICY)
    body = handle.read()
    body['stage'] = 'submitting'
    handle.path.write_text(json.dumps(body))
    original = reservations(resource)
    view = resource.snapshot()
    assert view['jobs'][0]['state'] == 'execution_unknown'
    assert view['available'] == dict.fromkeys(FIELDS, 0)
    assert reservations(resource) == original
    resource.validate_reservation(reservation)
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(prepared_handle(tmp_path, 'next'), cpu_threads=1, policy=POLICY)
    assert caught.value.code == 'local_resource_busy'
    assert reservations(resource) == original


@pytest.mark.parametrize('unavailable', [False, True], ids=['untracked', 'unavailable'])
def test_untracked_or_unavailable_observer_does_not_advertise_free_capacity(tmp_path, monkeypatch, unavailable):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 1))
    monkeypatch.setattr(native_lifecycle, '_control', lambda argv: SimpleNamespace(
        returncode=1 if unavailable else 0,
        stdout='' if unavailable else 'gene-local-job-observed.service loaded active running Observed\n'))
    view = resource.snapshot()
    assert view['state'] == ('unknown' if unavailable else 'busy')
    assert view['available'] == dict.fromkeys(FIELDS, 0)
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(prepared_handle(tmp_path, 'next'), cpu_threads=1, policy=POLICY)
    assert caught.value.code == ('local_job_boundary_unavailable' if unavailable else 'local_resource_busy')
    assert reservations(resource) == []


# Explicit new controls for the byte-only successor and original initialization fix.
@pytest.mark.parametrize('cpu_threads', [2, 64], ids=['two', 'sixty-four'])
def test_requested_threads_are_positive_metadata_not_capacity(tmp_path, observed_empty_host, cpu_threads):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 2))
    first = resource.reserve(prepared_handle(tmp_path, 'first'), cpu_threads=cpu_threads, policy=POLICY)
    second = resource.reserve(prepared_handle(tmp_path, 'second'), cpu_threads=cpu_threads, policy=POLICY)
    assert first['allocation']['cpu_threads'] == second['allocation']['cpu_threads'] == cpu_threads
    resource.validate_reservation(first)
    resource.validate_reservation(second)
    assert [row[2] for row in reservations(resource)] == [cpu_threads, cpu_threads]
    assert resource.snapshot()['reserved'] == dict.fromkeys(FIELDS, 2)
    assert resource.snapshot()['available'] == dict.fromkeys(FIELDS, 0)
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(prepared_handle(tmp_path, 'third'), cpu_threads=cpu_threads, policy=POLICY)
    assert caught.value.code == 'local_resource_busy'


@pytest.mark.parametrize('value', [None, 0, 1, True], ids=['none', 'zero', 'one', 'bool'])
def test_new_or_byte_only_existing_configuration_rejects_thread_count_settings(tmp_path, value):
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(tmp_path / 'new', {'cpu_threads': value})
    resource = local_resources.LocalResources(tmp_path / 'existing')
    raw = configuration_text(resource)
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(resource.directory, {'cpu_threads': value})
    assert configuration_text(resource) == raw


