"""The native-job policy recorded in receipts; never live execution configuration.

Values describe saved executions only. This module has no execution-policy,
launcher, provider, process or filesystem dependencies.
"""
from copy import deepcopy
import json

from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS

POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}


def retained_policy_matches(value):
    if type(value) is not dict:
        return False
    try:
        encoded = json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))
    except (ValueError, TypeError, OverflowError, RecursionError):
        return False
    return encoded == json.dumps(POLICY, sort_keys=True, allow_nan=False, separators=(',', ':'))


def retained_policy(value):
    if not retained_policy_matches(value):
        raise ValueError('unsupported_retained_native_policy')
    return deepcopy(POLICY)


def retained_metadata(value):
    policy = retained_policy(value)
    enforcement = {
        'memory': 'systemd_cgroup_v2_memory_max', 'swap': 'systemd_memory_swap_max_zero',
        'scratch': 'monitored_visible_allocated_bytes_with_possible_overshoot',
        'per_file_bytes': 'hard_rlimit_fsize_equal_to_scratch_bytes',
        'process_tree': 'systemd_control_group', 'filesystem_sandbox': False,
    }
    return {'native_lifecycle_version': 'durable_systemd_native_job_v2',
        'policy': policy, 'enforcement': enforcement}


def retained_cgroup(value):
    policy = retained_policy(value)
    return {'memory_max': policy['memory_bytes'], 'memory_swap_max': 0,
        'kill_mode': 'control-group', 'oom_policy': 'kill'}

