"""Original saved-capacity identity and initialization, with real own SQLite.

Service inventory is a controlled observation seam; no service or completed
execution is created. CPU requests are retained metadata, not allocated threads.
"""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import tomllib

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a105 import local_resources, native_lifecycle


def byte_defaults():
    settings = tomllib.loads(Path(local_resources.__file__).with_name('defaults.toml').read_text())
    return {key: settings['local_resources'][key] for key in ('memory_bytes', 'scratch_bytes')}


def original_default(directory):
    return {'version': 'shared_local_resources_v1', 'resource_id': local_resources._resource_id(),
        'directory': str(directory.resolve()),
        'limits': {**byte_defaults(), 'max_running_jobs': 1, 'cpu_threads': 1}}


def saved_rows(directory):
    with sqlite3.connect(directory / 'capacity.sqlite3') as db:
        return db.execute('SELECT value FROM configuration WHERE id=1').fetchone()[0], db.execute(
            'SELECT unit,token,handle,cpu_threads,memory_bytes,scratch_bytes FROM reservations ORDER BY unit').fetchall()


def seed_original(directory):
    resource = local_resources.LocalResources(directory)
    definition = original_default(directory)
    definition['limits'].update(memory_bytes=512, scratch_bytes=512)
    raw = json.dumps(definition, indent=2)
    with sqlite3.connect(resource.path) as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
    return definition, raw


@pytest.fixture
def observed_empty(monkeypatch):
    monkeypatch.setattr(native_lifecycle, '_control', lambda argv: SimpleNamespace(returncode=0, stdout=''))
    monkeypatch.setattr(native_lifecycle, '_properties', lambda unit: {'LoadState': 'not-found'})


def prepared(directory, name):
    path = directory / (name + '.json')
    path.write_text(json.dumps({'version': native_lifecycle.VERSION,
        'unit': 'gene-local-job-capacity-control-' + name + '.service', 'stage': 'prepared', 'paths': {}}))
    return native_lifecycle.NativeJobHandle(path)


@pytest.mark.parametrize('defect', ['custom-byte', 'missing-count', 'malformed-limits',
    'wrong-version', 'wrong-resource', 'extra-field'])
def test_rejected_missing_database_attempt_keeps_original_initialized_default_row(tmp_path, defect):
    directory = tmp_path / 'rejected'
    original = original_default(directory)
    requested = deepcopy(original)
    if defect == 'custom-byte':
        requested['limits']['scratch_bytes'] += 1
    elif defect == 'missing-count':
        del requested['limits']['max_running_jobs']
    elif defect == 'malformed-limits':
        requested['limits'] = None
    elif defect == 'wrong-version':
        requested['version'] = 'unrecognized-fixture'
    elif defect == 'wrong-resource':
        requested['resource_id'] = 'unrecognized-fixture'
    else:
        requested['unrecognized_fixture_field'] = True
    before = deepcopy(requested)
    with pytest.raises(ValueError, match='^local_resource_binding_conflict$'):
        local_resources.LocalResources.reopen(requested)
    raw, reservations = saved_rows(directory)
    assert raw == json.dumps(original, sort_keys=True)
    assert reservations == [] and requested == before


def test_original_exact_default_missing_database_reopens_without_row_normalization(tmp_path):
    directory = tmp_path / 'historical'
    descriptor = original_default(directory)
    retained = deepcopy(descriptor)
    reopened = local_resources.LocalResources.reopen(descriptor)
    assert reopened.as_record() == descriptor == retained
    assert saved_rows(directory) == (json.dumps(retained, sort_keys=True), [])


def test_new_exact_byte_default_can_reopen_without_becoming_historical(tmp_path):
    fresh = local_resources.LocalResources(tmp_path / 'fresh').as_record()
    assert set(fresh['limits']) == {'memory_bytes', 'scratch_bytes'}
    descriptor = {**fresh, 'directory': str((tmp_path / 'new-format').resolve())}
    reopened = local_resources.LocalResources.reopen(descriptor)
    assert reopened.as_record() == descriptor
    assert saved_rows(reopened.directory) == (json.dumps(descriptor, sort_keys=True), [])


@pytest.mark.parametrize('constructor', ['direct', 'configured'])
def test_original_saved_all_settings_remain_exact_and_inert(tmp_path, monkeypatch, observed_empty, constructor):
    directory = tmp_path / 'saved'
    descriptor, raw = seed_original(directory)
    supplied = deepcopy(descriptor['limits'])
    if constructor == 'direct':
        reopened = local_resources.LocalResources(directory, supplied)
    else:
        monkeypatch.setenv(local_resources.DIRECTORY_ENV, str(directory))
        reopened = local_resources.LocalResources.configured(supplied)
    assert reopened.as_record() == descriptor and supplied == descriptor['limits']
    assert set(reopened.snapshot()['available']) == {'memory_bytes', 'scratch_bytes'}
    assert saved_rows(directory) == (raw, [])


@pytest.mark.parametrize('field,value,error', [
    ('cpu_threads', True, 'invalid_local_resource_limits'),
    ('max_running_jobs', True, 'invalid_local_resource_limits'),
    ('cpu_threads', 2, 'local_resource_limits_conflict'),
    ('max_running_jobs', 2, 'local_resource_limits_conflict')],
    ids=['cpu-bool', 'job-bool', 'cpu-changed', 'job-changed'])
def test_changed_or_malformed_saved_count_metadata_still_rejects_without_rewrite(tmp_path, field, value, error):
    directory = tmp_path / 'saved'
    descriptor, raw = seed_original(directory)
    with pytest.raises(ValueError, match='^' + error + '$'):
        local_resources.LocalResources(directory, {**descriptor['limits'], field: value})
    assert saved_rows(directory) == (raw, [])


def test_two_saved_reservations_keep_positive_cpu_metadata_without_count_admission(tmp_path, observed_empty):
    directory = tmp_path / 'saved'
    descriptor, raw = seed_original(directory)
    resource = local_resources.LocalResources.reopen(descriptor)
    policy = SimpleNamespace(memory_bytes=64, scratch_bytes=64)
    first = resource.reserve(prepared(tmp_path, 'first'), cpu_threads=4, policy=policy)
    second = resource.reserve(prepared(tmp_path, 'second'), cpu_threads=64, policy=policy)
    assert first['allocation']['cpu_threads'] == 4 and second['allocation']['cpu_threads'] == 64
    resource.validate_reservation(first)
    resource.validate_reservation(second)
    view = resource.snapshot()
    assert view['reserved'] == {'memory_bytes': 128, 'scratch_bytes': 128}
    assert view['available'] == {'memory_bytes': 384, 'scratch_bytes': 384}
    assert saved_rows(directory)[0] == raw
    assert len(saved_rows(directory)[1]) == 2
    resource.release_reservation(first)
    resource.release_reservation(first)
    resource.validate_reservation(second)
    with pytest.raises(ValueError, match='^local_resource_binding_conflict$'):
        resource.validate_reservation({**second, 'resource': {**descriptor, 'directory': 'wrong-owner-fixture'}})


def test_unknown_inventory_retains_byte_capacity_and_does_not_create_reservation(tmp_path, monkeypatch):
    directory = tmp_path / 'saved'
    descriptor, raw = seed_original(directory)
    resource = local_resources.LocalResources.reopen(descriptor)
    monkeypatch.setattr(native_lifecycle, '_control', lambda argv: SimpleNamespace(returncode=1, stdout=''))
    with pytest.raises(AcquisitionError) as caught:
        resource.reserve(prepared(tmp_path, 'unknown'), cpu_threads=64,
            policy=SimpleNamespace(memory_bytes=1, scratch_bytes=1))
    assert caught.value.code == 'local_job_boundary_unavailable'
    view = caught.value.operational['local_resources']
    assert view['state'] == 'unknown'
    assert view['available'] == {'memory_bytes': 0, 'scratch_bytes': 0}
    assert saved_rows(directory) == (raw, [])


@pytest.mark.parametrize('settings', [{}, {'memory_bytes': 128, 'scratch_bytes': 256}],
                         ids=['explicit-empty', 'explicit-bytes'])
def test_private_restoration_argument_does_not_override_explicit_settings(tmp_path, settings):
    directory = tmp_path / 'explicit-settings'
    supplied = deepcopy(settings)
    restoration = original_default(directory)
    restoration['limits']['memory_bytes'] += 1
    before = deepcopy(restoration)
    resource = local_resources.LocalResources(directory, settings,
        _restoring_definition=restoration)
    expected = {**original_default(directory), 'limits': {**byte_defaults(), **settings}}
    assert resource.as_record() == expected
    assert saved_rows(directory) == (json.dumps(expected, sort_keys=True), [])
    assert settings == supplied and restoration == before


@pytest.mark.parametrize('field', ['memory_bytes', 'scratch_bytes'])
def test_changed_saved_byte_settings_preserve_exact_original_row(tmp_path, field):
    directory = tmp_path / 'changed-bytes'
    descriptor, raw = seed_original(directory)
    settings = deepcopy(descriptor['limits'])
    settings[field] += 1
    requested = deepcopy(settings)
    with pytest.raises(ValueError, match='^local_resource_limits_conflict$'):
        local_resources.LocalResources(directory, settings)
    assert saved_rows(directory) == (raw, []) and settings == requested


def test_unknown_saved_setting_preserves_exact_original_row(tmp_path):
    directory = tmp_path / 'unknown-setting'
    descriptor, raw = seed_original(directory)
    settings = {**descriptor['limits'], 'unknown_original_setting': 1}
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(directory, settings)
    assert saved_rows(directory) == (raw, [])


@pytest.mark.parametrize('field', ['max_running_jobs', 'cpu_threads', 'job_slots'])
def test_new_custom_count_settings_do_not_initialize_a_configuration(tmp_path, field):
    directory = tmp_path / field
    with pytest.raises(ValueError, match='^invalid_local_resource_settings$'):
        local_resources.LocalResources(directory, {field: 1})
    # Inspect schema/readback without constructing another resource or creating rows.
    with sqlite3.connect(directory / 'capacity.sqlite3') as db:
        if db.execute("SELECT name FROM sqlite_master WHERE name='configuration'").fetchone():
            assert db.execute('SELECT value FROM configuration').fetchall() == []


@pytest.mark.parametrize('defect', ['missing-version', 'missing-limits', 'invalid-count', 'invalid-byte'])
def test_additional_rejected_missing_database_keeps_original_default_side_effect(tmp_path, defect):
    directory = tmp_path / defect
    expected = original_default(directory)
    requested = deepcopy(expected)
    if defect == 'missing-version':
        requested.pop('version')
    elif defect == 'missing-limits':
        requested.pop('limits')
    elif defect == 'invalid-count':
        requested['limits']['max_running_jobs'] = False
    else:
        requested['limits']['scratch_bytes'] = -1
    before = deepcopy(requested)
    with pytest.raises(ValueError, match='^local_resource_binding_conflict$'):
        local_resources.LocalResources.reopen(requested)
    assert saved_rows(directory) == (json.dumps(expected, sort_keys=True), [])
    assert requested == before


def test_saved_full_settings_keep_existing_reservation_rows(tmp_path, observed_empty):
    directory = tmp_path / 'reserved'
    descriptor, raw = seed_original(directory)
    resource = local_resources.LocalResources.reopen(descriptor)
    reservation = resource.reserve(prepared(tmp_path, 'retained'), cpu_threads=1,
        policy=SimpleNamespace(memory_bytes=64, scratch_bytes=64))
    before = saved_rows(directory)
    supplied = deepcopy(descriptor['limits'])
    reopened = local_resources.LocalResources(directory, supplied)
    reopened.validate_reservation(reservation)
    assert reopened.as_record() == descriptor and supplied == descriptor['limits']
    assert saved_rows(directory) == before and before[0] == raw


def test_saved_local_byte_view_and_admission_remain_distinct_from_physical_authority(
        tmp_path, observed_empty):
    from gene_annotation_episode import workflow_budget
    directory = tmp_path / 'saved-large-bytes'
    descriptor, _ = seed_original(directory)
    descriptor['limits']['memory_bytes'] = 20 * 1024**3
    raw = json.dumps(descriptor, indent=2)
    with sqlite3.connect(directory / 'capacity.sqlite3') as db:
        db.execute('UPDATE configuration SET value=? WHERE id=1', (raw,))
    resource = local_resources.LocalResources.reopen(descriptor)
    assert resource.as_record() == descriptor
    assert resource.snapshot()['limits']['memory_bytes'] == 20 * 1024**3
    # This only reserves caller-owned bytes; it does not dispatch a native job.
    reservation = resource.reserve(prepared(tmp_path, 'byte-view'), cpu_threads=64,
        policy=SimpleNamespace(memory_bytes=6 * 1024**3, scratch_bytes=64))
    assert reservation['allocation']['memory_bytes'] == 6 * 1024**3
    assert resource.snapshot()['available']['memory_bytes'] == 14 * 1024**3
    # The real canonical checker independently authenticates the actual ancestor.
    workflow_budget.active_budget()
    assert workflow_budget.ENVIRONMENT_BOUNDS['memory_bytes'] == 5 * 1024**3
    with pytest.raises(ValueError, match='^native_request_exceeds_environment_bounds$'):
        workflow_budget.native_budget(SimpleNamespace(memory_bytes=6 * 1024**3), 64, tmp_path)
    resource.release_reservation(reservation)
    assert saved_rows(directory) == (raw, [])
