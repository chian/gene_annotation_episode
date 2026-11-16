"""The native job policy that receipt readers accept, and its recorded enforcement."""
from copy import deepcopy
import json

from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS

_POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}


def retained_policy_matches(value):
    if type(value) is not dict:
        return False
    try:
        encoded = json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))
    except (ValueError, TypeError, OverflowError, RecursionError):
        return False
    return encoded == json.dumps(_POLICY, sort_keys=True, allow_nan=False, separators=(',', ':'))


def retained_policy(value):
    if not retained_policy_matches(value):
        raise ValueError('unsupported_retained_native_policy')
    return deepcopy(_POLICY)


def retained_metadata(value):
    return {'native_lifecycle_version': 'durable_systemd_native_job_v2',
        'policy': retained_policy(value), 'enforcement': {
            'memory': 'systemd_cgroup_v2_memory_max', 'swap': 'systemd_memory_swap_max_zero',
            'scratch': 'monitored_visible_allocated_bytes_with_possible_overshoot',
            'per_file_bytes': 'hard_rlimit_fsize_equal_to_scratch_bytes',
            'process_tree': 'systemd_control_group', 'filesystem_sandbox': False}}


def retained_cgroup(value):
    return {'memory_max': retained_policy(value)['memory_bytes'], 'memory_swap_max': 0,
        'kill_mode': 'control-group', 'oom_policy': 'kill'}
