"""Exact historical receipt descriptions; never live execution configuration.

The historical profile is authenticated by original049 source-before/after pins:
native_fluorescence_preparation e2c9f22d19c89cf6435ef66e6307c452234f05cb25649ed4220582835037b241,
native_fluorescence_contracts 3b5703437ee1dbd28f572699adab891d4ae095eb57ad36cd4b242cd56da56495,
native_lifecycle 7956bc4583baa31237106e1358a9e0f5e6e952b07f78c3bca334979fde276195.
The field-removed profile preserves the tracked fb1e4d9 read contract. Values
describe those saved executions only. This module has no execution-policy,
launcher, provider, process, filesystem or environment dependencies.
"""
from copy import deepcopy
import json

_PROFILES = (
    ('retained_native_fields_v1', {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}),
    ('retained_native_unset_wall_field_v1',
        {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}),
)


def _profile(value):
    if type(value) is not dict:
        return None
    try:
        encoded = json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None
    for name, policy in _PROFILES:
        if encoded == json.dumps(policy, sort_keys=True, allow_nan=False, separators=(',', ':')):
            return name, policy
    return None


def retained_policy_matches(value):
    return _profile(value) is not None


def retained_policy(value):
    selected = _profile(value)
    if selected is None:
        raise ValueError('unsupported_retained_native_policy')
    return deepcopy(selected[1])


def retained_metadata(value):
    policy = retained_policy(value)
    enforcement = {
        'memory': 'systemd_cgroup_v2_memory_max', 'swap': 'systemd_memory_swap_max_zero',
        'scratch': 'monitored_visible_allocated_bytes_with_possible_overshoot',
        'per_file_bytes': 'hard_rlimit_fsize_equal_to_scratch_bytes',
        'process_tree': 'systemd_control_group', 'filesystem_sandbox': False,
    }
    if 'wall_seconds' in policy:
        enforcement['wall_time'] = 'unset'
    return {'native_lifecycle_version': 'durable_systemd_native_job_v2',
        'policy': policy, 'enforcement': enforcement}


def retained_cgroup(value):
    policy = retained_policy(value)
    result = {'memory_max': policy['memory_bytes'], 'memory_swap_max': 0,
        'kill_mode': 'control-group', 'oom_policy': 'kill'}
    if 'wall_seconds' in policy:
        result['runtime_max'] = 'infinity'
    return result


def retained_policy_schema():
    return {'anyOf': [
        {'type': 'object', 'properties': {key: {'const': value} for key, value in policy.items()},
            'required': list(policy), 'additionalProperties': False}
        for _, policy in _PROFILES
    ]}
