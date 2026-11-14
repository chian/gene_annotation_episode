"""Actual durable registration and saved resume, distinct from legacy archives."""
import pytest
from .registered_saved_bindings import HOMES, ROLES, authenticate_capture, capture, reopen


@pytest.fixture(scope='module')
def observations(tmp_path_factory):
    directory = tmp_path_factory.mktemp('registered-private-settings')
    original = capture(directory / 'capture')
    assert all(row['status'] == 'captured' for row in original), original
    custody = authenticate_capture(directory / 'capture')
    current = reopen(directory / 'capture', directory / 'reopen', custody=custody)
    return {(row['home'], row['role']): row for row in current}


@pytest.mark.parametrize('home,role', [(home, role) for home in HOMES for role in ROLES],
    ids=[home + ':' + role for home in HOMES for role in ROLES])
def test_real_registered_private_settings_and_replay(observations, home, role):
    value = observations[home, role]
    assert value['status'] == 'returned', value
    assert value['actual_settings']['episode_bindings']
    assert value['actual_settings']['episode_application_services']['definition']['home'] == home
    assert value['actual_runtime_run']['state'] == 'created'
    assert value['queue_before'] == value['queue_after'] == [0]
    assert value['no_provider_acquisition'] and value['original_archive_unchanged']
    assert value['full_iterator_restoration_claimed'] is False
