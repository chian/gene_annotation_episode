"""Real reservation SQLite; controlled service observations; no job dispatch.

The tiny capacities below are arithmetic fixtures, not requested cgroup bounds.
NativeJobHandle inputs are explicitly prepared-record fixtures. No completed
execution, scientific result, process, or service is manufactured.
"""
from copy import deepcopy
import json
from pathlib import Path
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


def test_original_default_descriptor_can_reopen_absent_database_without_normalization(tmp_path):
    resource = local_resources.LocalResources(tmp_path / 'original')
    descriptor = resource.as_record()
    descriptor['directory'] = str(tmp_path / 'restored')
    descriptor['limits'].update(max_running_jobs=1, cpu_threads=1)
    retained = deepcopy(descriptor)
    reopened = local_resources.LocalResources.reopen(descriptor)
    assert reopened.as_record() == descriptor
    assert descriptor == retained
    with sqlite3.connect(reopened.path) as db:
        assert json.loads(db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]) == retained


def test_legacy_saved_configuration_and_resource_settings_reopen_without_rewriting(tmp_path, observed_empty_host, monkeypatch):
    resource = local_resources.LocalResources(tmp_path / 'capacity')
    historical = resource.as_record()
    historical['limits'].update(max_running_jobs=1, cpu_threads=1)
    # Explicit historical configuration fixture in the actual owner table.
    raw = json.dumps(historical, indent=2)
    with sqlite3.connect(resource.path) as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
    reopened = local_resources.LocalResources(resource.directory)
    assert reopened.as_record() == historical
    assert local_resources.LocalResources(resource.directory, {'cpu_threads': 1}).as_record() == historical
    assert local_resources.LocalResources(resource.directory, historical['limits']).as_record() == historical
    monkeypatch.setenv(local_resources.DIRECTORY_ENV, str(resource.directory))
    assert local_resources.LocalResources.configured(historical['limits']).as_record() == historical
    with pytest.raises(ValueError, match='^local_resource_limits_conflict$'):
        local_resources.LocalResources.configured({**historical['limits'], 'max_running_jobs': 2})
    with pytest.raises(ValueError, match='^invalid_local_resource_limits$'):
        local_resources.LocalResources.configured({**historical['limits'], 'max_running_jobs': True})
    assert set(reopened.snapshot()['limits']) == FIELDS
    with sqlite3.connect(resource.path) as db:
        assert db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0] == raw
        assert db.execute('SELECT count(*) FROM reservations').fetchone()[0] == 0


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


def retained_count_definition(resource, count):
    """Explicit historical configuration fixture, preserved byte-for-byte."""
    definition = resource.as_record()
    definition['limits'].update(max_running_jobs=count, cpu_threads=1)
    raw = json.dumps(definition, indent=2)
    with sqlite3.connect(resource.path) as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
    return local_resources.LocalResources.reopen(definition), raw


def configuration_text(resource):
    with sqlite3.connect(resource.path) as db:
        return db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0]


@pytest.mark.parametrize('historical_count', [1, 7], ids=['old-one', 'old-seven'])
def test_historical_count_metadata_never_changes_resource_admission(tmp_path, observed_empty_host, historical_count):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 3))
    resource, raw = retained_count_definition(resource, historical_count)
    rows = [resource.reserve(prepared_handle(tmp_path, name), cpu_threads=1, policy=POLICY)
            for name in ('first', 'second', 'third')]
    assert len(reservations(resource)) == 3
    assert resource.snapshot()['reserved'] == dict.fromkeys(FIELDS, 3)
    assert resource.snapshot()['available'] == dict.fromkeys(FIELDS, 0)
    assert resource.snapshot()['limits'] == dict.fromkeys(FIELDS, 3)
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(prepared_handle(tmp_path, 'fourth'), cpu_threads=1, policy=POLICY)
    assert caught.value.code == 'local_resource_busy'
    for reservation in rows:
        resource.validate_reservation(reservation)
        assert reservation['resource'] == resource.as_record()
        resource.release_reservation(reservation)
        resource.release_reservation(reservation)
    assert reservations(resource) == []
    assert resource.as_record()['limits']['max_running_jobs'] == historical_count
    assert configuration_text(resource) == raw


@pytest.mark.parametrize('defect', ['token', 'unit', 'allocation'])
def test_original_reservation_validation_rejects_actual_row_mismatches(tmp_path, observed_empty_host, defect):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 1))
    resource, raw = retained_count_definition(resource, 1)
    actual = resource.reserve(prepared_handle(tmp_path, 'original'), cpu_threads=1, policy=POLICY)
    offered = deepcopy(actual)
    if defect == 'allocation':
        offered['allocation']['memory_bytes'] += 1
    else:
        offered['reservation_ref' if defect == 'token' else 'execution_handle'] += '-wrong'
    before = reservations(resource)
    with pytest.raises(ValueError, match='^local_resource_reservation_unavailable$'):
        resource.validate_reservation(offered)
    if defect != 'allocation':
        # Original idempotent cleanup matches token AND unit; it does not use
        # an invented stronger allocation/handle authentication interface.
        resource.release_reservation(offered)
    assert reservations(resource) == before
    assert configuration_text(resource) == raw
    resource.validate_reservation(actual)


def test_original_observer_rejects_saved_handle_unit_mismatch(tmp_path, observed_empty_host):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 1))
    resource, raw = retained_count_definition(resource, 1)
    handle = prepared_handle(tmp_path, 'original')
    resource.reserve(handle, cpu_threads=1, policy=POLICY)
    body = handle.read()
    body['unit'] += '-different'
    handle.path.write_text(json.dumps(body))
    before = reservations(resource)
    with pytest.raises(ValueError, match='^local_resource_reservation_identity_conflict$'):
        resource.snapshot()
    assert reservations(resource) == before and configuration_text(resource) == raw


@pytest.mark.parametrize('operation', ['status', 'collect', 'cancel', 'release'])
def test_original_native_cleanup_apis_preserve_historical_resource_owner(
        tmp_path, observed_empty_host, monkeypatch, operation):
    resource = local_resources.LocalResources(tmp_path / 'capacity', dict.fromkeys(FIELDS, 1))
    resource, raw = retained_count_definition(resource, 1)
    handle = prepared_handle(tmp_path, 'historical')
    reservation = resource.reserve(handle, cpu_threads=1, policy=POLICY)
    body = handle.read()
    body.update(metadata={'policy': POLICY.to_dict(), 'cpu_threads': 1,
                          'local_resources': resource.as_record()},
                started_monotonic_ns=None, boot_id=None,
                stdout=str(tmp_path / 'stdout'), stderr=str(tmp_path / 'stderr'),
                paths={name: str(tmp_path / name) for name in ('ready', 'release', 'status', 'result')},
                capacity_reservation=reservation)
    handle.path.write_text(json.dumps(body))
    calls = []
    monkeypatch.setattr(native_lifecycle, '_control', lambda argv:
        calls.append(argv) or SimpleNamespace(returncode=0, stdout=''))
    if operation == 'status':
        assert native_lifecycle.status(handle)['state'] == 'prepared'
        assert len(reservations(resource)) == 1
    elif operation == 'collect':
        with pytest.raises(AcquisitionError) as caught:
            native_lifecycle.collect(handle)
        assert caught.value.code == 'local_job_not_collectable'
        assert len(reservations(resource)) == 1
    else:
        getattr(native_lifecycle, operation)(handle)
        assert reservations(resource) == []
        assert calls and handle.path.exists() is (operation != 'release')
    assert configuration_text(resource) == raw


def genuine_prepared_handle(tmp_path, monkeypatch):
    """Original preparation and actual owning-workflow CPU/RAM authentication."""
    policy = LocalJobPolicy(64 * 1024**2, 4 * 1024**2)
    resource = local_resources.LocalResources(tmp_path / 'capacity', policy.to_dict())
    resource, raw = retained_count_definition(resource, 1)
    monkeypatch.setenv(local_resources.DIRECTORY_ENV, str(resource.directory))
    job = tmp_path / 'prepared'
    job.mkdir()
    handle = native_lifecycle.prepare_job(['/bin/true'], cwd=job, policy=policy,
        handle_path=job / 'native.handle.json')
    assert handle.read()['stage'] == 'prepared'
    return resource, handle, policy, raw


@pytest.mark.parametrize('descriptorless', [False, True], ids=['saved-v1-descriptor', 'original-fallback'])
def test_original_prepared_admission_and_descriptorless_fallback_reach_dispatch_boundary(
        tmp_path, observed_empty_host, monkeypatch, descriptorless):
    resource, handle, _, raw = genuine_prepared_handle(tmp_path, monkeypatch)
    body = handle.read()
    if descriptorless:
        del body['metadata']['local_resources']
        handle.path.write_text(json.dumps(body))
    before = handle.path.read_bytes()
    offered = []
    class DispatchBoundary(Exception):
        pass
    def at_dispatch(actual_handle, actual_body, *, cancel_event=None):
        offered.append(deepcopy(actual_body))
        resource.validate_reservation(actual_body['capacity_reservation'])
        assert actual_body['metadata']['local_resources'] == resource.as_record()
        raise DispatchBoundary
    monkeypatch.setattr(native_lifecycle, '_dispatch_prepared', at_dispatch)
    with pytest.raises(DispatchBoundary):
        native_lifecycle.start_prepared(handle)
    assert len(offered) == 1
    # Original failure-before-publication cleanup releases the in-memory token,
    # even though no capacity_reservation was ever written to the handle.
    assert reservations(resource) == [] and handle.path.read_bytes() == before
    assert configuration_text(resource) == raw


@pytest.mark.parametrize('descriptorless', [False, True], ids=['authenticated-v1-reservation', 'original-descriptorless-resume'])
def test_original_unreleased_resume_keeps_valid_saved_and_legacy_routes(
        tmp_path, observed_empty_host, monkeypatch, descriptorless):
    resource, handle, policy, raw = genuine_prepared_handle(tmp_path, monkeypatch)
    body = handle.read()
    body['stage'] = 'submitting'
    if descriptorless:
        del body['metadata']['local_resources']
    else:
        body['capacity_reservation'] = resource.reserve(handle, cpu_threads=1, policy=policy)
    handle.path.write_text(json.dumps(body))
    before = handle.path.read_bytes(), reservations(resource)
    with pytest.raises(AcquisitionError) as caught:
        native_lifecycle.resume_start(handle)
    assert caught.value.code == 'local_job_boundary_unavailable'
    assert caught.value.operational['reason'] == 'service_did_not_initialize'
    assert (handle.path.read_bytes(), reservations(resource)) == before
    assert not Path(body['paths']['release']).exists()
    assert configuration_text(resource) == raw


def test_original_released_handle_read_does_not_repeat_admission(tmp_path, observed_empty_host, monkeypatch):
    resource, handle, _, raw = genuine_prepared_handle(tmp_path, monkeypatch)
    body = handle.read()
    # Explicit release-marker state fixture; no process or completed result.
    body['stage'] = 'released'
    handle.path.write_text(json.dumps(body))
    Path(body['paths']['release']).touch()
    before = handle.path.read_bytes()
    assert native_lifecycle.resume_start(handle) is handle
    assert handle.path.read_bytes() == before and reservations(resource) == []
    assert configuration_text(resource) == raw


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


def expected_default_descriptor(directory, format_name):
    # Exact source values retained from the original and actually installed defaults.
    limits = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    if format_name in ('current-three', 'original-four'):
        limits['cpu_threads'] = 1
    if format_name == 'original-four':
        limits['max_running_jobs'] = 1
    return {'version': 'shared_local_resources_v1', 'resource_id': local_resources._resource_id(),
            'directory': str(directory.resolve()), 'limits': limits}


def exact_configuration_and_rows(directory):
    with sqlite3.connect(directory / 'capacity.sqlite3') as db:
        return db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0], db.execute(
            'SELECT * FROM reservations ORDER BY unit').fetchall()


@pytest.mark.parametrize('format_name', ['new-two', 'current-three', 'original-four'])
def test_known_default_formats_reopen_absent_database_without_rewriting(tmp_path, format_name):
    directory = tmp_path / 'restore'
    descriptor = expected_default_descriptor(directory, format_name)
    before = deepcopy(descriptor)
    resource = local_resources.LocalResources.reopen(descriptor)
    assert resource.as_record() == descriptor == before
    assert exact_configuration_and_rows(directory) == (json.dumps(before, sort_keys=True), [])


@pytest.mark.parametrize('defect', ['custom-two', 'custom-three', 'custom-four', 'missing-cpu',
    'missing-limits', 'null-limits', 'list-limits', 'string-limits', 'wrong-version', 'wrong-resource',
    'extra-field', 'extra-limit'])
def test_rejected_missing_database_attempt_restores_original_initialized_four_field_row(tmp_path, defect):
    directory = tmp_path / 'rejected'
    expected = expected_default_descriptor(directory, 'original-four')
    requested = deepcopy(expected)
    if defect.startswith('custom-'):
        requested = expected_default_descriptor(directory, {
            'custom-two': 'new-two', 'custom-three': 'current-three', 'custom-four': 'original-four'}[defect])
        requested['limits']['scratch_bytes'] += 1
    elif defect == 'missing-cpu':
        del requested['limits']['cpu_threads']
    elif defect == 'missing-limits':
        del requested['limits']
    elif defect == 'null-limits':
        requested['limits'] = None
    elif defect == 'list-limits':
        requested['limits'] = []
    elif defect == 'string-limits':
        requested['limits'] = 'invalid-limit-fixture'
    elif defect == 'wrong-version':
        requested['version'] = 'invalid-version-fixture'
    elif defect == 'wrong-resource':
        requested['resource_id'] = 'invalid-resource-fixture'
    elif defect == 'extra-field':
        requested['unknown_fixture'] = True
    else:
        requested['limits']['unknown_fixture'] = 1
    before = deepcopy(requested)
    with pytest.raises(ValueError, match='^local_resource_binding_conflict$'):
        local_resources.LocalResources.reopen(requested)
    assert requested == before
    assert exact_configuration_and_rows(directory) == (json.dumps(expected, sort_keys=True), [])


@pytest.mark.parametrize('format_name', ['current-three', 'original-four'])
def test_saved_formats_full_settings_and_rows_remain_exact_with_thread_metadata(
        tmp_path, observed_empty_host, monkeypatch, format_name):
    directory = tmp_path / 'saved'
    resource = local_resources.LocalResources(directory)
    descriptor = expected_default_descriptor(directory, format_name)
    descriptor['limits'].update(memory_bytes=3, scratch_bytes=3)
    if format_name == 'original-four':
        descriptor['limits']['max_running_jobs'] = 7
    raw = json.dumps(descriptor, indent=2)
    with sqlite3.connect(resource.path) as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
    supplied = deepcopy(descriptor['limits'])
    direct = local_resources.LocalResources(directory, supplied)
    monkeypatch.setenv(local_resources.DIRECTORY_ENV, str(directory))
    configured = local_resources.LocalResources.configured(supplied)
    reopened = local_resources.LocalResources.reopen(descriptor)
    assert direct.as_record() == configured.as_record() == reopened.as_record() == descriptor
    assert supplied == descriptor['limits']
    first = direct.reserve(prepared_handle(tmp_path, 'first'), cpu_threads=64, policy=POLICY)
    second = configured.reserve(prepared_handle(tmp_path, 'second'), cpu_threads=2, policy=POLICY)
    before = exact_configuration_and_rows(directory)
    for owner in (direct, configured, reopened):
        owner.validate_reservation(first)
        owner.validate_reservation(second)
        assert owner.snapshot()['limits'] == dict.fromkeys(FIELDS, 3)
    assert exact_configuration_and_rows(directory) == before and before[0] == raw
    reopened.release_reservation(first)
    reopened.release_reservation(first)
    reopened.validate_reservation(second)
    assert configuration_text(reopened) == raw


@pytest.mark.parametrize('field,value,error', [
    ('cpu_threads', True, 'invalid_local_resource_limits'),
    ('cpu_threads', 2, 'local_resource_limits_conflict'),
    ('max_running_jobs', True, 'invalid_local_resource_limits'),
    ('max_running_jobs', 2, 'local_resource_limits_conflict')],
    ids=['cpu-bool', 'cpu-changed', 'jobs-bool', 'jobs-changed'])
def test_saved_inert_count_settings_cannot_change_type_or_value(tmp_path, field, value, error):
    resource = local_resources.LocalResources(tmp_path / 'saved', dict.fromkeys(FIELDS, 3))
    resource, raw = retained_count_definition(resource, 1)
    before = reservations(resource)
    with pytest.raises(ValueError, match='^' + error + '$'):
        local_resources.LocalResources(resource.directory, {**resource.as_record()['limits'], field: value})
    assert configuration_text(resource) == raw and reservations(resource) == before


@pytest.mark.parametrize('value', [None, 0, 1, True], ids=['none', 'zero', 'one', 'bool'])
def test_new_or_byte_only_existing_configuration_rejects_thread_count_settings(tmp_path, value):
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(tmp_path / 'new', {'cpu_threads': value})
    resource = local_resources.LocalResources(tmp_path / 'existing')
    raw = configuration_text(resource)
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(resource.directory, {'cpu_threads': value})
    assert configuration_text(resource) == raw


def test_saved_large_memory_is_preserved_but_effective_view_uses_real_owner(tmp_path, observed_empty_host):
    from gene_annotation_episode.workflow_budget import active_budget
    resource = local_resources.LocalResources(tmp_path / 'saved')
    resource, raw = retained_count_definition(resource, 1)
    descriptor = resource.as_record()
    actual = active_budget()
    assert descriptor['limits']['memory_bytes'] == 21474836480
    view = resource.snapshot()
    assert view['limits']['memory_bytes'] == actual['environment_bounds']['memory_bytes'] == 5 * 1024**3
    assert view['available']['memory_bytes'] == view['limits']['memory_bytes']
    assert resource.as_record() == descriptor and configuration_text(resource) == raw
