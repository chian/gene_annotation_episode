"""Required actual resource/type baseline; it does not claim family restoration."""
import json
import subprocess
import pytest
from .homology_family_boundaries import (actual_descriptor_boundary, actual_public_family_type_gate,
    actual_registry_close_reopen, registry)


@pytest.fixture(autouse=True)
def no_process_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('homology_saved_family_baseline_does_not_authorize_native_or_network_work')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    import socket
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def test_original_v4_family_and_three_current_descriptors(tmp_path, record_property):
    with registry(tmp_path / 'descriptor') as (store, jobs, policy, scope, job_ref):
        observation = actual_descriptor_boundary(jobs, policy)
    record_property('full_original_family_descriptor_boundary', json.dumps(observation, sort_keys=True))


def test_real_registry_close_reopen_preserves_all_private_owner_identities(tmp_path, record_property):
    with registry(tmp_path / 'reopen') as (store, jobs, policy, scope, job_ref):
        observation = actual_registry_close_reopen(jobs, policy)
    record_property('actual_registry_close_reopen', json.dumps(observation, sort_keys=True))


@pytest.mark.parametrize('reference', ('tracked_original_class', 'current_factory_map'))
def test_current_public_run_rejects_unconnected_family(tmp_path, record_property, reference):
    with registry(tmp_path / reference) as (store, jobs, policy, scope, job_ref):
        observation = actual_public_family_type_gate(store, jobs, policy, tmp_path / ('run-' + reference), reference=reference)
    assert observation['observation'] == {'status': 'raised', 'type': 'builtins.TypeError',
        'message': 'typed_homology_episode_binding_required', 'args': ['typed_homology_episode_binding_required']}
    assert observation['provider_calls'] == []
    record_property('actual_unconnected_family_type_gate', json.dumps(observation, sort_keys=True))
