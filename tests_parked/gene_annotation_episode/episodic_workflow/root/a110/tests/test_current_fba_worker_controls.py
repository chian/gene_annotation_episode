"""Controlled current-producer record comparisons; no native execution claim."""
from copy import deepcopy
import os

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.current_fba_worker_controls import (
    current_worker_request_environment, current_worker_cgroup_matches,
)


def current_records():
    window = '12345678-1234-1234-1234-123456789abc'
    key = window.replace('-', '')
    unit, slice_ = 'gene-episode-workflow-' + key + '.service', 'geneepisodewindow' + key + '.slice'
    workflow = {'version': 'whole_workflow_budget_v2', 'window_id': window,
        'unit': unit, 'slice': slice_,
        'environment_bounds': {'cpu_percent': 100, 'memory_bytes': 5 * 1024**3, 'swap_bytes': 0},
        'run_directory': '/controlled/runs/work', 'slice_cgroup': '/user.slice/' + slice_,
        'driver_cgroup': '/user.slice/' + slice_ + '/' + unit,
        'boot_id': 'controlled-record-only', 'supervisor_pid': 5,
        'supervisor_start_ticks': '37', 'command': ['python', 'controlled.py', ''],
        'disk_bandwidth_enforced': False, 'memory_peak_scope': 'this_workflow'}
    body = {'cwd': '/controlled/runs/work/worker', 'metadata': {
        'whole_workflow_budget': workflow, 'cpu_threads': 64, 'cpu_quota_percent': 100,
        'local_resources': {'version': 'controlled-test-declaration-not-allocation'}}}
    intent = {'version': 'flux_balance_worker_intent_v3', 'environment': {
        'PYTHONDONTWRITEBYTECODE': '1', 'GENE_EPISODE_WORKFLOW_SLOT': 'overwritten-original-input'}}
    policy = {'memory_bytes': 1024, 'scratch_bytes': 2048}
    metadata = deepcopy(body['metadata'])
    metadata.update(service_exit={'SERVICE_RESULT': 'success'}, native_returncode=0,
        verified_cgroup={'memory_max': 1024, 'memory_swap_max': 0,
            'kill_mode': 'control-group', 'oom_policy': 'kill', 'workflow_slice': slice_,
            'workflow_owner': unit, 'cpu_max': '100000 100000', 'cpu_threads': 64,
            'cpu_quota_percent': 100})
    return body, intent, metadata, policy


@pytest.mark.parametrize('version', ['flux_balance_worker_intent_v3', 'flux_balance_worker_intent_v4'])
def test_current_native_injection_and_recorded_thread_metadata(version):
    body, intent, metadata, policy = current_records()
    intent['version'] = version
    before = deepcopy((body, intent, metadata, policy)); environment = dict(os.environ)
    expected = {**intent['environment'], 'GENE_EPISODE_WORKFLOW_SLOT': body['metadata']['whole_workflow_budget']['window_id'],
        'GENE_EPISODE_WORKFLOW_BUDGET_FILE': '/controlled/runs/work/workflow-budget.json'}
    assert current_worker_request_environment(body, intent) == expected
    assert current_worker_cgroup_matches(metadata, body, intent, policy)
    assert (body, intent, metadata, policy) == before and dict(os.environ) == environment


@pytest.mark.parametrize('value', [None, True, '100', {}, 200])
def test_current_marker_has_exact_source_type_and_value(value):
    body, intent, _, _ = current_records(); body['metadata']['cpu_quota_percent'] = value
    with pytest.raises(ValueError, match='^fba_preparation_request_mismatch$'):
        current_worker_request_environment(body, intent)


@pytest.mark.parametrize('version', ['flux_balance_worker_intent_v1', 'flux_balance_worker_intent_v2'])
def test_archived_worker_does_not_enter_current_controls(version):
    body, intent, _, _ = current_records(); intent['version'] = version
    with pytest.raises(ValueError, match='^fba_preparation_request_mismatch$'):
        current_worker_request_environment(body, intent)


@pytest.mark.parametrize('fault', ['quota', 'ratio', 'owner', 'threads', 'extra', 'boolean', 'workflow'])
def test_terminal_control_conflicts_remain_rejected(fault):
    body, intent, metadata, policy = current_records(); group = metadata['verified_cgroup']
    if fault == 'quota': group['cpu_quota_percent'] = 200
    elif fault == 'ratio': group['cpu_max'] = '200000 100000'
    elif fault == 'owner': group['workflow_owner'] = 'different.service'
    elif fault == 'threads': group['cpu_threads'] = 32
    elif fault == 'extra': group['unowned_control'] = True
    elif fault == 'boolean': group['memory_swap_max'] = False
    else: metadata['whole_workflow_budget']['supervisor_start_ticks'] = 'different'
    assert not current_worker_cgroup_matches(metadata, body, intent, policy)
